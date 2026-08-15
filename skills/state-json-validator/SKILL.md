---
name: state-json-validator
version: 1.0.0
last-reviewed: 2026-06-01
description: Validiert JSON-State-, Config- und Snapshot-Dateien auf Schema-Konformitaet, Korruption, veraltete Felder und Timestamp-Plausibilitaet. Pruefe state.json, metrics.json, docsis_snapshot.json (FritzBox), config.json (Discord Feature-Toggles), Analyse-Cache (FootstepPro). Erkennt korrupte JSON-Dateien und bietet Reparatur an. Trigger wenn der User "JSON kaputt", "state korrupt", "config validieren", "Schema pruefen", "warum sind die Werte komisch" sagt, oder nach Crashes/Updates die State-Konsistenz pruefen will.
---

# state-json-validator

Pruefe JSON-Dateien gegen Erwartungs-Schemas und biete Reparatur fuer korrupte oder veraltete Dateien.

## Wofuer

Alle drei Projekte nutzen JSON fuer State-Management. Wenn ein Cron-Job mitten im Schreiben crasht (FritzBox), wenn ein Bot-Update neue Felder einfuehrt (Discord), oder wenn der Cache aus einer alten Version stammt (FootstepPro), zeigt sich das oft erst Stunden spaeter durch obskure Folgefehler. Der Skill erkennt das frueh und kann repariert anbieten.

## Trigger

- "state.json ist kaputt"
- "Cache stimmt nicht"
- "config.json validieren"
- "Schema fuer X pruefen"
- Nach einem Crash, Update oder verdaechtigen Werten
- Vor einem Deployment als Sanity-Check

## Workflow

### 0. Projekt-Initialisierung pruefen — KLARE Diagnose statt schweigend

Bevor du in den Validierungs-Workflow gehst: Glob die unten gelisteten Pfade. Wenn KEINE der erwarteten JSON-Dateien existiert (auch keine `.tmp`, `.corrupt`, `.bak`-Reste), brich mit klarer Diagnose ab — nicht schweigend "alles OK" melden:

```
state-json-validator
====================
Projektordner:   <pfad>
Status:          NICHT INITIALISIERT — keine erwarteten JSON-Dateien gefunden

Erwartet (nicht vorhanden):
  - state.json
  - metrics.json
  - docsis_snapshot.json
  - state/bot_status.json

Moegliche Ursachen:
  - Projekt wurde noch nie ausgefuehrt (z.B. fritzbox_monitor.py mindestens 1x laufen lassen)
  - Andere Pfade in Verwendung — User: bitte konkreten Pfad angeben
  - Falscher Projekt-Ordner

Naechster Schritt:
  - User fragen: "Wurde das Projekt schon laufen lassen? Gibt es einen anderen Pfad fuer State-Files?"
```

Wenn EINIGE Dateien fehlen, ANDERE da sind: Workflow nur fuer die vorhandenen, fehlende als INFO ("noch nie geschrieben") melden — nicht als CRITICAL.

### 1. JSON-Dateien einsammeln

Bekannte Pfade pro Projekt:

**FritzBox-Monitor**:
- `state.json` (root)
- `metrics.json`
- `docsis_snapshot.json`
- evtl. `state.json.corrupt` (Backup nach Reparatur)

**Discord-Bot-System**:
- `config/config.json` (Feature-Toggles)
- `state/bot_status.json` (Heartbeat — pruefe nicht hier, ist im cron-monitor-check)
- `state/<bot>_<feature>.json` (laufzeit-State pro Cog)

**FootstepPro**:
- `output/cache/<hash>.json` (Analyse-Cache)
- evtl. `state.json` fuer Watcher

Wenn der User einen konkreten Pfad nennt, nur den. Sonst alle bekannten.

### 2. Korruptions-Pruefung

Versuche `json.load(...)` auf jede Datei. Bei `JSONDecodeError`:

- Speichere Inhalt als `<datei>.corrupt` (Backup vor jeder Reparatur, immer).
- Versuche Reparatur in dieser Reihenfolge:
  1. **Trailing-Komma entfernen**: oft Editor-Artefakt
  2. **Letzten unvollstaendigen Eintrag abschneiden**: bei abgebrochenem Schreiben — von hinten nach vorn parsen, bis ein gueltiges Object ende erreicht ist (`}`)
  3. **Mehrere konkatenierte Objects**: `}{` wird ein Trennstrich — splitte und nimm das zuletzt vollstaendige
- Wenn Reparatur gelingt: schreibe `<datei>.repaired.json` und zeige Diff. **NICHT** automatisch ueberschreiben — User entscheidet.
- Wenn nicht: melde Fehler mit der Position aus `JSONDecodeError`.

### 3. Schema-Validierung

Pro bekannten Datei-Typ ein Inline-Schema (kein externes JSON-Schema-File noetig fuer den Anfang):

