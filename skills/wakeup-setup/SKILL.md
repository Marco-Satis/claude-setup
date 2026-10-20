---
name: wakeup-setup
version: 2.0.1
last-reviewed: 2026-05-28
description: "Richtet Wake-Up-Polling fuer Long-Run/Nacht-Sessions ein — Multi-Session-Registry. Jede registrierte Session setzt eigenen ScheduleWakeup auf den 5h-Nutzungszyklus (gilt für alle Pro-/Max-Stufen), mit shared Window-Reset-Cache und Sub-Commands (register/list/remove/status). Endziel: der Nutzer aktiviert in jedem relevanten Chat einmal, ab dann triggert sich jede Session beim Window-Reset selbst."
when_to_use: wakeup einrichten, long run setup, nacht session, session ueber nacht, autonom ueber stunden, rate-limit-resume, ScheduleWakeup einrichten, wake-up polling, window-reset wake-up, multi-session wakeup, mehrere chats wakeup, wakeup liste, wakeup status
argument-hint: Sub-Command (register | list | remove | status) optional + Task-Name. Default ohne Argument = "register" mit der Nutzer-Frage nach Task-Name.
allowed-tools: Read Write Bash
userInvocable: true
---

# wakeup-setup v2 — Multi-Session-Wake-Up-Registry

Zweck: der Nutzer kann **mehrere Chat-Sessions** parallel mit Wake-Up versorgen. Jede Session setzt fuer sich eigenen ScheduleWakeup. Endziel: bei jedem Long-Run-Chat einmal `/wakeup-setup` triggern — bei Window-Reset feuern alle Sessions parallel und arbeiten ihr jeweiliges PROGRESS-File ab.

**Architektur-Entscheidung:** Wake-Up ist und bleibt Session-bound (ScheduleWakeup feuert nur in der Session die es gesetzt hat). Die "Multi-Session"-Logik dieses Skills ist eine **Registry** + **shared Window-State** — kein zentraler Scheduler. der Nutzer triggert pro Chat einmal, die Registry hilft den Ueberblick zu behalten.

## Sub-Commands

| Command | Was passiert |
|---|---|
| `/wakeup-setup` oder `/wakeup-setup register <task>` | Aktuelle Session in `wakeup_sessions.json` eintragen + ScheduleWakeup setzen |
| `/wakeup-setup list` | Alle aktiven Sessions zeigen mit naechster Wake-Up-Zeit |
| `/wakeup-setup remove` | Aktuelle Session aus Registry entfernen + Notiz "kein neuer Wake-Up" |
| `/wakeup-setup status` | Status aktuelle Session + globaler Window-Reset + Anzahl aktive Sessions |

## Vor dem Start

1. Sub-Command parsen (Default = `register`)
2. State-Files lesen:
   - `~/.claude/state/wakeup_window_state.json` (globaler Window-Reset, Cache)
   - `~/.claude/state/wakeup_sessions.json` (Multi-Session-Registry)
3. Aktuelle Session-Identifier ermitteln (CWD-Pfad-Hash, siehe unten)

## Session-Identifier

Da CC keine stabile Session-UUID exponiert, nutzen wir das **Working-Directory** als Proxy:

```python
import os, hashlib
from pathlib import Path

def get_session_id():
    cwd = str(Path.cwd().resolve())
    # Worktrees haben Format <repo>/.claude/worktrees/<slug>
    # Slug ist eindeutig pro Worktree
    return hashlib.sha256(cwd.encode()).hexdigest()[:12]

def get_session_label():
    cwd = Path.cwd().resolve()
    # Letzter Pfad-Teil als lesbares Label
    return cwd.name
```

Konsequenz: pro Worktree/CWD genau **eine** Wake-Up-Registrierung. Bei mehreren CC-Sessions im gleichen Worktree ueberschreibt die letztere — der Nutzer-Notiz im Output wenn das passiert.

## State-File-Schemata

### `wakeup_window_state.json` (unveraendert, global)

