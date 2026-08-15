#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""StopFailure Hook: API-Fehler am Turn-Ende loggen (rate_limit, overloaded, auth).

Natives CC-Event `StopFailure` feuert wenn ein Turn mit API-Error endet. Bisher
lief das ins Leere — Long-Run/Autonomous-Sessions (loopmode, /wakeup) sahen
Rate-Limits/Overloads nicht diagnostisch. Dieser Hook schreibt jeden StopFailure
nach ~/.claude/lessons/stop_failures.jsonl (Timestamp, error_type, session, cwd).
StopFailure ist Side-effects-only -> reines Logging, kein Context-Inject moeglich.
Best-effort: faengt jeden Fehler -> exit 0, bricht NIE die Session.
"""
import json
import sys
import time
from pathlib import Path


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    try:
        etype = (data.get("error_type") or data.get("matcher")
                 or data.get("reason") or data.get("stop_reason") or "unknown")
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "error_type": str(etype)[:120],
            "session_id": str(data.get("session_id", ""))[:64],
            "cwd": str(data.get("cwd", ""))[:200],
        }
        log = Path.home() / ".claude" / "lessons" / "stop_failures.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
