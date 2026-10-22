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
    """Gehe von start aufwaerts; gesyncter Root = .stfolder vorhanden (echter Syncthing-
    Ordner) UND .stignore mit 'Syncthing'-Marker. Nur .stignore genuegt nicht: am PC liegt
    in OneDrive\\Dokumente\\Projekte eine alte .stignore ohne Sync (Befund 2026-10-22)."""
    for d in (start, *start.parents):
        sti = d / ".stignore"
        try:
            if ((d / ".stfolder").exists() and sti.is_file()
                    and "syncthing" in sti.read_text(encoding="utf-8", errors="ignore").lower()):
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

    # Ordner `projekte` ist auf netcup sendonly (Stand 2026-10-22): netcup sendet zum PC,
    # Aenderungen vom PC kommen auf netcup NICHT an.
    if root.name.lower() != "projects":
        richtung = ("synct bidirektional PC<->Server via Syncthing (near-realtime) - "
                    "Datei-Aenderungen tauschen automatisch aus")
    elif os.name == "nt":
        richtung = ("synct per Syncthing mit dem Server. ACHTUNG: Der Server nimmt fuer ~/projects "
                    "keine Aenderungen vom PC an (sendonly) - was du hier aenderst, kommt dort nicht an")
    else:
        richtung = ("synct per Syncthing zum PC (dieser Server ist fuer ~/projects sendonly: "
                    "Aenderungen von hier gehen zum PC, Aenderungen vom PC werden hier nicht uebernommen)")
    msg = (
        f"[syncthing] Dieser Ordner ({root}) {richtung}. ABER: .git, Secrets, "
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