```json
{
  "window_reset_at": "2026-05-18T19:30:00+02:00",
  "last_updated": "2026-05-18T14:30:00+02:00",
  "source": "marco_input | fallback_5h15min | auto_extended"
}
```

### `wakeup_sessions.json` (NEU, Multi-Session-Registry)

```json
{
  "schema_version": 1,
  "sessions": {
    "<session_id_hash>": {
      "session_label": "silly-murdock-670cb2",
      "cwd": "~/projects/Discord_Bots/.claude/worktrees/silly-murdock-670cb2",
      "task_name": "pyright-error-cleanup",
      "progress_file": "~/.claude/audit/PROGRESS_pyright-cleanup_2026-05-18.md",
      "registered_at": "2026-05-18T07:15:00+02:00",
      "next_wake_at": "2026-05-18T19:35:00+02:00",
      "status": "active"
    }
  },
  "last_updated": "2026-05-18T07:15:00+02:00"
}
```

Pfad-Werte im Beispiel plattformneutral (`~` = Home der jeweiligen Seite); im realen Registry-File steht der absolute CWD der jeweiligen Plattform (Windows: `C:\Users\<user>\...`, netcup: `$HOME/...`).

Status-Werte: `active` (Wake-Up aktiv) / `paused` (manuell pausiert, kein Schedule) / `done` (alle Phasen done, auto-deregistriert).

## Phase 1 — Sub-Command: `register` (Default)

### Schritt 1: Task-Name auswerten
- Argument vorhanden? → nimm es
- Sonst: der Nutzer-Frage „Task-Name fuer Wake-Up (Default = `<session_label>-task`)?"

### Schritt 2: Window-Reset-Zeit (Cache-First)

```python
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path

STATE_FILE = Path.home() / ".claude" / "state" / "wakeup_window_state.json"
BERLIN_OFFSET = timedelta(hours=2)  # CEST — bei Winter umstellen auf +1

def get_window_reset():
    now = datetime.now(timezone(BERLIN_OFFSET))
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        reset_at = datetime.fromisoformat(state["window_reset_at"])
        if now < reset_at:
            return reset_at, "cached"
        # Cache veraltet — Window wurde inzwischen resettet
    return None, "needs_marco_input"
```

Bei `needs_marco_input`: der Nutzer-Frage wie in v1.0 (Uhrzeit/Restzeit/Token-Stand/Fallback 5h15min).

### Schritt 3: Session in Registry eintragen (Atomic-Write)

```python
SESSIONS_FILE = Path.home() / ".claude" / "state" / "wakeup_sessions.json"

def register_session(session_id, label, cwd, task_name, progress_file, next_wake_at):
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SESSIONS_FILE.exists():
        data = json.loads(SESSIONS_FILE.read_text())
    else:
        data = {"schema_version": 1, "sessions": {}}
    
    overwrite = session_id in data["sessions"]
    data["sessions"][session_id] = {
        "session_label": label,
        "cwd": cwd,
        "task_name": task_name,
        "progress_file": progress_file,
        "registered_at": datetime.now(timezone(BERLIN_OFFSET)).isoformat(),
        "next_wake_at": next_wake_at.isoformat(),
        "status": "active"
    }
    data["last_updated"] = datetime.now(timezone(BERLIN_OFFSET)).isoformat()
    
    # Atomic write
    tmp = SESSIONS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(SESSIONS_FILE)
    return overwrite
```

Bei Overwrite: der Nutzer-Notiz „Vorherige Registrierung fuer diese Session ueberschrieben."

### Schritt 4: ScheduleWakeup setzen

`delaySeconds` berechnen: `(window_reset_at - now).total_seconds() + 300` (5 min Buffer).

