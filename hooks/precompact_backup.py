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
    fp_docs = Path("C:/Users/der Nutzer/OneDrive/Dokumente/AudioSetup/FootstepAnalyzer/docs")
    prompt_opt = Path("C:/Users/der Nutzer/OneDrive/Dokumente/Projekte/Skills_&_Co")

    sources = []
    for directory, pat in [(fp_docs, "STATUS_*.md"), (fp_docs, "BACKLOG_v*.md")]:
        candidate = find_latest(directory, pat) if directory.is_dir() else None
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
        if copied:
            out = {
                "systemMessage": (
                    f"PreCompact-Backup -> {backup_dir} ({len(copied)} Files: "
                    f"{', '.join(copied)})"
                )
            }
            print(json.dumps(out))
    except Exception as e:
        # Niemals den Compact-Flow blockieren
        print(json.dumps({"systemMessage": f"PreCompact-Backup Fehler (ignoriert): {e}"}))


if __name__ == "__main__":
    main()
