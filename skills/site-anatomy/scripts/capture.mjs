#!/usr/bin/env node
// Phase 1 von site-anatomy: eine oeffentliche Website erfassen (nur lesend).
// Aufruf: node capture.mjs <url> --out <arbeitsordner> [--pages N] [--start-freigegeben]
//   <arbeitsordner>: von "workdir.py init <url>" angelegt (unter ~/site-anatomy/, mit LOESCHDATUM).
//   --pages N: zusaetzliche Seiten aus der Hauptnavigation (Default 5, hoechstens 19).
//   --start-freigegeben: der Nutzer hat einen Vorbehalt (legal_check Exit 2) fuer die START-URL ausdruecklich
//     freigegeben. Unterseiten mit Vorbehalt werden immer uebersprungen.
// Jede Seite (auch die Startseite) wird vor dem Besuch per legal_check.py geprueft.
// Schreibt kopien/capture.json (nach jeder Seite), kopien/pages/<n>/text.md, kopien/shots/<n>/*.png,
//   ergebnis/capture_errors.json; legal_check.py haengt je URL an ergebnis/legal.json an.
// Exit: 0 Startseite erfasst (Unterseiten ggf. in skipped[]/blocked[], Fehler in capture_errors.json)
//       1 Startseite technisch gescheitert   2 Startseite: Vorbehalt oder unklar (legal_check Exit 2)
//       3 Aufruf/Arbeitsordner ungueltig oder Startseite nicht erreichbar   4 Werkzeugkette fehlt
//       5 Startseite blockiert (HTTP 401/403/429/503 oder Captcha/Bot-Schutz)
import { execFile } from 'node:child_process';
import { mkdirSync, realpathSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { CONSENT_SELECTORS, honestUserAgent, loadTool, parseArgs, rejectConsent, requireWorkdir, sleep, toolVersion, toolVersions } from './_tool.mjs';

const VIEWPORTS = [390, 768, 1280, 1920]; // Handy, Tablet, Laptop, Desktop-breit
const SCHEMES = ['light', 'dark'];
const MIN_GAP_MS = 1000; // hoechstens 1 Seitenaufruf pro Sekunde; groesseres Crawl-delay aus robots.txt gewinnt
const NAV_TIMEOUT = 45000; // bis DOMContentLoaded; Konzernseiten mit Consent + Tag-Manager brauchen teils >30 s
const LOAD_TIMEOUT = 30000; // danach auf "load" warten; ueberschritten = Teilstand erfassen statt neu laden
const NETWORK_IDLE_MS = 8000; // Tracker halten networkidle oft dauerhaft offen: kurz warten, nie neu navigieren
const CONSENT_WAIT_MS = 8000; // erster Besuch: so lange auf spaet eingeblendete Banner (asynchrone CMPs) warten
const CONSENT_RECHECK_MS = 2500; // weitere Besuche: Banner ist bekannt bzw. die Ablehnung gespeichert
const SCROLL_MAX_Y = 30000; // Endlos-Feeds wachsen beim Scrollen unbegrenzt; ~30 Bildschirmhoehen reichen
const SCROLL_DEADLINE_MS = 15000; // page.evaluate hat keinen eigenen Timeout
const SHOT_MAX_H = 30000; // Screenshot gleich hoch kappen (1920 x 30000 px sind schon ~230 MB Bitmap)
const HOVER_TIMEOUT = 2000; // sichtbare Eintraege reagieren sofort; verdeckte nicht lange abwarten
const NAV_HOVER_MAX = 8; // Hauptnavigationen haben selten mehr Top-Eintraege mit Megamenue
const MAX_PAGES = 20;
const LEGAL_TIMEOUT_MS = 120000; // legal_check: je Abruf 15 s Timeout, mit Weiterleitung ueber zwei Origins ~6 Abrufe, plus Reserve
const BLOCK_STATUS = new Set([401, 403, 429, 503]); // Login, verboten, Rate-Limit, Wartung/Bot-Schutz
const STOP_STATUS = new Set([429, 503]); // Ziel drosselt oder wehrt Bots ab: danach keine weiteren Seiten
const CAPTCHA_TITLE = /captcha|just a moment|attention required|access denied|zugriff verweigert|are you (a )?(human|robot)|bot.?(check|detection|protection)|security check|sicherheits(ue|ü)berpr(ue|ü)fung|pardon our interruption/i;
const CAPTCHA_TEXT = /captcha|verify you are (a )?human|best(ae|ä)tigen sie, dass sie (ein )?mensch|ungew(oe|ö)hnliche[nr]? (aktivit(ae|ä)t|datenverkehr)|unusual traffic|enable javascript and cookies to continue/i;
const CAPTCHA_MARKERS = '#challenge-form, #challenge-running, #cf-challenge-running, .cf-browser-verification, #px-captcha, iframe[src*="captcha-delivery.com"], #captcha-container';
const CAPTCHA_SHORT_TEXT = 3000; // Sperrseiten sind kurz; laengere Seiten mit Captcha im Kontaktformular sind normal
const TRACKING_PARAM = /^(utm_|wt_|mc_|gclid$|fbclid$|msclkid$|ref$|icid$)/i; // gleiche Seite, nur Kampagnen-Kennung
const NON_HTML = /\.(pdf|zip|rar|7z|gz|tar|docx?|xlsx?|pptx?|odt|ods|odp|csv|rtf|jpe?g|png|gif|svg|webp|avif|ico|bmp|tiff?|mp4|webm|mov|m4v|mp3|wav|ogg|m4a|exe|msi|dmg|apk|ics|vcf|xml|json|txt)$/i; // goto wuerde einen Download starten und abbrechen
const AB_PATTERNS = /optimizely|abtasty|kameleoon|ablyft|visualwebsiteoptimizer|vwo\.com|convert\.com|dynamicyield|googleoptimize|\/at\.js|mbox|target\.adobe|launchdarkly|growthbook|split\.io/i;

// --- Aufruf und Arbeitsordner ------------------------------------------------------------------
const args = parseArgs(process.argv.slice(2), { pages: 5 }, ['start-freigegeben']);
if (args._.length !== 1 || !args.out || args.out === true) {
  console.error('Aufruf: node capture.mjs <url> --out <arbeitsordner> [--pages N] [--start-freigegeben]  (genau eine URL je Lauf)');
  process.exit(3);
}
let startUrl = String(args._[0]).trim();
if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(startUrl)) startUrl = `https://${startUrl}`; // "telekom.de" wie getippt
try {
  const u = new URL(startUrl);
  if (!['http:', 'https:'].includes(u.protocol)) throw new Error(u.protocol);
  startUrl = u.href;
} catch {
  console.error(`ungueltige URL: ${args._[0]} (nur http/https)`);
  process.exit(3);
}
const extraPages = Math.max(0, Math.min(Math.floor(Number(args.pages)) || 0, MAX_PAGES - 1));
const WD = requireWorkdir(args.out);
const KOPIEN = join(WD, 'kopien'), ERGEBNIS = join(WD, 'ergebnis');
for (const d of [KOPIEN, ERGEBNIS]) {
  mkdirSync(d, { recursive: true });
  if (realpathSync(d) !== d) { console.error(`Arbeitsordner ungueltig: ${d} ist ein Symlink`); process.exit(3); }
}
const CAPTURE_JSON = join(KOPIEN, 'capture.json');
const ERRORS_JSON = join(ERGEBNIS, 'capture_errors.json');
const LEGAL_JSON = join(ERGEBNIS, 'legal.json');
const SCRIPTS_DIR = dirname(fileURLToPath(import.meta.url));

