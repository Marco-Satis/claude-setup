#!/usr/bin/env python
"""PermissionRequest-Hook: Rueckfragen erfassen, nachts sammeln (G252 Phase 2, Baustein 2.2).

der Nutzer 2026-11-14 (Plan G252, Antwort 3 „Ja“; Bau freigegeben 10:46 „1 bis 5 ja“, Punkt 3).
NICHT VERDRAHTET: der Nutzer prueft vorher selbst im Gate-Test T2/T4/T8 (Plan 3.4). Der fertige
settings-Eintrag steht in PLAENE/REGEL_HOOKS_BAUBERICHT_2026-11-14.md.

Ablauf je PermissionRequest (stdin: tool_name, tool_input, cwd, session_id, agent_id, permission_mode):
  1. Modus bestimmen:
       sammeln  zwischen 23 und 07 Uhr (freigabe_config.json) oder Flag ~/.claude/flags/sammelmodus.on
       fragen   sonst, und IMMER: in der Zentrale (cwd unter ~/projects/Skills_&_Co), in einer Session
                mit eigener Eingabe in den letzten 20 min (state/zentrale/aktiv/<session_id>), oder wenn
                ~/.claude/flags/anwesend.on gilt (Inhalt optional Unix-Ablaufzeit).
     Ausnahmen schalten nur Richtung Dialog, nie Richtung allow (Grundsatz 6).
  2. Eintrag in den Eingang (scripts/zentrale_eingang.add, geschwaerzt, Klasse ENTSCHEIDUNG,
     Unterart `freigabe` bzw. `frage`; Herkunft im Block `ungeprueft`; `einloesbar` nach Allowlist 2.4).
  3. Entscheidung:
       fragen  -> keine Ausgabe, der native Dialog bleibt (Status `uebersicht`, laeuft nach 24 h ab)
       sammeln -> `deny` mit interrupt:false und Hinweistext — NUR wenn der Eintrag geschrieben wurde
       AskUserQuestion/ExitPlanMode -> nie deny, nur erfassen (Grundsatz 8)
  Es gibt KEIN allow. Fehler, Timeout, kaputtes JSON -> keine Entscheidung = normaler Dialog (Grundsatz 4);
  Schreibfehler zusaetzlich nach ~/.claude/logs/freigabe_eingang.err (rc-watchdog meldet neue Zeilen).

Zweiter Einstieg UserPromptSubmit: schreibt den Zeitstempel der letzten eigenen Eingabe je Session
(Nachrichten anderer Sessions und Task-Meldungen zaehlen nicht als Anwesenheit).

PC: zentrale_eingang.py nutzt fcntl -> unter Windows kein Import, also keine Entscheidung (Dialog wie
heute). Der SSH-Transport fuer den PC ist Aufgabe von Setup PC (Plan Abschnitt 6).
Test-Umgebung: FREIGABE_JETZT (ISO), FREIGABE_FLAGS, FREIGABE_AKTIV_DIR, FREIGABE_ERR, FREIGABE_CONFIG,
FREIGABE_ZENTRALE_CWD, FREIGABE_HOST, dazu ZENTRALE_DIR/ZENTRALE_ERR/ZENTRALE_JETZT. Tests: hooks/tests/test_freigabe_eingang.py
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shlex
import socket
import sys
from pathlib import Path

HOME = Path.home()
HOOKS = Path(__file__).resolve().parent
SCRIPTS = HOOKS.parent / "scripts"
FLAGS = Path(os.environ.get("FREIGABE_FLAGS") or HOME / ".claude" / "flags")
AKTIV = Path(os.environ.get("FREIGABE_AKTIV_DIR") or HOME / ".claude" / "state" / "zentrale" / "aktiv")
ERR = Path(os.environ.get("FREIGABE_ERR") or HOME / ".claude" / "logs" / "freigabe_eingang.err")
CONFIG = Path(os.environ.get("FREIGABE_CONFIG") or HOME / ".claude" / "state" / "zentrale" / "freigabe_config.json")
ZENTRALE_CWD = os.environ.get("FREIGABE_ZENTRALE_CWD") or str(HOME / "projects" / "Skills_&_Co")
FRAGEN_TOOLS = {"AskUserQuestion", "ExitPlanMode"}
DEFAULTS = {"nacht_ab": 23, "nacht_bis": 7, "aktiv_min": 20}


def jetzt() -> datetime.datetime:
    v = os.environ.get("FREIGABE_JETZT")
    return datetime.datetime.fromisoformat(v) if v else datetime.datetime.now()


def _err(msg: str) -> None:
    try:
        ERR.parent.mkdir(parents=True, exist_ok=True)
        with open(ERR, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg[:300]}\n")
    except Exception:
        pass


def config() -> dict:
    c = dict(DEFAULTS)
    try:
        d = json.loads(CONFIG.read_text(encoding="utf-8"))
        for k in DEFAULTS:
            if isinstance(d.get(k), int):
                c[k] = d[k]
    except Exception:
        pass
    return c


def _sid(data: dict) -> str:
    return "".join(c for c in str(data.get("session_id") or "") if c.isalnum() or c in "-_")[:80]


def _flag_gilt(name: str, now: datetime.datetime) -> bool:
    p = FLAGS / name
    if not p.exists():
        return False
    try:
        v = p.read_text(encoding="utf-8").strip()
        if v and re.fullmatch(r"\d{9,11}", v):
            return now.timestamp() < int(v)  # Ablaufzeit
    except Exception:
        pass
    return True


def _unter(pfad: str, basis: str) -> bool:
    try:
        p = os.path.normcase(os.path.realpath(pfad))
        b = os.path.normcase(os.path.realpath(basis))
        return p == b or p.startswith(b.rstrip("\\/") + os.sep)
    except Exception:
        return False


def modus(data: dict, now: datetime.datetime | None = None) -> tuple:
    """-> ('sammeln'|'fragen', grund)."""
    now = now or jetzt()
    c = config()
    if data.get("cwd") and _unter(str(data["cwd"]), ZENTRALE_CWD):
        return "fragen", "zentrale"
    if _flag_gilt("anwesend.on", now):
        return "fragen", "anwesend"
    sid = _sid(data)
    if sid:
        try:
            ts = float((AKTIV / sid).read_text(encoding="utf-8").strip())
            if 0 <= now.timestamp() - ts < c["aktiv_min"] * 60:
                return "fragen", "eingabe"
        except Exception:
            pass
    if _flag_gilt("sammelmodus.on", now):
        return "sammeln", "flag"
    h = now.hour
    ab, bis = c["nacht_ab"], c["nacht_bis"]
    nacht = (h >= ab or h < bis) if ab > bis else (ab <= h < bis)
    return ("sammeln", "nacht") if nacht else ("fragen", "tag")


def _segmente(cmd: str) -> list:
    try:
        sys.path.insert(0, str(HOOKS))
        from destructive_command_blocker import split_segments  # Tokenizer wiederverwenden
        return split_segments(cmd)
    except Exception:
        return [s.strip() for s in re.split(r"[;&|\n]", cmd) if s.strip()]


def werkzeug(tool: str, ti: dict) -> str:
    if tool != "Bash":
        return tool
    cmd = str(ti.get("command") or "")
    try:
        sys.path.insert(0, str(HOOKS))
        from destructive_command_blocker import cmd_name, skip_wrappers
        for seg in _segmente(cmd):
            toks = skip_wrappers(shlex.split(seg))
            if toks and toks[0] != "cd":
                return "Bash " + cmd_name(toks[0])[:30]
    except Exception:
        pass
    return "Bash"


_PFAD = re.compile(r"/[A-Za-z0-9._+@%/-]+")


def einloesbar(tool: str, ti: dict, host: str) -> bool:
    """Allowlist aus Plan 2.4 (nur Vorpruefung; die eigentliche Pruefung macht `einloesen`)."""
    if tool != "Bash" or "netcup" not in host.lower():
        return False
    cmd = str(ti.get("command") or "").strip()
    if not cmd or re.search(r"[|<>`$~*?\[\]{}()\n]|;|(?<!&)&(?!&)", cmd):
        return False
    m = re.fullmatch(r"cd (/\S+) && git push", cmd)
    if m:
        return bool(_PFAD.fullmatch(m.group(1)))
    segs = [s.strip() for s in cmd.split("&&")]
    for s in segs:
        toks = s.split()
        if not toks or toks[0] not in ("rm", "rmdir"):
            return False
        i = 1
        if i < len(toks) and toks[i] in ("-f", "-r", "-rf", "-fr"):
            i += 1
        if i >= len(toks) or toks[i] != "--" or i + 1 >= len(toks):
            return False
        if not all(_PFAD.fullmatch(p) and ".." not in p.split("/") for p in toks[i + 1:]):
            return False
    return True


def eintragen(data: dict, mod: str, grund: str) -> str | None:
    tool = str(data.get("tool_name") or "?")
    ti = data.get("tool_input") or {}
    if not isinstance(ti, dict):
        ti = {}
    frage = tool in FRAGEN_TOOLS
    host = os.environ.get("FREIGABE_HOST") or socket.gethostname()
    if tool == "Bash":
        inhalt = str(ti.get("command") or "")
    else:
        inhalt = json.dumps({k: v for k, v in ti.items() if k != "content"}, ensure_ascii=False)[:1500]
    cwd = str(data.get("cwd") or "")
    projekt = Path(cwd).name if cwd else "?"
    titel = f"{'Frage wartet' if frage else 'Freigabe'}: {werkzeug(tool, ti)} — {projekt}"
    text = f"{'Frage' if frage else 'Freigabe'}: {inhalt}"
    status = "gesammelt" if (mod == "sammeln" and not frage) else "uebersicht"
    try:
        if os.name == "nt":
            raise ImportError("zentrale_eingang braucht fcntl (nur netcup); PC-Transport per SSH ist Aufgabe von Setup PC")
        sys.path.insert(0, str(SCRIPTS))
        import zentrale_eingang as ze
        eid = ze.add(titel, text, klasse="ENTSCHEIDUNG", quelle="freigabe_eingang",
                     unterart="frage" if frage else "freigabe",
                     ungeprueft={"session_id": data.get("session_id"), "cwd": cwd, "agent_id": data.get("agent_id"),
                                 "description": ti.get("description"), "permission_mode": data.get("permission_mode")},
                     extra={"kurz": "Frage wartet" if frage else "Freigabe", "neu": False, "tool_name": tool,
                            "modus": mod, "modus_grund": grund, "host_kurz": host,
                            "einloesbar": (not frage) and einloesbar(tool, ti, host)},
                     status=status)
    except Exception as ex:
        _err(f"eintragen {tool}: {type(ex).__name__}: {ex}")
        return None
    if not eid:
        _err(f"eintragen {tool}: zentrale_eingang.add lieferte keine ID (siehe zentrale_eingang.err)")
    return eid


def bei_prompt(data: dict) -> None:
    prompt = str(data.get("prompt") or "")
    if re.search(r"<cross-session-message|<task-notification|^Another Claude session sent a message", prompt[:600]):
        return
    sid = _sid(data)
    if not sid:
        return
    AKTIV.mkdir(parents=True, exist_ok=True)
    p = AKTIV / sid
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
    tmp.write_text(f"{jetzt().timestamp():.0f}\n", encoding="utf-8")
    os.replace(tmp, p)


def bei_anfrage(data: dict) -> None:
    tool = str(data.get("tool_name") or "")
    mod, grund = modus(data)
    eid = eintragen(data, mod, grund)
    if tool in FRAGEN_TOOLS or mod != "sammeln" or not eid:
        return  # keine Entscheidung -> nativer Dialog
    msg = (f"Gesammelt als {eid} für Setup Server. Nicht erneut versuchen und nicht mit anderem Befehl "
           f"gleicher Wirkung umgehen. Ohne diesen Schritt weiterarbeiten, Wegwerf-Dateien ins Scratchpad, "
           f"{eid} im Abschluss nennen.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PermissionRequest",
                                             "decision": {"behavior": "deny", "message": msg, "interrupt": False}}},
                     ensure_ascii=False))


def main() -> None:
    for _s in (sys.stdin, sys.stdout, sys.stderr):  # Windows: sonst cp1252 und Umlaute scheitern still
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            sys.exit(0)
        ev = data.get("hook_event_name")
        if ev == "UserPromptSubmit":
            bei_prompt(data)
        elif ev == "PermissionRequest":
            bei_anfrage(data)
    except SystemExit:
        raise
    except Exception as ex:
        _err(f"main: {type(ex).__name__}: {ex}")
    sys.exit(0)


if __name__ == "__main__":
    main()
