#!/usr/bin/env python3
"""SessionStart-Hook: gibt netcup-RC-Sessions ihren festen Namen zurück.

der Nutzer 20.11.2026 (MB299): Seit Claude Code 2.1.328 übernimmt `claude remote-control --name X --continue`
den Namen nicht mehr als Peer-Namen; nach jedem Neustart heißen die Sessions automatisch (trading-a9 …)
und sind per SendMessage nicht unter ihrem Namen erreichbar. Laut offizieller Hook-Doku setzt
`hookSpecificOutput.sessionTitle` bei SessionStart (startup/resume/fork) den Titel „mit derselben Wirkung
wie /rename“; ein /rename hat den Peer-Namen am 20.11. nachweislich zurückgebracht.

Ablauf: Von diesem Hook aus die Prozess-Ahnen hochgehen, bis der nächste Claude-Binary-Prozess kommt (die
Session). Nur wenn dessen Elternprozess `claude remote-control … --name <X>` ist, wird <X> als sessionTitle
gemeldet. Damit greifen `claude -p`-Unterprozesse, Routinen und lokale Sitzungen nie (dort ist der Elternprozess
eine Shell bzw. cron), und es gibt keine Namensdubletten.

Best-effort: blockt nie (exit 0), schreibt genau ein JSON oder nichts auf stdout. Nur Linux (/proc).
Aus: touch ~/.claude/flags/rc_session_name.off
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

CLAUDE_VERSIONS = str(Path.home() / ".local/share/claude/versions") + "/"
FLAG_OFF = Path.home() / ".claude/flags/rc_session_name.off"
MAX_DEPTH = 8


def _ppid(pid: int) -> int | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("PPid:"):
                return int(line.split()[1])
    except (OSError, ValueError):
        return None
    return None


def _exe(pid: int) -> str:
    try:
        return os.readlink(f"/proc/{pid}/exe")
    except OSError:
        return ""


def _args(pid: int) -> list[str]:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return []
    return [a.decode("utf-8", "replace") for a in raw.split(b"\0") if a]


def rc_name(start_pid: int) -> str | None:
    """--name des remote-control-Prozesses, der die nächste Claude-Session gestartet hat, sonst None."""
    pid = start_pid
    for _ in range(MAX_DEPTH):
        if pid is None or pid <= 1:
            return None
        if _exe(pid).startswith(CLAUDE_VERSIONS):
            parent = _ppid(pid)
            if parent is None or not _exe(parent).startswith(CLAUDE_VERSIONS):
                return None
            args = _args(parent)
            if "remote-control" not in args or "--name" not in args:
                return None
            i = args.index("--name")
            name = args[i + 1].strip() if i + 1 < len(args) else ""
            if not name or len(name) > 64 or not name.isprintable():
                return None
            return name
        pid = _ppid(pid)
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if FLAG_OFF.exists() or not Path("/proc").is_dir():
        sys.exit(0)
    if str(data.get("source", "")) not in ("startup", "resume"):
        sys.exit(0)
    name = rc_name(os.getppid())
    if name:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "sessionTitle": name}},
                         ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
