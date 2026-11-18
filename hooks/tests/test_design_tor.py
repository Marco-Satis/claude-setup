"""Tests fuer hooks/design_tor.py (G247 B6, Plan 5.3, Abnahme T3 a-h plus weicher Modus).

Lauf: python3 -m pytest -q ~/.claude/hooks/tests/test_design_tor.py
Alles in tmp-Ordnern: Zustand, Log und Flags ueber DESIGN_TOR_STATE/_LOG/_FLAGS umgebogen.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HOOK = str(Path.home() / ".claude" / "hooks" / "design_tor.py")
A = [(f"A{i}", "H" if i not in (8, 9, 10, 13, 15) else ("W/H" if i == 13 else "W")) for i in range(1, 16)]
M = [(f"M{i}", "H" if i in (2, 5, 8, 12) else "W") for i in range(1, 13)]


@pytest.fixture()
def env(tmp_path):
    e = dict(os.environ)
    e.pop("CLAUDE_HEALTH_CHECK", None)
    e["DESIGN_TOR_STATE"] = str(tmp_path / "state")
    e["DESIGN_TOR_LOG"] = str(tmp_path / "log" / "design_tor.log")
    e["DESIGN_TOR_FLAGS"] = str(tmp_path / "flags")
    (tmp_path / "flags").mkdir()
    (tmp_path / "flags" / "design_tor.hart").touch()  # Standard im Test: hart (T3 beschreibt die Sperre)
    return e


def run(env, payload=None, args=()):
    p = subprocess.run([sys.executable, HOOK, *args], input=json.dumps(payload) if payload is not None else "",
                       capture_output=True, text=True, env=env, timeout=30, cwd="/tmp")
    out = json.loads(p.stdout) if p.stdout.strip() and not args else None
    return p.returncode, out, p.stdout, p.stderr


def post(path, sid="s1"):
    return {"hook_event_name": "PostToolUse", "session_id": sid, "cwd": "/tmp", "tool_name": "Write",
            "tool_input": {"file_path": str(path), "content": "x"}, "tool_response": {}}


def pre(tool, ti, sid="s1"):
    return {"hook_event_name": "PreToolUse", "session_id": sid, "cwd": "/tmp", "tool_name": tool, "tool_input": ti}


def stop(sid="s1", active=False):
    return {"hook_event_name": "Stop", "session_id": sid, "cwd": "/tmp", "stop_hook_active": active}


def protokoll(tmp_path, seite, stufe="K", runde="1", werte=None, kopf_extra=None):
    """Ausgefuelltes Protokoll im Format von visual_sheet.mjs buildProtocol (Tabelle mit 6 Spalten)."""
    img = tmp_path / "lauf" / "sheet_1280_light.png"
    img.parent.mkdir(parents=True, exist_ok=True)
    img.write_bytes(b"\x89PNG\r\n")
    werte = werte or {}
    k = {"Zweitblick Claude": "offen", "Zweitblick Codex": "offen", "Vorbild": "offen", "Plan (zwei Durchgänge)": "offen"}
    k.update(kopf_extra or {})
    L = [f"# Prüfprotokoll: {seite.name}", "", f"- Datei: {seite}", f"- Stufe: {stufe}", f"- Runde: {runde}",
         "- Lauf: x · 2026-11-18 04:00 MEZ"] + [f"- {a}: {b}" for a, b in k.items()] + ["", "## Bilder (alle mit Read ansehen)", "", f"- {img}", ""]
    for titel, rows in (("## Anti-KI-Checkliste A1–A15", A), ("## Bewegung M1–M12", M)):
        L += [titel, "", "| Nr | Art | Punkt | Wert | Beleg | Mechanik |", "|---|---|---|---|---|---|"]
        for nr, art in rows:
            wert, beleg = werte.get(nr, ("ok", ""))
            L.append(f"| {nr} | {art} | Punkt | {wert} | {beleg} |  |")
        L.append("")
    L += ["## Ergebnis", "", "- Harte Befunde: 0", "- Weiche Befunde: 0",
          f"- Restbefund (erst nach Runde 3): {k.get('Restbefund', 'offen')}", "- Verdikt: bestanden", ""]
    p = tmp_path / "lauf" / "pruefung.md"
    p.write_text("\n".join(L), encoding="utf-8")
    return p, img


@pytest.fixture()
def seite(tmp_path):
    s = tmp_path / "projekt" / "index.html"
    s.parent.mkdir()
    s.write_text("<h1>x</h1>", encoding="utf-8")
    old = time.time() - 60
    os.utime(s, (old, old))
    return s


# --- T3 (a) HTML-Edit ohne Pruefung: Stop blockt genau einmal
def test_a_stop_blockt_einmal(env, seite):
    rc, out, _, _ = run(env, post(seite))
    assert rc == 0 and "design_tor" in out["hookSpecificOutput"]["additionalContext"]
    rc, out2, raw, _ = run(env, post(seite))  # zweiter Edit derselben Datei: kein zweiter Hinweis
    assert raw == ""
    rc, out, _, _ = run(env, stop())
    assert out["decision"] == "block" and "stempel" in out["reason"]
    rc, out, raw, _ = run(env, stop())
    assert raw == ""
    # stop_hook_active laesst immer durch
    b = seite.with_name("b.html")
    b.write_text("x")
    run(env, post(b))
    rc, out, raw, _ = run(env, stop(active=True))
    assert raw == ""


# --- T3 (b) Artifact ohne Stempel: deny mit Befehl
def test_b_artifact_ohne_stempel_deny(env, seite):
    rc, out, _, _ = run(env, pre("Artifact", {"file_path": str(seite), "icon": "chart"}))
    h = out["hookSpecificOutput"]
    assert h["permissionDecision"] == "deny" and "visual_sheet.mjs" in h["permissionDecisionReason"]
    assert "design_tor.py stempel" in h["permissionDecisionReason"]


# --- T3 (c) mit gueltigem Stempel: geht durch; (d) Stempel-CLI lehnt offen/Befund ohne Bild ab
def test_c_d_stempel(env, seite, tmp_path):
    proto, img = protokoll(tmp_path, seite, werte={"A3": ("offen", "")})
    rc, _, raw, _ = run(env, args=("stempel", str(seite), str(proto)))
    assert rc == 2 and "A3 ist offen" in raw
    proto, img = protokoll(tmp_path, seite, werte={"A9": ("Befund", "Anführungszeichen im Hero")})
    rc, _, raw, _ = run(env, args=("stempel", str(seite), str(proto)))
    assert rc == 2 and "ohne vorhandenen Bildpfad" in raw
    proto, img = protokoll(tmp_path, seite, werte={"A9": ("Befund", f"{tmp_path}/lauf/fehlt.png Hero")})
    rc, _, raw, _ = run(env, args=("stempel", str(seite), str(proto)))
    assert rc == 2 and "nicht gefunden" in raw
    # weicher Befund mit Bild, M auf n.a. Stufe K: bestanden
    werte = {"A9": ("Befund", f"{img} Hero, gerade Anführungszeichen")}
    werte.update({f"M{i}": ("n.a.: Stufe K", "") for i in range(1, 13)})
    proto, img = protokoll(tmp_path, seite, werte=werte)
    rc, _, raw, _ = run(env, args=("stempel", str(seite), str(proto)))
    assert rc == 0 and "bestanden" in raw, raw
    rc, out, raw, _ = run(env, pre("Artifact", {"file_path": str(seite)}))
    assert raw == ""


def test_d_harter_befund_und_restbefund(env, seite, tmp_path):
    werte = {"A2": ("Befund", "sheet_1280_light.png Inter ohne Brief")}
    proto, _ = protokoll(tmp_path, seite, werte=werte)
    rc, _, raw, _ = run(env, args=("stempel", str(seite), str(proto)))
    assert rc == 2 and "durchgefallen" in raw
    proto, _ = protokoll(tmp_path, seite, runde="3", werte=werte, kopf_extra={"Restbefund": "A2 Inter, Kunde will es"})
    rc, _, raw, _ = run(env, args=("stempel", str(seite), str(proto)))
    assert rc == 0 and "Restbefund" in raw


def test_d_stufe_v_pflichtteile(env, seite, tmp_path):
    proto, _ = protokoll(tmp_path, seite, stufe="V", kopf_extra={"Zweitblick Claude": "unklar 30"})
    rc, _, raw, _ = run(env, args=("stempel", str(seite), str(proto)))
    assert rc == 2 and "Vorbild" in raw and "Codex" in raw and "Zwei-Durchgänge" in raw
    proto, _ = protokoll(tmp_path, seite, stufe="V", kopf_extra={
        "Zweitblick Claude": "unklar 30", "Zweitblick Codex": "entfallen: Limit", "Vorbild": "linear.app",
        "Plan (zwei Durchgänge)": "plan.md"})
    rc, _, raw, _ = run(env, args=("stempel", str(seite), str(proto)))
    assert rc == 0, raw


def test_d_falsche_datei(env, seite, tmp_path):
    andere = seite.with_name("andere.html")
    andere.write_text("x")
    proto, _ = protokoll(tmp_path, seite)
    rc, _, raw, _ = run(env, args=("stempel", str(andere), str(proto)))
    assert rc == 2 and "Protokoll gilt für" in raw


# --- T3 (e) Edit an .py: keine Wirkung
def test_e_py_keine_wirkung(env, tmp_path):
    f = tmp_path / "x.py"
    f.write_text("x")
    rc, out, raw, _ = run(env, post(f))
    assert raw == ""
    rc, out, raw, _ = run(env, stop())
    assert raw == ""


# --- T3 (f) Kill-Switch
def test_f_killswitch(env, seite, tmp_path):
    (tmp_path / "flags" / "design_tor.off").touch()
    for p in (post(seite), pre("Artifact", {"file_path": str(seite)}), stop()):
        rc, out, raw, _ = run(env, p)
        assert rc == 0 and raw == ""


# --- T3 (g) Datei nach dem Stempel geaendert: wieder gesperrt
def test_g_nach_stempel_geaendert(env, seite, tmp_path):
    proto, _ = protokoll(tmp_path, seite)
    assert run(env, args=("stempel", str(seite), str(proto)))[0] == 0
    seite.write_text("<h1>neu</h1>")
    rc, out, _, _ = run(env, pre("Artifact", {"file_path": str(seite)}))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


# --- T3 (h) SendUserFile mit PNG: keine Wirkung; mit .svg: deny
def test_h_senduserfile(env, tmp_path):
    png = tmp_path / "a.png"
    png.write_bytes(b"x")
    rc, out, raw, _ = run(env, pre("SendUserFile", {"file_path": str(png)}))
    assert raw == ""
    svg = tmp_path / "a.svg"
    svg.write_text("<svg/>")
    rc, out, _, _ = run(env, pre("SendUserFile", {"files": [str(svg)]}))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


# --- weicher Modus (MB133/6b): Hinweis + Vermerk statt Sperre
def test_weich(env, seite, tmp_path):
    (tmp_path / "flags" / "design_tor.hart").unlink()
    env = dict(env, DESIGN_TOR_HEUTE="2026-11-20")
    rc, out, _, _ = run(env, pre("Artifact", {"file_path": str(seite)}))
    h = out["hookSpecificOutput"]
    assert "permissionDecision" not in h and "weich" in h["additionalContext"]
    run(env, post(seite))
    rc, out, _, _ = run(env, stop())
    assert "decision" not in out and out["hookSpecificOutput"]["hookEventName"] == "Stop"
    log = (tmp_path / "log" / "design_tor.log").read_text()
    assert "uebergabe_ohne_stempel" in log and '"probe"' in log
    # nach WEICH_BIS automatisch hart
    env2 = dict(env, DESIGN_TOR_HEUTE="2026-12-03")
    rc, out, _, _ = run(env2, pre("Artifact", {"file_path": str(seite)}))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_ausnahmen_und_ohne_tor(env, seite, tmp_path):
    # Artifact-Aktionen ausser publish und Asset-Uploads sind nicht betroffen
    assert run(env, pre("Artifact", {"action": "read", "url": "https://claude.ai/artifact/x"}))[2] == ""
    assert run(env, pre("Artifact", {"url": "u", "file_path": str(seite), "asset": True}))[2] == ""
    # Ausnahmen: .bak, _archive, node_modules, ~/.claude
    for name in ("x.html.bak.1", "_archive_x/y.html", "node_modules/a/b.html",
                 "designs/start-20261118/variant-a.html", "designs/start-20261118/design-board.html"):
        f = tmp_path / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
        assert run(env, post(f))[2] == ""
    # ... aber die Veroeffentlichung eines Entwurfs prueft das Tor trotzdem
    v = tmp_path / "designs/start-20261118/variant-a.html"
    assert run(env, pre("Artifact", {"file_path": str(v)}))[1]["hookSpecificOutput"]["permissionDecision"] == "deny"
    # Protokoll ueber lokale URL mit gleichem Dateinamen gilt
    proto, _ = protokoll(tmp_path, seite)
    t = proto.read_text(encoding="utf-8").replace(f"- Datei: {seite}", "- Datei: http://127.0.0.1:18821/index.html")
    proto.write_text(t, encoding="utf-8")
    assert run(env, args=("stempel", str(seite), str(proto)))[0] == 0
    assert run(env, post(Path.home() / ".claude" / "templates" / "x.html"))[2] == ""
    # "ohne Tor"
    assert run(env, args=("ohne-tor", "s9", "der Nutzer 18.11."))[0] == 0
    assert run(env, pre("Artifact", {"file_path": str(seite)}, sid="s9"))[2] == ""
    assert "ohne_tor" in (tmp_path / "log" / "design_tor.log").read_text()


def test_robust(env):
    for raw in ("", "kein json", "[]"):
        p = subprocess.run([sys.executable, HOOK], input=raw, capture_output=True, text=True, env=env, timeout=30)
        assert p.returncode == 0 and p.stdout == ""
    e = dict(env, CLAUDE_HEALTH_CHECK="1")
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(stop()), capture_output=True, text=True, env=e, timeout=30)
    assert p.returncode == 0 and p.stdout == ""
