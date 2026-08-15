#!/usr/bin/env python3
"""routine_digest.py — SessionStart-Hook: Routine-Lage in die Session injizieren.

der Nutzer-Auftrag 2026-08-14: "sobald wir chatten in dieser Session einmal auf neue MD
pruefen und mit mir besprechen; gleichzeitig checken ob die Routinen planmaessig
liefen, sonst Ursache finden und fixen."

Als Hook statt als Vorsatz, weil ein Vorsatz genau die Sorte Regel ist, die nach
zwanzig Turns still verschwindet (belegt: gamebot-compact-amnesie). Der Hook laeuft
bei jedem SessionStart in diesem Projekt und haengt das Ergebnis von
routine_audit.py als Kontext an — Claude sieht es, ohne dass der Nutzer fragen muss.

Best-effort: jeder Fehler => still, Exit 0. Ein kaputter Hook darf keine Session
blockieren (Konvention aller Hooks hier).
"""
import json
import subprocess
import sys
from pathlib import Path

AUDIT = Path.home() / ".claude" / "scripts" / "routine_audit.py"
# Nur im Skills_&_Co-Projekt injizieren — anderswo waere es Rauschen.
PROJECT_MARKER = "Skills_&_Co"


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}

    cwd = str(payload.get("cwd") or Path.cwd())
    if PROJECT_MARKER not in cwd:
        return 0
    if not AUDIT.exists():
        return 0

    try:
        out = subprocess.run(
            ["/usr/bin/python3", str(AUDIT)],
            capture_output=True, text=True, timeout=25).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 0
    if not out:
        return 0

    # Nur melden, wenn es etwas zu melden gibt: reine "alles planmaessig"-Zeile
    # ohne Reports/Bedarf wuerde jede Session mit einer Nullaussage eroeffnen.
    interesting = any(k in out for k in
                      ("UEBERFAELLIG", "WARTET", "NEUE REPORTS", "BRAUCHT MARCO", "Problem"))
    if not interesting:
        return 0

    context = (
        "Routine-Lage auf dem Server (automatisch geprueft, routine_audit.py):\n"
        f"{out}\n"
        "Auftrag dazu (der Nutzer 2026-08-14): neue Reports mit ihm besprechen; "
        "ueberfaellige Routinen selbst root-causen und nach Moeglichkeit fixen, "
        "danach Bescheid geben. Details je Report: "
        "~/projects/Skills_&_Co/ROUTINE_REPORTS/"
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