const result = {
  meta: { startUrl, capturedAt: new Date().toISOString(), viewports: VIEWPORTS, schemes: SCHEMES, locale: 'de-DE', timezone: 'Europe/Berlin', minGapMs: MIN_GAP_MS, pagesRequested: 1 + extraPages },
  pages: [], skipped: [], blocked: [], aborted: null, stopped: null,
};
const errors = [];

function writeJsonAtomic(file, data) {
  const tmp = `${file}.tmp`;
  writeFileSync(tmp, JSON.stringify(data, null, 1));
  renameSync(tmp, file);
}
function save() {
  result.meta.updatedAt = new Date().toISOString();
  writeJsonAtomic(CAPTURE_JSON, result);
  writeJsonAtomic(ERRORS_JSON, errors);
}
function logError(pageRec, url, scheme, step, e) {
  const entry = { url, scheme, step, error: String(e?.message || e).split('\n')[0].slice(0, 500), at: new Date().toISOString() };
  errors.push(entry);
  pageRec?.errors.push(entry);
  console.error(`FEHLER ${step} ${url} (${scheme}): ${entry.error}`);
}

// Besuchs-URL: ohne Anker und Kampagnen-Parameter (der Pfad bleibt, /a und /a/ koennen verschieden sein).
function cleanUrl(u) {
  try {
    const x = new URL(u);
    x.hash = '';
    for (const k of [...x.searchParams.keys()]) if (TRACKING_PARAM.test(k)) x.searchParams.delete(k);
    return x.href.replace(/\?$/, '');
  } catch { return null; }
}
// Vergleichsschluessel "gleiche Seite": zusaetzlich ohne Schraegstrich am Ende, Parameter sortiert.
function normUrl(u) {
  const c = cleanUrl(u);
  if (!c) return null;
  const x = new URL(c);
  x.searchParams.sort();
  if (x.pathname.length > 1) x.pathname = x.pathname.replace(/\/+$/, '') || '/';
  return x.href.replace(/\?$/, '');
}

