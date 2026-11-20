# Profi-Kanon: Woran man professionelle Websites und Dashboards erkennt (positiver Maßstab)

> Stand 18.11.2026, v1.0. Pflichtlektüre vor jedem Design der Stufe L und V (`~/.claude/rules/design-qualitaet.md`,
> Punkt 3). Ergänzt die Anti-KI-Checkliste (`anti_ki_checkliste.md`, sagt, was **nicht** sein darf) um das, was
> sein **soll**. Vorbilder mit Arbeitsordnern und Kernwerten: `~/.claude/skills/site-anatomy/references/vorbilder.md`.
>
> **Grundlage:** 12 Startseiten (P1–P14 beziehen sich auf diese 12) plus 4 Nachträge (VALORANT, Arcane, Spline,
> Warp; nur Abschnitt 2.4 und `vorbilder.md`) am 18.11.2026 mit `site-anatomy` gemessen (designlang 13.3.2, axe 4.14, je 4 Breiten
> hell/dunkel), 6 davon zusätzlich mit `leanrea` (Website-Zeile: HTML, CSS, JS-Marker) auf ihren Aufbau geprüft;
> dazu zwei Literaturberichte (`~/projects/Skills_&_Co/RECHERCHE/PROFI_WEBDESIGN_2026-11-18.md`,
> `…/DESIGN_ARTIKEL_KI_SLOP_ANLEITUNGEN_2026-11-18.md`) und Auszüge aus `…/DESIGN_SKILLS_REPOS_2026-11-18.md`.
>
> **Kennzeichnung:** **[M]** an den Vorbildern gemessen · **[L]** Literatur mit Primärquelle · **[K]** Fachkonsens
> mehrerer Praxisquellen, keine Studie · **[E]** eigenes Urteil. Wo Messung und Literatur sich widersprechen, steht
> es ausdrücklich da („Widerspruch“).

## 0. Erst die Weiche: Was baust du?

Viele Regeln gelten nur für eine Oberflächenart. Vor allem anderen festlegen:

| Art | Beispiele | Leitfrage | Es gelten |
|---|---|---|---|
| **W — Werkzeug/Dashboard** | Leitstand, Bot-Dashboard, Trading-Ansicht, Admin, Status | Kann jemand damit in 5 s seine Aufgabe erledigen? | Abschnitte 1, 2-W, 4, 5 |
| **M — Marketing/Lesen** | Landingpage, Firmenseite, Produktseite, Doku-Start | Versteht ein Fremder in 5 s, was es ist und für wen? | Abschnitte 1, 2-M, 3, 4, 5 |

Marketing-Verbote (Hero mit großer Kennzahl, Eyebrow-Zeilen, Standard-Sektionsfolge) greifen bei **W** nicht: Ein
Dashboard **soll** Kennzahlen groß zeigen. Umgekehrt gelten die Dichteregeln von W nicht für M. [L] (impeccable
`mode-operate`, interface-design; Übernahme-Liste 1 im Skills-Report)

## 1. Die 14 Prinzipien, die alle gemessenen Spitzenseiten teilen

Messwerte aus `ergebnis/design.json` der Arbeitsordner (Liste in `vorbilder.md`). „12/12“ heißt: bei allen
12 Seiten zutreffend.

### P1 · Eine Fläche dominiert, Farbe ist ein Budget
- [M] Die häufigste Hintergrundfarbe deckt bei 9 von 12 Seiten **79–99,6 %** der CSS-Hintergrundfläche (Sunsama
  97 % Weiß, Linear 97 % `#08090a`, Vercel 97 % Weiß, Mercury 99,6 % `#1e1e2a`, Raycast 86 % Schwarz, Discord 84 %
  Tiefblau). Ausnahmen mit Absicht: Plausible (51 % Weiß + 27 % Hellgrau = zwei Ebenen eines Dashboards), Stripe
  (70 % Weiß + 16 % Dunkelblau-Bänder), TradingView (Schwarz/Weiß-Wechsel je Sektion).
- [M] Der Markenakzent hat **0,1–0,3 %** Flächenanteil (Sunsama `#ff891c` 0,1 %, Linear 0,1 %, Vercel 0,1 %, Stripe
  `#533afd` 0,3 %, Mercury 0,1 %, Discord 0,1 %). Er sitzt auf Primärknopf, Fokus und einzelnen Markierungen.
- [L] Stripe, Linear, Geist, Radix: Farben als **Skala mit Rollen** (Fläche, Hover, Aktiv, Rahmen, Vollfläche,
  Text 2, Text 1), Stufen in LCH/Lab statt HSL. Linear erzeugt Hell und Dunkel aus 3 Eingaben (Basis, Akzent,
  Kontrast).
- **Regel:** 1 Grundfläche ≥ 75 % + 1–2 Flächenstufen; 1 Akzent ≤ 1 % Fläche; Statusfarben nur für Status.
  Neutrale leicht temperiert, kein reines `#000`/`#fff` als Flächenpaar im Dunkelmodus (Linear `#08090a` /
  `#f7f8f8`). [M]+[L]

### P2 · Überschriften leicht bis mittel, eng gesetzt, negativ gesperrt
- [M] Gewicht der größten Überschrift: Stripe **300**, Vercel 400–450, Locomotive 400, Raycast 400, Mercury 480,
  Linear **510**, Sunsama 600, TradingView 600. Nur Discord (700–800, Versalien) setzt laut – Gaming-Marke, siehe 2.4.
