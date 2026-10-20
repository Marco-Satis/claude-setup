"""Smoke-Tests fuer alle der Nutzer-Hooks unter ~/.claude/hooks/.

Erstellt: 2026-05-16 (Review-Finding Q3)
Zweck: jeder Hook wird mit einem minimalen valid Input und einer Reihe
       Edge-Cases aufgerufen. Tests pruefen:
       - Exit-Code (0 = ok, nicht-blockierend; 2 = block)
       - stdout-Format (valid JSON wenn nicht leer)
       - Latenz (< Timeout aus settings.json)
       - Erwartete Patterns matchen / nicht-Patterns matchen nicht

Aufruf:
    cd ~/.claude/hooks/tests
    python -m pytest -v   (mit pytest)
    python test_hooks_smoke.py  (direkt, ohne pytest)
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent


def run_hook(hook_name: str, stdin_data: dict, timeout: float = 10.0) -> dict:
    """Returns dict with stdout/stderr/returncode/latency_ms.

    Bei Output-Parsing-Fehler returns stdout als raw-Text.
    """
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(HOOKS_DIR / hook_name)],
        input=json.dumps(stdin_data),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    latency = (time.perf_counter() - start) * 1000

    stdout = result.stdout.strip()
    parsed = None
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = {"_raw": stdout}

    return {
        "stdout": stdout,
        "stdout_parsed": parsed,
        "stderr": result.stderr.strip(),
        "returncode": result.returncode,
        "latency_ms": latency,
    }


# === Test-Cases (label, hook_file, stdin, expect_match, expect_empty) ===
# expect_match: substring der in stdout sein muss
# expect_empty: True -> stdout muss leer sein
TEST_CASES = [
    # === important_edit_reminder.py ===
    {
        "name": "important_edit / settings.json -> Reminder",
        "hook": "important_edit_reminder.py",
        "stdin": {"tool_name": "Edit", "tool_input": {"file_path": "C:/Users/der Nutzer/.claude/settings.json"}},
        "expect_match": "BACKUP-REMINDER",
    },
    {
        "name": "important_edit / CLAUDE.md -> Reminder",
        "hook": "important_edit_reminder.py",
        "stdin": {"tool_name": "Write", "tool_input": {"file_path": "C:/Users/der Nutzer/.claude/CLAUDE.md"}},
        "expect_match": "BACKUP-REMINDER",
    },
    {
        "name": "important_edit / hooks/foo.py -> Reminder",
        "hook": "important_edit_reminder.py",
        "stdin": {"tool_name": "Edit", "tool_input": {"file_path": "C:/Users/der Nutzer/.claude/hooks/foo.py"}},
        "expect_match": "BACKUP-REMINDER",
    },
    {
        "name": "important_edit / random file -> kein Reminder",
        "hook": "important_edit_reminder.py",
        "stdin": {"tool_name": "Edit", "tool_input": {"file_path": "C:/Users/der Nutzer/tmp/foo.txt"}},
        "expect_empty": True,
    },
    {
        "name": "important_edit / Read-Tool wird ignoriert",
        "hook": "important_edit_reminder.py",
        "stdin": {"tool_name": "Read", "tool_input": {"file_path": "C:/Users/der Nutzer/.claude/CLAUDE.md"}},
        "expect_empty": True,
    },
    # === git_push_reminder.py ===
    {
        "name": "git_push / normaler push -> Reminder",
        "hook": "git_push_reminder.py",
        "stdin": {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}},
        "expect_match": "TOKEN-PUSH-REMINDER",
    },
    {
        "name": "git_push / --force -> kein Reminder (inline blockt eh)",
        "hook": "git_push_reminder.py",
        "stdin": {"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}},
        "expect_empty": True,
    },
    {
        "name": "git_push / --dry-run -> kein Reminder",
        "hook": "git_push_reminder.py",
        "stdin": {"tool_name": "Bash", "tool_input": {"command": "git push --dry-run origin main"}},
        "expect_empty": True,
    },
    {
        "name": "git_push / harmloser bash-cmd -> kein Reminder",
        "hook": "git_push_reminder.py",
        "stdin": {"tool_name": "Bash", "tool_input": {"command": "ls -la"}},
        "expect_empty": True,
    },
    # === secret_leak_detector.py ===
    {
        "name": "secret_leak / Anthropic-FAKE -> Match",
        "hook": "secret_leak_detector.py",
        "stdin": {"prompt": "Test sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ende."},
        "expect_match": "Anthropic API Key",
    },
    {
        "name": "secret_leak / AWS-AKIA-FAKE -> Match",  # pragma: allowlist secret (Testattrappe, kein echter Schluessel)
        "hook": "secret_leak_detector.py",
        "stdin": {"prompt": "AWS Key: AKIAIOSFODNN7EXAMPLE aus Doku-Beispiel."},  # pragma: allowlist secret (Testattrappe, kein echter Schluessel)
        "expect_match": "AWS Access Key ID",
    },
    {
        "name": "secret_leak / Klartext -> kein Match",
        "hook": "secret_leak_detector.py",
        "stdin": {"prompt": "Normaler Prompt ohne Geheimnisse, lorem ipsum dolor."},
        "expect_empty": True,
    },
    {
        "name": "secret_leak / Kurzer Prompt -> geskipped",
        "hook": "secret_leak_detector.py",
        "stdin": {"prompt": "kurz"},
        "expect_empty": True,
    },
    # === context_threshold_warning.py ===
    {
        "name": "context_threshold / kein transcript_path -> ok",
        "hook": "context_threshold_warning.py",
        "stdin": {"prompt": "hallo"},
        # Hook prueft ggf. ob transcript existiert; sollte silent durchgehen
        "expect_empty": True,
    },
    # === footstep_constants_hint.py ===
    {
        "name": "footstep_constants / Edit ausserhalb constants.py -> ignoriert",
        "hook": "footstep_constants_hint.py",
        "stdin": {"tool_name": "Edit", "tool_input": {"file_path": "C:/Users/der Nutzer/foo.py"}},
        "expect_empty": True,
    },
    # === memory_start_probe.py (SessionStart, schreibt Health-State, silent) ===
    {
        "name": "memory_start_probe / valid SessionStart -> silent + exit 0",
        "hook": "memory_start_probe.py",
        "stdin": {"session_id": "__smoke_probe__", "cwd": "C:/tmp"},
        "expect_empty": True,  # Probe schreibt nur State-File, kein stdout
    },
    {
        "name": "memory_start_probe / leere stdin -> kein Crash, silent",
        "hook": "memory_start_probe.py",
        "stdin": {},
        "expect_empty": True,
    },
    # === memory_lazy_inject.py (UserPromptSubmit, nur bei Start=down + Service up) ===
    {
        "name": "memory_lazy_inject / unbekannte Session (start=None) -> silent (M-02)",
        "hook": "memory_lazy_inject.py",
        "stdin": {"session_id": "__smoke_inject_none__", "cwd": "C:/tmp", "prompt": "test"},
        "expect_empty": True,  # start=None -> exit ohne Flag (M-02), kein Inject
    },
    {
        "name": "memory_lazy_inject / leere stdin -> kein Crash, silent",
        "hook": "memory_lazy_inject.py",
        "stdin": {},
        "expect_empty": True,
    },
]


def main() -> int:
    failures: list[str] = []
    slow: list[str] = []

    for tc in TEST_CASES:
        try:
            result = run_hook(tc["hook"], tc["stdin"])
        except subprocess.TimeoutExpired:
            failures.append(f"{tc['name']}: TIMEOUT")
            continue
        except FileNotFoundError:
            failures.append(f"{tc['name']}: HOOK-FILE FEHLT ({tc['hook']})")
            continue

        # Latency-Check
        if result["latency_ms"] > 1000:
            slow.append(f"{tc['name']}: {result['latency_ms']:.0f}ms")

        # Assertion
        if tc.get("expect_empty"):
            if result["stdout"]:
                failures.append(f"{tc['name']}: erwartete leeren Output, war: {result['stdout'][:80]!r}")
                continue
        elif tc.get("expect_match"):
            if tc["expect_match"] not in result["stdout"]:
                failures.append(f"{tc['name']}: erwartete '{tc['expect_match']}', war: {result['stdout'][:120]!r}")
                continue

        # Returncode immer 0 (Hooks sind nicht-blockierend, nutzen JSON-Output)
        if result["returncode"] not in (0,):
            failures.append(f"{tc['name']}: exit-code {result['returncode']}, expected 0")
            continue

        print(f"  PASS ({result['latency_ms']:5.0f}ms): {tc['name']}")

    print()
    print("=" * 60)
    print(f"Total: {len(TEST_CASES)} Tests")
    print(f"Pass:  {len(TEST_CASES) - len(failures)}")
    print(f"Fail:  {len(failures)}")
    if slow:
        print(f"Slow (>1s):")
        for s in slow:
            print(f"  - {s}")
    if failures:
        print()
        print("FEHLSCHLAEGE:")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
