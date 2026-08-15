#!/usr/bin/env python3
"""SessionStart-Hook: schiebt den Gamebot-Wiring-Ledger aktiv in den Kontext.

der Nutzer 2026-07-25: Push statt Pull. Eine Datei-Konvention ("lies WIRING.md")
scheitert genau dann, wenn das Erinnern schon kaputt ist — nach dem Compact.
SessionStart feuert mit source=compact erneut, also ist das der einzige
verlaessliche Kanal, Verdrahtungswissen in den ersten Post-Compact-Turn zu
bekommen. Klein halten (CAP), sonst frisst es die Loop-Lebensdauer.

Scope: nur Sessions, deren cwd (oder ein Parent) eine LOOP_TICK.md enthaelt.
Best-effort: blockt nie, exit 0 immer.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

MARK = "LOOP_TICK.md"
CAP_WIRING = 4000
CAP_PENDING = 1200
CAP_DEFERRED = 2000
# HANDOVER.md: der ARBEITSSTAND (laufende Untersuchung, geprueft/ausgeschlossen,
# halbfertige Aenderungen, naechster Schritt). WIRING sagt was gebaut IST,
# DEFERRED was geparkt ist — HANDOVER sagt, wo die Session mitten drin steckt.
CAP_HANDOVER = 3000


def bot_dir(start: Path):
    for d in (start, *start.parents):
        try:
            if (d / MARK).is_file():
                return d
        except Exception:
            continue
    return None


def read_cap(p: Path, cap: int) -> str:
    try:
        t = p.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return ""
    return t[:cap] + ("\n… (gekuerzt)" if len(t) > cap else "")


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    try:
        root = bot_dir(Path(data.get("cwd") or os.getcwd()))
    except Exception:
        sys.exit(0)
    if root is None:
        sys.exit(0)

    source = data.get("source") or "?"
    wiring = read_cap(root / "WIRING.md", CAP_WIRING)
    pending = read_cap(root / "WIRING_PENDING.md", CAP_PENDING)
    # DEFERRED.md: Aufgaben, die der Loop ab der MONITOR-ONLY-Schwelle bewusst NICHT
    # begonnen, sondern geparkt hat (context_threshold_warning.py, LOOP_DEFER_THRESHOLD).
    # Ohne Re-Inject waeren sie nach dem Compact vergessen und der Nutzer muesste sie erneut
    # erklaeren — genau das soll die Kette verhindern.
    deferred = read_cap(root / "DEFERRED.md", CAP_DEFERRED)
    handover = read_cap(root / "HANDOVER.md", CAP_HANDOVER)
    if not wiring and not pending and not deferred and not handover:
        sys.exit(0)

    parts = [
        f"[gamebot-wiring] Bot-Verzeichnis {root.name}, SessionStart source={source}.",
        "Was folgt, ist der ZUSTAND der absichtlich gebauten + verdrahteten Teile "
        "dieses Bots. Er ueberlebt Compact, dein Kontext nicht.",
        "HARTE REGELN:",
        "1. Kein Entfernen/Umbauen eines hier gelisteten Symbols, ohne den "
        "genannten Grund vorher zu widerlegen.",
        "2. Code, den du nicht erklaeren kannst, ist NICHT automatisch Muell — "
        "erst `grep` im JOURNAL_*.md nach dem Symbol (kostet keinen Kontext).",
        "3. Neues Fertiges -> eine Zeile in WIRING.md nachtragen (Zustand, nicht Historie).",
    ]
    if wiring:
        parts.append("--- WIRING.md ---\n" + wiring)
    else:
        parts.append("--- WIRING.md fehlt/leer -> anlegen (Schema im Kopf der Datei) ---")
    if pending:
        parts.append("--- WIRING_PENDING.md (vom letzten Compact, abarbeiten) ---\n" + pending)
    if deferred:
        parts.append(
            "--- DEFERRED.md (vor dem Compact bewusst geparkt — JETZT dran) ---\n" + deferred +
            "\nDiese Punkte wurden ab der MONITOR-ONLY-Schwelle absichtlich nicht begonnen, nicht "
            "vergessen. der Nutzer hat sie EINMAL erklaert; frag nicht erneut nach dem Warum. Reihenfolge: "
            "zuerst Bot-Health pruefen, dann diese Liste von oben abarbeiten. Erledigtes hier abhaken "
            "(- [x]) statt die Zeile zu loeschen, damit erkennbar bleibt was schon lief."
        )

    if handover:
        parts.append(
            "--- HANDOVER.md (Arbeitsstand vor dem Compact — HIER weitermachen) ---\n" + handover +
            "\nDas ist der Faden, an dem du gerissen bist. Reihenfolge im ersten Tick nach dem Compact: "
            "(1) Bot-Health, (2) diesen Stand lesen und GENAU an 'NAECHSTER SCHRITT' anknuepfen, "
            "(3) dann DEFERRED.md. Bereits ausgeschlossene Hypothesen NICHT erneut pruefen — sie stehen "
            "mit Beleg da. Halbfertige Aenderungen erst zu Ende bringen oder bewusst zurueckrollen, "
            "nie liegen lassen. HANDOVER.md nach dem Wiederaufsetzen aktualisieren (Zustand, nicht Historie)."
        )

    text = "\n".join(parts)
    try:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": text,
            }
        }))
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
