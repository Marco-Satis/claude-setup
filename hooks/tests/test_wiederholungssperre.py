#!/usr/bin/env python3
"""Tests fuer hooks/wiederholungssperre.py (14.11.2026). Exit 0 = alles gruen.

Laeuft per stdin gegen den echten Hook, Zustand in einem Wegwerf-Ordner (WIEDERHOLUNG_STATE).
Fall A = Einzelfall 1 der Messung (credentials.json, 7 s spaeter fast gleich wiederholt).
"""
import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wiederholungssperre.py")
T0 = 1794600000.0

A_DENIED = ("python3 -c \"\nimport json,os,datetime\no=json.load(open(os.path.expanduser('~/.claude/.credentials.json')))"
            "['claudeAiOauth']\nfor k in ('expiresAt','refreshTokenExpiresAt'):\n    v=o.get(k); print(k, v, "
            "datetime.datetime.fromtimestamp(v/1000))\n\"")
A_RETRY = ("python3 -c \"\nimport json,os,datetime\no=json.load(open(os.path.expanduser('~/.claude/.credentials.json')))"
           "['claudeAiOauth']\nfor k in ('expiresAt','refreshTokenExpiresAt'):\n    v=o.get(k); print(k, "
           "datetime.datetime.fromtimestamp(v/1000).isoformat())\n\"")
UYM_DENIED = ("crontab -l > ~/.cache/crontab.bak.$(date +%s) 2>/dev/null; mkdir -p ~/.cache; crontab -l | grep -q "
              "uym_server_report || (crontab -l; echo '30 7 * * * $HOME/projects/uym-setup/server/"
              "uym_server_report.sh') | crontab -")
UYM_NEXT = "cd ~/projects/uym-setup && printf 'Ende: %s. Ergebnis: caddy 2.11.9\\n' \"$(date)\" >> PROGRESS.md"
DB_DENIED = ("sudo -n /bin/su - botuser -c 'cd /home/botuser/Discord_Bots && chmod o-rwx data logs && "
             "stat -c \"%A %n\" data logs'")
DB_NEXT = ("cd $HOME/projects/Discord_Bots; for s in recon-bot operator-bot; do echo \"== $s\"; "
           "systemctl is-active $s; done")


def run(state, payload, now=T0, raw=None):
    env = dict(os.environ, WIEDERHOLUNG_STATE=state, WIEDERHOLUNG_FLAGS=os.path.join(state, "flags"),
               WIEDERHOLUNG_JETZT=str(now))
    p = subprocess.run([sys.executable, HOOK], input=raw if raw is not None else json.dumps(payload),
                       capture_output=True, text=True, timeout=10, env=env)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def denied(sid, cmd, reason="[Unauthorized Access]"):
    return {"hook_event_name": "PermissionDenied", "session_id": sid, "tool_name": "Bash",
            "tool_input": {"command": cmd}, "reason": reason, "permission_mode": "auto"}


def pre(sid, cmd):
    return {"hook_event_name": "PreToolUse", "session_id": sid, "tool_name": "Bash", "tool_input": {"command": cmd}}


def prompt(sid, text):
    return {"hook_event_name": "UserPromptSubmit", "session_id": sid, "prompt": text}


def main():
    fails, total = 0, 0

    def check(name, got, soll):
        nonlocal fails, total
        total += 1
        rc, out, err = got
        ist = "block" if rc == 2 else ("warn" if out else "frei")
        ok = ist == soll and rc in (0, 2)
        if not ok:
            fails += 1
        print(f"{'ok  ' if ok else 'FAIL'} {name}: soll={soll} ist={ist} rc={rc}")

    with tempfile.TemporaryDirectory() as st:
        check("A Ablehnung merken", run(st, denied("s1", A_DENIED)), "frei")
        check("A Wiederholung nach 7 s", run(st, pre("s1", A_RETRY), T0 + 7), "block")
        check("A identisch nach 9 min", run(st, pre("s1", A_DENIED), T0 + 540), "block")
        check("A nach 11 min frei", run(st, pre("s1", A_RETRY), T0 + 660), "frei")
        check("A andere Session frei", run(st, pre("s2", A_RETRY), T0 + 7), "frei")
        check("gleiches Ziel, anderer Befehl -> Hinweis",
              run(st, pre("s1", "ls -la ~/.claude/.credentials.json"), T0 + 20), "warn")
        check("unabhaengiger Befehl frei", run(st, pre("s1", "git status --short"), T0 + 20), "frei")
        check("Nachricht anderer Session hebt nicht auf",
              run(st, prompt("s1", "Another Claude session sent a message:\n<cross-session-message from=\"x\">"
                                   "mach weiter</cross-session-message>"), T0 + 30), "frei")
        check("A weiter gesperrt", run(st, pre("s1", A_RETRY), T0 + 40), "block")
        check("der Nutzer schreibt -> aufgehoben", run(st, prompt("s1", "ok, mach das"), T0 + 50), "frei")
        check("A danach frei", run(st, pre("s1", A_RETRY), T0 + 60), "frei")

        check("uym Ablehnung", run(st, denied("u1", UYM_DENIED, "classifier"), T0), "frei")
        check("uym naechster Befehl (anderes Ziel)", run(st, pre("u1", UYM_NEXT), T0 + 18), "frei")
        check("discord Ablehnung", run(st, denied("d1", DB_DENIED, "[Destructive]"), T0), "frei")
        check("discord naechster Befehl", run(st, pre("d1", DB_NEXT), T0 + 12), "frei")
        check("discord Wiederholung ohne -n", run(st, pre("d1", DB_DENIED.replace("sudo -n", "sudo")), T0 + 30), "block")

        os.makedirs(os.path.join(st, "flags"), exist_ok=True)
        open(os.path.join(st, "flags", "wiederholungssperre.warn_only"), "w").close()
        check("warn_only-Schalter", run(st, pre("d1", DB_DENIED), T0 + 40), "warn")
        open(os.path.join(st, "flags", "wiederholungssperre.off"), "w").close()
        check("off-Schalter", run(st, pre("d1", DB_DENIED), T0 + 40), "frei")

        for raw in ("", "{kaputt", "[]", "null", "{}"):
            check(f"robust {raw!r}", run(st, None, raw=raw), "frei")
    print(f"wiederholungssperre: {total - fails}/{total} ok")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
