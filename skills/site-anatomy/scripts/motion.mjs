// motion.mjs - site-anatomy Phase 2d "Bewegung" (G247 B9, 2026-11-18).
// Misst die Bewegung einer fremden Seite mit ~/.claude/scripts/motion_probe.mjs: Startseite plus hoechstens
// 2 Unterseiten, nur Scrollen und Hover (kein Klick, keine Eingabe). Laeuft NACH capture.mjs und besucht nur
// URLs, die capture.mjs nach bestandenem legal_check.py erfasst hat (kopien/capture.json -> pages[]); der
// TDM-Vorbehalt in der Browser-Antwort wird hier erneut geprueft. Abstand je Abruf wie capture.mjs
// (meta.minGapMs inkl. Crawl-delay), ehrlicher User-Agent, Consent nur ablehnen.
// Schreibt:
//   kopien/motion/<n>_<gruppe>.png   Schrittboegen (0/20/40/50/60/80/100 %), hoechstens 6 - Kopien mit Loeschpflicht
//   kopien/motion/dump_<n>.json      Rohmessung je Seite (Selektoren, Keyframes)
//   ergebnis/motion.json             Messwerte je Rolle (Dauer, Kurve, Stagger, Schleifen, Flags, reduzierte Bewegung)
// Uebernommen werden nur Verhaeltnisse und Messwerte, nie Code, Lottie-Dateien oder Assets.
// Aufruf: node motion.mjs --out <arbeitsordner> [--pages 3] [--width 1280]
// Exit: 0 ok · 1 keine Seite messbar · 3 Aufruf/Arbeitsordner · 4 Werkzeugkette fehlt
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { honestUserAgent, loadTool, parseArgs, rejectConsent, requireWorkdir, sleep, toolVersion } from './_tool.mjs';

const MAX_PAGES = 3; // Startseite + 2 Unterseiten (Plan G247 B9)
const MAX_SHEETS = 6;
const HOVER_MAX = 6;
const NAV_TIMEOUT = 45000;
const SHEET_MAX_W = 1568;
const MOTION_PROBE = join(homedir(), '.claude/scripts/motion_probe.mjs');

const args = parseArgs(process.argv.slice(2), { pages: MAX_PAGES, width: 1280 });
if (!args.out || args.out === true) {
  console.error('Aufruf: node motion.mjs --out <arbeitsordner> [--pages 3] [--width 1280]  (nach capture.mjs)');
  process.exit(3);
}
const WD = requireWorkdir(args.out);
const KOPIEN = join(WD, 'kopien'), ERGEBNIS = join(WD, 'ergebnis'), MOTION_DIR = join(KOPIEN, 'motion');
const CAPTURE_JSON = join(KOPIEN, 'capture.json');
if (!existsSync(CAPTURE_JSON)) { console.error('kopien/capture.json fehlt: erst capture.mjs laufen lassen (Rechts-Check je URL).'); process.exit(3); }
const capture = JSON.parse(readFileSync(CAPTURE_JSON, 'utf8'));
const urls = (capture.pages ?? []).map((p) => p.url).filter(Boolean).slice(0, Math.max(1, Math.min(MAX_PAGES, Number(args.pages) || MAX_PAGES)));
if (!urls.length) { console.error('capture.json enthaelt keine erfasste Seite: nichts zu messen.'); process.exit(1); }
const width = Math.max(320, Math.min(1920, Number(args.width) || 1280));
const minGapMs = Math.max(1000, Number(capture.meta?.minGapMs) || 1000);
mkdirSync(MOTION_DIR, { recursive: true });

let mp;
try { mp = await import(pathToFileURL(MOTION_PROBE).href); } catch (e) { console.error(`Werkzeugkette fehlt: ${MOTION_PROBE} (${e.message})`); process.exit(4); }
const { chromium } = await loadTool('playwright');
const sharp = (await loadTool('sharp')).default;

let lastReq = 0;
async function politeGoto(page, url) {
  const w = lastReq + minGapMs - Date.now();
  if (w > 0) await sleep(w);
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForLoadState('load', { timeout: 30000 }).catch(() => {});
    await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
    return resp;
  } finally { lastReq = Date.now(); }
}

// Wie capture.mjs browserReservation: TDM-Vorbehalt in der tatsaechlichen Antwort -> Seite nicht messen.
async function reservation(page, resp) {
  const h = resp?.headers() || {};
  if ((h['tdm-reservation'] || '').trim() === '1') return 'Header tdm-reservation: 1';
  if (/\bno(image)?ai\b/i.test(h['x-robots-tag'] || '')) return `Header x-robots-tag: ${h['x-robots-tag']}`;
  const metas = await page.evaluate(() => [...document.querySelectorAll('meta[name]')].map((m) => [m.name.toLowerCase(), (m.content || '').toLowerCase()])).catch(() => []);
  for (const [n, c] of metas) {
    if (n === 'tdm-reservation' && c.trim() === '1') return 'Meta tdm-reservation: 1';
    if ((n === 'robots' || n === 'googlebot') && /\bno(image)?ai\b/.test(c)) return `Meta ${n}: ${c}`;
  }
  return null;
}