- [M] Laufweite der Display-Größen negativ: Linear −2,2 % (−1,41 px bei 64 px), Stripe −2,5 %, TradingView −4 %,
  Vercel **−6 %** (−3,84 px bei 64 px), Sunsama −1 %. Zeilenhöhe Display **1,0–1,16**. Fließtext ohne Sperrung.
- [L] Linear-Tokens: Titel ab 32 px `−0,022em`, darunter `−0,012em`; Zeilenhöhe Titel 1,0–1,1, Text 1,5–1,6.
- **Regel:** Display-Überschrift Gewicht 300–600 (nicht 700+ außer bewusst laute Marke), Zeilenhöhe 1,0–1,15,
  Laufweite −1 bis −3 % ab 32 px. [M]
- Widerspruch: Das Anthropic-Cookbook (10/2025) riet zu Extremgewichten 100/200 gegen 800/900. Die aktuelle
  `frontend-design/SKILL.md` und die Messung sprechen dagegen: Profis variieren fein (Linear 400/510/590). [L]+[M]

### P3 · Größensprung Hero : Fließtext = 3,5 bis 4,6
- [M] Größte Überschrift ÷ Fließtext: Sunsama 3,5 · Stripe 3,5 · Mercury 3,7 · Discord 3,8 · Locomotive 3,9 ·
  Linear 4,6 · Vercel 4,6 · TradingView 4,6. Ausreißer: Raycast 8,6 (112 px Hero auf 13 px), Things 2,4, Plausible
  2,6 (Dashboard).
- [M] Hero-Größen absolut bei 1280 px: **56–64 px** (Sunsama 56, Stripe 56, Mercury 59, Discord 61, Linear 64,
  Vercel 64, TradingView 64); Agentur bis 102 px (Locomotive); Werkzeug/Dashboard 32–36 px (Plausible 36, bo3 32).
- **Regel M:** Hero 56–64 px bei 16 px Text (Faktor 3,5–4). **Regel W:** größte Zahl/Überschrift 28–40 px bei
  13–14 px Text (Faktor 2,3–2,9). [M] Literatur gibt hier keine Zahl. [L: offen]

### P4 · Wenige Stufen, eine Skala
- [M] Anzahl Schriftgrößen: Things 9, Discord 9, Locomotive 7 (+0), Plausible 7, Vercel 11, Mercury 11, Sunsama 12,
  Raycast/Linear/Stripe/TradingView 14 (inkl. Kleinst-Labels in Produkt-Mockups).
- [L] Linear als Token-System: `--text-tiny/mini/small/regular/large` 10/13/14/15/17 px, `--title-1…9`
  17/20/24/32/40/48/56/64/72 px – eine geschlossene Leiter, keine freien Werte. Vercel Geist: Copy 13–24, Heading 14–72.
- **Regel:** Je Seite höchstens 6–8 genutzte Stufen aus einer benannten Leiter; Stufen als Tokens, nie freie px. [L]+[M]

### P5 · Zwei Familien maximal, eine davon oft Mono
- [M] 12/12 nutzen höchstens zwei Text-Familien, meist eine plus Mono: Linear Inter + Berkeley Mono, Vercel Geist +
  Geist Mono, Raycast Inter + Geist Mono, Stripe Söhne + Source Code Pro, Mercury Arcadia (Text + Display) und
  Tiempos (Serif-Auszeichnung), Discord ABC Ginto, TradingView Euclid Circular, Things Systemschrift.
- [M] Variable Fonts mit Zwischengewichten: Linear 510/590/680, Vercel 450, Mercury 420/480/530.
- [L]+[M] **Inter ist kein KI-Merkmal an sich:** Linear (Primärquelle) und Raycast nutzen Inter. Kennzeichen von
  KI-Seiten ist die **ungewählte** Standardschrift ohne Skala und Begründung. Siehe Abschnitt 6, Konflikt K1.
- **Regel:** Schrift **bewusst wählen und im Plan begründen** (Rolle, Charakter, Zahlendarstellung); höchstens zwei
  Familien; Mono für Zahlen, Code, Tastenkürzel. Ein Display-Schnitt ab ca. 28 px ist belegt (Linear). [L]+[M]

### P6 · Zeilenlänge im Lesebereich
- [M] Gemessene Fließtextzeilen: Sunsama 55, Stripe 55, TradingView 54, Things 49, Linear 48 Zeichen. (Vercel 157,
  Locomotive 160, Mercury 101 sind Messfehler auf Einzeilern bzw. Display-Texten, nicht Lesetext.)
- [L] 45–75 Zeichen (Practical Typography, Baymard), nie über 80 (WCAG 1.4.8), Practical UI 40–80.
- **Regel:** `max-width` 60–70ch für Lesetext; Zielwert 50–60 Zeichen wie die Vorbilder. [M]+[L]

### P7 · Fließtext 16 px (Marketing) bzw. 13–15 px (Werkzeug)
- [M] Marketing: Sunsama, Stripe, Mercury, Discord je 16 px. Produktnahe Seiten: Raycast 13, Linear 14 (Token 15),
  Vercel 14, TradingView 14, Plausible 14, bo3 14. Agentur Locomotive 26 px Lauftext (Editorial-Geste).
- [L] Web-Lesetext 15–25 px; Produkt-UI 13–14 px; Geist-Copy 13/14.
- **Regel:** M 16–18 px, W 13–14 px, nie unter 12 px für lesbaren Text. [M]+[L]

### P8 · Abstände aus einer Leiter, Sektionen weit auseinander
- [M] Abstandsbasis 4 px (Sunsama, Vercel, Mercury, TradingView) oder 2 px-Raster mit 4/8-Werten. Lücken-Leitern:
  Sunsama 8/12/16/20/24/32/40/64, Linear 2/4/8/10/16/20/24/32, Vercel 4/6/8/10/12/16/20/32.
