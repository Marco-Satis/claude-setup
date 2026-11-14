#!/usr/bin/env python
"""Wiederholungssperre nach Ablehnung (der Nutzer 2026-11-14 10:46, „1 bis 5 ja“, Punkt 2).

Anlass (REGEL_EINHALTUNG_2026-11-14.md, Fall 1): Der Auto-Mode-Classifier lehnte einen
Lesezugriff auf ~/.claude/.credentials.json ab [Unauthorized Access]; 7 s spaeter lief ein
fast gleicher Befehl (nur das Ausgabeformat geaendert) durch.

Ein Skript, drei Ereignisse (erkannt an `hook_event_name`):
  PermissionDenied (matcher Bash)  merkt sich den abgelehnten Befehl je session_id.
                                   Laut hooks.md feuert das NUR bei Auto-Mode-Ablehnungen
                                   (Classifier, auch ohne Verdict) — nicht bei Ablehnung im
                                   Dialog, nicht bei PreToolUse-Hook-Blocks, nicht bei deny-Regeln.
  PreToolUse (matcher Bash)        vergleicht den neuen Befehl mit den Ablehnungen der letzten
                                   10 min. Sperre (exit 2) nur bei klarer Wiederholung:
                                   gleiches Ziel (Pfad/Host) UND Aehnlichkeit >= 0,6, oder
                                   Aehnlichkeit >= 0,9. Schwaechere Treffer: nur Hinweis.
  UserPromptSubmit                 der Nutzer hat geschrieben -> Sperren der Session aufheben
                                   (Nachrichten anderer Sessions und Task-Meldungen zaehlen nicht).

Fehlalarme sind schlimmer als Luecken: im Zweifel nur Hinweis, jeder Fehler -> exit 0.
Zustand: ~/.claude/state/wiederholungssperre/<session_id>.json (je Maschine, synct nicht).
Schalter: ~/.claude/flags/wiederholungssperre.off (aus), ...warn_only (nie sperren).
Tests: hooks/tests/test_wiederholungssperre.py
"""
from __future__ import annotations

import difflib
import json
import os
import re
import sys
import time
from pathlib import Path

HOME = Path.home()
STATE = Path(os.environ.get("WIEDERHOLUNG_STATE") or HOME / ".claude" / "state" / "wiederholungssperre")
FLAGS = Path(os.environ.get("WIEDERHOLUNG_FLAGS") or HOME / ".claude" / "flags")
FENSTER = 600  # 10 min
BLOCK_GLEICHES_ZIEL = 0.6
BLOCK_OHNE_ZIEL = 0.9
WARN_OHNE_ZIEL = 0.75
HINWEIS = ("Nach einer Ablehnung nicht umformulieren, an der Nutzer geben: den abgelehnten Schritt als "
           "MB-Zeile an „Setup Server“ melden (Befehl + Ablehnungsgrund) und ohne ihn weiterarbeiten.")

_PATH_RE = re.compile(
    r"(?:~|\$HOME|\$\{HOME\}|[\w.\-]+)?/[\w.@%+\-/]*[\w\-]"
    r"|[\w.\-]+\.(?:json|env|py|sh|md|conf|cfg|ini|ya?ml|toml|txt|log|db|sqlite3?|key|pem|crt|service|timer|kdbx)\b")
_GENERIC = re.compile(r"^(?:/dev/.*|/proc/.*|/tmp|/usr(?:/.*)?|/bin/.*|/sbin/.*|/etc|/home|/home/\w+|"
                      r"\./?|\.\./?|/|~|python3?|bash)$")


def _now() -> float:
    v = os.environ.get("WIEDERHOLUNG_JETZT")
    return float(v) if v else time.time()


def _sid(data: dict) -> str:
    return "".join(c for c in str(data.get("session_id") or "") if c.isalnum() or c in "-_")[:80] or "ohne-id"


def ziele(cmd: str) -> set:
    out = set()
    home = str(HOME)
    # `cd <projektordner>` ist Arbeitsort, kein Ziel (sonst Hinweis bei jedem Befehl im Projekt)
    cmd = re.sub(r"(?:^|[;&|(\s])cd\s+(\"[^\"]*\"|'[^']*'|\S+)", " ", cmd)
    for m in _PATH_RE.finditer(cmd):
        p = m.group(0)
        p = re.sub(r"^(?:\$HOME|\$\{HOME\})", "~", p)
        if p.startswith(home):
            p = "~" + p[len(home):]
        p = p.rstrip("/")
        if p and not _GENERIC.match(p) and len(p) > 2:
            out.add(p)
    for m in re.finditer(r"\b(?:ssh|scp|rsync)\s+(?:-\S+\s+(?:\S+\s+)?)*([\w.@\-]+)", cmd):
        out.add("host:" + m.group(1))
    return out


