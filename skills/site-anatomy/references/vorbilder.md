# Vorbilder für eigene Oberflächen (G247 B12)

> Stand 18.11.2026. Gemessen mit `site-anatomy` 0.3.0 (designlang 13.3.2), nur Startseite, `--pages 0`.
> Prinzipien und Prüfliste: `~/.claude/templates/profi_kanon.md`. Messwerte bleiben in `<WD>/ergebnis/`, fremde
> Kopien in `<WD>/kopien/` werden zum Löschdatum (18.12.2026) gelöscht. WD-Wurzel: `~/site-anatomy/`.
> Rechts-Check (`legal_check.py`) aller gemessenen Seiten am 18.11.2026: **frei** (kein robots-/TDM-Vorbehalt).
> Ausnahme `blitz.gg`: **Vorbehalt** (von einer anderen Session geprüft), nicht gemessen.
>
> Wahl: Claude schlägt vor, der Nutzer streicht (Plan G247 B12). Kernwerte: Fläche = häufigste Hintergrundfarbe mit
> Anteil an der CSS-Hintergrundfläche; Akzent mit Anteil; Schrift; Hero px/Gewicht ÷ Fließtext px; Radius dominant;
> Bewegung häufigste Dauer/Kurve.

## Werkzeug / Dashboard

| Seite | WD | Schema | Kernwerte | Taugt für |
|---|---|---|---|---|
| plausible.io (Live-Dashboard) | `plausible.io_2026-11-18` | hell | Weiß 51 % + `#f4f4f4` 27 %; 3 Signalfarben < 0,3 %; System-Sans; größte Zahl 36/800 ÷ 14; Radius 6; 100–300 ms `(0.4,0,0.2,1)` | Dichte, Kennzahl + Verlauf, Tabellen |
| linear.app | `linear.app_2026-11-18` (gemessen von anderer Session) | dunkel | `#08090a` 97 %; Akzent `#5e6ad2` 0,1 %; Inter Variable + Berkeley Mono; 64/510/−2,2 % ÷ 14; Tokens 4–32 + Pill; 160 ms easeOutQuad | Flächenstufen, Textstufen, Tokens, Zurückhaltung |
| vercel.com | `vercel.com_2026-11-18` | hell + dunkel (System) | Weiß 97 %; Akzent `#156cff` 0,1 %; Geist + Geist Mono; 64/400/−6 % ÷ 14; Radien 4–20; 150–200 ms ease-out | Rahmen-als-Schatten, Graustufen-Rollen, Typo |
| raycast.com | `www.raycast.com_2026-11-18` | dunkel | Schwarz 86 %; Akzent `#ff6363` 0,1 %; Inter + Geist Mono; 112/400 ÷ 13 (Ausreißer), sonst 64/600; Radius 8–11; 300 ms easeOutQuint | Fenster-Mockups, Tastenkappen, Dunkel |

## Tagesplanung / Assistent

| Seite | WD | Schema | Kernwerte | Taugt für |
|---|---|---|---|---|
| sunsama.com | `www.sunsama.com_2026-11-18` (+ `_2` bis `_5` Unterseiten) | hell (kein Dunkel) | Weiß 97 %; Orange 0,1 %; DM Sans; 56/600/−1 % ÷ 16; Zeile 55 Zeichen; Karten 14–20 + Pill; 200 ms, Einblendung easeOutQuart | Ruhe, echte Produktausschnitte, Tagesablauf |
| culturedcode.com/things | `culturedcode.com_2026-11-18` | hell | `#f2f5f7` 79 % + Weiß 21 %; Blau `#2576eb`; Systemschrift (keine Webfonts); 36/700 ÷ 15,3; Container 1002; 100/200 ms | Schlichtheit, Systemschrift richtig eingesetzt |

## Trading / Finanzen

| Seite | WD | Schema | Kernwerte | Taugt für |
|---|---|---|---|---|
| stripe.com | `stripe.com_2026-11-18` | hell + Dunkelbänder | Weiß 70 % + `#061b31` 16 %; `#533afd` 0,3 %; Söhne + Source Code Pro; 56/300/−2,5 % ÷ 16; Radius 4; 300 ms `(.25,1,.5,1)` | Leichte Überschriften, Token-System, Präzision |
| mercury.com | `mercury.com_2026-11-18` | dunkel | `#1e1e2a` 99,6 %; `#5266eb` 0,1 %; Arcadia (+ Tiempos-Serif); 59/480 ÷ 16; Radius 4; 1 Schattenstufe | Seriöses Dunkel, Fotografie |
| tradingview.com | `www.tradingview.com_2026-11-18` | Schwarz/Weiß je Sektion | Schwarz 44 % / Weiß 41 %; Signal Grün `#22ab94`, Rot `#cc2f3c`; Euclid Circular; 64/600/−4 % ÷ 14; Radius 8; Container 1000 | Signalfarben, Kontrast-Rhythmus (nur Startseite, nicht das Terminal) |

