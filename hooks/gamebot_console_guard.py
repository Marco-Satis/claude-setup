#!/usr/bin/env python3
"""PreToolUse-Hook: blockt Gamebot-Starts, die ein sichtbares Terminal-Fenster erzeugen.

der Nutzer 2026-08-11. Gemessener Befund (System_Diagnose-Session):
  Ein Konsolen-Prozess, der per WMI `Win32_Process.Create` gestartet wird, bekommt eine
  SICHTBARE Konsole — WMI nimmt auf diesem Host keine CreateFlags an (ReturnValue=21), und
  die Konsolen-Delegation zieht dann Windows Terminal hoch, das erst KALT STARTEN muss.
  Genau das ist der Terminal-Blitz, der der Nutzer seit Wochen stoert (3305 Foreground-Events
  allein am 2026-08-05). Mit `pythonw.exe` entsteht GAR KEINE Konsole -> kein Blitz.

Warum ein Hook und keine Doku: die kanonische Prozedur steht seit 2026-07-28 in der Memory
und wurde trotzdem dreimal umgangen (07-25, 07-28, 08-05) — Parallel-Sessions verlieren das
Wissen ueber Compacts hinweg. Eine Regel driftet, ein Hook nicht.

Der Guard blockt NUR den eindeutigen Fehlgriff: WMI-Prozess-Create + blankes `python.exe` +
eine Gamebot-Datei. Alles andere laeuft durch (pythonw, normale Starts, Debug-Aufrufe,
fremde Projekte).

Notausgang: Datei ~/.claude/flags/gamebot_console_guard.off anlegen.
Best-effort: jeder unerwartete Fehler -> exit 0. Block: stderr + exit 2.
"""
from __future__ import annotations
import json
import os
import re
import sys
from pathlib import Path

OFF = Path.home() / ".claude" / "flags" / "gamebot_console_guard.off"
TOOLS = {"Bash", "BashOutput", "PowerShell"}

# Gamebot-Einstiegspunkte, deren Fehlstart den Blitz ausloest.
BOT_FILES = ("run.py", "cs_bot.py", "watchdog.py", "loop_watchdog.py",
             "_bots_control.py", "diagnose.py", "ad_guard.py")

# `python.exe` ja, `pythonw.exe` nein (negativer Lookahead auf das w).
RE_PYTHON_EXE = re.compile(r"python(?!w)\.exe", re.I)
RE_WMI_CREATE = re.compile(r"win32_process", re.I)
RE_CREATE_VERB = re.compile(r"\bcreate\b", re.I)
RE_START_PROC = re.compile(r"start-process", re.I)
RE_HIDDEN = re.compile(r"windowstyle\s+hidden|createnowindow|create_no_window", re.I)


def touches_bot(cmd: str) -> str | None:
    low = cmd.lower()
    if "games" not in low and "_botcore" not in low:
        return None
    for f in BOT_FILES:
        if f.lower() in low:
            return f
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if data.get("tool_name") not in TOOLS:
        sys.exit(0)
    if OFF.exists():
        sys.exit(0)

    ti = data.get("tool_input") or {}
    cmd = ti.get("command") or ""
    if not cmd or not RE_PYTHON_EXE.search(cmd):
        sys.exit(0)

    bot = touches_bot(cmd)
    if not bot:
        sys.exit(0)

    wmi = bool(RE_WMI_CREATE.search(cmd) and RE_CREATE_VERB.search(cmd))
    startproc = bool(RE_START_PROC.search(cmd) and not RE_HIDDEN.search(cmd))
    if not (wmi or startproc):
        sys.exit(0)

    weg = "WMI Win32_Process.Create" if wmi else "Start-Process ohne -WindowStyle Hidden"
    print(
        "BLOCKED gamebot-console-guard: dieser Start ({weg}) benutzt blankes `python.exe` "
        "fuer {bot} -> der Prozess bekommt eine SICHTBARE Konsole, Windows Terminal startet "
        "kalt = Terminal-Blitz auf der Nutzer Desktop (gemessen 2026-08-11).\n"
        "\n"
        "FIX — eines davon:\n"
        "  1. `python.exe` durch `pythonw.exe` ersetzen (GUI-Subsystem = gar keine Konsole).\n"
        "     Kein Shell-Redirect noetig, die Bots loggen selbst in bot_*.log.\n"
        "  2. Besser: den kanonischen Deploy nutzen statt selbst zu bauen —\n"
        "     `python _botcore\\redeploy.py --serial <SERIAL>`  (killt + startet fensterlos, verifiziert)\n"
        "     bzw. `_bots_control.py loop <SERIAL>` fuer einen Einzel-Loop.\n"
        "\n"
        "Hintergrund: _botcore/winhide.py faengt den Fehlstart zwar ab, kann den Blitz aber nur "
        "verkuerzen — die Konsole existiert dann schon. Verhindern geht nur beim Start.\n"
        "Notausgang (bewusste Ausnahme): ~/.claude/flags/gamebot_console_guard.off anlegen."
        .format(weg=weg, bot=bot),
        file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