- [M] Größter Sektionsabstand (Leiter-Maximum): Stripe 96, TradingView 96, Sunsama 120, Linear 128, Mercury 128,
  Discord 197, Raycast 224, Things 240 px. **Median ≈ 125 px** bei 1280 px. Linear-Token `--page-padding-block` 64 px.
- [L] Carbon 2/4/8/12/16/24/32/40/48/64/80/96/160; Literatur nennt **keine** belegte Zahl für Sektionsabstände.
- **Regel M:** Sektionsabstand 96–128 px (Desktop), auf 390 px etwa halbieren; innerhalb einer Gruppe ≤ 24 px.
  **Regel W:** Zonen 24–48 px, Karten-Innenabstand 16–24 px. Abstand zwischen Gruppen immer größer als innerhalb. [M]

### P9 · Inhaltsbreite 1000–1280 px
- [M] Container: Things 1002, TradingView 1000, Sunsama 1067, Plausible 1120, Discord 1200, Raycast 1204, bo3 1216,
  Stripe 1248, Linear 1260, Vercel 1280, Mercury 1280. Linear-Token `--page-max-width` 1024 px für Lesespalten.
- **Regel:** Hauptcontainer 1120–1280 px, Lese-/Formularspalten 640–1024 px. [M] (Literatur: keine Primärquelle.)

### P10 · Wenige, kleine Radien; Pill nur für Knöpfe und Chips
- [M] Dominanter Radius: Stripe **4 px** (82×), Mercury 4 px (205×), Linear-Tokens 4/6/8/12/16/24/32 + Pill (9999,
  83×), Vercel 4–20, TradingView 8 px, Plausible 6 px, Locomotive **0** (gar keine Radien). Große Radien (24–40 px)
  nur für Sektionsflächen und Mockup-Rahmen (Sunsama, Discord).
- **Regel:** Ein Basis-Radius 4–8 px für Bedienelemente, eine größere Stufe 12–16 px für Karten/Panels, Pill nur für
  Knopf/Chip. Nie ein Radius für alles. [M]

### P11 · Tiefe kaum sichtbar
- [M] Discord und Locomotive: **0** Schatten. Mercury 1 Stufe. Sunsama dreilagiger Haarschatten Alpha 0,05–0,08.
  Vercel: Rahmen als Schatten (`0 0 0 1px #00000014`) plus gestaffelte Ebenen mit Alpha ≤ 0,04. Stripe zweilagige
  Schatten mit negativem Spread. Linear: im Dunkeln `--shadow-*: none`, Tiefe über Flächenstufen
  `--color-bg-level-0…3` (`#08090a` → `#0f1011` → `#141516` → `#191a1b`).
- [L] Linear: „Struktur soll gefühlt, nicht gesehen werden“; Refactoring UI: weniger Rahmen.
- **Regel:** Hell: Haarschatten Alpha ≤ 0,08 oder 1-px-Rahmen; Dunkel: Flächenstufen von je +3–5 % Helligkeit statt
  Schatten. Schatten nach Ebene gestuft (Karte < Popover < Dialog). [M]+[L]

### P12 · Bewegung kurz, auslaufend, aus Tokens
- [M] Häufigste Dauer: Linear **160 ms** (39×) mit `--ease-out-quad` (59×), Tokens `--speed-quickTransition` 100 ms,
  `--speed-regularTransition` 250 ms; Stripe 300 ms (90×) mit `cubic-bezier(.25,1,.5,1)` (88×); Raycast 300 ms mit
  easeOutQuint `(.23,1,.32,1)`; Vercel 150–200 ms mit `ease-out` (65×); Locomotive 300 ms easeOutCubic. Sunsama
  200 ms Hover, Einblendung 450–700 ms easeOutQuart.
- [M] Respekt vor „Bewegung reduzieren“: `prefers-reduced-motion` Stripe 184×, Linear 41×, Vercel 29×, Raycast 12×,
  Mercury 9×, Locomotive 5×.
- [L] NN/g: Feedback ~100 ms, Übergänge 200–300 ms, über 500 ms zieht es sich; Eintritt ease-out. Stripe: nur
  `transform`/`opacity`. Material/Carbon: Dauerstaffel 50–1000 ms, Standardkurve `cubic-bezier(0.2,0,0,1)`, kein
  ease-in für UI-Eintritte (Skills-Report, Übernahme 4).
- **Regel:** Hover/Feedback 100–160 ms, Übergänge 200–300 ms, Einblendung einmalig ≤ 500 ms (Gesamt-Staffel ≤ 500 ms);
  Kurven ease-out (`(0.2,0,0,1)`, easeOutQuad/Quart/Quint); ease-in höchstens für kurze Austritte; nie `linear` außer
  Fortschritt; Dauern und Kurven als Tokens; Reduced-Motion-Variante Pflicht. Tastaturaktionen nicht animieren. [M]+[L]
- Widerspruch, ehrlich: Vercel hat einen Token „swift“ `cubic-bezier(.175,.885,.32,1.1)` (≈ 10 % Überschwingen) für
  Popover 200 ms und Overlay 300 ms; Raycast nutzt JS-Federn (stiffness 500–550, damping 25 = leicht unterdämpft).
  Profis setzen kleines Überschwingen also **nur** bei kleinen Aufklapp-Elementen ≤ 300 ms ein, nie bei Inhalt,
  Scroll oder Sektionen. Die Anti-KI-Regel A12 (Überschwingen hart) bleibt für uns gültig; siehe Konflikt K2.