> **WICHTIG (Tool-Clamp, verifiziert 2026-05-28):** `ScheduleWakeup` clamped `delaySeconds` hart auf **[60, 3600]** (max 1h). Ein 5h-Wert wird auf 3600 gekürzt → Wake-Up feuert nach 1h, NICHT beim echten Window-Reset. Daher:
> - Für echtes Window-Reset-Matching (>1h Abstand) **`CronCreate` ODER `mcp__scheduled-tasks__create_scheduled_task`** nutzen (akzeptieren lange/absolute Intervalle).
> - Mit `ScheduleWakeup`: es wird ein 1h-Re-Fire-Loop (jede Stunde aufwachen → PROGRESS prüfen → weiterarbeiten ODER erneut schedulen). Die Token-Bilanz unten (1-2 Wakeups/Nacht) gilt nur für Cron/scheduled-tasks; der ScheduleWakeup-1h-Loop kostet ~5× mehr Wake-Ups.

```
ScheduleWakeup({
  delaySeconds: <berechneter Wert>,
  reason: "Wake-Up Window-Reset Task <task_name> Session <label>",
  prompt: "<Resume-Prompt-Template, siehe Phase 4>"
})
```

### Schritt 5: PROGRESS-File-Pfad anlegen falls nicht vorhanden

der Nutzer-Anweisung wenn `progress_file` noch nicht existiert:

```
PROGRESS-File-Pfad: <path>
Bitte vor Window-Ende anlegen mit Phasen-Liste (Template unten).
```

## Phase 2 — Sub-Command: `list`

Zeige alle aktiven Sessions als Tabelle:

```
Aktive Wake-Up-Sessions (n=3):

| Session-Label | Task | PROGRESS-File | Naechster Wake-Up | Status |
|---|---|---|---|---|
| silly-murdock-670cb2 | pyright-cleanup | PROGRESS_pyright_2026-05-18.md | 2026-05-18 19:35 | active |
| dashboard-refactor | mockup-port | PROGRESS_dashboard_2026-05-18.md | 2026-05-18 19:35 | active |
| n8n-pipeline | content-curation | PROGRESS_n8n_2026-05-18.md | 2026-05-19 00:30 | active |

Globaler Window-Reset (cached): 2026-05-18 19:30 (Quelle: marco_input)
```

Bei status=`done` Eintraege optional zeigen mit „(abgeschlossen)" am Ende.

## Phase 3 — Sub-Command: `remove`

Aktuelle Session aus Registry entfernen. Hinweis: bestehender ScheduleWakeup wird **nicht** abgebrochen (CC bietet kein API dafuer) — er feuert noch einmal, der Resume-Prompt erkennt aber dass die Session nicht mehr in Registry ist und stoppt.

```python
def remove_session(session_id):
    if not SESSIONS_FILE.exists():
        return False
    data = json.loads(SESSIONS_FILE.read_text())
    removed = data["sessions"].pop(session_id, None)
    data["last_updated"] = datetime.now(timezone(BERLIN_OFFSET)).isoformat()
    tmp = SESSIONS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(SESSIONS_FILE)
    return removed is not None
```

Output: „Session <label> entfernt. Hinweis: ein eventuell noch geplanter ScheduleWakeup feuert noch einmal, stoppt aber direkt da Registry-Eintrag fehlt."

## Phase 4 — Sub-Command: `status`

Status aktuelle Session + globaler Window-State:

```
Diese Session: silly-murdock-670cb2
- Wake-Up registriert: JA (Task: pyright-cleanup)
- Naechster Wake-Up: 2026-05-18 19:35 (in 12h 15min)
- PROGRESS-File: PROGRESS_pyright-cleanup_2026-05-18.md (existiert: JA)

Globaler Window-Reset: 2026-05-18 19:30 (cached, von 14:30 marco_input)

Andere aktive Sessions: 2 (siehe `/wakeup-setup list`)
```

Bei nicht-registrierter Session: „Diese Session: keine Wake-Up-Registrierung. Trigger `/wakeup-setup register <task>` zum Einrichten."

## Phase 5 — Resume-Prompt-Template (registry-aware)