// --- Hoeflichkeit gegenueber der Zielseite ------------------------------------------------------
// Der Abstand zaehlt ab dem Ende des letzten Abrufs (Seitenaufruf oder legal_check).
let lastReq = 0;
async function politeWait() {
  const w = lastReq + result.meta.minGapMs - Date.now();
  if (w > 0) await sleep(w);
}
const markReq = () => { lastReq = Date.now(); };
function noteCrawlDelay(cd) {
  const s = Number(cd);
  if (!Number.isFinite(s) || s <= 0 || s * 1000 <= result.meta.minGapMs) return;
  result.meta.minGapMs = Math.round(s * 1000);
  result.meta.crawlDelay = s;
  if (s > 30) console.error(`Hinweis: robots.txt verlangt Crawl-delay ${s} s - der Lauf dauert entsprechend.`);
}

// --- Rechts-Check je URL -----------------------------------------------------------------------
async function legalCheck(url) {
  await politeWait();
  try {
    return await new Promise((resolve) => {
      execFile('python3', ['-I', join(SCRIPTS_DIR, 'legal_check.py'), url, '--out', LEGAL_JSON],
        { timeout: LEGAL_TIMEOUT_MS, maxBuffer: 8 * 1024 * 1024 },
        (err, stdout, stderr) => {
          let json = null;
          try { json = JSON.parse(stdout); } catch { /* kein JSON = Aufruffehler, unten fail-closed */ }
          resolve({ code: err ? (typeof err.code === 'number' ? err.code : -1) : 0, json, stderr: String(stderr || '').trim().slice(-300) });
        });
    });
  } finally {
    markReq();
  }
}
// Fail-closed: frei ist eine URL nur bei Exit 0 UND JSON "reserved": false.
function legalVerdict(r) {
  noteCrawlDelay(r.json?.crawl_delay);
  const status = Number(r.json?.status ?? /HTTP Error (\d{3})/.exec(r.json?.error || '')?.[1]) || null;
  if (status && BLOCK_STATUS.has(status)) return { ok: false, kind: 'blocked', status, reason: `HTTP ${status} (legal_check)`, legalExit: r.code };
  if (r.code === 0 && r.json && r.json.reserved === false) return { ok: true };
  if (r.code === 2) return { ok: false, kind: 'skipped', reason: 'Vorbehalt oder unklar (legal_check Exit 2, Fundstelle in ergebnis/legal.json)', legalExit: 2 };
  if (r.code === 3) return { ok: false, kind: 'skipped', reason: `nicht erreichbar oder ungueltig (legal_check Exit 3${r.json?.error ? `: ${r.json.error}` : ''})`, legalExit: 3 };
  return { ok: false, kind: 'skipped', reason: `legal_check ohne gueltiges Ergebnis (Exit ${r.code}${r.stderr ? `: ${r.stderr}` : ''})`, legalExit: r.code };
}

// TDM-Vorbehalt in der Antwort, die der Browser tatsaechlich bekam (kann vom legal_check-Abruf abweichen).
async function browserReservation(page, resp) {
  const h = resp?.headers() || {};
  const found = [];
  if ((h['tdm-reservation'] || '').trim() === '1') found.push('Header tdm-reservation: 1');
  if (/\bno(image)?ai\b/i.test(h['x-robots-tag'] || '')) found.push(`Header x-robots-tag: ${h['x-robots-tag']}`);
  const metas = await page.evaluate(() => [...document.querySelectorAll('meta[name]')].map((m) => [m.name.toLowerCase(), (m.content || '').toLowerCase()])).catch(() => []);
  for (const [n, c] of metas) {
    if (n === 'tdm-reservation' && c.trim() === '1') found.push('Meta tdm-reservation: 1');
    if ((n === 'robots' || n === 'googlebot') && /\bno(image)?ai\b/.test(c)) found.push(`Meta ${n}: ${c}`);
  }
  return found.length ? found.join('; ') : null;
}

// Sperre durch die Seite: Statuscode oder Captcha-/Bot-Schutz-Seite. Nie umgehen, nur vermerken.
async function blockedReason(page, status) {
  if (status && BLOCK_STATUS.has(status)) return { status, reason: `HTTP ${status}` };
  const hint = await page.evaluate(({ markers, max }) => ({
    title: document.title || '',
    marker: !!document.querySelector(markers),
    text: (document.body?.innerText || '').slice(0, max + 1),
  }), { markers: CAPTCHA_MARKERS, max: CAPTCHA_SHORT_TEXT }).catch(() => null);
  if (!hint) return null;
  const short = hint.text.length <= CAPTCHA_SHORT_TEXT;
  if (CAPTCHA_TITLE.test(hint.title) || (short && (hint.marker || CAPTCHA_TEXT.test(hint.text)))) {
    return { status, reason: `Captcha/Bot-Schutz (Titel: ${hint.title.slice(0, 80)})` };
  }
  return null;
}

