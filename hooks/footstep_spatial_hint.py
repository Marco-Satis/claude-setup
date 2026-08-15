#!/usr/bin/env python
"""PostToolUse Edit/Write Hook: Reminder bei spatial_analyzer.py Edit.

AUD-H2 zeigte ~140s statt 3s deklariert -> nach Edit Performance-Smoke-Test
(max 10s fuer 30s-Stereo) empfohlen.
"""
import json
import re
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", {})
    file_path = tool_input.get("file_path") or tool_response.get("filePath") or ""

    if re.search(r"FootstepAnalyzer.*spatial_analyzer\.py$", file_path):
        out = {
            "systemMessage": (
                "spatial_analyzer.py Edit erkannt - Performance-Smoke-Test empfohlen "
                "(Erwartung <10s fuer 30s-Stereo). Siehe AUD-H2 / "
                "/spatial-pipeline-helper."
            )
        }
        print(json.dumps(out))


if __name__ == "__main__":
    main()
