#!/usr/bin/env python
"""PreToolUse Hook (Edit/Write): Backup-Reminder bei wichtigen Files.

der Nutzer Universal Rule 2: 'Backup vor Edit persistenter/wichtiger Files:
cp -a <file> <file>.bak.$(date +%s)'.

Bisher passive Regel in CLAUDE.md — wurde im Flow oft vergessen. Dieser Hook
aktiviert sie: bei Edit/Write auf wichtige Files wird eine SystemMessage
injiziert die Claude erinnert, vorher Backup zu machen.

Nicht blockierend (gibt nur SystemMessage zurück, kein exit 2) — der Nutzer oder
Claude kann ignorieren wenn Backup nicht noetig (z.B. neue Datei via Write).
"""
import json
import re
import sys


# Patterns fuer "wichtige" Files die ein Backup verdienen
# Q8-Fix (2026-05-16): vereinfacht durch re.IGNORECASE (statt [Cc]:/[Uu]sers etc.)
# Alle Patterns werden case-insensitive gematched.
IMPORTANT_PATTERNS = [
    # Claude-Code-Config
    r"\.claude/CLAUDE\.md$",
    r"\.claude/settings\.json$",
    r"\.claude/settings\.local\.json$",
    r"\.claude/skills/.*/SKILL\.md$",
    r"\.claude/agents/.*\.md$",
    r"\.claude/hooks/.*\.py$",
    r"\.claude/rules/.*\.md$",
    # Plan/State-Files
    r"PROGRESS\.md$",
    r"REVIEW_REPORT.*\.md$",
    r"STATUS_.*\.md$",
    # Discord_Bots / FootstepPro kritisch (case-insensitive match)
    r"discord_bots/CLAUDE\.md$",
    r"discord_bots/.*\.env",
    r"footstepanalyzer/constants\.py$",
    # SEC-006 (2026-05-16): SSH / Server-Config Defense-in-Depth
    r"\.ssh/config$",
    r"\.ssh/known_hosts$",
    r"nginx/sites-(available|enabled)/.+",
    r"systemd/system/.+\.service$",
    r"/etc/sudoers\.d/.+",
]


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name not in ("Edit", "Write"):
        sys.exit(0)

    tool_input = data.get("tool_input", {}) or {}
    fp = tool_input.get("file_path", "") or ""
    if not fp:
        sys.exit(0)

    fp_norm = fp.replace("\\", "/")

    for pat in IMPORTANT_PATTERNS:
        if re.search(pat, fp_norm, re.IGNORECASE):
            msg = (
                f"[BACKUP-REMINDER] Wichtige Datei wird editiert: {fp_norm}\n"
                f"Laut Universal Rule 2: 'cp -a {fp_norm} {fp_norm}.bak.$(date +%s)' "
                f"vor Edit ausfuehren (nur bei Edit/Append; bei Write auf neue Datei nicht noetig). "
                f"Falls bereits gemacht oder Datei nicht-kritisch: ignorieren."
            )
            print(json.dumps({"systemMessage": msg}))
            break


if __name__ == "__main__":
    main()
