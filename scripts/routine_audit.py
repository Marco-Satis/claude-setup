#!/usr/bin/env python3
"""routine_audit.py — Laufen die Server-Routinen planmaessig? (der Nutzer 2026-08-14)

Zweck: der Nutzer sieht die Server-Routinen nicht. Diese Pruefung beantwortet pro Routine
zwei Fragen — ist sie planmaessig gelaufen, und braucht sie etwas von der Nutzer.

WICHTIG, Evidenz-Modell (der Grund, warum das kein Dreizeiler ist):
Nicht jede Routine schreibt bei jedem Lauf ins Log. Zwei Sorten:

  * "append"      — schreibt JEDEN Lauf (autoupdate, hook_suggest, tool_scout).
                    Log-mtime ist ein gueltiger Beleg; zu alt = ueberfaellig.
  * "event_only"  — schreibt NUR bei Ereignis (`pipeline_selfcheck --quiet` loggt
                    nur Warnungen, `sweep_watchdog` nur bei Daemon-Neustart).
                    Stille heisst hier GESUND. Log-mtime als Beleg zu nehmen waere
                    ein Fehlalarm — genau der Irrtum, der am 2026-08-14 fast zu
                    einer Falschmeldung gefuehrt haette.

Systemd-Timer liefern `LastTriggerUSec` direkt — das ist der harte Beleg, dort
braucht es keine Heuristik.

Ausgabe: kompakter Text auf stdout (fuer SessionStart-Hook + Claude) und, mit
--write-md, ein Digest nach ~/projects/Skills_&_Co/ROUTINE_REPORTS/.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path.home()
PROJECT = HOME / "projects" / "Skills_&_Co"
REPORTS = PROJECT / "ROUTINE_REPORTS"
STATE = HOME / ".claude" / "state" / "routine_audit_seen.json"
NOW = datetime.now(timezone.utc)

# name -> Plan, Evidenz-Art, Pfad, Toleranz (Stunden), Notiz
# Toleranz = Plan-Intervall + Puffer; woechentlich => 8 Tage.
CRON_ROUTINES = [
    {"name": "n8n_autoupdate", "plan": "taeglich 04:00", "kind": "append",
     "path": HOME / "n8n_stack/logs/autoupdate.log", "max_h": 30},
    {"name": "weekly_hook_suggest", "plan": "Mo 08:00", "kind": "append",
     "path": HOME / ".claude/logs/weekly_hook_suggest.log", "max_h": 8 * 24},
    {"name": "hook_health_check", "plan": "Mo 07:30", "kind": "append",
     "path": HOME / ".claude/logs/hook_health_cron.log", "max_h": 8 * 24},
    {"name": "weekly_tool_scout", "plan": "Mo 08:30", "kind": "append",
     "path": HOME / ".claude/logs/weekly_tool_scout.log", "max_h": 8 * 24,
     "since": "2026-08-13"},
    {"name": "pipeline_sync_reviewed", "plan": "Mo 06:17", "kind": "append",
     "path": HOME / "n8n_stack/logs/sync_reviewed.log", "max_h": 8 * 24,
     "since": "2026-08-12"},
    {"name": "resolve_unlinked_tools", "plan": "Mo 06:40", "kind": "append",
     "path": HOME / "n8n_stack/logs/resolve_tools.log", "max_h": 8 * 24,
     "since": "2026-08-13"},
    {"name": "pipeline_selfcheck", "plan": "alle 30 min", "kind": "event_only",
     "path": HOME / "n8n_stack/logs/selfcheck.log",
     "note": "--quiet: loggt nur Warnungen, Stille = gesund"},
    {"name": "sweep_watchdog", "plan": "alle 5 min", "kind": "event_only",
     "path": HOME / "n8n_stack/logs/sweep_watchdog.log",
     "note": "loggt nur bei Daemon-Neustart, Stille = Daemon laeuft"},
]

TIMERS = [
    ("claude-rc-watchdog.timer", "alle 5 min", 1),
    ("claude-autoupdate.timer", "taeglich 04:30", 30),
    ("mcp-memory-purge.timer", "taeglich 03:40", 30),
    ("routine-report.timer", "taeglich 08:15", 30),
]


def mtime(p: Path):
    try:
        return datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
    except OSError:
        return None


def age_str(dt: datetime) -> str:
    h = (NOW - dt).total_seconds() / 3600
    return f"{h:.0f}h" if h < 48 else f"{h / 24:.1f}d"


def timer_last(unit: str):
    """LastTriggerUSec eines systemd-user-Timers — harter Beleg, keine Heuristik."""
    try:
        out = subprocess.run(
            ["systemctl", "--user", "show", unit, "-p", "LastTriggerUSec", "--value"],
            capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    if not out or out in ("0", "n/a"):
        return None
    for fmt in ("%a %Y-%m-%d %H:%M:%S %Z", "%a %Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(out, fmt).astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def audit() -> dict:
    ok, overdue, pending, event_only, problems = [], [], [], [], []

    for r in CRON_ROUTINES:
        last = mtime(r["path"])
        if r["kind"] == "event_only":
            event_only.append((r["name"], r["plan"], r.get("note", ""),
                               age_str(last) if last else "nie"))
            continue
        if last is None:
            # Noch nie gelaufen: bei frisch eingerichteten Routinen normal.
            since = r.get("since")
            pending.append((r["name"], r["plan"],
                            f"eingerichtet {since}, erster Lauf steht aus" if since
                            else "Log fehlt — nie gelaufen?"))
            continue
        if (NOW - last) > timedelta(hours=r["max_h"]):
            overdue.append((r["name"], r["plan"], age_str(last)))
        else:
            ok.append((r["name"], r["plan"], age_str(last)))

    for unit, plan, max_h in TIMERS:
        last = timer_last(unit)
        if last is None:
            problems.append((unit, plan, "kein LastTrigger — nie ausgeloest?"))
        elif (NOW - last) > timedelta(hours=max_h):
            overdue.append((unit, plan, age_str(last)))
        else:
            ok.append((unit, plan, age_str(last)))

    return {"ok": ok, "overdue": overdue, "pending": pending,
            "event_only": event_only, "problems": problems}


def new_reports() -> list[Path]:
    """Report-MDs, die seit dem letzten Audit dazugekommen sind."""
    if not REPORTS.is_dir():
        return []
    try:
        seen = set(json.loads(STATE.read_text()).get("seen", []))
    except Exception:
        seen = set()
    found = sorted(p for p in REPORTS.glob("*.md") if p.name not in seen)
    return found


def mark_seen(paths: list[Path]) -> None:
    try:
        seen = set(json.loads(STATE.read_text()).get("seen", []))
    except Exception:
        seen = set()
    seen.update(p.name for p in paths)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"seen": sorted(seen)}, indent=1))


def needs_from(paths: list[Path]) -> list[str]:
    """`## BRAUCHT`-Abschnitte einsammeln — das ist der Teil, der der Nutzer betrifft."""
    out = []
    for p in paths:
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        grab = False
        for ln in lines:
            if ln.strip().lower().startswith("## braucht"):
                grab = True
                continue
            if grab and ln.startswith("## "):
                break
            if grab and ln.strip() and not ln.strip().lower().startswith("_(nichts"):
                out.append(f"{p.stem}: {ln.strip().lstrip('-* ')}")
    return out


def safety_flags() -> list[str]:
    """Sicherheitsnetze, die still ausfallen, wenn eine Datei fehlt.

    Anlass 2026-08-14: `context_threshold_warning.py` hat als erste Zeile ein Gate auf
    ~/.claude/flags/auto_compact_enforce.flag. Die Datei fehlte auf netcup — der Hook
    stieg damit bei JEDEM Prompt sofort aus. Ergebnis: eine Session lief auf 92% ohne
    eine einzige Warnung, seit dem 02.08. Solche Kill-Switch-Dateien synchronisieren
    bewusst nicht (.stignore Zeile 31: /flags), also muss ihr Fehlen auffallen.
    """
    out = []
    flag = Path.home() / ".claude" / "flags" / "auto_compact_enforce.flag"
    if not flag.exists():
        out.append("Context-Warnung AUS — ~/.claude/flags/auto_compact_enforce.flag fehlt "
                   "(Hook beendet sich sofort, keine Compact-Warnung in KEINER Session). "
                   "Fix: touch ~/.claude/flags/auto_compact_enforce.flag")
    return out


def main() -> int:
    res = audit()
    fresh = new_reports()
    needs = needs_from(fresh)
    flags = safety_flags()

    lines = []
    if flags:
        lines.append("SICHERHEITSNETZ:")
        lines += [f"  ! {f}" for f in flags]
    bad = res["overdue"] + res["problems"]
    if bad:
        lines.append(f"ROUTINEN: {len(bad)} auffaellig")
        for n, plan, info in bad:
            lines.append(f"  UEBERFAELLIG {n} ({plan}) — letzter Lauf {info}")
    else:
        lines.append(f"ROUTINEN: alle planmaessig ({len(res['ok'])} geprueft)")
    for n, plan, info in res["pending"]:
        lines.append(f"  WARTET     {n} ({plan}) — {info}")
    if fresh:
        lines.append(f"NEUE REPORTS: {len(fresh)} — " + ", ".join(p.name for p in fresh))
    if needs:
        lines.append("BRAUCHT MARCO:")
        lines += [f"  - {n}" for n in needs]

    print("\n".join(lines))

    if "--write-md" in sys.argv:
        REPORTS.mkdir(parents=True, exist_ok=True)
        md = REPORTS / f"AUDIT_{NOW.astimezone().strftime('%Y-%m-%d')}.md"
        body = [f"# Routine-Audit — {NOW.astimezone().strftime('%Y-%m-%d %H:%M')}", ""]
        for title, rows in (("Planmaessig", res["ok"]), ("Ueberfaellig", res["overdue"]),
                            ("Wartet auf ersten Lauf", res["pending"]),
                            ("Problem", res["problems"])):
            if rows:
                body.append(f"## {title}")
                body += [f"- **{a}** ({b}) — {c}" for a, b, c in rows]
                body.append("")
        if res["event_only"]:
            body.append("## Event-only (Stille = gesund, kein Alarm)")
            body += [f"- **{a}** ({b}) — {d} seit letztem Ereignis · {c}"
                     for a, b, c, d in res["event_only"]]
        md.write_text("\n".join(body) + "\n", encoding="utf-8")
        print(f"\ngeschrieben: {md}")

    if "--mark-seen" in sys.argv:
        mark_seen(fresh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
