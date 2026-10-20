#!/usr/bin/env node
// Phase 2 von site-anatomy: Messwerte zu einer Erfassung erzeugen.
// Aufruf: node measure.mjs <arbeitsordner> [--max-images 60]
// Liest kopien/capture.json (und ergebnis/legal.json fuer Crawl-delay). Schreibt nach ergebnis/:
// design.json, tokens.dtcg.json, a11y.json, images.json, text_on_image.json, measure_errors.json, versions.json.
// Bilddateien (fremde Werke) nur nach kopien/images/.
// Exit: 0 fertig, 3 Arbeitsordner/Eingabe ungueltig, 4 Werkzeugkette fehlt, 5 Zielseite blockt (Teilergebnis geschrieben).
import { mkdirSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { lookup as dnsLookup } from 'node:dns';
import http from 'node:http';
import https from 'node:https';
import { BlockList, isIP } from 'node:net';
import { join, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import { CONSENT_SELECTORS, TOOL_ROOT, honestUserAgent, loadTool, parseArgs, rejectConsent, requireWorkdir, sleep, toolVersions } from './_tool.mjs';

const PAGE_GAP_MIN_MS = 1000; // hoechstens 1 Seitenaufruf/s wie capture; robots Crawl-delay kann mehr verlangen
const IMG_GAP_MS = 1000; // hoechstens 1 Bildabruf/s je Host
const NAV_TIMEOUT = 45000; // wie capture: Konzernseiten mit Consent + Tag-Manager brauchen teils >30 s
const TEXT_ON_IMAGE_LIMIT = 30; // Hero/Teaser reichen; mehr kostet Minuten ohne neue Erkenntnis
const CONSENT_WAIT_MS = 8000; // CMP-Skripte blenden Banner teils Sekunden nach load ein
const CONSENT_WAIT_SHORT_MS = 2000; // capture fand keinen Ablehnen-Knopf: nur kurz nachsehen
const DOWNLOAD_TIMEOUT_MS = 20000; // Node-Default waere 300 s je Phase; ein Bild darf den Lauf nicht blockieren
const MAX_IMAGE_BYTES = 15e6; // Hero-Bilder liegen bei wenigen MB; groesser ist Druckdatei/Video-Standbild
const MAX_REDIRECTS = 3; // CDN-Weiterleitungen brauchen 1-2 Spruenge
const BLOCK_STATUSES = [401, 403, 429, 503]; // Vertrag: Seite blockt -> nicht weiter abfragen
const AXE_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']; // WCAG 2.2 AA; wcag21a bringt label-content-name-mismatch
const ACCEPT_LANGUAGE = 'de-DE,de;q=0.9'; // gleiche Sprachvariante wie capture (locale de-DE)
// Captcha-/Challenge-Seiten (Cloudflare u. a.) liefern oft HTTP 200: Titel und Formular verraten sie.
const CHALLENGE_TITLE = /captcha|just a moment|access denied|attention required|zugriff verweigert|are you a robot/i;
const CHALLENGE_SEL = '#challenge-form, #challenge-running, iframe[src*="challenges.cloudflare.com"]';

// --- Arbeitsordner pruefen (unter WORK_ROOT, gueltiges LOESCHDATUM; sonst Exit 3) --------------
const args = parseArgs(process.argv.slice(2), { 'max-images': 60 });
const fail = (msg) => { console.error(msg); process.exit(3); };
if (!args._[0]) fail('Aufruf: node measure.mjs <arbeitsordner> [--max-images 60]');
const WD = requireWorkdir(args._[0]);
const KOPIEN = join(WD, 'kopien'), ERGEBNIS = join(WD, 'ergebnis'), IMG_DIR = join(KOPIEN, 'images');
const readJson = (f) => { try { return JSON.parse(readFileSync(f, 'utf8')); } catch { return null; } };
const capture = readJson(join(KOPIEN, 'capture.json'));
if (!capture || !Array.isArray(capture.pages)) fail(`kopien/capture.json fehlt oder ist ungueltig in ${WD}`);
mkdirSync(ERGEBNIS, { recursive: true });
mkdirSync(IMG_DIR, { recursive: true });
for (const d of [ERGEBNIS, IMG_DIR]) if (!realpathSync(d).startsWith(WD + sep)) fail(`${d} zeigt aus dem Arbeitsordner heraus`);

const errors = [];
const step = async (name, fn) => {
  try { return await fn(); } catch (e) { errors.push({ step: name, error: String(e?.message || e) }); console.error(`FEHLER ${name}: ${e?.message || e}`); return null; }
};
const round = (x, n = 2) => Math.round(x * 10 ** n) / 10 ** n;

// Abstand je Host: Crawl-delay aus legal_check (strengster Wert gilt), mindestens 1 s.
const legal = readJson(join(ERGEBNIS, 'legal.json'));
const crawlDelay = Math.max(0, ...[].concat(legal || []).map((l) => Number(l?.crawl_delay) || 0));
const PAGE_GAP_MS = Math.max(PAGE_GAP_MIN_MS, crawlDelay * 1000);
const lastHit = new Map();
const politeWait = async (host, gap) => { const w = (lastHit.get(host) || 0) + gap - Date.now(); if (w > 0) await sleep(w); lastHit.set(host, Date.now()); };

// --- SSRF-Schutz fuer Bild-Downloads ------------------------------------------
const LOOPBACK = new BlockList();
LOOPBACK.addSubnet('127.0.0.0', 8, 'ipv4');
LOOPBACK.addAddress('::1', 'ipv6');
const NONPUBLIC = new BlockList(); // privat, link-local, CGNAT/Tailnet, Doku-, Multicast- und Reservebereiche
for (const [a, p] of [['0.0.0.0', 8], ['10.0.0.0', 8], ['100.64.0.0', 10], ['169.254.0.0', 16], ['172.16.0.0', 12], ['192.0.0.0', 24], ['192.0.2.0', 24], ['10.0.0.0', 16], ['198.18.0.0', 15], ['198.51.100.0', 24], ['203.0.113.0', 24], ['224.0.0.0', 4], ['240.0.0.0', 4]]) NONPUBLIC.addSubnet(a, p, 'ipv4');
for (const [a, p] of [['::', 96], ['64:ff9b::', 96], ['100::', 64], ['2001:db8::', 32], ['fc00::', 7], ['fe80::', 10], ['ff00::', 8]]) NONPUBLIC.addSubnet(a, p, 'ipv6');
function addrKind(addr) {
  let a = String(addr).replace(/^\[|\]$/g, '').split('%')[0].toLowerCase();
  const m = a.match(/^::ffff:(?:(\d+\.\d+\.\d+\.\d+)|([0-9a-f]{1,4}):([0-9a-f]{1,4}))$/); // IPv4-mapped
  if (m) a = m[1] || [parseInt(m[2], 16) >> 8, parseInt(m[2], 16) & 255, parseInt(m[3], 16) >> 8, parseInt(m[3], 16) & 255].join('.');
  const fam = isIP(a) === 4 ? 'ipv4' : isIP(a) === 6 ? 'ipv6' : null;
  if (!fam) return 'ungueltig';
  if (LOOPBACK.check(a, fam)) return 'loopback';
  return NONPUBLIC.check(a, fam) ? 'nicht-oeffentlich' : 'oeffentlich';
}
const lookupAll = (host) => new Promise((res, rej) => dnsLookup(host, { all: true }, (e, a) => (e ? rej(e) : res(a))));
const meta = readJson(join(WD, 'meta.json'));
const startRaw = meta?.url || capture.meta?.startUrl || capture.pages[0]?.url || '';
let startUrl = null;
try { startUrl = new URL(/^[a-z]+:\/\//i.test(startRaw) ? startRaw : `https://${startRaw}`); } catch { /* bleibt null: dann gilt nichts als Eigenbau */ }
// Loopback-Bilder nur, wenn die Startseite selbst Loopback ist (Tests, eigener Build).
let startLoopback = false;
if (startUrl) {
  const h = startUrl.hostname.replace(/^\[|\]$/g, '');
  const addrs = isIP(h) ? [{ address: h }] : await lookupAll(h).catch(() => []);
  startLoopback = addrs.length > 0 && addrs.every((x) => addrKind(x.address) === 'loopback');
}
const startPort = startUrl ? Number(startUrl.port) || (startUrl.protocol === 'https:' ? 443 : 80) : 443;
const ALLOWED_PORTS = new Set([80, 443, startPort]); // Bild-CDNs laufen auf 80/443; sonst nur der Port der Startseite
function assertPublic(host, addr) {
  const k = addrKind(addr);
  if (k === 'oeffentlich' || (k === 'loopback' && startLoopback)) return;
  throw Object.assign(new Error(`SSRF-Schutz: ${host} -> ${addr} (${k})`), { code: 'ESSRF' });
}
// Prueft die Adresse beim Verbindungsaufbau selbst, damit DNS-Rebinding zwischen Pruefung und Abruf nicht greift.
function guardedLookup(hostname, options, cb) {
  const o = options && typeof options === 'object' ? options : { family: options };
  dnsLookup(hostname, { ...o, all: true }, (err, addrs) => {
    if (err) return cb(err);
    try { for (const x of addrs) assertPublic(hostname, x.address); } catch (e) { return cb(e); }
    return o.all ? cb(null, addrs) : cb(null, addrs[0].address, addrs[0].family);
  });
}
function sniffImage(b) {
  const s = (o, t) => b.subarray(o, o + t.length).toString('latin1') === t;
  if (s(0, '\x89PNG')) return 'image/png';
  if (b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return 'image/jpeg';
  if (s(0, 'GIF8')) return 'image/gif';
  if (s(0, 'RIFF') && s(8, 'WEBP')) return 'image/webp';
  if (s(4, 'ftypavif') || s(4, 'ftypavis')) return 'image/avif';
  return null;
}
function checkTarget(u) {
  if (!/^https?:$/.test(u.protocol)) throw new Error(`nur http/https: ${u.protocol}`);
  const port = Number(u.port) || (u.protocol === 'https:' ? 443 : 80);
  if (!ALLOWED_PORTS.has(port)) throw new Error(`SSRF-Schutz: Port ${port} nicht erlaubt`);
  const h = u.hostname.replace(/^\[|\]$/g, '');
  if (isIP(h)) assertPublic(h, h); // IP-Literale laufen nicht ueber lookup
}
function requestOnce(u, headers) {
  return new Promise((resolve, rejectRaw) => {
    const reject = (e) => rejectRaw(/AbortError|TimeoutError/.test(e?.name) ? new Error(`Zeitlimit ${DOWNLOAD_TIMEOUT_MS / 1000} s ueberschritten`) : e);
    const req = (u.protocol === 'https:' ? https : http).request(u, { method: 'GET', headers, lookup: guardedLookup, signal: AbortSignal.timeout(DOWNLOAD_TIMEOUT_MS) }, (res) => {
      const h = res.headers;
      if (res.statusCode >= 300 && res.statusCode < 400 && h.location) { res.resume(); return resolve({ redirect: h.location }); }
      if (res.statusCode < 200 || res.statusCode >= 300) { res.resume(); return reject(new Error(`HTTP ${res.statusCode}`)); }
      // TDM-Vorbehalt je Bild (Header) -> nicht speichern, nicht auswerten
      if (String(h['tdm-reservation'] ?? '').trim() === '1') { res.destroy(); return resolve({ reserved: 'tdm-reservation' }); }
      if (/\bnoai\b|\bnoimageai\b/i.test(h['x-robots-tag'] || '')) { res.destroy(); return resolve({ reserved: 'x-robots-tag noai' }); }
      let type = String(h['content-type'] || '').split(';')[0].trim().toLowerCase();
      // Manche Server liefern Bilder als octet-stream; dann entscheiden die Magic Bytes (sniffImage unten)
      const sniff = type === 'application/octet-stream' || type === 'binary/octet-stream' || type === '';
      if (!type.startsWith('image/') && !sniff) { res.destroy(); return reject(new Error(`kein Bild: ${type}`)); }
      if (Number(h['content-length'] || 0) > MAX_IMAGE_BYTES) { res.destroy(); return reject(new Error(`zu gross: ${h['content-length']} Bytes`)); }
      const chunks = []; let n = 0;
      res.on('data', (c) => { n += c.length; if (n > MAX_IMAGE_BYTES) res.destroy(new Error(`zu gross: > ${MAX_IMAGE_BYTES} Bytes`)); else chunks.push(c); });
      res.on('end', () => {
        const body = Buffer.concat(chunks);
        if (sniff) { type = sniffImage(body); if (!type) return reject(new Error(`kein Bild: ${h['content-type'] || 'ohne content-type'}, Magic Bytes unbekannt`)); }
        resolve({ type, body });
      });
      res.on('error', reject);
      res.on('close', () => { if (!res.complete) reject(new Error('Verbindung abgebrochen')); });
    });
    req.on('error', reject);
    req.end();
  });
}
async function guardedGet(src, headers) {
  let u = new URL(src);
  for (let hop = 0; hop <= MAX_REDIRECTS; hop++) {
    checkTarget(u); // jede Weiterleitung neu pruefen
    const r = await requestOnce(u, headers);
    if (!r.redirect) return { ...r, finalUrl: u.href };
    u = new URL(r.redirect, u);
  }
  throw new Error(`mehr als ${MAX_REDIRECTS} Weiterleitungen`);
}

// --- Browser-Helfer (Consent-Replay: rejectConsent aus _tool.mjs, gleiche Logik wie capture) ---------
async function blockReason(page, status) {
  if (BLOCK_STATUSES.includes(status)) return `HTTP ${status}`;
  const title = await page.title().catch(() => '');
  if (CHALLENGE_TITLE.test(title)) return `Captcha/Challenge: ${title.slice(0, 80)}`;
  if (await page.locator(CHALLENGE_SEL).count().catch(() => 0)) return 'Captcha/Challenge-Formular';
  return null;
}
// axe-Ziel: Array je Frame-Ebene; eine Ebene ist ein Selektor oder eine Shadow-Kette (Array).
const chain = (scope, lvl) => (Array.isArray(lvl) ? lvl.slice(1).reduce((l, s) => l.locator(s), scope.locator(lvl[0])) : scope.locator(lvl));
function locate(page, target) {
  let scope = page;
  const owners = []; // iframe-Elemente von aussen nach innen
  for (const lvl of target.slice(0, -1)) { const owner = chain(scope, lvl).first(); owners.push(owner); scope = owner.contentFrame(); }
  return { el: chain(scope, target[target.length - 1]).first(), owners };
}
const targetLabel = (t) => t.map((l) => (Array.isArray(l) ? l.join(' >>> ') : l)).join(' |iframe| ');

// Laeuft im Browser: Textfarbe nach sRGB normieren (oklch, lab, color(), rgba) und Text samt Kindern
// unsichtbar machen; Originale bleiben am window haengen, bis restoreTextShot sie zurueckschreibt.
function prepareTextShot(n) {
  const cs = getComputedStyle(n);
  const css = cs.webkitTextFillColor || cs.color; // sichtbar ist die Fuellfarbe, falls gesetzt
  const g = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
  g.fillStyle = '#000';
  g.fillStyle = css;
  g.fillRect(0, 0, 1, 1);
  const d = g.getImageData(0, 0, 1, 1).data;
  const size = parseFloat(cs.fontSize), weight = Number(cs.fontWeight) || 400;
  const all = [n];
  const add = (root) => { for (const e of root.querySelectorAll('*')) { all.push(e); if (e.shadowRoot) add(e.shadowRoot); } };
  if (n.shadowRoot) add(n.shadowRoot);
  add(n);
  const orig = new Map();
  for (const e of all) {
    if (!e.style) continue;
    orig.set(e, e.getAttribute('style'));
    for (const [k, v] of [['color', 'transparent'], ['-webkit-text-fill-color', 'transparent'], ['text-shadow', 'none'], ['text-decoration-color', 'transparent']]) e.style.setProperty(k, v, 'important');
  }
  window[Symbol.for('site-anatomy.orig')] = orig;
  return { css, rgb: [d[0], d[1], d[2]], alpha: Math.round((d[3] / 255) * 1000) / 1000, large: size >= 24 || (size >= 18.66 && weight >= 700) };
}
function restoreTextShot() {
  const key = Symbol.for('site-anatomy.orig');
  for (const [e, s] of window[key] || []) { if (s === null) e.removeAttribute('style'); else e.setAttribute('style', s); }
  delete window[key];
}

const lum = ([r, g, b]) => { const f = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
const contrast = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05); };
// colorthief sortiert nicht nach Haeufigkeit (bei wenigen Farben gilt die Reihenfolge des ersten Auftretens).
const byPop = (p) => [...(p || [])].sort((a, b) => b.population - a.population);

// --- Ablauf ---------------------------------------------------------------------
const designlang = await loadTool('designlang');
const { chromium } = await loadTool('playwright');
const { default: AxeBuilder } = await loadTool('@axe-core/playwright');
const { getPalette } = await loadTool('colorthief');
let IGNORE_SELECTORS = CONSENT_SELECTORS;
try {
  const w = await import(pathToFileURL(join(TOOL_ROOT, 'node_modules/designlang/src/widgets.js')).href); // exports-Feld sperrt den Paketnamen
  IGNORE_SELECTORS = [...new Set([...w.WIDGET_SELECTORS, ...CONSENT_SELECTORS])];
} catch { /* nur Consent-Liste */ }

const browser = await chromium.launch({ headless: true });
const designs = [], a11y = [], textOnImage = [], images = [];
const versions = { ...toolVersions(), chromium: browser.version(), axeEngine: null };
let blocked = null;

async function measureTextOnImage(page, url, target) {
  const { el, owners } = locate(page, target);
  // Fremd-Origin-iframes ausserhalb des Sichtbereichs rendert Chromium nicht (Screenshot haengt bei "stable"):
  // erst das iframe-Element im Elternframe einscrollen.
  for (const o of owners) await o.scrollIntoViewIfNeeded({ timeout: 3000 }).catch(() => {});
  const handle = await el.elementHandle({ timeout: 3000 });
  try {
    if (!(await handle.isVisible())) return;
    const fg = await handle.evaluate(prepareTextShot);
    let buf;
    try { buf = await handle.screenshot({ timeout: 5000, animations: 'disabled' }); } finally { await handle.evaluate(restoreTextShot).catch(() => {}); }
    const pal = byPop(await getPalette(buf, { colorCount: 5, ignoreWhite: false })); // weisse Flaechen sind gerade der kritische Hintergrund
    const bg = pal.map((c) => {
      const rgb = c.array();
      const eff = fg.rgb.map((v, i) => v * fg.alpha + rgb[i] * (1 - fg.alpha)); // halbtransparenter Text mischt sich mit dem Grund
      return { hex: c.hex(), share: round(c.proportion, 3), ratio: fg.alpha > 0 ? round(contrast(eff, rgb)) : null };
    });
    const ratios = bg.map((b) => b.ratio).filter((r) => r !== null);
    const worst = ratios.length ? Math.min(...ratios) : null;
    textOnImage.push({
      url, selector: targetLabel(target), target, textColor: fg.css, textRgb: fg.rgb, textAlpha: fg.alpha, largeText: fg.large,
      background: bg, worstRatio: worst, dominantRatio: bg[0]?.ratio ?? null, passesAA: worst === null ? null : worst >= (fg.large ? 3 : 4.5),
      ...(fg.alpha === 0 && { note: 'Textfarbe transparent (z. B. background-clip:text), Kontrast nicht messbar' }),
    });
  } finally { await handle.dispose().catch(() => {}); }
}

try {
  const UA = await honestUserAgent(browser); // ein Token fuer allen Verkehr (Browser, designlang, Bildabruf)

  // Seiten, die capture als blockiert/uebersprungen/fehlerhaft vermerkt hat, nicht erneut abrufen.
  const pages = [];
  for (const p of capture.pages) {
    const why = !p?.url ? 'ohne url' : p.skipped ? `capture: ${typeof p.skipped === 'string' ? p.skipped : 'uebersprungen'}` : p.blocked ? 'capture: blockiert' : p.status >= 400 ? `capture: HTTP ${p.status}` : null;
    if (why) errors.push({ step: 'uebersprungen', url: p?.url ?? null, error: why }); else pages.push(p);
  }
  if (crawlDelay) console.error(`Crawl-delay ${crawlDelay} s -> Abstand je Seitenaufruf ${PAGE_GAP_MS / 1000} s`);

  // --- je Seite: axe + Text auf Bild, danach designlang mit demselben Consent-Zustand ---
  for (const [k, p] of pages.entries()) {
    let host;
    try { host = new URL(p.url).host; } catch { errors.push({ step: 'uebersprungen', url: p.url, error: 'ungueltige URL' }); continue; }
    await politeWait(host, PAGE_GAP_MS);
    const ctx = await browser.newContext({ locale: 'de-DE', timezoneId: 'Europe/Berlin', viewport: { width: 1280, height: 900 }, userAgent: UA });
    let ok = false, cookies;
    try {
      const page = await ctx.newPage();
      let resp = null, navErr = null;
      try { resp = await page.goto(p.url, { waitUntil: 'load', timeout: NAV_TIMEOUT }); } catch (e) { navErr = e; errors.push({ step: `goto ${p.url}`, error: String(e?.message || e) }); }
      lastHit.set(host, Date.now());
      // Fehlgeschlagene Navigation: nichts messen, sonst landet about:blank/chrome-error unter dieser URL.
      if ((navErr && navErr.name !== 'TimeoutError') || /^(about:blank|chrome-error:)/.test(page.url())) {
        a11y.push({ url: p.url, skipped: `goto fehlgeschlagen: ${String(navErr?.message || page.url()).split('\n')[0]}` });
        continue;
      }
      const entry = { url: p.url, status: resp?.status() ?? null, ...(navErr && { partial: true }) };
      const why = await blockReason(page, entry.status);
      if (why) {
        blocked = { url: p.url, status: entry.status, reason: why };
        errors.push({ step: 'blockiert', url: p.url, error: why });
        a11y.push({ url: p.url, skipped: `blockiert: ${why}` });
        break;
      }
      // capture hat abgelehnt (bzw. es versucht): Banner kommt wieder, lange warten. Kein Banner oder keiner mit Ablehnen-Knopf: kurz.
      const expectBanner = ['rejected', 'reject_failed'].includes(p.consent?.state);
      entry.consent = await rejectConsent(page, { waitMs: expectBanner ? CONSENT_WAIT_MS : CONSENT_WAIT_SHORT_MS });
      const builder = new AxeBuilder({ page }).withTags(AXE_TAGS);
      // Banner-Container immer ausschliessen, ausser er wurde wirksam abgelehnt: Ein spaet (nach dem kurzen Warten)
      // eingeblendeter Banner wuerde sonst als Verstoss der Seite gezaehlt. Ohne Banner kostet das Ausschliessen nichts.
      if (entry.consent.state !== 'rejected') for (const s of CONSENT_SELECTORS) builder.exclude(s);
      const res = await step(`axe ${p.url}`, () => builder.analyze());
      if (res) {
        versions.axeEngine ??= res.testEngine?.version ?? null;
        Object.assign(entry, {
          violations: res.violations.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length, help: v.help })),
          incomplete: res.incomplete.map((v) => ({ id: v.id, nodes: v.nodes.length, targets: v.nodes.slice(0, 20).map((n) => n.target) })),
        });
      }
      a11y.push(entry);

      // Text auf Bild: Kandidaten aus axe-incomplete (color-contrast), inkl. Shadow-DOM und iframes.
      const cc = res?.incomplete.find((v) => v.id === 'color-contrast')?.nodes || [];
      for (const n of cc.slice(0, TEXT_ON_IMAGE_LIMIT)) await step(`text-on-image ${targetLabel(n.target)}`, () => measureTextOnImage(page, p.url, n.target));

      if (entry.consent.state === 'rejected') {
        cookies = (await ctx.cookies().catch(() => [])).map(({ name, value, domain, path, expires, httpOnly, secure, sameSite }) => ({ name, value, domain, path, expires, httpOnly, secure, sameSite }));
      }
      ok = true;
    } finally { await ctx.close().catch(() => {}); }
    if (!ok) continue;

    // designlang startet einen eigenen Browser: Consent per Cookies + Ignore-Liste, gleiche Sprache und UA.
    await politeWait(host, PAGE_GAP_MS);
    const d = await step(`designlang ${p.url}`, () => designlang.extractDesignLanguage(p.url, {
      ignore: IGNORE_SELECTORS, headers: { 'Accept-Language': ACCEPT_LANGUAGE }, userAgent: UA, ...(cookies?.length && { cookies }),
    }));
    lastHit.set(host, Date.now());
    if (d) { delete d._raw; designs.push(d); } // Rohdaten sind gross und enthalten Volltext
    console.error(`gemessen ${k + 1}/${pages.length}: ${p.url}`);
  }
  if (designs[0]) {
    await step('dtcg', () => {
      const t = designlang.formatDtcgTokens(designs[0]); // liefert ein Objekt; String nicht doppelt kodieren
      writeFileSync(join(ERGEBNIS, 'tokens.dtcg.json'), typeof t === 'string' ? t : JSON.stringify(t, null, 1));
    });
  }

  // --- Bildpaletten (nicht nach einer Blockade: die Seite will gerade keine Abrufe) ---
  if (!blocked) {
    const seen = new Set();
    const imgs = pages.flatMap((p) => (p.images || []).filter((i) => i.src && i.kind !== 'icon-svg' && /^https?:/i.test(i.src)).map((i) => ({ ...i, page: p.url })))
      .filter((i) => !seen.has(i.src) && seen.add(i.src))
      .sort((a, b) => (b.shown?.w * b.shown?.h || 0) - (a.shown?.w * a.shown?.h || 0))
      .slice(0, Number(args['max-images']) || 0);
    const EXT = { 'image/jpeg': 'jpg', 'image/svg+xml': 'svg', 'image/x-icon': 'ico', 'image/vnd.microsoft.icon': 'ico' };
    for (const i of imgs) {
      await step(`bild ${i.src}`, async () => {
        const u = new URL(i.src);
        await politeWait(u.host, startUrl && u.host === startUrl.host ? PAGE_GAP_MS : IMG_GAP_MS);
        const r = await guardedGet(u.href, { 'User-Agent': UA, Accept: 'image/*', 'Accept-Language': ACCEPT_LANGUAGE, 'Accept-Encoding': 'identity', Referer: i.page });
        if (r.reserved) { images.push({ src: i.src, page: i.page, skipped: r.reserved }); return; }
        const ext = EXT[r.type] || (r.type.split('/')[1] || '').replace(/[^a-z0-9]/g, '').slice(0, 5) || 'bin';
        const name = `${createHash('sha1').update(i.src).digest('hex').slice(0, 12)}.${ext}`;
        writeFileSync(join(IMG_DIR, name), r.body);
        let pal = [], palErr = null;
        if (ext !== 'svg') { try { pal = byPop(await getPalette(r.body, { colorCount: 6, ignoreWhite: false })); } catch (e) { palErr = String(e?.message || e); } }
        images.push({
          src: i.src, ...(r.finalUrl !== i.src && { finalUrl: r.finalUrl }), page: i.page, file: `kopien/images/${name}`, bytes: r.body.length, contentType: r.type,
          kind: i.kind, alt: i.alt ?? null, shown: i.shown, natural: i.natural, aspect: i.natural?.[1] ? round(i.natural[0] / i.natural[1]) : null, objectFit: i.objectFit,
          dominant: pal[0]?.hex() ?? null, palette: pal.map((c) => c.hex()), shares: pal.map((c) => round(c.proportion, 3)), ...(palErr && { paletteError: palErr }),
        });
      });
    }
  }
} finally {
  await browser.close().catch(() => {});
  // Fremde Textstellen (Ueberschriften, Button-Texte, Titel) aus design.json nach kopien/ verschieben:
  // ergebnis/ bleibt ueber das LOESCHDATUM hinaus und soll nur Messwerte enthalten (§ 44b Abs. 2 UrhG).
  const texts = [];
  const TEXT_KEYS = new Set(['sampleHeadings', 'buttonPatterns', 'sampleText', 'heading', 'lede', 'title', 'description']);
  const isText = (v) => typeof v === 'string' || (Array.isArray(v) && v.length > 0 && v.every((x) => typeof x === 'string' || (x && typeof x.value === 'string')));
  const scrub = (o, path, parentKey) => {
    if (Array.isArray(o)) { o.forEach((v, i) => scrub(v, `${path}[${i}]`, parentKey)); return; }
    if (!o || typeof o !== 'object') return;
    for (const [k, v] of Object.entries(o)) {
      if ((TEXT_KEYS.has(k) || parentKey === 'slots') && isText(v)) { texts.push({ path: `${path}.${k}`, value: v }); o[k] = '-> kopien/design_texte.json'; }
      else scrub(v, `${path}.${k}`, k);
    }
  };
  designs.forEach((d, i) => scrub(d, `[${i}]`, null));
  if (texts.length) writeFileSync(join(WD, 'kopien', 'design_texte.json'), JSON.stringify(texts, null, 1));
  const out = { 'design.json': designs, 'a11y.json': a11y, 'text_on_image.json': textOnImage, 'images.json': images, 'measure_errors.json': errors, 'versions.json': versions };
  for (const [f, v] of Object.entries(out)) writeFileSync(join(ERGEBNIS, f), JSON.stringify(v, null, 1));
}
console.error(`fertig: ${designs.length} Designs, ${a11y.length} axe-Eintraege, ${textOnImage.length} Text-auf-Bild, ${images.length} Bilder, ${errors.length} Fehler${blocked ? `, ABGEBROCHEN (blockiert: ${blocked.url} ${blocked.reason})` : ''}`);
process.exitCode = blocked ? 5 : 0;
