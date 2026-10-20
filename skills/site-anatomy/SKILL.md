---
name: site-anatomy
version: 0.3.0
last-reviewed: 2026-10-20
description: Use this skill whenever der Nutzer wants someone else's public website or domain analysed, read out, taken apart, benchmarked or used as a model for his own design — e.g. "analysiere telekom.de", "wie ist die Seite von X aufgebaut", "Design-System/Tokens einer Website auslesen", "meine Seite soll so hochwertig werden wie die von X", "Konkurrenzseite zerlegen", "Firmenseite scannen und im eigenen Design nachbauen" — whether he asks about colours, fonts, design tokens, layout, imagery, texts, tone, navigation or page structure, and even when no skill is named. Not for his own code or UI (impeccable, ui-critique, design-taste-frontend), building pages (design-html), security scans (security-audit/cso), or technical questions about how a site works under the hood — JavaScript bundles, API calls, network requests, search backends (leanrea).
when_to_use: webseite analysieren, website auslesen, seite nachbauen eigenes design, wie ist die seite gebaut, design einer firma verstehen, design system einer fremden website auslesen, design tokens einer website, bildsprache analysieren, website inhalte analysieren, landingpage zerlegen, konkurrenz website design, warum wirkt die seite hochwertig, referenz website, inspiration von website, site teardown, website anatomy
argument-hint: "<url> [--pages N] [--own-tokens <pfad>] [--ziel <projektpfad>] — eine URL je Lauf; Default Startseite + bis 5 Seiten aus der Hauptnavigation"
allowed-tools: Read Grep Glob Bash Write Edit
userInvocable: true
---

# site-anatomy — Fremde Website verstehen und aufs eigene Design übertragen

Zweck: Eine öffentliche Website in allen Dimensionen vermessen (Design-System, Layout, Bildsprache,
Inhalte, Struktur, Technik), erklären **warum** sie hochwertig wirkt, und daraus einen
Transfer-Plan für des Nutzers **eigenes** Design ableiten. Ergebnis ist ein Bericht plus eigene
Token-Vorschläge — nie eine Kopie.

der Nutzer kennt die Fachbegriffe nicht. Bericht **und** Chat erklären jeden Fachbegriff beim ersten
Auftreten in einem Satz Alltagssprache.

## Werkzeugkette (Stand 0.2.1)

Skripte liegen unter `~/.claude/skills/site-anatomy/scripts/` und werden **immer mit diesem
absoluten Pfad** aufgerufen. Grund: Der Skill läuft im cwd von des Nutzers Projekt; ein relativer Pfad
scheitert dort, und Python meldet „Datei nicht gefunden" mit Exit 2 — demselben Code wie „Vorbehalt".
Python-Skripte immer mit `python3 -I` starten (keine Module aus dem cwd).

| Werkzeug | Aufgabe |
|---|---|
| `workdir.py` (stdlib) | Arbeitsordner anlegen (`init`), prüfen (`check`), abgelaufene Kopien löschen (`sweep`) |
| `legal_check.py` (stdlib) | robots.txt, tdmrep.json, Header und Meta je URL; Ergebnis nach `ergebnis/legal.json` |
| `capture.mjs` + playwright 1.61.1 (chromium-1228) | Erfassung: Screenshots, Volltext, Überschriften, Bild-Inventar, Navigation, CTAs; prüft jede Unterseite selbst per `legal_check.py` |
| `measure.mjs` mit designlang 13.3.2, @axe-core/playwright 4.14.0, colorthief 3.5.0 + sharp 0.35.5 | Tokens, Typo, Layout, Motion, Komponenten, Barrierefreiheit, Bildpaletten, Text auf Bild |
| `tile.sh` (ffmpeg 4.4; AVIF über sharp) | Screenshot-Kacheln und Kontaktbögen für die Vision-Analyse |
| `brand_distance.mjs` (ohne Abhängigkeiten) | Farbabstand ΔE (CIEDE2000) eigene Farben ↔ Markenfarben der Vorlage |
| Claude-Vision (Read-Tool auf PNG) | Bildsprache, Illustration, Icon-Stil, Gesamtwirkung |

Die Node-Pakete liegen isoliert unter `~/.local/share/site-anatomy/` (gepinnt, `install/package.json`
+ Lockfile). Kein `npx`, keine `@latest`-Aufrufe, keine bezahlten APIs. Fehlt
`~/.local/share/site-anatomy/node_modules`: abbrechen und der Nutzer
`~/.claude/skills/site-anatomy/install/install.sh` zur Freigabe vorlegen. Nicht selbst installieren.
Installiert ist die Kette nur auf **netcup** (Stand 2026-10-20). Läuft die Session auf dem PC
(Windows), keine Installation vorschlagen, sondern den Lauf in einer netcup-Session empfehlen.

## Abdeckung 0.2.1 — was die Skripte NICHT liefern

Diese Werte stehen im Bericht als „nicht erhoben: <Grund>", nie geschätzt und nie mit `[M]`/`[T]`:

