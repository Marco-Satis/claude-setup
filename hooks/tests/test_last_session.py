import os, sys, importlib
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude" / "hooks"))
sl = importlib.import_module("session_logger")

def _slug(cwd):
    import re
    return re.sub(r"[^a-z0-9-]", "-", cwd.lower()).strip("-")[:80] or "unknown"

def test_writes_last_md(tmp_path, monkeypatch):
    monkeypatch.setattr(sl, "_RC_STATE_DIR", tmp_path / "rc-state")
    cwd = "$HOME/n8n_stack"
    turn = {"intent": "n8n MCP fixen", "stand": "MCP neu geladen, läuft",
            "files": ["$HOME/n8n_stack/app.py"], "commits": ["fix x"], "tools": ["Bash"]}
    sl.write_last_session(cwd, "n8n_stack", turn, "2026-07-19T16:40:00+00:00")
    out = (tmp_path / "rc-state" / _slug(cwd) / "last.md")
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "n8n MCP fixen" in body and "MCP neu geladen" in body and "app.py" in body

def test_secret_gated(tmp_path, monkeypatch):
    monkeypatch.setattr(sl, "_RC_STATE_DIR", tmp_path / "rc-state")
    cwd = "$HOME/x"
    # Hinweis: Brief-Fixture (32 Zeichen Suffix) matcht das reale Pattern
    # \bsk-ant-api\d{2}-[A-Za-z0-9_-]{40,}\b NICHT (braucht >=40) -> auf 44
    # Zeichen gepolstert, damit der Secret-Gate-Test die reale Regel testet.
    turn = {"intent": "key setzen",
            "stand": "ANTHROPIC_API_KEY=sk-ant-api03-AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHHIIIIJJJJKKKK",  # pragma: allowlist secret (Testattrappe, kein echter Schluessel)
            "files": [], "commits": [], "tools": []}
    sl.write_last_session(cwd, "x", turn, "2026-07-19T16:40:00+00:00")
    out = (tmp_path / "rc-state" / _slug(cwd) / "last.md")
    assert not out.exists()   # Secret -> kein Write

def test_never_raises_on_bad_input(monkeypatch, tmp_path):
    monkeypatch.setattr(sl, "_RC_STATE_DIR", tmp_path / "rc-state")
    sl.write_last_session("/x", "x", {}, "")   # leeres turn -> kein Crash
