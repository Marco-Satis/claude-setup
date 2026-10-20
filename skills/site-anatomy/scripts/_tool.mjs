// Gemeinsame Helfer der site-anatomy-Skripte (capture.mjs, measure.mjs).
// Laedt die gepinnte Werkzeugkette aus ~/.local/share/site-anatomy statt aus dem Skill-Ordner.
// Grund: Skills synchen per Syncthing auf beide Maschinen, node_modules sollen das nicht.
import { createRequire } from 'node:module';
import { existsSync, readFileSync, realpathSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, sep } from 'node:path';
import { pathToFileURL } from 'node:url';

export const TOOL_ROOT = process.env.SITE_ANATOMY_HOME || join(homedir(), '.local/share/site-anatomy');
// Arbeitsordner liegen ausserhalb von ~/projects (das synct per Syncthing auf den PC).
// SITE_ANATOMY_WORKROOT nur fuer Tests.
export const WORK_ROOT = process.env.SITE_ANATOMY_WORKROOT || join(homedir(), 'site-anatomy');

export function assertInstalled() {
  if (!existsSync(join(TOOL_ROOT, 'node_modules'))) {
    console.error(`Werkzeugkette fehlt: ${TOOL_ROOT}/node_modules. Installation (install/install.sh) braucht des Nutzers Freigabe.`);
    process.exit(4);
  }
}

const require = createRequire(join(TOOL_ROOT, 'package.json'));

export async function loadTool(name) {
  assertInstalled();
  // ESM-Pakete (designlang, colorthief) brauchen den import-Einstieg, nicht require.resolve auf "main".
  const pkgDir = join(TOOL_ROOT, 'node_modules', name);
  const pkg = require(join(pkgDir, 'package.json'));
  const exp = pkg.exports?.['.'];
  const entry = (typeof exp === 'string' ? exp : exp?.import?.default || exp?.import || exp?.default) || pkg.module || pkg.main || 'index.js';
  return import(pathToFileURL(join(pkgDir, entry)).href);
}

// Paketversion aus der installierten package.json (Steckbrief), null wenn nicht installiert.
export function toolVersion(name) {
  try { return JSON.parse(readFileSync(join(TOOL_ROOT, 'node_modules', name, 'package.json'), 'utf8')).version ?? null; } catch { return null; }
}

// Alle Werkzeuge, die der Bericht im Steckbrief nennt (axe-core = die Regel-Engine hinter @axe-core/playwright).
export const TOOL_PACKAGES = ['playwright', 'designlang', '@axe-core/playwright', 'axe-core', 'colorthief', 'sharp', 'lighthouse'];
export function toolVersions() {
  return { ...Object.fromEntries(TOOL_PACKAGES.map((n) => [n, toolVersion(n)])), node: process.version };
}

// Prueft einen Arbeitsordner (von workdir.py init angelegt): muss existieren, real (Symlinks aufgeloest)
// unter WORK_ROOT liegen und ein gueltiges, nicht abgelaufenes LOESCHDATUM haben.
// Ohne LOESCHDATUM entstuenden Kopien ohne Loeschpflicht. Fehler -> Exit 3.
export function requireWorkdir(dir) {
  const fail = (msg) => { console.error(`Arbeitsordner ungueltig: ${msg}`); process.exit(3); };
  if (!dir || typeof dir !== 'string') fail('kein Pfad angegeben (--out <arbeitsordner>)');
  let root, real;
  try { root = realpathSync(WORK_ROOT); } catch { fail(`${WORK_ROOT} fehlt - erst "workdir.py init <url>" ausfuehren`); }
  try { real = realpathSync(dir); } catch { fail(`${dir} existiert nicht - erst "workdir.py init <url>" ausfuehren`); }
  if (!real.startsWith(root + sep)) fail(`${real} liegt nicht unter ${root}/`);
  if (!statSync(real).isDirectory()) fail(`${real} ist kein Ordner`);
  let del = '';
  try { del = readFileSync(join(real, 'LOESCHDATUM'), 'utf8').trim(); } catch { /* unten gemeldet */ }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(del)) fail(`${real}/LOESCHDATUM fehlt oder ist kein ISO-Datum`);
  const d = new Date(), today = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  if (del < today) fail(`LOESCHDATUM ${del} ist abgelaufen - neuen Arbeitsordner anlegen`);
  return real;
}