```
Lies ~/.claude/state/wakeup_sessions.json.

Wenn meine Session-ID (CWD-Hash) NICHT in sessions: STOP — Registry-Eintrag entfernt.

Wenn mein Eintrag status="done" oder status="paused": STOP.

Sonst:
  - Lies PROGRESS-File aus meinem Registry-Eintrag (Feld `progress_file`)
  - Wenn alle Phasen "done":
      - Update Registry-Eintrag: status="done"
      - Atomic write
      - STOP — kein neuer Schedule
  - Sonst:
      - Nimm erste "pending"-Phase
      - Arbeite sie vollstaendig ab
      - Update PROGRESS-File atomic (.tmp + rename) auf "done"
      - Wenn weitere Phasen "pending":
          - Re-Schedule: bevorzugt `CronCreate`/`mcp__scheduled-tasks` mit ~18900s (5h15min) für echtes Reset-Matching. Falls `ScheduleWakeup` genutzt: max 3600 möglich (Clamp) → 1h-Re-Fire-Loop, jede Stunde PROGRESS prüfen.
          - Update Registry-Eintrag: next_wake_at = now + 5h15min
          - Update wakeup_window_state.json: window_reset_at = now + 5h, source = "auto_extended"
      - Wenn alle done nach dieser Phase:
          - Update Registry-Eintrag: status="done"
          - STOP
```

## Phase 6 — PROGRESS-File-Template

```markdown
# PROGRESS — <Task-Name> — <YYYY-MM-DD>

## Session
- Session-Label: <slug-aus-cwd>
- Registriert: <timestamp>

## Phasen

- [ ] Phase 1: <Beschreibung> | Status: **pending** | Notes: —
- [ ] Phase 2: <Beschreibung> | Status: **pending** | Notes: —

## Status-Werte

`pending` / `in_progress` / `done` / `failed`

## Letzte Wake-Up-Aktivierung

- Timestamp: —
- Window-Reset-Zeit: —
- Quelle: —
```

## Phase 7 — Setup-Bestaetigung (bei `register`)

```
Wake-Up-Setup fuer <task> registriert (Session: <label>):
- Window-Reset: <berlin-zeit> (Quelle: <source>)
- ScheduleWakeup: in <delaySeconds>s (=<H>h<M>min)
- PROGRESS-File: <pfad> (existiert: JA/NEIN — bitte anlegen)
- Registry-Eintrag: ~/.claude/state/wakeup_sessions.json (n=<count> Sessions aktiv)
- Stop-Condition: alle Phasen "done" → Registry-Eintrag auto-status="done", kein neuer Schedule

Voraussetzung: der Nutzer-Maschine laeuft durch UND diese CC-Session bleibt offen.
Standby/Reboot/Session-Close toetet den Wake-Up.

Andere aktive Sessions: <count>. Liste: `/wakeup-setup list`.
```

## Token-Cost-Bilanz

> Window-Burn-Prozente wurden 05/2026 für Max 5x geschätzt; seit 07/2026 läuft Max 20x, dort ist der Anteil etwa ein Viertel davon. Die Token-Zahlen gelten unverändert.

| Pattern | Wake-Ups/Nacht | Tokens | Window-Burn |
|---|---|---|---|
| 30min-Polling (alt, falsch) | 16 | ~110k | ~15% |
| 5h+15min Reset-matched + Cache (v1.0) | 1–2 | ~5–15k | ~1–2% |
| v2.0 Multi-Session (3 Chats parallel) | 1-2 pro Session = 3-6 total | ~15-45k total | ~2-6% verteilt auf 3 Windows |

Multi-Session-Cost skaliert linear mit Anzahl aktiver Sessions — der Nutzer-Disziplin: nur Sessions registrieren die WIRKLICH Long-Run brauchen.

## Anti-Patterns

