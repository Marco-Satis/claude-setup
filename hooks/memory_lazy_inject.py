#!/usr/bin/env python
"""UserPromptSubmit Hook: laedt Memory-Kontext NACH wenn SessionStart ihn verpasst hat.

Slow-Start-Fix (der Nutzer 2026-05-29): wenn der Memory-Service beim SessionStart noch
am Booten war (memory_start_probe.py schrieb "down"), injiziert dieser Hook beim
ersten Turn — sobald der Service erreichbar ist — relevante Memories als
systemMessage. Laeuft EINMAL pro Session (Flag), nur bei Start="down" (sonst hat
der Plugin-SessionStart schon injiziert -> kein Doppel-Inject). Bei Service-noch-
down: kein Flag -> naechster Turn versucht erneut, bis der Service oben ist.

State: ~/.claude/state/memory_inject_done.json (session_id -> iso_ts)
       ~/.claude/state/memory_start_health.json (von memory_start_probe.py)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DONE = Path.home() / ".claude" / "state" / "memory_inject_done.json"
START_HEALTH = Path.home() / ".claude" / "state" / "memory_start_health.json"
RETRY = Path.home() / ".claude" / "state" / "memory_inject_retry.json"
HEALTH_URL = "http://127.0.0.1:8000/api/health"
SEARCH_URL = "http://127.0.0.1:8000/api/search"
N_RESULTS = 5
KEEP = 30
MAX_DOWN_RETRIES = 6   # nach N down-Prompts aufgeben (sonst 1.5s-Tax pro Prompt endlos)


def _load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}


def _mark_done(sid: str) -> None:
    try:
        DONE.parent.mkdir(parents=True, exist_ok=True)
        m = _load(DONE)
        m[sid] = datetime.now(timezone.utc).isoformat()
        if len(m) > KEEP:
            for k in list(m.keys())[: len(m) - KEEP]:
                m.pop(k, None)
        tmp = DONE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(m, indent=2), encoding="utf-8")
        os.replace(tmp, DONE)
    except Exception:
        pass


def _service_up() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=1.5) as r:
            d = json.loads(r.read().decode("utf-8", errors="replace"))
            return str(d.get("status", "")).lower() in ("healthy", "ok", "up")
    except Exception:
        return False


# Stufe-2 Memory-Auth + zentrale Base-URL (Netcup-Cutover). X-API-Key wenn MCP_API_KEY
# gesetzt, sonst {} (anonym). base_url: ENV MCP_MEMORY_BASE_URL > winreg > localhost-Default.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path.home() / ".claude" / "scripts"))
try:
    from memory_auth import auth_headers as _mem_auth_headers, base_url as _mem_base_url
except Exception:
    def _mem_auth_headers() -> dict:
        return {}
    def _mem_base_url() -> str:
        return "http://127.0.0.1:8000"

# Override der Default-Konstanten (oben) auf die zentrale Base-URL.
HEALTH_URL = f"{_mem_base_url()}/api/health"
SEARCH_URL = f"{_mem_base_url()}/api/search"


# Recall-Entrauschung (der Nutzer 2026-07-15): auto-capture Session-Delta-Stubs
# (1 pro Turn, tausende, Tags auto-captured/session-stand, Content "# Turn-Delta")
# sind point-in-time korrekt, aber beim Auto-Inject fuer "recent work decisions
# architecture" meist Noise -> rausfiltern. Achse = Tag, nicht Qualitaet; Store
# bleibt unangetastet (nur der injizierte Kontext wird entrauscht). Ueberfetchen,
# dann auf N_RESULTS gefilterte kuerzen. Empirie: ~36% Noise in Top-5 (Probe).
_NOISE_TAGS = {"auto-captured", "session-stand"}
FETCH_RESULTS = 15


def _is_noise(mem: dict) -> bool:
    tags = mem.get("tags") or []
    if any(t in _NOISE_TAGS for t in tags):
        return True
    return (mem.get("content") or "").lstrip().startswith("# Turn-Delta")


def _search(query: str) -> list[str]:
    try:
        payload = json.dumps({"query": query, "n_results": FETCH_RESULTS}).encode()
        req = urllib.request.Request(
            SEARCH_URL, data=payload,
            headers={"Content-Type": "application/json", **_mem_auth_headers()}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.loads(r.read().decode("utf-8", errors="replace"))
        out = []
        for item in d.get("results", []):
            mem = item.get("memory") or {}
            if _is_noise(mem):
                continue
            content = (mem.get("content") or "").strip().replace("\n", " ")
            if content:
                out.append(content[:140])
            if len(out) >= N_RESULTS:
                break
        return out
    except Exception:
        return []


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    sid = data.get("session_id", "unknown")
    cwd = data.get("cwd") or os.getcwd()
    project = Path(cwd).name if cwd else "unknown"

    # Einmal pro Session
    if sid in _load(DONE):
        sys.exit(0)

    start = _load(START_HEALTH).get(sid)
    # "up": Plugin-SessionStart hat injiziert -> kein Doppel-Inject, fertig markieren.
    if start == "up":
        _mark_done(sid)
        sys.exit(0)
    # None (Probe lief nicht / crashte): Health unbekannt -> KEIN Flag setzen, naechster
    # Turn versucht erneut (M-02: vermeidet permanentes Deaktivieren bei Probe-Glitch).
    if start is None:
        sys.exit(0)

    # Start war "down" -> nachladen sobald Service up
    if not _service_up():
        # Bounded retry: nicht jeden Prompt unbegrenzt ~1.5s zahlen wenn der
        # Service dauerhaft down bleibt. Nach MAX_DOWN_RETRIES aufgeben (mark_done)
        # -> Memory wird diese Session nicht nachgeladen (Plugin/naechste Session
        # deckt ab), aber der Per-Prompt-Stall hoert auf.
        rc = _load(RETRY)
        n = int(rc.get(sid, 0) or 0) + 1
        if n >= MAX_DOWN_RETRIES:
            _mark_done(sid)
            sys.exit(0)
        rc[sid] = n
        if len(rc) > KEEP:
            for k in list(rc.keys())[: len(rc) - KEEP]:
                rc.pop(k, None)
        try:
            RETRY.parent.mkdir(parents=True, exist_ok=True)
            tmp = RETRY.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(rc, indent=2), encoding="utf-8")
            os.replace(tmp, RETRY)
        except Exception:
            pass
        sys.exit(0)  # noch nicht bereit -> KEIN done-Flag, naechster Turn versucht erneut

    memories = _search(f"{project} recent work decisions architecture")
    if not memories:
        # Service up aber nichts gefunden -> trotzdem als erledigt markieren
        _mark_done(sid)
        sys.exit(0)

    lines = [
        f"[MEMORY-NACHGELADEN] Service war beim SessionStart noch am Booten (Slow-Start) — "
        f"{len(memories)} relevante Memories fuer '{project}' jetzt nachgeladen:"
    ]
    lines += [f"  - {m}" for m in memories]
    print(json.dumps({"systemMessage": "\n".join(lines)}))
    _mark_done(sid)


if __name__ == "__main__":
    main()
