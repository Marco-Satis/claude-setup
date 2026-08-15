#!/usr/bin/env python
"""SessionEnd-Hook: finaler Session-Rollup-Memory beim echten Session-Ende.

der Nutzer 2026-06-05 (Inventar-Audit E2): der Stop-Hook (`session_logger.py`) feuert
bei JEDEM Turn-Ende; SessionEnd feuert genau EINMAL wenn die Session terminiert
(clear/logout/resume) und kennt den `reason`. Das ist der präziseste Ort für den
DEFINITIVEN Abschluss-Rollup der ganzen Session — vollständiger als die
inkrementellen 5-Turn-Checkpoints.

Reuse der bewährten Logik aus session_logger.py (Single-Source). Best-effort:
blockt nie, gibt genau ein JSON {"systemMessage"} zurück. Secret-Gate vor Write.

Stdin (SessionEnd): {session_id, transcript_path, cwd, reason}.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
try:
    import session_logger as sl
except Exception:
    sys.exit(0)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    transcript_path = data.get("transcript_path")
    session_id = data.get("session_id", "unknown")
    cwd = data.get("cwd") or os.getcwd()
    project = Path(cwd).name if cwd else "unknown"
    reason = data.get("reason", "")  # clear | logout | resume | ...

    if not transcript_path:
        sys.exit(0)
    tp = Path(transcript_path)
    if not tp.exists():
        sys.exit(0)

    records = sl._load_records(tp)
    if not records:
        sys.exit(0)

    # Nur bei substanzieller Session schreiben (sonst Rauschen bei Kurz-Sessions).
    user_turns = sl.count_user_turns(records)
    if user_turns < sl.PERSIST_MIN_USER_TURNS and not sl.detect_marco_trigger(records):
        sys.exit(0)

    date_iso = datetime.now(timezone.utc).isoformat()
    files_edited: set[str] = set()
    distinct_tools: set[str] = set()
    edits = 0
    for rec in records:
        msg = rec.get("message", {})
        if not isinstance(msg, dict):
            continue
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict) or c.get("type") != "tool_use":
                continue
            name = c.get("name", "")
            if name:
                distinct_tools.add(name)
            fp = (c.get("input") or {}).get("file_path") if isinstance(c.get("input"), dict) else None
            if name in ("Edit", "Write", "NotebookEdit") and fp:
                files_edited.add(fp)
                edits += 1

    stats = {
        "date": date_iso,
        "files_edited_sample": sorted(files_edited),
        "files_edited_count": len(files_edited),
        "distinct_tools": sorted(distinct_tools),
    }
    try:
        summary = sl.build_session_summary(records, project, stats)
    except Exception as e:
        print(json.dumps({"systemMessage": f"[session_end] summary-Fehler: {str(e)[:80]}"}))
        sys.exit(0)

    leak, pat = sl.contains_secret(summary)
    if leak:
        print(json.dumps({"systemMessage": f"[session_end] Rollup geblockt (Secret {pat})"}))
        sys.exit(0)

    slug = re.sub(r"[^a-z0-9-]", "-", project.lower())[:40]
    tags = ["session-summary", "session-final", f"project-{slug}"] + sl.extract_topic_tags(records)
    ok, info = sl.post_memory({
        "content": summary,
        "tags": tags,
        "memory_type": "observation",
        "metadata": {
            "session_id": session_id, "kind": "session-final", "reason": reason,
            "user_turns": user_turns, "files_edited_count": len(files_edited),
            "code_edits": edits, "timestamp": date_iso,
        },
    })
    print(json.dumps({"systemMessage":
                      f"[session_end] Abschluss-Rollup (reason={reason or '?'}): "
                      f"{'ok ' + info if ok else 'fail ' + info}"}))


if __name__ == "__main__":
    main()
