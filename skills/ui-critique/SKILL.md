---
name: ui-critique
version: 1.3.0
last-reviewed: 2026-06-03
description: UX/Layout-Review für HTML/CSS-Komponenten — visuelle Hierarchie, Konsistenz, Spacing, Typografie-Skala, Interaktions-States, Empty/Loading/Error-States. Optimiert für FastAPI-Templates + style.css-Token-Systeme.
when_to_use: ui review, design critique, dashboard kritik, html review, css review, ux feedback, visual hierarchy check, design konsistenz, spacing check, hover states review
argument-hint: Optional File/Komponente ("web/templates/dashboard.html" | "navigation" | "stats-card") — Default scant gesamten templates-Ordner
allowed-tools: Read Grep Glob Bash Write Edit
userInvocable: true
---

# ui-critique — UX/Layout-Review

Zweck: HTML/CSS auf strukturelle UX-Probleme prüfen. Komplementär zu `/a11y-check` (WCAG) — hier geht's um Layout-Logik, visuelle Hierarchie, Konsistenz, Interaktions-Klarheit.

## Vor dem Start

1. Scope: Argument oder Default `web/templates/**/*.html` + `web/static/style.css`
2. Design-Token-Inventar aus `style.css`: Farb-Variables, Spacing-Skala (--s-*), Font-Skala, Border-Radius, Shadows
3. Komponenten-Mapping: Buttons, Cards, Tables, Forms, Modals, Navigation, Status-Indicators

## Phase 1 — Visuelle Hierarchie

### Heading-Hierarchie

```bash
grep -nE '<h[1-6]' web/templates/**/*.html
```

Pro Template prüfen:
- 1× `<h1>` pro Page (Page-Title)
- Logische Folge: `h1 → h2 → h3`, kein Skip
- `<h4>` und tiefer nur bei wirklich tiefer Struktur — sonst Indikator für überkomplexe Layout-Struktur

