#!/usr/bin/env python
"""SessionStart Hook: merkt sich ob der Memory-Service beim Session-Start erreichbar war.

Teil der Lazy-Reload-Loesung (der Nutzer 2026-05-29): der Memory-Service braucht
manchmal laenger zum Booten als Claude zum Starten (Slow-Start-Race) -> der
Plugin-SessionStart-Hook verpasst dann die Memory-Injection. Dieser Probe
schreibt nur ein Health-Flag pro Session; der UserPromptSubmit-Hook
`memory_lazy_inject.py` laedt Memory NACH (sobald Service up), aber NUR wenn
hier "down" stand (sonst hat das Plugin schon injiziert -> kein Doppel-Inject).

Silent (kein systemMessage). State: ~/.claude/state/memory_start_health.json
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

# Zentrale Base-URL (Netcup-Cutover): ENV MCP_MEMORY_BASE_URL > winreg > localhost-Default.
sys.path.insert(0, str(Path.home() / ".claude" / "scripts"))
try:
    from memory_auth import base_url as _mem_base_url
except Exception:
    def _mem_base_url() -> str:
        return "http://127.0.0.1:8000"

STATE = Path.home() / ".claude" / "state" / "memory_start_health.json"
HEALTH_URL = f"{_mem_base_url()}/api/health"
KEEP = 30

# G2-Down-Alert (Audit 2026-06-03): aggregierte Health-Historie, getrennt von der
# per-sid-Map (die lazy-inject liest) damit deren Struktur/Prune unangetastet bleibt.
META = Path.home() / ".claude" / "state" / "memory_health_meta.json"
CAPTURE_OK = Path.home() / ".claude" / "state" / "last_capture_ok.json"
SESSION_ACTIVE = Path.home() / ".claude" / "state" / "last_session_active.json"
DOWN_ALERT_AFTER = 2        # Service-Starts in Folge down -> warnen
CAPTURE_STALE_DAYS = 2      # kein erfolgreicher Write trotz Aktivitaet -> warnen

# Instinct-Layer (2026-06-04): verdichtete verifizierte Verhaltensregeln, top-N
# als kompakter Block in den SessionStart-Context. Distinkt zur Phase-2.5-
# Memory-Injection (= volle Story); hier nur die 1-Zeiler-Regeln. Read-only.
INSTINCTS = Path.home() / ".claude" / "state" / "instincts.json"
INSTINCTS_RENDER_N = 8


def _render_instincts() -> str:
    """Top-N Instincts nach Confidence als 1-Zeiler-Block (best-effort, leise bei leer)."""
    try:
        if not INSTINCTS.exists():
            return ""
        data = json.loads(INSTINCTS.read_text(encoding="utf-8"))
        items = data.get("instincts", []) if isinstance(data, dict) else []
        items = sorted(items, key=lambda x: (x.get("confidence", 0.0), x.get("hits", 0)),
                       reverse=True)[:INSTINCTS_RENDER_N]
        if not items:
            return ""
        lines = "\n".join("• " + str(it.get("rule", "")) for it in items)
        return "\U0001f9ed INSTINCTS (gelernt, top-%d):\n%s" % (len(items), lines)
    except Exception:
        return ""


def _read_ts(path: Path) -> float:
    try:
        return float(json.loads(path.read_text(encoding="utf-8")).get("ts", 0) or 0)
    except Exception:
        return 0.0


def is_up(attempts: int = 3, gap: float = 1.0) -> bool:
    """Health-Check mit Retry-Fenster gegen den Slow-Start-Race.

    Der Memory-Service bootet manchmal langsamer als Claude startet; der
    Plugin-Client retried selbst. Ein Single-Shot-Probe wuerde den
    noch-bootenden Service faelschlich als 'down' werten -> false G2-Alert
    (Bug 2026-06-03). Bei laufendem Service trifft der 1. Versuch sofort
    (~<100ms); die Wartezeit faellt NUR an wenn der Service wirklich nicht
    antwortet.

    Worst-Case gekappt (Audit 2026-06-04): 3x1.0s-timeout + 2x1.0s-gap = ~5s
    statt vorher ~10.5s — blockte sonst den SessionStart bei down-Service.
    Sicherheitsnetz: meldet der Probe faelschlich 'down', laedt
    memory_lazy_inject.py die Memories beim naechsten Turn nach (kein
    permanenter Verlust durch die kuerzere Wartezeit).
    """
    for i in range(attempts):
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=1.0) as r:
                d = json.loads(r.read().decode("utf-8", errors="replace"))
                if str(d.get("status", "")).lower() in ("healthy", "ok", "up"):
                    return True
        except Exception:
            pass
        if i < attempts - 1:
            time.sleep(gap)
    return False


def main() -> None:
    sid = "unknown"
    try:
        data = json.load(sys.stdin)
        sid = data.get("session_id", "unknown")
    except Exception:
        pass

    status = "up" if is_up() else "down"

    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        try:
            m = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
        except Exception:
            m = {}  # korruptes/leeres State-File -> frisch beginnen (M-04 Fix)
        m[sid] = status
        # Prune: letzte KEEP Eintraege behalten (Insertion-Order in py3.7+)
        if len(m) > KEEP:
            for k in list(m.keys())[: len(m) - KEEP]:
                m.pop(k, None)
        tmp = STATE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(m, indent=2), encoding="utf-8")
        os.replace(tmp, STATE)
    except Exception:
        pass  # best-effort, darf SessionStart nie blockieren

    # --- G2 Down-Alert (Audit 2026-06-03) ---
    alerts: list[str] = []
    try:
        now = time.time()
        try:
            meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
        except Exception:
            meta = {}
        if status == "up":
            meta["last_up_ts"] = now
            meta["consecutive_down"] = 0
        else:
            meta["consecutive_down"] = int(meta.get("consecutive_down", 0) or 0) + 1
        try:
            META.parent.mkdir(parents=True, exist_ok=True)
            tmpm = META.with_suffix(".json.tmp")
            tmpm.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            os.replace(tmpm, META)
        except Exception:
            pass

        cdown = int(meta.get("consecutive_down", 0) or 0)
        if status == "down" and cdown >= DOWN_ALERT_AFTER:
            last_up = float(meta.get("last_up_ts", 0) or 0)
            since = f"~{int((now - last_up) / 3600)}h" if last_up else "unbekannt lang"
            alerts.append(
                f"[MEMORY-DOWN] Service seit {cdown} Starts down (letzter up: {since}) — "
                f"Auto-Capture + Injection inaktiv. Start: scripts/start_memory_server.bat")
        elif status == "up":
            cap = _read_ts(CAPTURE_OK)
            act = _read_ts(SESSION_ACTIVE)
            stale = CAPTURE_STALE_DAYS * 86400
            if act and (now - act) < stale and cap and (now - cap) > stale:
                days = max(1, int((now - cap) / 86400))
                alerts.append(
                    f"[MEMORY-CAPTURE-STALE] Service up, aber seit ~{days}d kein erfolgreicher "
                    f"Memory-Write trotz aktiver Sessions — Writes failen evtl. still "
                    f"(db-lock/disk). Pruefe lessons/memory_write_failures.jsonl.")
    except Exception:
        pass

    parts: list[str] = list(alerts)
    instinct_block = _render_instincts()
    if instinct_block:
        parts.append(instinct_block)
    if parts:
        try:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "\n".join(parts)}}))
        except Exception:
            pass


if __name__ == "__main__":
    main()
