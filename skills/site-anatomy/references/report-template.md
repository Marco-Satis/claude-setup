# Vorlage BERICHT.md (site-anatomy 0.2.1)

Ablage: `<WD>/ergebnis/BERICHT.md`. Jeder der 22 Teile ist Pflicht. Fehlt ein Wert, steht dort
„nicht erhoben: <Grund>“ — nie eine leere Überschrift, nie ein geschätzter Wert mit `[M]` oder `[T]`.
Jede Aussage trägt eine Kennzeichnung: `[M]` gemessen (capture/measure) · `[T]` Werkzeug
(designlang, axe) · `[V]` Vision (Kachel angesehen, Dateiname nennen) · `[E]` Urteil mit Beleg.
Jeder Zahlenwert nennt seine Quelle als `Datei:JSON-Pfad`, relativ zum WD, z. B.
`ergebnis/design.json:[0].typography.system.ratio.value`. Jeder Fachbegriff wird beim ersten
Auftreten in einem Satz Alltagssprache erklärt.

Kürzel in den Quellenzeilen unten (im Bericht selbst den vollen Pfad schreiben):
`cap` = `kopien/capture.json` · `des[i]` = `ergebnis/design.json`, Eintrag mit `meta.url` = Seiten-URL
(`[0]` ist meist die Startseite, an `meta.url` prüfen) · `legal` = `ergebnis/legal.json` ·
`a11y` = `ergebnis/a11y.json` · `img` = `ergebnis/images.json` · `toi` = `ergebnis/text_on_image.json`.

`kopien/` wird zum Löschdatum gelöscht. Was der Bericht aus `cap`, `kopien/pages/` oder
`kopien/design_texte.json` braucht, steht danach nur noch im Bericht. Der Bericht wird nie
veröffentlicht; teilbar ist nur `BERICHT_teilbar.md` (ohne Teil 3, ohne wörtliche Zitate, ohne
Bilder), und die entsteht nur auf des Nutzers Wunsch, den Bericht zu teilen.

## Inhalt

1. Steckbrief · 2. Rechts-Check · 3. Screenshot-Satz · 4. Design-Tokens · 5. Farbe ·
6. Typografie · 7. Layout · 8. Komponenten · 9. Bildsprache · 10. Seitenstruktur ·
11. Inhalte · 12. Motion · 13. Responsive · 14. Barrierefreiheit · 15. Performance · 16. SEO ·
17. Vertrauen und Conversion · 18. Technik · 19. Konsistenz · 20. Prinzipien · 21. Transfer-Plan ·
22. Grenzen der Analyse

---

## 1. Steckbrief
URL-Liste mit Weiterleitungsziel, Zeitpunkt, tatsächliche Laufzeit, Viewports, Hell/Dunkel,
Consent-Zustand je Seite, erkannte A/B-Test-Skripte, Werkzeugversionen.
Nur bei `no_reject_button_found` oder `reject_failed`: „Banner blieb offen auf <Seiten>;
Screenshots können überdeckt sein; CTA- und Token-Werte können Banner-Elemente enthalten.“ Bei
`rejected` und `no_banner` (kein Banner gefunden) kein Banner-Satz. Fehlalarm (laut `bannerText`
und Kachel kein Cookie-Banner): statt des Satzes ein Vermerk in Teil 22.
Quelle: `cap` `meta.startUrl`, `meta.capturedAt`, `meta.viewports`, `meta.schemes`, `pages[].url`,
`pages[].consent` (und `consentDark`, falls vorhanden), `pages[].ab`; `legal` `final_url`;
Laufzeit aus den `date +%s`-Zeilen von Phase 1/2. Versionen: `ergebnis/versions.json` (node,
playwright, designlang, @axe-core/playwright, axe-core, colorthief, sharp, chromium, axeEngine);
ersatzweise `cap` `meta.chromium`, `meta.playwright`, `meta.tools`. Vorsicht bei Läufen von 0.1.0:
dort enthielt `meta.playwright` die Chromium-Version. `tokens.dtcg.json` `$metadata.version` ist
die Format-Version, nicht die designlang-Version.

