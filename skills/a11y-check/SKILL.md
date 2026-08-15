---
name: a11y-check
version: 1.0.0
last-reviewed: 2026-05-17
description: WCAG-2.1-AA-Accessibility-Audit für HTML/CSS/JS — Color-Contrast, Keyboard-Nav, Touch-Targets, ARIA, Semantik, Focus-Indicators. Optimiert für FastAPI-Templates + HTMX-Patterns (Discord-Bots-Dashboard).
when_to_use: a11y check, accessibility audit, WCAG audit, kontrast prüfen, keyboard navigation, ARIA review, dashboard barrierefreiheit, color contrast check, screen reader compatibility
argument-hint: Optional File/Glob ("web/templates/dashboard.html" | "web/templates/**/*.html") — Default scant gesamten templates-Ordner
allowed-tools: Read Grep Glob Bash Write Edit
userInvocable: true
---

# a11y-check — WCAG 2.1 AA Audit

Zweck: Dashboard und HTML-Templates auf Accessibility-Probleme prüfen. Fokus: WCAG 2.1 AA als Standard, nicht AAA (zu strikt für interne Tools).

## Vor dem Start

1. Scope ermitteln: Argument oder Default `web/templates/**/*.html` + zugehörige CSS-Files
2. Komponenten-Liste aus HTML extrahieren (Buttons, Links, Form-Inputs, Modals, Tables, Charts)
3. CSS-Tokens lesen (`web/static/style.css` für Color-Variables)

## Phase 1 — Statische Checks

### Color-Contrast (WCAG 1.4.3)

Aus `style.css`-Tokens die Foreground/Background-Paare berechnen:
```python
# Pseudo: für jedes (text-*, bg-*)-Paar
contrast_ratio = relative_luminance_ratio(text_color, bg_color)
# WCAG AA: 4.5:1 für Body-Text, 3:1 für Large-Text (>= 18pt oder 14pt bold)
# WCAG AAA: 7:1 für Body, 4.5:1 für Large — als INFO melden, nicht als Finding
```

Tools (lokal nutzbar):
- `npx pa11y <url>` (CLI-Wrapper für axe-core) — wenn Dashboard läuft
- Manuell: Browser-DevTools → Lighthouse → Accessibility-Audit

**Pflicht-Findings:**
- Body-Text < 4.5:1 → HIGH
- Large-Text < 3:1 → MEDIUM
- Interactive-State (hover/focus) verliert Kontrast → MEDIUM

### Keyboard-Navigation (WCAG 2.1.1)

Per Grep prüfen:
```bash
# Buttons ohne tabindex müssen native <button> sein
grep -E 'class="btn"' web/templates/**/*.html
# Wenn nicht-button mit btn-class: prüfen ob tabindex="0" + role="button" + onkeydown gesetzt
```

**Pflicht-Findings:**
- `<div onclick="">` ohne `tabindex` + `role="button"` + Enter/Space-Handler → HIGH
- Custom-Dropdowns ohne Keyboard-Steuerung (Pfeiltasten, Esc, Enter) → MEDIUM
- Modal ohne Focus-Trap (Tab kann Modal verlassen) → MEDIUM
- `tabindex="-1"` auf interaktiven Elementen → HIGH (entfernt aus Tab-Order)
- `tabindex` > 0 → MEDIUM (überschreibt natürliche Reihenfolge)

### Touch-Targets (WCAG 2.5.5 AAA / 2.5.8 AA)

CSS-Check für Buttons/Links:
```bash
grep -E "min-(width|height)|padding" web/static/style.css | grep -E "btn|button|link"
```

**Pflicht-Findings:**
- Touch-Target < 24×24 CSS-Pixel (WCAG 2.5.8 AA) → MEDIUM
- Touch-Target < 44×44 (WCAG 2.5.5 AAA) → LOW (Best-Practice)
- Nahe-beieinander-Buttons ohne 8px-Spacing → LOW

### ARIA & Semantik (WCAG 4.1.2)

```bash
grep -nE 'role="|aria-' web/templates/**/*.html
```

**Pflicht-Findings:**
- `<div role="button">` statt `<button>` ohne Begründung → MEDIUM
- Fehlende `aria-label` auf Icon-Only-Buttons → HIGH
- Fehlende `aria-live` auf dynamischen Bereichen (HTMX-Swap-Targets) → MEDIUM
- `alt=""` auf semantischen Bildern (Logos, Charts) → MEDIUM
- Fehlende Form-Label (kein `<label for="...">` oder `aria-labelledby`) → HIGH

