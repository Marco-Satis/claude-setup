---
name: quick-review
version: 2.2.0
last-reviewed: 2026-05-29
description: Schneller Spot-Review eines einzelnen Files oder uncommitted Git-Diffs — max 10 Tool-Calls, inline ohne Sub-Agent-Dispatch. Severity-Skala + Anti-Patterns kompatibel mit /review. Leichter Self-Review-Pass (Cap=2) gegen Whitewashing und Severity-Drift.
when_to_use: spot review aktuelles file, uncommitted git diff review, pre-commit single-file check, inline schneller check ohne sub-agent, schneller code-check
argument-hint: 'Optional Datei-Pfad — Default: `git diff` für uncommitted changes'
allowed-tools: Read Grep Bash
userInvocable: true
---

# Quick-Review — Spot-Check vor Commit

Zweck: kleines, schnelles Code-Quality-Audit auf einem einzelnen File oder dem aktuellen Git-Diff. **Nicht** für Multi-File-Reviews (dort `/review`), **nicht** für Security-tiefe (`/security-audit`).

## Vor dem Start (Pre-Flight)

1. **Git-Repo-Check:** `git rev-parse --git-dir 2>/dev/null` — wenn nicht in Repo: Fehler, abort
2. **Argument auswerten:**
   - File-Pfad → `Read <pfad>`
   - Kein Argument → `git diff --no-color` (uncommitted changes)
3. **Leerer Diff?** → Output „nichts zu reviewen" + Exit
4. **Diff zu groß** (>10 Files / >500 Zeilen) → Hinweis „besser `/review` für diese Größe" + dennoch knapp durchgehen

## Phase 1 — 6-Achsen-Audit (inline)

Pro Achse: konkrete Findings sammeln mit File:Zeile.

**Coverage-statt-Filtering (Opus-4.7-Recall-Paradox):** in Phase 1 jedes Finding sammeln inkl. unsicherer/low-severity — NICHT vorab nach Wichtigkeit filtern. Phase 2 (Severity) + Phase 4.5 (Self-Review) ranken/filtern. Opus 4.7 befolgt „nur Wichtiges" zu treu → Recall sinkt; Sammel-Pass muss breit sein.

| Achse | Worauf prüfen |
|---|---|
| **Async-Korrektheit** | `time.sleep()` in async-Funktion, `requests.get()` statt aiohttp, Sync-DB-Calls in async |
| **Error-Handling** | bare `except: pass`, fehlende Exception-Logging, generic `except Exception` ohne re-raise |
| **Logging** | `print()` für persistente Logs, Token-/PII-Werte in Log-Strings |
| **Type-Hints** | fehlende Hints in öffentlichen Funktions-Signaturen, `Any` als Lazy-Workaround |
| **Doc-Konsistenz** | Docstring widerspricht Signature, fehlt komplett bei public API, alte Parameter erwähnt |
| **Testing-Coverage** | geänderte Logik ohne korrespondierendes Test-File in `tests/<name>` |

### Achse 7 — Repo-Hygiene (mechanisch, v2.2 — kostet Sekunden, kein Modell)

Die billigste Achse überhaupt: drei Befehle, keine Bewertung. Übernommen aus `/review` Phase 4.6 Achse H — Kriterien und Severity stehen kanonisch in [`_shared/projekt-achsen.md`](../_shared/projekt-achsen.md) (Achse H) und **K2p** in [`_shared/severity-anchors.md`](../_shared/severity-anchors.md). Hier nur ausführen, nicht neu definieren.

```bash
PRUNE="-path */.git -o -path */.venv -o -path */venv -o -path */node_modules -o -path */site-packages -o -path */__pycache__"
find <root> \( $PRUNE \) -prune -o -name '*.sync-conflict-*' -print     # Konflikt-Kopien im Quellbaum
git -C <root> ls-files | grep -E '(__pycache__|\.pyc$|/venv/|node_modules|\.env$|\.key$|\.pem$)'
find <root> \( $PRUNE \) -prune -o -name '.env*' -print | while read -r f; do
  git -C <root> check-ignore -q "$f" || echo "NICHT IGNORIERT: $f"; done
```

Bei der Nutzer Syncthing-Setup sind Konflikt-Kopien **wiederkehrend real** — deshalb läuft die Achse immer mit, auch beim Einzel-File-Check. Trifft keiner der drei Befehle etwas: eine Zeile „Hygiene: sauber (3 Checks)". Kein Git-Repo → die `git`-Zeilen entfallen mit Notiz.

