---
name: deploy-preflight
version: 1.1.0
last-reviewed: 2026-07-21
description: Fuehrt Pre-Deployment-Checks fuer Python-Projekte aus. Laesst alle pytest-Suiten laufen, prueft Importierbarkeit aller Module, validiert .env-Vollstaendigkeit gegen Code-Verbrauch (via python-env-audit), prueft requirements.txt mit pip check, sucht nach Debug-Relikten (print, breakpoint, TODO, FIXME, pdb) im produktiven Code, und fasst alles zu einer Go/No-Go-Entscheidung zusammen. Trigger wenn der User "deployen", "vor dem Release", "preflight", "ist das ready", "kann ich pushen", "alles gruen?", "deployment vorbereiten" sagt — auch ohne explizite Skill-Erwaehnung.
---

# deploy-preflight

Eine kompakte Checkliste vor jedem Push, die alle bekannten Stolperfallen abklappert. Ergebnis: eine klare Go/No-Go-Empfehlung mit allen Issues.

## Wofuer

des Nutzers Discord-Bot-System wird via `deploy.sh` auf einen Netcup-Server gepusht, der FritzBox-Monitor via `deploy.ps1` per SCP. Wenn dabei ein Test rot ist, eine ENV fehlt, oder ein `print("DEBUG", token)` im Code haengt, kommt das oft erst auf der Produktion auf — und dann nervt es richtig. Der Skill macht das billig vorher sichtbar.

## Trigger

- "Ich will deployen"
- "Preflight"
- "Pruef bitte ob ich pushen kann"
- "Ist alles bereit fuer das Release?"
- Vor `deploy.sh` / `deploy.ps1` ausfuehren
- Nach groesseren Code-Aenderungen als Sanity-Check

## Workflow

Fuehre Schritte 1-7 in dieser Reihenfolge aus. Wenn ein Schritt fehlschlaegt: weitermachen, im Report sammeln. Erst am Ende Go/No-Go entscheiden.

### 1. Tests laufen lassen

Erkenne anhand der Projektstruktur, was wie auszufuehren ist:

- `tests/` mit `test_*.py` -> `pytest tests/ -v --tb=short`
- Spezifische Pflicht-Tests im Discord-System:
  - `pytest tests/test_imports.py tests/test_cogs.py tests/test_env_completeness.py tests/test_routes.py -v`
- FootstepPro: `pytest tests/test_basic.py tests/test_metrics_regression.py -v`

Lauf via `Bash`. Speichere Output. Pass: alle gruen. Fail: pro fehlgeschlagenem Test eine Zeile mit Datei::Test::Fehler im Report.

**pytest nicht installiert?** Pruefe per `python -c "import pytest"` vorher. Wenn das Modul fehlt:
- Im Report markieren als `[BLOCKER]` (NICHT silently skip — Tests sind ein Pflichtschritt vor Deploy)
- Konkrete Anweisung geben: `pip install pytest pytest-asyncio` (asyncio bei Discord) oder `pip install -r requirements-dev.txt` falls vorhanden
- Erst weitermachen wenn der User das bestaetigt oder `--skip-tests` explizit setzt

Auto-Skip ohne Hinweis ist gefaehrlich, weil dann der Preflight gruenes Licht gibt obwohl die Tests gar nicht liefen.

### 2. Importierbarkeit aller Module

Sammele alle `.py`-Dateien (ohne `tests/`, `venv/`, `__pycache__/`). Pro Datei:

```bash
python -c "import ast; ast.parse(open('<datei>', encoding='utf-8').read())"
```

Das prueft Syntax **ohne Code auszufuehren** — das ist der sichere Default fuer ALLE `.py`.

**⚠ Import-Test (`exec_module`) fuehrt Modul-Top-Level-Code REAL aus** — DB-Writes, Mail-Versand, Netz-Calls, oder ein destruktives Skript laufen dabei tatsaechlich. Darum NICHT pauschal auf alle Dateien:

- **Entry-Point-/Runner-Dateien AUSSCHLIESSEN** vom exec-Test — nur ast-parse (oben). Das sind Dateien die beim Import etwas *tun*: alles unter `bots/`, `scripts/`, `deploy*`, sowie jede Datei mit Top-Level `bot.run(`, `asyncio.run(`, `app.run(`, `uvicorn.run(`, `main()` ausserhalb `if __name__`, oder Shell-/Subprocess-Aufrufe auf Modulebene. Diese NIE exec-importieren.
- **Nur Library-Module** (cogs/, modules/, utils/ — Code der beim Import nur definiert, nicht handelt) exec-testen, und zwar **isoliert im Subprocess mit Timeout**, damit ein haengendes/gefaehrliches Modul gekillt wird statt den Preflight zu blockieren:

```bash
python -c "import importlib.util,sys; s=importlib.util.spec_from_file_location('m','<datei>'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)"  # via Bash mit timeout, NUR fuer Library-Module
```

Bei Fehler unterscheiden: echter Fehler (`SyntaxError`, `ImportError`, `ModuleNotFoundError`) = Issue; blosser Side-Effect (`ConnectionError`, `OSError`) = kein Code-Problem. Im Zweifel bei ast-parse bleiben — ein gruener Syntax-Check ist besser als ein Preflight der Produktions-Side-Effects ausloest.

### 3. .env-Vollstaendigkeit

Falls der `python-env-audit`-Skill verfuegbar: verwende ihn. Sonst inline:

- `os.getenv`/`os.environ`-Calls aus Code sammeln
- `.env` lesen
- Diff melden

CRITICAL wenn `code_vars - env_vars` nicht leer.

### 4. Requirements pruefen

```bash
pip check
```

Liefert Konflikte/fehlende Deps. Bei Fehler: melden. Wenn Projekt eine `requirements-lock.txt` hat: zusaetzlich die installierten Versionen mit der Lock-Datei vergleichen.

Wichtig: in der korrekten venv ausfuehren — pruefe zuerst ob `.venv/` oder `venv/` im Projekt-Root, dann das venv-Python verwenden.

### 5. Debug-Relikte suchen

Suche im produktiven Code (NICHT in `tests/`):

- `print(...)` ausserhalb von `if __name__ == "__main__":` und CLI-Entry-Points
- `breakpoint()` — immer Issue
- `pdb.set_trace()` — immer Issue
- `import ipdb`, `import pdb` ohne Verwendung in einem klaren Debug-Tool
- `# TODO` und `# FIXME` (informativ, nicht blocking)
- `# XXX`, `# HACK` (informativ)
- `console.log` (falls JS/HTML im Repo)
- Hartcodierte Test-IDs / Test-Tokens (`123456789`, `test_token_xxx`)

Per `Grep` mit den Patterns. Pro Treffer eine Zeile mit Datei:Zeile.

### 6. Konfig-Syntax

- `requirements.txt` parsen — keine doppelten Pakete, keine `==` neben `>=` fuer dasselbe Paket
- `pyproject.toml` (falls vorhanden) — TOML-Syntax pruefen
- `setup.py` / `setup.cfg` — Syntax pruefen
- Bei Discord-System: `config/config.json` validieren (Feature-Flags-Schema, siehe state-json-validator)
  - **Inline-Fallback wenn `state-json-validator` nicht verfügbar:** prüfen ob `config/config.json` valides JSON parst UND ein `features`-Key auf Top-Level existiert; fehlt/kaputt → No-Go-Finding.
- Bei FootstepPro: keine extra Configs noetig

### 7. Versions-Konsistenz

- Existiert `VERSION`-Datei? -> Inhalt lesen
- Existiert `__version__` in einem Haupt-Modul? -> per AST extrahieren
- `CHANGELOG.md` letzter Versionseintrag
- Diese drei vergleichen — Drift melden

### 8. Lint (optional, wenn vorhanden)

Falls `ruff`, `flake8`, oder `pylint` in den Deps: einen schnellen Run machen. Ergebnisse als INFO, nicht als blocker.

```bash
ruff check .
# oder
flake8 . --max-line-length=120
```

## Report-Format