async function politeGoto(page, url) {
  await politeWait();
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    const loaded = await page.waitForLoadState('load', { timeout: LOAD_TIMEOUT }).then(() => true, () => false);
    await page.waitForLoadState('networkidle', { timeout: NETWORK_IDLE_MS }).catch(() => {});
    return { resp, loaded };
  } finally {
    markReq();
  }
}

async function autoScroll(page) {
  // Lazy-Load-Bilder und Scroll-Animationen ausloesen, dann zurueck nach oben. Gedeckelt (Endlos-Feeds).
  const r = await page.evaluate(async ({ maxY, deadlineMs }) => {
    const step = Math.max(200, Math.floor(window.innerHeight * 0.8));
    const end = Date.now() + deadlineMs;
    let y = 0;
    for (; y < Math.min(document.documentElement.scrollHeight, maxY) && Date.now() < end; y += step) {
      window.scrollTo(0, y);
      await new Promise((res) => setTimeout(res, 120));
    }
    window.scrollTo(0, 0);
    return { scrolledTo: y, height: document.documentElement.scrollHeight };
  }, { maxY: SCROLL_MAX_Y, deadlineMs: SCROLL_DEADLINE_MS });
  await sleep(500);
  return r;
}

async function fullShot(page, file, width) {
  const h = await page.evaluate(() => Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0));
  await page.screenshot({ path: file, fullPage: true, clip: { x: 0, y: 0, width, height: Math.max(1, Math.min(h, SHOT_MAX_H)) } });
  return { pageHeight: h, truncated: h > SHOT_MAX_H };
}