## Phase 2 — Severity-Klassifikation

| Severity | Trigger |
|---|---|
| 🔴 **CRITICAL** | Active-Exploit ohne Pre-Condition, oder direkter Daten-Verlust-Pfad |
| 🟠 **HIGH** | Bare-except in Security/Auth, Token in Log, missing FK-Constraint, Tests fehlen bei Security-Code |
| 🟡 **MEDIUM** | Bare-except in Diagnose-Tool, `print` für Bot-Log, Magic-Number, fehlende Doc bei public API |
| 🟢 **LOW** | Inkonsistente Naming, fehlende Type-Hints in privater Helper, Style-Drift |
| 🔵 **INFO** | Beobachtung ohne Risiko (z.B. „könnte als Skill ausgelagert werden") |

> **Kanonische Anker:** `~/.claude/skills/_shared/severity-anchors.md` (K1/K2). Diese Tabelle = Quick-Kurzform; bei Konflikt gilt die kanonische Datei (Single-Source, Audit-Fund M1).

Bei Security-Verdacht (auth, crypto, sql, exec, secrets): Hinweis im Output „tiefer Audit via `/security-audit`" — NICHT inline auditieren (Out-of-Scope für Quick).

## Phase 3 — Anti-Patterns vermeiden (Output-Qualität)

Im Output **verboten** (analog zu `/review`):

| Anti-Pattern | Korrektur |
|---|---|
| Kraft-Adjektive ohne Beweis („sauber", „solide", „elegant") | konkretes File:Zeile + warum |
| Score-Vergaben („9/10", „B+") | weglassen, ersetzen durch Severity-Counts |
| Empfehlungs-Floskeln („sollte überdacht werden") | konkretes „Fix in <N> Min: <Befehl/Edit>" oder „kein Fix nötig WEIL ..." |
| Production-Ready-Behauptung | weglassen — der Nutzer Entscheidung |
| Findings ohne File:Zeile | Pflicht: Pfad + Zeilennummer |

## Phase 4 — Output-Draft

Initial-Output gemäß Format unten (noch nicht final — geht in Phase 4.5 Self-Review).

```
⚡ Quick-Review — <File oder "git diff: N Files, M Zeilen">

Severity-Counts: 🔴 X | 🟠 Y | 🟡 Z | 🟢 W | 🔵 V

Findings:
- 🟠 <file:line> — <Was + warum Risiko> (Fix: <konkret, <N> Min)
- 🟡 <file:line> — <Beschreibung> (Fix: ...)
- 🟢 <file:line> — <Style> (Fix: ...)

Tests:
- <file>: Tests existieren / fehlen (vorgeschlagen: <test_file.py>)

Empfehlung: Commit OK / vor Commit fixen / Deeper Audit via /<skill>
```

## Phase 4.5 — Self-Review-Pass (PFLICHT seit v2.1, Cap=2)

Nach Output-Draft **immer einmal** kritisch durchgehen — kein heimliches Skip. Cap=2 (Initial + 1 Self-Review-Pass). Token-Budget: max 5k pro Iter.

### Self-Review-Checks (kombinierter Single-Pass)

**A) Anti-Pattern-Filter** (Phrasen aus Phase 3):
- Kraft-Adjektive ohne Beweis (sauber/solide/elegant) → entfernen
- Score-Vergaben (9/10, B+) → entfernen
- Empfehlungs-Floskeln (sollte überdacht werden) → konkretes „Fix in N Min" oder „kein Fix nötig WEIL ..."
- Production-Ready-Behauptung → entfernen
- Findings ohne File:Zeile → File:Zeile ergänzen oder Finding löschen

**B) Severity-Anker-Drift** (Kalibrierung gegen kanonische Anker `~/.claude/skills/_shared/severity-anchors.md` K2):
- "Hardcoded Pfad der bei Upgrade brechen kann" → MEDIUM (nicht HIGH)
- "Magic Number ohne Konstante" → LOW (nicht MEDIUM)
- "Bare-except: pass im Diagnose-Tool" → LOW (nicht MEDIUM)
- "Bare-except: pass im Sicherheits-Hook" → MEDIUM
- "Fehlende Tests bei Util-Code" → LOW
- "Fehlende Tests bei Security-/Auth-/DB-Code" → MEDIUM Pflicht
- "Duplicate-Install (System + venv)" → MEDIUM **nie LOW**

**C) False-Positive-Check** (single-file scope):
- Bei Finding mit grenzwertiger Severity oder unsicherer Reproducibility: in Output mit `[VERIFIED]` taggen oder als INFO downgraden

