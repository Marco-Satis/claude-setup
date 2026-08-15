#!/usr/bin/env python3
"""rc-trust-guard.py — stellt vor dem RC-Start den Workspace-Trust-Eintrag sicher.

Hintergrund (Incident 2026-08-14): CLI 2.1.232 erzwingt den Trust-Dialog fuer
Workspaces mit Projekt-`.claude/settings.json`. Headless (systemd/RC) kann niemand
den Dialog beantworten -> Crash-Loop (453 Restarts, 2,5 h discord down). Der
Eintrag hatte nie existiert; Ursache war die CLI-Verschaerfung, keine Race
(2.1.229 startete denselben Zustand noch sauber).

Verhalten:
- ergaenzt `projects.<cwd>.hasTrustDialogAccepted: true` in ~/.claude.json,
  falls der Schluessel fehlt oder false ist; sonst no-op
- NUR additiv — bestehende Eintraege und alle fremden Felder bleiben unberuehrt
- flock auf Lock-Datei: die sieben Hosts starten um 04:30 parallel, ohne Lock
  wuerde der Guard selbst eine last-writer-wins-Race einfuehren
- atomar via tempfile + os.replace im selben Verzeichnis (kein halber Write)
- best-effort: JEDER Fehler (kaputtes JSON, Lock-Timeout, ...) -> Meldung auf
  stderr, Exit 0 — der Launcher darf nie am Guard scheitern. Ein defektes
  ~/.claude.json wird NIE ueberschrieben.

Aufruf: rc-trust-guard.py <projekt-dir> [claude-json-pfad]
(zweiter Parameter nur fuer Tests; Default ~/.claude.json)
"""
import json
import os
import sys
import tempfile

# Plattformneutral (PC-Port 2026-08-15): fcntl gibt es nur auf Unix — auf Windows
# scheiterte schon der Import, der Guard war dort unbenutzbar. Unter Windows faellt
# nur der Lock weg; die Race, die er verhindert (sieben parallel startende RC-Hosts
# um 04:30), gibt es ausschliesslich auf netcup. Der atomare Write via tempfile +
# os.replace bleibt auf beiden Plattformen erhalten.
try:
    import fcntl

    def _lock_exclusive(fh):
        fcntl.flock(fh, fcntl.LOCK_EX)
except ImportError:  # Windows
    def _lock_exclusive(fh):
        return None


def main() -> int:
    if len(sys.argv) < 2:
        print("rc-trust-guard: kein Projekt-Verzeichnis uebergeben", file=sys.stderr)
        return 0
    project = os.path.realpath(sys.argv[1])
    cfg_path = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/.claude.json")
    lock_path = cfg_path + ".trustguard.lock"

    try:
        with open(lock_path, "w") as lock:
            # Blockierend mit Alarm-Timeout waere komplexer; die kritische Sektion
            # ist Millisekunden kurz, blockierendes flock reicht.
            _lock_exclusive(lock)

            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError("Top-Level ist kein Objekt")
            projects = data.setdefault("projects", {})
            entry = projects.get(project)
            if isinstance(entry, dict) and entry.get("hasTrustDialogAccepted") is True:
                return 0  # nichts zu tun

            if isinstance(entry, dict):
                entry["hasTrustDialogAccepted"] = True
            else:
                projects[project] = {"hasTrustDialogAccepted": True}

            d = os.path.dirname(cfg_path) or "."
            fd, tmp = tempfile.mkstemp(prefix=".claude.json.trustguard.", dir=d)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, cfg_path)
            except BaseException:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
            print(f"rc-trust-guard: Trust-Eintrag ergaenzt fuer {project}", file=sys.stderr)
    except Exception as exc:  # best-effort: nie den Start blockieren
        print(f"rc-trust-guard: uebersprungen ({exc.__class__.__name__}: {exc})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