// Ehrlicher User-Agent: Standard-UA des gestarteten Browsers plus Werkzeug-Kennung, damit Betreiber
// den Verkehr zuordnen und per robots.txt (Token site-anatomy) steuern koennen.
export const UA_TOKEN = 'site-anatomy/0.1';
export async function honestUserAgent(browser) {
  const ctx = await browser.newContext();
  try {
    const page = await ctx.newPage(); // about:blank, kein Netzverkehr
    return `${await page.evaluate(() => navigator.userAgent)} ${UA_TOKEN}`;
  } finally {
    await ctx.close().catch(() => {});
  }
}

// --- Consent ---------------------------------------------------------------------------------
// Nur Ablehnen-Knoepfe (DE/EN). Die Vorausschau schliesst Zustimmen-Knoepfe aus; geklickt wird nie
// etwas anderes als Ablehnen, auch nicht "Einstellungen" (Ablehnen in zweiter Ebene wird nicht gesucht).
export const CONSENT_REJECT = /^(?!.*(alle\s+(cookies\s+)?(akzeptieren|annehmen|erlauben|zulassen)|accept\s+all|allow\s+all))(?:.*\b(ablehnen|verweigern|reject|decline|deny|refuse)\b|.*\b(nur|only)\b.*(notwendig|erforderlich|essenziell|essentiell|technisch|necessary|essential|required)|.*\b(necessary|essential|required)\s+(cookies\s+)?only\b|.*\bweiter\s+ohne\b|.*\bcontinue\s+without\b|.*\bnicht\s+(zustimmen|akzeptieren|einverstanden))/i;

// Container gaengiger Consent-Manager: Inhalte darin sind keine Gestaltung der Seite (CTAs, Texte).
// Liste aus designlang src/widgets.js (Abschnitt Cookie/Consent; per exports-Feld nicht importierbar),
// ergaenzt um in DE verbreitete CMPs (Borlabs, consentmanager, Didomi, Sourcepoint, Quantcast, Klaro).
export const CONSENT_SELECTORS = [
  '#CybotCookiebotDialog', '#onetrust-banner-sdk', '#onetrust-consent-sdk', '#onetrust-pc-sdk',
  '.termly-banner-top', '.termly-styles-banner', '#cookiebanner', '#cookie-banner', '#cookie-notice',
  '.cc-window', '.cc-banner', '#usercentrics-root', '#iubenda-cs-banner', '[aria-label*="cookie" i][role="dialog"]',
  '#BorlabsCookieBox', '#cmpbox', '#cmpwrapper', '#didomi-host', '[id^="sp_message_container"]', '.qc-cmp2-container', '.klaro',
];

const CONSENT_POLL_MS = 500; // Suchtakt; CMPs blenden meist animiert ein, feiner bringt nichts
const CONSENT_EFFECT_MS = 3000; // so lange darf das Ausblenden nach dem Klick dauern (Animation)
const CONSENT_MAX_CLICKS = 6; // Banner in Seite und iframe plus je eine Rueckfrage-Ebene; mehr waere eine Schleife
const CONSENT_WORDS = /cookie|datenschutz|einwilligung|consent|tracking|privacy/i; // Wortschatz eines Banners ohne bekannten CMP-Container
// Ohne Entscheidungsknopf ist eine fixierte Leiste mit "Datenschutz"/"Sendungstracking" nur Navigation (Header/Footer), kein Banner.
const CONSENT_BUTTON = /akzept|zustimm|einverstanden|ablehn|einstellung|verstanden|erlauben|accept|agree|reject|decline|allow|^ok$/i;
const CONSENT_DIALOG = '[role=dialog],[role=alertdialog],[aria-modal=true],dialog[open]';
const BANNER_TEXT_MAX = 3000; // erste Banner-Ebene ist kurz; laengere fixierte Flaechen sind App-Huellen mit Footer-Links
const BANNER_MIN_AREA = 8000; // px² im Sichtbereich; schwebende "Cookie-Einstellungen"-Knoepfe nach der Wahl liegen bei ~64x64
const BANNER_EXCERPT = 80; // bannerText: nur so viel, dass der Nutzer den Banner erkennt

