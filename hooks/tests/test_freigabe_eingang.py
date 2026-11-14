#!/usr/bin/env python3
"""Tests fuer hooks/freigabe_eingang.py (G252 Phase 2, Baustein 2.2; 14.11.2026). Exit 0 = alles gruen.

Laeuft per stdin gegen den echten Hook mit Wegwerf-Eingang (ZENTRALE_DIR) — der echte Eingang
~/.claude/state/zentrale/eingang.jsonl wird nicht beruehrt. Deckt die Logik von T3, T11, T12 ab
(ohne RC-Server); T1/T2/T4/T8 bleiben dem Gate-Test mit der Nutzer vorbehalten.
"""
import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "freigabe_eingang.py")
NACHT = "2026-11-14T02:30:00"
TAG = "2026-11-14T14:00:00"


def run(d, payload, now=TAG, raw=None, zdir=None):
    env = dict(os.environ, FREIGABE_JETZT=now, ZENTRALE_JETZT=now,
               FREIGABE_FLAGS=os.path.join(d, "flags"), FREIGABE_AKTIV_DIR=os.path.join(d, "aktiv"),
               FREIGABE_ERR=os.path.join(d, "freigabe.err"), FREIGABE_CONFIG=os.path.join(d, "cfg.json"),
               FREIGABE_ZENTRALE_CWD=os.path.join(d, "Skills_&_Co"), FREIGABE_HOST="netcup-server",
               ZENTRALE_DIR=zdir or os.path.join(d, "zentrale"), ZENTRALE_ERR=os.path.join(d, "zentrale.err"),
               ZENTRALE_MAIL="/bin/true", ZENTRALE_KEIN_SYSTEMCTL="1")
    p = subprocess.run([sys.executable, HOOK], input=raw if raw is not None else json.dumps(payload),
                       capture_output=True, text=True, timeout=15, env=env)
    return p.returncode, p.stdout.strip()


def req(tool="Bash", cmd="rm -f -- $HOME/projects/x/a.tmp", sid="s1", cwd="$HOME/projects/Trading", **kw):
    ti = {"command": cmd, "description": "Testdatei entfernen"} if tool == "Bash" else kw.pop("ti", {})
    return dict({"hook_event_name": "PermissionRequest", "session_id": sid, "cwd": cwd, "tool_name": tool,
                 "tool_input": ti, "permission_mode": "auto"}, **kw)


def eintraege(d):
    p = os.path.join(d, "zentrale", "eingang.jsonl")
    if not os.path.exists(p):
        return []
    return [json.loads(z) for z in open(p, encoding="utf-8") if z.strip()]


