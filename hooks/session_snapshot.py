#!/usr/bin/env python3
"""session_snapshot.py — Stop-Hook: Stand jeder Session am Zugende (der Nutzer 15.11.2026 06:34, G252-Ausbau).

Am Ende jedes Zugs schreibt der Hook einen kleinen Snapshot der Session in den Eingang der Zentrale:
  ~/.claude/state/zentrale/sessions/<session-name>.json  (netcup, 600, synct nicht)
Inhalt: Zeit, Host, cwd/Projekt, Status, die ersten ~600 Zeichen der letzten Antwort (geschwaerzt),
Session-Link (nur RC-Sessions mit claude.ai-ID). Wechselt eine Session auf `braucht-marco`, legt
zentrale_eingang.snapshot_aufnehmen() einen ENTSCHEIDUNG-Eintrag an; der gebuendelte ntfy-Push meldet dann
„<Session> braucht dich“ (nachts nur der 07:45-Digest).

Status (Heuristik ueber die letzte Antwort, Messung im Test test_session_snapshot.py):
  braucht-marco        Frage, Freigabe oder Entscheidung an der Nutzer offen
  arbeitet             eigene Hintergrundarbeit laeuft noch (Agent, Workflow, Test, Lauf)
  wartet-auf-ereignis  wartet auf andere Session, Menschen, Uhrzeit, Cron
  fertig               sonst

Session-Name: Env CLAUDE_SESSION_NAME -> `remote-control --name <X>` unter den Eltern-Prozessen (RC-Hosts
auf netcup) -> Anzeigename des Projektordners aus meldungs_klassen.json (Allowlist) -> Ordnername.
Headless-Laeufe (`claude -p` ohne --sdk-url, --no-session-persistence) werden uebersprungen.

PC: derselbe Hook (synct). Ohne lokales zentrale_eingang.py geht der Snapshot per SSH an netcup
(notify_fallback.snapshot_senden, im Hintergrund, blockiert den Zug nicht).

Best-effort: kein Netz auf netcup, jeder Fehler -> exit 0 ohne Ausgabe. Schalter: ~/.claude/flags/session_snapshot.off
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HOME = Path.home()
FLAG_OFF = HOME / ".claude" / "flags" / "session_snapshot.off"
SCRIPTS = HOME / ".claude" / "scripts"
ZEIT_STATE = HOME / ".claude" / "state" / "zeit"
TEXT_MAX = 600
TAIL = 900

# ------------------------------------------------------------------ Status-Heuristik

_BS = [  # starke Bitte an der Nutzer: direkte Frage oder Handgriff mit Rueckmeldung, schlaegt Park-Hinweise
    r"\?\s*(\*\*)?\s*$",
    r"\bAntworte (mit|bei)\b",
    r"\bschreib(e|st)?\b[^.\n]{0,25}[„\"“]?\b(weiter|durch|ja|nein)\b",
    r"[„\"“](durch|weiter)[“\"”] schreiben",
    r"\bSag (Ja|Nein|ein Wort|Bescheid|mir)\b",
    r"\bsag mir\b",
    r"\bTipp(e|st)?\b[^.\n]{0,60}\b(ein|Terminal|/compact|/login|auf)\b",
    r"/\w+ tippen\b",
    r"\bNächste Aktion\b[^.\n]{0,40}\b(dein|deine|bleibt deine|Entscheid)",
    r"\bNächste Aktion:\s(?!keine)",
    r"\bmir [^.\n]{0,50}\bnennen\b",
    r"\bschick(e)? mir\b",
    r"\bSchreib mir\b",
    r"\bBitte (schau|prüf|zuerst|führ|tipp|gib|bestätig)",
    r"\bAskUserQuestion\b",
    r"`\w{4} ja`",
    r"(?:^|[.!:]\s+)(Soll|Sollen|Darf|Hast|Willst|Magst|Kannst|Passt|Ist das|Gibst)\b[^.?\n]{0,160}\?",
    r"\bIch warte auf deine (Wahl|Antwort|Entscheidung|Rückmeldung|Freigabe)\b",
    r"\bSagst du (Ja|Nein)\b",
    r"\bWenn du dazu kommst\b",
    r"\bNächste Aktion liegt bei dir\b",
    r"\bDu kannst (jetzt )?[`/]*compact",
    r"\bganz vorne im der Nutzer-Block\b",
]
_B = _BS + [  # schwache Bitte: zaehlt nur ohne Park-Hinweis
    r"\bdeine Entscheidung\b",
    r"\bDu entscheidest\b",
    r"\bEntscheide\b",
    r"\bZu klären ist\b",
    r"(?<!danach )\b(brauche|benötige) (ich )?(noch )?dein(e|en)?\b",
    r"\bwartet auf dich\b",
    r"\bOffen bleib\w* [^.\n]{0,40}\bbei dir\b",
    r"\bmusst du\b",
    r"\bDu arbeitest\b",
    r"\bMit einem Ja\b",
    r"(?<!ohne )(?<!ich )(?<!dort )\bdein (direktes |gesondertes )?Ja\b(?! hast)",
    r"\b(sobald|wenn) du (ihn |sie |es )?(zustimmst|freigibst)\b",
    r"\bWenn du (weitermachen willst|magst)\b",
    r"\bneu (bei dir|im der Nutzer-Block) ist\b",
    r"\bNeue Frage\b",
    r"\bFreigabe (von dir|nötig|fehlt|brauche)\b",
    r"\bMB:\s",
]
_BZ = [r"\bMB\d+\b[^.\n]{0,80}\b(freigibst|zustimmst|Frage|entscheiden|dein Ja)\b"]  # nur Zentrale
_B_NEG = [  # Session hat geparkt bzw. gesammelt, fragt bewusst nicht jetzt
    r"\bich frage dich (also )?nicht\b",
    r"\bGute Nacht\b", r"\bSchlaf gut\b",
    r"\bBis (du wieder da bist|Sonntag)\b",
    r"\bbis Sonntag\b",
    r"\bAm Sonntag\b",
    r"\bSonntags-Block\b",
    r"\bBis dahin muss ich nichts\b",
    r"\bBis zu deiner Antwort\b",
    r"\bAm Ende bekommst du\b",
    r"\bNächste Aktion: keine\b",
]
_A = [  # eigene Arbeit laeuft weiter
    r"\bläuft (noch|gerade|im Hintergrund|jetzt)\b",
    r"\b(rechnet|lädt|scannt|prüfen?) (gerade|noch|parallel)\b",
    r"\bnoch in Arbeit\b",
    r"\b(behebe|baue|prüfe|schreibe) ich gerade\b",
    r"\b(laufen|läuft) noch\b",
    r"\bSobald (die|der|das|er|sie) [^.\n]{0,40}fertig\b",
    r"\b[Ww]enn (er|sie|es|der \S+) fertig ist\b",
    r"\bMelde mich\b",
    r"\bErgebnis (also )?gegen \d",
    r"\bgestartet; er läuft\b",
    r"(?-i:(?:^|\. )Jetzt (die|der|das)) \w+",
    r"^\s*Plan:",
    r"\bIst der Workflow fertig\b",
    r"\b(zusammen mit den Ergebnissen|den anderen (zwei|drei|vier)) (der )?\w*",
    r"\bAm Ende bekommst du\b",
    r"\bläuft (im Hintergrund )?weiter\b",
    r"\bSobald (der|die|das) \w+ durch ist\b",
    r"\bnach dem (Import|Neuimport|Lauf|Refresh|Test)\b",
    r"\bAls Nächstes (baue|mache|prüfe|schreibe|werte) ich\b",
]
_W = [  # wartet auf Ereignis von aussen
    r"\bwarte(n)? (ich |wir )?(ohnehin |weiter )?(auf|bis)\b",
    r"\bwartet ohnehin\b",
    r"\b(Morgen|morgen)\b[^.\n]{0,40}\bprüfe ich\b",
    r"\bUm \d\d:\d\d prüfe ich\b",
    r"\bSobald [^.\n]{0,60}(antwortet|antworten|geantwortet|da sind|meldet|bereit)\b",
    r"\bDas Ergebnis kommt\b",
    r"\bBis dahin muss ich nichts\b",
    r"\bIch mache erst weiter, wenn\b",
    r"\bBis zu deiner Antwort\b",
    r"\bläuft bis\b",
]
_RX = {k: [re.compile(p, re.I | re.M) for p in v] for k, v in
       {"BS": _BS, "B": _B, "BZ": _BZ, "N": _B_NEG, "A": _A, "W": _W}.items()}


def _treffer(art: str, text: str) -> list[str]:
    return [r.pattern for r in _RX[art] if r.search(text)]


def status_erkennen(text: str, background_tasks=None, session_crons=None, zentrale: bool = False) -> tuple[str, str]:
    """-> (status, art). art = Freigabe | Frage | Entscheidung (nur bei braucht-marco, sonst '')."""
    t = str(text or "").strip()
    tail = t[-TAIL:]
    letzter = re.split(r"\n\s*\n", tail.rstrip())[-1] if tail else ""
    b = _treffer("B", tail) + (_treffer("BZ", tail) if zentrale else [])
    if b and _treffer("N", t) and not _treffer("BS", letzter):
        b = []
    if b and not _treffer("BS", tail) and _treffer("A", letzter):
        b = []  # nur schwache Bitte, aber die eigene Arbeit laeuft noch -> arbeitet
    if b:
        if re.search(r"Freigabe|freigibst|zustimm|\bJa\b|„?durch“? schreiben|ausführen|Tipp|neu ?start|Neustart|"
                     r"pushen|\bPush\b|löschen|deploy", letzter, re.I):
            art = "Freigabe"
        elif "?" in letzter:
            art = "Frage"
        else:
            art = "Entscheidung"
        return "braucht-marco", art
    if background_tasks or _treffer("A", tail):
        return "arbeitet", ""
    if session_crons or _treffer("W", tail):
        return "wartet-auf-ereignis", ""
    return "fertig", ""


# ------------------------------------------------------------------ Umgebung

def _vorfahren(max_n: int = 8) -> list[list[str]]:
    """cmdlines der Eltern-Prozesse (Linux /proc). Leer auf Windows oder bei Fehlern."""
    out, pid = [], os.getppid()
    for _ in range(max_n):
        try:
            raw = Path(f"/proc/{pid}/cmdline").read_bytes()
            out.append([a.decode("utf-8", "replace") for a in raw.split(b"\0") if a])
            st = Path(f"/proc/{pid}/status").read_text()
            pid = int(re.search(r"^PPid:\s*(\d+)", st, re.M).group(1))
            if pid <= 1:
                break
        except Exception:
            break
    return out


def _arg(cmd: list[str], name: str) -> str:
    for i, a in enumerate(cmd):
        if a == name and i + 1 < len(cmd):
            return cmd[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return ""


def _desktop_titel() -> tuple[str, bool]:
    """PC/Desktop-App: (Titel, von der Nutzer benannt). Quelle Setup PC 15.11.2026:
    %APPDATA%/Claude/claude-code-sessions/<konto>/<org>/<CLAUDE_CODE_HOST_SESSION_ID>.json, Feld title;
    titleSource fehlt bei Desktop-Routinen. Ohne Treffer ("", False)."""
    hid = os.environ.get("CLAUDE_CODE_HOST_SESSION_ID", "")
    if os.name != "nt" or not re.fullmatch(r"local_[0-9a-f-]{36}", hid):
        return "", False
    base = Path(os.environ.get("APPDATA", "")) / "Claude" / "claude-code-sessions"
    for p in base.glob(f"*/*/{hid}.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            t = str(d.get("title") or "").strip()[:60]
            return t, bool(t) and d.get("titleSource") == "user"
        except Exception:
            return "", False
    return "", False


def umgebung(cwd: str) -> dict:
    """-> {name, rc, link, headless}."""
    vf = _vorfahren() if os.name != "nt" else []
    name, sid, headless, rc = os.environ.get("CLAUDE_SESSION_NAME", "").strip(), "", False, False
    if os.name == "nt" and not name:
        titel, benannt = _desktop_titel()
        if titel and not benannt:      # Desktop-Routine (kein von der Nutzer vergebener Titel): kein Snapshot
            headless = True
        elif titel:
            name = titel
    for cmd in vf:
        if not cmd:
            continue
        if "remote-control" in cmd:
            rc = True
            name = name or _arg(cmd, "--name")
        s = _arg(cmd, "--session-id")
        if s.startswith("cse_") and not sid:
            sid = s
        if ("-p" in cmd or "--print" in cmd) and not _arg(cmd, "--sdk-url"):
            headless = True
        if "--no-session-persistence" in cmd:
            headless = True
    if not name:
        name = _anzeige_ordner(cwd)
    link = ""
    if rc and re.fullmatch(r"cse_[A-Za-z0-9]{10,40}", sid or ""):
        link = "https://claude.ai/code/session_" + sid[4:]
    return {"name": name[:60], "rc": rc, "link": link, "headless": headless and not rc}


def _anzeige_ordner(cwd: str) -> str:
    base = Path(cwd or os.getcwd()).name or "unbekannt"
    try:
        erlaubt = json.loads((SCRIPTS / "meldungs_klassen.json").read_text(encoding="utf-8"))["projekte"]["erlaubt"]
        n = erlaubt.get(base, base)
    except Exception:
        n = base
    if os.name == "nt" and n == "Setup Server":
        n = "Setup PC"
    return n


def marco_vor_s(session_id: str, jetzt: float) -> float | None:
    """Sekunden seit des Nutzers letzter Nachricht in dieser Session (zeit_kontext.py-Zustand) oder None."""
    sid = "".join(c for c in str(session_id or "") if c.isalnum() or c == "-")[:64]
    try:
        return max(0.0, jetzt - float((ZEIT_STATE / f"{sid}.ts").read_text().strip()))
    except Exception:
        return None


def letzte_antwort(data: dict) -> str:
    t = data.get("last_assistant_message")
    if isinstance(t, str) and t.strip():
        return t
    tp = data.get("transcript_path")   # Rueckfall aeltere CLI: letzte Assistenten-Textzeile im Transkript-Ende
    try:
        p = Path(os.path.expanduser(str(tp)))
        size = p.stat().st_size
        with open(p, "rb") as f:
            f.seek(max(0, size - 400_000))
            zeilen = f.read().decode("utf-8", "ignore").splitlines()
        for z in reversed(zeilen):
            if '"assistant"' not in z:
                continue
            try:
                o = json.loads(z)
            except ValueError:
                continue
            if o.get("type") == "assistant" and not o.get("isSidechain"):
                txt = "\n".join(b.get("text", "") for b in (o.get("message") or {}).get("content") or []
                                if isinstance(b, dict) and b.get("type") == "text")
                if txt.strip():
                    return txt
    except Exception:
        pass
    return ""


# ------------------------------------------------------------------ main

def snapshot_bauen(data: dict, jetzt: float) -> dict | None:
    cwd = str(data.get("cwd") or os.getcwd())
    um = umgebung(cwd)
    if um["headless"]:
        return None
    text = letzte_antwort(data)
    zentrale = um["name"] == "Setup Server" or (os.name != "nt" and "Skills_&_Co" in cwd)
    status, art = status_erkennen(text, data.get("background_tasks"), data.get("session_crons"), zentrale)
    import socket
    return {"name": um["name"], "ts": jetzt, "host": socket.gethostname(), "cwd": cwd,
            "projekt": Path(cwd).name, "status": status, "art": art, "text": text[:TEXT_MAX],
            "session_id": str(data.get("session_id") or "")[:80], "link": um["link"], "rc": um["rc"],
            "marco_vor_s": marco_vor_s(data.get("session_id"), jetzt), "zentrale": zentrale}


def main() -> None:
    import time
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict) or FLAG_OFF.exists():
            return
        snap = snapshot_bauen(data, time.time())
        if not snap:
            return
        if os.name != "nt" and (SCRIPTS / "zentrale_eingang.py").exists() and (HOME / ".claude" / "rc-notify.sh").exists():
            sys.path.insert(0, str(SCRIPTS))
            import zentrale_eingang  # noqa: E402
            zentrale_eingang.snapshot_aufnehmen(snap)
        else:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import notify_fallback  # noqa: E402
            notify_fallback.snapshot_senden(snap)
    except Exception:
        pass


if __name__ == "__main__":
    for _s in (sys.stdin, sys.stdout):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()
    sys.exit(0)