// Laeuft im Frame: sucht einen sichtbaren Consent-Banner, zuerst bekannte CMP-Container, dann Dialoge und
// fixierte Elemente mit Consent-Wortschatz, jeweils auch in offenen Shadow Roots. whole = der Frame steckt in
// einem fixierten Element/Dialog der Elternseite (CMP im iframe): dann zaehlt sein ganzer Text.
function probeConsentBanner({ sels, words, button, dialog, maxText, minArea, whole }) {
  const WORDS = new RegExp(words, 'i');
  const BUTTON = new RegExp(button, 'i');
  const SKIP = new Set(['STYLE', 'SCRIPT', 'TEMPLATE', 'NOSCRIPT']);
  const area = (e) => { // sichtbare Flaeche im Viewport, 0 bei display/visibility/opacity-Versteck
    const r = e.getBoundingClientRect();
    const w = Math.min(r.right, innerWidth) - Math.max(r.left, 0), h = Math.min(r.bottom, innerHeight) - Math.max(r.top, 0);
    return w > 0 && h > 0 && (e.checkVisibility?.({ opacityProperty: true, visibilityProperty: true }) ?? true) ? w * h : 0;
  };
  // Shadow-Hosts haben oft Hoehe 0 (Inhalt fixiert): dann entscheidet ein ausreichend grosser Nachfahre.
  const shown = (e) => {
    for (const todo = [e]; todo.length;) {
      const n = todo.pop();
      if (area(n) >= minArea) return true;
      for (const c of [...n.children, ...(n.shadowRoot?.children ?? [])]) if (!SKIP.has(c.tagName)) todo.push(c);
    }
    return false;
  };
  // innerText laesst Shadow-Inhalte aus: offene Shadow Roots im Unterbaum einzeln anhaengen.
  const text = (e) => {
    let s = e.innerText || '';
    for (const h of [e, ...e.querySelectorAll('*')]) if (h.shadowRoot) for (const c of h.shadowRoot.children) if (!SKIP.has(c.tagName)) s += ` ${text(c)}`;
    return s.replace(/\s+/g, ' ').trim();
  };
  // Ein Banner verlangt eine Entscheidung: mindestens ein Knopf mit Zustimmen/Ablehnen/Einstellungen-Text (auch im Shadow DOM).
  const hasDecision = (e) => {
    const q = 'button,[role=button],input[type=button],input[type=submit],a';
    const pool = [e, ...e.querySelectorAll('*')].flatMap((h) => [...(h === e ? h.querySelectorAll(q) : []), ...(h.shadowRoot ? h.shadowRoot.querySelectorAll(q) : [])]);
    return pool.some((b) => BUTTON.test(((b.innerText || b.value || b.getAttribute('aria-label') || '') + '').trim()));
  };
  const roots = [document];
  for (let i = 0; i < roots.length; i++) for (const e of roots[i].querySelectorAll('*')) if (e.shadowRoot) roots.push(e.shadowRoot);
  for (const r of roots) {
    for (const s of sels) {
      let list = [];
      try { list = r.querySelectorAll(s); } catch { continue; }
      for (const e of list) if (shown(e)) return { selector: s, text: text(e) };
    }
  }
  for (const r of roots) {
    for (const e of r.querySelectorAll('*')) {
      if (SKIP.has(e.tagName) || !(e.matches(dialog) || getComputedStyle(e).position === 'fixed')) continue;
      const t = text(e);
      if (t.length <= maxText && WORDS.test(t) && hasDecision(e) && shown(e)) return { selector: null, text: t };
    }
  }
  if (whole && document.body) {
    const t = text(document.body);
    if (t.length <= maxText && WORDS.test(t) && hasDecision(document.body)) return { selector: null, text: t };
  }
  return null;
}

// Laeuft in der Elternseite auf dem iframe-Element: sichtbare Flaeche und ob es in einem fixierten Element/Dialog steckt.
function frameOwnerState(el, dialog) {
  const r = el.getBoundingClientRect();
  const w = Math.min(r.right, innerWidth) - Math.max(r.left, 0), h = Math.min(r.bottom, innerHeight) - Math.max(r.top, 0);
  const area = w > 0 && h > 0 && (el.checkVisibility?.({ opacityProperty: true, visibilityProperty: true }) ?? true) ? w * h : 0;
  let floating = false;
  for (let n = el; n && !floating; n = n.parentElement || n.getRootNode().host) floating = n.matches(dialog) || getComputedStyle(n).position === 'fixed';
  return { area, floating };
}

const scopeOf = (page, f) => (f === page.mainFrame() ? 'page' : f.url());

