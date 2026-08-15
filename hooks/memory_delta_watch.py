#!/usr/bin/env python
"""UserPromptSubmit Hook: erkennt Setup-Aenderungen anderer Sessions mid-session.

der Nutzer-Wunsch 2026-07-21: Claude soll aktiv mitbekommen, wenn andere Sessions
das Setup aendern (Skills/Hooks/Agents/Server/Config), statt es erst beim
naechsten SessionStart zu sehen.

Mechanik: Sessions, die Setup aendern, speichern eine mcp-Memory mit Tag
`setup-change` (Konvention in globaler CLAUDE.md). Dieser Hook pollt
gedrosselt (max. alle CHECK_INTERVAL_S) per /api/search/by-tag nach solchen
Memories und injiziert neue (created_at > letzter Check dieser Session) als
kompakten Digest.

Baseline = erster Prompt der Session (kein Historie-Dump; Vergangenheit deckt
der SessionStart-Inject des mcp-memory-Plugins ab). Fail-silent: Service down /
Timeout / Parse-Fehler => exit 0 ohne Output, naechster Check nach Intervall.

State: ~/.claude/state/memory_delta_watch.json (session_id -> last_check_iso)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "scripts"))
try:
    from memory_auth import auth_headers as _auth, base_url as _base
except Exception:
    def _auth() -> dict:
        return {}
    def _base() -> str:
        return "http://127.0.0.1:8000"

STATE = Path.home() / ".claude" / "state" / "memory_delta_watch.json"
BY_TAG_URL = f"{_base()}/api/search/by-tag"
WATCH_TAGS = ["setup-change"]
CHECK_INTERVAL_S = 600   # max. 1 Netz-Call pro 10 min pro Session
MAX_SHOW = 5
KEEP = 30                # State-Eintraege (Sessions) cappen


def _load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        if len(state) > KEEP:
            for k in list(state.keys())[: len(state) - KEEP]:
                state.pop(k, None)
        STATE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, STATE)
    except Exception:
        pass


def _parse_ts(v):
    # Service liefert created_at als Unix-Float, created_at_iso als ISO-String
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(v, tz=timezone.utc)
        except Exception:
            return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:
        return None


def _fetch_setup_changes() -> list[dict]:
    payload = json.dumps({"tags": WATCH_TAGS}).encode()
    req = urllib.request.Request(
        BY_TAG_URL, data=payload,
        headers={"Content-Type": "application/json", **_auth()}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=3) as r:
        d = json.loads(r.read().decode("utf-8", errors="replace"))
    # Response-Shape defensiv: {"memories":[...]} oder {"results":[{"memory":{...}}]}
    mems = d.get("memories")
    if mems is None:
        mems = [it.get("memory") or it for it in d.get("results", [])]
    return [m for m in mems if isinstance(m, dict)]


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    sid = data.get("session_id", "unknown")

    now = datetime.now(timezone.utc)
    state = _load_state()
    entry = state.get(sid)

    if entry is None:
        # Baseline: ab jetzt beobachten, kein Historie-Dump
        state[sid] = now.isoformat()
        _save_state(state)
        sys.exit(0)

    last_check = _parse_ts(entry)
    if last_check is None:
        state[sid] = now.isoformat()
        _save_state(state)
        sys.exit(0)

    if (now - last_check).total_seconds() < CHECK_INTERVAL_S:
        sys.exit(0)

    try:
        mems = _fetch_setup_changes()
    except Exception:
        sys.exit(0)  # Service down/Timeout: kein State-Update, naechster Versuch nach Intervall

    fresh = []
    for m in mems:
        ts = _parse_ts(m.get("created_at_iso") or m.get("created_at") or "")
        if ts is not None and ts > last_check:
            fresh.append((ts, (m.get("content") or "").strip().replace("\n", " ")))

    state[sid] = now.isoformat()
    _save_state(state)

    if not fresh:
        sys.exit(0)

    fresh.sort(key=lambda t: t[0], reverse=True)
    lines = [
        f"[SETUP-DELTA] {len(fresh)} neue setup-change-Memory(s) seit letztem Check "
        f"(andere Sessions haben das Setup geaendert — beruecksichtigen!):"
    ]
    lines += [f"  - {c[:200]}" for _, c in fresh[:MAX_SHOW]]
    if len(fresh) > MAX_SHOW:
        lines.append(f"  … +{len(fresh) - MAX_SHOW} weitere (memory_search tags=setup-change)")
    print(json.dumps({"systemMessage": "\n".join(lines)}))


if __name__ == "__main__":
    main()