**Findings:**
- Mehrere `<h1>` → MEDIUM (verwirrt Reading-Order)
- Heading-Skip (`h1 → h3`) → MEDIUM
- `<h6>` ohne `h4`/`h5` davor → MEDIUM (vermutlich Stil-Hack für „kleiner Text")
- Bold-Text als visuelle Heading statt `<h*>` → LOW

### Typografie-Skala

Aus `style.css` Font-Sizes extrahieren:
```bash
grep -E "font-size:" web/static/style.css | sort -u
```

Prüfen:
- Anzahl Font-Sizes < 6 (mehr = inkonsistente Skala)
- Skala-Logik: 12/14/16/18/24/32 (typisch) oder Major-Third-Scale
- Body-Text mind. 16px für Desktop, 14px für Dense-Tables OK

**Findings:**
- >8 verschiedene Font-Sizes → MEDIUM (Skala uneinheitlich)
- Body-Text < 14px → MEDIUM (Lesbarkeit)
- Mehrere Font-Familien für Body-Text → LOW

### Spacing-System

Aus `style.css` Spacing-Tokens:
```bash
grep -E "^\s*--s-[0-9]" web/static/style.css
```

der Nutzer's Dashboard sollte 8px-Skala haben (--s-1 = 4px, --s-2 = 8px, --s-3 = 12px, ...).

**Findings:**
- Hardcoded `margin:`/`padding:` mit Werten außerhalb der Skala (z.B. `padding: 13px`) → MEDIUM
- Inkonsistente Spacing zwischen ähnlichen Komponenten → MEDIUM (z.B. Card-Padding mal `--s-3`, mal `--s-4`)
- Negative-Margin-Hacks ohne Begründung → LOW

## Phase 2 — Interaktions-Klarheit

### Button/Link-Differenzierung

```bash
grep -nE '<button|<a ' web/templates/**/*.html
```

**Regel:** Buttons = Aktionen die State ändern; Links = Navigation zu URLs.

**Findings:**
- `<a>` mit `onclick` ohne Navigation → HIGH (sollte `<button>` sein)
- `<button>` ohne `type="button"` in `<form>` → MEDIUM (löst unbeabsichtigt Submit aus)
- Link-Styling auf Buttons (oder umgekehrt) → MEDIUM (User unklare Erwartung)

### Interaktions-States (Hover/Focus/Active/Disabled/Loading)

Pro Interaktives Element prüfen ob alle States definiert:
```bash
grep -E ":(hover|focus|active|disabled)" web/static/style.css
```

**Pflicht-States:**
- `:hover` für Buttons + Links (Visual-Affordance)
- `:focus-visible` für Keyboard-Navigation (siehe `/a11y-check` für Detail)
- `:active` (Click-Feedback) — optional aber empfohlen
- `[disabled]` oder `.disabled` Styling — Pflicht falls Buttons disable-bar
- `.loading` / `.spinner` State für HTMX-Requests

**Findings:**
- Fehlender `:hover` auf interaktiven Elementen → MEDIUM
- Identisches `:hover` + `:focus` → LOW (Keyboard-User kann nicht unterscheiden)
- Disabled-State sieht aus wie Active → MEDIUM (User klickt erfolglos)

### Empty/Loading/Error-States

Für jede dynamische Komponente (HTMX-Targets, Charts, Tables):
```bash
grep -nE 'hx-(get|post|swap)|chart\.js' web/templates/**/*.html
```

**Pflicht-Frage pro Komponente:**
- Was sieht User wenn **keine Daten**? (Empty-State mit erklärendem Text + nächstem Schritt)
- Was sieht User **während Laden**? (Skeleton-Screen oder Spinner)
- Was sieht User bei **Fehler**? (Error-Message mit Retry-Option)

**Findings:**
- Empty-State nur „Keine Daten" ohne nächsten Schritt → MEDIUM (UX-Sackgasse)
- Kein Loading-Indicator bei HTMX-Request > 200ms → MEDIUM (User klickt mehrfach)
- Error-State zeigt rohen 500-Stack-Trace → HIGH (Security + UX)

## Phase 3 — Konsistenz-Audit

### Token-Verwendung

```bash
# Findet hardcoded Werte die eigentlich Tokens sein sollten
grep -rE "#[0-9a-fA-F]{3,6}|rgb\(|rgba\(" web/static/style.css | grep -v ":root"
```

**Findings:**
- Hardcoded Farbwerte außerhalb von `:root` → MEDIUM (umgeht Theme-System)
- Magic-Spacing-Werte (`margin: 27px`) → LOW
- Inline-Styles in HTML (`style="..."`) → MEDIUM

### Komponenten-Variants

Pro Komponente (z.B. Button) prüfen ob Variants konsistent sind:
- `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-ghost` — alle definiert?
- Größen-Variants (`.btn-sm`, `.btn-lg`) — konsistent über alle Komponenten?
- Naming-Convention BEM oder Tailwind-like — gemischt?

**Findings:**
- Component-Variant inkonsistent benannt (`.btn-large` vs `.card-lg`) → LOW
- Variants fehlen (z.B. Buttons haben Primary/Secondary, Cards aber nicht) → INFO

### Responsive-Verhalten

```bash
grep -nE "@media" web/static/style.css
```

**Pflicht-Breakpoints:**
- Mobile: < 768px
- Tablet: 768–1024px
- Desktop: > 1024px

**Findings:**
- Keine Media-Queries → MEDIUM (Mobile-Bricht)
- Fixed-Width-Container ohne Max-Width-Cap → LOW
- Tabellen ohne `overflow-x: auto` auf mobilem → MEDIUM

## Phase 4 — HTMX-spezifische UX

der Nutzer's Dashboard nutzt HTMX. Spezifische Checks:

| Pattern | UX-Risiko | Fix |
|---|---|---|
| `hx-trigger="every Xs"` ohne sichtbares Polling-Indicator | User weiß nicht ob Live oder Stale | Subtiler „Updated 3s ago" Indicator |
| `hx-swap="innerHTML"` ohne Transition | Visueller Sprung beim Update | `hx-swap="innerHTML transition:true"` + CSS-Transition |
| Multiple `hx-target` auf gleicher Page | Komplexer Mental-Model für User | Sicherstellen dass Targets visuell unterschieden sind |
| HTMX-Form ohne Optimistic-Update | Verzögerung wirkt wie „kaputt" | Lokales `disabled` + Spinner auf Submit-Button |

## Phase 4.5 — AI-Slop-Risk + Unresolved Decisions (adopt gstack plan-design-review, 2026-05-29)

### AI-Slop-Risk
Erkenne generisches „AI-Default-Design". Opus-4.7-Hausstil-Default: warmes Creme `#F4F1EA`, Serif-Display (Georgia/Fraunces/Playfair), Terracotta/Amber-Akzent — passt für Editorial/Hospitality, FALSCH für Dashboards/Dev-Tools/Fintech/Healthcare. Prüfe:
- Default-Creme/Serif ohne Domänen-Begründung → LOW „AI-Slop-Verdacht: Stil passt nicht zur Domäne (Bot-Dashboard ≠ Editorial)"
- Generische Hero/Card/Gradient-Muster ohne eigene Design-Sprache → INFO
- Fix-Richtung: konkrete Alternativ-Spec (Hex/Typo/Radius) ODER „N Optionen vorschlagen" (Lyra Frontend-Variety-Steering)

### AI-Slop-Tells-Checkliste (adopt impeccable v3.5, Apache-2.0 / pbakaus — Wissen, nicht der Skill)
Konkrete, deterministisch prüfbare 2026-Tells. Pro Treffer LOW/INFO + benannte Stelle + Fix. **≥3 Tells = MEDIUM** „generisches AI-Default-Design, keine eigene Sprache":
- **Cream/Sand-Body-BG** (OKLCH L 0.84–0.97, C<0.06, hue 40–100; Token-Namen `--paper/--cream/--sand/--linen/--parchment` = Tell an sich) → echtes Off-White bei chroma 0 ODER saturierte Brand-Farbe; „Wärme" über Akzent+Typo, nicht Body-BG.
- **Gradient-Text** (`background-clip:text` + Gradient) → eine Solid-Farbe, Emphasis via Weight/Size.
- **Glassmorphism als Default** (deko-Blur/Glas-Cards) → selten + gezielt, oder weg.
- **Hero-Metric-Template** (Big-Number + kleines Label + Gradient-Akzent) → SaaS-Klischee.
- **Identische Card-Grids** (gleich große Icon+Heading+Text-Cards endlos) → Hierarchie/Variation rein.
- **Uppercase-tracked Eyebrow** über jeder Section (ABOUT/PROCESS-Kicker, 55–95% aller Generations) → andere Kadenz.
- **Side-Stripe-Border** (`border-left`>1px farbig auf Cards/Alerts) → volle Border/BG-Tint/Leading-Icon.
- **Aphoristische Copy-Kadenz** (3+ Blöcke „ernster Satz, dann kurze Negation") → spezifisch statt aphoristisch umschreiben.
- **Ähnliche-aber-nicht-identische Font-Paarung** (2× Geometric-Sans) → Kontrast-Achse (Serif+Sans) oder 1 Familie/mehrere Weights.
- **Arbiträre z-index** (999/9999) → semantische Scale (dropdown→sticky→modal→toast→tooltip).
- **Uniformer Entrance-Reflex** (1 identische Einblend-Animation auf JEDER Section) → pro Reveal passend, nie content hinter class-gated transition versteckt (rendert sonst blank).
- **Emoji als Content/Icon-Platzhalter** (adopt huashu-design, 2026-06-04) (📊🚀✨ als Feature-Card-Icons/Heading-Deko statt echtem Icon-Set) → echtes Icon-Set (Lucide/Heroicons/Phosphor) ODER weglassen; Emoji nie als Deko-Füller.
- **Generic-Illustration/SVG-Silhouette statt echtem Asset** (adopt huashu, 2026-06-04) (undraw-artige Figuren/Platzhalter-Blobs wo echter Screenshot/Foto hingehört) → echtes Produkt-Bild; Illustration nur wenn bewusst Brand-Teil.
- **Default-UI-Sans als Display-Face** (adopt huashu, 2026-06-04) (Inter/Geist/Roboto für große Headlines = AI-Default) → Display-Schrift mit Charakter (Serif/Grotesk/Display-Cut) für Headlines; UI-Sans nur Body/UI.
- **Fehlende Positiv-Defaults** (schwacher Tell, adopt huashu, 2026-06-04): kein `text-wrap: balance/pretty` auf Headlines+Absätzen · Flex-Margin-Hacks statt CSS-Grid für präzises Layout · `oklch()` statt Default-Hex für Farb-Kohärenz. Vorhandensein = Politur-Signal, Fehlen bei sonst-AI-Stil verstärkt den Slop-Verdacht.
- **Second-Order-Tell:** wenn die Ästhetik aus „Kategorie minus Anti-Referenz" erratbar ist (z.B. „AI-Tool das nicht SaaS-cream → editorial-typografisch") → erste Reflex vermieden, zweite getroffen. Solange überarbeiten bis beide nicht offensichtlich.

### Unresolved Decisions
Explizit alle Design-Entscheidungen auflisten die das Template offenlässt (z.B. „Mobile-Nav-Pattern undefiniert", „Loading-State für Chart konzeptionell fehlt"). Macht Lücken targetable statt sie zu überdecken.

### Ideal-Zustand statt Score
Pro Finding NICHT 0-10 bewerten (Score = Whitewashing-Anti-Pattern, siehe Constraints), sondern **beschreiben wie der Ideal-Zustand für DIESE Komponente aussähe** — targetable Spec die der Implementierer anbauen kann (gstack-Idee „was 10/10 wäre", ohne die Zahl).

## Phase 5 — Findings-Report

**Output:** `~/.claude/reports/ui-critique/<datum>_<HHMM>/REPORT.md`

Format:
```
| ID | Severity | File:Line | Kategorie | Komponente | Problem | Fix | Aufwand |
```

Kategorien: `Hierarchie` / `Konsistenz` / `Interaktion` / `States` / `Responsive` / `HTMX`

**Master-Sektionen:**
1. Executive Summary (max 150 Worte)
2. Design-Token-Status (vollständig / Lücken / Inkonsistenzen)
3. Komponenten-Matrix: pro Komponente Status (Hover ✓, Focus ✓, Loading ✗, etc.)
4. Findings nach Severity
5. Quick-Wins (Aufwand < 30 min, Severity ≥ MEDIUM)
6. Mismatch zu `/a11y-check` falls beide Skills genutzt — Cross-Reference

## Constraints

- **Read-only.** Keine Auto-Fixes
- **Komplementär zu `/a11y-check`** — WCAG-Themen dorthin verschieben, hier nur UX-Logik
- **Severity-Skala** kompatibel mit `/review`
- **Keine subjektiven Geschmacks-Urteile** („sieht hässlich aus") — nur konkrete Probleme mit Begründung
- **der Nutzer-Convention:** Beispiele aus Discord-Bots-Dashboard (style.css v5.0 mit Discord-Blurple Tokens)

## Komplementäre Skills (wann anders triggern)

| Use-Case | Skill |
|---|---|
| Neue Komponente bauen statt reviewen | `frontend-design` (claude-plugins-official) |
| Tieferer Design-Feedback (z.B. visuelle Hierarchie-Reflexion) | `design:design-critique` |
| UX-Texte nachschärfen (Microcopy, Error-States) | `design:ux-copy` |
| Design-Token-Drift im ganzen CSS-System | `design:design-system` |
| WCAG-Audit (Color-Contrast, Keyboard, ARIA) | `/a11y-check` |

Workflow-Übersicht: `~/.claude/docs/design-workflow.md`

## Beispiel-Triggers

- `/ui-critique` — gesamtes templates-Verzeichnis
- `/ui-critique web/templates/dashboard.html` — einzelnes File
- `/ui-critique navigation` — nur Navigation-Komponente (Lyra-Style Component-Match)

## Changelog

- **v1.3.0 (2026-06-04):** **+4 Anti-Slop-Tells** aus huashu-design (alchaincyf, 16k★ MIT — web+GitHub-API-verifiziert, Wissen adoptiert NICHT Skill: huashu mandatet Playwright/Node-Render-Pipeline): Emoji-als-Content/Icon-Platzhalter, Generic-Illustration/SVG-Silhouette-statt-echtem-Asset, Default-UI-Sans (Inter/Geist) als Display-Face, fehlende Positiv-Defaults (`text-wrap:balance/pretty`, CSS-Grid, oklch). Jetzt 16 Tells. **Quelle:** TikTok-Pipeline claude-code-tips 2026-06-04 → GitHub-API-verifiziert (huashu real, ui-ux-pro-max=404-fake aussortiert) → nur nicht-überlappendes Wissen übernommen.
- **v1.2.0 (2026-06-03):** **AI-Slop-Tells-Checkliste** in Phase 4.5 (adopt impeccable v3.5 Apache-2.0/pbakaus — nur das Design-Wissen, NICHT der Skill: impeccable mandatet unaudited Node-Scripts + Browser-Automation, daher Pattern-Adoption statt Install). 12 konkrete 2026-Tells (Cream-BG/OKLCH, Gradient-Text, Glassmorphism, Hero-Metric, Card-Grids, Eyebrow, Side-Stripe, aphoristische Copy, Font-Paarung, z-index, Entrance-Reflex, Second-Order). ≥3 Tells = MEDIUM. **Quelle:** TikTok-Pipeline-Finding (claude-code-tips, 2026-06-03) → web-verifiziert → Wissen adoptiert.
- **v1.1.0 (2026-05-29):** gstack-plan-design-review-Best-of adoptiert (score-frei) — Phase 4.5: AI-Slop-Risk (Opus-4.7-Default-Stil-Erkennung, Lyra-Frontend-Variety), Unresolved-Decisions-Liste, „Ideal-Zustand statt Score" (targetable Spec ohne 0-10, da Score = Whitewashing-Anti-Pattern). Output-Dir → `~/.claude/reports/ui-critique/`.
- **v1.0.0 (2026-05-17):** Erste Version.
