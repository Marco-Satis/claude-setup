#!/usr/bin/env python3
"""Gemeinsamer Discord-Meldeweg fuer Hooks auf PC und netcup (der Nutzer-Entscheid 2026-10-22, Weg A).

Reihenfolge:
  1. ~/.claude/rc-notify.sh vorhanden (netcup) -> direkt aufrufen.
  2. CLAUDE_DISCORD_BOT_TOKEN + CLAUDE_DISCORD_CHANNEL_ID gesetzt -> Discord-API.
  3. Windows ohne beides -> per SSH an netcup: `ssh netcup-marco ~/.claude/rc-notify.sh …`
     (Webhook bleibt auf netcup, am PC liegt kein Secret).

Best-effort: wirft nie. True = Weg ausgeloest (SSH-Zweig: nur bei Exit 0).
`timeout` kuerzen, wenn der aufrufende Hook ein knappes Limit hat.
Not-Aus: ~/.claude/flags/discord_notify.off
"""
import json
import os
import shlex
import subprocess
from pathlib import Path

HOME = Path.home()
NOTIFY = HOME / ".claude" / "rc-notify.sh"
SSH_HOST = os.environ.get("CLAUDE_NOTIFY_SSH_HOST", "netcup-marco")


def send(title: str, text: str, timeout: float = 20) -> bool:
    try:
        if (HOME / ".claude" / "flags" / "discord_notify.off").exists():
            return False
        title, text = str(title)[:200], str(text)[:1700]
        if NOTIFY.exists():
            subprocess.run([str(NOTIFY), title, text], timeout=timeout, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        token = os.environ.get("CLAUDE_DISCORD_BOT_TOKEN", "").strip()
        channel = os.environ.get("CLAUDE_DISCORD_CHANNEL_ID", "").strip()
        if token and channel:
            import urllib.request
            req = urllib.request.Request(
                f"https://discord.com/api/v10/channels/{channel}/messages",
                data=json.dumps({"content": f"**{title}**\n{text}"[:1900]}).encode("utf-8"),
                method="POST",
                headers={"Authorization": f"Bot {token}", "Content-Type": "application/json",
                         "User-Agent": "claude-notify-fallback/1.0"})
            urllib.request.urlopen(req, timeout=min(8, timeout)).read()
            return True
        if os.name == "nt":
            remote = "~/.claude/rc-notify.sh " + shlex.quote(title) + " " + shlex.quote(text)
            proc = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={min(6, int(timeout))}",
                                   SSH_HOST, remote],
                                  timeout=timeout, check=False,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return proc.returncode == 0
    except Exception:
        pass
    return False
