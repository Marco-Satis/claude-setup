#!/usr/bin/env python3
"""Hook-Health-Check fuer des Nutzers Claude-Code-Setup — v2 (Wiring-treu).

Historie:
    2026-05-16  v1 (Review-Finding Q9) — testete hooks/*.py mit sys.executable
                und riet Events per Namens-Heuristik.
    2026-07-21  v2 (Fixsweep, Audit-Findings H-2 hoch + H-6-Anteil aus
                REVIEW_TIKTOK_CLAUDE_CODE_TIPS_2026-07-20.md):
                v1 pruefte das FALSCHE — sys.executable statt der verdrahteten
                Command-Line (uebersah so den mit nicht existentem `python`
                verdrahteten syncthing_project_notice-Guard) und 19/30 Hooks
                defaulteten auf das UserPromptSubmit-Event.

Neue Logik (v2):
    1. settings.json hooks-Sektion parsen -> exakte verdrahtete Command-Lines
       + Events + Matcher + Timeouts (keine Heuristik, kein Raten).
    2. Pro verdrahtetem Hook:
       (a) referenziertes File existiert?
       (b) Interpreter der Command-Line existiert (which python vs python3!)?
       (c) Command-Line 1:1 wie verdrahtet ausfuehren (shell, wie es der
           Claude-Code-Harness tut) mit event-korrektem synthetischem
           stdin-JSON (session_id "healthcheck", env CLAUDE_HEALTH_CHECK=1),
           Timeout = verdrahteter timeout (Default 10s) -> exit-code + stderr.
    3. Reconcile (H-6): hooks/*.py im Dir vs. verdrahtetes Set ->
       "unverdrahtet auf DIESER Maschine" (kann auf der Windows-Seite
       verdrahtet sein — settings.json synct NICHT via Syncthing, hooks/*.py
       schon) + "verdrahtet aber File fehlt".
    4. Report: ~/.claude/lessons/hook_health_<YYYY-MM-DD>.md + kompaktes
       stdout. Exit != 0 wenn ein verdrahteter Hook hart failt
       (Interpreter/File fehlt, Timeout, exit-code weder 0 noch 2,
       korruptes JSON-stdout).

Manueller Aufruf:
    python3 ~/.claude/hooks/_health_check.py [--verbose] [--no-report]

Automatisiert:
    Cron (netcup): Mo 07:30, siehe crontab -l (Eintrag "_health_check.py").
    Optional als SessionStart-Hook: --hook-mode (liest stdin, exit immer 0,
    meldet Failures als {"systemMessage": ...} — fail-open-Konvention).
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOOKS_DIR = Path.home() / ".claude" / "hooks"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
LESSONS_DIR = Path.home() / ".claude" / "lessons"

DEFAULT_TIMEOUT = 10.0  # Sekunden, wenn kein timeout im Wiring deklariert
SELF_NAME = "_health_check.py"
IS_WINDOWS = os.name == "nt"

# Hard-Fail-Stati (=> exit != 0)
FAIL_STATI = {"FAIL", "TIMEOUT", "INTERPRETER-MISSING", "FILE-MISSING",
              "SYNTAX-ERROR", "JSON-INVALID"}


# ---------------------------------------------------------------- wiring parse

def load_wired_hooks(settings_path: Path) -> tuple[list[dict], str]:
    """Parst die hooks-Sektion aus settings.json.

    Returns ([{event, matcher, command, timeout}, ...], error_msg).
    """
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception as e:
        return [], f"settings.json nicht lesbar/parsebar: {e}"

    wired: list[dict] = []
    for event, blocks in (settings.get("hooks") or {}).items():
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            matcher = block.get("matcher", "")
            for hook in block.get("hooks", []):
                if not isinstance(hook, dict) or hook.get("type") != "command":
                    continue
                cmd = hook.get("command", "").strip()
                if not cmd:
                    continue
                wired.append({
                    "event": event,
                    "matcher": matcher,
                    "command": cmd,
                    "timeout": float(hook.get("timeout", DEFAULT_TIMEOUT)),
                })
    return wired, ""


def unquote(token: str) -> str:
    """'"C:\\x\\y.js"' -> 'C:\\x\\y.js' (umschliessende Quotes weg)."""
    for q in ('"', "'"):
        if len(token) >= 2 and token.startswith(q) and token.endswith(q):
            return token[1:-1]
    return token


def parse_command(command: str) -> tuple[str, list[Path]]:
    """(interpreter, referenzierte existenz-pruefbare Pfad-Tokens).

    Interpreter = argv[0]. Pfad-Tokens = alle weiteren Argumente die wie
    Datei-Pfade aussehen (enthalten / oder \\ oder beginnen mit ~).
    """
    try:
        tokens = shlex.split(command, posix=not IS_WINDOWS)
    except ValueError:
        tokens = command.split()
    # posix=False (Windows) laesst die Anfuehrungszeichen im Token stehen ->
    # Path('"C:\\...\\x.js"').exists() ist immer False. Darum entquoten.
    tokens = [unquote(t) for t in tokens]
    if not tokens:
        return "", []
    interpreter = tokens[0]
    paths: list[Path] = []
    for tok in tokens[1:]:
        if tok.startswith("-"):
            continue
        if tok.startswith("~") or "/" in tok or "\\" in tok:
            paths.append(Path(tok).expanduser())
    return interpreter, paths


# ------------------------------------------------------------- synthetic stdin

def first_matcher_tool(matcher: str) -> str:
    """"Edit|Write" -> "Edit"; "" -> "Bash" (generischer Default)."""
    if not matcher:
        return "Bash"
    return matcher.split("|")[0].strip() or "Bash"


def tool_input_for(tool: str) -> dict:
    dummy_file = str(Path.home() / ".claude" / "tmp_healthcheck_dummy.txt")
    if tool == "Bash":
        return {"command": "echo healthcheck", "description": "healthcheck dummy"}
    if tool == "Write":
        return {"file_path": dummy_file, "content": "healthcheck"}
    if tool in ("Edit", "Read", "Glob", "Grep"):
        return {"file_path": dummy_file, "old_string": "a", "new_string": "b"}
    return {"healthcheck": True}


def synthetic_stdin(event: str, matcher: str) -> dict:
    """Event-korrektes synthetisches Hook-Input-JSON (keine echten Daten)."""
    payload: dict = {
        "session_id": "healthcheck",
        "transcript_path": os.devnull,
        "cwd": str(Path.home()),
        "hook_event_name": event,
    }
    tool = first_matcher_tool(matcher)
    if event == "UserPromptSubmit":
        payload["prompt"] = "healthcheck synthetic prompt - bitte ignorieren, keine Secrets"
    elif event == "PreToolUse":
        payload.update({"tool_name": tool, "tool_input": tool_input_for(tool)})
    elif event == "PostToolUse":
        payload.update({"tool_name": tool, "tool_input": tool_input_for(tool),
                        "tool_response": {"stdout": "healthcheck", "success": True}})
    elif event == "PostToolUseFailure":
        payload.update({"tool_name": tool, "tool_input": tool_input_for(tool),
                        "error": "healthcheck synthetic error"})
    elif event in ("Stop", "SubagentStop"):
        payload["stop_hook_active"] = False
    elif event == "StopFailure":
        payload.update({"stop_hook_active": False,
                        "error": "healthcheck synthetic stop failure"})
    elif event == "SessionStart":
        payload["source"] = "startup"
    elif event == "SessionEnd":
        payload["reason"] = "other"
    elif event == "PreCompact":
        payload.update({"trigger": "manual", "custom_instructions": ""})
    elif event == "Notification":
        payload["message"] = "healthcheck synthetic notification"
    return payload


# ------------------------------------------------------------------ execution

def syntax_check(path: Path) -> str:
    """"" wenn OK, sonst Fehlertext. Nur fuer .py-Files sinnvoll."""
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return ""
    except SyntaxError as e:
        return f"SyntaxError: {e}"
    except OSError as e:
        return f"OSError: {e}"


def run_wired(entry: dict) -> dict:
    """Fuehrt die Command-Line 1:1 wie verdrahtet aus (shell, wie der Harness).

    stdin = event-korrektes synthetisches JSON, env CLAUDE_HEALTH_CHECK=1.
    """
    command = entry["command"]
    if IS_WINDOWS and "~" in command:
        # cmd.exe expandiert ~ nicht — plattformneutral vor-expandieren
        command = command.replace("~", str(Path.home()))

    env = dict(os.environ)
    env["CLAUDE_HEALTH_CHECK"] = "1"

    start = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            input=json.dumps(synthetic_stdin(entry["event"], entry["matcher"])),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=entry["timeout"],
            cwd=str(Path.home()),
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "returncode": None,
                "latency_ms": round(entry["timeout"] * 1000),
                "stderr": f"Timeout nach {entry['timeout']:.0f}s", "stdout_len": 0}
    except OSError as e:
        return {"status": "FAIL", "returncode": None, "latency_ms": 0,
                "stderr": f"OSError beim Start: {e}", "stdout_len": 0}

    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()[:300]

    # JSON-stdout nur validieren wenn der Hook JSON sein WILL ({/[-Start);
    # Plain-Text-stdout ist legaler Context-Injection-Modus.
    json_valid = True
    if stdout.startswith(("{", "[")):
        try:
            json.loads(stdout)
        except json.JSONDecodeError:
            json_valid = False

    if proc.returncode in (0, 2) and json_valid:
        status = "OK" if proc.returncode == 0 else "OK-BLOCKING"
    elif not json_valid:
        status = "JSON-INVALID"
    else:
        status = "FAIL"

    return {"status": status, "returncode": proc.returncode,
            "latency_ms": latency_ms, "stderr": stderr,
            "stdout_len": len(stdout)}


def check_entry(entry: dict) -> dict:
    """Kompletter Check eines verdrahteten Hooks: File, Interpreter, Ausfuehrung."""
    interpreter, paths = parse_command(entry["command"])
    result = {
        "event": entry["event"],
        "matcher": entry["matcher"],
        "command": entry["command"],
        "timeout": entry["timeout"],
        "interpreter": interpreter,
        "files": [str(p) for p in paths],
    }

    # Selbst-Rekursion vermeiden falls _health_check je verdrahtet wird
    if any(p.name == SELF_NAME for p in paths):
        result["status"] = "SKIPPED-SELF"
        return result

    # (a) referenzierte Files
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        result["status"] = "FILE-MISSING"
        result["stderr"] = f"File(s) nicht gefunden: {', '.join(missing)}"
        return result

    # (b) Interpreter auf PATH?
    if interpreter and shutil.which(interpreter) is None and not Path(interpreter).expanduser().exists():
        result["status"] = "INTERPRETER-MISSING"
        result["stderr"] = (f"Interpreter `{interpreter}` existiert auf dieser "
                            f"Maschine nicht (which {interpreter} = leer)")
        return result

    # Syntax-Vorpruefung fuer .py-Files (billig, praeziser Fehlertext)
    for p in paths:
        if p.suffix == ".py":
            err = syntax_check(p)
            if err:
                result["status"] = "SYNTAX-ERROR"
                result["stderr"] = f"{p.name}: {err}"
                return result

    # (c) 1:1-Ausfuehrung wie verdrahtet
    result.update(run_wired(entry))
    return result


# ------------------------------------------------------------------- reconcile

def reconcile(wired: list[dict]) -> dict:
    """H-6: hooks/*.py im Dir vs. verdrahtetes Set dieser Maschine."""
    wired_files: set[str] = set()
    for entry in wired:
        _, paths = parse_command(entry["command"])
        for p in paths:
            wired_files.add(p.name)

    present = sorted(
        p.name for p in HOOKS_DIR.glob("*.py")
        if not p.name.startswith("_") and ".bak" not in p.name
    )
    unwired = [n for n in present if n not in wired_files]
    wired_outside_dir = sorted(
        n for n in wired_files
        if n.endswith(".py") and not (HOOKS_DIR / n).exists()
    )
    return {
        "present_count": len(present),
        "wired_count": len(wired_files),
        "unwired_here": unwired,
        "wired_outside_hooks_dir": wired_outside_dir,
    }


# ---------------------------------------------------------------------- report

def write_report(results: list[dict], recon: dict, failures: list[dict],
                 settings_err: str) -> Path:
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)
    path = LESSONS_DIR / f"hook_health_{datetime.now().strftime('%Y-%m-%d')}.md"
    lines: list[str] = []
    lines.append("# Hook-Health-Report (v2, wiring-treu)\n")
    lines.append(f"- **Stand:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- **Maschine:** {os.uname().nodename if hasattr(os, 'uname') else os.environ.get('COMPUTERNAME', '?')} ({sys.platform})")
    lines.append(f"- **Settings:** `{SETTINGS_PATH}`")
    lines.append("- **Methode:** Command-Lines 1:1 wie verdrahtet ausgefuehrt (shell), "
                 "event-korrektes synthetisches stdin-JSON (session_id `healthcheck`, "
                 "env `CLAUDE_HEALTH_CHECK=1`), Timeout = verdrahteter timeout (Default 10s)")
    lines.append(f"- **Verdrahtete Eintraege:** {len(results)}, "
                 f"**Failures:** {len(failures)}\n")
    if settings_err:
        lines.append(f"> **FEHLER:** {settings_err}\n")

    lines.append("## Verdrahtete Hooks\n")
    lines.append("| Event | Matcher | Command | Status | Exit | Latenz (ms) | Detail |")
    lines.append("|---|---|---|---|---|---:|---|")
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
    for r in results:
        lat = r.get("latency_ms")
        lat_s = f"{lat:.0f}" if isinstance(lat, (int, float)) else "-"
        rc = r.get("returncode")
        detail = esc(r.get("stderr") or "")[:160]
        lines.append(
            f"| {r['event']} | `{esc(r['matcher'] or '*')}` | `{esc(r['command'])}` "
            f"| **{r['status']}** | {rc if rc is not None else '-'} | {lat_s} | {detail} |"
        )

    if failures:
        lines.append("\n## Failures-Detail\n")
        for r in failures:
            lines.append(f"### `{r['command']}` — {r['status']} (Event: {r['event']})")
            lines.append("```json")
            lines.append(json.dumps(r, indent=2, ensure_ascii=False))
            lines.append("```\n")

    lines.append("\n## Reconcile hooks/*.py vs. Wiring (H-6)\n")
    lines.append(f"- Files in `{HOOKS_DIR}` (ohne `_`-Prefix/.bak): {recon['present_count']}")
    lines.append(f"- In settings.json dieser Maschine referenziert: {recon['wired_count']}")
    if recon["unwired_here"]:
        lines.append(f"- **Unverdrahtet auf DIESER Maschine ({len(recon['unwired_here'])}):** "
                     + ", ".join(f"`{n}`" for n in recon["unwired_here"]))
    else:
        lines.append("- Unverdrahtet auf dieser Maschine: keine")
    if recon["wired_outside_hooks_dir"]:
        lines.append("- Verdrahtet, liegt aber ausserhalb von hooks/ oder fehlt: "
                     + ", ".join(f"`{n}`" for n in recon["wired_outside_hooks_dir"]))
    lines.append("")
    lines.append("> Hinweis: `hooks/*.py` synct bidirektional PC<->netcup via Syncthing, "
                 "`settings.json` (das Wiring) synct NICHT. \"Unverdrahtet\" gilt daher nur "
                 "fuer DIESE Maschine — dieselbe Datei kann auf der Windows-Seite verdrahtet "
                 "sein (z.B. footstep_*, ai_balance_banner, discord_afk_relay laut "
                 "HOOK_REGISTRIERUNG). Vor Archivierung Gegenseite pruefen.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ------------------------------------------------------------------------ main

def main() -> int:
    parser = argparse.ArgumentParser(description="Hook-Health-Check v2 (wiring-treu)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--no-report", action="store_true",
                        help="keinen Markdown-Report schreiben")
    parser.add_argument("--hook-mode", action="store_true",
                        help="laeuft selbst als Hook (stdin lesen, exit 0, systemMessage)")
    args = parser.parse_args()

    if args.hook_mode:
        try:
            json.load(sys.stdin)
        except Exception:
            pass

    wired, settings_err = load_wired_hooks(SETTINGS_PATH)
    if settings_err:
        print(f"FEHLER: {settings_err}")
        return 0 if args.hook_mode else 1
    if not wired:
        print(f"WARNUNG: keine verdrahteten Hooks in {SETTINGS_PATH} gefunden")

    results = [check_entry(e) for e in wired]
    failures = [r for r in results if r["status"] in FAIL_STATI]
    recon = reconcile(wired)

    # Kompaktes stdout
    print(f"Hook-Health-Check v2  {datetime.now().isoformat(timespec='seconds')}")
    print(f"Settings: {SETTINGS_PATH}")
    print(f"Verdrahtet: {len(results)} Eintraege | Failures: {len(failures)} | "
          f"unverdrahtet hier: {len(recon['unwired_here'])}")
    print()
    for r in results:
        ok = r["status"].startswith("OK") or r["status"] == "SKIPPED-SELF"
        marker = "OK" if ok else "!!"
        lat = r.get("latency_ms")
        lat_s = f"{lat:5.0f}ms" if isinstance(lat, (int, float)) else "      -"
        print(f"  {marker} [{lat_s}] {r['event']:20s} {r['command']}")
        if (not ok and r.get("stderr")) or (args.verbose and r.get("stderr")):
            print(f"       -> {r['status']}: {r['stderr'][:200]}")
    if recon["unwired_here"]:
        print("\nUnverdrahtet auf DIESER Maschine (evtl. Windows-seitig verdrahtet, "
              "settings.json synct nicht):")
        for n in recon["unwired_here"]:
            print(f"  - {n}")

    if not args.no_report:
        report = write_report(results, recon, failures, settings_err)
        print(f"\nReport: {report}")

    if args.hook_mode:
        if failures:
            msg = (f"[HOOK-HEALTH-FAIL] {len(failures)}/{len(results)} verdrahtete "
                   f"Hooks fehlerhaft ({', '.join(sorted({f['status'] for f in failures}))}). "
                   "Details: ~/.claude/lessons/hook_health_*.md")
            print(json.dumps({"systemMessage": msg}))
        return 0  # fail-open als Hook

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
