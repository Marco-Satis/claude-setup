#!/usr/bin/env python
"""PreCompact Hook: erzwingt einen Session-Checkpoint-Memory-Write vor JEDEM /compact.

der Nutzer 2026-06-05: "bei jeder Vorbereitung auf compact soll ein Memory-Update
gemacht werden." Begruendung (CLAUDE.md/Lyra-Doktrin): aktiver Hook statt passiver
Regel — sonst im Flow vergessen. Compact ist ein Wissens-Schnitt; davor MUSS der
Stand persistiert sein, damit nichts beim Zusammenfassen verloren geht.

Reuse der bewaehrten Logik aus session_logger.py (Single-Source: build_session_summary,
post_memory, contains_secret, extract_topic_tags, _load_records). Anders als der
Stop-Hook (Checkpoint nur alle 5 Turns) schreibt dieser IMMER, sobald das Transcript
substanziell ist. Best-effort: darf den Compact NIE blockieren (alle Fehler -> exit 0).

Stdin (PreCompact-Event): {transcript_path, session_id, cwd, trigger:"manual"|"auto"}
Stdout: genau ein JSON-Objekt {"systemMessage": "..."} (Hook-Protokoll).
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# session_logger liegt im selben Hooks-Ordner -> importierbar (hat __main__-Guard,
# Import triggert kein main()). Bei Import-Fail: Hook degradiert lautlos (exit 0).
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
try:
    import session_logger as sl
except Exception:
    sys.exit(0)


def _collect_stats(records: list[dict]) -> dict:
    """Minimal-Stats fuer build_session_summary (date, files, tools)."""
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
    return {
        "files_edited": files_edited,
        "distinct_tools": distinct_tools,
        "edits": edits,
    }


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    transcript_path = data.get("transcript_path")
    session_id = data.get("session_id", "unknown")
    cwd = data.get("cwd") or os.getcwd()
    project = Path(cwd).name if cwd else "unknown"
    trigger = data.get("trigger", "")  # "manual" (/compact) oder "auto" (Kontext voll)

    if not transcript_path:
        sys.exit(0)
    tp = Path(transcript_path)
    if not tp.exists():
        sys.exit(0)

    records = sl._load_records(tp)
    if not records:
        sys.exit(0)

    date_iso = datetime.now(timezone.utc).isoformat()
    st = _collect_stats(records)
    stats = {
        "date": date_iso,
        "files_edited_sample": sorted(st["files_edited"]),
        "files_edited_count": len(st["files_edited"]),
        "distinct_tools": sorted(st["distinct_tools"]),
    }

    try:
        summary = sl.build_session_summary(records, project, stats)
    except Exception as e:
        print(json.dumps({"systemMessage": f"[precompact_memory] summary-Fehler: {str(e)[:80]}"}))
        sys.exit(0)

    # Secret-Gate (Re-Use derselben Patterns) — niemals ein Secret in die Memory.
    leak, pat = sl.contains_secret(summary)
    if leak:
        try:
            ld = Path.home() / ".claude" / "lessons"
            ld.mkdir(parents=True, exist_ok=True)
            with (ld / "leaks.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": date_iso, "event": "secret_in_precompact_checkpoint_blocked",
                    "pattern_name": pat, "session_id": session_id, "project": project,
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        print(json.dumps({"systemMessage": f"[precompact_memory] Checkpoint geblockt (Secret {pat})"}))
        sys.exit(0)

    slug = re.sub(r"[^a-z0-9-]", "-", project.lower())[:40]
    tags = ["session-summary", "precompact-checkpoint", f"project-{slug}"] + sl.extract_topic_tags(records)

    # 2026-10-21 E1/S5: conversation_id auf OBERSTER Ebene (wie session_logger.py:675). Ohne sie
    # verwarf die Semantik-Dedupe des Dienstes 7/7 Checkpoints, und der Hook meldete "ok".
    # Mit ihr greift nur noch die exakte Hash-Dublette. Rueckweg: .bak.pre-e1.*
    ok, info = sl.post_memory({
        "content": summary,
        "conversation_id": session_id,
        "tags": tags,
        "memory_type": "observation",
        "metadata": {
            "session_id": session_id,
            "kind": "precompact-checkpoint",
            "trigger": trigger,
            "files_edited_count": stats["files_edited_count"],
            "code_edits": st["edits"],
            "timestamp": date_iso,
        },
    })
    # Ehrliche Meldung: eine Dublette ist kein neuer Checkpoint. post_memory meldet sie als
    # (True, "duplicate-existing"); mit conversation_id kann das nur noch die exakte sein.
    if ok and info.startswith("duplicate-existing"):
        status = "nicht neu gespeichert: duplicate-existing (exact), identischer Stand liegt schon vor"
    else:
        status = ("ok " + info) if ok else ("fail " + info)
    print(json.dumps({"systemMessage": f"[precompact_memory] Checkpoint vor Compact: {status}"}))


if __name__ == "__main__":
    main()