// Laeuft im Browser: alles Inhaltliche einer Seite in einem Durchgang.
function extractPage({ ab, cmp, nonHtml }) {
  const AB = new RegExp(ab, 'i');
  const NON_HTML = new RegExp(nonHtml, 'i');
  const isCmp = (el) => { try { return el.matches(cmp); } catch { return false; } };
  // Consent-Banner samt Unterbaum (auch dessen Shadow Root) gehoeren nicht zur Gestaltung der Seite.
  const walk = (root, fn) => {
    const it = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT, { acceptNode: (n) => (isCmp(n) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) });
    // currentNode ist anfangs root; ein ShadowRoot ist kein Element (kein tagName) -> beim ersten Kind beginnen.
    for (let n = root.nodeType === Node.ELEMENT_NODE ? root : it.nextNode(); n; n = it.nextNode()) {
      try { fn(n); } catch { /* ein exotisches Element darf nicht die ganze Seite kippen */ }
      if (n.shadowRoot) walk(n.shadowRoot, fn);
    }
  };
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none';
  };
  const rect = (el) => { const r = el.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y + scrollY), w: Math.round(r.width), h: Math.round(r.height) }; };
  const txt = (el) => (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
  // Listenpunkt ohne Unterlisten und eigene Bloecke: die werden selbst ausgegeben (sonst Text doppelt).
  const NESTED_BLOCK = 'ul,ol,p,blockquote,table,figure,figcaption,h1,h2,h3,h4,h5,h6';
  const ownText = (el) => {
    let s = '';
    for (const c of el.childNodes) {
      if (c.nodeType === 3) s += c.textContent;
      else if (c.nodeType === 1 && !c.matches(NESTED_BLOCK) && getComputedStyle(c).display !== 'none') s += ` ${ownText(c)}`;
    }
    return s;
  };

  const headings = [], images = [], ctas = [], md = [];
  const seenBg = new Set();
  walk(document.body, (el) => {
    const tag = el.tagName.toLowerCase();
    if (/^h[1-6]$/.test(tag) && visible(el)) {
      headings.push({ level: Number(tag[1]), text: txt(el), y: rect(el).y });
      md.push(`${'#'.repeat(Number(tag[1]))} ${txt(el)}`);
    } else if (['p', 'li', 'blockquote', 'figcaption', 'td'].includes(tag) && visible(el) && !el.parentElement?.closest('p,blockquote,figcaption,td')) {
      // Bloecke in p/blockquote/figcaption/td stecken schon in deren Text.
      const t = (tag === 'li' ? ownText(el) : txt(el)).replace(/\s+/g, ' ').trim();
      if (t) md.push(tag === 'li' ? `- ${t}` : t);
    }
    if (tag === 'img' && visible(el)) {
      const cs = getComputedStyle(el);
      const pic = el.closest('picture');
      images.push({
        kind: 'img', src: el.currentSrc || el.src, srcset: el.getAttribute('srcset') || el.dataset.srcset || null,
        dataSrc: el.dataset.src || null, sizes: el.getAttribute('sizes'), alt: el.getAttribute('alt'),
        loading: el.getAttribute('loading'), natural: [el.naturalWidth, el.naturalHeight], shown: rect(el),
        objectFit: cs.objectFit, objectPosition: cs.objectPosition,
        sources: pic ? [...pic.querySelectorAll('source')].map((s) => ({ media: s.media, type: s.type, srcset: s.srcset })) : [],
      });
    } else if (tag === 'video' && el.poster) {
      images.push({ kind: 'video-poster', src: el.poster, shown: rect(el) });
    } else if (tag === 'svg' && visible(el) && el.getBoundingClientRect().width <= 64) {
      images.push({ kind: 'icon-svg', shown: rect(el), viewBox: el.getAttribute('viewBox'), stroke: getComputedStyle(el).stroke, fill: getComputedStyle(el).fill });
    }
    const bg = getComputedStyle(el).backgroundImage;
    if (bg && bg.includes('url(') && visible(el)) {
      for (const m of bg.matchAll(/url\(["']?([^"')]+)["']?\)/g)) {
        if (!seenBg.has(m[1])) { seenBg.add(m[1]); images.push({ kind: 'css-background', src: new URL(m[1], location.href).href, shown: rect(el), size: getComputedStyle(el).backgroundSize, position: getComputedStyle(el).backgroundPosition }); }
      }
    }
    const isButtonish = tag === 'button' || el.getAttribute('role') === 'button' ||
      (tag === 'a' && (() => { const cs = getComputedStyle(el); return cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && parseFloat(cs.paddingLeft) >= 8; })());
    if (isButtonish && visible(el) && txt(el)) {
      const cs = getComputedStyle(el);
      ctas.push({ text: txt(el), href: el.getAttribute('href'), rect: rect(el), bg: cs.backgroundColor, color: cs.color, radius: cs.borderRadius, fontWeight: cs.fontWeight });
    }
  });

  const bodyText = document.body.innerText;
  const trust = {
    prices: [...bodyText.matchAll(/\d{1,5},\d{2}\s?€|€\s?\d{1,5},\d{2}/g)].slice(0, 50).map((m) => m[0]),
    monthly: (bodyText.match(/mtl\.|monatlich|pro monat/gi) || []).length,
    footnoteMarkers: (bodyText.match(/\d\)|\*{1,3}(?=\s|$)/g) || []).length,
    sealAlts: [...document.querySelectorAll('img[alt]')].map((i) => i.alt).filter((a) => /tüv|testsieger|siegel|award|bewertung|trusted|zertifi|ausgezeichnet/i.test(a)),
    forms: [...document.forms].map((f) => ({ fields: f.querySelectorAll('input:not([type=hidden]),select,textarea').length, action: f.getAttribute('action') })),
  };
  const scripts = [...document.scripts].map((s) => s.src).filter(Boolean);
  const hosts = [...new Set(scripts.map((s) => { try { return new URL(s).host; } catch { return null; } }).filter(Boolean))];
  const tech = {
    generator: document.querySelector('meta[name=generator]')?.content || null,
    globals: ['__NEXT_DATA__', '__NUXT__', '__remixContext', 'Shopify', 'angular', 'Vue', '__SVELTEKIT_DATA__', 'dataLayer', 'utag', '_satellite', 'adobe']
      .filter((g) => typeof window[g] !== 'undefined'),
    frameworkHints: { reactRoot: !!document.querySelector('[data-reactroot], #__next'), ngVersion: document.querySelector('[ng-version]')?.getAttribute('ng-version') || null },
    scriptHosts: hosts,
    fonts: [...document.fonts].filter((f) => f.status === 'loaded').map((f) => `${f.family} ${f.weight} ${f.style}`),
  };
  const abHits = scripts.filter((s) => AB.test(s));
  const meta = {
    title: document.title, lang: document.documentElement.lang,
    description: document.querySelector('meta[name=description]')?.content || null,
    canonical: document.querySelector('link[rel=canonical]')?.href || null,
    og: Object.fromEntries([...document.querySelectorAll('meta[property^="og:"]')].map((m) => [m.getAttribute('property'), m.content])),
    jsonLdTypes: [...document.querySelectorAll('script[type="application/ld+json"]')].flatMap((s) => { try { const j = JSON.parse(s.textContent); return [].concat(j).map((x) => x['@type']); } catch { return ['(ungueltig)']; } }),
  };
  // Navigationsziele: gleiche Origin, nur HTML-Seiten, Anker abgeschnitten statt Link verworfen.
  const navLinks = [];
  for (const a of document.querySelectorAll('nav a[href], header a[href]')) {
    try {
      const u = new URL(a.href);
      if (u.origin !== location.origin || a.hasAttribute('download') || NON_HTML.test(u.pathname)) continue;
      u.hash = '';
      navLinks.push(u.href);
    } catch { /* ungueltige href */ }
  }
  return { headings, images, ctas, trust, tech, ab: abHits, meta, markdown: md.join('\n\n'), navLinks: [...new Set(navLinks)], pageHeight: document.documentElement.scrollHeight };
}

