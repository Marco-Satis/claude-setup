---
name: code-doc-sync
version: 1.0.1
last-reviewed: 2026-06-01
description: Vergleicht die Projekt-Dokumentation (CODE_DOKUMENTATION_*.md, README.md, COWORK.md, CLAUDE.md) mit dem aktuellen Code-Stand und meldet Abweichungen. Findet undokumentierte neue Module/Funktionen/Cogs, dokumentierte aber geloeschte oder umbenannte Elemente, ueberholte Zeilenzahl-Angaben (z.B. "analyzer.py (1885 lines)") und veraltete Beispiele. Generiert einen Diff-Report im Stil "Doku sagt X, Code sagt Y". Trigger wenn der User von "Code-Doku synchron", "Doku aktualisieren", "ist die Doku noch aktuell", "stimmt CODE_DOKUMENTATION noch", oder nach groesseren Refactorings spricht.
---

# code-doc-sync

Findet die Stellen, an denen die Markdown-Doku schon laenger nicht mehr zum Code passt — bevor neue Mitarbeitende oder zukuenftige Claude-Sessions sich darauf verlassen.

## Wofuer

des Nutzers Projekte haben grosse handgepflegte Doku-Files (CODE_DOKUMENTATION_FOOTSTEP.md, CODE_DOKUMENTATION fuer Discord, etc.) mit Modul-Listen, Zeilenzahl-Angaben und Architektur-Beschreibungen. Bei Refactorings ueberlebt die Code-Aenderung, aber die Doku driftet stumm weg. Bei 29 Modulen (FootstepPro), 175+ Modulen (Discord), 9 Modulen (FritzBox) ist manuelles Abgleichen nicht realistisch. Der Skill macht den Diff sichtbar.

## Trigger

- "Pruef ob die Doku noch stimmt"
- "Was ist seit dem letzten Doku-Update neu/weg?"
- "CODE_DOKUMENTATION aktualisieren"
- Nach groesseren Refactorings
- Vor einem Release / vor neuem Mitarbeitenden / vor Anlernen einer neuen Claude-Session

## Eingabe-Dokumente

Per Glob im Projekt:

- `CODE_DOKUMENTATION*.md` (FootstepPro, Discord)
- `README.md`
- `CLAUDE.md`
- `COWORK.md`
- `docs/SESSION_LOG.md` (FootstepPro)
- `ARCHITEKTUR*.md`, `architecture*.md`
- `docs/analyses/*.md` mit Modul-Listen

Wenn der User explizit eine Datei nennt: nur die. Sonst alle.

## Workflow

### 1. Modul-Inventar aus dem Code

Scanne alle `.py`-Dateien (ohne `venv/`, `__pycache__/`, `node_modules/`, `tests/fixtures/`).

Erfasse pro Datei:
- Datei-Pfad relativ zum Projekt-Root
- **Zwei Schluessel: vollstaendig (`tests/test_basic.py`) UND Basisname (`test_basic.py`)** — die Doku referenziert oft nur den Basisnamen, der Skill darf das nicht als STALE markieren
- Zeilenzahl (`wc -l` oder `len(open(file).readlines())`)
- Top-Level-`def` und `class` (per AST)
- Kurzbeschreibung aus dem Modul-Docstring (erste Zeile)
- Imports der wichtigsten Symbole (`from .x import y` -> y ist von Modul x)

Resultat: `code_inventory[file_path] = {lines, top_level_defs, classes, docstring_summary, basename}`.

### 1a. Pfad-Normalisierung beim Vergleich

Wenn Doku ein Modul nur als Basisname nennt (z.B. `test_basic.py`) und im Code unter `tests/test_basic.py` liegt: das ist KEIN Drift. Pflege ein Mapping `basename -> full_path` und vergleiche tolerant. Doku verweist also auf Modul X wenn entweder der full_path oder der basename matcht.

