#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PreToolUse-Guard: schuetzt Games/_botcore vor Schreibzugriffen fremder Bot-Sessions.

der Nutzer-Entscheid 2026-11-13: Der Bot-Kern (_botcore) wird von EINER Session verwaltet
("Bot-Kern Verwaltung", Projekt-Ordner Games/ bzw. Games/_botcore). Die drei Bot-Sessions
aendern nur ihren eigenen Bot-Ordner und melden Kern-Bedarf per SendMessage dorthin.

Grund fuer einen Hook statt einer Regel: Die Bot-Sessions laufen 24/7 mit Auto-Compact und
abgeschaltetem Context-Nag (Memory 92a268a6) - eine reine Doku-Regel driftet dort weg,
ein Hook nicht.

Verhalten: exit 2 (Block, Meldung auf stderr) wenn ein Schreibzugriff auf _botcore aus
einem Bot-Ordner kommt. Sonst exit 0. Jeder Fehler -> exit 0 (best effort, blockt nie
aus Versehen die ganze Session).

Notausgang (nur mit des Nutzers Ja): touch Games/_botcore/.core_guard.off
Selbsttest: python gamebot_core_guard.py --selftest
"""
import json
import os
import re
import sys

WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
# Steuer-Skripte im Games-Root, die seit MB82 (2026-11-13) ebenfalls dem Kern gehoeren.
CORE_ROOT_FILES = ("_bots_control.py", "bots_start.bat", "bots_restart_detached.ps1")
_CORE_TOKEN = r"(?:_botcore|_bots_control\.py|bots_start\.bat|bots_restart_detached\.ps1)"
# Schreib-Verben fuer Bash; Lesen und Ausfuehren (cat/grep/python ...) bleiben frei.
BASH_WRITE = re.compile(
    r"(>>?\s*\S*" + _CORE_TOKEN + r"|"
    r"\b(sed\s+-i|tee|truncate|chmod|chown)\b[^|;&]*" + _CORE_TOKEN + r"|"
    r"\b(cp|mv|rm|rmdir|mkdir|touch|dd)\b[^|;&]*" + _CORE_TOKEN + r")",
    re.IGNORECASE,
)
_CORE_MENTION = re.compile(_CORE_TOKEN, re.IGNORECASE)
BOT_DIRS = ("cellsurvivor", "survivor_io", "idleslayer")

MSG = (
    "BLOCKIERT: Schreibzugriff auf den geteilten Bot-Kern (_botcore/ bzw. die Steuer-Skripte\n"
    "_bots_control.py, BOTS_START.bat, BOTS_RESTART_DETACHED.ps1) aus einer Bot-Session.\n"
    "Zustaendig ist seit 2026-11-13 ausschliesslich die Session 'Bot-Kern Verwaltung'\n"
    "(der Nutzer-Entscheid, Gesetz in Games/CLAUDE.md, Ledger in _botcore/OWNERSHIP.md).\n"
    "\n"
    "Richtiger Weg: ListAgents -> SendMessage an 'Bot-Kern Verwaltung' mit\n"
    "  (1) was im Kern gebraucht wird, (2) Beleg: Befehl + woertliche Ausgabe, (3) Vorschlag.\n"
    "Danach am eigenen Bot weiterarbeiten, nicht auf die Antwort warten.\n"
    "KEINE Workaround-Kopie im eigenen Bot-Ordner anlegen - so entstand CellSurvivor/bots/core.py.\n"
    "Notfall (Bot steht, Kern ist die Ursache): der Nutzer fragen. Eine Peer-Session kann das nicht freigeben.\n"
)


def _norm(p):
    try:
        return os.path.normpath(os.path.abspath(str(p))).replace("\\", "/").lower()
    except Exception:
        return ""


def _is_core_path(path):
    """Zielt der Pfad in _botcore/ oder auf ein Kern-Steuerskript im Games-Root?"""
    n = _norm(path)
    if "/games/_botcore/" in n or n.endswith("/games/_botcore"):
        return True
    return any(n.endswith("/games/" + f) for f in CORE_ROOT_FILES)


def _is_core_session(cwd):
    """Ist das Arbeitsverzeichnis die Kern-Session (Games/ oder Games/_botcore)?"""
    n = _norm(cwd)
    if n.endswith("/games") or n.endswith("/games/_botcore"):
        return True
    # kein Bot-Ordner und nicht unter Games -> nicht unsere Sache
    return False


def _is_bot_session(cwd):
    n = _norm(cwd)
    if "/games/" not in n + "/":
        return False
    return any(("/games/" + b) in n + "/" for b in BOT_DIRS)


def _guard_off(cwd, target):
    for base in (target, cwd):
        n = _norm(base)
        i = n.find("/games/")
        if i == -1:
            continue
        flag = n[: i + len("/games/")] + "_botcore/.core_guard.off"
        if os.path.exists(flag):
            return True
    return False


def decide(tool_name, tool_input, cwd):
    """-> (block: bool, reason: str). Reine Funktion, fuer den Selbsttest."""
    if _is_core_session(cwd):
        return False, "kern-session"
    if not _is_bot_session(cwd):
        return False, "ausserhalb-games"

    target = ""
    if tool_name in WRITE_TOOLS:
        target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if not _is_core_path(target):
            return False, "kein kern-pfad"
    elif tool_name == "Bash":
        cmd = tool_input.get("command") or ""
        if not _CORE_MENTION.search(cmd) or not BASH_WRITE.search(cmd):
            return False, "bash ohne kern-schreibmuster"
        target = cwd
    else:
        return False, "tool irrelevant"

    if _guard_off(cwd, target):
        return False, "notausgang .core_guard.off"
    return True, "kern-schreibzugriff aus bot-session"


def _selftest():
    games = "C:/Users/der Nutzer/OneDrive/Dokumente/Games"
    cases = [
        # (tool, input, cwd, erwartet_block)
        ("Edit", {"file_path": games + "/_botcore/core.py"}, games + "/IdleSlayer", True),
        ("Write", {"file_path": games + "/_botcore/neu.py"}, games + "/Survivor_io", True),
        ("Edit", {"file_path": games + "/_botcore/core.py"}, games, False),
        ("Edit", {"file_path": games + "/_botcore/core.py"}, games + "/_botcore", False),
        ("Edit", {"file_path": games + "/IdleSlayer/run.py"}, games + "/IdleSlayer", False),
        ("Bash", {"command": "cat ../_botcore/core.py"}, games + "/IdleSlayer", False),
        ("Bash", {"command": "python ../_botcore/selfcheck.py idle"}, games + "/IdleSlayer", False),
        ("Bash", {"command": "sed -i s/a/b/ ../_botcore/core.py"}, games + "/IdleSlayer", True),
        ("Bash", {"command": "echo x >> ../_botcore/core.py"}, games + "/CellSurvivor", True),
        ("Bash", {"command": "cp -a ../_botcore/core.py ../_botcore/core.py.bak"}, games + "/CellSurvivor", True),
        ("Read", {"file_path": games + "/_botcore/core.py"}, games + "/IdleSlayer", False),
        ("Edit", {"file_path": "C:/tmp/x.py"}, "C:/tmp", False),
        # MB82: Steuer-Skripte im Games-Root gehoeren dem Kern
        ("Edit", {"file_path": games + "/_bots_control.py"}, games + "/CellSurvivor", True),
        ("Write", {"file_path": games + "/BOTS_START.bat"}, games + "/IdleSlayer", True),
        ("Edit", {"file_path": games + "/BOTS_RESTART_DETACHED.ps1"}, games, False),
        ("Bash", {"command": "python ../_bots_control.py status"}, games + "/Survivor_io", False),
        ("Bash", {"command": "sed -i s/a/b/ ../_bots_control.py"}, games + "/Survivor_io", True),
        ("Edit", {"file_path": games + "/IdleSlayer/_bots_control_notes.md"}, games + "/IdleSlayer", False),
    ]
    bad = 0
    for tool, ti, cwd, want in cases:
        got, why = decide(tool, ti, cwd)
        ok = got == want
        bad += 0 if ok else 1
        print("%s %-6s %-28s cwd=%-18s -> block=%s (%s)" % (
            "OK  " if ok else "FAIL", tool,
            (ti.get("file_path") or ti.get("command") or "")[-28:],
            os.path.basename(cwd), got, why))
    print("\n%d/%d ok" % (len(cases) - bad, len(cases)))
    return 1 if bad else 0


def main():
    if "--selftest" in sys.argv:
        return _selftest()
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        tool_name = data.get("tool_name") or ""
        tool_input = data.get("tool_input") or {}
        cwd = data.get("cwd") or os.getcwd()
        block, _why = decide(tool_name, tool_input, cwd)
        if block:
            sys.stderr.write(MSG)
            return 2
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