**FritzBox `state.json`**:
```python
{
    "last_run": str,        # ISO timestamp
    "last_success": str,    # ISO timestamp
    "consecutive_failures": int,  # >= 0
    "last_error": str | None,
    "version": str,
}
```

**FritzBox `metrics.json`**:
```python
{
    "snapshots": [
        {
            "timestamp": str,
            "downstream_power_dbmv": float,
            "upstream_power_dbmv": float,
            "downstream_snr_db": float,
            "errors": dict,
        }
    ],
    "schema_version": int,
}
```

**Discord `config.json`**:
```python
{
    "features": {
        "<bot_name>": {
            "<feature_key>": bool,
            ...
        }
    },
    "schema_version": int,
}
```

**FootstepPro Cache**:
```python
{
    "wav_path": str,
    "wav_mtime": float,
    "wav_size": int,
    "analyzer_version": str,
    "metrics": dict,
    "computed_at": str,
}
```

Pro Eintrag pruefe:
- Pflichtfelder vorhanden
- Typ stimmt
- Timestamp parsebar (ISO 8601 oder Unix-Float)
- `version`-Felder gegen aktuelle Projekt-Version
- Listen-Eintraege in chronologischer Reihenfolge (Drift = wahrscheinlich Korruption)

### 4. Plausibilitaets-Checks

- **Timestamp nicht in der Zukunft**: ein Eintrag mit Timestamp > now ist verdaechtig (Uhrzeit am Server falsch beim Schreiben).
- **Timestamp nicht zu alt**: bei Heartbeat-aehnlichen Files (FritzBox `last_run`) — wenn > 24h, melden.
- **`consecutive_failures` zu hoch**: bei FritzBox > 10 — der Monitor laeuft offenbar leer.
- **Keine Snapshots in `metrics.json` der letzten 24h**: die Erfassungs-Pipeline ist gestorben.
- **`config.json` Feature-Flags**: Pruefe ob jeder im Code genutzte `is_enabled("xyz")` einen Eintrag hat (cross-check mit Grep).

### 5. Versions-Drift

`schema_version` oder `analyzer_version` mit dem Projekt-Stand vergleichen. Bei alter Cache-Version: schlage Loeschung des Caches vor (NICHT automatisch loeschen — User-Entscheidung).

### 6. Schema-Datei generieren (optional)

Wenn der User explizit fragt: erzeuge fuer jede validierte JSON-Datei ein begleitendes `<datei>.schema.json` im JSON-Schema-Format (Draft 2020-12). Damit kann der User in Zukunft auch ohne diesen Skill validieren.

## Report-Format

```
state-json-validator
====================

state.json (FritzBox):
  [OK] gueltige JSON
  [OK] Schema vollstaendig
  [WARN] last_success: 7h alt — Cron laeuft, kommt aber nicht durch
  [WARN] consecutive_failures = 12 — schau in den letzten Log-Eintrag

metrics.json (FritzBox):
  [OK] gueltige JSON
  [WARN] schema_version: 1 (aktuell: 2) — neue Felder fehlen

docsis_snapshot.json (FritzBox):
  [CRITICAL] JSONDecodeError @ pos 4421
  [INFO] Reparaturversuch (Trailing-Komma): erfolgreich
  [INFO] Repariert geschrieben nach: docsis_snapshot.repaired.json
  [INFO] Backup nach: docsis_snapshot.json.corrupt
  Naechster Schritt: pruef diff docsis_snapshot.json docsis_snapshot.repaired.json — falls OK, ersetzen.

config/config.json (Discord):
  [OK] gueltige JSON
  [WARN] feature 'mc_server_status' im Code referenziert (cogs/server.py:42), in config.json nicht definiert
```

## Edge Cases

- **Symlinks**: bei Symlinks die Quelldatei lesen, nicht das Ziel als zusaetzliche Datei zaehlen.
- **Sehr grosse JSON** (>50 MB): warnen und Streaming-Parser empfehlen, hier nicht laden.
- **Encoding**: alles als UTF-8 lesen. Wenn UTF-8 fehlschlaegt: BOM/CP1252 als Fallback, dann nach UTF-8 normalisieren.
- **Atomare Write-Pattern erkennen**: Wenn `<datei>.tmp` existiert und juenger als `<datei>` ist, ist gerade ein Schreibvorgang im Gange — nicht in dem Moment validieren, melden ("write in progress?").
- **Backup-Hygiene**: nach erfolgreicher Reparatur und User-Bestaetigung gibts einen `.repaired.json` und `.corrupt` — User soll den `.repaired.json` selbst nach Pruefung umbenennen.

## Sicherheit

- **Niemals automatisch ueberschreiben** ohne explizite Bestaetigung.
- **Backup vor JEDER Reparatur**, immer mit Suffix `.corrupt`.
- **Werte mit Secrets** (z.B. API-Keys in `state.json`): Im Report nur Variablennamen, nie Werte ausgeben.
