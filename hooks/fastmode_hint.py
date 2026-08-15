#!/usr/bin/env python
"""UserPromptSubmit-Hook: weist auf Fast Mode (/fast) hin wenn sinnvoll.

der Nutzer 2026-07-13: Fast Mode (Claude Code `/fast`) = gleiches Opus, nur schnellere
Output-Tokens/s. Lohnt bei latenz-sensitiv + OUTPUT-LASTIGEN Tasks (viel Text/Code,
Bulk-Gen, schnelle Iteration). Lohnt NICHT bei Nacht-/Autonom-/Long-Run (Latenz
egal, nur schnellerer Quota-Burn) oder Reasoning-schweren Tasks (Effort schlägt
Speed). Active-Enforcement-Pattern (statt passiver Lyra-Regel).

Best-effort: blockt nie (exit 0), gibt genau ein JSON {"systemMessage"} zurück
oder nichts. Anti-Nag: max 1 Hinweis pro Session-Cooldown.
"""
from __future__ import annotations
import json, re, sys, time
from pathlib import Path

COOLDOWN_S = 1800  # 30 Min: max 1 Hinweis je Session-Fenster

# Output-lastig / Bulk-Gen — der Kern-Trigger (Fast Mode zahlt sich bei viel Output aus)
VOLUME = [
    "generiere", "erzeuge", "erstelle alle", "komplette", "kompletten", "vollständig",
    "vollstaendig", "alle varianten", "mehrere varianten", "bulk", "batch", "massen",
    "liste alle", "für jede", "fuer jede", "boilerplate", "ganzen code", "gesamten code",
    "viele beispiele", "generate all", "write the entire", "full implementation",
]
# Numerische Mengen: "10 varianten", "8 versionen", "12 beispiele", ...
VOLUME_RE = re.compile(
    r"\b([5-9]|\d{2,})\s*(varianten|versionen|beispiele|items|einträge|eintraege|zeilen|dateien|files|components|komponenten)",
    re.IGNORECASE,
)
# Latenz-Signal (verstärkt, aber allein kein Trigger)
LATENCY = ["schnell", "zügig", "zuegig", "sofort", "eilig", "quick", "asap", "iterativ", "iteration", "draft"]

# Suppressoren: hier ist Fast Mode NICHT sinnvoll (Lyra-Regel)
SUPPRESS_LONGRUN = [
    "über nacht", "ueber nacht", "autonom", "im hintergrund", "langlaufend",
    "über stunden", "ueber stunden", "nacht-session", "overnight", "unattended", "wakeup-setup",
]
SUPPRESS_REASONING = [
    "root cause", "architektur", "architecture", "security audit", "sicherheits-audit",
    "beweis", "proof", "tief analysier", "debugge tief",
]


def _session_key(data: dict) -> str:
    sid = data.get("session_id") or ""
    if not sid:
        tp = data.get("transcript_path") or ""
        sid = Path(tp).stem if tp else "nosession"
    return re.sub(r"[^A-Za-z0-9_.-]", "_", sid)[:80] or "nosession"


def _on_cooldown(key: str) -> bool:
    marker = Path(__import__("tempfile").gettempdir()) / f"fastmode_hint_{key}.marker"
    now = time.time()
    try:
        if marker.exists() and (now - marker.stat().st_mtime) < COOLDOWN_S:
            return True
    except OSError:
        return False
    try:
        marker.write_text(str(now), encoding="utf-8")
    except OSError:
        pass
    return False


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    prompt = (data.get("prompt") or "").lower()
    if not prompt:
        sys.exit(0)

    # Suppressoren zuerst — bei Nacht/Autonom/Reasoning gar nicht hinten
    if any(s in prompt for s in SUPPRESS_LONGRUN) or any(s in prompt for s in SUPPRESS_REASONING):
        sys.exit(0)

    has_volume = any(v in prompt for v in VOLUME) or bool(VOLUME_RE.search(prompt))
    if not has_volume:
        sys.exit(0)  # Output-Last ist der Pflicht-Trigger — Latenz allein reicht nicht

    has_latency = any(l in prompt for l in LATENCY)

    key = _session_key(data)
    if _on_cooldown(key):
        sys.exit(0)

    tail = " Iterations-/Latenz-Signal erkannt." if has_latency else ""
    msg = (
        "[fastmode_hint] Task wirkt output-lastig." + tail +
        " → Fast Mode erwägen (`/fast`): identisches Opus, Antwort kommt schneller."
        " NICHT sinnvoll bei Nacht-/Autonom-Läufen oder Reasoning-schweren Tasks"
        " (dort Effort statt Speed). (Hinweis 1×/30min)"
    )
    print(json.dumps({"systemMessage": msg}))
    sys.exit(0)


if __name__ == "__main__":
    main()
