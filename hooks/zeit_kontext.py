#!/usr/bin/env python3
"""zeit_kontext.py - UserPromptSubmit hook: active time awareness (der Nutzer 2026-11-13).

Injects the current local time and the gap since the previous prompt of the same session, e.g.
"[Zeit] Fr 13.11.2026 23:14:05 · letzte Nachricht 22:58 (vor 16 min)". After a gap of 60 min or
more it adds a reminder to check what happened in between before answering.

Best effort: never blocks, always exit 0. State: ~/.claude/state/zeit/<session>.ts (one float).
"""
import datetime
import json
import os
import sys
import time

STATE = os.path.expanduser("~/.claude/state/zeit")
TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
LANG_MIN = 60


def dauer(sek):
    m = int(sek // 60)
    if m < 60:
        return f"{m} min"
    h, m = divmod(m, 60)
    if h < 48:
        return f"{h} h {m} min" if m else f"{h} h"
    return f"{h // 24} Tagen {h % 24} h"


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    sid = "".join(c for c in str(data.get("session_id", "")) if c.isalnum() or c == "-")[:64] or "ohne-id"
    jetzt = time.time()
    now = datetime.datetime.now()
    text = f"[Zeit] {TAGE[now.weekday()]} {now:%d.%m.%Y %H:%M:%S} (lokal)"
    pfad = os.path.join(STATE, sid + ".ts")
    # Messages from other sessions also fire UserPromptSubmit; they must not reset "der Nutzer's last message".
    von_session = "<cross-session-message" in str(data.get("prompt", ""))
    try:
        vorher = float(open(pfad).read().strip())
        luecke = max(0.0, jetzt - vorher)
        text += f" · letzte Nachricht von der Nutzer {datetime.datetime.fromtimestamp(vorher):%d.%m. %H:%M} (vor {dauer(luecke)})"
        if luecke >= LANG_MIN * 60 and not von_session:
            text += (" · Längere Pause: vor dem Antworten kurz prüfen, was inzwischen passiert ist "
                     "(Postfach/Nachrichten, Routine-Reports, PROGRESS, der Nutzer-Block) und es in einem Satz nennen.")
    except (OSError, ValueError):
        text += " · erste Nachricht dieser Session seit Einführung"
        try:  # retention: drop state of sessions idle for more than 30 days (rules/backup-aufbewahrung.md)
            for e in os.scandir(STATE):
                if e.name.endswith(".ts") and jetzt - e.stat().st_mtime > 30 * 86400:
                    os.remove(e.path)
        except OSError:
            pass
    if von_session:
        text += " · (diese Eingabe ist eine Session-Nachricht, nicht von der Nutzer)"
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}}))
        return
    try:
        os.makedirs(STATE, exist_ok=True)
        tmp = pfad + ".tmp"
        with open(tmp, "w") as f:
            f.write(str(int(jetzt)))
        os.replace(tmp, pfad)
    except OSError:
        pass
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a context hook must never break the session
        pass
    sys.exit(0)
