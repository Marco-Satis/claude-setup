#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Notification Hook: wartende Sessions an die Zentrale melden (Dateiname bleibt aus Verdrahtungsgruenden).

Seit G252 (14.11.2026, Bausteine 1.3 und 1.9): kein Discord mehr. Freigabe-Dialoge, Fragen und
"wartet auf Eingabe" werden ENTSCHEIDUNG und laufen ueber notify_fallback.send() -> rc-notify.sh ->
Eingang der Zentrale + gebuendelter ntfy-Push ("Session <Name> wartet auf dich (Freigabe)",
hoechstens 1 Push je 15 min, 23-7 Uhr keiner). Am PC geht derselbe Weg per SSH nach netcup.

Ereignisarten (Feld notification_type): permission_prompt -> Freigabe (bei AskUserQuestion/ExitPlanMode
-> Frage), idle_prompt -> Eingabe, elicitation_* -> Frage, auth_success -> ignoriert (Rauschen).
Fehlt das Feld, wird aus dem Meldungstext geschlossen. Jede Art landet ohne Meldungstext in
~/.claude/logs/notification_events.log (Beleg, welche Arten wirklich ankommen).

Schutz vor Spam: Cooldown pro Session (Default 300 s, CLAUDE_DISCORD_NOTIFY_COOLDOWN), identische
Meldung zusaetzlich laenger entprellt. Not-Aus: ~/.claude/flags/discord_notify.off.
Der Hook-Healthcheck (CLAUDE_HEALTH_CHECK=1, session_id "healthcheck") meldet nichts nach aussen.
Best-effort: exit 0 immer, bricht NIE die Session.
"""
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

HOME = Path.home()
OFF = HOME / ".claude" / "flags" / "discord_notify.off"
STATE_DIR = HOME / ".claude" / ".state" / "discord_notify"
EVENTS = HOME / ".claude" / "logs" / "notification_events.log"
COOLDOWN = int(os.environ.get("CLAUDE_DISCORD_NOTIFY_COOLDOWN", "300"))
RAUSCHEN = {"auth_success"}


def art_bestimmen(nt: str, msg: str) -> str:
    """-> 'Freigabe' | 'Frage' | 'Eingabe' | '' (= ignorieren)."""
    if nt in RAUSCHEN or msg.lower().startswith("claude code login successful"):
        return ""
    frage_tool = re.search(r"permission to use (AskUserQuestion|ExitPlanMode)\b", msg)
    if nt == "permission_prompt":
        return "Frage" if frage_tool else "Freigabe"
    if nt.startswith("elicitation"):
        return "Frage"
    if nt == "idle_prompt":
        return "Eingabe"
    if "needs your permission" in msg:
        return "Frage" if frage_tool else "Freigabe"
    return "Eingabe"


def _ereignis_loggen(nt: str, art: str, cwd: str) -> None:
    try:
        EVENTS.parent.mkdir(parents=True, exist_ok=True)
        with open(EVENTS, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{nt or '-'}\t{art or 'ignoriert'}\t{cwd}\n")
    except Exception:
        pass


def main():
    if OFF.exists() or os.environ.get("CLAUDE_HEALTH_CHECK") == "1":
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    try:
        session = str(data.get("session_id") or "nosession")
        if session == "healthcheck":
            sys.exit(0)
        msg = str(data.get("message") or "").strip()
        nt = str(data.get("notification_type") or "")
        cwd = Path(str(data.get("cwd") or "")).name or "?"
        art = art_bestimmen(nt, msg)
        _ereignis_loggen(nt, art, cwd)
        if not art:
            sys.exit(0)

        sig = hashlib.sha256((art + msg).encode("utf-8")).hexdigest()[:16]
        sp = STATE_DIR / (hashlib.sha256(session.encode()).hexdigest()[:16] + ".json")
        now = time.time()
        try:
            prev = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
        age = now - float(prev.get("ts", 0))
        if age < COOLDOWN or (prev.get("sig") == sig and age < COOLDOWN * 4):
            sys.exit(0)
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps({"ts": now, "sig": sig}), encoding="utf-8")

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import notify_fallback
        # Titel "Claude wartet — <Ordner>": die Zentrale macht daraus per Allowlist den Session-Namen.
        # Der Meldungstext bleibt im Eingang (lokal); in den Push kommt nur die Vorlage.
        notify_fallback.send(f"Claude wartet — {cwd}", f"{art}: {msg[:300]}", klasse="ENTSCHEIDUNG", timeout=20)
    except SystemExit:
        raise
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
