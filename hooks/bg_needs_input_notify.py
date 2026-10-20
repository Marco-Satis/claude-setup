#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notification-Hook: Discord-Meldung, wenn eine Hintergrund-Session auf Eingabe wartet.

Punkt A1.3 (TikTok-Auswertung 30.09.2026). Verdrahtet in settings.json unter
hooks.Notification mit matcher "agent_needs_input".

Belegte Semantik (CLI 2.1.285, Binary + code.claude.com/docs/en/agent-view):
  - `agent_needs_input` feuert der Prozess, der die Agent View (`claude agents`)
    zeigt, sobald eine lokale Hintergrund-Session in den Zustand "blocked" wechselt.
    Text: "<label> needs your input" bzw. "<label> needs your input: <needs>".
    Doku: "While agent view is open ..." -> ohne offene Agent View kein Event.
  - `session_id`/`cwd` im Event gehoeren dem Agent-View-Prozess, NICHT der
    Hintergrund-Session (qO(v$(), ...) im Binary). Die Hintergrund-Session steckt
    nur im Label der Nachricht. Deshalb drosselt dieses Skript je
    (session_id, Label) statt nur je session_id -- sonst verschluckt die erste
    Meldung alle anderen Sessions fuer 10 Minuten.
  - Derselbe Typ kommt selten auch aus Vordergrund-Sessions (Dialoge wie
    "Auto mode has a classifier billing notice to acknowledge"). Die brauchen
    ebenfalls Eingabe und laufen mit derselben Drosselung durch.

Abgrenzung: discord_notify.py deckt alle uebrigen Notification-Typen ab
(permission_prompt usw., auch aus Hintergrund-Sessions selbst). Sein matcher
schliesst agent_needs_input aus, damit nichts doppelt kommt.

Schalter:
  ~/.claude/flags/bg_needs_input_notify.off   nur diesen Hook aus
  ~/.claude/flags/discord_notify.off          alle Claude-Discord-Meldungen aus
  BG_NEEDS_INPUT_COOLDOWN   Sekunden je (Session, Label), Default 600
  BG_NEEDS_INPUT_DRY_RUN=1  nichts senden, Meldung als JSON nach stderr
  BG_NEEDS_INPUT_STATE_DIR  State-Verzeichnis (Default ~/.claude/state)

Best-effort: exit 0 immer, bricht nie die Session.
"""
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

TYPE = "agent_needs_input"
HOME = Path.home()
FLAGS = HOME / ".claude" / "flags"
NOTIFY = HOME / ".claude" / "rc-notify.sh"
STATE_DIR = Path(os.environ.get("BG_NEEDS_INPUT_STATE_DIR") or (HOME / ".claude" / "state"))
STATE = STATE_DIR / "bg_needs_input_notify.json"
KEEP_S = 86400  # alte Drossel-Eintraege nach einem Tag verwerfen

LABEL_RE = re.compile(r"^(?P<label>.+?) needs your input(?::\s*(?P<needs>.*))?$", re.S)

# Grobe Schwaerzung: "needs" kann Befehlszusammenfassungen enthalten
# (z. B. "approve Bash: ..."). Muster wie secret_leak_detector.py.
REDACT = [
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}"), "[REDACTED]"),
    (re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"), "[REDACTED]"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "[REDACTED]"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "[REDACTED]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED]"),
    (re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}"), "[REDACTED]"),
    (re.compile(r"AIza[0-9A-Za-z_-]{30,}"), "[REDACTED]"),
    (re.compile(r"[MNO][A-Za-z\d_-]{23,}\.[\w-]{6}\.[\w-]{27,}"), "[REDACTED]"),
    (re.compile(r"https?://\S*discord(?:app)?\.com/api/webhooks/\S+", re.I), "[REDACTED]"),
    (re.compile(r"(?i)\bbearer\s+\S+"), "Bearer [REDACTED]"),
    (re.compile(r"(?i)\b(\w*(?:token|secret|passw(?:or)?d|api[_-]?key|authorization))(\s*[:=]\s*)\S+"),
     r"\1\2[REDACTED]"),
]


def redact(text: str) -> str:
    for pat, rep in REDACT:
        text = pat.sub(rep, text)
    return text


def off() -> bool:
    return (FLAGS / "bg_needs_input_notify.off").exists() or (FLAGS / "discord_notify.off").exists()


def load_state() -> dict:
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, STATE)


def throttled(key: str, now: float, cooldown: float) -> bool:
    """True = innerhalb der Sperrfrist, nicht senden. Sonst Zeitstempel setzen."""
    lock = None
    try:
        import fcntl  # nur Linux; auf Windows ohne Lock weiter
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        lock = open(STATE_DIR / "bg_needs_input_notify.lock", "w")
        fcntl.flock(lock, fcntl.LOCK_EX)
    except Exception:
        lock = None
    try:
        state = load_state()
        state = {k: v for k, v in state.items()
                 if isinstance(v, (int, float)) and now - v < KEEP_S}
        if now - float(state.get(key, 0)) < cooldown:
            return True
        state[key] = now
        save_state(state)
        return False
    finally:
        if lock is not None:
            try:
                lock.close()
            except Exception:
                pass


def main() -> None:
    if off():
        return
    try:
        raw = sys.stdin.buffer.read()
        data = json.loads(raw.decode("utf-8", errors="replace") or "{}")
    except Exception:
        return
    if not isinstance(data, dict) or data.get("notification_type") != TYPE:
        return

    msg = str(data.get("message") or "").strip()
    session = str(data.get("session_id") or "nosession")
    cwd = Path(str(data.get("cwd") or "")).name or "?"
    m = LABEL_RE.match(msg)
    label = (m.group("label").strip() if m else "") or cwd
    needs = (m.group("needs") or "").strip() if m else msg

    try:
        cooldown = float(os.environ.get("BG_NEEDS_INPUT_COOLDOWN", "600"))
    except ValueError:
        cooldown = 600.0
    key = hashlib.sha256(f"{session}\0{label}".encode("utf-8")).hexdigest()[:16]
    if throttled(key, time.time(), cooldown):
        return

    host = socket.gethostname() or "?"
    kind = "Claude-Hintergrund-Session" if m else "Claude-Session"
    title = redact(f"{kind} wartet — {label}")[:200]
    lines = [redact(needs)[:300] if needs else "braucht deine Eingabe"]
    lines.append(f"Gemeldet von: {cwd} auf {host} · öffnen mit `claude agents`")
    text = "\n".join(lines)

    if os.environ.get("BG_NEEDS_INPUT_DRY_RUN") == "1":
        sys.stderr.write(json.dumps({"title": title, "text": text}, ensure_ascii=False) + "\n")
        return
    if not NOTIFY.exists():
        return
    subprocess.run([str(NOTIFY), title, text], timeout=20,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
