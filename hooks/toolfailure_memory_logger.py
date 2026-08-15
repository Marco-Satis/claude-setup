#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PostToolUseFailure Hook: Tool-Fehler loggen, Memory-Write-Fails aktiv flaggen.

Natives CC-Event `PostToolUseFailure` feuert wenn ein Tool-Call fehlschlaegt.
Zweck: das [MEMORY-CAPTURE-STALE]-Problem operationalisieren — silent
mcp__memory__*-Write-Fails nach ~/.claude/lessons/memory_write_failures.jsonl
loggen UND per systemMessage sichtbar machen (statt uebersehen). Andere
Tool-Fails: leises Logging nach tool_failures.jsonl.
Best-effort: exit 0 immer, bricht NIE die Session.
"""
import json
import sys
import time
from pathlib import Path


def _log(fname, rec):
    try:
        p = Path.home() / ".claude" / "lessons" / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    try:
        tool = str(data.get("tool_name", ""))
        err = str(data.get("error") or data.get("tool_error")
                  or data.get("reason") or "")[:300]
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "tool": tool[:80], "error": err}
        is_mem = tool.startswith("mcp__memory__") and any(
            k in tool for k in ("store", "update", "session"))
        if is_mem:
            _log("memory_write_failures.jsonl", rec)
            print(json.dumps({"systemMessage":
                f"[MEMORY-WRITE-FAIL] {tool} fehlgeschlagen: {err[:160]} — Write NICHT "
                "persistiert. Service pruefen (memory_health) + erneut speichern."}))
        else:
            _log("tool_failures.jsonl", rec)
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
