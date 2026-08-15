#!/usr/bin/env python3
"""PreCompact-Hook: rettet Gamebot-Verdrahtungsspur vor dem Auto-Compact.

der Nutzer 2026-07-25: Gamebot-Sessions laufen unbeaufsichtigt 24/7 mit Nag aus
(loopmode/SKILL.md:21) -> Auto-Compact feuert wiederholt und verliest das WARUM
zu Code, der schon gebaut ist. Folge (belegt: _bots_control.py 2026-06-16):
ein spaeterer Tick entfernt eine fertige Funktion als "unerklaerten Code".

Dieser Hook feuert in der Sekunde VOR dem Vergessen und schreibt mechanisch
(ohne Modell) die in diesem Kontext-Fenster editierten Dateien ins JOURNAL,
plus WIRING_PENDING.md als To-do fuer die Post-Compact-Session.

Scope: nur Sessions, deren cwd (oder ein Parent) eine LOOP_TICK.md enthaelt.
Best-effort: blockt nie, exit 0 immer.
"""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path

MARK = "LOOP_TICK.md"      # markiert ein Gamebot-Verzeichnis
MAX_EDITS = 60
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def bot_dir(start: Path):
    for d in (start, *start.parents):
        try:
            if (d / MARK).is_file():
                return d
        except Exception:
            continue
    return None


def _norm(p: str) -> str:
    return p.replace("\\", "/").lower()


def edits_from_transcript(path: str, root: Path):
    """Edit/Write-Pfade im Bot-Baum aus dem Transcript-jsonl ziehen."""
    if not path:
        return []
    hits = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "tool_use" not in line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                content = ((rec.get("message") or {}).get("content"))
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_use":
                        continue
                    if block.get("name") not in EDIT_TOOLS:
                        continue
                    fp = (block.get("input") or {}).get("file_path") or ""
                    if fp:
                        hits.append(fp)
    except Exception:
        return []
    rs = _norm(str(root))
    out = []
    for fp in hits:
        if rs in _norm(fp) and fp not in out:
            out.append(fp)
    return out[-MAX_EDITS:]


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    try:
        root = bot_dir(Path(data.get("cwd") or os.getcwd()))
    except Exception:
        sys.exit(0)
    if root is None:
        sys.exit(0)

    ts = time.strftime("%Y-%m-%dT%H:%M")
    edits = edits_from_transcript(data.get("transcript_path") or "", root)

    journals = sorted(root.glob("JOURNAL*.md"))
    journal = journals[0] if journals else root / f"JOURNAL_{root.name}.md"

    lines = [
        "",
        f"## [PRE-COMPACT {ts}] trigger={data.get('trigger', '?')} "
        f"session={str(data.get('session_id', ''))[:8]}",
    ]
    if edits:
        lines.append("Editierte Dateien in diesem Kontext-Fenster "
                     "(mechanisch aus dem Transcript):")
        lines += [f"- {e}" for e in edits]
        lines.append("PFLICHT nach dem Compact: pruefen ob jede FERTIGE Sache "
                     "eine Zeile in WIRING.md hat. Sonst vergisst der naechste "
                     "Tick, dass sie Absicht war.")
    else:
        lines.append("Keine Edits im Bot-Baum in diesem Fenster.")

    try:
        with open(journal, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass

    try:
        body = f"# WIRING_PENDING — offen seit Compact {ts}\n"
        body += "\n".join(f"- {e}" for e in edits) if edits else "- (keine)"
        (root / "WIRING_PENDING.md").write_text(body + "\n", encoding="utf-8")
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
