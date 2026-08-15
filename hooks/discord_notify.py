#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Notification Hook: Claude-Benachrichtigungen in den kanonischen Discord-Kanal.

Natives CC-Event `Notification` feuert bei Permission-Anfragen und wenn Claude
laenger auf Eingabe wartet. Zweck: Server-Sessions die auf eine Freigabe warten
sollen nicht stundenlang stillstehen (Lehre aus dem RC-Ausfall 2026-07-23).

Kanal + Regel: ~/.claude/rules/discord-notify-channel.md — ein Webhook fuer alle
Info-Benachrichtigungen, ausser TikTok-Pipeline. Versand ueber rc-notify.sh.

Schutz vor Spam:
  - Cooldown pro Session (Default 300s, CLAUDE_DISCORD_NOTIFY_COOLDOWN)
  - identische Nachricht wird innerhalb des Cooldowns nicht wiederholt
  - Kill-Switch: ~/.claude/flags/discord_notify.off

Best-effort: exit 0 immer, bricht NIE die Session.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
OFF = HOME / ".claude" / "flags" / "discord_notify.off"
STATE_DIR = HOME / ".claude" / ".state" / "discord_notify"
NOTIFY = HOME / ".claude" / "rc-notify.sh"
COOLDOWN = int(os.environ.get("CLAUDE_DISCORD_NOTIFY_COOLDOWN", "300"))


def main():
    if OFF.exists():
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    try:
        msg = str(data.get("message") or "").strip()
        if not msg:
            sys.exit(0)
        session = str(data.get("session_id") or "nosession")
        cwd = Path(str(data.get("cwd") or "")).name or "?"

        sig = hashlib.sha256(msg.encode("utf-8")).hexdigest()[:16]
        sp = STATE_DIR / (hashlib.sha256(session.encode()).hexdigest()[:16] + ".json")
        now = time.time()
        try:
            prev = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
        # Cooldown pro Session; identische Nachricht zusaetzlich dauerhaft entprellt.
        age = now - float(prev.get("ts", 0))
        if age < COOLDOWN or (prev.get("sig") == sig and age < COOLDOWN * 4):
            sys.exit(0)

        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps({"ts": now, "sig": sig}), encoding="utf-8")

        subprocess.run(
            [str(NOTIFY), f"Claude wartet — {cwd}", msg[:1500]],
            timeout=20, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
