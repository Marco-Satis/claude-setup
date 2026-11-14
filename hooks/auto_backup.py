#!/usr/bin/env python
"""PreToolUse-Hook (Edit|Write|MultiEdit): Auto-Backup fuer Dateien ohne git.

der Nutzer 2026-11-14 10:46 („1 bis 5 ja“, Punkt 4). Messung REGEL_EINHALTUNG_2026-11-14.md:
52 Edits an bestehenden Dateien hatten weder git noch eine Sicherung (z. B. ~/.claude/scripts/*,
PROGRESS_weapon_db.md). Die Regel „Backup vor Edit“ haengt damit nicht mehr nur an der Disziplin.

Legt `<datei>.bak.auto.<unixzeit>` an (shutil.copy2 = wie `cp -a`), wenn ALLES gilt:
  - die Datei existiert, ist eine normale Datei, <= 20 MB
  - sie liegt unter einer Wurzel, die backup_prune.py abraeumt (netcup: ~/.claude, ~/projects,
    ~/.config/systemd/user, ~/.codex; PC: ~/.claude, ~/.codex, ~/OneDrive/Dokumente,
    C:\\Allgemein_Projektuebergreifend). ACHTUNG seit 14.11. 10:58 (der Nutzer, backup_prune.in_git):
    ausserhalb von git loescht backup_prune nur noch unter ~/.claude; in Projekten ohne git bleiben
    auch die .bak.auto liegen (hoechstens 1 je Datei und Stunde)
  - nicht in Ordnern, die backup_prune auslaesst (.git, node_modules, .venv, plugins, _archive*,
    ~/.claude/backups), nicht im Scratchpad, nicht unter ~/wissen oder dem Temp-Ordner
  - sie ist nicht von git verfolgt (kein Repo, oder im Repo untracked/ignoriert)
  - kein Secret-Ort (.env*, /secrets/, *.pem/*.key, .credentials.json)
  - es gibt kein .bak.auto dieser Datei aus der letzten Stunde
Blockt nie, gibt nichts aus (Log: ~/.claude/logs/auto_backup.log). Jeder Fehler -> exit 0.
Schalter: ~/.claude/flags/auto_backup.off. Tests: hooks/tests/test_auto_backup.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HOME = os.path.expanduser("~")
MAX_BYTES = 20 * 1024 * 1024
ABSTAND = 3600
SKIP_DIRS = {".git", "node_modules", ".stversions", ".venv", "venv", "__pycache__", "plugins"}
SKIP_PREFIX = ("_archive", "_archiv")
SECRET_RE = re.compile(r"(^|[\\/])(\.env[^\\/]*|[^\\/]*\.(pem|key|kdbx)|\.credentials\.json|auth\.json|"
                       r"oauth_creds\.json)$|[\\/]secrets[\\/]", re.I)


def roots() -> list:
    env = os.environ.get("AUTO_BACKUP_ROOTS")
    if env:
        return [r for r in env.split(os.pathsep) if r]
    if os.name == "nt":
        return [os.path.join(HOME, ".claude"), os.path.join(HOME, ".codex"),
                os.path.join(HOME, "OneDrive", "Dokumente"), "C:\\Allgemein_Projektübergreifend"]
    return [os.path.join(HOME, ".claude"), os.path.join(HOME, "projects"),
            os.path.join(HOME, ".config", "systemd", "user"), os.path.join(HOME, ".codex")]


def _norm(p: str) -> str:
    return os.path.normcase(os.path.realpath(p))


def _unter(p: str, root: str) -> bool:
    r = _norm(root)
    return p == r or p.startswith(r.rstrip("\\/") + os.sep)


def ausgeschlossen(path: str, scratchpad: str = "") -> str:
    """-> Grund, warum KEIN Backup, oder '' (dann sichern, sofern nicht git-verfolgt)."""
    p = _norm(path)
    if SECRET_RE.search(path) or SECRET_RE.search(p):
        return "secret"
    if scratchpad and _unter(p, scratchpad):
        return "scratchpad"
    if _unter(p, os.path.join(HOME, "wissen")):
        return "wissen"
    temps = os.environ.get("AUTO_BACKUP_TEMPDIRS")
    temps = [t for t in temps.split(os.pathsep) if t] if temps is not None else \
        [tempfile.gettempdir(), "/tmp", "/var/tmp"]
    for t in temps:
        if t and os.path.isdir(t) and _unter(p, t):
            return "temp"
    rs = [r for r in roots() if r]
    root = next((r for r in rs if _unter(p, r)), None)
    if not root:
        return "ausserhalb backup_prune-Wurzeln"
    rel = os.path.relpath(p, _norm(root))
    teile = rel.split(os.sep)[:-1]
    if any(t in SKIP_DIRS or t.startswith(SKIP_PREFIX) for t in teile):
        return "ausgelassener Ordner"
    if _norm(root) == _norm(os.path.join(HOME, ".claude")) and teile[:1] == ["backups"]:
        return "ausgelassener Ordner"
    if re.search(r"\.bak(?=[.\-_]|$)", os.path.basename(p)):
        return "ist selbst ein Backup"
    return ""


def git_verfolgt(path: str) -> bool:
    d = os.path.dirname(os.path.abspath(path))
    cur = d
    while True:
        if os.path.exists(os.path.join(cur, ".git")):
            break
        nxt = os.path.dirname(cur)
        if nxt == cur:
            return False  # kein Repo
        cur = nxt
    try:
        r = subprocess.run(["git", "-C", d, "ls-files", "--error-unmatch", "--", os.path.basename(path)],
                           capture_output=True, timeout=3)
        return r.returncode == 0
    except Exception:
        return True  # git nicht pruefbar: im Repo -> lieber kein Extra-Backup (Repo ist das Netz)


def juengstes_auto(path: str) -> int:
    best = 0
    for b in glob.glob(glob.escape(path) + ".bak.auto.*"):
        m = re.search(r"\.bak\.auto\.(\d{10})$", b)
        if m:
            best = max(best, int(m.group(1)))
    return best


def _log(msg: str) -> None:
    try:
        lp = os.environ.get("AUTO_BACKUP_LOG") or os.path.join(HOME, ".claude", "logs", "auto_backup.log")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        with open(lp, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except Exception:
        pass


def sichern(path: str, scratchpad: str = "", now: float | None = None) -> str:
    """-> Pfad des neuen Backups oder '' (mit Grund im Rueckgabe-Log)."""
    now = int(now or time.time())
    if not path or not os.path.isfile(path) or os.path.islink(path):
        return ""
    if os.path.getsize(path) > MAX_BYTES:
        return ""
    if ausgeschlossen(path, scratchpad):
        return ""
    if now - juengstes_auto(path) < ABSTAND:
        return ""
    if git_verfolgt(path):
        return ""
    ziel = f"{path}.bak.auto.{now}"
    shutil.copy2(path, ziel)
    _log(f"{ziel}")
    return ziel


def main() -> None:
    for _s in (sys.stdin, sys.stdout, sys.stderr):  # Windows: sonst cp1252 und Umlaute scheitern still
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # leeres/kaputtes JSON: still durchlassen, kein Log-Rauschen
    try:
        if not isinstance(data, dict):
            sys.exit(0)
        if os.path.exists(os.path.join(HOME, ".claude", "flags", "auto_backup.off")):
            sys.exit(0)
        if data.get("tool_name") not in ("Edit", "Write", "MultiEdit", None):
            sys.exit(0)
        ti = data.get("tool_input") or {}
        path = str(ti.get("file_path") or "")
        if path:
            path = os.path.expanduser(path)
            if not os.path.isabs(path) and data.get("cwd"):
                path = os.path.join(str(data["cwd"]), path)
            sichern(path, str(data.get("scratchpad_dir") or ""),
                    float(os.environ["AUTO_BACKUP_JETZT"]) if os.environ.get("AUTO_BACKUP_JETZT") else None)
    except SystemExit:
        raise
    except Exception as ex:
        _log(f"Fehler: {type(ex).__name__}: {str(ex)[:200]}")
    sys.exit(0)


if __name__ == "__main__":
    main()