| Anti-Pattern | Warum problematisch | Ersatz |
|---|---|---|
| Jede neue Session unueberlegt registrieren | Token-Burn skaliert linear, viele Sessions = viele parallele Wake-Ups | der Nutzer-Disziplin: nur Long-Run-Sessions registrieren |
| Registry-Eintrag manuell editieren | Schema-Verletzung, Race-Conditions | Sub-Commands nutzen (`register`/`remove`) |
| Multiple Wake-Ups fuer dieselbe Session | Doppelte Schedule-Calls, doppelte Token-Kosten | Skill ueberschreibt bei `register` — Output sagt es der Nutzer |
| Session geschlossen, ScheduleWakeup feuert ins Leere | CC-Verhalten — kann nichts dagegen tun | Setup-Output erinnert daran dass Session offen bleiben muss |
| Resume-Prompt liest nur PROGRESS-File ohne Registry-Check | Wake-Up feuert auch nach `remove`-Befehl | Registry-Check im Resume-Prompt **vor** PROGRESS-File-Read |
| State-File nicht atomic | Race wenn 2 Sessions gleichzeitig registrieren | `.tmp` + `os.replace()` (Atomic-Write Pflicht) |
| Endloser Loop (keine Stop-Bedingung) | Wake-Up feuert auch nach Abschluss aller Phasen | Stop-Condition: alle `done` → status="done" → kein neuer Schedule |
| der Nutzer bei jeder neuen Session neu fragen nach Window-Reset | Unnoetiger Interaction-Overhead | Window-State ist global gecached, nur 1× pro Reset-Zyklus der Nutzer-Frage |

## Constraints

- **Token-effizient pro Session:** Skill laeuft on-demand pro Trigger, kein Hintergrund-Hook
- **Shared Window-Cache** verhindert wiederholte der Nutzer-Fragen bei Multi-Session-Setup
- **Atomic-Writes** Pflicht fuer beide State-Files (Race-Conditions bei parallelen Sessions)
- **Read-Maschine-laeuft-durch + Session-offen** ist Voraussetzung — Setup-Output sagt es deutlich
- **der Nutzer-Convention:** PROGRESS-File-Pfad `~/.claude/audit/PROGRESS_<task>_<YYYY-MM-DD>.md`
- **Kein Auto-Trigger:** Skill wird NICHT als Hook gestartet — der Nutzer entscheidet pro Session manuell
- **Session-Identifier via CWD-Hash:** stabil pro Worktree, kollidiert nur bei mehreren CC-Instanzen im gleichen CWD

## Migrations-Hinweis v1.0 → v2.0

Wer v1.0 genutzt hat: kein automatischer Migration noetig, weil v1.0 keine Multi-Session-Registry hatte. Bestehender `wakeup_window_state.json` bleibt erhalten und wird von v2.0 weiterhin gelesen. Erst-Trigger nach v2.0-Update legt `wakeup_sessions.json` automatisch an.

## Beispiel-Triggers

- `/wakeup-setup` — interaktiv (Task-Name-Frage, Window-Reset-Frage falls Cache leer), registriert aktuelle Session
- `/wakeup-setup register pyright-cleanup` — direkt mit Task-Name
- `/wakeup-setup list` — alle aktiven Sessions zeigen
- `/wakeup-setup status` — Status aktuelle Session
- `/wakeup-setup remove` — aktuelle Session abmelden

## Changelog

- **v2.0.1** (2026-05-28): Lyra-Audit-Fix — `ScheduleWakeup`-Clamp [60,3600] dokumentiert (verifiziert). Phase-1-Schritt-4 + Phase-5-Resume: bei >1h-Abstand `CronCreate`/`mcp__scheduled-tasks` statt `ScheduleWakeup` (sonst 5h→3600 geclampt = stündlicher Re-Fire-Loop, ~5× Token). Token-Bilanz-Gültigkeit präzisiert.
- **v2.0.0** (2026-05-18): Multi-Session-Registry. Sub-Commands `register`/`list`/`remove`/`status`. State-File `wakeup_sessions.json` neu. Session-Identifier via CWD-Hash. Resume-Prompt registry-aware mit Stop-Condition bei fehlendem Registry-Eintrag.
- **v1.0.0** (2026-05-17): Erste Version. Extrahiert aus Lyra v4.5.1 als eigenstaendiger Skill. Single-Session-Pattern.
