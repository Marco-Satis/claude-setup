#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord-AFK-Relay Hook (2026-06-13)
===================================
Bei Stop/Notification eine Nachricht in einen privaten Discord-Kanal posten; beim
Stop blockierend auf der Nutzer Antwort pollen und die Antwort via decision:block ->
reason zurueck in die Session geben (echter Round-Trip / Fernsteuerung wenn AFK).

Aktiviert NUR wenn Flag-File existiert -> sonst sofort exit 0 (null Effekt).
Best-effort: faengt JEDEN Fehler -> exit 0, bricht NIE die Session.

Verifiziert gegen offizielle Doc (code.claude.com/docs/en/hooks):
- Stop-Continue: {"decision":"block","reason":"..."} -> reason geht an Claude.
- Notification: flaches `message`-Feld; kann NICHT zurueck-injizieren (nur Alert).
- timeout pro Hook in settings.json (Default 600s command) -> Poll-Fenster < timeout.
- Transcript = JSONL, Eintraege {"type":...,"message":{"role":...,"content":[...]}}.

ENV (spaeter von der Nutzer gesetzt, Token NIE im Code/Chat):
  CLAUDE_DISCORD_BOT_TOKEN   Bot-Token (Pflicht)            -> User-ENV + KeePass
  CLAUDE_DISCORD_CHANNEL_ID  Ziel-Kanal-ID (Pflicht)
  CLAUDE_DISCORD_USER_ID     nur diese User-ID darf antworten (PFLICHT fuer den
                             Reply-Round-Trip; ohne sie wird NICHT gepollt/injiziert
                             — sonst koennte jeder Nicht-Bot-User die Session steuern)
  CLAUDE_DISCORD_POLL_SECONDS Poll-Fenster (Default 540, < Hook-timeout)

Toggle:  python discord_afk.py on|off|status   (legt/entfernt das Flag-File)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

FLAG = Path.home() / ".claude" / "flags" / "discord_afk.flag"
STATE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "claude-discord-afk"
LOG = STATE_DIR / "relay.log"

TOKEN = os.environ.get("CLAUDE_DISCORD_BOT_TOKEN", "").strip()
CHANNEL = os.environ.get("CLAUDE_DISCORD_CHANNEL_ID", "").strip()
ALLOWED_USER = os.environ.get("CLAUDE_DISCORD_USER_ID", "").strip()
POLL_SECONDS = int(os.environ.get("CLAUDE_DISCORD_POLL_SECONDS", "540"))
POLL_INTERVAL = 5
API = "https://discord.com/api/v10"
MAX_MSG = 1800  # Discord-Limit 2000, Puffer fuer Rahmen-Text


def log(msg: str) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except OSError:
        pass


def _req(method: str, path: str, body: dict | None = None) -> dict | list | None:
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bot {TOKEN}")
    req.add_header("User-Agent", "claude-afk-relay (local, 1.0)")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        log(f"HTTP {e.code} {method} {path}: {e.read()[:200]!r}")
    except Exception as e:  # noqa: BLE001 - best-effort
        log(f"req-fail {method} {path}: {e}")
    return None


def post_message(text: str) -> str | None:
    """Postet Text, gibt Message-ID zurueck (zum Poll-Anker)."""
    res = _req("POST", f"/channels/{CHANNEL}/messages", {"content": text[:1990]})
    if isinstance(res, dict):
        return res.get("id")
    return None


def get_human_reply(after_id: str) -> str | None:
    """Erste Nachricht NACH after_id von einem (erlaubten) Menschen -> Text."""
    res = _req("GET", f"/channels/{CHANNEL}/messages?after={after_id}&limit=20")
    if not isinstance(res, list):
        return None
    # Discord liefert neueste zuerst -> chronologisch von hinten pruefen
    for m in reversed(res):
        author = m.get("author") or {}
        if author.get("bot"):
            continue
        # Fail-closed: ohne gesetzte ALLOWED_USER wird KEINE Antwort akzeptiert
        # (M-08). Sonst koennte jeder Nicht-Bot-User Steuer-Input injizieren.
        if not ALLOWED_USER or str(author.get("id")) != ALLOWED_USER:
            continue
        content = (m.get("content") or "").strip()
        if content:
            return content
    return None