Klassische False-Positive-Quellen: `analyzer.py` (Root) vs. `bots/admin_bot.py` haben gleichen Basename `analyzer.py` nicht, aber bei Tests passiert das oft.

### 2. Inventar aus der Doku

Pro Doku-File: scanne nach Modul-Listen.

Heuristik fuer Modul-Erwaehnungen:

- Code-Bloecke mit Datei-Listings:
  ```
  analyzer.py              CLI + Orchestrierung
  band_analyzer.py         12-Band Butterworth
  ```
- Inline-Erwaehnungen mit Backticks: `` `analyzer.py` `` -> Modul wird genannt
- Headers wie `## metrics.py`
- Tabellen: `| Modul | Zweck |`

Pro Doku-Erwaehnung:
- Datei-Name
- Doku-Datei und Zeile
- Falls Zeilenzahl angegeben (`analyzer.py (1885 lines)`): Wert mitnehmen
- Falls Funktions-/Klassenname genannt: separater Eintrag

Resultat: `doc_inventory[doc_file][module_name] = {claimed_lines, claimed_purpose, line_in_doc}`.

### 3. Diff

Berechne pro Modul:

**Modul-Existenz:**
- In Code, nicht in Doku -> **MISSING_IN_DOC** (medium)
- In Doku, nicht in Code -> **STALE_IN_DOC** (high — Doku verweist auf nicht existierendes)

**Zeilenzahl-Drift:**
- Doku sagt `analyzer.py (1885 lines)`, Code hat 2103 Zeilen -> **OUTDATED_LINES**
- Schwellwert: > 5% Abweichung melden, sonst INFO oder ignorieren

**Funktions-/Klassen-Drift:**
- Doku erwaehnt `compute_core_metrics()`, im Code nicht (mehr) -> **STALE_FUNCTION**
- Code hat neue oeffentliche Funktion, Doku erwaehnt sie nicht -> **MISSING_FUNCTION** (low priority)

**Architektur-Beschreibungen:**
- Datenfluss-Diagramm in CLAUDE.md (`module_a -> module_b`): pruefe per AST, ob `module_a` `module_b` importiert. Wenn nicht: **DATAFLOW_DRIFT** (eher informativ — Diagramme sind oft konzeptuell)

### 4. CLI-/Subcommand-Drift (FootstepPro speziell) — implementiert

CLAUDE.md listet alle `analyzer.py`-Subcommands in einem Code-Block. So gehst du vor:

**4a. Subcommands aus dem Code extrahieren (per AST):**

```python
import ast
src = Path("analyzer.py").read_text(encoding="utf-8")
tree = ast.parse(src)

cli_commands = set()
for node in ast.walk(tree):
    # argparse subparsers add: subparsers.add_parser("analyze", ...)
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "add_parser":
            if node.args and isinstance(node.args[0], ast.Constant):
                cli_commands.add(node.args[0].value)
        # alternative: click @click.command(name="...")
        # oder: typer.Typer + @app.command("...")
```

**4b. Subcommands aus der Doku extrahieren:**

In `CLAUDE.md` (und `README.md`, falls eine CLI-Liste dort ist) suche Code-Bloecke der Form:

```
python analyzer.py analyze <wav> [...]
python analyzer.py compare <wav_a> <wav_b>
```

Per Regex `python\s+analyzer\.py\s+(\w+)` -> Set von dokumentierten Commands.

**4c. Diff:**

- Code hat, Doku nicht -> **HIGH** (`MISSING_IN_DOC` fuer Subcommand)
- Doku hat, Code nicht -> **CRITICAL** (`STALE_IN_DOC` fuer Subcommand — User wuerde versuchen den Befehl zu nutzen und scheitern)

### 5. Cog-Drift (Discord-System)

Pro Bot-Modul (`bots/<x>_bot.py`): suche die `COGS = [...]`-Liste. Vergleiche mit:

- `cogs/*_cog.py` per Glob (was tatsaechlich existiert)
- Cog-Erwaehnungen in `CODE_DOKUMENTATION_DC_BOTS.md` (inkl. Cog-Tabelle, Permission-Tabellen, Feature-Flag-Tabellen)

Diff: neuer Cog ohne Eintrag in COGS-Liste, dokumentierter Cog ohne Datei, Datei ohne COGS-Eintrag.

### 6. SESSION_LOG.md (FootstepPro)

Pruefe ob der Stand "29 Module" / "v1.x.y" / "alle Phasen abgeschlossen" mit der echten Anzahl Module und der Versionsnummer in `constants.py` zusammenpasst. Drift melden.

### 7. Report

Schreibe nach `docs/analyses/code_doc_sync_<DATUM>.md`:

```markdown
# Code-Doku-Sync — <DATUM>

## Zusammenfassung
- Module im Code:        29
- Module in CODE_DOKUMENTATION_FOOTSTEP.md: 27 (2 fehlen)
- Module nur in Doku:    1 (geloescht?)
- Zeilenzahl-Drift:      8 Module mit > 5% Abweichung

## CRITICAL (Doku verweist auf nicht-existierende Datei)
- COWORK.md L93: `compressor_sim_v2.py` -> Datei nicht gefunden im Code

## HIGH (Code hat Modul, Doku nicht)
- `analysis_cache.py`     (vorhanden seit ?, in keiner Doku)
- `windows_registry.py`   (vorhanden, nur in CLAUDE.md erwaehnt aber nicht detailliert)

## MEDIUM (Zeilenzahl)
- analyzer.py            Doku: 1885 lines, Code: 2103 lines (+12%)
- band_analyzer.py        Doku: 612 lines,  Code: 580 lines (-5%)

## INFO (Funktions-Drift)
- `compute_core_metrics()` in CLAUDE.md L132 erwaehnt — im Code vorhanden (OK)
- `apply_psychoacoustics()` in CLAUDE.md L92 erwaehnt — im Code vorhanden (OK)

## Vorschlag fuer naechste Schritte
1. CODE_DOKUMENTATION_FOOTSTEP.md: Eintraege fuer analysis_cache.py + windows_registry.py ergaenzen
2. Zeilenzahlen einmal komplett refresh (Skript-Vorschlag im Anhang)
3. COWORK.md L93 pruefen — wahrscheinlich Tippfehler oder veralteter Verweis
```

### 8. Fix-Vorschlag (optional)

Wenn der User darum bittet: erzeuge ein `<doku-datei>.suggested.md` mit angepassten Eintraegen. Niemals die Original-Doku ueberschreiben.

Insbesondere ein Skript-Vorschlag, das Zeilenzahlen automatisch refreshen kann — kurzer Python-Snippet in den Report aufnehmen.

## Edge Cases

- **Duplizierte Modul-Erwaehnungen** (manchmal in mehreren Doku-Files): aufzaehlen, nicht doppelt zaehlen.
- **Code-Generierung** (autogenerierte Dateien wie Migrations): aus dem Vergleich ausschliessen.
- **Doku-Zeilen-Brueche**: Modul-Eintrag der ueber zwei Zeilen geht — bei Tabellen aufpassen.
- **Anglisierte Namen in deutscher Doku**: wenn Doku `analyse.py` sagt aber Code `analyzer.py` ist — als Tippfehler markieren, nicht als Drift.
- **Session-Log Eintraege**: chronologisch — nur den letzten Stand mit Code vergleichen, fruehere Eintraege sind absichtlich historisch.

## Sicherheit

- Skill liest nur, schreibt nur in `docs/analyses/`.
- Modifiziert NIEMALS die Original-Doku-Files ohne `.suggested.md`-Suffix.
- Keine Funktions-Bodies aus der Doku zitieren wenn sich der Code geaendert hat (kann veraltete Sicherheits-Patterns dokumentieren).
