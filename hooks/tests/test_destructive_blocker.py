#!/usr/bin/env python3
"""Regression-Tests fuer destructive_command_blocker.py (Audit H-3, 2026-07-21).

Testet AUSSCHLIESSLICH via stdin-JSON-Pipe (PreToolUse-Format) — es wird nie
ein echtes Kommando ausgefuehrt. Erwartung: exit 2 = deny, exit 0 = allow;
'warn' = exit 0 + systemMessage-JSON auf stdout.
"""
import json
import subprocess
import sys
import os

HOOK = os.path.expanduser("~/.claude/hooks/destructive_command_blocker.py")

# (command, expected)  expected in {"deny", "allow", "warn"}
CASES = [
    # --- Audit-Angriffs-Formen (vorher alle ALLOWED) ---
    ("rm -rf /*", "deny"),
    ("rm -rf ~/*", "deny"),
    ("git push origin +main", "deny"),
    ("find / -delete", "deny"),
    ("git reset --hard", "warn"),
    # --- rm-Varianten ---
    ("rm -rf /", "deny"),
    ("rm -fr /", "deny"),
    ("rm -rf ~", "deny"),
    ("rm -rf ~/", "deny"),
    ("rm --recursive --force /", "deny"),
    ("rm --force --recursive ~", "deny"),
    ("rm -r -f $HOME", "deny"),
    ("rm -rf $HOME/*", "deny"),
    ("rm -rf ${HOME}", "deny"),
    ("rm -rf " + os.path.expanduser("~"), "deny"),
    ("rm -Rf /", "deny"),
    ("rm -rvf /", "deny"),
    ("sudo rm -rf /", "deny"),
    ("rm -rf .", "deny"),
    ("rm -rf ..", "deny"),
    ("cd /tmp && rm -rf /", "deny"),
    ("bash -c 'rm -rf /'", "deny"),
    ("sh -c \"rm -rf ~/*\"", "deny"),
    ("eval rm -rf /", "deny"),
    ("echo $(rm -rf /)", "deny"),
    # --- git push Varianten ---
    ("git push -f origin main", "deny"),
    ("git push --force origin main", "deny"),
    ("git push origin '+refs/heads/main'", "deny"),
    ("git -C /tmp/repo push --force", "deny"),
    # --- find Varianten ---
    ("find /etc -name '*.conf' -delete", "deny"),
    ("find ~ -name '*.log' -delete", "deny"),
    ("find $HOME -delete", "deny"),
    ("find ../.. -name x -delete", "deny"),
    # --- Legacy-Klassiker (Original-Liste, jetzt token-basiert) ---
    ("mkfs.ext4 /dev/sda1", "deny"),
    ("dd if=/dev/zero of=/dev/sda", "deny"),
    # --- Warn-Stufe ---
    ("git reset --hard HEAD~1", "warn"),
    ("git reset --hard origin/main", "warn"),
    # --- Benigne Formen (muessen ALLE durchgehen) ---
    ("rm -rf ./build", "allow"),
    ("rm -rf /tmp/x", "allow"),
    ("rm -rf build/ dist/", "allow"),
    ("rm -rf node_modules", "allow"),
    ("rm -f /tmp/lockfile", "allow"),
    ("rm -r ./cache", "allow"),
    ("git push origin main", "allow"),
    ("git push --force-with-lease origin main", "allow"),
    ("git push --force-with-lease=main origin main", "allow"),
    ("find . -name '*.pyc' -delete", "allow"),
    ("find /tmp -name '*.tmp' -delete", "allow"),
    ("find /tmp/build -delete", "allow"),
    ("find src -name '*.orig' -delete", "allow"),
    ("find / -name 'foo'", "allow"),          # kein -delete
    ("git reset --soft HEAD~1", "allow"),
    ("git reset HEAD file.py", "allow"),
    ("git checkout -b feature", "allow"),
    ("ls -la /", "allow"),
    # Quote-Literal-FPs (Audit-Bonus-Befund): Daten-Strings blocken nicht mehr
    ('echo "rm -rf /"', "allow"),
    ("echo 'git push --force'", "allow"),
    ('git commit -m "fix: rm -rf / handling"', "allow"),
    ('grep -r "find / -delete" docs/', "allow"),
    ('echo "dd if=/dev/zero"', "allow"),
    # format/del nur in Kommando-Position
    ("echo format c:", "allow"),
    ("python3 -c 'print(1)'", "allow"),
]


def run_case(command):
    payload = json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": command}})
    proc = subprocess.run(
        [sys.executable, HOOK], input=payload,
        capture_output=True, text=True, timeout=15)
    if proc.returncode == 2:
        return "deny", proc.stderr.strip()
    if proc.returncode == 0:
        out = proc.stdout.strip()
        if out:
            try:
                if "systemMessage" in json.loads(out):
                    return "warn", out
            except Exception:
                pass
        return "allow", out
    return f"exit{proc.returncode}", proc.stderr.strip()


def main():
    failures = []
    for command, expected in CASES:
        got, detail = run_case(command)
        status = "OK " if got == expected else "FAIL"
        if got != expected:
            failures.append((command, expected, got, detail))
        print(f"{status} [{expected:5s}→{got:5s}] {command}")
    print(f"\n{len(CASES) - len(failures)}/{len(CASES)} passed")
    if failures:
        print("\nFAILURES:")
        for command, expected, got, detail in failures:
            print(f"  {command!r}: expected {expected}, got {got} ({detail})")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
