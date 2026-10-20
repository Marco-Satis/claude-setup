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
    {"name": "exposure_watch", "plan": "taeglich 07:25", "kind": "append",
     "path": HOME / ".claude/logs/exposure_watch.log", "max_h": 30,
     "since": "2026-08-17"},
    {"name": "weekly_hook_suggest", "plan": "Mo 08:00", "kind": "append",
     "path": HOME / ".claude/logs/weekly_hook_suggest.log", "max_h": 8 * 24},
    # 2026-10-01 auf Meldung der Allgemein-Session (der Nutzer-Auftrag): befristet bis 14.11.,
    # danach beendet sich das Skript still -> "until" blendet die Routine im Audit aus.
    {"name": "therme_deal_check", "plan": "taeglich 09:00", "kind": "append",
     "path": HOME / "general/routinen/therme_deal_check.log", "max_h": 30,
     "since": "2026-10-01", "until": "2026-11-14"},
    {"name": "weekly_transcript_dreamer", "plan": "So 04:50", "kind": "append",
     "path": HOME / ".claude/logs/weekly_transcript_dreamer.log", "max_h": 8 * 24,
     "since": "2026-10-01"},
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
    {"name": "scraper_health", "plan": "Mi 07:05", "kind": "append",
     "path": HOME / "n8n_stack/logs/scraper_health.log", "max_h": 8 * 24,
     "since": "2026-08-17",
     "note": "prueft nach, ob die Scraper-Fixes a4bf740/cb9d9fe halten "
             "(0-URL-Quote und EPIPE gegen die Ausgangslage 62 % / 3 in 5 Tagen)"},
    {"name": "graphify_doku_staleness", "plan": "Mo 07:45", "kind": "append",
     "path": HOME / ".claude/logs/graphify_doku_staleness.log", "max_h": 8 * 24,
     "since": "2026-08-19",
     "note": "prueft Alter, geaenderte Korpus-Dateien und Geisterquellen des "
             "Doku-Graphen sowie den HTTP-Dienst dahinter (Anlass: Graph war 66 "
             "Tage alt, GraphifyRefresh pflegt einen anderen Graphen)"},
    {"name": "memory_pressure_watch", "plan": "alle 5 min", "kind": "event_only",
     "path": HOME / ".claude/logs/memory_pressure.log",
     "note": "meldet nur bei Druck; Stille = Slice unter der Drossel"},
    {"name": "pipeline_selfcheck", "plan": "alle 30 min", "kind": "event_only",
     "path": HOME / "n8n_stack/logs/selfcheck.log",
     "note": "--quiet: loggt nur Warnungen, Stille = gesund"},
    {"name": "lyra_weekly_check", "plan": "Mo 09:00", "kind": "append",
     "path": HOME / ".claude/logs/lyra_weekly_check.log", "max_h": 8 * 24,
     "since": "2026-08-25",
     "note": "vom PC uebernommen. Recherchiert zwei Pflicht-Fenster (Anthropic + "
             "OpenAI/Codex) und wendet Edits ab Konfidenz MITTEL auf den Lyra-Skill "
             "an; Bericht in LYRA_WEEKLY/. Als Desktop-Aufgabe fiel sie zweimal "
             "unbemerkt aus, weil eine solche Routine ihren Ausfall nicht meldet"},
    {"name": "memory_consolidate", "plan": "taeglich 02:30", "kind": "append",
     "path": HOME / ".claude/state/mcp-memory/consolidation_runner.log", "max_h": 30,
     "since": "2026-08-25",
     "note": "vom PC uebernommen (Desktop-Aufgabe dort abgeschaltet). Loggt jede "
             "faellige Stufe; daily ist taeglich faellig, deshalb append. Zwei "
             "Ausloeser wuerden die Kadenz-Sperre gegenseitig aushebeln"},
    {"name": "routine_selbstpruefung", "plan": "So 07:50", "kind": "event_only",
     "path": HOME / ".claude/logs/routine_selbstpruefung.log",
     "note": "prueft die Verdrahtung aller Routinen inklusive der eigenen; Stille = "
             "nichts verrutscht. Selbsteinschluss statt zweiter Aufsichtsebene — eine "
             "Aufsicht ueber die Aufsicht waere ein unendlicher Regress"},
    {"name": "mcp_log_secret_purge", "plan": "taeglich 07:35", "kind": "event_only",
     "path": HOME / ".claude/logs/mcp_log_secret_purge.log",
     "note": "raeumt MCP-Debug-Logs weg, die X-API-Key/Bearer im Klartext enthalten; "
             "Stille = nichts gefunden. Angelegt 2026-08-23, weil die eingebaute "
             "Bereinigung nur in gestarteten Projekten greift und in ruhenden Ordnern "
             "Schluessel seit dem 09.07. lagen"},
    {"name": "memory_liveness", "plan": "alle 5 min", "kind": "event_only",
     "path": HOME / ".claude/logs/memory_liveness.log",
     "note": "echter HTTP-Request gegen /api/health statt is-active; Stille = Dienst "
             "antwortet. Zwei Fehlschlaege in Folge loesen einen py-spy-Stack-Dump aus "
             "(Anlass: 74-min-Blockade am 18.08., Unit meldete durchgehend active)"},
    {"name": "memory_outbox_flush", "plan": "taeglich 07:23", "kind": "event_only",
     "path": HOME / ".claude/logs/memory_outbox_flush.log",
     "note": "reicht gepufferte Memory-Payloads nach; Stille = Puffer war leer. "
             "Angelegt 2026-08-20, weil der Flusher auf netcup keinen Aufrufer hatte "
             "(die Routine dazu laeuft nur auf dem PC, ~/.claude/state synct nicht) "
             "und 67 Payloads seit dem 14.07. mit attempts=0 liegenblieben"},
    {"name": "sweep_watchdog", "plan": "alle 5 min", "kind": "event_only",
     "path": HOME / "n8n_stack/logs/sweep_watchdog.log",
     "note": "loggt nur bei Daemon-Neustart, Stille = Daemon laeuft"},
    {"name": "agent_msg_notify", "plan": "alle 10 min", "kind": "event_only",
     "path": HOME / ".claude/logs/agent_msg_notify.log",
     "note": "loggt nur, wenn Codex-Nachrichten >10 min unabgeholt sind (seit 2026-09-29)"},
    {"name": "codex_rc_watch", "plan": "taeglich 08:40", "kind": "append",
     "path": HOME / ".claude/logs/codex_rc_watch.log", "max_h": 30, "since": "2026-09-29"},
    # 2026-10-18 auf Meldung der Trading-Session: Paper-Trading-Bot (~/projects/Trading).
    # Alle drei teilen ein monatlich rotiertes Log -> Beleg ist der eigene Report je Routine.
    {"name": "trading_crypto", "plan": "taeglich 08:00+20:00", "kind": "append",
     "path": REPORTS / "trading_crypto_*.md", "max_h": 30, "since": "2026-10-19"},
    {"name": "trading_stocks", "plan": "Mo-Fr 16:00+20:45", "kind": "append",
     "path": REPORTS / "trading_stocks_*.md", "max_h": 4 * 24, "since": "2026-10-19",
     "note": "4 Tage Toleranz, damit Wochenende plus ein Feiertag keinen Alarm ausloesen"},
    {"name": "trading_review", "plan": "Fr 22:30", "kind": "append",
     "path": REPORTS / "trading_review_*.md", "max_h": 8 * 24, "since": "2026-10-23"},
    {"name": "codex_zombie_guard", "plan": "alle 15 min", "kind": "event_only",
     "path": HOME / ".claude/logs/codex_zombie_guard.log",
     "note": "loggt nur bei >500 Zombies unter dem Codex-app-server (Bug #43256) + Neustart"},
]