```
deploy-preflight fuer <projekt-name>
====================================
Branch:      <git branch>
HEAD:        <git rev short> "<git commit msg first line>"
Zeitpunkt:   <ISO>

[1] Tests:               24/24 PASS
[2] Importierbarkeit:    29/29 OK
[3] ENV-Audit:           OK (40 Variablen synchron)
[4] pip check:           OK
[5] Debug-Relikte:       2 issues
    - bots/admin/cogs/cleanup.py:88  print("removing user", user_id)
    - bots/monitor/heartbeat.py:14   # TODO: schwellwert konfigurierbar machen (informativ)
[6] Config-Syntax:       OK
[7] Versions:            VERSION=4.1.0, __version__=4.1.0, CHANGELOG=4.1.0  -> OK
[8] Lint (ruff):         3 warnings (informativ)

============================
Empfehlung:  GO mit Vorbehalt
============================

Vor dem Push:
  - print() in cleanup.py:88 entfernen oder zu logger.debug() umstellen

Nicht-blockend:
  - 1 TODO, 3 ruff warnings — beim naechsten Refactor mitnehmen
```

Go/No-Go-Logik:

- **NO-GO**: Tests fail, ENV fehlend, Import-Fehler, `pip check` fail, `breakpoint()`/`pdb` im Code
- **GO mit Vorbehalt**: `print()` im Code, TODOs/FIXMEs, Versions-Drift, Lint-Warnings
- **GO**: alles gruen oder nur INFO-Befunde

### Evidence-Regel fuer den Go-Entscheid (geerntet aus superpowers:verification-before-completion v6.1.1, 2026-07-21)

Jede gruene Report-Zeile braucht **frischen Command-Output aus DIESEM Preflight-Lauf** — kein "lief vorhin schon durch", kein "sollte passen", keine Erinnerungs-Gruens. Pro Zeile vor dem GO: Command wirklich gelaufen? Exit-Code + vollstaendigen Output gelesen (Failures gezaehlt, nicht nur die letzte Zeile)? Erst dann Status eintragen.

Stale-State-Fallen: alter pytest-Lauf/`.pytest_cache` von vor der letzten Code-Aenderung, `pip check` aus der falschen venv, `__pycache__` das einen frischen Syntax-Fehler maskiert, Report-Zeilen aus einem frueheren Preflight derselben Session. Nach jeder Code-Aenderung waehrend des Preflights: betroffene Schritte neu laufen lassen statt das alte Ergebnis weiterzuverwenden.

Zukunft: falls Preflight-Schritte an Subagents delegiert werden (z.B. env-audit als Dispatch) — ein Subagent-"Success"-Report ist keine Evidence; dessen Output/Diff selbst verifizieren bevor die Zeile gruen wird.

## Projekt-spezifische Anpassungen

**Discord-Bot-System**:
- Auf 4 Pflicht-Tests besonders achten (`test_imports.py`, `test_cogs.py`, `test_env_completeness.py`, `test_routes.py`) — wenn die fail, ist das ein Auto-NO-GO.
- DB-Schema-Drift mitchecken wenn `db-schema-diff`-Skill verfuegbar.
- `deploy.sh`-Inhalt parsen — gibt Hinweise auf Server-Pfade die existieren muessen.

**FootstepPro**:
- Tests langsam — bei Zeitnot kann der User den Test-Schritt mit `--skip-tests` skippen, default aber rein.
- `analyzer.py --version` als Smoke-Test ausfuehren.

**FritzBox-Monitor**:
- `deploy.ps1` ist PowerShell — Skill laeuft auf Windows-Maschine, das ist OK.
- `heartbeat.txt`-Schreib-Test: `python fritzbox_check.py --dry-run` einmal durch.

## Edge Cases

- **Pre-Push-Hook im Repo**: wenn `.git/hooks/pre-push` existiert, kann der Inhalt zusaetzliche Checks vorschreiben — kurz pruefen und im Report erwaehnen.
- **Uncommittete Aenderungen**: `git status --porcelain` — wenn nicht leer, melden ("ungetrackte oder uncommittete Aenderungen — Deployment basiert NICHT auf dem aktuellen Zustand").
- **Nicht-gepushter Branch**: Distance zu `origin/<branch>` zeigen.
- **Deploy-Skript-Sanity**: `deploy.sh`/`deploy.ps1` einmal lesen — falls dort hartcodierte alte Pfade stehen, INFO.

## Changelog

- 1.1.0 (2026-07-21): Evidence-Regel fuer den Go-Entscheid + Stale-State-Fallen + Zukunfts-Hinweis Subagent-Verifikation (geerntet aus superpowers:verification-before-completion v6.1.1).
- 1.0.0 (2026-06-01): Initialversion.
