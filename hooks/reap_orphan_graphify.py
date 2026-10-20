#!/usr/bin/env python
"""SessionStart-Hook: raeumt verwaiste graphify.serve-MCP-Prozesse weg.

Fix fuer Terminal-Spam-Leak (2026-06-13): jede Claude-Code-Session spawnt
`python -m graphify.serve` (MCP-Server); beim Session-Ende werden sie NICHT
gekillt -> verwaisen (Parent-claude.exe tot) -> akkumulieren -> Terminal-Spam-
Lockout. Dieser Reaper killt beim Session-Start nur Leichen mit totem/nicht-
claude Parent. AKTIVE Sessions (lebender claude.exe-Parent) bleiben unangetastet
-> Live-MCP-Zugriff jeder Session bleibt, aber es akkumuliert nie.

Windowless: nutzt psutil (kein taskkill/subprocess -> keine Konsole). Best-effort,
blockt SessionStart nie, exit 0. Silent (kein stdout -> keine Context-Verschmutzung);
Log nach ~/.claude/state/graphify_reaper.log nur wenn was gekillt wurde.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

LOG = Path.home() / ".claude" / "state" / "graphify_reaper.log"


def main() -> None:
    try:
        import psutil
    except Exception:
        return  # ohne psutil leise nichts tun

    killed = []
    # WICHTIG (Perf): NUR `name` vorab holen. `ppid` (oder cmdline/exe) fuer ALLE
    # Prozesse in process_iter zu ziehen kostet auf dieser Box ~8s (608 Procs +
    # Defender) -> SessionStart-Lag + Health-Check-TIMEOUT. name-only = ~12ms.
    # cmdline/ppid lazy NUR fuer die paar Treffer holen.
    for p in psutil.process_iter(["name"]):
        try:
            name = (p.info.get("name") or "").lower()
            # der Nutzer-Fix 2026-08-19, zweiter Teil: der Prozessname ist auf dieser Box
            # `graphify-mcp` (das Startskript setzt comm), NICHT `python3`. Der alte
            # Filter hat die Treffer damit schon vor der Kommandozeilen-Pruefung
            # ausgeworfen — deshalb war der Hook selbst mit richtigem Muster wirkungslos.
            if "python" not in name and "graphify" not in name:
                continue
            try:
                cmd = " ".join(p.cmdline() or [])     # lazy, nur fuer python-Procs
            except psutil.Error:
                continue
            # der Nutzer-Fix 2026-08-19: Das Muster `graphify.serve` traf auf dieser Box
            # NIEMALS zu — die MCP-Server laufen als
            # `/usr/bin/python3 ~/.local/bin/graphify-mcp --graph ...`.
            # Beleg: ~/.claude/state/graphify_reaper.log existierte nicht, der Hook
            # hat also seit seiner Einfuehrung (2026-06-13) nichts aufgeraeumt.
            if "graphify.serve" not in cmd and "graphify-mcp" not in cmd:
                continue
            # Der HTTP-Dienst (systemd-user-Unit graphify-mcp.service, seit
            # 2026-08-19) hat systemd als Parent und waere damit formal ein
            # "Orphan". Er ist aber genau das Gegenteil: der EINE gewollte Server,
            # den sich alle Sessions teilen. Nie anfassen.
            if "--transport http" in cmd:
                continue
            # Parent lebt UND ist eine claude.exe? -> aktive Session, NICHT killen.
            # ppid lazy NUR fuer graphify.serve-Treffer (bulk-ppid = 8s, s.o.).
            try:
                ppid = p.ppid()
            except psutil.Error:
                ppid = None
            parent_is_live_claude = False
            if ppid:
                try:
                    parent_is_live_claude = "claude" in (psutil.Process(ppid).name() or "").lower()
                except psutil.Error:
                    parent_is_live_claude = False     # Parent weg = Orphan
            if not parent_is_live_claude:
                p.kill()
                killed.append(p.pid)
        except psutil.Error:
            continue

    if killed:
        try:
            LOG.parent.mkdir(parents=True, exist_ok=True)
            with LOG.open("a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] reaped orphans: {killed}\n")
        except OSError:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - darf SessionStart nie brechen
        pass
    sys.exit(0)
