#!/usr/bin/env python
"""SessionStart Hook: zeigt offene Probleme aus dem Problem-Tracker.

der Nutzer-Wunsch (2026-06-02): jeder Session-Start zeigt die Gesamt-Zahl offener
Probleme (auch LOW) → `problems/OPEN.md` ist immer präsent. Refresht zugleich
das Rollup (OPEN.md/OPEN.json), damit es aktuell ist.

Best-effort: jede Exception → stiller Exit (Session-Start nie blockieren).
"""
import json
import sys
from pathlib import Path

_SCRIPTS = Path.home() / ".claude" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def main() -> int:
    try:
        import problem  # type: ignore
        counts = problem.build_index()  # refresht OPEN.md + liefert counts
    except Exception:
        sys.exit(0)

    total = counts.get("total_open", 0)
    ideas = counts.get("ideas_open", 0)
    if total <= 0 and ideas <= 0:
        sys.exit(0)  # nichts offen → kein Banner

    crit = counts.get("CRITICAL", 0)
    high = counts.get("HIGH", 0)
    med = counts.get("MEDIUM", 0)
    low = counts.get("LOW", 0)
    info = counts.get("INFO", 0)
    flag = "⚠ " if (crit or high) else "📋 "
    msg = (f"{flag}Setup-Probleme (Skills/Hooks/Agents): {total} "
           f"(CRITICAL {crit} · HIGH {high} · MEDIUM {med} · LOW {low} · INFO {info})"
           f"  ·  💡 Ideen/Setup-Lücken: {ideas} "
           f"→ ~/.claude/problems/OPEN.md  ·  fixen: problem.py resolve <id>")
    # SessionStart: additionalContext injiziert die Note in den Start-Kontext
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    main()
