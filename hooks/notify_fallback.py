#!/usr/bin/env python3
"""Gemeinsamer Discord-Meldeweg fuer Hooks auf PC und netcup (der Nutzer-Entscheid 2026-10-22, Weg A).

Reihenfolge (seit G252, 14.11.2026):
  1. ~/.claude/rc-notify.sh vorhanden (netcup) -> direkt aufrufen.
  2. Windows -> per SSH an netcup (Eingang der Zentrale).
  3. Nur wenn SSH scheitert: CLAUDE_DISCORD_BOT_TOKEN + CLAUDE_DISCORD_CHANNEL_ID gesetzt -> Discord-API.
  Bis G252 stand Discord vor SSH. SSH-Aufruf: `ssh netcup-marco ~/.claude/rc-notify.sh …`
     (Webhook bleibt auf netcup, am PC liegt kein Secret).

Best-effort: wirft nie. True = Weg ausgeloest (SSH-Zweig: nur bei Exit 0).
`timeout` kuerzen, wenn der aufrufende Hook ein knappes Limit hat.
Not-Aus: ~/.claude/flags/discord_notify.off

G252 (14.11.2026): optionale `klasse` (ALARM, ENTSCHEIDUNG, INFO, ...) geht als 3. Argument an rc-notify.sh,
auch per SSH vom PC. rc-notify.sh meldet seitdem an den Eingang der Zentrale und per ntfy, nicht mehr an Discord.
"""
import json
import os
import shlex
import subprocess
from pathlib import Path

HOME = Path.home()
NOTIFY = HOME / ".claude" / "rc-notify.sh"
SSH_HOST = os.environ.get("CLAUDE_NOTIFY_SSH_HOST", "netcup-marco")


def snapshot_senden(snap: dict, timeout: float = 20) -> bool:
    """Session-Snapshot (Stop-Hook session_snapshot.py, 15.11.2026) an den Eingang der Zentrale.
    netcup: direkt `zentrale_eingang.py snapshot`. PC: per SSH an netcup, im Hintergrund (blockiert den Zug nicht),
    JSON ueber stdin. Not-Aus wie send(). True = Weg ausgeloest."""
    try:
        if (HOME / ".claude" / "flags" / "discord_notify.off").exists():
            return False
        payload = json.dumps(snap, ensure_ascii=False).encode("utf-8")[:8000]
        lokal = HOME / ".claude" / "scripts" / "zentrale_eingang.py"
        if os.name != "nt" and NOTIFY.exists() and lokal.exists():
            cmd = ["python3", "-I", str(lokal), "snapshot"]
        else:
            cmd = ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={min(6, int(timeout))}", SSH_HOST,
                   "python3 -I ~/.claude/scripts/zentrale_eingang.py snapshot"]
        kw = {"stdin": subprocess.PIPE, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
                subprocess, "DETACHED_PROCESS", 0)
        else:
            kw["start_new_session"] = True
        proc = subprocess.Popen(cmd, **kw)
        proc.stdin.write(payload)
        proc.stdin.close()
        return True
    except Exception:
        return False


def send(title: str, text: str, timeout: float = 20, klasse: str = "") -> bool:
    try:
        if (HOME / ".claude" / "flags" / "discord_notify.off").exists():
            return False
        title, text = str(title)[:200], str(text)[:1700]
        klasse = klasse if klasse in ("ALARM", "ENTSCHEIDUNG", "INFO", "RAUSCHEN") else ""
        if NOTIFY.exists():
            subprocess.run([str(NOTIFY), title, text] + ([klasse] if klasse else []), timeout=timeout, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        if os.name == "nt":
            # G252: zuerst per SSH an den Eingang der Zentrale (netcup); Discord-Bot nur noch als Rueckfall.
            remote = "~/.claude/rc-notify.sh " + shlex.quote(title) + " " + shlex.quote(text)
            if klasse:
                remote += " " + klasse
            proc = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={min(6, int(timeout))}",
                                   SSH_HOST, remote],
                                  timeout=timeout, check=False,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if proc.returncode == 0:
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
    except Exception:
        pass
    return False
