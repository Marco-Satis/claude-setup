import sys, importlib
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude" / "hooks"))
mod = importlib.import_module("rc_session_resume_impl")  # siehe Step 3: Logik in importierbarem Modul

def test_render_local_only():
    out = mod.render("# Last session — n8n\nStand: MCP läuft", "")
    assert "Resume nach Restart" in out
    assert "MCP läuft" in out
    assert "mcp-memory" not in out   # kein Memory-Block wenn leer

def test_render_merges_both_dedup():
    local = "# Last session — n8n\nStand: MCP läuft"
    out = mod.render(local, "# Checkpoint\nletzter Stand X")
    assert "MCP läuft" in out and "letzter Stand X" in out

def test_render_skips_identical_memory():
    local = "# Last session\nStand: gleich"
    out = mod.render(local, local)   # identisch -> Memory-Block weglassen
    assert out.count("gleich") == 1

def test_render_empty_returns_empty():
    assert mod.render("", "") == ""