TIMERS = [
    ("claude-rc-watchdog.timer", "alle 5 min", 1),
    # 2026-08-25 nachgetragen: beide liefen seit Tagen, standen aber in keiner
    # Registrierung — gefunden von routine_selbstpruefung.py beim ersten Lauf.
    # Genau der Fall, den sie abdecken soll: eine Routine, die niemandem fehlt.
    ("host-memory-watch.timer", "alle 10 min", 1),
    ("mcp-memory-watch.timer", "alle 10 min", 1),
    ("claude-autoupdate.timer", "taeglich 04:30", 30),
    ("mcp-memory-purge.timer", "taeglich 03:40", 30),
    ("routine-report.timer", "taeglich 08:15", 30),
    # 2026-10-01 auf Meldung der Discord_Bots-Session (der Nutzer-Entscheid 29.09.): System-Timer,
    # nicht --user. Skript /usr/local/sbin/weekly-apt-upgrade schreibt den Report selbst.
    ("weekly-apt-upgrade.timer", "Mo 05:00", 8 * 24, "system"),
]


def mtime(p: Path):
    # Glob im Dateinamen (z. B. trading_crypto_*.md): juengster Treffer zaehlt.
    if "*" in p.name:
        hits = [m for m in (mtime(q) for q in p.parent.glob(p.name)) if m]
        return max(hits) if hits else None
    try:
        return datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
    except OSError:
        return None