- Zustände von Komponenten (Hover, Fokus, aktiv, Fehler). Erfasst wird nur Hover in der
  Hauptnavigation (`nav_hover_<i>.png`). Fehlerzustände bräuchten Formulareingaben — verboten.
- Ausschnitte einzelner Komponenten (nur falls `design.json` `componentScreenshots` gefüllt ist).
- Verhalten bei „Bewegung reduzieren" (`prefers-reduced-motion`).
- Seitenbaum jenseits der Hauptnavigation, Sitemap, echte Klickpfade (nur Urteil `[E]` aus `nav.tree`).
- Dark-Mode-Farbwerte, solange `design.json` kein `darkMode` enthält; dann nur `[V]` aus `*_dark.png`.
- **Felddaten** echter Nutzer (CrUX). `perf.mjs` liefert nur **Labordaten** (Lighthouse, simulierte
  Drosselung, Erstbesuch mit offenem Consent-Banner) und wird genau so benannt.
- Bildgewicht aus `images.json` nur für die heruntergeladenen Bilder (höchstens `--max-images`);
  das Gesamtgewicht je Ressourcentyp liefert `perf.json` `resourceSummary`.
- hreflang, robots-Meta, Crawlbarkeit.
- Juristische Prüfung von Impressum/AGB. `legal_check.py --legal-pages` sucht dort nur nach
  TDM-Formulierungen (bis zu 3 Seiten) und legt Funde der Nutzer vor.
- Flächenanteile in Bildschirmpixeln. designlang `areaShare` ist der Anteil an der
  **CSS-Hintergrundfläche** laut DOM (Bilder und Verläufe zählen nicht) und wird genau so benannt.

Werkzeug-Eigenheiten (gemessen mit designlang 13.3.2) — so lesen, nicht anders:

- `tokens.dtcg.json` `$metadata.version` ist die Version des Token-**Formats** (gemessen `7.0.0`),
  nicht die designlang-Version; die steht in `ergebnis/versions.json`.
- `semantic`-Tokens in `tokens.dtcg.json` können auf `primitive`-Tokens zeigen, die es nicht gibt
  (gemessen `{primitive.shadow.sh0}` bei leerem `primitive.shadow`), und Ersatzwerte tragen
  (gemessen `fontFamily: system-ui` bei `font-family: sans-serif` im CSS). Nur zitieren, wenn das
  Ziel existiert bzw. der Wert in `design.json` steht.
- `animations` zählt `transition: all` (Browser-Standardwert) als Bewegung: Eine Seite ganz ohne
  CSS-Übergang ergab `animations.transitions: ["all"]`. Bewegungsanteile sind damit eine **obere
  Schranke** und werden so benannt.
- `typography.families` kann leer sein. Dann Schriften aus `kopien/capture.json:pages[].tech.fonts`
  (nur geladene Webfonts); sind beide leer: „nicht erhoben".

## Arbeitsordner und Löschpflicht

`WD = ~/site-anatomy/<domain>_<YYYY-MM-DD>[_n]/` — bewusst **nicht** unter `~/projects` (synct per
Syncthing auf den PC). Aufbau:

- `WD/LOESCHDATUM`, `WD/meta.json` — Löschdatum (Default heute + 30 Tage), URL, Anlagedatum.
- `WD/kopien/` — fremde Werke: `capture.json`, `shots/`, `pages/<seite>/text.md`, `images/`,
  `tiles/`, `sheets/`, `design_texte.json` (fremde Texte, die measure.mjs aus `design.json`
  verschiebt; das Feld in `design.json` zeigt dann `-> kopien/design_texte.json`). Wird zum
  Löschdatum gelöscht.
- `WD/ergebnis/` — bleibt: `legal.json`, `design.json`, `tokens.dtcg.json`, `a11y.json`,
  `images.json` (nur Paletten/Metadaten), `text_on_image.json`, `measure_errors.json`,
  `capture_errors.json`, `versions.json`, `BERICHT.md`, `own-tokens.dtcg.json`, `transcript.txt`.

Grund: § 44b Abs. 2 UrhG verlangt, Vervielfältigungen zu löschen, sobald die Analyse sie nicht mehr
braucht. Messwerte, Regeln und eigene Entwürfe sind keine Werkkopien und bleiben. **Ausnahme zur
Projektregel „archivieren statt löschen":** `kopien/` wird gelöscht, nicht archiviert.

## Ablauf

### Schritt 0 — Abgelaufene Kopien löschen

```bash
python3 -I ~/.claude/skills/site-anatomy/scripts/workdir.py sweep
crontab -l 2>/dev/null | grep -q site_anatomy_sweep && echo ROUTINE_OK || echo ROUTINE_FEHLT
```

