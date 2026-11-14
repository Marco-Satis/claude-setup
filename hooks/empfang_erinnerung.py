#!/usr/bin/env python
"""Stop-Hook: Erinnerung an die Empfangsbestaetigung (rules/session-disziplin.md, „Empfang bestaetigen“).

der Nutzer 2026-11-14 10:46 („1 bis 5 ja“, Punkt 5). Messung REGEL_EINHALTUNG_2026-11-14.md: Setup Server
beantwortete nur 7 von 22 Auftraegen/Fragen anderer Sessions binnen 30 min mit einer Zeile an den
Absender; fuer den Absender sieht das wie „nicht angekommen“ aus.

Am Zugende liest der Hook das Transkript (nur die letzten ~3 MB): Kam in den letzten 45 min eine
`<cross-session-message from=… from-name=…>` mit Frage oder Auftrag, und danach ging kein
SendMessage an diesen Absender (`to` = from oder from-name), gibt er EINEN Hinweis:
  - `systemMessage` (sichtbar fuer der Nutzer) und `additionalContext` (Claude sieht ihn und kann die
    Quittung im selben Zug nachholen). Kein `decision: block`, kein Fehler.
  - hoechstens einmal je Nachricht (Merkliste ~/.claude/state/empfang_erinnerung/<session>.json),
    nie bei `stop_hook_active` -> keine Schleife.
Ausgenommen (wie in der Messung): reine Quittungen („Empfangen:“, „Erledigt:“, „OK“, „Danke“),
Ergebnis-/Abschlussmeldungen, geplante „ARBEITSBLOCK“-Anstoesse, Texte ohne Frage-/Auftragsmerkmal.
Best-effort: jeder Fehler -> exit 0, keine Ausgabe. Schalter: ~/.claude/flags/empfang_erinnerung.off.
Tests: hooks/tests/test_empfang_erinnerung.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

HOME = Path.home()
STATE = Path(os.environ.get("EMPFANG_STATE") or HOME / ".claude" / "state" / "empfang_erinnerung")
FLAG_OFF = HOME / ".claude" / "flags" / "empfang_erinnerung.off"
FENSTER = 45 * 60
TAIL_BYTES = 3 * 1024 * 1024

CROSS = re.compile(r"<cross-session-message\b([^>]*)>(.*?)(?:</cross-session-message>|$)", re.S)
ATTR = re.compile(r'([\w-]+)="([^"]*)"')
TASKY = re.compile(r"\?|\bbitte\b|\bkannst\b|\bkönntest\b|\bsoll(?:st)?\b|\bprüf|\bmach\b|\bschick|\bmelde\b|"
                   r"\bantworte|\bzieh\b|\bnachziehen\b|\bübernimm|\bbaue?\b|\bfix", re.I)
QUIT = re.compile(r"^\s*(Empfangen:|Erledigt:|Quittung|OK\b|Danke)", re.I)
ERGEBNIS = re.compile(r"^(Ergebnis|MB\d+ erledigt|G\d+ erledigt|Nachtbetrieb quittiert|"
                      r"[\w ._-]{0,30}: Nachtbetrieb quittiert|ARBEITSBLOCK \(geplanter Anstoß)")
ABSCHLUSS = re.compile(r"\b(erledigt|ausgeführt|ausgefuehrt|live|fertig|deployt|abgeschlossen|Ergebnis)\b", re.I)


def _now() -> float:
    v = os.environ.get("EMPFANG_JETZT")
    return float(v) if v else time.time()


def _nz(x: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(x or "").lower())


def _ts(s) -> float:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def ist_auftrag(body: str) -> bool:
    b = body.strip()
    if not b or QUIT.match(b) or ERGEBNIS.match(b):
        return False
    # Hinweis-Anhang der Harness nicht als Auftrag werten
    b = re.split(r"<artifact-content-authored-by-others", b)[0]
    # Ergebnis-/Abschlussmeldung ohne Frage (Fehlalarme 14.11.: „MB144 ausgeführt …“, „Kaufschutz-Fix MB142 live …“)
    if "?" not in b and ABSCHLUSS.search(b.splitlines()[0][:120] if b.splitlines() else ""):
        return False
    return bool(TASKY.search(b))


def ereignisse(transcript: str) -> list:
    """-> [('msg', ts, absender_ids, from_name, key, body) | ('send', ts, to)] in Dateireihenfolge."""
    p = Path(transcript)
    size = p.stat().st_size
    with open(p, "rb") as f:
        if size > TAIL_BYTES:
            f.seek(size - TAIL_BYTES)
            f.readline()
        raw = f.read().decode("utf-8", errors="ignore")
    out = []
    for line in raw.splitlines():
        if "cross-session-message" not in line and "SendMessage" not in line:
            continue
        try:
            o = json.loads(line)
        except ValueError:
            continue
        msg = o.get("message") or {}
        ts = _ts(o.get("timestamp"))
        if o.get("type") == "user":
            txt = _text(msg.get("content"))
            for m in CROSS.finditer(txt):
                attrs = dict(ATTR.findall(m.group(1)))
                body = m.group(2)
                ids = {_nz(attrs.get("from")), _nz(attrs.get("from-name"))} - {""}
                key = hashlib.sha1((attrs.get("from", "") + "|" + body[:500] + "|" + str(o.get("uuid", ""))).encode(
                    "utf-8", "ignore")).hexdigest()[:16]
                out.append(("msg", ts, ids, attrs.get("from-name") or attrs.get("from") or "?", key, body))
        elif o.get("type") == "assistant":
            for b in msg.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "SendMessage":
                    inp = b.get("input") or {}
                    out.append(("send", ts, _nz(inp.get("to") or inp.get("recipient") or "")))
    return out


def offene(ev: list, now: float) -> list:
    res = []
    for i, e in enumerate(ev):
        if e[0] != "msg" or (e[1] and now - e[1] > FENSTER) or not ist_auftrag(e[5]):
            continue
        ids = e[2]
        beantwortet = any(x[0] == "send" and x[2] and any(x[2] == s or s in x[2] or x[2] in s for s in ids)
                          for x in ev[i + 1:])
        if not beantwortet:
            res.append(e)
    return res


def main() -> None:
    for _s in (sys.stdin, sys.stdout, sys.stderr):  # Windows: sonst cp1252 und Umlaute scheitern still
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict) or data.get("stop_hook_active") or FLAG_OFF.exists():
            sys.exit(0)
        tp = data.get("transcript_path")
        if not tp or not os.path.isfile(os.path.expanduser(str(tp))):
            sys.exit(0)
        tp = os.path.expanduser(str(tp))
        now = _now()
        kandidaten = offene(ereignisse(tp), now)
        if kandidaten and not os.environ.get("EMPFANG_JETZT"):
            time.sleep(0.7)  # Transkript kann hinterherhinken (hooks.md): einmal neu lesen
            kandidaten = offene(ereignisse(tp), now)
        if not kandidaten:
            sys.exit(0)
        sid = "".join(c for c in str(data.get("session_id") or "") if c.isalnum() or c in "-_")[:80] or "ohne-id"
        sp = STATE / f"{sid}.json"
        try:
            gemeldet = set(json.loads(sp.read_text(encoding="utf-8")))
        except Exception:
            gemeldet = set()
        neu = [k for k in kandidaten if k[4] not in gemeldet]
        if not neu:
            sys.exit(0)
        STATE.mkdir(parents=True, exist_ok=True)
        tmp = sp.with_name(sp.name + f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(sorted(gemeldet | {k[4] for k in neu})[-300:]), encoding="utf-8")
        os.replace(tmp, sp)
        namen = ", ".join(dict.fromkeys(k[3] for k in neu))
        text = (f"[empfang_erinnerung] Ohne Empfangsbestaetigung: {len(neu)} Nachricht(en) mit Frage/Auftrag "
                f"von {namen}. Regel session-disziplin.md: dem Absender per SendMessage eine Zeile schicken – "
                f"„Empfangen: <Stichwort> – <übernommen | erledigt | an der Nutzer-Block | abgelehnt: Grund>“. "
                f"Ein Eintrag im der Nutzer-Block ersetzt die Quittung nicht.")
        print(json.dumps({"systemMessage": text,
                          "hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": text}},
                         ensure_ascii=False))
    except SystemExit:
        raise
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