async function navSnapshot(page, shotDir) {
  // Navigationsbaum als ARIA-Snapshot, Megamenues per Hover auf sichtbare Top-Eintraege aufklappen.
  const nav = page.locator('header nav, nav[aria-label], [role=navigation]').filter({ visible: true }).first();
  if (!(await nav.count().catch(() => 0))) return { tree: null, hovered: [] };
  const tree = await nav.ariaSnapshot({ timeout: 5000 }).catch(() => null);
  const items = nav.locator('a, button').filter({ visible: true });
  // Handles statt nth(): nach einem Hover werden Megamenue-Links sichtbar und verschieben die Indizes.
  const handles = await items.elementHandles().catch(() => []);
  const isTop = await Promise.all(handles.map((h) => h.evaluate((el) => {
    // Top-Ebene = hoechstens ein Listenpunkt zwischen Eintrag und Navigation (tiefer = Untermenue).
    const root = el.closest('nav, [role=navigation]');
    let depth = 0;
    for (let p = el.parentElement; p && p !== root; p = p.parentElement) if (p.tagName === 'LI') depth++;
    return depth <= 1;
  }).catch(() => false)));
  const top = handles.filter((_, i) => isTop[i]).slice(0, NAV_HOVER_MAX);
  const hovered = [];
  for (const [i, h] of top.entries()) {
    const label = ((await h.textContent().catch(() => '')) || '').replace(/\s+/g, ' ').trim();
    if (!(await h.hover({ timeout: HOVER_TIMEOUT }).then(() => true, () => false))) {
      hovered.push({ label, screenshot: null, note: 'nicht hoverbar (verdeckt oder verschwunden)' });
      continue;
    }
    await sleep(600);
    const file = join(shotDir, `nav_hover_${i}.png`);
    const shot = await page.screenshot({ path: file }).then(() => file, () => null);
    hovered.push({ label, screenshot: shot, snapshot: await nav.ariaSnapshot({ timeout: 3000 }).catch(() => null) });
    await page.mouse.move(0, 0).catch(() => {});
    await sleep(300);
  }
  await Promise.all(handles.map((h) => h.dispose().catch(() => {})));
  return { tree, hovered };
}

