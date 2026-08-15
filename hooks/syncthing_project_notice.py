#!/usr/bin/env python
"""SessionStart-Hook: Sync-Status-Hinweis fuer Sessions in Syncthing-gesyncten Ordnern.

der Nutzer 2026-07-15: ~/projects synct seit Increment 2 bidirektional PC<->Server via
Syncthing (near-realtime). Jede Session in einem gesyncten Ordner soll das wissen —
Datei-Aenderungen tauschen automatisch aus, aber .git/Secrets bleiben pro-Seite, und
gleichzeitiges Editieren derselben Datei erzeugt .sync-conflict. Passive Doku wird im
Flow vergessen -> aktiver Hook injiziert es verlaesslich (Active-Enforcement).

Erkennung: vom cwd aufwaerts nach einer .stignore mit dem Marker "Syncthing" suchen
(die gesyncten Roots wie ~/projects/.stignore tragen den). Best-effort: blockt nie
(exit 0), gibt genau ein JSON {"systemMessage"} zurueck oder nichts.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path


def _synced_root(start: Path) -> Path | None:
    """Gehe von start aufwaerts; erste .stignore mit 'Syncthing'-Marker = gesyncter Root."""
    for d in (start, *start.parents):
        sti = d / ".stignore"
        try:
            if sti.is_file() and "syncthing" in sti.read_text(encoding="utf-8", errors="ignore").lower():
                return d
        except Exception:
            continue
    return None


def main() -> None:
    try:
        json.load(sys.stdin)  # SessionStart liefert {source}; wir brauchen nur den cwd
    except Exception:
        sys.exit(0)
    try:
        cwd = Path(os.getcwd())
    except Exception:
        sys.exit(0)

    root = _synced_root(cwd)
    if root is None:
        sys.exit(0)

    msg = (
        f"[syncthing] Dieser Ordner ({root}) synct bidirektional PC<->Server via Syncthing "
        "(near-realtime) - Datei-Aenderungen tauschen automatisch aus. ABER: .git, Secrets, "
        "node_modules und Caches sind vom Sync ausgeschlossen -> git-History/Commits bleiben "
        "pro-Seite (Push/Deploy pro Seite ausfuehren). Nicht dieselbe Datei zeitgleich auf PC "
        "und Server anfassen (sonst .sync-conflict-Dateien). Konflikte pruefen: "
        "find . -name '*.sync-conflict-*'."
    )
    try:
        print(json.dumps({"systemMessage": msg}))
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
