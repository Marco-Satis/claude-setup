#!/usr/bin/env python
"""SessionStart Hook: warnt wenn das Memory-DB-Backup veraltet oder fehlgeschlagen ist.

Mitigiert F1/F2 (Review 2026-05-29): backup_memory_db.py kann im pythonw-Autostart
still ausfallen (DB-Lock / OneDrive-offline / Python-Upgrade bricht .bat-Pfad).
Dieser Hook macht den Ausfall beim Session-Start SICHTBAR — Active-Enforcement
statt stillem Daten-Verlust. Warnt wenn:
  - gar kein Backup existiert
  - juengstes Backup > 48h alt (Backup laeuft nicht mehr)
  - backup.log einen FAIL-Eintrag in den letzten 48h hat
Non-blocking (nur systemMessage, exit 0).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKUP_DIR = Path(r"C:\Users\der Nutzer\OneDrive\Backups\mcp-memory")
PREFIX = "sqlite_vec_"
STALE_HOURS = 48


def main() -> None:
    try:
        json.load(sys.stdin)
    except Exception:
        pass  # SessionStart-stdin egal

    msgs: list[str] = []

    try:
        backups = sorted(BACKUP_DIR.glob(f"{PREFIX}*.db"), key=lambda p: p.stat().st_mtime)
    except Exception:
        backups = []

    if not backups:
        msgs.append("kein Memory-DB-Backup gefunden")
    else:
        age_h = (time.time() - backups[-1].stat().st_mtime) / 3600
        if age_h > STALE_HOURS:
            msgs.append(f"juengstes Backup ist {age_h:.0f}h alt (>{STALE_HOURS}h — Autostart-Backup laeuft evtl. nicht)")

    # backup.log auf kuerzlich geloggten FAIL pruefen (F1-Logging)
    log = BACKUP_DIR / "backup.log"
    try:
        if log.exists() and (time.time() - log.stat().st_mtime) / 3600 < STALE_HOURS:
            tail = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-5:]
            fails = [ln for ln in tail if "FAIL" in ln]
            if fails:
                msgs.append(f"Backup-FAIL geloggt: {fails[-1][:80]}")
    except Exception:
        pass

    # Memory-Write-Failures (von session_logger persistiert) sichtbar machen (#3) —
    # Stop-systemMessage geht am Session-Ende verloren, daher SessionStart-Surfacing.
    fail_log = Path.home() / ".claude" / "lessons" / "memory_write_failures.jsonl"
    try:
        if fail_log.exists() and (time.time() - fail_log.stat().st_mtime) / 3600 < STALE_HOURS:
            tail = fail_log.read_text(encoding="utf-8", errors="replace").strip().splitlines()
            if tail:
                msgs.append(f"Memory-Write-Failure (letzte {STALE_HOURS}h): {tail[-1][:90]} — Service down?")
    except Exception:
        pass

    if msgs:
        out = (
            "[BACKUP-HEALTH] " + " | ".join(msgs)
            + " — pruefe `python ~/.claude/scripts/backup_memory_db.py --force` + backup.log"
        )
        print(json.dumps({"systemMessage": out}))


if __name__ == "__main__":
    main()
