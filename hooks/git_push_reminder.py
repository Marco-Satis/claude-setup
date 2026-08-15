#!/usr/bin/env python
"""PreToolUse Hook (Bash): Reminder bei git push wegen Token-Push-Verbot.

der Nutzer Universal Rule 4: 'Token-Push-Verbot bis Token-Rotation manuell
durchgefuehrt (siehe Discord_Bots PLAN)'.

Bisher passive Regel — Claude wurde dadurch nicht aktiv gestoppt. Dieser
Hook injiziert eine SystemMessage wenn `git push` ohne `--force` erkannt
wird (der existierende inline-Bash-Hook in settings.json blockt bereits
`git push --force` hart). Nicht-blockierend — der Nutzer kann explizit
bestaetigen dass Token-Rotation erledigt ist und dann nochmal pushen.
"""
import json
import re
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    cmd = data.get("tool_input", {}).get("command", "") or ""

    # Match git push (Variants: 'git push', 'git push origin', etc.)
    # Aber NICHT git push --force (wird bereits geblockt) und nicht git push --dry-run
    if not re.search(r"\bgit\s+push\b", cmd):
        sys.exit(0)
    if "--force" in cmd or re.search(r"(^|\s)-f\b", cmd) or "--dry-run" in cmd:
        sys.exit(0)

    msg = (
        "[TOKEN-PUSH-REMINDER] git push erkannt: "
        f"`{cmd[:120]}{'...' if len(cmd) > 120 else ''}`\n"
        "Universal Rule 4: 'Token-Push-Verbot bis Token-Rotation manuell durchgefuehrt'. "
        "Vor dem Push pruefen:\n"
        " 1. Token-Rotation in Discord Developer Portal erledigt?\n"
        " 2. .env nicht im commit (`git diff --staged --name-only` checken)?\n"
        " 3. `detect-secrets-hook` gelaufen (kein hardcoded Token im Diff)?\n"
        "Falls alles geklaert: der Nutzer im Chat explizit bestaetigen und Push wiederholen."
    )
    print(json.dumps({"systemMessage": msg}))


if __name__ == "__main__":
    main()