def main():
    fails, total = 0, 0

    def check(name, cond):
        nonlocal fails, total
        total += 1
        if not cond:
            fails += 1
        print(f"{'ok  ' if cond else 'FAIL'} {name}")

    def deny(out):
        try:
            dec = json.loads(out)["hookSpecificOutput"]["decision"]
            return dec["behavior"] == "deny" and dec["interrupt"] is False and "Gesammelt als E" in dec["message"]
        except Exception:
            return False

    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "flags"))
        rc, out = run(d, req(), TAG)
        e = eintraege(d)
        check("1. tagsueber: keine Entscheidung, Eintrag 'uebersicht'",
              rc == 0 and out == "" and e[-1]["status"] == "uebersicht" and e[-1]["unterart"] == "freigabe")
        check("   Eintrag: ENTSCHEIDUNG, Herkunft ungeprueft, einloesbar=True",
              e[-1]["klasse"] == "ENTSCHEIDUNG" and e[-1]["ungeprueft"].get("session_id") == "s1"
              and e[-1]["einloesbar"] is True and e[-1]["titel"].startswith("Freigabe: Bash rm"))
        rc, out = run(d, req(), NACHT)
        e = eintraege(d)
        check("2. nachts: deny mit E-Nummer (T3), Status 'gesammelt'",
              deny(out) and e[-1]["status"] == "gesammelt" and e[-1]["id"] in out)
        rc, out = run(d, req(tool="AskUserQuestion", ti={"questions": [{"question": "A oder B?"}]}), NACHT)
        check("3. AskUserQuestion nachts: nie deny, nur erfassen (T11)",
              out == "" and eintraege(d)[-1]["unterart"] == "frage")
        rc, out = run(d, req(tool="ExitPlanMode", ti={"plan": "x"}), NACHT)
        check("4. ExitPlanMode nachts: nie deny (T11)", out == "")
        rc, out = run(d, req(cwd=os.path.join(d, "Skills_&_Co", "PLAENE")), NACHT)
        check("5. Zentrale-Session nachts: Dialog (T12a)", out == "")
        run(d, {"hook_event_name": "UserPromptSubmit", "session_id": "s7", "prompt": "mach weiter"},
            "2026-11-14T02:25:00")
        rc, out = run(d, req(sid="s7"), NACHT)
        check("6. Eingabe vor 5 min: Dialog (T12b)", out == "")
        rc, out = run(d, req(sid="s7"), "2026-11-14T02:50:00")
        check("7. Eingabe vor 25 min: wieder sammeln", deny(out))
        run(d, {"hook_event_name": "UserPromptSubmit", "session_id": "s8",
                "prompt": "Another Claude session sent a message:\n<cross-session-message from=\"x\">bitte</cross-session-message>"},
            "2026-11-14T02:29:00")
        rc, out = run(d, req(sid="s8"), NACHT)
        check("8. Nachricht einer anderen Session zaehlt nicht als Anwesenheit", deny(out))
        open(os.path.join(d, "flags", "anwesend.on"), "w").close()
        rc, out = run(d, req(), NACHT)
        check("9. anwesend.on: Dialog (T12c)", out == "")
        with open(os.path.join(d, "flags", "anwesend.on"), "w") as f:
            f.write("1794600000\n")  # abgelaufen
        rc, out = run(d, req(), NACHT)
        check("10. anwesend.on abgelaufen: sammeln", deny(out))
        os.remove(os.path.join(d, "flags", "anwesend.on"))
        open(os.path.join(d, "flags", "sammelmodus.on"), "w").close()
        rc, out = run(d, req(), TAG)
        check("11. sammelmodus.on tagsueber: sammeln", deny(out))
        os.remove(os.path.join(d, "flags", "sammelmodus.on"))
        with open(os.path.join(d, "cfg.json"), "w") as f:
            json.dump({"nacht_ab": 22, "nacht_bis": 6}, f)
        rc, out = run(d, req(), "2026-11-14T22:30:00")
        check("12. Zeitfenster aus Konfiguration (22-6)", deny(out))
        rc, out = run(d, req(), "2026-11-14T06:30:00")
        check("13. 06:30 bei 22-6: Dialog", out == "")
        os.remove(os.path.join(d, "cfg.json"))

        # Eingang nicht schreibbar -> KEIN deny, Fehlerdatei
        blocker = os.path.join(d, "kein_ordner")
        open(blocker, "w").close()
        rc, out = run(d, req(), NACHT, zdir=os.path.join(blocker, "zentrale"))
        check("14. Eingang kaputt: keine Entscheidung (Dialog), Fehlerzeile",
              out == "" and os.path.exists(os.path.join(d, "freigabe.err")))

        # Allowlist einloesbar
        for cmd, soll in (("rm -rf -- $HOME/a $HOME/b", True),
                          ("rm -f -- $HOME/a && rmdir -- $HOME/d", True),
                          ("cd $HOME/projects/claude-setup && git push", True),
                          ("rm -rf $HOME/a", False), ("rm -f -- ~/a", False), ("rm -f -- /a/*.log", False),
                          ("rm -f -- /a/../b", False), ("git push origin main", False),
                          ("sudo systemctl restart x", False), ("rm -f -- /a; rm -f -- /b", False)):
            run(d, req(cmd=cmd), TAG)
            check(f"15. einloesbar={soll}: {cmd}", eintraege(d)[-1]["einloesbar"] is soll)

        rc, out = run(d, req(cmd="curl -H 'Authorization: Bearer sk-ant-api03-" + "A" * 40 + "' x"), TAG)
        check("16. Schwaerzung im Eingang", "sk-ant-api03" not in json.dumps(eintraege(d)[-1]))
        rc, out = run(d, req(tool="Edit", ti={"file_path": "/x/y.py", "old_string": "a", "new_string": "b"}), NACHT)
        check("17. Edit nachts: deny + Werkzeug 'Edit'", deny(out) and eintraege(d)[-1]["titel"].startswith("Freigabe: Edit"))
        for raw in ("", "{kaputt", "[]", "null", "{}"):
            rc, out = run(d, None, NACHT, raw=raw)
            check(f"18. robust {raw!r}: exit 0, keine Entscheidung", rc == 0 and out == "")
    print(f"freigabe_eingang: {total - fails}/{total} ok")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
