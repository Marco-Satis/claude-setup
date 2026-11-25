#!/usr/bin/env python
"""PreCompact Hook: Backup juengstes STATUS + Review-Master + Backlog vor Compact.

Findet die jeweils juengsten Files dynamisch via glob (statt hartkodierter
Datums-Pfade, die mit jedem neuen Snapshot veralten). Retention: behaelt
nur die letzten 7 precompact_*-Ordner, aelteres wird geloescht.
"""
import json
import os
import shutil
import time
from pathlib import Path


def find_latest(directory, pattern):
    """Finde das juengste File matching pattern im directory."""
    try:
        matches = sorted(
            directory.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return matches[0] if matches else None
    except Exception:
        return None


def main():
    home = Path(os.path.expanduser("~"))
    ts = int(time.time())
    backups_root = home / ".claude" / "backups"
    backup_dir = backups_root / f"precompact_{ts}"

    # Dynamisch jeweils juengstes Status / Backlog / Review-Report finden
    if os.name == "nt":
        fp_docs = Path("C:/Users/der Nutzer/AudioSetup/FootstepAnalyzer/docs")  # seit 17.11.2026 ausserhalb von OneDrive
        # Seit 17.11.2026 (Phase 4 Stufe 4) ist die projects-sync-Kopie der Arbeitsordner, die OneDrive-Kopie heisst _ALT.
        prompt_opt = Path("C:/Users/der Nutzer/projects-sync/Skills_&_Co")
        quellordner = (fp_docs, prompt_opt)
    else:
        # netcup (25.11.2026): FootstepAnalyzer liegt nur am PC; Skills_&_Co unter ~/projects. Vorher meldete K4 bei
        # jedem Compact auf netcup beide PC-Pfade als fehlend (Fehlalarm).
        fp_docs = None
        prompt_opt = home / "projects" / "Skills_&_Co"
        quellordner = (prompt_opt,)

    sources = []
    for directory, pat in [(fp_docs, "STATUS_*.md"), (fp_docs, "BACKLOG_v*.md")]:
        candidate = find_latest(directory, pat) if directory is not None and directory.is_dir() else None
        if candidate:
            sources.append(candidate)
    if prompt_opt.is_dir():
        try:
            # rglob: Review-Master liegen seit Reorg verschachtelt
            # (_archiv/reviews_historisch/REVIEW_*/REVIEW_REPORT_MASTER*.md) statt
            # in REVIEW_20*-*-Top-Level-Ordnern -> rekursiv juengsten Master nehmen.
            masters = sorted(
                prompt_opt.rglob("REVIEW_REPORT_MASTER*.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except Exception:
            masters = []
        if masters:
            sources.append(masters[0])

    # SEC-003 (2026-05-16): Setup-Config-Files auch sichern.
    # Falls der Nutzer Skill/Settings/Hook aendert und /compact triggert, muss
    # ein PreCompact-Snapshot der wichtigsten ~/.claude/-Files verfuegbar sein.
    setup_critical = [
        home / ".claude" / "CLAUDE.md",
        home / ".claude" / "settings.json",
        home / ".claude" / "rules" / "secret-handling.md",
        home / ".claude" / "skills" / "lyra" / "SKILL.md",
        home / ".claude" / "skills" / "review" / "SKILL.md",
    ]
    sources.extend(p for p in setup_critical if p.exists())

    copied = []
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        for src in sources:
            if src.exists():
                shutil.copy2(src, backup_dir / src.name)
                copied.append(src.name)
        # Retention: nur die letzten 7 precompact_*-Ordner behalten
        try:
            all_backups = sorted(
                backups_root.glob("precompact_*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for old in all_backups[7:]:
                shutil.rmtree(old, ignore_errors=True)
        except Exception:
            pass  # Retention darf den Backup-Flow nicht stoeren
        # K4 (Umzugsplan 16.11.): fehlende Quellordner melden statt still uebergehen
        fehlt = [str(d) for d in quellordner if not d.is_dir()]
        if copied or fehlt:
            msg = f"PreCompact-Backup -> {backup_dir} ({len(copied)} Files: {', '.join(copied)})"
            if fehlt:
                msg += f" | [K4] Quellordner fehlt: {'; '.join(fehlt)} - Pfad in hooks/precompact_backup.py nachziehen"
            print(json.dumps({"systemMessage": msg}))
    except Exception as e:
        # Niemals den Compact-Flow blockieren
        print(json.dumps({"systemMessage": f"PreCompact-Backup Fehler (ignoriert): {e}"}))


if __name__ == "__main__":
    main()
