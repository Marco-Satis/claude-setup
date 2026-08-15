---
name: changelog-updater
version: 1.0.0
last-reviewed: 2026-06-01
description: Generiert einen neuen CHANGELOG-Eintrag aus den Git-Commits seit dem letzten Release-Tag. Kategorisiert Commits (Feature, Bugfix, Refactoring, Config-Aenderung), respektiert das bestehende CHANGELOG-Format des Projekts, erkennt Breaking Changes (geaenderte ENV-Variablen, entfernte Funktionen), aktualisiert VERSION-Datei oder __version__ Konstante. Trigger wenn der User "Changelog updaten", "Release-Notes schreiben", "neue Version", "v1.2.3 vorbereiten", "was ist seit dem letzten Release passiert" sagt.
---

# changelog-updater

Bringt CHANGELOG.md auf den Stand der Commits seit dem letzten Tag — ohne dass der User selbst den Git-Log durchscrollen muss.

## Wofuer

der Nutzer Projekte haben aktive Versionierung (Discord v4.1.0, FootstepPro v1.2.0). Releases ohne aktualisierten Changelog sind aergerlich — und der Changelog dann nachzutragen ist nervig, weil der User die Commits aus dem Kopf rekonstruieren muss. Der Skill macht das in 30 Sekunden.

## Trigger

- "Changelog aktualisieren"
- "Was ist seit v1.2.0 passiert?"
- "Release vorbereiten"
- "v1.3.0 macht ich gerade"
- Vor jedem Tag/Release

## Workflow

### 1. Aktuelles Format aus CHANGELOG.md selbst lernen

Lies `CHANGELOG.md`. Statt fest verdrahteter Section-Namen zu raten: parse die letzten 3 Eintraege und sammle die tatsaechlich verwendeten Section-Headings.

```python
# Beispiel-Heuristik:
# Pro Eintrag (zwischen zwei `## v...`-Headern) sammle alle `### XYZ`-Subheaders
# -> { "v1.2.0": ["Hinzugefuegt", "Geaendert", "Behoben", "Documentation Updates"] }
# Diese gefundenen Section-Namen sind die Wahrheit. Verwende sie 1:1 fuer den neuen Eintrag.
```

der Nutzer Projekte verwenden teils deutsche Sektionen ("Hinzugefuegt"/"Geaendert"/"Behoben"), teils englische (Keep-a-Changelog-Style "Added"/"Changed"/"Fixed"), teils Custom-Sections wie "Documentation Updates", "Validierung", "Fixes (Code Review)" mit Prio-Markern wie `[KRITISCH]`. Diese Vielfalt ist absichtlich — kopiere das Muster der letzten Eintraege exakt, statt zu standardisieren.

Wenn Datei leer/fehlt: nach Keep-a-Changelog-Default fragen, sonst initial anlegen mit explizitem Hinweis ("kein bisheriges Format gefunden — schlage Keep-a-Changelog vor, OK?").

### 2. Letzten Tag finden — mit klarem Git-Fallback

Pruefe ZUERST ob das Verzeichnis ein Git-Repo ist:

```bash
git -C <projekt-pfad> rev-parse --git-dir 2>/dev/null
```

**Wenn KEIN Git-Repo:**

Brich nicht still ab — der Skill ist sonst nutzlos und der User wundert sich. Sage explizit:

```
Projekt ist KEIN Git-Repository.

Optionen:
  (a) git init + erstmaligen Commit machen, dann Skill erneut starten
  (b) Skill bedient sich aus CHANGELOG.md selbst — nimm den letzten Eintrag
      als Versions-Anker. Neue Aenderungen kann der Skill aber NUR aus
      User-Beschreibung uebernehmen, nicht automatisch erfassen.
  (c) Skill abbrechen.