### P13 · Echtes zeigen statt Deko
- [V] 5 von 12 Startseiten zeigen im ersten Bildschirm (1280 × 800) das **echte Produkt** (Sunsama Planer, Linear
  App, Plausible Live-Daten, Discord App-Mockup, bo3 Turnierdaten); Things zeigt App-Icon und Video-Link. Die übrigen
  setzen ein Markenbild (Stripe Farbband, Raycast rote Diagonale, Vercel Dreieck, Mercury Foto, TradingView Planet,
  Locomotive WebGL-Video) – das ist Markensignatur, nicht übertragbar (Abschnitt 5). Kontaktbogen:
  `~/site-anatomy/_kanon_bewertung/kontaktbogen_startseiten.png`.
- [L] Evil Martians (100 DevTool-Seiten): echter Code/Screenshot als Hauptvisual; Raycast echte Screenshots im
  macOS-Fensterrahmen. Ouyang/Krebs: Lucide-Icons und abstrakte Blobs als häufigste KI-Muster.
- **Regel:** Hauptbild = echte Oberfläche, echter Code oder echte Daten (bei uns Dummy-Daten nach Fach, A7). Icons
  nur als Bedienzeichen. [M]+[L]

### P14 · Moderne CSS als Handwerkszeichen
- [M] `text-wrap: balance` (Vercel 17, Raycast 10, Stripe 12, Linear 2, Mercury 4), `color-mix()` (Vercel 281,
  Linear 69, Stripe 22), `oklch()` (Vercel 216), Container-Queries (Vercel 148, Stripe 26), `:has()` (Stripe 308),
  `@layer` (Stripe 156, Linear 66), `font-variant-numeric` (Linear 27). [leanrea, Zählungen über HTML+CSS]
- **Regel:** Überschriften `text-wrap: balance`, Absätze `pretty`; Farben in OKLCH/`color-mix` aus Tokens; Zahlen in
  Tabellen `tabular-nums`; Komponenten mit Container-Queries, wo sie in verschiedene Breiten fallen. [M]

## 2. So sieht es bei den Besten aus (je Projektart)

### 2.1 Tagesplanung / Assistent (Art M für die Seite, W für die App)
- **Vorbilder:** Sunsama (hell), Things (hell); App-Bild: Linear.
- **Werte [M]:** Sunsama: 97 % Weiß, Akzent Orange 0,1 %, DM Sans 400–700, Hero 56 px/600/−1 %, Text 16 px, Zeile
  55 Zeichen, Lücken 8–64, Sektionen bis 120 px, Radien 14–20 Karte + Pill, dreilagiger Haarschatten, 200 ms.
  Things: Grund `#f2f5f7` 79 % + Weiß 21 %, Akzent Blau `#2576eb`, Systemschrift, Hero 36 px/700, Text 15,3 px,
  Container 1002 px, Radien 3–18, Dauern 100/200 ms, keine Webfonts.
- **Übertragbar:** Ruhe als Produktversprechen (fast keine Bewegung, eine warme Atmosphäre nur oben); Tagesablauf als
  Gliederung; echte Planer-Ausschnitte in gedämpften Karten; ein Akzent.
- **Nicht übertragbar:** Sunsamas Orange/Pfirsichverlauf, DM Sans, das Akzentwort in der Headline (bei uns A3).
  Things wirkt stark durch das bekannte App-Icon und die Apple-Nähe (Markenbonus).

### 2.2 Dashboard / Werkzeug (Art W)
- **Vorbilder:** Plausible (Live-Dashboard, hell), Linear (App im Hero, dunkel), Vercel (hell/dunkel), Raycast (dunkel).
- **Werte [M]:** Plausible: Text 14 px, größte Zahl 36 px/800, 7 Größen, Abstände 4–32, Radien 2/6, Fläche Weiß 51 %
  + `#f4f4f4` 27 % (zwei Ebenen), 3 Signalfarben (Grün, Blau, Rot) mit je < 0,3 % Fläche, Dauern 100–300 ms
  `(0.4,0,0.2,1)`. Linear: Flächenstufen `#08090a/#0f1011/#141516/#191a1b`, Text `#f7f8f8`/`#d0d6e0`/`#8a8f98`/
  `#62666d` (4 Textstufen), Header 57–72 px, Ebenen-Tokens (`--layer-popover` 600, `--layer-dialog` 700,
  `--layer-tooltip` 1100). Vercel: Rahmen-als-Schatten, Graustufen als Rollen, Geist + Mono.
- **Übertragbar:** 4 Textstufen statt beliebiger Grautöne; Flächenstufen statt Schatten im Dunkeln; Kennzahl + Verlauf
  (Plausible: Zahl, Veränderung in %, Linie); Tabellenzeilen mit rechtsbündigen Zahlen; Dichte 13–14 px.
- **Dashboard-Prüfpunkte D1–D5** (aus Skills-Report Übernahme 1/9, an Plausible/Linear gegengeprüft):
  - D1 Standard-Bedienelemente (Filter, Zeitraum, Tabs) an erwarteter Stelle, nichts nur per Hover.
  - D2 Ein Signaturzug, nicht mehr (Plausible: die eine große Linie; Linear: die Seitenleiste).
  - D3 Echte Werte mit Einheiten, unrund, `tabular-nums`, rechtsbündig; Datenalter sichtbar („vor 12 s“).
  - D4 Mindestens ein sehenswerter Sonderzustand gebaut: leer, laden, Fehler, Alarm.
  - D5 Kennzahl immer mit Vergleich/Verlauf, nicht als nackte Zahl; Status nie nur über Farbe.
