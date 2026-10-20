#!/usr/bin/env python
"""PostToolUse Edit/Write Hook: Run FootstepPro tests on Python file edits.

Triggers `python -m pytest tests -q` (only summary) for any Edit/Write
on FootstepAnalyzer/*.py except tests/. pytest (nicht unittest) weil die Suite
conftest.py + Fixtures nutzt; `unittest discover` laedt conftest nicht -> die
pytest-Style-Tests (chunk_lib/offline_bench-Import) scheiterten als falsche errors=3.

Reason: Plan v1.5 hat 141 Tests aufgebaut; verhindert Regression bei
AUD-RESOLVED-Findings (kf_penalty Slope, Centroid Hann-Window, Mono-LUFS).
"""
import json
import os
import re
import subprocess
import sys
import time


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", {})
    file_path = tool_input.get("file_path") or tool_response.get("filePath") or ""

    # Match FootstepAnalyzer/*.py mit smarten Excludes
    if not re.search(r"FootstepAnalyzer", file_path):
        sys.exit(0)
    if not file_path.endswith(".py"):
        sys.exit(0)
    # Verzeichnisse die nicht test-relevant sind ueberspringen
    if re.search(r"FootstepAnalyzer[\\/](tests|_archiv|backups|__pycache__|examples|examples_data|scripts|docs)[\\/]", file_path):
        sys.exit(0)
    # Underscore-prefix-Konvention: privat/experimentell/temp -> kein Auto-Test
    basename = os.path.basename(file_path)
    if basename.startswith("_"):
        sys.exit(0)

    fp_root = "C:/Users/der Nutzer/OneDrive/Dokumente/AudioSetup/FootstepAnalyzer"
    if not os.path.isdir(fp_root):
        sys.exit(0)

    # Debounce (2026-05-29): der Test-Lauf blockt synchron (pytest ~10s). Bei schnellem
    # iterativem Editieren wuerde jeder Edit erneut stallen. Wenn der letzte Lauf
    # < 90s her ist: skip (Regression-Gate bleibt erhalten, nur nicht bei jeder Mini-Edit).
    marker = os.path.join(os.path.expanduser("~"), ".claude", "state", ".footstep_pytest_last")
    try:
        if os.path.exists(marker) and (time.time() - os.path.getmtime(marker)) < 90:
            print(json.dumps({"systemMessage": "FootstepPro Tests: skip (lief < 90s her, Debounce)"}))
            sys.exit(0)
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w") as _m:
            _m.write(str(time.time()))  # Marker VOR Lauf setzen -> debounct auch parallele Edits
    except Exception:
        pass  # Debounce-Fehler darf Test-Lauf nicht verhindern

    # venv-Umstellung (2026-08-03, P9-03-Folgeschritt): Suite laeuft im Projekt-venv.
    # Seit 2026-10-07 (Audit M-037, der Nutzer-Go) liegt das kanonische venv AUSSERHALB von
    # OneDrive unter %USERPROFILE%\.venvs\FootstepAnalyzer (Files-On-Demand hatte das alte
    # FootstepAnalyzer/.venv dehydriert -> Errno 22). Reihenfolge: .venvs > altes .venv >
    # global-python (Fallback, z.B. frisch geklont oder auf netcup ohne venv).
    candidates = [
        os.path.join(os.path.expanduser("~"), ".venvs", "FootstepAnalyzer", "Scripts", "python.exe"),
        os.path.join(fp_root, ".venv", "Scripts", "python.exe"),
    ]
    python_exe = next((p for p in candidates if os.path.isfile(p)), "python")

    try:
        result = subprocess.run(
            [python_exe, "-m", "pytest", "tests", "-q", "--no-header"],
            cwd=fp_root,
            capture_output=True,
            text=True,
            timeout=80,
        )
        # pytest schreibt die Summary ("484 passed, 5 skipped in ...s") auf STDOUT (unittest
        # schrieb auf stderr). Summary-Zeile suchen (enthaelt passed/failed/error).
        out_lines = [ln for ln in (result.stdout or "").strip().splitlines() if ln.strip()]
        summary = next((ln for ln in reversed(out_lines)
                        if re.search(r"passed|failed|error|no tests ran", ln, re.I)),
                       out_lines[-1] if out_lines else "pytest run finished")
        msg = summary.strip().strip("=").strip()
        print(json.dumps({"systemMessage": f"FootstepPro Tests: {msg}"}))
    except subprocess.TimeoutExpired:
        print(json.dumps({"systemMessage": "FootstepPro Tests TIMEOUT (>80s)"}))
    except Exception as e:
        print(json.dumps({"systemMessage": f"FootstepPro Tests Hook-Fehler: {e}"}))


if __name__ == "__main__":
    main()
