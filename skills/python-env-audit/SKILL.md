---
name: python-env-audit
version: 1.0.0
last-reviewed: 2026-06-01
description: Audit .env-Dateien gegen tatsaechliche Code-Verwendung in Python-Projekten. Findet fehlende Variablen (im Code referenziert, aber nicht in .env), verwaiste Variablen (in .env aber nirgends benutzt), hartcodierte Secrets im Code und Inkonsistenzen zwischen .env und .env.example. Verwende diesen Skill, sobald der User von "env audit", ".env pruefen", "ENV-Vollstaendigkeit", "fehlende ENV-Variablen", "ungenutzten Variablen", oder vor Deployments im Discord-Bot-System, FootstepPro oder FritzBox-Monitor spricht. Trigger auch wenn der User einen Config-Drift vermutet oder eine .env.example aktualisieren will.
---

# python-env-audit

Vergleicht `.env`-Dateien mit dem tatsaechlichen Verbrauch im Python-Code und meldet Drift in beide Richtungen.

## Wofuer

des Nutzers Projekte haben deutlich mehr ENV-Variablen als ein Mensch im Kopf behalten kann (Discord Bot System ~40, FritzBox 16, FootstepPro nutzt Pfad-Konstanten in `constants.py`). Manuelle Synchronisation fuehrt zu zwei klassischen Bugs: Bot startet nicht weil eine ENV fehlt, oder der `.env` schleppt monatelang tote Eintraege mit. Dieser Skill findet beides automatisch.

## Trigger

Verwende diesen Skill wenn der User:

- Vor einem Deployment die Config validieren moechte
- Eine `.env.example` aktualisieren will
- Berichtet "Variable XY ist nicht gesetzt" oder aehnliche Boot-Fehler
- Refactoring an Config-Pfaden gemacht hat
- Ein neues Feature eingebaut und noch nicht weiss, welche neuen ENVs noetig sind

## Workflow

### 1. Projekt scannen

Fuer jedes `.py`-File im Projektordner (ohne `venv/`, `.venv/`, `__pycache__/`, `node_modules/`, `tests/fixtures/`):

Suche nach diesen Mustern und sammele die ENV-Namen ein:

```python
os.getenv("VAR_NAME")
os.getenv("VAR_NAME", default)
os.environ["VAR_NAME"]
os.environ.get("VAR_NAME")
load_dotenv() / dotenv_values()  # markiere die Datei als ENV-Konsumenten
```

Fuer dynamische Lookups wie `os.getenv(varname)` nur warnen ("dynamic key in {file}:{line}"), nicht raten.

Tools: `Grep` mit den Patterns `os\.getenv\s*\(`, `os\.environ\[`, `os\.environ\.get\s*\(`. Sammele Treffer in einer Liste mit `(var_name, datei, zeile)`.

### 2. .env-Dateien lesen

Lies alle `.env`, `.env.example`, `.env.template` aus dem Projekt (Discord-Bot-System hat sie meist unter `config/`). Parse jeweils zu einem `dict[name -> raw_value]`. Kommentarzeilen (`#`) und Leerzeilen ignorieren. Werte mit Anfuehrungszeichen entstrippen.

### 3. Drift-Analyse

Erzeuge drei Mengen:

- **Code-Variablen**: alle in Punkt 1 gesammelten Namen
- **Env-Variablen**: alle in `.env` definierten Namen
- **Example-Variablen**: alle in `.env.example` definierten Namen

Berechne und melde:

- **Fehlend in `.env`**: `code_vars - env_vars` mit Datei:Zeile als Quelle. Kritisch — Boot-Risiko.
- **Verwaist in `.env`**: `env_vars - code_vars`. Warnung — toter Eintrag, evtl. Rest aus altem Refactoring.
- **Fehlend in `.env.example`**: `code_vars - example_vars`. Mittel — neue Devs koennen das Projekt nicht starten.
- **Inkonsistenz `.env` vs `.env.example`**: Variablen nur in einer der Dateien (ohne als Code-Variable bekannt zu sein).

### 4. Hartcodierte Secrets erkennen — in `.py` UND in `.env*`-Dateien

**Im Python-Code:**
- Strings die wie Discord-Tokens aussehen: `[A-Za-z0-9_-]{24}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,}`
- Bot-Token-Zuweisungen ausserhalb von `os.getenv`: `(token|api_key|password|secret|webhook)\s*=\s*["'][^"']{16,}["']` (case-insensitive)
- FritzBox-Credentials hartkodiert: `username\s*=\s*["']` mit nicht-leerem Wert direkt im Code

**In allen `.env*`-Dateien (nicht nur `.env.example`)** — kritisch wegen `.env.new`, `.env.backup_*`, `.env.working_*`:

Pro gefundener `.env`-Datei: pruefe jeden Wert. Heuristik fuer "echter Secret-Wert":

- Discord-Bot-Token-Pattern (siehe oben) als Wert
- Wert mit > 20 Zeichen, der nicht offensichtlich Platzhalter ist (`xxxxxx`, `<your-...>`, `CHANGE_ME`, `your_token_here`, leer)
- Wert mit mindestens je einem Buchstaben und einer Ziffer und (nicht-trivialer Sonderzeichen-Mix)
- Bei Variablen-Namen mit `TOKEN`, `SECRET`, `KEY`, `PASSWORD`, `PASS`, `WEBHOOK`, `OAUTH`, `CLIENT_ID`, `CLIENT_SECRET`, `RCON`, `SMTP_PASS`, `API_TOKEN`: schon wahrscheinliche Werte (>10 Zeichen) als Treffer melden.

