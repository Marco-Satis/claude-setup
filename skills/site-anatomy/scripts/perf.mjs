#!/usr/bin/env node
// site-anatomy, Phase 2c: Ladezeit und Technik-Qualitaet per Lighthouse (Labordaten, keine Felddaten).
// Aufruf: node perf.mjs <arbeitsordner> [--pages N]   (Default: nur Startseite; N weitere erfasste Seiten)
// Liest kopien/capture.json (nur dort erfasste, nicht blockierte Seiten -> Rechts-Check ist schon gelaufen).
// Schreibt ergebnis/perf.json (Kennzahlen) und kopien/lighthouse/<seite>_<formfaktor>.json (voller Bericht,
// enthaelt Screenshots der fremden Seite -> kopien/). Exit 0 ok, 3 WD/Aufruf ungueltig, 4 Werkzeug fehlt,
// 5 Zielseite blockt (Teilergebnis geschrieben).
import { mkdirSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { join, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import { TOOL_ROOT, UA_TOKEN, loadTool, parseArgs, requireWorkdir, sleep, toolVersion } from './_tool.mjs';

const PAGE_GAP_MIN_MS = 1000; // wie capture/measure: hoechstens 1 Seitenaufruf/s, Crawl-delay kann mehr verlangen
const MAX_EXTRA_PAGES = 4; // je Seite 2 Laeufe a 20-60 s; mehr Seiten sagen ueber Ladezeit selten Neues
const FORM_FACTORS = ['mobile', 'desktop']; // Lighthouse-Standard: Handy gedrosselt (Slow 4G), Desktop ungedrosselt
const CATEGORIES = ['performance', 'accessibility', 'best-practices', 'seo'];
const METRICS = ['first-contentful-paint', 'largest-contentful-paint', 'total-blocking-time', 'cumulative-layout-shift', 'speed-index', 'interactive', 'max-potential-fid', 'server-response-time', 'total-byte-weight', 'dom-size', 'bootup-time', 'mainthread-work-breakdown'];
const BLOCKING_STATUS = new Set([401, 403, 429, 503]);

const args = parseArgs(process.argv.slice(2), { pages: 0 });
const fail = (msg) => { console.error(msg); process.exit(3); };
if (!args._[0]) fail('Aufruf: node perf.mjs <arbeitsordner> [--pages N]');
const WD = requireWorkdir(args._[0]);
const KOPIEN = join(WD, 'kopien'), ERGEBNIS = join(WD, 'ergebnis'), LH_DIR = join(KOPIEN, 'lighthouse');
const readJson = (f) => { try { return JSON.parse(readFileSync(f, 'utf8')); } catch { return null; } };
const capture = readJson(join(KOPIEN, 'capture.json'));
if (!capture || !Array.isArray(capture.pages)) fail(`kopien/capture.json fehlt oder ist ungueltig in ${WD}`);
mkdirSync(ERGEBNIS, { recursive: true });
mkdirSync(LH_DIR, { recursive: true });
for (const d of [ERGEBNIS, LH_DIR]) if (!realpathSync(d).startsWith(WD + sep)) fail(`${d} zeigt aus dem Arbeitsordner heraus`);

const legal = readJson(join(ERGEBNIS, 'legal.json'));
const crawlDelay = Math.max(0, ...[].concat(legal || []).map((l) => Number(l?.crawl_delay) || 0));
const GAP_MS = Math.max(PAGE_GAP_MIN_MS, crawlDelay * 1000);

// Nur Seiten, die capture erfolgreich erfasst hat (nicht blocked/skipped, Status < 400)
const pages = capture.pages.filter((p) => !(p.status >= 400) && !p.blocked)
  .slice(0, 1 + Math.min(Math.max(0, Number(args.pages) || 0), MAX_EXTRA_PAGES))
  .map((p, i) => ({ idx: i, url: p.finalUrl || p.url }));
if (!pages.length) fail('keine erfasste Seite in capture.json');

const { default: lighthouse } = await loadTool('lighthouse');
const imp = (rel) => import(pathToFileURL(join(TOOL_ROOT, 'node_modules', rel)).href);
const { default: desktopConfig } = await imp('lighthouse/core/config/desktop-config.js');
const { userAgents } = await imp('lighthouse/core/config/constants.js');
const chromeLauncher = await loadTool('chrome-launcher');
const { chromium } = await loadTool('playwright');

const round = (x, n = 0) => (typeof x === 'number' ? Math.round(x * 10 ** n) / 10 ** n : null);
const results = [], errors = [];
let blocked = null;

// Lighthouse braucht einen eigenen Chrome mit Debug-Port; wir nehmen das Chromium der Playwright-Kette.
const chrome = await chromeLauncher.launch({
  chromePath: chromium.executablePath(),
  chromeFlags: ['--headless=new', '--no-sandbox', '--disable-gpu', '--lang=de-DE'],
  logLevel: 'silent',
});

function summarize(lhr) {
  const a = lhr.audits;
  const metric = (id) => a[id] && { value: round(a[id].numericValue, id === 'cumulative-layout-shift' ? 3 : 0), unit: a[id].numericUnit, display: a[id].displayValue ?? null, score: a[id].score };
  const byType = {};
  for (const r of a['network-requests']?.details?.items || []) {
    const t = r.resourceType || 'Other';
    byType[t] ??= { requests: 0, bytes: 0 };
    byType[t].requests++; byType[t].bytes += r.transferSize || 0;
  }
  // Insights/Diagnosen, die Punkte kosten: Titel + Kurzwert, ohne Detailtabellen (die enthalten fremde URLs/Texte)
  const issues = Object.values(a)
    .filter((x) => typeof x.score === 'number' && x.score < 0.9 && x.scoreDisplayMode !== 'informative' && !METRICS.includes(x.id))
    .map((x) => ({ id: x.id, title: x.title, display: x.displayValue ?? null, score: x.score }))
    .sort((p, q) => p.score - q.score).slice(0, 25);
  // Lighthouse 13: LCP-Element als Eintrag type 'node' in lcp-breakdown-insight (aeltere Versionen: largest-contentful-paint-element)
  const lcpItems = [...(a['lcp-breakdown-insight']?.details?.items || []), ...(a['largest-contentful-paint-element']?.details?.items || [])];
  const lcpEl = lcpItems.find((i) => i?.type === 'node') ?? lcpItems.flatMap((i) => i?.items || []).find((i) => i?.node)?.node;
  return {
    scores: Object.fromEntries(Object.entries(lhr.categories).map(([k, v]) => [k, round(v.score * 100)])),
    metrics: Object.fromEntries(METRICS.map((id) => [id, metric(id)]).filter(([, v]) => v)),
    // nur Selektor und Groesse: nodeLabel/snippet enthalten fremden Text und bleiben im vollen Bericht unter kopien/
    lcpElement: lcpEl ? { selector: lcpEl.selector ?? null, rect: lcpEl.boundingRect ? { w: lcpEl.boundingRect.width, h: lcpEl.boundingRect.height, top: lcpEl.boundingRect.top } : null } : null,
    resourceSummary: byType,
    thirdPartyEntities: (a['third-parties-insight'] || a['third-party-summary'])?.details?.items?.slice(0, 15).map((e) => ({ entity: typeof e.entity === 'object' ? e.entity.text : e.entity, transferSize: e.transferSize ?? null, mainThreadTime: round(e.mainThreadTime ?? e.blockingTime) })) ?? null,
    issues,
    warnings: lhr.runWarnings || [],
    lighthouseVersion: lhr.lighthouseVersion,
    fetchTime: lhr.fetchTime,
  };
}

try {
  for (const p of pages) {
    for (const ff of FORM_FACTORS) {
      await sleep(GAP_MS);
      const ua = `${ff === 'desktop' ? userAgents.desktop : userAgents.mobile} ${UA_TOKEN}`;
      const flags = { port: chrome.port, output: 'json', logLevel: 'error', onlyCategories: CATEGORIES, locale: 'de', emulatedUserAgent: ua, enableErrorReporting: false };
      const t0 = Date.now();
      let res = null;
      try {
        res = await lighthouse(p.url, flags, ff === 'desktop' ? desktopConfig : undefined);
      } catch (e) {
        errors.push({ url: p.url, formFactor: ff, error: String(e?.message || e).split('\n')[0] });
        continue;
      }
      const lhr = res?.lhr;
      if (!lhr) { errors.push({ url: p.url, formFactor: ff, error: 'kein Ergebnis' }); continue; }
      const status = lhr.audits['network-requests']?.details?.items?.find((r) => r.url === lhr.finalDisplayedUrl || r.url === p.url)?.statusCode ?? null;
      if (lhr.runtimeError || BLOCKING_STATUS.has(status)) {
        const why = lhr.runtimeError ? `${lhr.runtimeError.code}: ${lhr.runtimeError.message}` : `HTTP ${status}`;
        errors.push({ url: p.url, formFactor: ff, error: why });
        if (BLOCKING_STATUS.has(status) || /ERRORED_DOCUMENT_REQUEST|FAILED_DOCUMENT_REQUEST/.test(lhr.runtimeError?.code || '')) { blocked = { url: p.url, reason: why }; break; }
        continue;
      }
      writeFileSync(join(LH_DIR, `${p.idx}_${ff}.json`), res.report);
      results.push({ url: p.url, page: p.idx, formFactor: ff, seconds: round((Date.now() - t0) / 1000, 1), ...summarize(lhr) });
      console.error(`gemessen ${p.url} ${ff}: Performance ${results.at(-1).scores.performance}, LCP ${results.at(-1).metrics['largest-contentful-paint']?.display}`);
    }
    if (blocked) break;
  }
} finally {
  await chrome.kill();
  const out = {
    note: 'Labordaten (Lighthouse, simulierte Drosselung). Keine Felddaten echter Nutzer (CrUX). Consent-Banner wurde nicht bedient: gemessen wird der Erstbesuch.',
    tools: { lighthouse: toolVersion('lighthouse'), chromium: chromium.executablePath().split(sep).find((s) => /^chromium/.test(s)) ?? null, node: process.version },
    gapMs: GAP_MS, results, errors, ...(blocked && { blocked }),
  };
  writeFileSync(join(ERGEBNIS, 'perf.json'), JSON.stringify(out, null, 1));
}
console.error(`fertig: ${results.length} Laeufe, ${errors.length} Fehler${blocked ? `, ABGEBROCHEN (blockiert: ${blocked.url} ${blocked.reason})` : ''}`);
process.exitCode = blocked ? 5 : 0;
