#!/usr/bin/env python3
"""rc-liveness.py — prueft, ob eine RC-Sitzung noch ANTWORTET, nicht ob sie laeuft.

Luecke, die das schliesst (Ausfall 2026-08-17): drei RC-Hosts sind nicht
abgestuerzt, sondern haben stundenlang gehangen. `Restart=always` greift dabei
nicht — der Prozess lebt ja. `rc-watchdog.sh` griff ebenfalls nicht, denn er
prueft `SubState=running` und `NRestarts`; beides sah gesund aus. der Nutzer merkte
es erst, als die Sitzungen in der App nicht mehr reagierten.

Warum nicht ueber das Journal: dort steht kein verwertbares Signal. Gemessen am
17.08. — waehrend des Ausfalls 26 "Reconnecting"-Zeilen in zwei Stunden, im
Normalbetrieb ebenfalls 4–6 je zwei Stunden. Eine Erfolgsmeldung ("connected")
schreibt die CLI gar nicht. Weder Vorhandensein noch Rate unterscheiden also
haengend von arbeitet-gerade-nicht.

Was funktioniert: jede Sitzung haelt einen Unix-Socket unter
/run/user/<uid>/cc-socks/<pid>.sock. Ein Prozess im D-State — genau der Zustand
der eingefrorenen Sitzungen, Wait-Channel `mem_cgroup_handle_over_high` —
nimmt dort keine Verbindung mehr an. Der Socket-Handshake ist damit der
belastbarste verfuegbare Lebendbeweis, und er kostet Millisekunden.

Grenze, die ehrlich benannt gehoert: das erkennt eingefrorene und tote
Sitzungen. Eine Sitzung, deren Prozess gesund ist, deren Transport zur
Gegenstelle aber abgerissen ist, nimmt weiterhin Verbindungen an und gilt hier
als lebendig. Fuer diesen Fall gibt es von aussen kein Signal.

Ausgabe: eine Zeile je Problemfall auf stdout, leer wenn alles antwortet.
Exit 1 bei Befunden, sonst 0 — damit `rc-watchdog.sh` es als Bedingung nutzen
kann. Jeder Fehler in diesem Skript -> Exit 0, kein Fehlalarm aus Defekt.
"""
import os
import socket
import subprocess
import sys

TIMEOUT_S = 5
SOCK_DIR = f"/run/user/{os.getuid()}/cc-socks"


def enabled_hosts():
    try:
        out = subprocess.run(
            ["systemctl", "--user", "list-unit-files", "claude-rc-*.service",
             "--state=enabled", "--no-legend"],
            capture_output=True, text=True, timeout=15,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    hosts = []
    for line in out.splitlines():
        unit = line.split()[0] if line.split() else ""
        if unit and "watchdog" not in unit:
            hosts.append(unit)
    return hosts


def prop(unit, name):
    try:
        return subprocess.run(
            ["systemctl", "--user", "show", unit, "-p", name, "--value"],
            capture_output=True, text=True, timeout=15,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def session_socket(unit):
    """Der eine Prozess im cgroup des Dienstes, der einen Session-Socket haelt."""
    cg = prop(unit, "ControlGroup")
    if not cg:
        return None
    procs = f"/sys/fs/cgroup{cg}/cgroup.procs"
    try:
        with open(procs) as f:
            pids = [p.strip() for p in f if p.strip()]
    except OSError:
        return None
    for pid in pids:
        path = f"{SOCK_DIR}/{pid}.sock"
        if os.path.exists(path):
            return path
    return None


def responds(path):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT_S)
    try:
        s.connect(path)
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except OSError:
            pass


def main() -> int:
    findings = []
    for unit in enabled_hosts():
        if prop(unit, "SubState") != "running":
            continue          # nicht laufend -> das erkennt rc-watchdog.sh bereits
        name = unit.replace("claude-rc-", "").replace(".service", "")
        sock = session_socket(unit)
        if sock is None:
            findings.append(f"{name}: laeuft, hat aber keinen Session-Socket")
        elif not responds(sock):
            findings.append(f"{name}: laeuft, antwortet aber nicht "
                            f"(Socket-Verbindung nach {TIMEOUT_S}s ohne Antwort)")
    for f in findings:
        print(f)
    return 1 if findings else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"rc-liveness: uebersprungen ({exc.__class__.__name__}: {exc})", file=sys.stderr)
        sys.exit(0)