Welche Option?
```

Bei Option (b): frage den User nach 3-7 Saetzen, was sich seit dem letzten CHANGELOG-Eintrag geaendert hat — das wird die Eingabe fuer Schritt 4 (Kategorisierung).

**Wenn Git-Repo:**

```bash
git -C <pfad> describe --tags --abbrev=0 2>/dev/null
```

Wenn kein Tag: nimm den Hash des Commits, der die letzte Veraenderung an `CHANGELOG.md` einfuehrte:

```bash
git -C <pfad> log -1 --format="%H" -- CHANGELOG.md
```

Wenn auch das nichts liefert: alle Commits einbeziehen.

Speichere den gefundenen Anker als `LAST_RELEASE`.

### 3. Commits seit LAST_RELEASE einsammeln

```bash
git log <LAST_RELEASE>..HEAD --pretty=format:"%H|%s|%b|%an" --no-merges
```

Parse Zeile fuer Zeile. Felder: hash, subject, body, author.

Filter:
- Merge-Commits ausschliessen (oben schon gemacht)
- Reine Format-/Whitespace-Commits unter `chore:` zusammenfassen
- Revert-Commits speziell handhaben (sehen aus wie negative Eintraege im Log — den ursprünglichen Commit auch entfernen, falls in Range)

### 4. Kategorisieren

Per Heuristik: Subject-Praefix oder Keyword.

| Praefix | Kategorie |
|---------|-----------|
| `feat:`, `feature:`, "add", "added", "neu" | Hinzugefuegt / Added |
| `fix:`, `bugfix:`, "fix", "behebt" | Behoben / Fixed |
| `refactor:`, `chore:`, "refactor" | Geaendert / Changed |
| `remove:`, "entfernt", "deprecate" | Entfernt / Removed |
| `docs:`, "doku" | Dokumentation (eigene Section oder unter Geaendert) |
| `test:` | Tests (eigene Section oder unter Geaendert) |
| `breaking:`, "BREAKING CHANGE" im body | BREAKING (eigene Section oben) |

Wenn Praefix unklar: aus Body und Datei-Aenderungen raten:
- nur `tests/` veraendert -> Tests
- nur `*.md` -> Docs
- neue Datei in `bots/<x>/cogs/` -> Hinzugefuegt (neuer Cog)
- `requirements.txt` veraendert -> Geaendert (Deps)

### 5. Breaking Changes erkennen

Diese Aenderungen markieren als BREAKING:

- `.env`-Variable entfernt oder umbenannt: NUR gegen die getrackte Vorlage `git diff <LAST>..HEAD -- '*.env.example' '*.env.sample'` diffen (enthaelt keine echten Werte). **NIEMALS `git diff` auf echte `.env`-Dateien** — bei getrackter `.env` dumpt das Klartext-Secrets ins Transcript (Leak-Klasse Lesson 2026-05-16). Um nur zu ERKENNEN ob sich eine echte `.env` aenderte: `git diff --name-only <LAST>..HEAD -- '*.env*'` (nur Dateinamen, keine Werte).
- DB-Schema-Aenderungen: per `git diff <LAST>..HEAD -- '*schema*' '*migration*'`
- Funktionssignaturen entfernt/umbenannt: schwer per Heuristik — nur melden wenn Commit-Subject "BREAKING" sagt
- Kommando-Linie geaendert (FootstepPro `analyzer.py` Subcommands): pruefe `cli`-Bezeichnungen in den Diffs

Breaking Changes als eigene Sektion **oben** im Eintrag:

```markdown
### Breaking Changes
- `BOT_TOKEN_GAME` umbenannt zu `DISCORD_TOKEN_GAME` ([abc1234](url))
```

### 6. Neue Versionsnummer vorschlagen

Wenn der User keine vorgegeben hat: SemVer-Vorschlag basierend auf den Findings:

- Breaking Changes -> Major (1.0.0 -> 2.0.0)
- Nur Features, keine Breaking -> Minor (1.0.0 -> 1.1.0)
- Nur Fixes/Refactor -> Patch (1.0.0 -> 1.0.1)

Frage: "Vorschlag: v1.3.0. OK oder andere Nummer?" — nur wenn der User es selbst nicht gesagt hat.

### 7. Eintrag schreiben

Format an bestehende Eintraege anlehnen. Beispiel:

```markdown
## [1.3.0] - 2026-04-30

### Hinzugefuegt
- Neuer `optimize`-Subcommand: kombiniert analyze + config generate ([abc1234](#))
- Heatmap-Visualisierung in DOCSIS-Analyse ([def5678](#))

### Behoben
- Crash bei Mono-WAVs in `band_analyzer.py` ([ghi9012](#))
- `state.json` wurde nicht atomar geschrieben ([jkl3456](#))

### Geaendert
- Hann-Fenster-Kompensation korrigiert (1/sqrt(mean(h^2)) statt 1/mean(h)) ([mno7890](#))

### Entfernt
- Veraltete `--legacy-mode`-Flag ([pqr1234](#))
```

Hash-Links nur wenn das Repo eine Forge-URL hat (in `git config --get remote.origin.url`). Sonst Hash plain in Klammern.

### 8. VERSION-Datei und __version__ aktualisieren

Pruefe per Glob/Grep:
- `VERSION` (Discord-System)
- `constants.py` mit `VERSION = "1.2.0"` (FootstepPro)
- `__init__.py` mit `__version__`
- `pyproject.toml` mit `version = ...`

Schreibe die neue Versionsnummer in alle gefundenen Stellen — aber NUR wenn der User die Versionsnummer bestaetigt hat. Sonst Diff-Vorschlag.

### 9. Schreibvorgang

Schreibe den neuen Eintrag direkt unter `## [Unreleased]`-Section (falls vorhanden), sonst direkt nach dem `# Changelog`-Header.

NICHT die alten Eintraege anfassen. NICHT die `[Unreleased]`-Section loeschen.

## Edge Cases

- **Kein Tag im Repo**: nimm Hash + Datum als "vorlaeufiger Anker", User kann spaeter taggen.
- **Sehr viele Commits** (> 50): gruppiere per Datei-Pfad + Tag, sonst wird der Eintrag unlesbar.
- **Co-author-Commits**: ignoriere `Co-authored-by` im Body, kein eigener Eintrag.
- **Squash-Merges**: meist haben die einen guten Subject, das reicht. Body checken nur bei Bedarf.
- **Versions-Drift zwischen `VERSION`-Datei und CHANGELOG**: melden bevor du was schreibst — manchmal ist die Datei schon hoch, der Changelog hinterher.

## Sicherheit

- **Nichts uebernehmen ohne dass der User die Versionsnummer freigegeben hat**.
- **Bestehende Eintraege niemals aendern**.
- **`.env`-Variablen-Beispiele NICHT in den Changelog kopieren** — nur Namen ("`API_KEY` umbenannt zu `DISCORD_API_KEY`"), keine Werte.

## Report nach Erstellung

```
Neuer Eintrag:    1.3.0 (vorgeschlagen, bestaetigt)
Commits:          14 zwischen v1.2.0..HEAD
Kategorien:       3 Hinzugefuegt, 4 Behoben, 5 Geaendert, 1 Entfernt, 1 Breaking
Geaendert:        CHANGELOG.md, VERSION (3.2.1 -> 3.3.0), constants.py (VERSION="3.3.0")

Naechste Schritte:
  1. CHANGELOG.md gegenlesen (besonders die Kategorisierung)
  2. git tag v1.3.0
  3. deploy-preflight ausfuehren
```