## 2. Rechts-Check
Je geprüfte URL eine Zeile: URL, `final_url`, `reserved`, Fund, `crawl_delay`. Übersprungene Seiten
(Rechts-Check) und blockierte Seiten mit Grund. Impressum/AGB-Fundstellen. Speicherort der Kopien.
**Löschdatum**; eine Verlängerung nur mit neuem Datum und Grund an dieser Stelle.
Satz: „Fotos, Texte, Logo und Marke der Vorlage werden nicht übernommen.“
Quelle: `legal` (Liste; die Start-URL steht zweimal darin — Schritt 2 und Neuprüfung in capture —,
je URL den letzten Eintrag nehmen: `verdict`, `final_url`, `redirects`, `crawl_delay`,
`findings[]`); `cap` `skipped[]`, `blocked[]`, `aborted`, `stopped`; bei Freigabe trotz Vorbehalt:
des Nutzers Ja und Grund. Impressum/AGB aus dem `legal`-Fund `check: Impressum/AGB` (`seiten[]`,
`hinweise[]` mit Ausschnitt); fehlt er, „nicht geprüft“. Ein Vorbehalt in natürlicher Sprache
genügt nach OLG Hamburg 5 U 104/24 möglicherweise nicht; das Urteil ist nicht rechtskräftig,
deshalb wird jeder Fund der Nutzer vorgelegt.
Speicherort: `<WD>/kopien/`, das Session-Transcript und PreCompact-Backups unter
`~/.claude/backups/` — die beiden letzten löscht `sweep` nicht. Für das Transcript den
Projekt-Transcript-Ordner aus `ergebnis/transcript.txt` nennen: Die angesehenen Bilder stecken in
der jsonl dieser Session bzw. bei Subagents unter `<session>/subagents/`; welche Datei genau, ist
aus einer Session heraus nicht sicher bestimmbar, deshalb steht dort der Ordner.
Löschdatum: `<WD>/LOESCHDATUM`.

## 3. Screenshot-Satz
Tabelle Seite × Breite × Schema mit Pfaden. Nur intern, nie in `BERICHT_teilbar.md`.
Quelle: `kopien/shots/<seite>/<breite>_<schema>.png`, Navigations-Hover `nav_hover_<i>.png`.
Nach dem Löschdatum existieren diese Dateien nicht mehr.

## 4. Design-Tokens
Anzahl eindeutiger Werte je Kategorie, Token-Ebenen (Rohwert → Rolle → Komponente) soweit
erkennbar, Benennung der CSS-Variablen. [T]
Quelle: `ergebnis/tokens.dtcg.json` (`primitive`, `semantic`); `des[i]` `variables`, `tokenSources`.
Ein `semantic`-Verweis wie `{primitive.shadow.sh0}` wird nur zitiert, wenn das Ziel in `primitive`
existiert; Schriftfamilien dort können Ersatzwerte sein (`system-ui`), Gegenprobe in `des[i]`.

## 5. Farbe
Palette mit Rollen (primary, secondary, accent, neutrals), Flächenanteil, Kontrastmatrix,
Text auf Bild, Dark Mode.
Quelle: Rollen `des[i]` `colors.primary/secondary/accent/neutrals` [T]. Flächenanteil
`des[i]` `colors.dominance[]` bzw. `colors.all[].areaShare` — das ist der Anteil an der
**CSS-Hintergrundfläche** laut DOM (Bilder und Verläufe zählen nicht), keine Bildschirmpixel;
genau so benennen. Kontrastmatrix `des[i]` `accessibility.pairs`, `accessibility.failingPairs`.
Text auf Bild `toi` (`worstRatio`, `passesAA`). Dark Mode: `des[i]` `darkMode.colors`, falls
vorhanden; sonst „Farbwerte Dark Mode: nicht erhoben“ plus [V] aus `kopien/shots/<seite>/*_dark.png`.
Sind alle Dunkel-Kacheln byte-identisch mit den hellen (md5-Vergleich, `vision-raster.md`
„Vorab 1“): „kein Dark Mode erkennbar (Screenshots identisch)“, ohne Dunkel-Kachel anzusehen.