## Spiel / Community (eigene Wahl, keine Literaturquelle)

| Seite | WD | Schema | Kernwerte | Taugt für |
|---|---|---|---|---|
| discord.com | `discord.com_2026-11-18` | dunkel (Tiefblau) | `#1a2081` 84 %; `#5865f2` 0,1 %; ABC Ginto; 61/700 Versalien ÷ 16; 0 Schatten; Radien 12–16; 250–400 ms ease | eine laute Marke diszipliniert |
| bo3.gg | `bo3.gg_2026-11-18` (gemessen von anderer Session) | dunkel | `#22262c` 88 % + 2 Stufen; Gold `#e0aa5a` 0,1 %; Fira Sans; 32/500 ÷ 14; 13 Größen ab 8 px | Datendichte; auch Gegenbeispiel (Werbebanner, zu viele Größen) |
| playvalorant.com | `playvalorant.com_2026-11-18` | dunkel (Navy) | `#1a242e` 53 % + `#0f1923` 17 %; Rot `#ff4655` 4,6 %, Creme `#ece8e1` 12 % statt Weiß; Tungsten Bold (Plakat, Versalien) + DIN Next + Inter; 89 px ÷ 13; Radien 2–16 | Navy-Bühne mit warmem Gegenpol, Plakat-Typografie |
| arcane.com | `www.arcane.com_2026-11-18` | dunkel | `#161616` 62 % + `#0a0a0a` 31 %; Blau `#3d528f` 0,4 %; Oswald 700 + Inter; 89 px; gemalte Szenen (Textur) | Textur und Leuchten ohne Glätte |

Kreativ-Werkzeug dunkel: **spline.design** (`spline.design_2026-11-18`): Schwarz 75 % + `#101010` 18 % + `#1e1e1e`
6 % (drei Stufen); Geist + Spline Sans + Geist Mono; 56/450/−6 %; Pill-Knöpfe; Farbe nur aus 3D-Inhalten; Kurve
`(0.2,0.8,0.2,1)`, daneben eine Federkurve `(0.2,0.9,0.3,1.35)`. Ebenfalls gemessen: **warp.dev**
(`www.warp.dev_2026-11-18`, inzwischen hell: Weiß 96 %, Matter + Azeret Mono, Akzent `#2a1eff`).
Nicht messbar (Rechts-Check **Vorbehalt** am 18.11.2026): cyberpunk.net.

## Agentur / Firmenseite

| Seite | WD | Schema | Kernwerte | Taugt für |
|---|---|---|---|---|
| locomotive.ca | `locomotive.ca_2026-11-18` | hell + dunkler Hero | Weiß 84 % / Schwarz 16 %; ein Blau; Helvetica Now Display + Hausschrift, nur Gewicht 400; 102 px ÷ 26; 0 Radien, 0 Schatten; 300 ms easeOutCubic; GSAP + Lenis + WebGL | Typografie als Bild, Reduktion |

## Ungemessen (vorgeschlagen, Rechts-Check offen)

Aus dem Recherche-Report (Galerien, Fachartikel) bzw. eigener Wahl; vor Nutzung mit `site-anatomy` messen.

| Seite | Art | Grund |
|---|---|---|
| resend.com | Werkzeug | Code-Beispiel über dem Falz, interaktive Demos (Fachartikel) |
| sentry.io | Werkzeug | eigene Stimme, echtes Snippet |
| plane.so | Werkzeug | Preise ohne Kartenreihe |
| tailwindcss.com, astro.build, bun.sh | Werkzeug | Code als Hauptbild, Vergleichstabelle, Schrittfolge |
| binance.com Spot-Terminal, pro.kraken.com | Trading (App) | Dichte Live-Panels; vermutlich Bot-Schutz, erst Rechts-Check |
| tradingview.com/chart, /heatmap | Trading (App) | Chart-Mitte, Treemap |
| wise.com | Finanzen | eingebetteter Rechner |
| wearebulletproof.com, emotion-agency.com | Agentur | Awwwards Site of the Day (nur Optik, Scroll-Jacking prüfen) |
| amie.so | Tagesplanung | schöne Oberfläche, als Gegenbeispiel „schön, unreif“ |