Diese Funde sind **kritisch** — die Datei enthaelt echte Secrets im Klartext und kann ueber Git/OneDrive/Backup unbemerkt rausgehen.

**Spezial-Pruefung fuer alternative `.env`-Varianten:**

Wenn der Projektordner mehrere `.env*` enthaelt (z.B. `.env`, `.env.new`, `.env.backup_<datum>`, `.env.working_<datum>`):

- Jede zeigt potenziell Secrets aus einer anderen Phase / Schema-Version.
- Im Report eine Tabelle: Variable | .env | .env.new | .env.example | (jeder mit "leer" / "platzhalter" / "WERT VORHANDEN").
- Werte NIE im Report ausgeben — nur "WERT VORHANDEN".
- Wenn `.env.example` Variablen hat, die in keiner Live-`.env`-Variante sind (Schema-Drift): melden.
- Wenn `.env.new` oder `.env.backup_*` Secrets enthalten: **CRITICAL** mit Empfehlung "Datei in nicht-getrackten Ordner verschieben oder loeschen, Tokens rotieren falls die Datei jemals committet wurde".

### 5. Report ausgeben

Format (Konsole + optional `output/env_audit_<timestamp>.md`):

```
ENV-Audit fuer <projekt-name>
============================
.env-Pfad:           config/.env
.env.example-Pfad:   config/.env.example
Python-Dateien:      <count>

KRITISCH (Boot-Risiko):
  - DISCORD_TOKEN_GAME    referenziert in cogs/admin.py:42, fehlt in .env
  - DB_PATH               referenziert in db.py:15, fehlt in .env

WARNUNG (verwaist):
  - OLD_WEBHOOK_URL       in .env definiert, im Code nicht verwendet
  - LEGACY_API_KEY        in .env definiert, im Code nicht verwendet

INFO (.env.example-Drift):
  - NEW_FEATURE_FLAG      in .env, fehlt in .env.example

KRITISCH (hartkodierte Secrets):
  - cogs/notify.py:88   sieht aus wie Discord-Token (Pattern-Match)
```

Wenn keine Probleme: positiver Einzeiler ("ENV-Audit OK — N Variablen synchron").

### 6. Aktualisierte .env.example anbieten

Wenn der User explizit darum bittet (oder bei viel Drift selbst vorschlagen):

Generiere eine neue `.env.example` mit:
- Allen Code-Variablen (auch wenn aktuell nicht in der alten Example)
- Werten als Platzhalter (`<your-value-here>` oder leer)
- Kommentaren aus der Quelldatei (Datei:Zeile, woher die Variable stammt)
- Bestehende Kommentare aus der alten Example beibehalten wenn moeglich

Schreibe die Datei NICHT automatisch ueber die echte `.env.example` — biete sie als Diff oder unter `.env.example.suggested` an.

## Projekt-spezifische Hinweise

**Discord Bot System** (`~/projects/Discord_Bots`, Syncthing-synct PC↔netcup): ENVs liegen unter `config/.env`. Die Variablen sind in 13 Sektionen gruppiert (Bot-Tokens, DB-Pfade, MC-Server, Feature-Flags). Sektions-Header (`# ===== SECTION =====`) beim Generieren der Example beibehalten.

**FootstepPro** (`C:\Users\<user>\OneDrive\Dokumente\AudioSetup\FootstepAnalyzer`, **Windows-lokal** — kein Syncthing-Sync, auf netcup nicht vorhanden): Hat keine .env, sondern Konstanten in `constants.py`. Skill kann hier degradiert laufen: hartcodierte Pfade (z.B. `C:\Program Files\EqualizerAPO\config\`) erkennen und melden, aber kein .env-Diff durchfuehren. Klarstellen im Report.

**FritzBox Monitor** (`~/projects/FritzBox Docsis logging`, Syncthing-synct PC↔netcup): ENVs unter `.env.example` im Root. 16 Variablen (FRITZBOX_HOST, FRITZBOX_USER, SMTP_*, ALERT_THRESHOLD_*, etc.). Kompakt, aber Drift hier ist besonders kritisch weil der Cron-Job sonst still scheitert.

## Edge Cases

- **f-Strings mit ENV in Pfaden**: `os.getenv("DATA_DIR") + "/foo"` — ist OK, wird erkannt.
- **Default-Werte mit Komma-Listen**: `os.getenv("ALLOWED_IDS", "1,2,3").split(",")` — auch OK.
- **Test-Fixtures**: `tests/` ueberspringen, sonst kommen Test-Dummys in den Report.
- **Mehrere `.env` (z.B. `.env.dev`, `.env.prod`, `.env.new`, `.env.backup_*`)**: alle anzeigen, ueberschneidung als Tabelle (Variable | dev | prod | example | new | ...). Drift in der Sektions-Struktur (z.B. `.env.example` v4.1 vs `.env` v3.2) explizit als INFO melden.
- **Variablen mit Praefix**: Discord-Bots haben `DISCORD_TOKEN_GAME`, `DISCORD_TOKEN_MONITOR` — als getrennte Eintraege behandeln, nicht zusammenfassen.

## Nicht tun

- Keine Werte aus der echten `.env` im Report ausgeben (Secrets!). Nur Variablennamen.
- `.env` nicht automatisch ueberschreiben.
- Keine "Reparatur" vorschlagen, die hartkodierte Defaults in .env wandert (das soll der User entscheiden).