## 6. Typografie
Familien, Skalenfaktor, Stufenzahl, Gewichte, Zeilenhöhen, Zeilenlänge in Zeichen.
Quelle: `des[i]` `typography.families`, `.scale`, `.weights`, `.lineHeights`; Skalenfaktor
`typography.system.ratio` (`value`, `name`, `fit`, `steps`; `value: null` = „keine regelmäßige
Skala“); Zeilenlänge `typography.system.measure.charsPerLine` — eine Schätzung über rund 0,5 em
Zeichenbreite, nicht gezählt, `confidence` mit nennen; geladene Schriften `cap` `pages[].tech.fonts`.
`typography.families` kann leer sein: dann Schriften nur aus `cap` `pages[].tech.fonts` (geladene
Webfonts); sind beide leer, „nicht erhoben“.
Ladeverhalten der Schrift (font-display, Preload): nicht erhoben.

## 7. Layout
Container-Breite, Spalten, Gutter, Sektionsabstand vs. Komponentenabstand (Verhältnis),
Ausrichtungsachsen, Füllgrad im ersten Bildschirm.
Quelle: `des[i]` `layout.system.container` (`contentWidth`, `gutter`, `fullBleed`),
`layout.system.columns` (ganzes Feld `null` = kein Spaltenraster erkannt; sonst Unterfeld `dominant`),
`layout.system.rhythm.section` / `layout.system.rhythm.ladder` (Sektionsabstand),
`layout.system.gapScale`, `layout.system.density` (= Gutter ÷ Inhaltsbreite) und `spacing.base` /
`spacing.scale` / `spacing.tokens` (Komponentenabstand); Verhältnis =
`layout.system.rhythm.section` ÷ `spacing.base`. `container`, `columns`, `rhythm`, `density` und
`spacing.base` können `null` sein → „nicht erhoben“ (ebenso `colors.primary`/`colors.accent` in Teil 5).
Achsen und Füllgrad [V] aus der Kachel `1280_light` t00 der Startseite.

## 8. Komponenten
Katalog: Navigation, Hero, Karten, Teaser, Formulare, Footer … je mit Varianten.
Quelle: `des[i]` `components`, `componentAnatomy`, `componentClusters` [T]; Ausschnitte nur, falls
`des[i]` `componentScreenshots` gefüllt ist, sonst „nicht erhoben“. Zustände: nur Hover der
Hauptnavigation [V] (`cap` `pages[].nav.hovered[]`, Dateien `nav_hover_<i>.png`). Hover, Fokus und
aktiv anderer Komponenten: nicht erhoben. Fehlerzustände: nicht erhoben (bräuchten
Formulareingaben, die der Skill nicht macht).

## 9. Bildsprache
Bild-Inventar-Tabelle (Ort, Art, Format, Seitenverhältnis, Ausschnitt/object-position, Palette)
plus Bewertung nach `vision-raster.md`: Licht, Farbtemperatur, Motive, Menschen, Komposition,
Behandlung, Konsistenz, Illustration, Icon-Stil, Art Direction je Breite.
Quelle: `cap` `pages[].images[]` (`kind`, `natural`, `shown`, `objectFit`, `objectPosition`,
`sources`) und `img` (`palette`, `dominant`, `aspect`) [M]; Bewertung [V] mit Dateinamen aus
`kopien/tiles/` und `kopien/sheets/`; `des[i]` `imageryStyle` als Werkzeug-Einschätzung [T].

## 10. Seitenstruktur
Navigationsmodell (Megamenü? Tiefe?), Seitenbaum der Hauptnavigation, Klickpfade zu den
3 wichtigsten Aufgaben.
Quelle: `cap` `pages[].nav.tree` (ARIA-Snapshot), `pages[0].navLinks`. Seitenbaum = nur die
Hauptnavigation; Sitemap und tiefere Ebenen: nicht erhoben. Klickpfade sind [E] aus `nav.tree`,
nicht durchgeklickt.