def age_str(dt: datetime) -> str:
    h = (NOW - dt).total_seconds() / 3600
    return f"{h:.0f}h" if h < 48 else f"{h / 24:.1f}d"


def _show(unit: str, prop: str, scope: str = "user") -> str:
    try:
        return subprocess.run(
            ["systemctl"] + (["--user"] if scope == "user" else []) + ["show", unit, "-p", prop, "--value"],
            capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _parse_ts(out: str):
    if not out or out in ("0", "n/a"):
        return None
    for fmt in ("%a %Y-%m-%d %H:%M:%S %Z", "%a %Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(out, fmt).astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def timer_last(unit: str, scope: str = "user"):
    """LastTriggerUSec eines systemd-user-Timers — harter Beleg, keine Heuristik.

    Fallback (2026-09-29): Nach Reboot/daemon-reload ist LastTriggerUSec bei nicht-persistenten
    Timern zeitweise leer, obwohl der Dienst regelmaessig lief. Folge war ein Fehlalarm
    "nie ausgeloest?" fuer claude-rc-watchdog + mcp-memory-watch, waehrend das Journal
    Laeufe alle 5 min zeigte. Dann zaehlt der letzte Start des ausgeloesten Dienstes.
    """
    last = _parse_ts(_show(unit, "LastTriggerUSec", scope))
    if last is not None:
        return last
    service = _show(unit, "Unit", scope) or unit.replace(".timer", ".service")
    return _parse_ts(_show(service, "ExecMainStartTimestamp", scope))


def audit() -> dict:
    ok, overdue, pending, event_only, problems = [], [], [], [], []

    for r in CRON_ROUTINES:
        # Befristete Routine nach Ablauf nicht mehr pruefen (Cron-Zeile dann entfernen).
        if r.get("until") and NOW.date().isoformat() > r["until"]:
            continue
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

    for unit, plan, max_h, *scope in TIMERS:
        last = timer_last(unit, scope[0] if scope else "user")
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
    if "--mark-seen-only" in sys.argv:
        # Billiger Pfad fuer den SessionStart-Hook: nur die Report-Liste als
        # gesehen vermerken, ohne die systemctl-Abfragen des vollen Audits.
        # Getrennt vom `--mark-seen`-Flag, weil der Hook erst markieren darf,
        # NACHDEM er den Digest ausgegeben hat — sonst verbraucht eine Session,
        # die den Text nie zu sehen bekommt, ihn trotzdem.
        mark_seen(new_reports())
        return 0

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
