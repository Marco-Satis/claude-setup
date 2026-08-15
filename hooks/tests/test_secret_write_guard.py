#!/usr/bin/env python3
"""Regression-Tests fuer secret_write_guard.py (TikTok-Audit Finding H-4, 2026-07-21).

Testet AUSSCHLIESSLICH via stdin-JSON-Pipe (PreToolUse-Format) — es wird nie
ein Secret persistiert oder ein echtes Kommando ausgefuehrt. Alle Token sind
SYNTHETISCH (FAKETEST) und werden erst zur LAUFZEIT per Konkatenation gebaut,
damit diese Datei at-rest nie ein literal matchendes Pattern enthaelt (sonst
wuerde der live verdrahtete Guard Edits an dieser Testdatei selbst blocken).

Erwartung: deny = exit 0 + stdout-JSON hookSpecificOutput.permissionDecision
== "deny"; allow = exit 0 ohne deny-Output. Test-Output printet NIE einen
Token-Wert (nur Labels), damit nichts ins Transcript leakt.
"""
import json
import os
import subprocess
import sys

HOOK = os.path.expanduser("~/.claude/hooks/secret_write_guard.py")
LEAKS = os.path.expanduser("~/.claude/lessons/leaks.jsonl")

# --- Synthetische Tokens: NUR zur Laufzeit konkatenieren (nie literal!) ---
FAKE_ANTHROPIC = "sk-ant-api" + "03-" + "FAKETEST" + "A" * 40
FAKE_OPENAI_PROJ = "sk-" + "proj-" + "FAKETEST" * 6
FAKE_GHP = "ghp" + "_" + ("FAKETEST" * 5)[:36]
FAKE_AWS = "AKI" + "A" + "FAKETESTFAKETEST"
FAKE_GOOGLE = "AIz" + "a" + ("FAKETEST" * 5)[:35]
FAKE_SLACK = "xox" + "b-" + "FAKETEST-1234567890"
FAKE_DISCORD = ".".join(
    ["FakeDiscordTokenSegment1", "FakeSg", "FakeDiscordTokenSegment3Long"]
)

# (label, payload, expected)  expected in {"deny", "allow"}
CASES = [
    # --- Kern-Faelle aus dem Fix-Auftrag ---
    ("Write mit Fake-Anthropic-Key",
     {"tool_name": "Write",
      "tool_input": {"file_path": "/tmp/notes.md",
                     "content": "api_key = '" + FAKE_ANTHROPIC + "'\n"}},
     "deny"),
    ("Write mit harmlosem Text",
     {"tool_name": "Write",
      "tool_input": {"file_path": "/tmp/notes.md",
                     "content": "Ganz normaler Text ohne Secrets, sk-ant ist "
                                "nur ein Praefix-Fragment.\n"}},
     "allow"),
    ("Bash export mit Fake-Anthropic-Key",
     {"tool_name": "Bash",
      "tool_input": {"command": "export X=" + FAKE_ANTHROPIC}},
     "deny"),
    ("Bash harmlos (ls -la)",
     {"tool_name": "Bash", "tool_input": {"command": "ls -la /tmp && echo fertig"}},
     "allow"),
    # --- Edit / MultiEdit ---
    ("Edit new_string mit Fake-GitHub-PAT",
     {"tool_name": "Edit",
      "tool_input": {"file_path": "/tmp/app.py",
                     "old_string": "token = None",
                     "new_string": "token = '" + FAKE_GHP + "'"}},
     "deny"),
    ("Edit Redaktion (Secret nur in old_string) bleibt erlaubt",
     {"tool_name": "Edit",
      "tool_input": {"file_path": "/tmp/app.py",
                     "old_string": "token = '" + FAKE_GHP + "'",
                     "new_string": "token = get_env('GITHUB_TOKEN')  # [REDACTED]"}},
     "allow"),
    ("MultiEdit mit Fake-OpenAI-Key im 2. Edit",
     {"tool_name": "MultiEdit",
      "tool_input": {"file_path": "/tmp/app.py",
                     "edits": [
                         {"old_string": "a", "new_string": "b = 1  # harmlos"},
                         {"old_string": "c", "new_string": "k = '" + FAKE_OPENAI_PROJ + "'"},
                     ]}},
     "deny"),
    # --- Weitere Pattern-Klassen (Single-Source secret_patterns.json) ---
    ("Bash mit Fake-AWS-Key",
     {"tool_name": "Bash",
      "tool_input": {"command": "aws configure set aws_access_key_id " + FAKE_AWS}},
     "deny"),
    ("Write mit Fake-Google-Key",
     {"tool_name": "Write",
      "tool_input": {"file_path": "/tmp/g.py",
                     "content": "GEMINI = '" + FAKE_GOOGLE + "'\n"}},
     "deny"),
    ("Write mit Fake-Slack-Token",
     {"tool_name": "Write",
      "tool_input": {"file_path": "/tmp/s.py",
                     "content": "SLACK = '" + FAKE_SLACK + "'\n"}},
     "deny"),
    ("Write mit Fake-Discord-Token",
     {"tool_name": "Write",
      "tool_input": {"file_path": "/tmp/d.py",
                     "content": "DISCORD = '" + FAKE_DISCORD + "'\n"}},
     "deny"),
    # --- Ausnahme-Pfade ---
    ("Write nach ~/.claude/lessons/ (exempt)",
     {"tool_name": "Write",
      "tool_input": {"file_path": os.path.join(os.path.expanduser("~"),
                                               ".claude", "lessons", "leaks.jsonl"),
                     "content": "{\"note\": \"" + FAKE_ANTHROPIC + "\"}\n"}},
     "allow"),
    ("Write nach *.bak.pre-<tag>.<ts> (exempt, Backup-Konvention)",
     {"tool_name": "Write",
      "tool_input": {"file_path": "/tmp/settings.json.bak.pre-fixsweep.1784600000",
                     "content": "key = '" + FAKE_ANTHROPIC + "'\n"}},
     "allow"),
    # --- Robustheit / Nicht-Zustaendigkeit ---
    ("Unbewachtes Tool (Read) mit Token im Input",
     {"tool_name": "Read",
      "tool_input": {"file_path": "/tmp/" + FAKE_ANTHROPIC}},
     "allow"),
    ("Content unter MIN_SCAN_LEN",
     {"tool_name": "Write",
      "tool_input": {"file_path": "/tmp/x", "content": "kurz"}},
     "allow"),
    ("Leerer tool_input",
     {"tool_name": "Write", "tool_input": {}},
     "allow"),
]