// Sichtbarer Consent-Banner in Seite oder iframe? null = keiner. Scheitert die Pruefung der Hauptseite,
// wird nicht "kein Banner" behauptet (bannerCheck statt null), damit der Bericht den Vorbehalt behaelt.
async function findConsentBanner(page) {
  let mainError = null;
  for (const f of page.frames()) {
    if (f.isDetached()) continue;
    const isMain = f === page.mainFrame();
    let whole = false;
    if (!isMain) {
      const owner = await f.frameElement().catch(() => null);
      const st = owner ? await owner.evaluate(frameOwnerState, CONSENT_DIALOG).catch(() => null) : null;
      await owner?.dispose().catch(() => {});
      if (!st || st.area < BANNER_MIN_AREA) continue; // unsichtbare/winzige iframes (Tracking, reCAPTCHA-Plakette)
      whole = st.floating;
    }
    let hit = null;
    try {
      hit = await f.evaluate(probeConsentBanner, { sels: CONSENT_SELECTORS, words: CONSENT_WORDS.source, button: CONSENT_BUTTON.source, dialog: CONSENT_DIALOG, maxText: BANNER_TEXT_MAX, minArea: BANNER_MIN_AREA, whole });
    } catch (e) {
      if (isMain) mainError = String(e?.message || e).split('\n')[0].slice(0, 200);
      continue;
    }
    if (hit) return { bannerScope: scopeOf(page, f), ...(hit.selector && { bannerSelector: hit.selector }), ...(hit.text && { bannerText: hit.text.slice(0, BANNER_EXCERPT) }) };
  }
  return mainError ? { bannerCheck: `fehlgeschlagen: ${mainError}` } : null;
}

// Beobachtet bis waitMs die Seite (getByRole durchdringt offene Shadow DOMs) und alle iframes, klickt
// jeden sichtbaren Ablehnen-Knopf und prueft die Wirkung (Knopf verschwunden). Bis zum Fensterende,
// nicht nur bis zum ersten Treffer: ein zweiter Banner kommt oft spaeter (z. B. iframe vor Seite).
// Rueckgabe-state: rejected | reject_failed | no_reject_button_found (Banner sichtbar, mit bannerSelector/
// bannerText bzw. bannerCheck) | no_banner (kein Ablehnen-Knopf und kein sichtbarer Banner).
export async function rejectConsent(page, { waitMs = 8000 } = {}) {
  const t0 = Date.now(), deadline = t0 + waitMs;
  const scopeName = (f) => scopeOf(page, f);
  const labelOf = async (btn) => ((await btn.textContent().catch(() => '')) || '').replace(/\s+/g, ' ').trim();
  const hits = [], failed = new Set(); // failed: Knoepfe, die schon einmal nicht gewirkt haben
  const visibleButtons = async () => {
    const found = [];
    for (const f of page.frames()) {
      if (f.isDetached()) continue;
      const btn = f.getByRole('button', { name: CONSENT_REJECT }).filter({ visible: true }).first();
      if (!(await btn.count().catch(() => 0))) continue;
      const label = await labelOf(btn);
      found.push({ f, btn, label, key: `${scopeName(f)}\n${label}` });
    }
    return found;
  };
  for (;;) {
    for (const { f, btn, label, key } of await visibleButtons()) {
      if (failed.has(key) || hits.length >= CONSENT_MAX_CLICKS) continue;
      const clicked = await btn.click({ timeout: 5000 }).then(() => true, () => false);
      if (clicked) await btn.waitFor({ state: 'hidden', timeout: CONSENT_EFFECT_MS }).catch(() => {});
      const gone = !(await btn.isVisible().catch(() => false));
      hits.push({ button: label, scope: scopeName(f), clicked, gone });
      if (!(clicked && gone)) failed.add(key);
    }
    if (Date.now() >= deadline || hits.length >= CONSENT_MAX_CLICKS) break;
    await sleep(CONSENT_POLL_MS);
  }
  const waitedMs = Date.now() - t0;
  if (!hits.length) {
    const banner = await findConsentBanner(page);
    return banner ? { state: 'no_reject_button_found', waitedMs, hits, ...banner } : { state: 'no_banner', waitedMs, hits };
  }
  const stillOpen = (await visibleButtons()).length > 0;
  const ok = hits.every((h) => h.clicked && h.gone) && !stillOpen;
  return { state: ok ? 'rejected' : 'reject_failed', button: hits[0].button, waitedMs, hits, stillOpen };
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// flags: Namen von Schaltern ohne Wert (sonst wuerde "--schalter <url>" die URL als Wert schlucken).
export function parseArgs(argv, defaults = {}, flags = []) {
  const out = { _: [], ...defaults };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (flags.includes(key) || next === undefined || next.startsWith('--')) out[key] = true;
      else { out[key] = next; i++; }
    } else out._.push(a);
  }
  return out;
}