`sweep` löscht in jedem WD mit abgelaufenem `LOESCHDATUM` nur `kopien/` und gibt einen JSON-Bericht
aus. Gelöschte Ordner in einer Zeile an der Nutzer melden. `ROUTINE_FEHLT`: Die Löschung hängt dann
allein am nächsten Skill-Aufruf → in Teil 22 vermerken und im Chat unter „Hinweise" (Teil 4 der
Chat-Ausgabe, siehe Output-Format) melden, einmal je Session.

### Schritt 1 — Arbeitsordner anlegen

```bash
python3 -I ~/.claude/skills/site-anatomy/scripts/workdir.py init "<url>"
```

Die einzige stdout-Zeile ist der WD-Pfad. Ihn wörtlich in alle folgenden Aufrufe einsetzen (jeder
Bash-Aufruf ist eine neue Shell). `--days N` ändert die Frist. Nur für Tests ersetzt die
Umgebungsvariable `SITE_ANATOMY_WORKROOT` den Ordner `~/site-anatomy`.

### Schritt 2 — Rechts-Check der Start-URL AUSFÜHREN

```bash
python3 -I ~/.claude/skills/site-anatomy/scripts/legal_check.py "<url>" --legal-pages --out "<WD>/ergebnis/legal.json"; echo "exit=$?"
```

Ausgewertet werden Exit-Code **und** das JSON auf stdout (`verdict`, `reserved`, `unclear`, `findings[]`):

| Ergebnis | Bedeutung | Handlung |
|---|---|---|
| Exit 0, `verdict: frei` | kein maschinenlesbarer Vorbehalt | weiter |
| Exit 2 mit JSON, `verdict: vorbehalt` | robots.txt (auch KI-Crawler-Gruppen), tdmrep.json, Header/Meta `tdm-reservation`, `noai` | **stoppen**, Fundstelle aus `findings[]` melden |
| Exit 2 mit JSON, `verdict: unklar` | robots.txt 5xx/429, kaputte tdmrep.json, Netzfehler | **stoppen**, melden; später erneut versuchen |
| Exit 2 **ohne** JSON auf stdout | Aufruffehler (z. B. Skriptpfad), kein Vorbehalt | Aufruf korrigieren |
| Exit 3 mit JSON (`verdict: nicht erreichbar`/`ungueltig`) | nicht erreichbar oder ungültige URL | melden, nicht raten |
| Exit 3 **ohne** JSON | Aufruffehler, z. B. `--out` außerhalb der Workroot (Testvariable `SITE_ANATOMY_WORKROOT` nur in einer früheren Shell gesetzt) | Aufruf korrigieren |

Nach einem Stopp wird die Startseite nur mit des Nutzers **ausdrücklichem Ja** erfasst (z. B. weil eine
Erlaubnis des Rechteinhabers vorliegt); dann bekommt capture.mjs `--start-freigegeben`, und Ja plus
Grund stehen in Teil 2. Unterseiten mit Vorbehalt überspringt capture.mjs immer. Ein Stopp ist eine
eigene Meldung, keine Rückfrage zu den Argumenten.

Außerdem aus dem JSON: `final_url` (Weiterleitungsziel) im Bericht nennen. `crawl_delay` hält
capture.mjs selbst ein (Abstand = max(1 s, crawl_delay)); ab 10 s die Dauer-Schätzung entsprechend
erhöhen. Der Fund `check: Impressum/AGB` mit nicht leeren `hinweise[]` geht an der Nutzer (Ausschnitt +
URL); er sperrt nicht automatisch.

### Schritt 3 — Argumente auswerten, höchstens EINE gebündelte Rückfrage

- **URL:** eine je Lauf. Mehrere URLs → nacheinander je ein eigener Lauf mit eigenem WD.
- **`--pages N`:** weitere Seiten aus der Hauptnavigation, Default 5, höchstens 19.
- **`--own-tokens <pfad>`:** DTCG-JSON mit mindestens `color.brand.primary.$value` und
  `font.family.base.$value`. Prüfen:
  `python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); d["color"]["brand"]["primary"]["$value"]; d["font"]["family"]["base"]["$value"]; print("ok")' "<pfad>"`
  Kein `ok` → Datei fehlt oder ist ungültig, das gehört in die Rückfrage.
- **`--ziel <projektpfad>`:** Projekt, in dem später `design-html` baut (nur für Phase 6).

Fehlt `--own-tokens` oder `--ziel`: **eine** Nachricht mit beiden Fragen — „Hast du schon Farben und
Schrift festgelegt? Wenn nein, schlage ich welche vor." und „In welchem Projektordner soll später
gebaut werden? ‚Noch keins' ist in Ordnung." Danach keine weitere Rückfrage zu den Argumenten.
Stopps durch Rechts-Check, fehlende Werkzeugkette oder Blockade sind eigene Meldungen.

Vor Phase 1 eine Zeile an der Nutzer: höchstens (1 + N) Seiten, höchstens (1 + N) × 8 Screenshots
(2 Schemata × 4 Breiten, dazu Hover-Bilder der Navigation; welche Unterseiten der Rechts-Check
überspringt, zeigt erst capture.mjs) und Dauer als **Schätzwert** „ca. 30 s bis 3 min je Seite"
(lokal gemessen 25–30 s; die echte Dauer kommt in Teil 1).

