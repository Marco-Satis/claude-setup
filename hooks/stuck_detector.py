#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PostToolUseFailure Hook: Festgefahren-Erkennung -> Pflicht-Websuche.

Zaehlt gleichartige Tool-Fehler pro Session. Ab THRESHOLD identischen
Fehlersignaturen innerhalb WINDOW wird eine harte Anweisung injiziert:
weiterprobieren gestoppt, erst web-researcher-Agent dispatchen.

Motivation (der Nutzer-Entscheid 2026-07-23): beim RC-Ausfall wurde eine falsche
Ursachen-These (OAuth-Race) gebaut und implementiert, statt die Fehlermeldung
nachzuschlagen. Wiederholtes Scheitern an derselben Signatur ist das Signal,
dass Wissen fehlt — nicht dass der naechste Versuch klappt.

Signatur = Tool + normalisierte Fehlermeldung (Zahlen/Pfade/Hex maskiert),
damit "Port 8000 refused" und "Port 8001 refused" als dasselbe Problem zaehlen.

Best-effort: exit 0 immer, bricht NIE die Session.
Kill-Switch: ~/.claude/flags/stuck_detector.off
"""
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

HOME = Path.home()
OFF = HOME / ".claude" / "flags" / "stuck_detector.off"
STATE_DIR = HOME / ".claude" / ".state" / "stuck_detector"
THRESHOLD = int(os.environ.get("CLAUDE_STUCK_THRESHOLD", "3"))
WINDOW = int(os.environ.get("CLAUDE_STUCK_WINDOW", "1800"))     # Zaehler-Reset nach 30 min Ruhe
REARM = int(os.environ.get("CLAUDE_STUCK_REARM", "7200"))       # gleiche Signatur fruehestens nach 2 h erneut
DISTINCT = int(os.environ.get("CLAUDE_STUCK_DISTINCT", "6"))    # verschiedene Fehlschlaege im Fenster


def _norm(err):
    s = err.lower()
    s = re.sub(r"0x[0-9a-f]+", "<hex>", s)
    s = re.sub(r"[a-z]?:?[/\\][\w.\-/\\]+", "<path>", s)
    s = re.sub(r"\d+", "<n>", s)
    return re.sub(r"\s+", " ", s).strip()[:200]


def main():
    if OFF.exists():
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    try:
        tool = str(data.get("tool_name", ""))[:80]
        err = str(data.get("error") or data.get("tool_error")
                  or data.get("reason") or "")[:600]
        if not err:
            sys.exit(0)
        # Permission-/Klassifier-Blocks sind kein Wissensproblem -> ignorieren.
        if re.search(r"permission|blocked by|safety net|denied by|user (denied|rejected)",
                     err, re.I):
            sys.exit(0)

        session = str(data.get("session_id") or "nosession")
        sig = hashlib.sha256((tool + "|" + _norm(err)).encode("utf-8")).hexdigest()[:16]
        sp = STATE_DIR / (hashlib.sha256(session.encode()).hexdigest()[:16] + ".json")
        now = time.time()
        try:
            st = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            st = {}

        rec = st.get(sig) or {}
        if now - float(rec.get("last", 0)) > WINDOW:
            rec = {"n": 0, "fired": 0}
        rec["n"] = int(rec.get("n", 0)) + 1
        rec["last"] = now
        rec["sample"] = err[:200]
        st[sig] = rec
        # alte Signaturen ausduennen
        st = {k: v for k, v in st.items() if now - float(v.get("last", 0)) < WINDOW * 4}
        try:
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(json.dumps(st), encoding="utf-8")
        except Exception:
            pass

        # Ausloeser A: gleiche Signatur wiederholt (im Kreis drehen).
        # Ausloeser B: viele VERSCHIEDENE Fehlschlaege im Fenster (Problem laesst
        # sich nicht loesen, es wird nur breit herumprobiert).
        distinct = sum(1 for k, v in st.items()
                       if not k.startswith("_") and now - float(v.get("last", 0)) < WINDOW)
        last_broad = float(st.get("_broad", {}).get("fired", 0))
        trigger_a = rec["n"] >= THRESHOLD and now - float(rec.get("fired", 0)) > REARM
        trigger_b = distinct >= DISTINCT and now - last_broad > REARM
        if trigger_a or trigger_b:
            if trigger_b:
                st["_broad"] = {"fired": now, "last": now}
            rec["fired"] = now
            st[sig] = rec
            try:
                sp.write_text(json.dumps(st), encoding="utf-8")
            except Exception:
                pass
            why = (f"{rec['n']}x dieselbe Fehlersignatur bei {tool}"
                   if trigger_a else
                   f"{distinct} verschiedene Fehlschlaege im Fenster — das Problem "
                   f"laesst sich so nicht loesen")
            print(json.dumps({"systemMessage":
                f"[FESTGEFAHREN] {why}. Zuletzt: {err[:180]}\n"
                "STOP: keinen weiteren Loesungsversuch aus dem Bauch. Wiederholtes "
                "Scheitern an derselben Signatur heisst, dass Wissen fehlt — nicht, "
                "dass der naechste Versuch klappt.\n"
                "PFLICHT jetzt: Agent-Tool mit subagent_type 'web-researcher' "
                "dispatchen. Im Prompt mitgeben: die woertliche Fehlermeldung, das "
                "eingesetzte Tool/Version, was schon probiert wurde und warum es "
                "scheiterte. Erst nach dem Report weiterarbeiten — und die dortige "
                "Erkenntnis explizit gegen die eigene bisherige These pruefen.\n"
                "Regel: ~/.claude/rules/stuck-research.md"}))
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
