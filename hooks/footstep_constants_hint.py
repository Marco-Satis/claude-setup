#!/usr/bin/env python
"""PreToolUse Edit Hook: Reminder bei constants.py Edit.

Wenn TRANSIENT_PROFILES geaendert werden, sollte der Nutzer
/transient-profile-validator nach dem Edit ausfuehren (AUD-H3).
"""
import json
import re
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "") or ""
    if re.search(r"FootstepAnalyzer.*constants\.py$", file_path):
        out = {
            "systemMessage": (
                "FootstepPro constants.py Edit erkannt - falls TRANSIENT_PROFILES "
                "geaendert wird, /transient-profile-validator nach dem Edit ausfuehren "
                "(siehe AUD-H3 in REVIEW_REPORT_MASTER_v4.md)."
            )
        }
        print(json.dumps(out))


if __name__ == "__main__":
    main()