// Hover auf sichtbare Bedienelemente (Kopf, Hauptbereich), damit Rueckmelde-Transitions im Dump landen.
async function hoverControls(page) {
  const loc = page.locator('header a, header button, nav a, main a, main button, [role="button"]');
  const n = Math.min(await loc.count().catch(() => 0), 40);
  let done = 0;
  for (let i = 0; i < n && done < HOVER_MAX; i++) {
    const el = loc.nth(i);
    if (!(await el.isVisible().catch(() => false))) continue;
    if (await el.hover({ timeout: 1500 }).then(() => true, () => false)) { done++; await sleep(350); }
  }
  await page.mouse.move(1, 1).catch(() => {});
  return done;
}

const stats = (xs) => {
  const v = xs.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  if (!v.length) return null;
  return { n: v.length, min: v[0], median: v[Math.floor(v.length / 2)], max: v[v.length - 1] };
};
const curves = (es) => es.reduce((m, e) => { const c = mp.curveInfo(e).cls; m[c] = (m[c] ?? 0) + 1; return m; }, {});

function roles(dump) {
  const A = (dump.animations ?? []).filter((a) => Number(a.duration) > 0);
  const items = (dump.transitions ?? []).flatMap((t) => t.items.map((x) => ({ ...x, interactive: t.interactive })));
  const loops = A.filter((a) => a.total === 'infinite' || a.total > 5000);
  const entries = A.filter((a) => a.entry && !loops.includes(a));
  const other = A.filter((a) => !a.entry && !loops.includes(a));
  const feedback = items.filter((x) => x.interactive && x.duration > 0);
  const state = items.filter((x) => !x.interactive && x.duration > 0);
  // Stagger wie motion_probe: je Geschwistergruppe (gleiche Animation, gleiches Elternelement), groesste Spanne.
  const groups = entries.reduce((m, a) => { const k = `${a.key}|${a.parentId}`; return m.set(k, [...(m.get(k) ?? []), Number(a.delay) || 0]); }, new Map());
  const spreads = [...groups.values()].filter((d) => d.length > 1).map((d) => Math.max(...d) - Math.min(...d));
  const sig = [...entries, ...other].sort((a, b) => Number(b.duration) - Number(a.duration))[0];
  return {
    eintritt: { dauer: stats(entries.map((a) => Number(a.duration))), kurven: curves(entries.map((a) => a.easing)) },
    rueckmeldung: { dauer: stats(feedback.map((x) => x.duration)), kurven: curves(feedback.map((x) => x.easing)), properties: [...new Set(feedback.map((x) => x.property))].slice(0, 8) },
    zustand: { dauer: stats(state.map((x) => x.duration)), kurven: curves(state.map((x) => x.easing)) },
    sonstige_animation: { dauer: stats(other.map((a) => Number(a.duration))), kurven: curves(other.map((a) => a.easing)) },
    stagger_ms: spreads.length ? Math.max(...spreads) : 0,
    schleifen: loops.length,
    signatur_kandidat: sig ? { ziel: sig.target, art: sig.kind, name: sig.name, dauer: Number(sig.duration), kurve: mp.curveInfo(sig.easing).norm } : null,
    js: dump.js ? { urteil: dump.js.verdict, bibliotheken: dump.js.libs, nicht_erfasst: dump.js.notCaptured ?? [],
      skripte: (dump.js.scripts ?? []).slice(0, 60) } : null, // Eingang fuer leanrea (nur diese Bundles durchsuchen; motion_probe liefert hoechstens 60)
  };
}

async function sheet(group, file) {
  const fr = group.frames;
  const meta = await sharp(fr[0].buf).metadata();
  const gap = 8, label = 22, n = fr.length;
  const scale = Math.min(1, (SHEET_MAX_W - (n + 1) * gap) / (n * meta.width));
  const w = Math.max(1, Math.round(meta.width * scale)), h = Math.max(1, Math.round(meta.height * scale));
  const tiles = await Promise.all(fr.map((f) => sharp(f.buf).resize(w, h).png().toBuffer()));
  const W = n * w + (n + 1) * gap, H = h + label + 2 * gap;
  const esc = (s) => String(s).replace(/[<&>]/g, (c) => ({ '<': '&lt;', '&': '&amp;', '>': '&gt;' }[c]));
  const svg = `<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">${fr.map((f, i) =>
    `<text x="${gap + i * (w + gap)}" y="${gap + 15}" font-family="sans-serif" font-size="13" fill="#222">${esc(`${f.pct} % · ${Math.round(f.tMs ?? 0)} ms`)}</text>`).join('')}</svg>`;
  await sharp({ create: { width: W, height: H, channels: 3, background: '#f4f4f4' } })
    .composite([{ input: Buffer.from(svg), top: 0, left: 0 }, ...tiles.map((t, i) => ({ input: t, top: gap + label, left: gap + i * (w + gap) }))])
    .png().toFile(file);
}

