#!/usr/bin/env python3
"""Tests fuer hooks/empfang_erinnerung.py (14.11.2026). Exit 0 = alles gruen.

Baut kleine Transkripte im Wegwerf-Ordner (Format wie ~/.claude/projects/*/*.jsonl) und ruft den Hook
per stdin auf. EMPFANG_JETZT fixiert die Uhr (und schaltet die 0,7-s-Nachlese ab).
"""
import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "empfang_erinnerung.py")
NOW_ISO = "2026-11-14T10:00:00Z"
NOW = 1794650400.0  # = NOW_ISO


def xmsg(text, frm="bridge:session_01AAA", name="IdleSlayer_bot", ts=NOW_ISO, uuid="u1"):
    content = (f"Another Claude session sent a message:\n<cross-session-message from=\"{frm}\" "
               f"from-name=\"{name}\" from-mode=\"prompting\">\n{text}\n</cross-session-message>\n\nThis came from ...")
    return {"type": "user", "uuid": uuid, "timestamp": ts, "message": {"role": "user", "content": content}}


def send(to, ts=NOW_ISO):
    return {"type": "assistant", "timestamp": ts, "message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "SendMessage", "input": {"to": to, "message": "Empfangen: x – übernommen"}}]}}


def run(d, lines, sid="s1", raw=None, active=False):
    tp = os.path.join(d, f"{sid}.jsonl")
    with open(tp, "w", encoding="utf-8") as f:
        for l in lines:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    payload = {"hook_event_name": "Stop", "session_id": sid, "transcript_path": tp, "stop_hook_active": active,
               "last_assistant_message": "fertig"}
    env = dict(os.environ, EMPFANG_STATE=os.path.join(d, "state"), EMPFANG_JETZT=str(NOW))
    p = subprocess.run([sys.executable, HOOK], input=raw if raw is not None else json.dumps(payload),
                       capture_output=True, text=True, timeout=10, env=env)
    return p.returncode, p.stdout.strip()


def main():
    fails, total = 0, 0

    def check(name, got, soll_hinweis):
        nonlocal fails, total
        total += 1
        rc, out = got
        ok = rc == 0 and bool(out) == soll_hinweis
        if out:
            try:
                o = json.loads(out)
                ok = ok and o["hookSpecificOutput"]["hookEventName"] == "Stop" and "decision" not in o
            except Exception:
                ok = False
        if not ok:
            fails += 1
        print(f"{'ok  ' if ok else 'FAIL'} {name}: soll={'Hinweis' if soll_hinweis else 'still'} rc={rc}")

    frage = xmsg("MB: Frage an der Nutzer: Soll ein Truhenbrett eingebaut werden?")
    with tempfile.TemporaryDirectory() as d:
        check("1. Frage ohne Antwort", run(d, [frage], "a"), True)
        check("2. dieselbe Nachricht erneut -> nur einmal", run(d, [frage], "a"), False)
        check("3. Antwort per bridge-ID", run(d, [frage, send("bridge:session_01AAA")], "b"), False)
        check("4. Antwort per Namen", run(d, [frage, send("IdleSlayer_bot")], "c"), False)
        check("5. Antwort an andere Session zaehlt nicht", run(d, [frage, send("Cell Survivor")], "d"), True)
        check("6. reine Quittung", run(d, [xmsg("Empfangen: MB82 – erledigt")], "e"), False)
        check("7. Ergebnis-Meldung", run(d, [xmsg("MB114 erledigt: Token rotiert.")], "f"), False)
        check("8. ARBEITSBLOCK-Anstoss", run(d, [xmsg("ARBEITSBLOCK (geplanter Anstoß 09:00): bitte weiter")], "g"), False)
        check("9. Info ohne Auftrag", run(d, [xmsg("Neu live ist tap_loop.py.")], "h"), False)
        check("10. Auftrag 'bitte prüfen'", run(d, [xmsg("Bitte prüf den Hook auf netcup.")], "i"), True)
        check("11. alte Nachricht (> 45 min)", run(d, [xmsg("Kannst du X?", ts="2026-11-14T09:00:00Z")], "j"), False)
        check("12. stop_hook_active -> still", run(d, [frage], "k", active=True), False)
        check("13. zweite neue Nachricht danach -> wieder Hinweis",
              run(d, [frage, xmsg("Und noch: kannst du Y?", uuid="u2")], "a"), True)
        check("14. Antwort vor der Nachricht zaehlt nicht", run(d, [send("IdleSlayer_bot"), frage], "l"), True)
        for raw in ("", "{kaputt", "[]", "null", "{}",
                    json.dumps({"hook_event_name": "Stop", "transcript_path": "/gibt/es/nicht.jsonl"})):
            check(f"15. robust {raw[:25]!r}", run(d, [], "z", raw=raw), False)
    print(f"empfang_erinnerung: {total - fails}/{total} ok")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
