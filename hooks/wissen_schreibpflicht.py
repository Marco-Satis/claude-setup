#!/usr/bin/env python3
"""wissen_schreibpflicht.py — Stop-Hook: Sessions halten Dauerhaftes fest, bevor sie den Zug beenden.

der Nutzer 16.11.2026 21:24: „Memories werden nicht aktiv geschrieben oder nur sporadisch von manchen Sessions.
Das muss wieder aktiv von jeder Session geschrieben werden, durchgehend.“ Befund 16.11.: von 111 wz-Einträgen
der letzten 7 Tage stammten 70 aus der Setup-Zentrale; die PC-Sessions schrieben fast nichts selbst.

Auslöser (einmal je der Nutzer-Nachricht bzw. je Setup-Edit-Zug):
  a) des Nutzers letzte Nachricht enthält eine Festlegung: Detektor wissen_m.erkennen() (dauerhaft, verbot,
     korrektur, entscheidung) oder ein Auftrags-/Entscheidungswort (soll, muss, will, möchte, darf, ja, MB-Nr.);
  b) oder in diesem Zug wurde unter ~/.claude/ editiert (Setup-Änderung).
Liegt seit dieser Nachricht kein Schreibvorgang vor (wz neu/set/merk, mcp memory_store/update, wissen_merken),
blockt der Hook das Zugende einmal mit einer kurzen Aufforderung. Die Session schreibt dann oder sagt in einer
Zeile, warum nichts Dauerhaftes dabei war. stop_hook_active verhindert Schleifen.

Aus: touch ~/.claude/flags/wissen_schreibpflicht.off
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HOME = Path.home()
FLAG_AUS = HOME / ".claude" / "flags" / "wissen_schreibpflicht.off"
STATE = HOME / ".claude" / "state" / "wissen_schreibpflicht.json"
sys.path.insert(0, str(HOME / ".claude" / "scripts" / "wissen"))

AUFTRAG = re.compile(r"\b(soll|sollen|sollte|muss|muessen|müssen|ich will|ich moechte|ich möchte|darf|duerfen|dürfen|"
                     r"ab jetzt|ab sofort|kuenftig|künftig|immer|nie|niemals|ja|nein)\b|\bmb ?\d{1,3}\b", re.I)
SCHREIB_TOOLS = {"mcp__memory__memory_store", "mcp__memory__memory_update", "mcp__memory__memory_store_session",
                 "mcp__claude_ai_memory-netcup__wissen_merken", "mcp__memory-netcup__wissen_merken"}
SCHREIB_BASH = re.compile(r"\bwz(\.py)?\s+(neu|set|merk|supersede|bestaetigen)\b")


def _inhalt(d):
    if d.get("type") == "attachment":  # Nachricht während eines laufenden Zugs (queued_command)
        return str((d.get("attachment") or {}).get("prompt") or "")
    c = (d.get("message") or {}).get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return ""


def _ist_marco(d):
    if d.get("type") == "attachment":
        a = d.get("attachment") or {}
        return (a.get("type") == "queued_command" and bool(a.get("humanTurn"))
                and (a.get("origin") or {}).get("kind") == "human" and bool(str(a.get("prompt") or "").strip()))
    if d.get("type") != "user" or d.get("isMeta") or d.get("isSidechain") or d.get("isCompactSummary"):
        return False
    if (d.get("origin") or {}).get("kind") != "human":
        return False
    c = _inhalt(d).lstrip()
    return bool(c) and not c.startswith(("<command-", "<local-command", "<task-notification", "<system-reminder"))


def _parse(daten, abgeschnitten):
    zeilen = daten.split(b"\n")
    if abgeschnitten:
        zeilen = zeilen[1:]
    out = []
    for z in zeilen:
        if z.strip():
            try:
                out.append(json.loads(z))
            except ValueError:
                pass
    return out


def _eintraege(pfad, block=2_000_000, obergrenze=20_000_000):
    """Liest rückwärts in Blöcken, bis eine der Nutzer-Nachricht im Fenster liegt (höchstens `obergrenze` Bytes).
    Grund (Setup PC 16.11.): Lange Züge füllen 1,5 MB in ~20 min, des Nutzers Nachricht fiel sonst heraus."""
    try:
        with open(pfad, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            n = block
            while True:
                n = min(n, size, obergrenze)
                f.seek(size - n)
                out = _parse(f.read(n), size > n)
                if n >= size or n >= obergrenze or any(_ist_marco(d) for d in out):
                    return out
                n += block
    except OSError:
        return []


def _tool_uses(d):
    if d.get("type") != "assistant":
        return []
    c = (d.get("message") or {}).get("content")
    return [x for x in c if isinstance(x, dict) and x.get("type") == "tool_use"] if isinstance(c, list) else []


def _festlegung(text):
    try:
        import wissen_m as M
        if M.erkennen(text):
            return True
        t = M.fold(text)
    except Exception:
        t = text.lower()
    return len(text.strip()) >= 2 and bool(AUFTRAG.search(t))


ARBEIT_BASH = re.compile(r"\b(git\s+(commit|push|mv|rm|checkout|merge|rebase|tag)|systemctl|crontab|mv|cp|mkdir|"
                         r"rm|chmod|pip3?\s+install|npm\s+(i|install)|apt(-get)?\s+install|docker|sed\s+-i|"
                         r"robocopy|Move-Item|Copy-Item|Set-ItemProperty|New-Item|schtasks|Register-ScheduledTask)\b")
ARBEIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
VIELE_TOOLS = 8   # ab so vielen Werkzeugaufrufen in einem Zug gab es fast immer Befunde


def _ist_zugstart(d):
    """Echte Nutzer-Zeile (kein tool_result) = Beginn eines Zugs."""
    if d.get("type") == "attachment":
        return False
    if d.get("type") != "user":
        return False
    c = (d.get("message") or {}).get("content")
    return not (isinstance(c, list) and any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c))


def pruefen(eintraege):
    """Gibt (grund, schluessel) zurück, wenn geblockt werden soll, sonst (None, None).
    der Nutzer 16.11.2026 21:33: nicht nur Entscheidungen, sondern alles Nützliche festhalten (Änderungen, Neues,
    Befunde, Fehler und Lösungen, Werte, offene Punkte)."""
    idx = max((i for i, d in enumerate(eintraege) if _ist_marco(d)), default=None)
    letzte_user = max((i for i, d in enumerate(eintraege) if _ist_zugstart(d)), default=-1)
    zug = eintraege[letzte_user + 1:]
    start = min(idx + 1, letzte_user + 1) if idx is not None else letzte_user + 1
    for d in eintraege[start:]:
        for u in _tool_uses(d):
            n, inp = u.get("name", ""), u.get("input") or {}
            if n in SCHREIB_TOOLS or (n == "Bash" and SCHREIB_BASH.search(str(inp.get("command", "")))):
                return None, None
    uses = [u for d in zug for u in _tool_uses(d)]
    arbeit = any(u.get("name") in ARBEIT_TOOLS
                 and "/.claude/state/" not in str((u.get("input") or {}).get("file_path", "")).replace("\\", "/")
                 for u in uses)
    arbeit = arbeit or any(u.get("name") in ("Bash", "PowerShell")
                           and ARBEIT_BASH.search(str((u.get("input") or {}).get("command", ""))) for u in uses)
    schluessel_zug = (zug[-1].get("uuid") if zug else None) or f"zug{letzte_user}"
    if idx is not None and idx >= letzte_user - 1 and _festlegung(_inhalt(eintraege[idx])):
        return "marco", eintraege[idx].get("uuid") or str(idx)
    if arbeit:
        return "arbeit", schluessel_zug
    # Loop-/Cron-Ticks und Peer-Nachrichten (Zugstart nicht von der Nutzer): Befund-Auslöser erst ab 25 Aufrufen,
    # sonst bliebe jeder Gamebot-Tick einmal hängen (Einwand Setup PC 16.11. 21:35). Änderungen zählen weiter.
    start_d = eintraege[letzte_user] if letzte_user >= 0 else {}
    schwelle = VIELE_TOOLS if (start_d.get("origin") or {}).get("kind") == "human" else 25
    if len(uses) >= schwelle:
        return "befunde", schluessel_zug
    return None, None


def main():
    if FLAG_AUS.exists():
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("stop_hook_active"):
        return 0
    pfad = data.get("transcript_path")
    if not pfad or not os.path.exists(pfad):
        return 0
    grund, schluessel = pruefen(_eintraege(pfad))
    if not grund:
        return 0
    sid = data.get("session_id", "?")
    try:
        st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    except Exception:
        st = {}
    if st.get(sid) == schluessel:
        return 0  # für diese Nachricht schon einmal erinnert
    st[sid] = schluessel
    if len(st) > 60:
        st = dict(list(st.items())[-60:])
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(st), encoding="utf-8")
    except OSError:
        pass
    anlass = {"marco": "der Nutzer hat in seiner letzten Nachricht etwas festgelegt, beauftragt oder mitgeteilt",
              "arbeit": "Du hast in diesem Zug etwas geändert oder neu angelegt",
              "befunde": "Du hast in diesem Zug viel untersucht"}[grund]
    print(json.dumps({"decision": "block", "reason": (
        f"[WISSEN-PFLICHT] {anlass}, und seitdem wurde nichts festgehalten (der Nutzer 16.11.2026: alles Nützliche "
        "festhalten, nicht nur Entscheidungen). Halte jetzt in 1–3 Einträgen fest, was davon zutrifft: "
        "des Nutzers Entscheidung, Wunsch, Korrektur oder Vorliebe · Änderung (was, wo, warum, Sicherung/Rückweg) · "
        "Neues (Datei, Skript, Hook, Dienst, Routine, Konto) · Befund und Ursache · Fehler mit Lösung und Lehre · "
        "Sackgasse (was nicht funktioniert hat, warum) · gemessener Wert, Pfad, Port, Version, Befehl · "
        "offener Punkt und nächster Schritt · Zusammenhang mit anderen Projekten oder Sessions. "
        "Wohin: Dauerhaftes per `wz neu` (netcup; am PC per ssh netcup-marco „wz neu …“), Verlauf und Stand "
        "als mcp memory_store mit Projekt-Tag, Setup-Änderungen zusätzlich mit Tag setup-change. War der Zug "
        "ohne Neues (reine Frage, nur gelesen, nichts gelernt), sag das in einem Satz und beende den Zug.")},
        ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
