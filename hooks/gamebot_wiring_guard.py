#!/usr/bin/env python3
"""PreToolUse-Hook: blockt das Entfernen registrierter Gamebot-Symbole.

der Nutzer 2026-07-25: Gamebot-Loop-Sessions laufen unbeaufsichtigt mit Nag aus.
der Nutzer ist meistens nicht am PC und kann nicht "nein, das brauchst du noch"
sagen. Eine Regel in CLAUDE.md driftet ueber Compacts hinweg; ein Hook nicht.
Deshalb mechanischer Backstop: verschwindet ein in WIRING.md registriertes
Symbol durch einen Edit, blockt der Hook mit der Begruendungszeile aus dem
Ledger — die Session liest also genau das Wissen, das ihr der Compact nahm.

Praezedenzfall: 2026-06-16 wurde der Direkt-Start in _bots_control.py
entfernt ("Dup-Loop-Race") -> Cold-Boot startete die Bots gar nicht.

Notausgaenge:
  * Ledger-Zeile enthaelt das Wort ALLOW-REMOVE -> Symbol wird ignoriert.
  * Datei Games/.wiring_guard.off (neben LOOP_TICK.md) -> Guard aus.
  * Legitimes Entfernen: erst die Ledger-Zeile loeschen, dann den Code.

Best-effort: jeder unerwartete Fehler -> exit 0. Block: stderr + exit 2.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

MARK = "LOOP_TICK.md"
OFF = ".wiring_guard.off"
TOOLS = {"Edit", "Write", "MultiEdit"}


def bot_dir(start: Path):
    for d in (start, *start.parents):
        try:
            if (d / MARK).is_file():
                return d
        except Exception:
            continue
    return None


def ledger(root: Path):
    """[(symbol, datei_feld, ganze_zeile)] aus WIRING.md."""
    out = []
    try:
        raw = (root / "WIRING.md").read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return out
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "ALLOW-REMOVE" in s:
            continue
        if "|" not in s:
            continue
        fields = [f.strip() for f in s.split("|")]
        sym = fields[0]
        fil = fields[1] if len(fields) > 1 else ""
        if len(sym) < 3:          # zu kurz = zu viele Fehltreffer
            continue
        out.append((sym, fil, s))
    return out


def applies(fil: str, target: str) -> bool:
    """Ledger-Zeile ohne Datei-Feld gilt ueberall; sonst Basename-Match."""
    if not fil:
        return True
    return os.path.basename(fil).lower() in target.lower()


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool = data.get("tool_name")
    if tool not in TOOLS:
        sys.exit(0)
    ti = data.get("tool_input") or {}
    fp = ti.get("file_path") or ""
    if not fp:
        sys.exit(0)

    try:
        root = bot_dir(Path(fp).parent) or bot_dir(Path(data.get("cwd") or os.getcwd()))
    except Exception:
        sys.exit(0)
    if root is None or (root / OFF).exists():
        sys.exit(0)

    entries = [e for e in ledger(root) if applies(e[1], os.path.basename(fp))]
    if not entries:
        sys.exit(0)

    pairs = []   # (alt_text, neu_text)
    if tool == "Edit":
        pairs.append((ti.get("old_string") or "", ti.get("new_string") or ""))
    elif tool == "MultiEdit":
        for e in ti.get("edits") or []:
            if isinstance(e, dict):
                pairs.append((e.get("old_string") or "", e.get("new_string") or ""))
    elif tool == "Write":
        try:
            cur = Path(fp).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            cur = ""
        if not cur:
            sys.exit(0)          # neue Datei -> nichts zu schuetzen
        pairs.append((cur, ti.get("content") or ""))

    removed = []
    for sym, _fil, line in entries:
        for old, new in pairs:
            if sym in old and sym not in new:
                removed.append((sym, line))
                break

    if removed:
        msg = [f"BLOCKED wiring-guard: dieser {tool} entfernt "
               f"{len(removed)} in WIRING.md registrierte(s) Symbol(e) aus {fp}."]
        for sym, line in removed[:5]:
            msg.append(f"  * {sym} -> {line}")
        msg.append("Das ist Absicht, nicht unerklaerter Code. Vor dem Entfernen: "
                   "den genannten Grund widerlegen, `grep` im JOURNAL_*.md nach dem "
                   "Symbol, und erst die Ledger-Zeile loeschen (mit Journal-Eintrag). "
                   "Einmal-Ausnahme: ALLOW-REMOVE in die Ledger-Zeile schreiben.")
        print("\n".join(msg), file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