### Focus-Indicators (WCAG 2.4.7)

CSS-Check:
```bash
grep -E ":focus\b|outline:" web/static/style.css
```

**Pflicht-Findings:**
- `outline: none` ohne Replacement-Indikator → HIGH (Tab-User verliert Orientierung)
- Focus-Indicator-Contrast < 3:1 → MEDIUM
- Identischer Focus-vs-Hover-Style → LOW (User kann nicht unterscheiden)

### Semantische HTML-Struktur

```bash
grep -nE '^\s*<(div|span)' web/templates/**/*.html | wc -l
grep -nE '<(header|nav|main|section|article|aside|footer)' web/templates/**/*.html | wc -l
# Ratio: > 5:1 div/span vs semantic → "div-soup" Anti-Pattern
```

**Pflicht-Findings:**
- Heading-Skip (`h1 → h3` ohne `h2`) → MEDIUM
- Mehrere `<h1>` pro Seite → LOW
- Fehlende `<main>` / `<nav>` / `<header>` Landmarks → MEDIUM
- Tables ohne `<th scope="...">` → MEDIUM

## Phase 2 — HTMX-spezifische Checks

HTMX-Patterns die a11y brechen können:

| Pattern | Problem | Fix |
|---|---|---|
| `hx-swap="innerHTML"` auf Modal-Triggers | Focus geht verloren nach Swap | `hx-swap-oob` + Focus-Restore via JS |
| Dynamisch geladene Form-Inputs | Screen-Reader bekommt sie nicht mit | `aria-live="polite"` auf Container |
| `hx-trigger="every Xs"` | Konstante Polling-Updates lenken Screen-Reader ab | `aria-live="off"` für Polling-Bereiche |
| Toast-Notifications via HTMX | Screen-Reader liest sie evtl. nicht | `role="status"` oder `role="alert"` |

## Phase 3 — Findings-Report

**Output:** `~/.claude/reports/a11y-check/<datum>_<HHMM>/REPORT.md`

Format pro Finding:
```
| ID | Severity | File:Line | WCAG-Criterion | Element/Selector | Problem | Fix | Aufwand |
|----|----------|-----------|----------------|------------------|---------|-----|---------|
```

WCAG-Criterion: z.B. „1.4.3 Contrast (Minimum)" oder „2.1.1 Keyboard"

**Master-Sektionen:**
1. Executive Summary (max 150 Worte, Findings-Counts pro Severity)
2. Color-Contrast-Tabelle (alle Token-Paare mit Ratio + Pass/Fail)
3. Findings nach Severity sortiert
4. Komponenten-Checkliste (für jede UI-Komponente: a11y-OK / Probleme)
5. Quick-Wins (Aufwand < 30 min, Severity ≥ MEDIUM)

## Phase 4 — Live-Test (optional)

Wenn Dashboard läuft (`http://localhost:8080`):
```bash
# Falls pa11y verfügbar:
npx pa11y http://localhost:8080 --standard WCAG2AA --reporter json > a11y_live.json
# Falls nicht: Lighthouse-Bookmarklet im Browser
```

## Constraints

- **Read-only.** Keine Auto-Fixes — nur Findings + Empfehlungen
- **Token-effiziente Ausgabe.** Tabellen-Format, max 30 Zeilen Chat-Summary
- **der Nutzer-Convention:** Severity-Skala kompatibel mit `/review` (CRITICAL/HIGH/MEDIUM/LOW)
- **Quellen** für WCAG-Kriterien: https://www.w3.org/WAI/WCAG21/quickref/ (nicht halluzinieren — wenn unsicher, INFO statt Finding)

## Komplementäre Skills (wann anders triggern)

| Use-Case | Skill |
|---|---|
| Layout-Logik / UX-Hierarchie (kein WCAG) | `/ui-critique` |
| Tieferer A11Y-Audit (Anthropic-Cowork-Variante) | `design:accessibility-review` |
| UX-Texte für Screen-Reader (alt-texts, aria-labels) | `design:ux-copy` |
| Neue Komponente bauen mit A11Y-First | `frontend-design` + danach `/a11y-check` |

Workflow-Übersicht: `~/.claude/docs/design-workflow.md`

## Beispiel-Triggers

- `/a11y-check` — gesamten templates-Ordner
- `/a11y-check web/templates/dashboard.html` — einzelnes File
- `/a11y-check web/templates/admin/*.html` — Glob
