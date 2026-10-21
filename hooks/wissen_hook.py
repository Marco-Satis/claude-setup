#!/usr/bin/env python3
"""wissen_hook — Einstieg des Wissenssystems (BAUPLAN_v4 B05, Phase M).

Aufruf: python3 -I ~/.claude/hooks/wissen_hook.py start|prompt|guard  (stdin = Hook-JSON)
Ohne ~/.claude/flags/wissen_m.on (nur auf netcup gesetzt; flags/ synct nicht): sofort Exit 0 ohne Ausgabe.
~/.claude/flags/wissen.off: start/prompt aus; der Guard (Selbstschutz) bleibt aktiv (BAUPLAN_v4 2.3 Nr. 5).
Jeder Fehler: Exit 0 ohne Ausgabe und eine Zeile in ~/.claude/logs/wissen_hook.log.
"""
import os
import sys


def main():
    t0 = __import__("time").monotonic()
    home = os.path.expanduser("~")
    flags = os.path.expanduser(os.environ.get("WZ_FLAGS") or os.path.join(home, ".claude", "flags"))
    if not os.path.exists(os.path.join(flags, "wissen_m.on")):
        return 0
    modus = sys.argv[1] if len(sys.argv) > 1 else ""
    if modus not in ("start", "prompt", "guard"):
        return 0
    if modus != "guard" and os.path.exists(os.path.join(flags, "wissen.off")):
        return 0
    import json
    try:
        d = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(d, dict):
        return 0
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "wissen"))
    if modus == "guard":
        import wissen_guard as g
        out = g.hook(d, t0)
    else:
        import wissen_m as m
        out = m.start_hook(d, t0) if modus == "start" else m.prompt_hook(d, t0)
    if out:
        sys.stdout.write(json.dumps(out, ensure_ascii=False))
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 — Hook endet immer mit Exit 0
        try:
            import time
            p = os.path.join(os.path.expanduser("~"), ".claude", "logs", "wissen_hook.log")
            with open(p, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {sys.argv[1:2]} {type(e).__name__}: {str(e)[:200]}\n")
        except Exception:  # noqa: BLE001
            pass
    sys.exit(0)