## 11. Inhalte
Gliederung H1–H3, Sektions-Dramaturgie der Startseite (Reihenfolge und Zweck jeder Sektion),
Headline-Formeln, CTA-Verben, Tonalität auf den 4 NN/g-Achsen, Microcopy-Beispiele (kurz zitiert,
höchstens ein Satz je Zitat; in `BERICHT_teilbar.md` nur das Muster).
Quelle: `kopien/pages/<seite>/text.md`, `cap` `pages[].headings`, `pages[].ctas`; `des[i]` `voice`
(`ctaVerbs`, `buttonPatterns`) [T]; `kopien/design_texte.json` (`path` + `value`) für Felder, die in
`des[i]` `-> kopien/design_texte.json` zeigen (z. B. `voice.sampleHeadings`, `voice.buttonPatterns`),
kurz zitiert; Dramaturgie und Tonalität [E] mit Beleg.

## 12. Motion
Dauern, Easing-Kurven, welche Elemente sich bewegen.
Quelle: `des[i]` `motion.durations`, `.easings`, `.springs`, `.feel` und `animations` [T]; bewegte
Elemente nur [V], soweit Screenshots sie zeigen. `animations` zählt `transition: all` (den
Browser-Standardwert) als Bewegung — Anteile bewegter Elemente sind eine obere Schranke und werden
so benannt. Verhalten bei „Bewegung reduzieren“: nicht erhoben.

## 13. Responsive
Breakpoints × Umbau-Muster (Spalten → gestapelt, Navigation → Burger, Bildausschnitt wechselt …).
Quelle: `des[i]` `breakpoints` [T]; Vergleich der Kacheln 390 / 768 / 1280 / 1920 [V];
Art Direction über `<picture>` aus `cap` `pages[].images[].sources`.

## 14. Barrierefreiheit
axe-Verstöße nach Schwere, axe-Incompletes, Text-auf-Bild-Ergebnis, Bezug WCAG 2.2 AA.
Quelle: `a11y` `violations[]` (nach `impact`), `incomplete[]`; `toi`; `des[i]`
`accessibility.failingPairs`. Seiten ohne axe-Lauf (Eintrag fehlt oder `skipped`) nennen.

## 15. Performance
**Labordaten** [T], ausdrücklich so benannt (Lighthouse, simulierte Drosselung, Erstbesuch mit
Banner; keine Felddaten echter Nutzer). Je Seite und Formfaktor (Handy/Desktop): Punkte
(`perf` `results[].scores`), LCP, CLS, TBT, FCP, Speed Index (`results[].metrics.<id>.display`),
LCP-Element (`results[].lcpElement.selector`), Gewicht je Typ (`results[].resourceSummary`, darin
Schrift = `Font`), Drittanbieter (`results[].thirdPartyEntities`), größte Punkte-Verluste
(`results[].issues`, höchstens 5 nennen). Laienerklärung je Kennzahl in einem Satz (LCP = wann das
größte sichtbare Element fertig ist; CLS = wie stark die Seite beim Laden springt; TBT = wie lange
sie auf Eingaben nicht reagiert). Fehlt `perf.json` oder ein Lauf (`errors[]`): „nicht erhoben: <Grund>“.
Bildgewicht der heruntergeladenen Bilder zusätzlich aus `img` `bytes`.

## 16. SEO
Title, Description, Canonical, Open Graph, JSON-LD-Typen, Sprache.
Quelle: `cap` `pages[].meta` (`title`, `description`, `canonical`, `og`, `jsonLdTypes`, `lang`);
`des[i]` `seo` [T]. hreflang, robots-Meta und Crawlbarkeit: nicht erhoben.