const out = { version: 1, motion_probe: mp.MOTION_PROBE_VERSION, gemessen: new Date().toISOString(), breite: width,
  playwright: toolVersion('playwright'), seiten: [], uebersprungen: [], boegen: [] };
const browser = await chromium.launch({ headless: true });
let sheets = 0;
try {
  const userAgent = await honestUserAgent(browser);
  const base = { locale: 'de-DE', timezoneId: 'Europe/Berlin', viewport: { width, height: 900 }, userAgent };
  for (const [i, url] of urls.entries()) {
    const rec = { url };
    let ctx = null, rctx = null;
    const consentState = (c) => c?.state ?? 'pruefung_fehlgeschlagen';
    try {
      ctx = await browser.newContext({ ...base, reducedMotion: 'no-preference' });
      await mp.installMotionProbe(ctx);
      const page = await ctx.newPage();
      const resp = await politeGoto(page, url);
      const res = await reservation(page, resp);
      if (res) { out.uebersprungen.push({ url, grund: `Vorbehalt: ${res}` }); continue; }
      rec.consent = consentState(await rejectConsent(page, { waitMs: i === 0 ? 8000 : 2500 }).catch(() => null));
      if (!['rejected', 'no_banner'].includes(rec.consent)) rec.hinweis_consent = 'Banner evtl. offen: seine Animationen koennen in der Messung stecken';
      rec.hover = await hoverControls(page);
      const { dump, steps } = await mp.probeMotion(page, { scroll: true, steps: sheets < MAX_SHEETS, maxGroups: Math.min(2, MAX_SHEETS - sheets) });
      await ctx.close(); ctx = null;
      // Gegenlauf mit reduzierter Bewegung (ersetzt "Reduced Motion nicht erhoben").
      let reduced = null;
      try {
        rctx = await browser.newContext({ ...base, reducedMotion: 'reduce' });
        await mp.installMotionProbe(rctx);
        const rp = await rctx.newPage();
        const rresp = await politeGoto(rp, url);
        const rres = await reservation(rp, rresp);
        if (rres) throw new Error(`Vorbehalt im zweiten Abruf: ${rres}`);
        rec.consent_reduziert = consentState(await rejectConsent(rp, { waitMs: 2500 }).catch(() => null));
        reduced = (await mp.probeMotion(rp, { scroll: true, steps: false })).dump;
      } catch (e) { rec.reduziert_fehler = String(e.message).split('\n')[0]; }
      finally { if (rctx) await rctx.close().catch(() => {}); rctx = null; }
      const { flags, hints } = mp.motionFlags(dump, reduced);
      writeFileSync(join(MOTION_DIR, `dump_${i + 1}.json`), JSON.stringify({ url, dump, reduced }, null, 1));
      rec.rollen = roles(dump);
      rec.reduzierte_bewegung = reduced ? { animationen: (reduced.animations ?? []).length, vorher: (dump.animations ?? []).length,
        unveraendert: flags.some((f) => f.id === 'rm-unchanged') } : null;
      rec.flags = flags.map((f) => ({ id: f.id, art: f.art, anzahl: f.count, beleg: f.evidence.slice(0, 3) }));
      rec.hinweise = hints;
      for (const [g, grp] of (steps?.groups ?? []).entries()) {
        if (sheets >= MAX_SHEETS) break;
        const file = join(MOTION_DIR, `${i + 1}_${g + 1}.png`);
        await sheet(grp, file);
        sheets++;
        out.boegen.push({ datei: file, url, ziel: grp.target, name: grp.name, kurve: grp.curve, messgroesse: grp.metric, fortschritt: grp.progress });
      }
      out.seiten.push(rec);
    } catch (e) {
      out.uebersprungen.push({ url, grund: `Messfehler: ${String(e.message).split('\n')[0].slice(0, 300)}` });
    } finally {
      if (ctx) await ctx.close().catch(() => {});
    }
  }
} finally {
  await browser.close().catch(() => {});
}
const tmp = join(ERGEBNIS, 'motion.json.tmp');
writeFileSync(tmp, JSON.stringify(out, null, 1));
renameSync(tmp, join(ERGEBNIS, 'motion.json'));
console.log(`motion: ${out.seiten.length} Seite(n) gemessen, ${out.boegen.length} Schrittboegen in ${MOTION_DIR}, ${out.uebersprungen.length} uebersprungen -> ergebnis/motion.json`);
for (const s of out.seiten) console.log(`- ${s.url}: Flags ${s.flags.map((f) => f.id).join(', ') || 'keine'}; Eintritt ${JSON.stringify(s.rollen.eintritt.dauer)}; Rueckmeldung ${JSON.stringify(s.rollen.rueckmeldung.dauer)}`);
for (const u of out.uebersprungen) console.log(`- uebersprungen ${u.url}: ${u.grund}`);
process.exit(out.seiten.length ? 0 : 1);
