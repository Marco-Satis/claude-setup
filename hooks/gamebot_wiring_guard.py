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
import re
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


_BT = re.compile(r"`([^`]+)`")
_IDENT = re.compile(r"^[A-Za-z_][\w.]*$")
_LITERAL = re.compile(r"^[\w.]+\(.*\)$")
_FILE = re.compile(r"[\w./\\-]+\.(?:py|pyw|json|md|txt|flag|bat|ps1|vbs|ya?ml|toml|cfg|ini|png)\b", re.I)


def symbols_of(part: str):
    """Code-Symbole einer (Teil-)Zelle. 16.11.2026 (Befund Survivor.io_Bot): Sammelzellen wie
    `A + B`, `A/B`, `X=7min` und Prosa wurden vorher als EIN Wort verglichen und schuetzten nichts.
    -> [(token, wortgrenze)]; Backtick-Ausdruecke gelten woertlich, Prosa und Allerweltswoerter
    (nur Kleinbuchstaben, ohne _ . Ziffer) fallen weg."""
    out = []
    for m in _BT.finditer(part):
        t = m.group(1).strip()
        if len(t) >= 3:
            out.append((t, bool(_IDENT.match(t))))
    rest = _BT.sub(" ", part)
    for tok in re.split(r"\s+\+\s+|/|=|,\s*|\s+", rest):
        tok = tok.strip().strip(".,;:")
        if len(tok) < 4:
            continue
        if _IDENT.match(tok) and re.search(r"[_.A-Z0-9]", tok):
            out.append((tok, True))
        elif _LITERAL.match(tok):
            out.append((tok, False))
    return out


def ledger(root: Path):
    """[(symbol, wortgrenze, [dateien], ganze_zeile)] aus WIRING.md.
    Sammelzeilen: Teile mit ' ; ', Spalte 1 und 2 in gleicher Reihenfolge."""
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
        fields = [f.strip() for f in s.strip("|").split("|")]
        sym_parts = [p.strip() for p in fields[0].split(" ; ")]
        fil_parts = [p.strip() for p in (fields[1] if len(fields) > 1 else "").split(" ; ")]
        all_files = _FILE.findall(fields[1] if len(fields) > 1 else "")
        for i, part in enumerate(sym_parts):
            if len(fil_parts) == len(sym_parts):
                files = _FILE.findall(fil_parts[i]) or all_files
            else:
                files = all_files
            for tok, wb in symbols_of(part):
                out.append((tok, wb, files, s))
    return out


def applies(files, target: str) -> bool:
    """Ledger-Eintrag ohne Datei gilt ueberall; sonst Basename-Match."""
    if not files:
        return True
    t = target.lower()
    return any(os.path.basename(f.replace("\\", "/")).lower() in t for f in files)


def present(sym: str, wb: bool, text: str) -> bool:
    if not wb:
        return sym in text
    return re.search(r"(?<![\w])" + re.escape(sym) + r"(?![\w])", text) is not None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if not isinstance(data, dict):
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

    entries = [e for e in ledger(root) if applies(e[2], os.path.basename(fp))]
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
    seen = set()
    for sym, wb, _files, line in entries:
        if sym in seen:
            continue
        for old, new in pairs:
            if present(sym, wb, old) and not present(sym, wb, new):
                removed.append((sym, line))
                seen.add(sym)
                break

    if removed:
        msg = [f"BLOCKED wiring-guard: dieser {tool} entfernt "
               f"{len(removed)} in WIRING.md registrierte(s) Symbol(e) aus {fp}."]
        for sym, line in removed[:5]:
            msg.append(f"  * {sym} -> {line[:300]}")
        msg.append("Das ist Absicht, nicht unerklaerter Code. Vor dem Entfernen: "
                   "den genannten Grund widerlegen, `grep` im JOURNAL_*.md nach dem "
                   "Symbol, und erst die Ledger-Zeile loeschen (mit Journal-Eintrag). "
                   "Einmal-Ausnahme: ALLOW-REMOVE in die Ledger-Zeile schreiben.")
        print("\n".join(msg), file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)  # best-effort: eigener Fehler blockt nie