## 17. Vertrauen und Conversion
Preisangaben, „mtl.“-Hinweise, Fußnoten, Siegel, Formularlänge, CTA-Dichte, Glaubwürdigkeit nach den
4 NN/g-Faktoren, Dark-Pattern-Notizen.
Quelle: `cap` `pages[].trust` (`prices`, `monthly`, `footnoteMarkers`, `sealAlts`, `forms`);
CTA-Dichte = Anzahl `pages[].ctas[]` mit `rect.y` < 900 (erster Bildschirm bei 1280×900);
Glaubwürdigkeit und Dark Patterns [E] mit Beleg. Steht der Consent auf `no_reject_button_found`
oder `reject_failed`, Banner-Knöpfe aus der CTA-Zählung herausnehmen und das sagen.

## 18. Technik
Framework-Hinweise, Tag-Manager, CMS, Schriftquellen, Drittanbieter-Hosts — jeweils mit Fundstelle
und Konfidenz (Fingerprints sind Heuristik).
Quelle: `cap` `pages[].tech` (`generator`, `globals`, `frameworkHints`, `scriptHosts`, `fonts`);
`des[i]` `stack`, `stackIntel`, `componentLibrary` [T].

## 19. Konsistenz
Abweichungen zwischen den erfassten Seiten (Farben, Abstände, Komponenten-Varianten).
Quelle: Vergleich der `des[i]` untereinander (`colors.all`, `spacing.scale`, `components`);
Kacheln [V].

## 20. Prinzipien
„Warum wirkt die Seite hochwertig?“ — 5–10 Prinzipien, jedes mit **Wert und Quelle**
(`Datei:JSON-Pfad`, bei [V] der Kachel-Dateiname). Ein Prinzip ohne Quelle wird gestrichen.

## 21. Transfer-Plan
- eigene Tokens `ergebnis/own-tokens.dtcg.json` als Tabelle: Token | Wert | Herleitung
  (übernommenes Verhältnis mit Quelle, neuer Wert). Umgerechnet wird auf die eigene Basis:
  Abstände = Vielfache der eigenen Abstandsbasis (Vorlagenwert ÷ `des[0]` `spacing.base` × eigene
  Basis, Default 4 px oder 8 px), Schriftgrößen = eigene Fließtextgröße × Skalenfaktor
  (`typography.system.ratio.value`, je Stufe einmal mehr)
- Ausgabe von `brand_distance.mjs` wörtlich (JSON `rows`) plus Exit-Code; ΔE ≥ 20 zu jeder
  Markenfarbe der Vorlage (`--brand` nur mit Werten ≠ `null`: `des[0]` `colors.primary.hex`,
  `colors.accent.hex`, bekannte Markenfarbe; sind beide `null`: Ersatzregel aus SKILL Phase 5).
  Fehlt die Ausgabe ohne diesen Vermerk, gilt die Prüfung als nicht bestanden
- Bild-Briefing für eigene Fotos/Illustrationen
- Tonalitätsprofil
- **Nicht übernehmen:** Logo, Markenzeichen, Hausschrift, Fotos, Illustrationen, Texte, Slogans,
  geschützte Markenfarben, eine Gesamtanmutung, die Herkunft von der Vorlage suggeriert
- Sektionsplan für `design-html`; falls geschrieben: Pfade von `<ziel>/DESIGN.md` und
  `<ziel>/designs/ceo-plans/<domain>-sektionsplan.md`
- falls Phase 6 lief: Vergleichstabelle Kennzahl | Quelle | Vorlage | eigen | Δ | Toleranz | ok

## 22. Grenzen der Analyse
Alles, was oben „nicht erhoben“ ist, gesammelt mit Grund. Dazu: Werkzeugfehler aus
`ergebnis/measure_errors.json` und `ergebnis/capture_errors.json`; per Rechts-Check übersprungene
und blockierte Seiten; offener Consent-Banner (Satz aus Teil 1, nur bei `no_reject_button_found`
oder `reject_failed`); Kacheln oder Kontaktbögen = 0; „kein Dark Mode erkennbar (Screenshots
identisch)“, falls zutreffend; Bewegungsanteile als obere Schranke (`transition: all`); fehlende
Lösch-Routine (`ROUTINE_FEHLT` aus Schritt 0); A/B-Varianten, Personalisierung, Login-Bereiche,
Bot-Schutz.