// --- Hauptlauf ---------------------------------------------------------------------------------
const { chromium } = await loadTool('playwright');
const browser = await chromium.launch({ headless: true });
let exitCode = 0;
try {
  const userAgent = await honestUserAgent(browser);
  Object.assign(result.meta, { userAgent, chromium: browser.version(), playwright: toolVersion('playwright'), tools: toolVersions() });
  const ctxBase = { locale: 'de-DE', timezoneId: 'Europe/Berlin', viewport: { width: 1280, height: 900 }, userAgent };
  const queue = [startUrl];
  const seen = new Set([normUrl(startUrl)]); // eingereiht
  const capturedFinal = new Set(); // tatsaechlich besuchte Ziel-URLs (nach Weiterleitung)
  const maxCaptured = 1 + extraPages;
  const maxAttempts = 2 * maxCaptured; // gesperrte Kandidaten duerfen nicht beliebig viele Pruefabrufe ausloesen
  let baseOrigin = new URL(startUrl).origin;
  let consentStorage = null, consentSeen = false;
  const t0 = Date.now();
  save();

  for (let idx = 0; idx < queue.length && idx < maxAttempts && result.pages.length < maxCaptured; idx++) {
    const url = queue[idx];
    const isStart = idx === 0;
    const startFree = isStart && args['start-freigegeben'] === true;

    // 1. Rechts-Check vor dem Besuch
    const lc = await legalCheck(url);
    const v = legalVerdict(lc);
    if (isStart) result.meta.legalStart = { exit: lc.code, reserved: lc.json?.reserved ?? null, final_url: lc.json?.final_url ?? null, ...(startFree && { freigegeben: true }) };
    if (!v.ok && !(startFree && v.legalExit === 2 && v.kind !== 'blocked')) {
      const rec = { url, kind: v.kind, reason: v.reason, legalExit: v.legalExit, ...(v.status && { status: v.status }) };
      (v.kind === 'blocked' ? result.blocked : result.skipped).push(rec);
      if (isStart) {
        result.aborted = rec;
        exitCode = v.kind === 'blocked' ? 5 : v.legalExit === 2 ? 2 : v.legalExit === 3 ? 3 : 1;
        console.error(`Startseite nicht erfasst: ${v.reason}`);
        break;
      }
      console.error(`${v.kind === 'blocked' ? 'blockiert' : 'uebersprungen'}: ${url} (${v.reason})`);
      if (v.kind === 'blocked' && STOP_STATUS.has(v.status)) { result.stopped = { url, reason: `HTTP ${v.status}: Ziel drosselt, keine weiteren Seiten` }; break; }
      save();
      continue;
    }

    // 2. Erfassen, je Farbschema ein eigener Kontext
    const slot = String(result.pages.length);
    const shotDir = join(KOPIEN, 'shots', slot), pageDir = join(KOPIEN, 'pages', slot);
    const pageRec = { url, shots: [], errors: [] };
    let drop = null; // gesetzt = Seite wird nicht (weiter) erfasst
    for (const scheme of SCHEMES) {
      let ctx = null, stepName = 'context';
      try {
        ctx = await browser.newContext({ ...ctxBase, colorScheme: scheme, ...(consentStorage && { storageState: consentStorage }) });
        const page = await ctx.newPage();
        stepName = 'goto';
        const { resp, loaded } = await politeGoto(page, url);
        const status = resp?.status() ?? null;
        stepName = 'sperrpruefung';
        const block = await blockedReason(page, status);
        if (block) { drop = { kind: 'blocked', scheme, ...block }; break; }
        if (scheme === 'light') {
          Object.assign(pageRec, { status, finalUrl: page.url(), ...(!loaded && { partial: `load-Ereignis nach ${LOAD_TIMEOUT / 1000} s nicht erreicht` }) });
          const fin = normUrl(page.url());
          if (isStart) { baseOrigin = new URL(page.url()).origin; seen.add(fin); }
          else if (new URL(page.url()).origin !== baseOrigin) { drop = { kind: 'skipped', reason: `umgeleitet auf fremden Origin ${new URL(page.url()).origin}` }; break; }
          if (fin !== normUrl(url) && capturedFinal.has(fin)) { drop = { kind: 'skipped', reason: `umgeleitet auf bereits erfasste Seite ${page.url()}` }; break; }
          if (fin !== normUrl(url) && fin !== normUrl(lc.json?.final_url)) {
            // Browser landete woanders als legal_check (JS- oder UA-abhaengige Weiterleitung): Ziel nachpruefen.
            stepName = 'legal_check Weiterleitungsziel';
            const v2 = legalVerdict(await legalCheck(page.url()));
            if (!v2.ok && !(startFree && v2.legalExit === 2 && v2.kind !== 'blocked')) { drop = { kind: v2.kind, reason: `Weiterleitungsziel ${page.url()}: ${v2.reason}`, legalExit: v2.legalExit, ...(v2.status && { status: v2.status }) }; break; }
          }
          const reservation = await browserReservation(page, resp);
          if (reservation && !startFree) { drop = { kind: 'skipped', reason: `Vorbehalt in der Browser-Antwort: ${reservation}`, legalExit: 2 }; break; }
          if (reservation) pageRec.reservation = { found: reservation, freigegeben: true };
          capturedFinal.add(fin);
        } else if (status !== pageRec.status) pageRec.statusDark = status;

        stepName = 'consent';
        let consent = await rejectConsent(page, { waitMs: consentSeen ? CONSENT_RECHECK_MS : CONSENT_WAIT_MS });
        consentSeen = true;
        // Nur ohne sichtbaren Banner gilt die fruehere Ablehnung weiter; erscheint trotzdem einer
        // (no_reject_button_found), bleibt der Zustand stehen, damit der Bericht ihn meldet.
        if (consent.state === 'no_banner' && consentStorage) consent = { ...consent, state: 'rejected', inherited: true, note: 'frueher wirksame Ablehnung uebernommen, Banner nicht erneut erschienen' };
        if (scheme === 'light') pageRec.consent = consent; else pageRec.consentDark = consent;
        // Wirksame Ablehnung fuer alle weiteren Kontexte uebernehmen (wie ein Besucher, der einmal ablehnt);
        // nach jeder neuen Ablehnung erneuern, damit spaeter abgelehnte Banner dazukommen.
        if (consent.state === 'rejected' && consent.hits.length) consentStorage = (await ctx.storageState().catch(() => null)) ?? consentStorage;

        mkdirSync(shotDir, { recursive: true });
        for (const width of VIEWPORTS) {
          const file = join(shotDir, `${width}_${scheme}.png`);
          stepName = `screenshot ${width}_${scheme}`;
          try {
            await page.setViewportSize({ width, height: 900 });
            await sleep(400);
            const sc = await autoScroll(page);
            const shot = await fullShot(page, file, width);
            pageRec.shots.push(file);
            if (shot.truncated || sc.scrolledTo < Math.min(sc.height, SCROLL_MAX_Y)) {
              (pageRec.limits ??= []).push({ file, pageHeight: shot.pageHeight, shotHeightMax: SHOT_MAX_H, scrolledTo: sc.scrolledTo });
            }
          } catch (e) {
            logError(pageRec, url, scheme, stepName, e);
          }
        }

        if (scheme === 'light') {
          stepName = 'extract';
          await page.setViewportSize({ width: 1280, height: 900 });
          await autoScroll(page);
          const data = await page.evaluate(extractPage, { ab: AB_PATTERNS.source, cmp: CONSENT_SELECTORS.join(','), nonHtml: NON_HTML.source });
          mkdirSync(pageDir, { recursive: true });
          writeFileSync(join(pageDir, 'text.md'), `<!-- Quelle: ${page.url()} — fremdes Werk, nur zur Analyse, Loeschdatum beachten -->\n\n${data.markdown}\n`);
          delete data.markdown;
          Object.assign(pageRec, data);
          stepName = 'navigation';
          pageRec.nav = await navSnapshot(page, shotDir);
          if (isStart) {
            for (const l of data.navLinks) {
              const n = normUrl(l);
              if (n && !seen.has(n)) { seen.add(n); queue.push(cleanUrl(l)); }
            }
          }
        }
      } catch (e) {
        logError(pageRec, url, scheme, stepName, e);
        if (stepName === 'context' || stepName === 'goto') break; // nicht noch einmal laden, wenn schon der Abruf scheitert
      } finally {
        await ctx?.close().catch(() => {});
      }
    }

    // 3. Ergebnis der Seite verbuchen
    const hasData = pageRec.shots.length > 0 || pageRec.headings !== undefined;
    if (drop && drop.kind === 'blocked' && drop.scheme === 'dark' && hasData) {
      pageRec.blockedDark = drop; // hell erfasst, dunkel gesperrt: Seite bleibt, Sperre wird vermerkt
      result.blocked.push({ url, ...drop });
    } else if (drop) {
      const rec = { url, ...drop };
      (drop.kind === 'blocked' ? result.blocked : result.skipped).push(rec);
      console.error(`${drop.kind === 'blocked' ? 'blockiert' : 'uebersprungen'}: ${url} (${drop.reason})`);
      if (isStart) {
        result.aborted = rec;
        exitCode = drop.kind === 'blocked' ? 5 : drop.legalExit === 2 ? 2 : drop.legalExit === 3 ? 3 : 1;
        break;
      }
      if (drop.kind === 'blocked' && STOP_STATUS.has(drop.status)) { result.stopped = { url, reason: `HTTP ${drop.status}: Ziel drosselt, keine weiteren Seiten` }; break; }
      save();
      continue;
    }
    if (!hasData) {
      result.skipped.push({ url, kind: 'error', reason: `technischer Fehler: ${pageRec.errors[0]?.error ?? 'unbekannt'}` });
      if (isStart) { result.aborted = { url, reason: 'Startseite technisch gescheitert, siehe ergebnis/capture_errors.json' }; exitCode = 1; break; }
      save();
      continue;
    }
    result.pages.push(pageRec);
    if (pageRec.blockedDark && STOP_STATUS.has(pageRec.blockedDark.status)) { result.stopped = { url, reason: `HTTP ${pageRec.blockedDark.status}: Ziel drosselt, keine weiteren Seiten` }; break; }
    save();
    const n = result.pages.length, sec = (Date.now() - t0) / 1000;
    const rest = Math.max(0, Math.min(maxCaptured - n, queue.length - idx - 1));
    console.error(`erfasst ${n}/${maxCaptured}: ${url} (${pageRec.images?.length ?? 0} Bilder, ${pageRec.headings?.length ?? 0} Ueberschriften, Consent ${pageRec.consent?.state ?? '-'}) nach ${Math.round(sec)} s, Rest ca. ${Math.round((sec / n) * rest)} s`);
  }
} finally {
  await browser.close().catch(() => {});
}
if (exitCode === 0 && !result.pages.length) exitCode = 1;
save();
console.error(`fertig: ${result.pages.length} Seiten, ${result.skipped.length} uebersprungen, ${result.blocked.length} blockiert, ${errors.length} Fehler -> ${CAPTURE_JSON} (Exit ${exitCode})`);
process.exit(exitCode);
