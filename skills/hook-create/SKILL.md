---
name: hook-create
version: 1.0.0
description: |
  Erstellt einen neuen Claude-Code-Hook nach der Nutzer Standard-Pattern (best-effort,
  stdin-JSON, exit 0, optional systemMessage) UND verdrahtet ihn idempotent in
  settings.json. Submodus `audit`: pingt alle verdrahteten Hooks via _health_check.
  Setup ist hook-lastig (20+ Hooks) — dieser Skill ist das fehlende Gegenstück zu
  skill-create/agent-create.
  Use when: "neuen Hook erstellen", "Hook anlegen", "Hook bauen", "PreToolUse-Hook",
  "PostToolUse-Hook", "Hook verdrahten", "Hooks auditieren", "hook-create".
---

# hook-create — Hook scaffolden + verdrahten

Du erstellst einen neuen Lifecycle-Hook für der Nutzer Setup, verdrahtest ihn in
`settings.json` und verifizierst ihn. Active-Enforcement-Doktrin (CLAUDE.md): wenn
eine Regel Zustand überwacht (Context/Token/Budget/Security), gehört sie in einen
aktiven Hook, nicht in passiven Doku-Text.

## Submodi
- **(default) create** — neuen Hook bauen + verdrahten.
- **audit** — `python ~/.claude/hooks/_health_check.py --verbose` laufen lassen (pingt alle
  verdrahteten Hooks, auch die in `scripts/`, prüft Syntax + Dummy-Run). Bei Failures: melden.

## Phase 1 — Spezifikation klären
Ermittle (frag nur was unklar ist):
1. **Event** (Tabelle unten) + ggf. **Matcher** (nur Pre/PostToolUse: `Bash`, `Edit`, `Edit|Write`, …).
2. **Zweck** (1 Satz) + **blockt es?** (nur Pre*-Events können via `exit 2` blocken).
3. **Hook-Name** (`snake_case.py`, sprechend).

### Event-Referenz (verifiziert offiziell — keine erfundenen Events)
| Event | Stdin-Felder (u.a.) | Blockt? | Typischer Use-Case |
|---|---|---|---|
| `PreToolUse` | `tool_name`, `tool_input`, `cwd` | ja (`exit 2`) | Destructive-Guard, Pre-Condition, Read-Tool-Enforce |
| `PostToolUse` | `tool_name`, `tool_input`, `tool_response` | nein | Side-Effect-Reminder, Test-Trigger nach Edit |
| `UserPromptSubmit` | `prompt`, `transcript_path` | (Kontext injizieren) | Secret-Scan, Context-Schwelle, Mode-Tracking |
| `PreCompact` | `transcript_path`, `trigger` | nein | State-Backup, Memory-Checkpoint |
| `Stop` | `transcript_path`, `stop_hook_active` | nein | Per-Turn-Logging/Memory |
| `SessionStart` | `source` | nein | Banner, Health-Check, Context-Inject |
| `SessionEnd` | `transcript_path`, `reason` | nein | Finaler Session-Rollup, Cleanup |
| `SubagentStop` | `transcript_path`, ggf. `agent_type` | nein | Per-Subagent-Tracing |

> NICHT erfinden: `PostCompact`, `UserPromptExpansion`, `PostToolBatch`, `TaskCreated`,
> `MessageDisplay` sind **unbestätigt** (nicht-offizielle Quellen). Vor Nutzung gegen
> `https://code.claude.com/docs/en/hooks` verifizieren.

## Phase 2 — Scaffold schreiben
Schreibe `~/.claude/hooks/<name>.py` nach diesem Pattern (best-effort, blockt nie ausser gewollt):

```python
#!/usr/bin/env python
"""<Event>-Hook: <Zweck>.

der Nutzer <datum>: <Begründung>. Best-effort: blockt nie (exit 0), gibt genau ein
JSON {"systemMessage"} zurück (Hook-Protokoll) oder nichts.
"""
from __future__ import annotations
import json, sys

def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    # ... Zustand aus data/transcript_path messen ...
    if False:  # <bedingung>
        # Blocken (nur Pre*-Events): sys.stderr.write("BLOCKED: ...\n"); sys.exit(2)
        print(json.dumps({"systemMessage": "[<name>] ..."}))
    sys.exit(0)

if __name__ == "__main__":
    main()
```

Regeln: stdout = **genau ein** JSON-Objekt ODER nichts (mehrere JSONs brechen das Protokoll
— Fehler nach `stderr`). Secret-Scan vor jedem Memory-Write (reuse `session_logger.contains_secret`
bzw. `secret_leak_detector.PATTERNS`). Niemals Secret-Werte loggen. Windows: bei Emoji-stdout
`sys.stdout.reconfigure(encoding="utf-8")`.

## Phase 3 — Verdrahten (idempotent)
Backup `settings.json` (`cp -a`), dann via Python einfügen (nicht von Hand JSON editieren):
```python
import json, os
from pathlib import Path
p=Path.home()/".claude"/"settings.json"; s=json.loads(p.read_text(encoding="utf-8"))
cmd="python ~/.claude/hooks/<name>.py"; ev=s.setdefault("hooks",{}).setdefault("<EVENT>",[])
if not any(cmd==h.get("command") for b in ev for h in b.get("hooks",[])):
    block=next((b for b in ev if b.get("matcher","")=="<MATCHER>"), None)
    if block is None: block={"matcher":"<MATCHER>","hooks":[]}; ev.append(block)
    block["hooks"].append({"type":"command","command":cmd,"timeout":10})
    tmp=p.with_suffix(".json.tmp"); tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8"); os.replace(tmp,p)
```
Matcher leer `""` für Nicht-Tool-Events (UserPromptSubmit/Stop/SessionStart/SessionEnd/Pre/PostCompact/SubagentStop).

## Phase 4 — Verifizieren (Pflicht)
1. `python -m py_compile ~/.claude/hooks/<name>.py` → muss 0.
2. Dummy-Stdin-Test: `echo '{...realistische Felder...}' | python ~/.claude/hooks/<name>.py` → genau 1 JSON oder leer, exit wie erwartet.
3. Bei Block-Hook: je 1 Block-Fall + 1 Allow-Fall testen (False-Positive-Check).
4. `python ~/.claude/hooks/_health_check.py` → neuer Hook OK.

## Constraints
- Nur verifizierte Events (Tabelle) — keine erfundenen.
- Hook blockt nur wenn explizit gewollt UND Event Pre* ist; sonst exit 0.
- Genau ein stdout-JSON; Fehler nach stderr.
- Backup vor settings.json-Edit; idempotentes Einfügen.
- Hooks live ab nächstem Session-Start (Pre/PostToolUse oft sofort).

## Beispiel-Triggers
`/hook-create` · „PostToolUse-Hook der nach jedem Write lintet" · „SessionEnd-Cleanup-Hook" ·
„hook-create audit" (alle Hooks pingen)

## Changelog
- v1.0.0 (2026-06-05): Initial — aus Inventar-Audit G1 (hook-lastiges Setup ohne hook-create).