- **Nicht übertragbar:** Linears Lila `#5e6ad2/#7170ff`, Vercels schwarzes Dreieck und Geist-Pixel-Schriften.

### 2.3 Trading / Finanzen
- **Vorbilder:** Stripe (hell), Mercury (dunkel), TradingView (Schwarz/Weiß).
- **Werte [M]:** Stripe: Söhne **300** für Überschriften (56 px, −2,5 %), Text 16 px, Radius 4 px dominant,
  zweilagige Schatten, `cubic-bezier(.25,1,.5,1)` 300 ms, Akzent `#533afd` 0,3 %, Container 1248, HDS-Tokens
  (~4.900 Farbverweise, ~2.900 Abstandsverweise). Mercury: Fläche `#1e1e2a` 99,6 %, Arcadia 480 + Tiempos-Serif,
  Hero 59 px, Radius 4 px (205×), 1 Schattenstufe, Fotografie (Arbeitsplatz in Landschaft). TradingView: Euclid
  Circular 600, Hero 64 px/−4 %, Text 14 px, Container 1000, Signalfarben Grün `#22ab94`/`#06806b`, Rot `#cc2f3c`.
- **Übertragbar:** Leichte Überschriften wirken seriös (300–480); kleine Radien (4 px) wirken präzise; Grün/Rot nur für
  Kursrichtung, mit Vorzeichen und Pfeil, nie als Deko; Zahlen mono/tabellarisch.
- **Nicht übertragbar:** Stripes Farbband-Verlauf (Markensignatur, als „Verlauf“ bei uns A6), Mercurys Fotowelt,
  TradingViews Weltraum-Hero. Für echte Trading-Ansichten (Terminal, Heatmap) siehe ungemessene Vorbilder.

### 2.4 Gaming / Community (eigene Wahl, keine tragfähige Literaturquelle)
- **Vorbilder:** Discord (laute Marke), bo3.gg (dichte Esport-Daten, dunkel). Die Wahl ist **eigene Begründung**:
  Discord ist die Plattform, auf der die Bots leben; bo3 zeigt Datendichte in dunklem Schema.
- **Werte [M]:** Discord: Fläche Tiefblau `#1a2081` 84 %, ABC Ginto 700–800 in Versalien, Hero 61 px, Text 16 px,
  **0** Schatten, Radien 12–16 + 88 für Mockups, 250–400 ms `ease`, Akzent Blurple `#5865f2` 0,1 %, Illustrationen
  (Maskottchen). bo3: Fläche `#22262c` 88 % + `#2a3038` 10 % + `#434a54` 3 % (drei Flächenstufen), Fira Sans
  400/500, Text 14 px, 13 Größen 8–32 px, Gold `#e0aa5a` 0,1 % als Akzent.
- **Dunkle Navy-/Plakat-Richtung [M]:** VALORANT: Navy `#1a242e` 53 % + `#0f1923` 17 %, Rot `#ff4655` 4,6 % als
  warmer Gegenpol, Creme `#ece8e1` statt Weiß, schmale fette Plakatschrift (Tungsten) 89 px in Versalien über 13 px
  Text, Radien 2–16. Arcane: `#161616`/`#0a0a0a`, Oswald 700 bis 89 px, gemalte Szenen mit Textur, ein Blau
  `#3d528f`. Spline (Kreativ-Werkzeug): drei Schwarzstufen, Farbe nur aus dem Inhalt. Zeigt: „dunkel + ein Licht“
  wird erst durch **Textur, Plakat-Schrift und warmen Gegenpol** eigenständig – ohne sie ist es der KI-Cluster
  „Near-Black + Neon“ (A1).
- **Übertragbar:** Laute Marke darf laut sein, aber **eine** Lautstärke (Discord: Versalien-Headline, sonst ruhig);
  drei dunkle Flächenstufen für Datenpanels (bo3); keine Schatten im Dunkeln.
- **Nicht übertragbar / Schwächen:** Discords Maskottchen und Blurple; bo3 hat Glücksspiel-Werbebanner im ersten
  Bildschirm, 13 Schriftgrößen ab 8 px und den Consent-Banner ohne Ablehnen-Knopf (`no_reject_button_found`) –
  Gegenbeispiel für Dichte ohne Disziplin.

### 2.5 Agentur / Firmenseite (Art M)
- **Vorbilder:** Locomotive (Awwwards-Agentur, hell/dunkel), Stripe (Firmenseite), Mercury.
- **Werte [M]:** Locomotive: Helvetica Now Display + Hausschrift, **ein** Gewicht (400), Lauftext 26 px, Überschriften
  64–102 px mit Zeilenhöhe 1,0, **keine Radien, keine Schatten**, nur Schwarz/Weiß + ein Blau, 300 ms easeOutCubic;
  Technik: Vue + GSAP + Lenis (sanftes Scrollen) + three.js (WebGL-Video-Hero) [leanrea].
- **Übertragbar:** Typografie als Hauptbild (große Schrift, wenige Gewichte); radikale Reduktion der Mittel; eine
  starke Signatur statt vieler Effekte.
- **Nicht übertragbar:** WebGL-Hero und sanftes Scrollen (Lenis) – teuer, oft Scroll-Jacking-nah (YC-Kritik);
  Agentur-Ruhm trägt die Wirkung mit. Für eine kleine Agentur: Typo-Reduktion ja, WebGL nein.

## 3. Wie es gebaut ist (leanrea, Website-Zeile, 18.11.2026)

