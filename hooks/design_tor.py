#!/usr/bin/env python3
"""design_tor: Tor fuer sichtbare Ergebnisse (G247 Phase 2, Baustein B6).

Version 1.0.0 (2026-11-18). Plan: ~/projects/Skills_&_Co/PLAENE/PLAN_G247_DESIGN_QUALITAET_2026-11-13.md, Abschnitt 5.3.
der Nutzer 14.11.2026 08:29 (MB133/6b, MB97): erst 2 Wochen weich (Hinweis + Vermerk), danach hart.

Hook-Modus (ohne Argument, liest stdin-JSON, unterscheidet nach hook_event_name):
  PostToolUse Edit|Write|MultiEdit  sichtbare Datei vormerken, einmal je Datei Hinweis per additionalContext
  PreToolUse  Artifact|SendUserFile  .html/.htm/.svg ohne gueltigen Stempel: hart deny, weich Hinweis + Vermerk
  Stop                               vorgemerkte Dateien ohne Stempel: hart decision=block, weich Hinweis;
                                     je Datei nur einmal, stop_hook_active laesst immer durch
CLI:
  design_tor.py stempel <datei> <pruefung.md> [weitere dateien ...]   Protokoll pruefen, Stempel schreiben
  design_tor.py status [<datei> ...]                                   Modus und Stempel anzeigen
  design_tor.py ohne-tor <session_id> [grund]                          des Nutzers "ohne Tor" fuer eine Session

Modus: Flag ~/.claude/flags/design_tor.hart bzw. .weich erzwingt; sonst weich bis WEICH_BIS, danach hart.
Aus: ~/.claude/flags/design_tor.off. Best-effort: eigener Fehler -> exit 0 ohne Ausgabe.
Nur auf netcup verdrahtet (am PC fehlt visual_sheet/Chrome; dort gilt Claude in Chrome).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

VERSION = "1.0.0"
HOME = Path.home()
CLAUDE = HOME / ".claude"
STATE_DIR = Path(os.environ.get("DESIGN_TOR_STATE", str(CLAUDE / "state" / "design_tor")))
STAMP_DIR = STATE_DIR / "stempel"
LOG = Path(os.environ.get("DESIGN_TOR_LOG", str(CLAUDE / "logs" / "design_tor.log")))
FLAGS = Path(os.environ.get("DESIGN_TOR_FLAGS", str(CLAUDE / "flags")))
LOOPMODE_STATE = CLAUDE / "state" / "loopmode_sessions.json"
WEICH_BIS = _dt.date(2026, 12, 2)  # 14 Tage ab Verdrahtung 18.11.2026 (MB133/6b)

SICHTBAR = {".html", ".htm", ".css", ".scss", ".svg", ".jsx", ".tsx", ".vue", ".svelte", ".astro"}
UEBERGABE = {".html", ".htm", ".svg"}  # Artifact / SendUserFile
SEITE = {".html", ".htm", ".svg"}      # Protokoll muss genau diese Datei nennen
A_NR = [f"A{i}" for i in range(1, 16)]
M_NR = [f"M{i}" for i in range(1, 13)]

VS = "node ~/.claude/scripts/visual_sheet.mjs"
TOR = "python3 ~/.claude/hooks/design_tor.py"


# ------------------------------------------------------------------ Hilfen
def _sq(p: str) -> str:
    return "'" + str(p).replace("'", "'\\''") + "'"


def _log(art: str, **kw) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "art": art, **kw}
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def modus() -> str:
    if (FLAGS / "design_tor.hart").exists():
        return "hart"
    if (FLAGS / "design_tor.weich").exists():
        return "weich"
    heute = _dt.date.fromisoformat(os.environ["DESIGN_TOR_HEUTE"]) if os.environ.get("DESIGN_TOR_HEUTE") else _dt.date.today()
    return "weich" if heute <= WEICH_BIS else "hart"


def _real(p: str, cwd: str | None = None) -> Path:
    q = Path(os.path.expanduser(p))
    if not q.is_absolute() and cwd:
        q = Path(cwd) / q
    return Path(os.path.realpath(q))


def _sid_ok(sid: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", sid or "unbekannt")[:120]


def ausgenommen(p: Path) -> bool:
    s = str(p)
    if s == str(CLAUDE) or s.startswith(str(CLAUDE) + os.sep):
        return True
    teile = p.parts
    if any(t in ("node_modules", "kopien", "tests", "test", "__tests__") or t.startswith("_archiv") for t in teile[:-1]):
        return True
    n = p.name.lower()
    # design-shotgun-Entwuerfe (designs/<screen>/variant-*.html, design-board.html) sind keine Uebergabe; das
    # Tor greift bei design-html bzw. beim Veroeffentlichen (PreToolUse prueft ohne diese Ausnahme).
    if "designs" in teile[:-1] and (n.startswith("variant-") or n == "design-board.html"):
        return True
    return ".bak" in n or n.startswith("test_") or ".test." in n or ".spec." in n


def stempel_pfad(real: Path) -> Path:
    return STAMP_DIR / (hashlib.sha1(str(real).encode("utf-8")).hexdigest() + ".json")


def stempel_gueltig(real: Path) -> dict | None:
    try:
        st = json.loads(stempel_pfad(real).read_text(encoding="utf-8"))
        if real.stat().st_mtime <= float(st.get("datei_mtime", 0)) + 0.001:
            return st
    except Exception:
        pass
    return None


def _loop_session(sid: str, cwd: str) -> bool:
    try:
        lm = json.loads(LOOPMODE_STATE.read_text(encoding="utf-8"))
        if sid in lm and time.time() - float(lm[sid]) < 7 * 24 * 3600:
            return True
    except Exception:
        pass
    try:
        sys.path.insert(0, str(CLAUDE / "scripts"))
        from games_dir import games_dir  # type: ignore
        g = Path(games_dir()).resolve()
    except Exception:
        g = (HOME / "Games").resolve()
    try:
        here = Path(cwd).resolve()
        return here == g or g in here.parents
    except Exception:
        return False


def _state_lesen(sid: str) -> dict:
    try:
        return json.loads((STATE_DIR / f"{_sid_ok(sid)}.json").read_text(encoding="utf-8"))
    except Exception:
        return {"files": {}}


def _state_schreiben(sid: str, st: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    p = STATE_DIR / f"{_sid_ok(sid)}.json"
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


def _ablauf(real: Path) -> str:
    seite = real.suffix.lower() in SEITE
    ziel = _sq(str(real)) if seite else "<seite, die sie einbindet (Datei oder lokale URL)>"
    return (f"`{VS} {ziel} --pruefen --outdir <scratchpad>/pruefung_{real.stem}` (Bash-Timeout 200000), "
            f"alle PNGs mit Read ansehen, pruefung.md ausfüllen (Stufe K/L/V, höchstens 3 Runden), dann "
            f"`{TOR} stempel {_sq(str(real))} <scratchpad>/pruefung_{real.stem}/pruefung.md`")


def _modus_satz(m: str) -> str:
    if m == "hart":
        return "Modus hart: Übergabe ohne gültigen Stempel wird gesperrt."
    return f"Modus weich bis {WEICH_BIS:%d.%m.%Y} (danach Sperre): ohne Stempel gibt es nur diesen Hinweis und einen Vermerk."


def _out(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))


# ------------------------------------------------------------------ Hook-Teile
def hook_post(data: dict, sid: str, m: str) -> None:
    ti = data.get("tool_input") or {}
    fp = ti.get("file_path") or ti.get("path")
    if not isinstance(fp, str) or not fp:
        return
    real = _real(fp, data.get("cwd"))
    if real.suffix.lower() not in SICHTBAR or ausgenommen(real):
        return
    st = _state_lesen(sid)
    files = st.setdefault("files", {})
    neu = str(real) not in files
    files.setdefault(str(real), {"t": time.time()})
    files[str(real)]["zuletzt"] = time.time()
    _state_schreiben(sid, st)
    if neu:
        _log("vorgemerkt", sid=sid, datei=str(real), modus=m)
        _out({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": (
            f"[design_tor] {real.name} ist sichtbares Ergebnis (rules/design-qualitaet.md). Vor Übergabe oder Zugende: "
            f"{_ablauf(real)}. {_modus_satz(m)} Sagt der Nutzer ausdrücklich „ohne Tor“: "
            f"`{TOR} ohne-tor {sid}` und im Abschlusssatz nennen.")}})


def _uebergabe_dateien(ti, cwd: str | None) -> list[Path]:
    funde: list[Path] = []

    def lauf(v, tiefe=0):
        if tiefe > 4:
            return
        if isinstance(v, str):
            if Path(v).suffix.lower() in UEBERGABE and "://" not in v:
                r = _real(v, cwd)
                if r.is_file() and r not in funde:
                    funde.append(r)
        elif isinstance(v, dict):
            for k, w in v.items():
                if k in ("url", "from_url", "type_url"):
                    continue
                lauf(w, tiefe + 1)
        elif isinstance(v, list):
            for w in v:
                lauf(w, tiefe + 1)

    lauf(ti)
    return funde


def hook_pre(data: dict, sid: str, m: str) -> None:
    tool = str(data.get("tool_name") or "")
    ti = data.get("tool_input") or {}
    _log("probe", sid=sid, tool=tool)  # B0(a): belegt, dass der Matcher den Toolnamen trifft
    if tool == "Artifact":
        if str(ti.get("action") or "publish") != "publish" or ti.get("asset"):
            return
    dateien = _uebergabe_dateien(ti, data.get("cwd"))
    offen = [d for d in dateien if not stempel_gueltig(d)]
    if not offen:
        return
    befehle = " | ".join(f"{d.name}: {_ablauf(d)}" for d in offen)
    _log("uebergabe_ohne_stempel", sid=sid, tool=tool, dateien=[str(d) for d in offen], modus=m)
    if m == "hart":
        _out({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
              "permissionDecisionReason": (
                  f"[design_tor] Übergabe gesperrt: kein gültiger Stempel (fehlt oder Datei danach geändert). {befehle}. "
                  f"Bei des Nutzers ausdrücklichem „ohne Tor“: `{TOR} ohne-tor {sid}`.")}})
    else:
        _out({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": (
            f"[design_tor] Ungeprüfte Übergabe vermerkt ({', '.join(d.name for d in offen)}). {_modus_satz(m)} "
            f"Nachholen: {befehle}. Im Übergabesatz sagen, dass nicht gestempelt ist.")}})


def hook_stop(data: dict, sid: str, m: str) -> None:
    if data.get("stop_hook_active"):
        return
    st = _state_lesen(sid)
    files = st.get("files") or {}
    offen = []
    for f, info in files.items():
        p = Path(f)
        if not p.exists() or info.get("stop_gemeldet") or stempel_gueltig(p):
            continue
        offen.append(p)
    if not offen:
        return
    for p in offen:
        files[str(p)]["stop_gemeldet"] = time.time()
    _state_schreiben(sid, st)
    _log("stop_ohne_stempel", sid=sid, dateien=[str(p) for p in offen], modus=m)
    liste = "; ".join(f"{p.name}: {_ablauf(p)}" for p in offen[:5])
    if len(offen) > 5:
        liste += f"; und {len(offen) - 5} weitere"
    text = (f"[design_tor] Sichtbare Dateien ohne gültigen Stempel: {liste}. Prüfen und stempeln, oder im "
            f"Abschlusssatz sagen, dass ungeprüft ist und warum. „ohne Tor“ nur auf des Nutzers Wort: `{TOR} ohne-tor {sid}`.")
    if m == "hart":
        _out({"decision": "block", "reason": text})
    else:
        _out({"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": text + " " + _modus_satz(m)}})


def hook_main() -> int:
    if os.environ.get("CLAUDE_HEALTH_CHECK") == "1":
        try:
            json.load(sys.stdin)
        except Exception:
            pass
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        if (FLAGS / "design_tor.off").exists():
            return 0
        sid = str(data.get("session_id") or "unbekannt")
        if (STATE_DIR / f"{_sid_ok(sid)}.skip").exists():
            return 0
        if _loop_session(sid, str(data.get("cwd") or os.getcwd())):
            return 0
        ev = data.get("hook_event_name") or ""
        m = modus()
        if ev == "PostToolUse":
            hook_post(data, sid, m)
        elif ev == "PreToolUse":
            hook_pre(data, sid, m)
        elif ev == "Stop":
            hook_stop(data, sid, m)
    except Exception as e:  # best-effort
        sys.stderr.write(f"design_tor: {type(e).__name__}: {e}\n")
    return 0


# ------------------------------------------------------------------ Stempel-CLI
_PNG = re.compile(r"""((?:~|/|\.{1,2}/)?[^\s`'"|,;()<>]*\.png)""", re.I)


def _zellen(zeile: str) -> list[str]:
    teile = re.split(r"(?<!\\)\|", zeile.strip())
    if teile and teile[0] == "":
        teile = teile[1:]
    if teile and teile[-1] == "":
        teile = teile[:-1]
    return [t.replace("\\|", "|").strip() for t in teile]


def _offen(v: str | None) -> bool:
    return v is None or not v.strip() or v.strip().lower().startswith("offen")


def protokoll_lesen(text: str) -> dict:
    kopf: dict[str, str] = {}
    punkte: dict[str, dict] = {}
    bilder: list[str] = []
    abschnitt = ""
    for z in text.splitlines():
        if z.startswith("## "):
            abschnitt = z[3:].strip().lower()
            continue
        mk = re.match(r"^- ([^:]{2,40}): (.*)$", z)
        if mk and not abschnitt.startswith("bilder"):
            kopf.setdefault(mk.group(1).strip().lower(), mk.group(2).strip())
        if abschnitt.startswith("bilder") and z.startswith("- "):
            bilder.append(z[2:].strip())
        if z.lstrip().startswith("|"):
            c = _zellen(z)
            if len(c) >= 5 and re.fullmatch(r"[AM]\d{1,2}", c[0]):
                punkte[c[0]] = {"art": c[1].upper(), "name": c[2], "wert": c[3], "beleg": c[4]}
    return {"kopf": kopf, "punkte": punkte, "bilder": bilder}


def _wert(w: str) -> str:
    w = w.strip().lower().lstrip("`*").strip()
    if w.startswith("ok"):
        return "ok"
    if w.startswith("befund"):
        return "befund"
    if w.startswith("n.a") or w.startswith("n. a") or w.startswith("na:"):
        return "na"
    return "offen"


def _pngs(beleg: str, basis: Path) -> tuple[list[Path], list[str]]:
    da, fehlt = [], []
    for roh in _PNG.findall(beleg):
        p = Path(os.path.expanduser(roh))
        if not p.is_absolute():
            p = basis / p
        (da if p.is_file() else fehlt).append(p if p.is_file() else roh)
    return da, fehlt


def stempel_pruefen(ziel: Path, proto_pfad: Path) -> tuple[list[str], dict]:
    fehler: list[str] = []
    pr = protokoll_lesen(proto_pfad.read_text(encoding="utf-8"))
    kopf, punkte = pr["kopf"], pr["punkte"]
    basis = proto_pfad.parent

    stufe_roh = (kopf.get("stufe") or "").strip()
    stufe = stufe_roh[:1].upper() if stufe_roh[:1].upper() in ("K", "L", "V") else ""
    if not stufe:
        fehler.append("Stufe fehlt (K, L oder V)")
    try:
        runde = int(re.match(r"\s*(\d+)", kopf.get("runde") or "").group(1))  # type: ignore[union-attr]
        if not 1 <= runde <= 3:
            fehler.append("Runde muss 1 bis 3 sein")
    except Exception:
        runde = 0
        fehler.append("Runde fehlt (1 bis 3)")

    if ziel.suffix.lower() in SEITE:
        datei = kopf.get("datei") or ""
        url_ok = bool(re.match(r"^https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?/", datei)) and \
            datei.split("#")[0].split("?")[0].rstrip("/").endswith("/" + ziel.name)
        if not datei or (not url_ok and _real(datei) != ziel):
            fehler.append(f"Protokoll gilt für „{datei or '?'}“, nicht für {ziel}")

    bilder = [Path(os.path.expanduser(b)) for b in pr["bilder"]]
    bilder_da = [b for b in bilder if b.is_file()]
    if not bilder_da:
        fehler.append("Abschnitt „Bilder“ ohne vorhandene PNG")
    else:
        try:
            if max(b.stat().st_mtime for b in bilder_da) + 2 < ziel.stat().st_mtime:
                fehler.append("Datei wurde nach dem Rendern geändert: neu rendern (visual_sheet --pruefen)")
        except Exception:
            pass

    harte = weiche = 0
    befund_pngs: list[str] = []
    for nr in A_NR + M_NR:
        p = punkte.get(nr)
        if not p:
            fehler.append(f"{nr} fehlt in der Tabelle")
            continue
        w = _wert(p["wert"])
        if w == "offen":
            fehler.append(f"{nr} ist offen (ok, Befund oder n.a.)")
            continue
        if w == "befund":
            da, fehlt = _pngs(p["beleg"] + " " + p["wert"], basis)
            if not da:
                fehler.append(f"{nr}: Befund ohne vorhandenen Bildpfad im Beleg")
            for f in fehlt:
                fehler.append(f"{nr}: Bild nicht gefunden: {f}")
            befund_pngs += [str(x) for x in da]
            art = p["art"].replace(" ", "")
            text = (p["wert"] + " " + p["beleg"]).lower()
            if art == "H" or (art == "W/H" and "weich" not in text and "(w)" not in text):
                harte += 1
            else:
                weiche += 1
        elif w == "na":
            stufe_k_m = nr.startswith("M") and stufe == "K" and "stufe k" in (p["wert"] + " " + p["beleg"]).lower()
            if not stufe_k_m and not p["beleg"].strip() and ":" not in p["wert"]:
                fehler.append(f"{nr}: n.a. ohne Zitat aus dem Brief")
            if nr.startswith("M") and stufe in ("L", "V") and "stufe k" in (p["wert"] + " " + p["beleg"]).lower():
                fehler.append(f"{nr}: „n.a.: Stufe K“ gilt nicht bei Stufe {stufe}")

    if stufe in ("L", "V") and _offen(kopf.get("zweitblick claude")):
        fehler.append("Stufe L/V: Zweitblick Claude fehlt")
    if stufe == "V":
        for feld, name in (("zweitblick codex", "Zweitblick Codex (oder Grund, z. B. Limit)"),
                           ("vorbild", "Vorbild (oder des Nutzers „ohne Vorbild“)"),
                           ("plan (zwei durchgänge)", "Zwei-Durchgänge-Plan")):
            if _offen(kopf.get(feld)):
                fehler.append(f"Stufe V: {name} fehlt")

    rest = kopf.get("restbefund (erst nach runde 3)")
    if harte or weiche >= 3:
        if runde == 3 and not _offen(rest):
            verdikt = "restbefund"
        else:
            fehler.append(f"durchgefallen: {harte} harte, {weiche} weiche Befunde (bestanden: 0 hart, unter 3 weich; "
                          f"Restbefund erst nach Runde 3 und im Feld „Restbefund“ beschrieben)")
            verdikt = "durchgefallen"
    else:
        verdikt = "bestanden"

    info = {"stufe": stufe, "runde": runde, "verdikt": verdikt, "harte": harte, "weiche": weiche,
            "restbefund": None if _offen(rest) else rest, "pngs": [str(b) for b in bilder_da],
            "befund_pngs": befund_pngs, "protokoll": str(proto_pfad),
            "zweitblick_claude": kopf.get("zweitblick claude"), "zweitblick_codex": kopf.get("zweitblick codex"),
            "vorbild": kopf.get("vorbild")}
    return fehler, info


def cli_stempel(args: list[str]) -> int:
    if len(args) < 2:
        print(f"Aufruf: {TOR} stempel <datei> <pruefung.md> [weitere dateien ...]", file=sys.stderr)
        return 1
    ziel = _real(args[0])
    proto = _real(args[1])
    weitere = [_real(a) for a in args[2:]]
    for p in [ziel, proto, *weitere]:
        if not p.is_file():
            print(f"nicht gefunden: {p}", file=sys.stderr)
            return 1
    fehler, info = stempel_pruefen(ziel, proto)
    if fehler:
        print(f"Kein Stempel für {ziel.name} ({len(fehler)} Mängel):")
        for f in fehler:
            print(f"- {f}")
        _log("stempel_abgelehnt", datei=str(ziel), protokoll=str(proto), maengel=len(fehler))
        return 2
    STAMP_DIR.mkdir(parents=True, exist_ok=True)
    jetzt = time.strftime("%Y-%m-%d %H:%M:%S")
    for d in [ziel, *weitere]:
        st = {"datei": str(d), "datei_mtime": d.stat().st_mtime, "zeit": jetzt, "version": VERSION,
              "modus": modus(), "geprueft_ueber": str(ziel), **info}
        tmp = stempel_pfad(d).with_suffix(".tmp")
        tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, stempel_pfad(d))
        _log("stempel", datei=str(d), verdikt=info["verdikt"], stufe=info["stufe"], runde=info["runde"])
    satz = f"Stempel gesetzt: {', '.join(d.name for d in [ziel, *weitere])} · Stufe {info['stufe']} · Runde {info['runde']} · {info['verdikt']}"
    if info["restbefund"]:
        satz += f" · Restbefund: {info['restbefund']} (im Übergabesatz nennen)"
    print(satz)
    return 0


def cli_status(args: list[str]) -> int:
    print(f"design_tor {VERSION} · Modus {modus()} (weich bis {WEICH_BIS:%d.%m.%Y}) · aus: {(FLAGS / 'design_tor.off').exists()}")
    for a in args:
        r = _real(a)
        st = stempel_gueltig(r) if r.exists() else None
        print(f"- {r}: {'gestempelt ' + st['zeit'] + ' · ' + st['verdikt'] if st else 'kein gültiger Stempel'}")
    return 0


def cli_ohne_tor(args: list[str]) -> int:
    if not args:
        print(f"Aufruf: {TOR} ohne-tor <session_id> [grund]", file=sys.stderr)
        return 1
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    grund = " ".join(args[1:]) or "der Nutzer: ohne Tor"
    (STATE_DIR / f"{_sid_ok(args[0])}.skip").write_text(json.dumps({"zeit": time.strftime("%Y-%m-%d %H:%M:%S"), "grund": grund}, ensure_ascii=False), encoding="utf-8")
    _log("ohne_tor", sid=args[0], grund=grund)
    print(f"Tor für Session {args[0]} aus (vermerkt in {LOG}). Im Abschlusssatz nennen.")
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        cmd, rest = sys.argv[1], sys.argv[2:]
        try:
            if cmd == "stempel":
                return cli_stempel(rest)
            if cmd == "status":
                return cli_status(rest)
            if cmd == "ohne-tor":
                return cli_ohne_tor(rest)
            if cmd in ("-h", "--help"):
                print(__doc__)
                return 0
        except Exception as e:
            print(f"design_tor: {type(e).__name__}: {e}", file=sys.stderr)
            return 1
        print(__doc__)
        return 1
    return hook_main()


if __name__ == "__main__":
    sys.exit(main())