def norm(cmd: str) -> str:
    return re.sub(r"\s+", " ", cmd).strip()[:2000]


def aehnlichkeit(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b), autojunk=False).ratio()


def _laden(sid: str) -> list:
    try:
        d = json.loads((STATE / f"{sid}.json").read_text(encoding="utf-8"))
        return [e for e in d if isinstance(e, dict)] if isinstance(d, list) else []
    except Exception:
        return []


def _speichern(sid: str, eintraege: list) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    p = STATE / f"{sid}.json"
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(eintraege, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


def bewerten(cmd: str, ablehnungen: list, now: float):
    """-> ('block'|'warn'|None, ablehnung, aehnlichkeit, gemeinsame_ziele)"""
    best = (None, None, 0.0, set())
    z_neu = ziele(cmd)
    for e in ablehnungen:
        if now - float(e.get("ts", 0)) > FENSTER:
            continue
        r = aehnlichkeit(cmd, e.get("cmd", ""))
        shared = z_neu & set(e.get("ziele", []))
        if (shared and r >= BLOCK_GLEICHES_ZIEL) or r >= BLOCK_OHNE_ZIEL:
            stufe = "block"
        elif shared or r >= WARN_OHNE_ZIEL:
            stufe = "warn"
        else:
            continue
        rang = {"block": 2, "warn": 1}[stufe]
        if best[0] is None or rang > {"block": 2, "warn": 1}[best[0]] or (rang == {"block": 2, "warn": 1}[best[0]] and r > best[2]):
            best = (stufe, e, r, shared)
    return best


def bei_ablehnung(data: dict) -> None:
    if data.get("tool_name") not in (None, "Bash"):
        return
    cmd = str((data.get("tool_input") or {}).get("command") or "")
    if not cmd.strip():
        return
    sid, now = _sid(data), _now()
    eintraege = [e for e in _laden(sid) if now - float(e.get("ts", 0)) <= FENSTER]
    eintraege.append({"ts": now, "cmd": cmd[:4000], "ziele": sorted(ziele(cmd)),
                      "grund": str(data.get("reason") or "")[:200], "agent_id": str(data.get("agent_id") or "")})
    _speichern(sid, eintraege[-20:])


def bei_prompt(data: dict) -> None:
    prompt = str(data.get("prompt") or "")
    if re.search(r"<cross-session-message|<task-notification|^Another Claude session sent a message", prompt[:600]):
        return
    sid = _sid(data)
    if (STATE / f"{sid}.json").exists():
        _speichern(sid, [])


def vor_bash(data: dict) -> None:
    if data.get("tool_name") not in (None, "Bash"):
        return
    cmd = str((data.get("tool_input") or {}).get("command") or "")
    if not cmd.strip():
        return
    sid = _sid(data)
    if not (STATE / f"{sid}.json").exists():
        return
    stufe, e, r, shared = bewerten(cmd, _laden(sid), _now())
    if not stufe:
        return
    grund = (e or {}).get("grund") or "ohne Angabe"
    alter = int(_now() - float((e or {}).get("ts", 0)))
    ziel = ", ".join(sorted(shared)[:3]) or "–"
    if stufe == "block" and not (FLAGS / "wiederholungssperre.warn_only").exists():
        sys.stderr.write(
            f"BLOCKED (Wiederholungssperre): Dieser Befehl gleicht einem vor {alter} s vom Auto-Mode "
            f"abgelehnten ({grund}; Aehnlichkeit {r:.2f}, gleiches Ziel: {ziel}). {HINWEIS} "
            f"Die Sperre endet nach 10 min oder mit des Nutzers naechster Nachricht.\n")
        sys.exit(2)
    text = (f"[wiederholungssperre] Achtung: aehnlich zu einem vor {alter} s abgelehnten Befehl "
            f"({grund}; Aehnlichkeit {r:.2f}, gleiches Ziel: {ziel}). Ist das derselbe Effekt auf anderem "
            f"Weg? Dann nicht ausfuehren. {HINWEIS}")
    print(json.dumps({"systemMessage": text,
                      "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text}},
                     ensure_ascii=False))


def main() -> None:
    for _s in (sys.stdin, sys.stdout, sys.stderr):  # Windows: sonst cp1252 und Umlaute scheitern still
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict) or (FLAGS / "wiederholungssperre.off").exists():
            sys.exit(0)
        ev = data.get("hook_event_name")
        if ev == "PermissionDenied":
            bei_ablehnung(data)
        elif ev == "UserPromptSubmit":
            bei_prompt(data)
        elif ev == "PreToolUse":
            vor_bash(data)
    except SystemExit:
        raise
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
