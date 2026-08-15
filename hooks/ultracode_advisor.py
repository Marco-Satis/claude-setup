#!/usr/bin/env python
"""UserPromptSubmit-Hook: erinnert an ultracode/Multi-Agent-Schwarm wenn ein Task
davon profitieren wuerde — startet aber NIE selbst (gated bleibt gated).

der Nutzer 2026-06-05: ultracode (= xhigh + stehende Workflow-Permission) ist gegated,
damit der teure Agenten-Schwarm nicht ungefragt feuert. Kehrseite: der Nutzer *vergisst*
ihn bei genau den Tasks wo er am meisten brächte (Full-Audit, Migration ueber viele
Files, N-Varianten-Vergleich, Multi-Projekt-Sweep). Active-Enforcement-Doktrin:
passive Regel -> vergessen, aktiver Hook -> injiziert verlaesslich. Dieser Hook
scannt den Prompt auf Fan-out-Signale (Breite x Unabhaengigkeit) und injiziert eine
systemMessage-Erinnerung. Entscheidung bleibt bei der Nutzer (Keyword "ultracode" tippen).

Mode: BALANCED (der Nutzer-Wahl 2026-06-05) — starke + mittlere Signale, Cooldown 15min.
Toggle aus: Datei ~/.claude/flags/ultracode_advisor_off.flag anlegen.

Best-effort: blockt NIE (exit 0), gibt genau ein JSON {"systemMessage"} oder nichts.
Stdin (UserPromptSubmit): {session_id, transcript_path, cwd, prompt}.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

# Windows-cp1252-stdout-Guard (Non-ASCII in systemMessage).
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

STATE = Path.home() / ".claude" / "state" / "ultracode_advisor.json"
OFF_FLAG = Path.home() / ".claude" / "flags" / "ultracode_advisor_off.flag"

# --- Mode-Tuning (BALANCED) --------------------------------------------------
THRESHOLD = 2      # feuert ab Score >= 2 (mittel+). Konservativ=3, Eager=1.
COOLDOWN_S = 900   # 15 min zwischen zwei Nudges. Konservativ=1800, Eager=300.
MIN_WORDS = 4      # zu kurze Prompts ignorieren (ausser starkes Signal).

# Schon opted-in / orchestriert -> kein Nudge.
OPTED_IN = re.compile(r"\b(ultracode|workflow|fan[\s-]?out|schwarm|orchestr|subagent|parallel\s+agent)", re.I)

# STARKE Signale (Score 3): klare Breite + Unabhaengigkeit.
STRONG = [
    (r"\bfull[\s-]?audit\b|gesamt\w*\s+(audit|review)|komplett\w*\s+(audit|review|refactor)", "Full-Audit-Scope"),
    (r"\b(alle|jede[nrs]?|saemtliche|across\s+all)\s+\w*\s*(files?|dateien|module?n?|cogs?|skills?|hooks?|endpoints?|tests?|projekte?n?|tabellen?|routes?)", "alle Files/Module-Scope"),
    (r"\b(in\s+allen|ueber\s+alle|across\s+all|ueberall)\b", "über-alle-Scope"),
    (r"\bmigr(ier|ate|ation)\w*\b", "Migration"),
    (r"\bvergleich\w*\s+(?:\d+|mehrere|verschiedene|\w+\s+(?:ansaetze|varianten|optionen|approaches))", "N-Varianten-Vergleich"),
    (r"\b(audit|review|durchforste|durchleuchte)\s+(alles|das\s+ganze|die\s+ganze)\b", "audit-alles"),
    (r"\bdeep[\s-]?research\b|recherchiere\w*\s+(tief|umfassend|mehrere|viele)", "tiefe Multi-Quellen-Recherche"),
    (r"\b(alle|beide|mehrere)\s+projekte?n?\b", "Multi-Projekt"),
]

# MITTLERE Signale (Score 2): Breite angedeutet, weniger eindeutig.
MEDIUM = [
    (r"\b(audit|auditier\w*|review\w*|refactor\w*)\b", "Audit/Review/Refactor"),
    (r"\b(durchgehen|durcharbeiten|abarbeiten)\b.*\b(alle|alles|liste|punkte|findings)\b", "Liste-durchgehen"),
    (r"\bstueck\s+f[uü]r\s+stueck\b|one\s+by\s+one|nacheinander", "sequentielle Liste"),
    (r"\bmehrere?\s+\w+", "mehrere-Einheiten"),
    (r"\b\d{2,}\b.*\b(files?|dateien|module?n?|punkte|items?|varianten|quellen|tests?)", "zweistellige Stückzahl"),
    (r"\.py\b.*\.py\b|\ballen?\s+\.\w+-?(files?|dateien)?", "Multi-File"),
    (r"\b(alle|alles)\b", "alle-Scope (schwach)"),
]


def score_prompt(text: str) -> tuple[int, str]:
    """Hoechstes getroffenes Signal bestimmt Score + Grund."""
    for pat, label in STRONG:
        if re.search(pat, text, re.I):
            return 3, label
    for pat, label in MEDIUM:
        if re.search(pat, text, re.I):
            return 2, label
    return 0, ""


def main() -> None:
    if OFF_FLAG.exists():
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        sys.exit(0)

    # Schon opted-in / orchestriert -> nichts tun.
    if OPTED_IN.search(prompt):
        sys.exit(0)

    sc, reason = score_prompt(prompt)
    if sc < THRESHOLD:
        sys.exit(0)

    # Sehr kurze Prompts nur bei starkem Signal.
    if len(prompt.split()) < MIN_WORDS and sc < 3:
        sys.exit(0)

    # Cooldown: seit letztem Nudge genug Zeit?
    now = time.time()
    last = 0.0
    try:
        if STATE.exists():
            last = float(json.loads(STATE.read_text(encoding="utf-8")).get("last_nudge_ts", 0))
    except Exception:
        last = 0.0
    if now - last < COOLDOWN_S:
        sys.exit(0)

    # Nudge feuern + Cooldown-Stempel atomar schreiben.
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"last_nudge_ts": now, "reason": reason}), encoding="utf-8")
        os.replace(tmp, STATE)
    except Exception:
        pass

    print(json.dumps({"systemMessage":
                      f"[ultracode-advisor] Task wirkt fan-out-faehig ({reason}). "
                      f"Multi-Agent-Schwarm (gated, laeuft nur auf dein Wort): Keyword "
                      f"„ultracode“ tippen fuer parallele Subagents + adversariales "
                      f"Verify — sonst loese ich solo."}))
    sys.exit(0)


if __name__ == "__main__":
    main()
