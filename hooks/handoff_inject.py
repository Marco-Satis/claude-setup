#!/usr/bin/env python3
"""SessionStart-Hook: ungelesene Handoffs im Arbeitsverzeichnis melden.

Anlass (2026-08-20, Problem p-268067c187): Die PC-Session legte um 06:55 einen
Handoff zum naechtlichen Auth-Ausfall in das Arbeitsverzeichnis dieser Session —
den etablierten Kanal, weil `SendMessage` in diese Richtung nicht zustellt. Die
Datei lag korrekt da und erreichte trotzdem niemanden: `memory_delta_watch.py`
haengt allein am Event **UserPromptSubmit**, eine frisch gestartete Session pollt
also nie von selbst, und ihr eigenes cwd liest sie ohnehin nicht. Gemerkt hat es
erst der Nutzer, der nachfragte.

Der Hook schliesst genau diese Luecke: Er nennt beim Session-Start die
`HANDOFF_*`-, `AKTION_*`- und `LIES_MICH_*`-Dateien im Projektverzeichnis, die
seit ihrer letzten Aenderung noch nicht gelesen wurden.

Bewusste Entscheidungen:

* **Nur Dateinamen und erste Zeile, nicht der Inhalt.** Ein vollstaendiger
  Handoff kostet leicht 5.000 Tokens; drei davon vergiften den Kontext jeder
  Session, auch wenn keiner sie betrifft. Die Session liest gezielt nach.
* **Gelesen-Zustand ueber mtime, nicht ueber ein Flag.** Wird eine Datei
  ergaenzt — wie AKTION_PC_JETZT heute dreimal —, gilt sie wieder als ungelesen.
  Ein einmal gesetztes Flag haette den Nachtrag verschluckt.
* **Alter begrenzt (14 Tage).** Das Verzeichnis enthaelt Handoffs bis zurueck in
  den Juni. Ohne Grenze meldet der Hook bei jedem Start ein Archiv.
* **Best effort.** Faellt er aus, startet die Session trotzdem: jede Ausnahme
  wird geschluckt, Exit immer 0.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

STATE = Path.home() / ".claude" / "state" / "handoff_seen.json"
MUSTER = ("HANDOFF_", "AKTION_", "LIES_MICH_", "OFFENE_FRAGEN_")
MAX_ALTER_TAGE = 14
MAX_MELDUNGEN = 6


def erste_zeile(p: Path) -> str:
    try:
        with p.open(encoding="utf-8", errors="replace") as fh:
            for zeile in fh:
                z = zeile.strip().lstrip("# ").strip()
                if z:
                    return z[:110]
    except OSError:
        pass
    return ""


def main() -> int:
    try:
        roh = sys.stdin.read()
        daten = json.loads(roh) if roh.strip() else {}
    except Exception:
        daten = {}

    cwd = Path(daten.get("cwd") or os.getcwd())
    if not cwd.is_dir():
        return 0

    try:
        zustand = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        zustand = {}

    jetzt = time.time()
    neu = []
    for p in sorted(cwd.glob("*.md")):
        if not p.name.startswith(MUSTER):
            continue
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if (jetzt - mtime) > MAX_ALTER_TAGE * 86400:
            continue
        # "erledigt" = bewusst abgeschlossen, nicht mehr melden. Der Marker steht
        # mal im Dateinamen, mal in der Ueberschrift ("PC-Aktion — ERLEDIGT,
        # nichts mehr zu tun") — beides pruefen.
        if "erledigt" in p.name.lower() or "erledigt" in erste_zeile(p).lower():
            continue
        if zustand.get(p.name, 0) >= mtime:
            continue
        neu.append((mtime, p))

    if not neu:
        return 0

    neu.sort(reverse=True)
    zeilen = []
    for i, (mtime, p) in enumerate(neu):
        # ALLE als gesehen vermerken, auch die nicht angezeigten. Sonst meldet der
        # naechste Start brav die naechsten sechs — im Test kam so aus einem
        # Hinweis eine dreiteilige Serie (2026-08-20).
        zustand[p.name] = mtime
        if i >= MAX_MELDUNGEN:
            continue
        alter_h = (jetzt - mtime) / 3600
        wann = f"{alter_h:.0f} h alt" if alter_h < 48 else f"{alter_h/24:.0f} Tage alt"
        kopf = erste_zeile(p)
        zeilen.append(f"  · {p.name} ({wann}){' — ' + kopf if kopf else ''}")

    if len(neu) > MAX_MELDUNGEN:
        zeilen.append(f"  · … und {len(neu) - MAX_MELDUNGEN} weitere")

    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(zustand, indent=1, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # Melden ist wichtiger als Merken

    text = (
        f"UNGELESENE HANDOFFS in {cwd}:\n" + "\n".join(zeilen) +
        "\n\nDiese Dateien sind der Kanal zwischen den Sessions (SendMessage stellt "
        "zwischen PC und Server nicht zu). Lies die relevanten, bevor du weiterarbeitest."
    )
    print(json.dumps({"systemMessage": text}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