def last_assistant_text(transcript_path: str) -> str:
    """Letzte Assistant-Text-Nachricht aus dem Transcript-JSONL."""
    p = Path(transcript_path)
    if not p.is_file():
        return ""
    found = ""
    try:
        with p.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = rec.get("message") if isinstance(rec, dict) else None
                if not isinstance(msg, dict) or msg.get("role") != "assistant":
                    continue
                content = msg.get("content")
                text = ""
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    parts = [c.get("text", "") for c in content
                             if isinstance(c, dict) and c.get("type") == "text"]
                    text = "\n".join(t for t in parts if t)
                if text.strip():
                    found = text.strip()  # letzte gewinnt
    except OSError:
        return ""
    return found


def _state_path(session_id: str) -> Path:
    h = hashlib.sha256((session_id or "x").encode()).hexdigest()[:16]
    return STATE_DIR / f"state_{h}.json"


def handle_stop(data: dict) -> None:
    text = last_assistant_text(data.get("transcript_path", ""))
    if not text:
        sys.exit(0)
    if not ALLOWED_USER:
        # M-08: Reply-Round-Trip injiziert Discord-Input in die Session. Ohne feste
        # CLAUDE_DISCORD_USER_ID koennte JEDER Nicht-Bot-User im Kanal steuern ->
        # fail-closed: nur informativer Alert, KEIN Poll, normaler Stop.
        log("Stop-Relay: CLAUDE_DISCORD_USER_ID nicht gesetzt -> kein Reply-Round-Trip (fail-closed).")
        cwd_name = Path(data.get("cwd", "")).name or "session"
        post_message(f"\U0001F916 **Claude** — `{cwd_name}` ist fertig. "
                     f"_(AFK-Fernsteuerung aus: CLAUDE_DISCORD_USER_ID nicht gesetzt.)_")
        sys.exit(0)
    session_id = data.get("session_id", "")
    sig = hashlib.sha256(text.encode()).hexdigest()
    sp = _state_path(session_id)
    # Dedup: gleiche Assistant-Nachricht nicht doppelt posten (spurious Stop).
    try:
        if sp.is_file() and json.loads(sp.read_text(encoding="utf-8")).get("sig") == sig:
            sys.exit(0)
    except (OSError, json.JSONDecodeError):
        pass

    cwd_name = Path(data.get("cwd", "")).name or "session"
    header = f"\U0001F916 **Claude** — `{cwd_name}` ist fertig:"
    footer = (f"\n\n_Antworte hier → fließt zurück in die Session. "
              f"Keine Antwort in {POLL_SECONDS // 60} min → Claude stoppt._")
    body = text if len(text) <= MAX_MSG else text[:MAX_MSG] + " …[gekürzt]"
    sent_id = post_message(f"{header}\n>>> {body}{footer}")
    if not sent_id:
        sys.exit(0)  # Discord nicht erreichbar -> normal stoppen
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps({"sig": sig, "ts": time.time()}), encoding="utf-8")
    except OSError:
        pass

    deadline = time.time() + POLL_SECONDS
    while time.time() < deadline:
        reply = get_human_reply(sent_id)
        if reply:
            post_message("✅ Empfangen — Claude macht weiter.")
            log(f"reply relayed ({len(reply)} chars)")
            print(json.dumps({
                "decision": "block",
                "reason": f"[Antwort von der Nutzer via Discord]: {reply}",
            }))
            sys.exit(0)
        time.sleep(POLL_INTERVAL)

    post_message("⏳ Keine Antwort — Claude stoppt.")
    sys.exit(0)  # kein decision -> normaler Stop


def handle_notification(data: dict) -> None:
    ntype = (data.get("notification_type") or "").lower()
    if ntype and ntype not in ("permission_prompt", "idle_prompt", "elicitation_dialog"):
        sys.exit(0)
    msg = (data.get("message") or "Claude wartet auf dich.").strip()
    cwd_name = Path(data.get("cwd", "")).name or "session"
    icon = {"permission_prompt": "\U0001F510", "idle_prompt": "\U0001F4A4",
            "elicitation_dialog": "❓"}.get(ntype, "\U0001F514")
    post_message(f"{icon} **Claude** — `{cwd_name}`: {msg}\n"
                 f"_(Hinweis: Permission/Dialog kann nur am PC beantwortet werden.)_")
    sys.exit(0)


def main() -> None:
    if not FLAG.exists():
        sys.exit(0)
    if not TOKEN or not CHANNEL:
        log("Flag an, aber CLAUDE_DISCORD_BOT_TOKEN/CHANNEL_ID fehlt -> no-op.")
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    event = data.get("hook_event_name", "")
    if event == "Stop":
        handle_stop(data)
    elif event == "Notification":
        handle_notification(data)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 - niemals die Session brechen
        try:
            log(f"FATAL (geschluckt): {e}")
        except Exception:
            pass
        sys.exit(0)
