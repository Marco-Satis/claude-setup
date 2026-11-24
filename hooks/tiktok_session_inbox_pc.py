"""Model-free Windows receiver: send only routing metadata over existing SSH."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

# Verified PC project roots, not model-provided target names.
ROOTS = (
    Path(r"C:\Users\<user>\AudioSetup"),
    Path(r"C:\Users\<user>\OneDrive\Dokumente\Projekte\System_Diagnose"),
    Path(r"C:\Users\<user>\projects-sync\Skills_&_Co"),
    Path(r"C:\Users\<user>\Games\Survivor_io"),
    Path(r"C:\Users\<user>\Games\CellSurvivor"),
    Path(r"C:\Users\<user>\Games\IdleSlayer"),
)
REMOTE_SCRIPT = "$HOME/n8n_stack/scripts/session_inbox.py"
# 2026-11-24 (Befund Setup PC, MB329): Ohne netcup-Verbindung kostete jeder Hook 2-4,5 s.
# Nach einem SSH-Fehlschlag ueberspringen alle drei Ereignisse 60 s lang den Abruf.
FAIL_BACKOFF_S = 60
OK_INTERVAL_S = 30


def _write_state(state: Path, fehler: bool) -> None:
    state.parent.mkdir(parents=True, exist_ok=True)
    temporary = state.with_name(state.name + f".tmp.{os.getpid()}")
    temporary.write_text(json.dumps({"checked_at": time.time(), "fehler": fehler}), encoding="utf-8")
    os.replace(temporary, state)


def metadata(data: dict) -> dict | None:
    if not isinstance(data, dict) or data.get("agent_id"):
        return None
    event, cwd, session = data.get("hook_event_name"), data.get("cwd"), data.get("session_id")
    if event not in ("SessionStart", "UserPromptSubmit", "PostToolUse"):
        return None
    if not isinstance(cwd, str) or not isinstance(session, str) or not session or len(session) > 200:
        return None
    current = Path(cwd).resolve()
    if not any(current == root or root in current.parents for root in ROOTS):
        return None
    return {"hook_event_name": event, "cwd": str(current), "session_id": session}


def receive(data: dict) -> dict | None:
    info = metadata(data)
    if info is None:
        return None
    if (Path.home() / ".claude/flags/tiktok_session_inbox.off").exists():
        return None
    key = hashlib.sha256(info["session_id"].encode()).hexdigest()
    state = Path.home() / ".claude/state/tiktok_inbox_pc" / (key + ".json")
    if state.exists():
        try:
            last = json.loads(state.read_text())
            age = time.time() - float(last["checked_at"])
            if last.get("fehler") and age < FAIL_BACKOFF_S:
                return None
            if info["hook_event_name"] == "PostToolUse" and not last.get("fehler") and age < OK_INTERVAL_S:
                return None
        except (ValueError, KeyError, TypeError, OSError):
            pass
    try:
        process = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=2", "-o", "ConnectionAttempts=1",
             "netcup-marco", "python3", "-I", "-S", REMOTE_SCRIPT, "hook"],
            input=json.dumps(info), capture_output=True, text=True, encoding="utf-8", timeout=4.5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (subprocess.TimeoutExpired, OSError):
        _write_state(state, fehler=True)
        return None
    if process.returncode != 0:
        _write_state(state, fehler=True)
        return None
    # An empty response means the server was reachable, with nothing to deliver.
    result = json.loads(process.stdout) if process.stdout.strip() else None
    if result is not None:
        if not isinstance(result, dict) or not isinstance(result.get("hookSpecificOutput"), dict):
            return None
        output = result["hookSpecificOutput"]
        if output.get("hookEventName") != info["hook_event_name"] or not isinstance(output.get("additionalContext"), str):
            return None
        # Only the allowed context fields are forwarded, never a block/approval decision.
        result = {"hookSpecificOutput": {"hookEventName": output["hookEventName"],
                                          "additionalContext": output["additionalContext"]}}
    _write_state(state, fehler=False)
    return result


def main() -> int:
    try:
        raw = sys.stdin.read(65537)
        if len(raw) > 65536:
            return 0
        result = receive(json.loads(raw))
        if result is not None:
            print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        # Never print SSH stderr, prompts, tool output or credential-like data.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
