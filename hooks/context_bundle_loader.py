#!/usr/bin/env python
"""SessionStart-Hook: injiziert einen Index der Projekt-Wissens-Bundles.

Teil der Worktree-Migration (2026-06-02): jedes Projekt-Verzeichnis hat einen
`context/`-Ordner mit Wissens-Bundles (_core-knowledge.md + Topic-Bundles), die
beim Session-Start aus dem Memory-Korpus erzeugt wurden. Dieser Hook macht sie der
Session bewusst — OHNE den Volltext zu dumpen (Token-Hygiene). Claude liest das
relevante Bundle bei Bedarf via Read.

Sucht `context/` ab cwd aufwärts (max 4 Ebenen) — funktioniert auch wenn die
Session in einem Unterordner/Worktree startet. Leise wenn kein context/ gefunden.

Input: SessionStart-Hook-JSON via stdin (Feld `cwd`). Output: stdout-Text wird als
Session-Kontext injiziert.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:  # Windows-cp1252-Safety: Hook-stdout auf UTF-8 (Emoji/→/•)
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

MAX_UP = 4
# PII-Umzug (p-8e628d7b4d): OneDrive-Projekte legen ihre Bundles NICHT mehr in den (cloud-
# synchronisierten) context/-Ordner, sondern in einen lokalen Mirror. Im context/ liegt dann nur
# diese PII-freie Pointer-Datei mit dem lokalen Bundle-Pfad, dem dieser Loader folgt.
REDIRECT_NAME = ".bundle_redirect"


def find_context_dir(start: Path) -> Path | None:
    cur = start.resolve()
    for _ in range(MAX_UP + 1):
        cand = cur / "context"
        # gueltig wenn Bundles direkt drinliegen ODER ein Redirect-Pointer (OneDrive-Umzug)
        if cand.is_dir() and (any(cand.glob("*.md")) or (cand / REDIRECT_NAME).is_file()):
            return cand
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def resolve_bundle_dir(ctx: Path) -> Path:
    """Folgt einer .bundle_redirect-Pointer-Datei auf den lokalen (nicht-OneDrive) Bundle-Pfad.

    Ohne Pointer (Nicht-OneDrive-Projekte) unveraendert: die Bundles liegen direkt in ctx.
    """
    rf = ctx / REDIRECT_NAME
    if rf.is_file():
        try:
            target = Path(rf.read_text(encoding="utf-8").strip())
            if target.is_dir():
                return target
        except Exception:
            pass
    return ctx


def count_items(md: Path) -> int:
    """Anzahl Memory-Einträge im Bundle (Entry-Header `## [type] ...`)."""
    try:
        return sum(1 for ln in md.read_text(encoding="utf-8", errors="replace").splitlines()
                   if ln.startswith("## ["))
    except Exception:
        return 0


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    cwd = Path(data.get("cwd") or ".")
    ctx = find_context_dir(cwd)
    if not ctx:
        return 0  # leise — Projekt hat (noch) keine Bundles

    bundle_dir = resolve_bundle_dir(ctx)  # OneDrive-Projekte: Bundles liegen lokal (Redirect)
    bundles = sorted(bundle_dir.glob("*.md"))
    if not bundles:
        return 0

    lines = [f"📚 Projekt-Wissens-Bundles verfügbar in {bundle_dir} (bei Bedarf via Read laden):"]
    # _core-knowledge zuerst, dann Topics nach Größe
    core = [b for b in bundles if b.stem.startswith("_")]
    topics = sorted((b for b in bundles if not b.stem.startswith("_")),
                    key=lambda b: -count_items(b))
    for b in core + topics:
        n = count_items(b)
        label = "Cross-Cutting (Lessons/Decisions/global)" if b.stem.startswith("_") else b.stem
        lines.append(f"  • {b.name} — {n} Memories — {label}")
    lines.append("→ Enthält gesichertes Wissen aus früheren Sessions. Lies das passende "
                 "Bundle wenn ein Thema Vorwissen braucht.")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