| Seite | Gerüst | CSS-Ansatz | Schriften | Bewegung | Bilder |
|---|---|---|---|---|---|
| Linear | React Server Components, gebaut mit **Vite** (`vite-rsc`, Pfad `/_next/` nur Name), 47 CSS-Dateien | styled-components 6.1.24 + CSS-Module, Tokens als Custom Properties (`--color-bg-level-*`, `--title-1…9`, `--ease-*`, `--speed-*`, `--radius-*`, `--layer-*`) | Inter Variable (vorgeladen) + Berkeley Mono, `font-feature-settings "cv01","ss03"` | reines CSS, Kurven-Tokens (12 Penner-Kurven), 160 ms | SVG + 5 PNG, 32× `loading=lazy` + `decoding=async` |
| Vercel | Next.js | Tailwind (109 `--tw-`-Variablen) + Geist-Tokens (`--ds-shadow-*`, `--ds-motion-*`), OKLCH | Geist Variable + Geist Mono + 5 Geist-Pixel-Schnitte vorgeladen | CSS, ease-out 150–200 ms, Popover-„swift“ mit Überschwingen | 59× WebP, Logos als SVG hell/dunkel vorgeladen |
| Raycast | Next.js | CSS-Module (`*_embla__*`), 118 Custom Properties, viel `backdrop-filter` (64) | Inter + Geist Mono + Instrument Serif + VT323 (Akzent) | CSS easeOutQuint 300 ms + JS-Federn (stiffness 500–550) | überwiegend PNG/JPG (333 PNG), kaum WebP |
| Stripe | Next.js (`__NEXT_DATA__`, CDN `b.stripecdn.com`) | CSS-Module + eigenes Token-System `--hds-*` (Farbe, Abstand, Schrift, Schatten in Teilwerten), `@layer` 156× | Söhne Variable + Source Code Pro (vorgeladen) | CSS `(.25,1,.5,1)` 300 ms, Reduced Motion 184× | PNG + WebP-Fallbacks des Wellenbilds je Breite, `fetchpriority=high` 4× |
| Mercury | Next.js | Tailwind (88 `--tw-`) + eigene Variablen, `:has()` 61× | Arcadia Text/Display (Variable) + Tiempos Headline (4 Schnitte vorgeladen) + IBM Plex Mono | CSS ease-out + `(.16,0,.13,1)` | 216× WebP, 3 MP4 |
| Locomotive | Vue (vermutlich Nuxt) | ein CSS-Bundle (212 KB), `clamp()` 106× | Helvetica Now Display + LocomotiveNew | **GSAP** + ScrollTrigger + **Lenis** + **three.js/WebGL** | JPG/PNG + 2 MP4 |

Grenzen: Statische Zählung über HTML, bis 25 Skripte und alle verlinkten CSS-Dateien; keine Laufzeitbeobachtung.
Marker wie „rive“ oder „segment“ treffen auch fremde Wörter (derive, segment) und sind nicht ausgewertet. Kein
Quelltext übernommen. **Bildformate [M]:** AVIF in keinem HTML der sechs Seiten; WebP bei Vercel und Mercury
Standard, PNG/JPG bei Raycast und Stripe – das Format allein macht keine Profi-Seite (Literatur: offen).

**Gemeinsam:** Tokens für alles (Farbe, Größe, Kurve, Dauer, Ebene, Radius); eine Variable-Font-Familie selbst
gehostet und vorgeladen; Bewegung in CSS, JS nur für Signaturmomente; kein UI-Kit-Standardlook (kein shadcn-Default
erkennbar).

## 4. So baust du es (Arbeitsanweisung für Sessions)

Aus dem Artikel-Report (Abschnitt b), an der Messung gegengeprüft:

1. **Weiche W/M setzen** (Abschnitt 0), dann Brief: Produkt, Zielgruppe, eine Hauptaktion. [L: Anthropic SKILL.md]
2. **Vorbild wählen** aus `vorbilder.md` (passende Projektart) und seine Kernwerte notieren; Adjektive wie „modern“
   ersetzen durch prüfbare Werte. [L]
3. **Plan in eine Designdatei** (`DESIGN.md` im Projekt): 4–6 benannte Farben mit Rolle, Schriftrollen mit
   Begründung, Typo-Leiter (6–8 Stufen), Abstandsleiter, Radius-/Schattenstufen, Bewegungs-Tokens, Layoutskizze.
   Jede Seite zitiert die Datei vor dem Bauen. [L: CodeMySpec, Anthropic]
4. **Tokens statt freier Werte**, Farben als Rollen-Skala (P1), Leitern aus P4/P8. [L]+[M]
5. **Eine Hauptaktion und ein Signaturmoment** je Seite; Bewegung nur als Reaktion oder einmaliger Auftritt. [L]
6. **Struktur aus dem Inhalt** statt Standardfolge; mindestens eine nicht-gleichförmige Sektion (Tabelle, Vergleich,
   Ablauf, echter Ausschnitt). [L]
7. **Konkretes statt Floskel**; jede Zahl nach Fach (bei Dummy-Daten unrund, mit Einheit); Logo-Abdecktest. [L]
8. **Echtes statt Stock** (P13). [M]+[L]
9. **Randzustände mitbauen** (leer, laden, Fehler mit Lösungsweg). [L]
10. **Nach einem Verbot den neuen Default prüfen** (zweite Welle: Creme + Serif + Terrakotta, Near-Black + Neon,
    Versal-Eyebrows, Mono-Kleintext, Pfeile). [L]
11. **Prüfen wie ein Fremder:** rendern 390/1280, jede Interaktion selbst durchspielen, Vorbild-Vergleich (Abschnitt 7),
    Zweitblick. [Regel design-qualitaet]

## 5. Was nur durch die Marke wirkt (nicht übertragbar)

