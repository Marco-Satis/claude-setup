#!/usr/bin/env python
"""SubagentStop-Hook: tracet jeden Sub-Agent-Run in eine JSONL.

der Nutzer 2026-06-05 (Inventar-Audit E1): der Nutzer 16 Sub-Agents liefen bisher "blind"
— kein aggregiertes Tracing pro Run. Dieser Hook feuert bei jedem SubagentStop und
schreibt einen Tracing-Datensatz nach `~/.claude/lessons/subagent_runs.jsonl`
(Timestamp, Transcript-Stats, Tool-/Token-Schätzung aus dem Subagent-Transcript).

Best-effort: blockt NIE (alle Fehler → exit 0), gibt genau ein JSON {"systemMessage"}
zurück (Hook-Protokoll) oder nichts. Liest das Subagent-Transcript NUR um Stats zu
zählen (kein Inhalt, keine Secrets ins Log).

Stdin (SubagentStop): {session_id, transcript_path, cwd, stop_hook_active, ...}.
Hinweis: das `transcript_path` zeigt auf das SUBAGENT-Transcript (eigener Lauf).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG = Path.home() / ".claude" / "lessons" / "subagent_runs.jsonl"


def _scan_transcript(tp: Path) -> dict:
    """Zählt Records/Tools/Token-Schätzung + Agent-Typ aus dem Subagent-Transcript.
    Nur Metadaten, kein Inhalt."""
    records = 0
    tool_calls = 0
    tools: set[str] = set()
    in_tok = out_tok = 0
    agent_type = ""
    first_ts = last_ts = None
    try:
        with tp.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if not isinstance(rec, dict):
                    continue
                records += 1
                ts = rec.get("timestamp")
                if ts:
                    first_ts = first_ts or ts
                    last_ts = ts
                if not agent_type:
                    agent_type = rec.get("agent_type") or rec.get("subagent_type") or ""
                msg = rec.get("message") or {}
                if isinstance(msg, dict):
                    usage = msg.get("usage") or {}
                    if isinstance(usage, dict):
                        in_tok += int(usage.get("input_tokens", 0) or 0)
                        out_tok += int(usage.get("output_tokens", 0) or 0)
                    content = msg.get("content")
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get("type") == "tool_use":
                                tool_calls += 1
                                n = c.get("name")
                                if n:
                                    tools.add(n)
    except Exception:
        pass
    return {
        "records": records, "tool_calls": tool_calls,
        "distinct_tools": sorted(tools)[:15], "input_tokens": in_tok,
        "output_tokens": out_tok, "agent_type": agent_type,
        "first_ts": first_ts, "last_ts": last_ts,
    }


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tp = data.get("agent_transcript_path") or data.get("transcript_path")
    session_id = data.get("session_id", "unknown")
    cwd = data.get("cwd") or os.getcwd()
    project = Path(cwd).name if cwd else "unknown"
    now = datetime.now(timezone.utc).isoformat()

    rec: dict = {
        "ts": now,
        "session_id": session_id,
        "project": project,
        "agent_type": data.get("agent_type") or data.get("subagent_type") or "",
    }
    if tp:
        p = Path(tp)
        if p.exists():
            rec.update(_scan_transcript(p))
            rec["agent_type"] = rec.get("agent_type") or ""
            try:
                rec["transcript_kb"] = round(p.stat().st_size / 1024, 1)
            except Exception:
                pass

    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        sys.exit(0)

    # Leise: nur bei substanziellem Run eine kurze systemMessage (sonst Rauschen).
    tc = rec.get("tool_calls", 0)
    if tc and tc >= 5:
        at = rec.get("agent_type") or "subagent"
        print(json.dumps({"systemMessage":
                          f"[subagent_tracer] {at}: {tc} Tool-Calls, "
                          f"~{rec.get('output_tokens', 0)} out-tok → subagent_runs.jsonl"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
