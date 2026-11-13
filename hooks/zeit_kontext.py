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
# Sammelmodus der Zentrale (der Nutzer 2026-11-14): nach ABWESEND_MIN ohne Antwort nur noch sammeln, bei Rückkehr vorlegen.
ABWESEND_MIN = 10
SAMMEL = os.path.expanduser("~/.claude/scripts/sammel.py")


def ist_zentrale(data):
    # Nur die netcup-Session "Setup Server"; Setup PC teilt den Ordnernamen, schreibt aber nicht in die Mappe.
    return os.name != "nt" and "Skills_&_Co" in str(data.get("cwd") or os.getcwd())


def offene_eintraege():
    try:
        sys.path.insert(0, os.path.dirname(SAMMEL))
        import sammel  # noqa: E402
        return len(sammel.offene())
    except Exception:
        return 0


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
    _p = str(data.get("prompt", ""))
    von_session = any(m in _p for m in ("<cross-session-message", "<task-notification", "[SYSTEM NOTIFICATION",
                                          "<agent-message", "Tool loaded."))
    try:
        vorher = float(open(pfad).read().strip())
        luecke = max(0.0, jetzt - vorher)
        text += f" · letzte Nachricht von der Nutzer {datetime.datetime.fromtimestamp(vorher):%d.%m. %H:%M} (vor {dauer(luecke)})"
        if luecke >= LANG_MIN * 60 and not von_session:
            text += (" · Längere Pause: vor dem Antworten kurz prüfen, was inzwischen passiert ist "
                     "(Postfach/Nachrichten, Routine-Reports, PROGRESS, der Nutzer-Block) und es in einem Satz nennen.")
        if ist_zentrale(data) and luecke >= ABWESEND_MIN * 60:
            if von_session:
                text += (f" · [Sammelmodus] der Nutzer antwortet seit {dauer(luecke)} nicht. Eingang erledigen bzw. "
                         "quittieren wie immer, aber im Chat höchstens 1 Zeile, keine Tabellen oder Zusammenfassungen. "
                         "Jeden Eingang eintragen: python3 ~/.claude/scripts/sammel.py <sicherheit|braucht-dich|"
                         "erledigt|laeuft|info> \"<session> | <was> | <stand, z. B. MB-Nummer>\". "
                         "Entscheidungen weiter als MB-Zeile.")
            else:
                n = offene_eintraege()
                if n:
                    text += (f" · [Rückkehr] der Nutzer war {dauer(luecke)} weg, {n} Einträge in der Sammelmappe. "
                             "Erst seine Nachricht beantworten, dann die Sammelmappe vorlegen (sammel.py --offen): "
                             "3-5 Zeilen Kurzfassung, was er entscheiden muss, was erledigt ist; danach "
                             "python3 ~/.claude/scripts/sammel.py --vorgelegt.")
    except (OSError, ValueError):
        text += " · erste Nachricht dieser Session seit Einführung"
        try:  # retention: drop state of sessions idle for more than 30 days (rules/backup-aufbewahrung.md)
            for e in os.scandir(STATE):
                if e.name.endswith(".ts") and jetzt - e.stat().st_mtime > 30 * 86400:
                    os.remove(e.path)
        except OSError:
            pass
    if von_session:
        text += " · (diese Eingabe ist eine Session- bzw. Systemnachricht, nicht von der Nutzer)"
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