def run_payload(raw_stdin):
    proc = subprocess.run(
        [sys.executable, HOOK], input=raw_stdin,
        capture_output=True, text=True, timeout=15)
    if proc.returncode != 0:
        return f"exit{proc.returncode}", proc.stderr.strip()
    out = proc.stdout.strip()
    if out:
        try:
            parsed = json.loads(out)
            hso = parsed.get("hookSpecificOutput", {})
            if (hso.get("permissionDecision") == "deny"
                    and hso.get("hookEventName") == "PreToolUse"
                    and hso.get("permissionDecisionReason")):
                return "deny", hso.get("permissionDecisionReason", "")
        except Exception:
            return "badout", out[:100]
    return "allow", ""


def main():
    failures = []
    for label, payload, expected in CASES:
        got, _detail = run_payload(json.dumps(payload))
        status = "OK " if got == expected else "FAIL"
        if got != expected:
            failures.append((label, expected, got))
        print(f"{status} [{expected:5s}->{got:5s}] {label}")

    # Kaputtes JSON darf nie crashen (best-effort, exit 0, kein deny)
    got, _ = run_payload("{kaputt::: kein json")
    status = "OK " if got == "allow" else "FAIL"
    if got != "allow":
        failures.append(("Kaputtes stdin-JSON", "allow", got))
    print(f"{status} [allow->{got:5s}] Kaputtes stdin-JSON")

    got, _ = run_payload("")
    status = "OK " if got == "allow" else "FAIL"
    if got != "allow":
        failures.append(("Leeres stdin", "allow", got))
    print(f"{status} [allow->{got:5s}] Leeres stdin")

    # Leak-Log-Hygiene: leaks.jsonl darf NIE einen Token-Wert enthalten
    try:
        with open(LEAKS, encoding="utf-8") as fh:
            log_text = fh.read()
        if "FAKETEST" in log_text or FAKE_DISCORD.split(".")[0] in log_text:
            failures.append(("leaks.jsonl enthaelt Token-Wert!", "nur Hash", "WERT"))
            print("FAIL leaks.jsonl enthaelt einen Token-Wert!")
        else:
            print("OK   leaks.jsonl: nur Pattern-Name + Hash, kein Wert")
    except OSError:
        print("WARN leaks.jsonl nicht lesbar — Log-Check uebersprungen")

    total = len(CASES) + 2
    print(f"\n{total - len(failures)}/{total} passed (+ Log-Hygiene-Check)")
    if failures:
        print("\nFAILURES:")
        for label, expected, got in failures:
            print(f"  {label}: expected {expected}, got {got}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
