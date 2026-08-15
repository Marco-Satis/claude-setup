#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SessionStart: Gamebot-Grundgeruest-Inventar injizieren + Reuse-first-Reminder.

Zweck: jede Bot-Session startet mit Kenntnis des vorhandenen Werkzeugkastens, damit nicht pro Bot
dieselbe Funktion neu gebaut oder reflexhaft ein anderes System vorgeschlagen wird.

WICHTIG: das geteilte Grundgeruest heisst hier `_botcore/` (NICHT gamebot_core - das existiert nicht).
Discovery 2026-07-24: _botcore hat 17 Module und wird von Survivor_io + IdleSlayer importiert;
CellSurvivor haelt eine eigene core.py-Kopie in bots/. Details: ~/.claude/rules/gamebot-reuse-first.md

Best-effort: exit 0 IMMER, bricht NIE die Session. Feuert nur in Gamebot-Projekten.
"""
import ast
import json
import sys
from pathlib import Path

BOTS = {"cellsurvivor", "survivor_io", "survivorio", "idleslayer", "games"}
CORE_DIRNAME = "_botcore"


def find_core(start: Path):
    """_botcore an oder oberhalb von cwd suchen (Games/ ist der gemeinsame Parent)."""
    for d in [start, *start.parents]:
        c = d / CORE_DIRNAME
        if c.is_dir():
            return c
    return None


def is_gamebot(cwd: Path, core) -> bool:
    names = {cwd.name.lower(), cwd.parent.name.lower()}
    return core is not None or bool(names & BOTS)


def inventory(core: Path):
    """Public-Funktionen + erste Docstring-Zeile je Modul. Rein statisch (ast), kein Import."""
    out = []
    for py in sorted(core.glob("*.py")):
        if py.name.startswith("_"):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        fns = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                doc = (ast.get_docstring(node) or "").strip().splitlines()
                summary = doc[0][:95] if doc else ""
                fns.append(f"    {node.name}() — {summary}" if summary else f"    {node.name}()")
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                doc = (ast.get_docstring(node) or "").strip().splitlines()
                summary = doc[0][:95] if doc else ""
                fns.append(f"    class {node.name} — {summary}" if summary else f"    class {node.name}")
        if fns:
            out.append(f"  {py.name}:")
            out.extend(fns[:8])            # pro Modul deckeln -> Inventar bleibt lesbar
    return out


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    try:
        cwd = Path(str(data.get("cwd") or "."))
        core = find_core(cwd)
        if not is_gamebot(cwd, core):
            sys.exit(0)
        msg = ["[GAMEBOT] Reuse-first: vor Neubau eines Helpers ODER dem Vorschlag eines anderen Systems "
               "erst _botcore/ (Grep) + memory_search Tag `gamebot-framework` pruefen. Eine bessere Methode "
               "nur als geflaggten Tradeoff nennen (Vorteil + Kosten), nie still ersetzen. "
               "Regel: ~/.claude/rules/gamebot-reuse-first.md"]
        if core is not None:
            lines = inventory(core)
            if lines:
                msg.append(f"Geteiltes Grundgeruest ({core}):")
                msg.extend(lines[:70])
            msg.append("Parallel-Sessions: vor Edit an einer fremden Bot-Datei mtime pruefen "
                       "(frisch geaendert = dort arbeitet jemand). _botcore-Edits treffen ALLE Bots.")
        else:
            msg.append("Kein _botcore/ gefunden - Pfad pruefen (erwartet unter Games/).")
        print(json.dumps({"systemMessage": "\n".join(msg)}))
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