### Convergence

| Modus | Auslöser |
|---|---|
| `clean` | Keine Anti-Pattern-Phrasen, Severity passt zu Ankern, keine FP-Verdachtsfälle | 
| `cap` | Cap=2 erreicht (1 Self-Review-Pass durchgeführt, falls Drift gefunden wurde — Final-Output ist gepatcht) |

Bei `clean`: 1-Zeilen-Trace im Output `Self-Review: clean (Iter 1, keine Drift)`.
Bei `cap` mit Patches: Trace zeigt was geändert wurde, z.B. `Self-Review: 2× Severity-Recalibration (HIGH→MEDIUM bei F002, MEDIUM→LOW bei F005), 1× Whitewashing-Phrase entfernt`.

### Loop-Anti-Patterns

| Pattern | Vermeidung |
|---|---|
| Self-Review-Pass heimlich skippen | Trace ist Pflicht-Output (1 Zeile) |
| Findings im 2. Pass neu erfinden | Strikt: nur Anti-Pattern-Filter + Severity-Anker + FP-Check, keine neuen Findings |
| Severity-Anker ignorieren weil "fühlt sich höher an" | Anker ist Final, Bauchgefühl löscht keinen Anker |

## Phase 5 — Final-Output

Output aus Phase 4 + Patches aus Phase 4.5 + **Pflicht-Zeile** mit Self-Review-Status:

```
⚡ Quick-Review — <File>

Severity-Counts: 🔴 X | 🟠 Y | 🟡 Z | 🟢 W | 🔵 V

Findings:
- 🟠 <file:line> — <Was + warum Risiko> (Fix: <konkret>)
- 🟡 <file:line> — <Beschreibung> (Fix: ...)

Tests:
- <file>: Tests fehlen (vorgeschlagen: <test_file.py>)

Self-Review: <clean | "2× Severity-Recalibration, 1× Whitewashing entfernt"> (Iter <N>)

Empfehlung: Commit OK / vor Commit fixen
```

## Constraints

- **Max 10 Tool-Calls** (Read + Grep + Bash für Git)
- **Inline-only** — kein Sub-Agent-Dispatch
- **Read-only** — keine Auto-Fixes
- **Bei Multi-File-Diff (>10 Files):** `/review` empfehlen
- **Bei Security-Verdacht:** `/security-audit` empfehlen
- **Severity-Skala** identisch zu `/review` für Workflow-Konsistenz

## Beispiel-Triggers

- `/quick-review` — uncommitted git diff
- `/quick-review web/routes/sse_route.py` — einzelnes File
- `/quick-review modules/database/db_manager.py` — anderes File

## Changelog

- **v2.2.0 (2026-08-02):** Achse 7 **Repo-Hygiene** ergaenzt — drei mechanische Befehle (Konflikt-Kopien, getrackte Artefakte/Secrets, nicht-ignorierte `.env*`), kein Modell noetig. Kriterien + Severity kanonisch aus `_shared/projekt-achsen.md` (Achse H) und K2p in `_shared/severity-anchors.md`, hier nur ausgefuehrt. Grund: Konflikt-Kopien sind im Syncthing-Setup wiederkehrend real und kosten in der Erkennung Sekunden.
- **v2.1.0** (2026-05-18): Leichter Self-Review-Pass (Phase 4.5, Cap=2). Kombinierter Single-Pass: Anti-Pattern-Filter + Severity-Anker-Drift + False-Positive-Check. Token-Budget 5k/Iter. Pflicht-Trace im Output (1 Zeile). Symmetrie zu /review v3.0 Phase 5.5 — leichtere Variante für Single-File-Scope.
- **v2.0.0** (2026-05-17): Standardisierung — Severity-Skala kompatibel mit `/review`, Anti-Patterns-Tabelle ergänzt, 5 → 6 Audit-Achsen (Testing-Coverage neu), Pre-Flight-Checks, expliziter Output-Format, argument-hint statt argumentHint (Schema-Konformität).
- **v1.0.0** (2026-05-16): Erste Version.
