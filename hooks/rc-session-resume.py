#!/usr/bin/env python3
# SessionStart (resume|startup): aktiv den letzten Stand injizieren, damit eine
# per --continue resumte RC-Session sich re-orientiert statt kalt ins Transcript
# zu fallen. Merged lokale (nicht-gesyncte) last.md + mcp-memory (best-effort).
# Loest die passive rc-session-recovery.py-Note ab. Best-effort, exit 0, <=1 JSON.
import sys, json, os, re
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude" / "hooks"))

def emit(ctx=None):
    if ctx:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart", "additionalContext": ctx}}))
    sys.exit(0)

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
try:
    import rc_session_resume_impl as impl
except Exception:
    emit()
try:
    d = json.load(sys.stdin)
except Exception:
    emit()
if not isinstance(d, dict):
    emit()

if d.get("source") not in ("resume", "startup"):
    emit()
cwd = d.get("cwd")
cwd = cwd if isinstance(cwd, str) and cwd else os.getcwd()
project_slug = re.sub(r"[^a-z0-9-]", "-", (os.path.basename(cwd.rstrip("/")) or "unknown").lower())[:40]

try:
    local_txt = impl.load_local(cwd)
except Exception:
    local_txt = ""
try:
    mem_txt = impl.fetch_latest_memory(project_slug)
except Exception:
    mem_txt = ""
try:
    ctx = impl.render(local_txt, mem_txt)
except Exception:
    ctx = ""
emit(ctx if ctx else None)