### Phase 1 — Erfassen

```bash
date +%s; node ~/.claude/skills/site-anatomy/scripts/capture.mjs "<url>" --out "<WD>" --pages N; echo "exit=$?"; date +%s
```

Das Skript prüft **jede** Seite, auch die Startseite erneut, vor dem Besuch per `legal_check.py`
(Ergebnis an `ergebnis/legal.json` angehängt; Vorbehalt → `skipped[]`), hält den Abstand ein, lehnt
Cookie-Banner nur ab („nur notwendige / ablehnen"), fotografiert 390 / 768 / 1280 / 1920 px hell und
dunkel, liest Volltext, Überschriften (inkl. Shadow DOM), Bild-Inventar, Navigation (`ariaSnapshot`,
Hover), CTAs, Vertrauens- und Preis-Muster, A/B-Skripte und Tech-Hinweise. Es schreibt
`kopien/capture.json` nach jeder Seite neu; Fehler einzelner Seiten stehen in
`ergebnis/capture_errors.json`, der Lauf geht weiter. Seiten mit HTTP 401/403/429/503 oder Captcha
werden nicht erfasst (`blocked[]`); nach 429/503 hört es ganz auf (`stopped`).

| Exit | Handlung |
|---|---|
| 0 | Startseite erfasst → weiter |
| 1 | Startseite technisch gescheitert → `capture_errors.json` lesen, der Nutzer melden |
| 2 | Startseite Vorbehalt/unklar (Rechts-Check hat sich seit Schritt 2 geändert) → wie Schritt 2 |
| 3 | Aufruf/WD ungültig oder Startseite nicht erreichbar → Aufruf prüfen bzw. melden |
| 4 | Werkzeugkette fehlt → Installation vorlegen |
| 5 | Startseite blockiert → abbrechen, der Nutzer melden. Kein erneuter Versuch, auch nicht nach Retry-After |

Danach `capture.json` prüfen: `pages[]`, `skipped[]`, `blocked[]`, `aborted`, `stopped`.
Übersprungene und blockierte Seiten kommen mit Grund in Teil 2 und Teil 22.

**Consent:** `pages[].consent.state` (bzw. `consentDark`, falls vorhanden) ist `rejected`
(abgelehnt), `no_banner` (kein Banner gefunden), `no_reject_button_found` (Banner ohne
Ablehnen-Knopf) oder `reject_failed` (Ablehnen wirkte nicht). Bei `rejected` und `no_banner` kein
Banner-Satz. Bei `no_reject_button_found` und `reject_failed`: **keinen anderen Knopf klicken**,
auch nicht „Einstellungen" oder „Akzeptieren". Die Erfassung läuft ohne Einwilligung weiter. In
Teil 1 und Teil 22 steht dann: „Banner blieb offen auf <Seiten>; Screenshots können überdeckt
sein; CTA- und Token-Werte können Banner-Elemente enthalten." Im Chat kommt das unter „Hinweise".
Vorher `bannerText`/`bannerSelector` lesen und die Kachel `<seite>_1280_light_t00.png` ansehen: Ist
es erkennbar kein Cookie-Banner (z. B. Newsletter- oder Chat-Fenster), statt des Satzes „Fehlalarm
der Banner-Erkennung: <bannerText>" in Teil 22. Steht `bannerCheck` im Zustand, war die Prüfung
selbst gestört — dann den Satz schreiben.

### Phase 2 — Messen

```bash
node ~/.claude/skills/site-anatomy/scripts/measure.mjs "<WD>"; echo "exit=$?"
```

Schreibt nach `ergebnis/`: `design.json` + `tokens.dtcg.json` (designlang), `a11y.json` (axe:
`violations` **und** `incomplete`), `images.json`, `text_on_image.json` (Kontrast von Text über Bild
per Pixelanalyse — axe kann das nicht), `measure_errors.json`, `versions.json`. Bilder landen in
`kopien/images/`. Exit 0 fertig · 3 WD ungültig · 4 Werkzeugkette fehlt · 5 Zielseite blockt jetzt
(Teilergebnis ist geschrieben) → nicht wiederholen, der Nutzer melden, mit dem Teilergebnis weiter.
Jeder Eintrag in `measure_errors.json` kommt in Teil 22, nichts wird stillschweigend weggelassen.

### Phase 2b — Kacheln und Kontaktbögen (erst NACH measure.mjs)

```bash
bash ~/.claude/skills/site-anatomy/scripts/tile.sh "<WD>"
```

Argument ist der **WD**, nicht `kopien/shots`. Erst nach measure.mjs, weil die Kontaktbögen aus
`kopien/images/` entstehen und measure.mjs diesen Ordner füllt. Ausgabe „Kacheln: N,
Kontaktboegen: M" prüfen. N = 0 oder M = 0 trotz Bildern in `images.json` → Teil 22.

### Phase 2c — Ladezeit (Lighthouse)

```bash
node ~/.claude/skills/site-anatomy/scripts/perf.mjs "<WD>"; echo "exit=$?"
```

Misst die Startseite zweimal (Handy gedrosselt, Desktop) mit Lighthouse 13.5.0 auf dem
Playwright-Chromium: Punkte je Kategorie, Core Web Vitals (LCP, CLS, TBT, FCP, Speed Index),
LCP-Element, Gewicht je Ressourcentyp, Drittanbieter, Punkte-Verluste. `--pages N` misst N weitere
erfasste Seiten (höchstens 4; je Seite ca. 15–60 s). Nur Seiten aus `capture.json` `pages[]`, also
schon rechtlich geprüft. Schreibt `ergebnis/perf.json` (Kennzahlen, keine fremden Texte) und den
vollen Bericht nach `kopien/lighthouse/` (enthält Screenshots der Seite). Exit 0 fertig · 3 WD
ungültig · 4 Werkzeugkette fehlt · 5 Seite blockt → nicht wiederholen, melden, Teilergebnis nutzen.

### Phase 3 — Sehen (Vision)

Kacheln (`kopien/tiles/`) und Kontaktbögen (`kopien/sheets/`) mit dem Read-Tool ansehen und nach
`references/vision-raster.md` bewerten. Jede Vision-Aussage `[V]`, mit Dateinamen, und wo möglich
gegen Messwerte prüfen (Palette aus `ergebnis/images.json`, Seitenverhältnisse aus
`kopien/capture.json`). Widerspruch → benennen.

Jedes angesehene Bild landet base64-kodiert im Session-Transcript und in PreCompact-Backups
(`~/.claude/backups/`), also außerhalb von `kopien/`, und `sweep` erreicht es dort nicht. Deshalb
nur so viele Kacheln ansehen, wie das Raster braucht: vorher Hell- und Dunkel-Kacheln per `md5sum`
vergleichen (Schritt „Hell/Dunkel vergleichen" in `references/vision-raster.md`); byte-identische
Dunkel-Kacheln werden nicht angesehen. Vor der ersten Kachel den Transcript-Ordner des Projekts
festhalten:

```bash
echo "$HOME/.claude/projects/$(pwd | sed 's#[^A-Za-z0-9]#-#g')/" > "<WD>/ergebnis/transcript.txt"
```

Die angesehenen Bilder stecken in der jsonl dieser Session bzw. bei Subagents unter
`<session>/subagents/`. Welche Datei genau, ist aus einer Session heraus nicht sicher bestimmbar,
deshalb wird der Ordner genannt.

### Phase 4 — Verstehen (Inhalte und Struktur)

Aus `kopien/pages/<seite>/text.md`, `capture.json` (`headings`, `ctas`, `nav.tree`) und
`kopien/design_texte.json` (Überschriften-, Button- und Titeltexte aus designlang; Einträge
`path` + `value`; kurz zitieren, höchstens ein Satz je Zitat):
Sektions-Dramaturgie der Startseite, Headline-Muster, CTA-Verben, Tonalität auf den 4 Achsen der
Nielsen Norman Group (formell–locker, ernst–witzig, respektvoll–respektlos, sachlich–enthusiastisch),
Vertrauenselemente, Dark-Pattern-Hinweise, Seitenstruktur. Kennzeichnung `[E]` (Urteil) mit Beleg.

### Phase 5 — Destillat und Transfer

1. **Prinzipien:** „Warum wirkt die Seite hochwertig?" — 5–10 Prinzipien, jedes mit **Wert und
   Quelle** als `Datei:JSON-Pfad` (bei `[V]` der Kachel-Dateiname). Beispiel: „Akzent-Cluster hat
   3 % der Hintergrundfläche (`ergebnis/design.json:[0].colors.all[].areaShare`)". Kein Prinzip
   ohne Quelle.
2. **Eigene Tokens** `ergebnis/own-tokens.dtcg.json` — Verhältnisse übernehmen, Werte neu setzen:

   ```json
   {
     "color": {
       "brand":   { "primary": { "$type": "color", "$value": "#…" }, "accent": { "$type": "color", "$value": "#…" } },
       "text":    { "default": { "$type": "color", "$value": "#…" } },
       "surface": { "default": { "$type": "color", "$value": "#…" } }
     },
     "font": {
       "family": { "base": { "$type": "fontFamily", "$value": "…" } },
       "size":   { "<stufe>": { "$type": "dimension", "$value": "…px" } }
     },
     "space": { "<stufe>": { "$type": "dimension", "$value": "…px" } }
   }
   ```

   „Umgerechnet auf die eigene Basis" heißt: **Abstände** = Vielfache der eigenen Abstandsbasis,
   **Schriftgrößen** = eigene Fließtextgröße × Skalenfaktor.
   - `font.size`: so viele Stufen wie die Vorlage (`design.json:[0].typography.system.ratio.steps`),
     Faktor `[0].typography.system.ratio.value` (Name in `[0].typography.system.ratio.name`).
     Stufe n = eigene Fließtextgröße × Faktorⁿ. Bei `value: null`: „keine regelmäßige Skala",
     Stufen einzeln aus `[0].typography.scale` als Vielfache der Vorlagen-Fließtextgröße herleiten
     und das sagen.
   - `space`: Verhältnisse aus `[0].layout.system.rhythm.ladder` und `[0].spacing.scale` (bzw.
     `[0].spacing.tokens`): jeden Wert durch `[0].spacing.base` teilen und mit der eigenen
     Abstandsbasis malnehmen (Default 4 px oder 8 px, die gewählte nennen). Beispiel: Basis 4,
     Skala 12/32/64 → Faktoren 3/8/16 → bei eigener Basis 8: 24/64/128 px. `spacing.base` oder
     `layout.system.rhythm` `null` → „nicht erhoben" für diesen Teil, nicht raten.
   - Farben und Schrift: aus `--own-tokens` wörtlich übernehmen; sonst eigene Vorschläge.
   - Danach prüfen: `python3 -I -m json.tool "<WD>/ergebnis/own-tokens.dtcg.json" >/dev/null && echo ok`.
3. **Eigenes Bild-Briefing** (Regeln, keine fremden Fotos), **eigenes Tonalitätsprofil**.
4. **Nicht-übernehmen-Liste:** Logo, Markenzeichen, Hausschrift, Fotos, Illustrationen, Texte,
   Slogans, geschützte Markenfarben (z. B. Telekom-Magenta, DPMA 39552630).
5. **Markenabstand AUSFÜHREN:**

   ```bash
   node ~/.claude/skills/site-anatomy/scripts/brand_distance.mjs --own "<eigene primary>,<eigene accent>" --brand "<Markenfarben, nur Hex-Werte ≠ null>"; echo "exit=$?"
   ```

   In `--brand` nur Werte einsetzen, die nicht `null` sind: `design.json:[0].colors.primary.hex`,
   `[0].colors.accent.hex` und eine bekannte Markenfarbe (z. B. Telekom-Magenta `#e20074`). Fehlt
   accent (`[0].colors.accent` ist `null`), nur primary — plus die bekannte Markenfarbe, falls die
   Marke eine hat. Ein wörtliches `null` in der Liste endet mit Exit 3. Sind primary **und** accent
   `null` und gibt es keine bekannte Markenfarbe: die bis zu drei häufigsten nicht-grauen Farben aus
   `[0].colors.all[]` nehmen (Sättigung über 15 %, nach `count`). Gibt es auch die nicht, entfällt
   der Schritt mit dem Vermerk „kein Markenfarbabstand prüfbar: Vorlage ohne Buntfarbe" in Teil 21.

   Exit 0 = alle ΔE ≥ 20 · Exit 2 = mindestens eine Farbe zu nah → andere Farbe vorschlagen und
   erneut prüfen · Exit 3 = ungültige Eingabe → Werte korrigieren. **Keine JSON-Ausgabe zählt als
   NICHT bestanden.** Die Ausgabe kommt wörtlich in Teil 21. Stammt die zu nahe Farbe aus
   `--own-tokens`, wird sie nicht still ersetzt: der Nutzer den Abstand nennen und einen Ersatz vorschlagen.

### Phase 6 — Übergabe an design-html und Vergleich

Nur mit Zielprojekt (`--ziel` oder Antwort aus Schritt 3). `design-html` liest Tokens aus
`DESIGN.md` im Projekt-Root und den Inhaltsplan aus `designs/ceo-plans/*.md` (dann „plan-driven
mode"); `own-tokens.dtcg.json` kennt es nicht.

1. `<ziel>/DESIGN.md` schreiben. Existiert sie: vorher `cp -a DESIGN.md DESIGN.md.bak.$(date +%s)`.
   Inhalt: Farben (Hex, Rolle), Schriftfamilien und Gewichte, Typo-Skala (px je Stufe),
   Abstandsskala, Radien — alles aus `own-tokens.dtcg.json` — plus Bild-Briefing, Tonalitätsprofil
   und Nicht-übernehmen-Liste. Keine fremden Texte, keine Pfade nach `kopien/`.
2. `<ziel>/designs/ceo-plans/<domain>-sektionsplan.md` schreiben (Backup wie oben, falls vorhanden):
   Sektionen in Reihenfolge, je Zweck, eigener Inhalt, CTA-Verb.
3. Nächster Schritt für der Nutzer: `/design-html` in einer Session mit cwd = Zielprojekt starten
   (design-html prüft relativ zum Projekt-Root) und dort „Skip mockups — plan-driven" wählen.
   Ergebnis: `<ziel>/designs/<screen>-<YYYYMMDD>/finalized.html`.
4. Vergleich, höchstens 3 Runden. Eigenen Build lokal ausliefern (freier Port 18800–18899):
   `nohup python3 -m http.server <port> --bind 127.0.0.1 -d "<ordner von finalized.html>" >/dev/null 2>&1 & echo $!`
   → PID merken. Dann Schritt 1, Schritt 2, Phase 1 (`--pages 0`), Phase 2 und Phase 2b für
   `http://127.0.0.1:<port>/finalized.html` (eigenes WD). Am Ende `kill <PID>`.
5. Tabelle in Teil 21 schreiben, Werte aus beiden WDs:

   | Kennzahl | Quelle | Vorlage | eigen | Δ | Toleranz | ok |
   |---|---|---|---|---|---|---|
   | Typo-Skalenfaktor | `design.json:[0].typography.system.ratio.value` | | | | ±0,05 | |
   | Abstandsrhythmus | `[0].layout.system.rhythm.section` ÷ `[0].spacing.base` | | | | ±15 % | |
   | Akzent-Flächenanteil | `[0].colors.all[]` mit hex = `[0].colors.accent.hex` → `areaShare` | | | | ±50 % relativ | |
   | CTAs im ersten Bildschirm | `capture.json:pages[0].ctas[]` mit `rect.y` < 900 (1280×900) | | | | ±1 | |
   | axe-Verstöße je Schwere | `a11y.json:[0].violations[].impact` (Anzahl) | | | | eigen ≤ Vorlage | |

   Toleranzen: ±0,05 trennt benachbarte Standard-Skalen (1,2 / 1,25 / 1,333); ±15 % liegt knapp
   über der 12-%-Bündelung, mit der designlang Abstände gruppiert; ±50 % weil `areaShare` nur
   CSS-Hintergrundfläche misst und Bilder ignoriert; ±1 weil CTA-Zahlen klein sind; axe darf nicht
   schlechter werden. Fehlt ein Wert auf einer Seite: „nicht vergleichbar", nicht schätzen.
6. Vision-Vergleich Vorlage vs. eigener Build nebeneinander: Ziel „gleichwertig, nicht verwechselbar".
7. Alle Zeilen mit `ok = nein` als Liste an design-html zurückgeben (Refinement-Loop).
8. Danach der Nutzer anbieten, die Kopien sofort zu löschen statt zum Löschdatum. Bei Ja:
   `date -d yesterday +%F > "<WD>/LOESCHDATUM"`, dann Schritt 0 (`sweep`). Verlängern nur mit neuem
   Datum **und** Grund in Teil 2.

## Output-Format

`<WD>/ergebnis/BERICHT.md` nach `references/report-template.md` (22 Teile, Quelle je Wert als
`Datei:JSON-Pfad`, Evidenz-Kennzeichnung `[M]` gemessen · `[T]` Werkzeug · `[V]` Vision · `[E]` Urteil).

`ergebnis/BERICHT_teilbar.md` nur erzeugen, wenn der Nutzer den Bericht teilen will (Regel unter
Constraints) — nie von selbst.

Im Chat drei Pflichtteile in dieser Reihenfolge, danach höchstens ein optionaler vierter, kein
Berichtsdump:
1. **Nächster Schritt** für der Nutzer (eine Zeile).
2. Pfad zu `BERICHT.md`.
3. Die 5 wichtigsten Prinzipien, je ein Satz Alltagssprache mit Zahl; Fachbegriff in Klammern erklärt.
4. *Optional* **Hinweise** (höchstens 2 Zeilen): `ROUTINE_FEHLT` aus Schritt 0 (einmal je Session)
   und offener Consent-Banner (`no_reject_button_found`/`reject_failed`, betroffene Seiten). Ohne
   beides entfällt der Teil.

## Constraints

- **Gegenüber der Zielseite nur lesen:** kein Login, keine Formulare absenden, keine Bestellungen,
  keine Schutzmaßnahmen (Captcha, Bot-Schutz, Paywall) umgehen. Blockt die Seite (Exit 5, blocked):
  abbrechen, melden, kein erneuter Versuch.
- **Kopien fremder Werke** liegen in `<WD>/kopien/` und — durch die Vision-Analyse — im
  Session-Transcript (Transcript-Ordner des Projekts in `ergebnis/transcript.txt`) und in
  PreCompact-Backups. `sweep` löscht nur `kopien/`; Transcript und Backups nennt Teil 2 als offenen
  Speicherort.
- **BERICHT.md wird nie veröffentlicht** — kein Artifact, kein Doc, kein Repo, auch nicht auf die
  Bitte „mach eine Seite draus". Die Standardregel, fertige Berichte als Artifact zu teilen, gilt
  hier nicht: Der Bericht enthält Zitate (Teil 11) und Screenshot-Pfade (Teil 3). Teilbar ist nur
  `ergebnis/BERICHT_teilbar.md`, und die entsteht **nur auf des Nutzers Wunsch**, den Bericht zu teilen:
  ohne Teil 3, ohne wörtliche Zitate (Teil 11 nur Muster wie „Verb + Nutzen"), ohne Bilder.
- Keine bezahlten APIs, keine Telemetrie (designlang ohne `--smart`, ohne `studio`; Lighthouse ohne
  Fehlerberichte, `enableErrorReporting: false`; keine CrUX-Abfrage).
- Schreibt nur in den WD unter `~/site-anatomy/`. Einzige Ausnahme: `DESIGN.md` und
  `designs/ceo-plans/<domain>-sektionsplan.md` im Zielprojekt, jeweils mit Backup.
- Kein 1:1-Nachbau einer fremden Marke, auch nicht „nur zum Testen", wenn er veröffentlicht würde.

## Beispiel-Triggers

- `/site-anatomy https://www.telekom.de` — Startseite + 5 Seiten, Rückfrage zu Design und Zielprojekt
- `/site-anatomy https://stripe.com --pages 3 --own-tokens ~/projects/meinprojekt/tokens.dtcg.json --ziel ~/projects/meinprojekt`
- „Warum wirkt apple.com so hochwertig? Ich will so etwas für mein Projekt."

## Changelog

- **v0.3.0** (2026-10-20): Ladezeit-Messung `perf.mjs` (Lighthouse 13.5.0, Node 24; der Nutzer-Ja). Labordaten
  Handy+Desktop, CWV, LCP-Element, Ressourcen je Typ, Drittanbieter; voller Bericht nach `kopien/`.
- **v0.2.1** (2026-10-20, Nachtrag Gegenprüfung): Banner-Erkennung verlangt einen
  Entscheidungsknopf (fixierte Header/Footer mit „Datenschutz"/„Sendungstracking" waren Fehlalarme);
  axe schließt Banner-Container aus, sobald nicht wirksam abgelehnt (später Banner zählte sonst als
  Verstoß); Fehlalarm-Regel über `bannerText` + Kachel; Ersatzregel bei `colors.primary` = `null`;
  legal_check Exit 3 ohne JSON = Aufruffehler; Vorab-Zeile als Obergrenze; `legal.json` mit doppelter
  Start-URL; `layout.system.columns` kann ganz `null` sein.
- **v0.2.1** (2026-10-20): Doku-Fix nach Praxistest mit frischem Agent. Chat-Ausgabe mit
  optionalem Teil 4 „Hinweise" (`ROUTINE_FEHLT`, offener Banner); Consent-Zustand `no_banner`
  (kein Banner-Satz), Banner-Satz nur bei `no_reject_button_found`/`reject_failed`;
  `transcript.txt` hält den Projekt-Transcript-Ordner statt einer geratenen jsonl;
  `brand_distance --brand` nur mit Werten ≠ `null`; `design.json`-Pfade gegen eine echte Messung
  (designlang 13.3.2) korrigiert (`layout.system.*`, `spacing.tokens`) und „umgerechnet auf die
  eigene Basis" definiert; Screenshot-Zahl und Dauer-Schätzung (gemessen 25–30 s je Seite);
  `BERICHT_teilbar.md` nur auf Wunsch; `kopien/design_texte.json` als Kopie und Zitatquelle;
  md5-Vergleich Hell/Dunkel vor der Vision; Werkzeug-Eigenheiten im Abschnitt Abdeckung.
- **v0.2.0** (2026-10-20): Review-Runde 1 eingearbeitet. Ablauf mit Schnittstellen-Vertrag
  (`workdir.py sweep` → `init` → `legal_check` → `capture` → `measure` → `tile` → Vision → Bericht);
  `tile.sh` bekommt den WD und läuft nach measure (L18, SA-SEC-11); absolute Skriptpfade und
  Exit-2-ohne-JSON-Regel (SQ-05); Rechts-Check auch für jede Unterseite über capture.mjs (SQ-01);
  Ordner `kopien/` vs. `ergebnis/`, `sweep` + Routine-Check (SQ-08, SA-SEC-01); Abdeckungsliste
  (SQ-02); Consent-Regel bei offenem Banner (SQ-10, SA-SEC-05); Transcript als Kopien-Ort
  (SA-SEC-06); Bericht nie veröffentlichen (SA-SEC-14); Übergabe über `DESIGN.md` + Sektionsplan im
  Zielprojekt (SQ-06); `brand_distance.mjs` als Pflichtschritt (SQ-07); Vergleichstabelle mit
  Toleranzen (SQ-11); DTCG-Gerüst für eigene Tokens (SQ-12); Rechts-Check vor der Rückfrage, eine
  gebündelte Rückfrage (SQ-17); Chat: nächster Schritt zuerst, Dauer-Schätzung (SQ-15);
  Description gegen impeccable/design:*/leanrea geschärft (SQ-03); eine URL je Lauf.
- **v0.1.0** (2026-10-19): Entwurf (Staging, nicht installiert). Grundlage
  `RECHERCHE_WEBSEITEN_ANALYSE_2026-10-19.md`.