| Wirkung | Seite | Warum nur Marke |
|---|---|---|
| Farbband-Verlauf als Hauptbild | Stripe | Seit Jahren Markenzeichen; bei uns wäre es Deko-Verlauf (A6, Rang 1 der KI-Merkmale) |
| Rote Diagonale, 112-px-Hero | Raycast | Markenkunst; die Seite lebt davon, dass man das Produkt kennt |
| Weltall-/Landschaftsfoto | TradingView, Mercury | Bildetat und Fotoproduktion, nicht nachbaubar ohne eigene Fotos |
| Maskottchen, Blurple, Versal-Headline | Discord | Wiedererkennung über 10 Jahre |
| WebGL-Video, riesige Hausschrift | Locomotive | Agentur zeigt Technik als Portfolio; bei Kundenseiten Overkill |
| Akzentwort in der Headline | Sunsama, Stripe | Bei bekannten Marken ein Stilmittel, bei uns A3 (Ouyang: 52 % der KI-Seiten) |
| App-Icon allein als Hero | Things | Funktioniert nur, weil das Icon bekannt ist |

**Übertragbar sind die Verhältnisse**, nicht die Bilder: Flächenanteile (P1), Gewichte und Sperrung (P2), Sprünge
(P3), Leitern (P4/P8), Radien (P10), Tiefe (P11), Bewegungsdauern (P12).

## 6. Typische Schwächen (KI-Slop) und ihre Belastbarkeit

Strichliste über 24 direkt gelesene Quellen (Artikel-Report 1.2); Quellen sind teils voneinander abhängig.

| Merkmal | Quellen | Bei den Vorbildern? |
|---|---|---|
| Violett/Indigo/Blau-Verläufe als Deko | 20 | Stripe-Band (Marke), Raycast-Rot – sonst nicht |
| Austauschbare Copy, Mad-Lib-Headline | 13 | nein |
| Ungewählte Standardschrift | 12 | Inter bei Linear/Raycast, aber **gewählt** (Skala, Display-Schnitt, Features) |
| Drei gleiche Icon-Karten | 12 | nicht im ersten Bildschirm gesehen |
| Zentrierter Standard-Hero mit Pill-Badge | 10 (Badge 4) | zentriert: Raycast, TradingView, Things, Mercury – **ohne** Pill-Badge |
| Uniforme Radien/Schatten/Abstände | 8 | nein (Radien gestuft, P10) |
| Emoji-Icons, Glas/Glow, Versal-Eyebrows | je 7 | Raycast nutzt `backdrop-filter` 64× (Fenster-Mockups) |
| Zweite Welle (Creme+Serif+Terrakotta, Near-Black+Neon) | 7 | nein |
| Standard-Sektionsfolge, Fade auf jeder Sektion, Stockbilder, Karten in Karten | je 5 | nicht geprüft (nur erster Bildschirm angesehen) |
| Erfundene Zahlen/Testimonials | 4 | nein (echte Logos/Kunden) |
| Farbiger Kartenrand, 01/02/03, Dauer-Dunkel, fehlende Randzustände | 3–4, unsicher | Dauer-Dunkel: Linear, Raycast, Mercury – bei Profis normal |

**Gewichtung:** Ein Einzelmerkmal beweist nichts. Belastbar ist erst ein **Bündel von 4–6 Merkmalen** auf einer
Seite (Krebs ≥ 4, Ouyang ≥ 6). Dunkel, zentrierter Hero und Inter sind bei Profis normal; entscheidend ist die
begründete Wahl. Verbotslisten verschieben nur den Default. [L]

**Konflikte mit dem Bestand (nicht hier entschieden, an die Setup-Zentrale gemeldet):**
- **K1 Schriftnamen:** `anti_ki_checkliste.md` A2 nennt Inter, Space Grotesk, Geist, Outfit, Satoshi „im Bild“ und
  prüft mit dem Detektor `overused-font`; `design-taste-frontend` (:48, :115) verbietet dieselben „ohne Grund aus dem
  Brief“; die impeccable-Ablehnungsliste (`reference/brand.md:32`) enthält Inter, DM Sans, IBM Plex, Instrument Serif.
  Die Vorbilder nutzen Inter (Linear, Raycast), Geist (Vercel), DM Sans (Sunsama), IBM Plex Mono und Instrument Serif
  (Mercury, Raycast). Die Regeln sind bedingt formuliert („ohne Begründung“), der Detektor aber namensbasiert.
  Kanon-Regel: P5 („bewusst wählen und begründen“). Eine begründete Inter-Wahl ist kein A2-Befund.
  **Entschieden (der Nutzer 20.11.2026 21:51, MB289 „ja“):** A2 und `visual_sheet.mjs` umgestellt; `overused-font` und
  `reflex-schrift` sind nur noch Hinweise, Befund ist allein die fehlende Begründung im Plan.
- **K2 Überschwingen:** A12 wertet Überschwingen hart; Vercel („swift“, 10 %) und Raycast (Federn) nutzen es klein
  bei Popovern ≤ 300 ms. Kanon: bleibt verboten bei Inhalt/Sektionen; für Popover offen (Entscheidung Zentrale).
- **K3 Akzentwort/Verlauf:** Sunsama und Stripe haben ein farbiges Wort in der Headline (A3) und Stripe einen
  Verlauf als Hauptbild (A6). Bei Marken mit Wiedererkennung tragen sie; bei uns bleiben A3/A6 gültig.
- **K4 ease-in:** NN/g erlaubt ease-in für Austritte, Material/Carbon (Skills-Report) „nie ease-in bei UI“. Kanon:
  ease-in nur für Austritte ≤ 200 ms.

