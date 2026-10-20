#!/usr/bin/env node
// Markenabstand: CIEDE2000 zwischen eigenen Farben und geschuetzten Markenfarben der Vorlage.
// Aufruf: node brand_distance.mjs --own "#1a73e8,#ff6b00" --brand "#e20074" [--min 20]
// Exit 0 alle Farben weit genug weg, 2 mindestens eine zu nah, 3 ungueltige Eingabe. Ohne Abhaengigkeiten.
// Farben nur als Hex (#rgb, #rgba, #rrggbb, #rrggbbaa); Alpha wird ignoriert, Markenidentitaet ist deckend.
import { realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parseArgs } from './_tool.mjs';

const HEX = /^#?([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$/i;

export const hexToRgb = (h) => {
  const m = HEX.exec(String(h).trim());
  if (!m) throw new Error(`keine Hex-Farbe: ${JSON.stringify(h)}`);
  const s = m[1].length <= 4 ? m[1].split('').map((c) => c + c).join('') : m[1];
  return [0, 2, 4].map((i) => parseInt(s.slice(i, i + 2), 16));
};

function rgbToLab([r, g, b]) {
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const [R, G, B] = [lin(r), lin(g), lin(b)];
  // sRGB D65 -> XYZ, normiert auf Weisspunkt D65
  const X = (R * 0.4124564 + G * 0.3575761 + B * 0.1804375) / 0.95047;
  const Y = R * 0.2126729 + G * 0.7151522 + B * 0.072175;
  const Z = (R * 0.0193339 + G * 0.119192 + B * 0.9503041) / 1.08883;
  const f = (t) => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116);
  return [116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))];
}

// CIEDE2000 nach Sharma, Wu, Dalal (2005).
export function deltaE2000([L1, a1, b1], [L2, a2, b2]) {
  const rad = Math.PI / 180, deg = 180 / Math.PI;
  const C1 = Math.hypot(a1, b1), C2 = Math.hypot(a2, b2);
  const Cb = (C1 + C2) / 2;
  const G = 0.5 * (1 - Math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)));
  const a1p = (1 + G) * a1, a2p = (1 + G) * a2;
  const C1p = Math.hypot(a1p, b1), C2p = Math.hypot(a2p, b2);
  const hp = (b, a) => (b === 0 && a === 0 ? 0 : (Math.atan2(b, a) * deg + 360) % 360);
  const h1p = hp(b1, a1p), h2p = hp(b2, a2p);
  const dLp = L2 - L1, dCp = C2p - C1p;
  let dhp = 0;
  if (C1p * C2p !== 0) {
    dhp = h2p - h1p;
    if (dhp > 180) dhp -= 360; else if (dhp < -180) dhp += 360;
  }
  const dHp = 2 * Math.sqrt(C1p * C2p) * Math.sin((dhp / 2) * rad);
  const Lbp = (L1 + L2) / 2, Cbp = (C1p + C2p) / 2;
  let hbp = h1p + h2p;
  if (C1p * C2p !== 0) {
    if (Math.abs(h1p - h2p) > 180) hbp += h1p + h2p < 360 ? 360 : -360;
    hbp /= 2;
  }
  const T = 1 - 0.17 * Math.cos((hbp - 30) * rad) + 0.24 * Math.cos(2 * hbp * rad) + 0.32 * Math.cos((3 * hbp + 6) * rad) - 0.2 * Math.cos((4 * hbp - 63) * rad);
  const dTheta = 30 * Math.exp(-(((hbp - 275) / 25) ** 2));
  const Rc = 2 * Math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7));
  const Sl = 1 + (0.015 * (Lbp - 50) ** 2) / Math.sqrt(20 + (Lbp - 50) ** 2);
  const Sc = 1 + 0.045 * Cbp, Sh = 1 + 0.015 * Cbp * T;
  const Rt = -Math.sin(2 * dTheta * rad) * Rc;
  return Math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh));
}

export const hexDeltaE = (h1, h2) => deltaE2000(rgbToLab(hexToRgb(h1)), rgbToLab(hexToRgb(h2)));

// Hauptmodul ueber echte Dateipfade erkennen: ein Rohtext-Vergleich mit argv[1] scheitert an
// Leerzeichen (%20), Symlinks und Windows-Pfaden und endete dann still mit Exit 0.
const isMain = (() => {
  try {
    return Boolean(process.argv[1]) && realpathSync(fileURLToPath(import.meta.url)) === realpathSync(process.argv[1]);
  } catch {
    return false;
  }
})();

if (isMain) {
  const usage = () => {
    console.error('Aufruf: node brand_distance.mjs --own "#aaa,#bbb" --brand "#e20074" [--min 20]');
    process.exit(3);
  };
  const args = parseArgs(process.argv.slice(2), { min: 20 });
  const list = (v) => (typeof v === 'string' ? v.split(',').map((s) => s.trim()).filter(Boolean) : []);
  const own = list(args.own), brand = list(args.brand);
  const min = typeof args.min === 'boolean' ? NaN : Number(args.min); // "--min" ohne Wert ist kein Wert
  if (!own.length || !brand.length || args._.length) usage();
  if (!Number.isFinite(min) || min < 0) {
    console.error(`--min muss eine Zahl >= 0 sein: ${JSON.stringify(args.min)}`);
    process.exit(3);
  }
  const bad = [...own, ...brand].filter((c) => !HEX.test(c));
  if (bad.length) {
    console.error(`keine Hex-Farbe: ${bad.map((c) => JSON.stringify(c)).join(', ')}`);
    process.exit(3);
  }
  const rows = [];
  for (const o of own) for (const b of brand) {
    const d = hexDeltaE(o, b);
    rows.push({ own: o, brand: b, deltaE: Math.round(d * 10) / 10, ok: d >= min });
  }
  console.log(JSON.stringify({ min, ok: rows.every((r) => r.ok), rows }, null, 1));
  process.exit(rows.every((r) => r.ok) ? 0 : 2);
}
