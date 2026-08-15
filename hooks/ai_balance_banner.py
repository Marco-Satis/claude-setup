#!/usr/bin/env python
r"""ai_balance_banner.py — SessionStart-Hook: Multi-AI Balance/Cost-Watchdog (2026-06-04).

Reaktiver Watchdog (KEIN Live-Balance-Query — kein Provider hat das verdrahtet).
Scannt die Usage-Logs via ai_usage.py --json und injiziert NUR dann eine
systemMessage, wenn echte Aktion noetig ist:
  - DeepSeek/Nano: letzter Call HTTP 402 / Tages-Cap erreicht  -> Guthaben
  - irgendein Provider: letzter Call auth-needed                -> Key/Login
  - Geld-Spend-Gelbwarnung (Nano-Cap-Naehe, DeepSeek-402-Haeufung)

Kein Alarm = stilles Exit 0 (kein Banner-Spam). Aktiv-Injektion statt passiver
Doku-Regel, weil Self-Monitoring im Flow vergessen wird (Lyra-Active-Monitoring).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")   # Windows cp1252 + Emoji-safe
except Exception:
    pass

AI_USAGE = Path.home() / ".claude" / "scripts" / "ai_usage.py"


def main() -> int:
    if not AI_USAGE.exists():
        return 0
    try:
        p = subprocess.run([sys.executable, str(AI_USAGE), "--json", "--days", "7"],
                           capture_output=True, text=True, encoding="utf-8", timeout=8)
    except Exception as e:
        # Watchdog darf Session-Start nie blocken — aber Ausfall SICHTBAR machen
        # (vorher: stilles return 0 -> Watchdog tot ohne jedes Signal).
        print(json.dumps({"systemMessage":
              f"⚠ Multi-AI-Watchdog inaktiv: ai_usage.py nicht ausfuehrbar ({type(e).__name__})"},
              ensure_ascii=False))
        return 0
    if p.returncode != 0:
        print(json.dumps({"systemMessage":
              f"⚠ Multi-AI-Watchdog inaktiv: ai_usage.py exit {p.returncode} "
              f"({(p.stderr or '').strip()[:80]})"}, ensure_ascii=False))
        return 0
    try:
        d = json.loads(p.stdout or "{}")
    except Exception:
        print(json.dumps({"systemMessage":
              "⚠ Multi-AI-Watchdog inaktiv: ai_usage.py lieferte kein gueltiges JSON"},
              ensure_ascii=False))
        return 0

    lines: list[str] = list(d.get("balance_needed", []))
    # Nur Geld-relevante Flags ins Banner (Rate-Limit-Gelb interessiert hier weniger).
    for f in d.get("flags", []):
        if any(t in f for t in ("$", "402", "Balance", "Prepay", "Guthaben")):
            lines.append(f)

    if not lines:
        return 0

    total = d.get("usd_window_total", 0.0)
    msg = ("💰 Multi-AI-Watchdog — Aktion noetig:\n"
           + "\n".join(f"• {ln}" for ln in lines)
           + f"\n(Fenster-Kosten 7d: ${total} · Details: python ~/.claude/scripts/ai_usage.py)")
    print(json.dumps({"systemMessage": msg}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