## 7. Prüfliste „Hält der Entwurf neben dem Vorbild stand?“

Eigenen Entwurf und Vorbild in **derselben Breite** (1280 und 390 px) nebeneinander rendern; Werte aus beiden
`design.json` (eigener Entwurf: site-anatomy Phase 6 Schritt 4 auf `127.0.0.1`) bzw. aus den Kernwerten in
`vorbilder.md`. Jede Zeile: Vorbild · eigen · Δ · ok.

| # | Kennzahl | Quelle (`design.json`) | Toleranz |
|---|---|---|---|
| V1 | Flächenanteil Grundfläche | `colors.dominance[0].areaShare` | eigen ≥ 0,75 (W: Grund + 1 Stufe ≥ 0,75) |
| V2 | Akzent-Flächenanteil | `colors.dominance[]` des Akzents | ≤ 0,01 |
| V3 | Anzahl Buntfarben (Sättigung > 15 %) außer Status | `colors.all[]` | ≤ Vorbild + 1 |
| V4 | Hero : Fließtext | `typography.scale[0].size ÷ typography.body.size` | M 3,5–4,6 · W 2,3–2,9 |
| V5 | Gewicht der größten Überschrift | `typography.scale[0].weight` | ±100 zum Vorbild, ≤ 600 außer Brief verlangt laut |
| V6 | Laufweite Display | `typography.scale[0].letterSpacing ÷ size` | −1 bis −3 % ab 32 px |
| V7 | Zahl der Schriftgrößen | `typography.system.sizeCount` | ≤ 8 (W ≤ 9) |
| V8 | Schriftfamilien | `typography.families` | ≤ 2 + Mono, Wahl im Plan begründet |
| V9 | Zeilenlänge Lesetext | `typography.system.measure.charsPerLine` | 45–75 |
| V10 | Abstandsbasis und Leiter | `spacing.base`, `layout.system.gapScale` | Basis 4 oder 8; Werte nur aus der Leiter |
| V11 | Größter Sektionsabstand | `layout.system.rhythm.ladder` max | M 96–128 px · W 24–48 px |
| V12 | Containerbreite | `layout.system.container.contentWidth` | 1120–1280 px |
| V13 | Radien | `borders.radii` | ≤ 4 Stufen + Pill; kein Radius > 16 px auf Bedienelementen |
| V14 | Schattenstufen und Stärke | `shadows.system.levels`, Alpha | ≤ 3 Stufen, Alpha ≤ 0,08 (dunkel: 0) |
| V15 | Bewegungsdauern | `motion.durations`, `animations.durations` | Hover ≤ 160 ms, Übergang ≤ 300 ms, nichts > 500 ms außer Signatur |
| V16 | Kurven | `animations.easings` | ease-out-Familie; kein `linear` außer Fortschritt; kein Überschwingen (K2) |
| V17 | Reduced Motion | CSS-Suche `prefers-reduced-motion` | vorhanden |
| V18 | axe-Verstöße | `a11y.json` `violations[].impact` | eigen ≤ Vorbild und 0 kritische |
| V19 | Echtes im ersten Bildschirm | Bild 1280 × 800 | Produkt/Daten/Code sichtbar (P13) |
| V20 | W: D1–D5 | Bild + Code | alle erfüllt |

Bestanden: alle V-Zeilen ok oder begründet abweichend (Begründung aus Brief/Vorbild im Prüfprotokoll). Sichtvergleich:
„gleichwertig, nicht verwechselbar“. Drei Zeilen „nein“ ohne Begründung = nicht bestanden, nächste Tor-Runde.

## 8. Grenzen

- **Keine Übernahme** von Logos, Markenzeichen, Hausschriften (Söhne, ABC Ginto, Geist Pixel, Berkeley Mono, Arcadia,
  Tiempos, Helvetica Now, LocomotiveNew sind lizenzpflichtig bzw. markengebunden), Fotos, Illustrationen, Texten,
  Slogans und Markenfarben. Übernommen werden nur Verhältnisse und Prinzipien; Markenabstand mit
  `brand_distance.mjs` (ΔE ≥ 20).
- Messwerte sind Stand 18.11.2026, nur Startseite, nur erster Eindruck plus designlang-Statistik. Unterseiten, echte
  Apps (Login), Hover-/Fehlerzustände und Felddaten sind **nicht erhoben**.
- designlang-Grenzen: `areaShare` misst CSS-Hintergrundfläche (Bilder zählen nicht); `measure` greift bei Display-Text
  daneben (Vercel 157, Locomotive 160); `isBounce` meldet auch blinkende Deckkraft (Linear-Punktmatrix,
  Raycast-Keyframes ungenutzt) – Bewegungsbefunde gegen CSS prüfen.
- Die Profis sind nicht fehlerfrei: alle 12 haben axe-Verstöße (Linear 1 ernst, TradingView 2 kritisch, Sunsama
  Orange auf Weiß ≈ 2,3:1). Barrierefreiheit (WCAG 2.2) geht vor dem Vorbild.
- des Nutzers Geschmacksprofil fehlt noch; es entsteht aus `~/site-anatomy/_kanon_bewertung/bewertung.md` und kann
  Gewichtungen hier verschieben.

## Pflege

Vierteljährlich oder wenn ein Vorbild neu gemessen wird: Werte in P1–P14 und `vorbilder.md` nachziehen, Kopien nach
30 Tagen löschen lassen (`workdir.py sweep`), Messwerte bleiben in `ergebnis/`. Neue Konflikte in Abschnitt 6
eintragen. Changelog: v1.0 (18.11.2026) Erstfassung.
