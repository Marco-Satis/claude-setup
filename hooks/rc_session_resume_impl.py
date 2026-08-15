#!/usr/bin/env python3
"""rc_session_resume_impl.py — reine Logik fuer den aktiven RC-Session-Resume-Hook
(rc-session-resume.py). Getrennt vom Hook-Entrypoint, damit ohne stdin/Netz testbar.

Teil B (aktive Resume-Injektion) + Teil C (mcp-memory als Zweitquelle) der
RC-Continuity-Spezifikation. Liest die von session_logger.write_last_session
(Task 1) geschriebene ~/.cache/claude-rc-state/<slug>/last.md und merged sie
best-effort mit dem letzten mcp-memory-Checkpoint des Projekts.
"""
import json
import re
import urllib.request
from pathlib import Path

RC_STATE_DIR = Path.home() / ".cache" / "claude-rc-state"

MEMORY_FETCH_TIMEOUT = 2  # Sekunden — best-effort, darf den SessionStart-Hook nie blockieren


def slug_for(cwd: str) -> str:
    """MUSS byte-identisch zu session_logger.write_last_session's Slug-Formel sein,
    sonst findet der Reader die vom Writer erzeugte Datei nicht."""
    return re.sub(r"[^a-z0-9-]", "-", (cwd or "unknown").lower()).strip("-")[:80] or "unknown"


def load_local(cwd: str) -> str:
    """Liest die lokale (nicht-gesyncte) last.md fuer cwd. Best-effort, nie ein Crash."""
    try:
        p = RC_STATE_DIR / slug_for(cwd) / "last.md"
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        pass
    return ""


def fetch_latest_memory(project_slug: str) -> str:
    """Best-effort: letzten Session-Checkpoint/-Stand des Projekts aus mcp-memory.
    Bounded 2s. JEDE Ausnahme -> "" (lokale last.md ist die verlaessliche Primaerquelle,
    Merge degradiert sauber auf lokal-only).

    Endpoint verifiziert (Task 2 Step 4) am laufenden Service (127.0.0.1:8000):
    - GET  /api/search              -> 405 Method Not Allowed (ist POST, Semantic-Search)
    - GET  /api/memories?tag=...    -> 401 authorization_required (auch mit gueltigem
      X-API-Key liefert dieser Pfad keine taggefilterte Liste im erwarteten Shape)
    - POST /api/search/by-tag       -> 200, TagSearchRequest {"tags": [...], "match_all": false}
      -> SearchResponse {"results": [{"memory": {"content": ..., "created_at": <epoch>, ...},
         "similarity_score": ..., "relevance_reason": ...}], "total_found": N}
      Verifiziert live gegen project-n8n-stack (90 Treffer, Content-Shape wie erwartet).
    Es gibt keinen limit-Parameter im Request-Schema -> Response kann mehrere Eintraege
    liefern; wir sortieren client-seitig nach created_at (neuestes zuerst) und nehmen nur
    den ersten Content. Kein Treffer/Fehler jeder Art -> "".
    """
    try:
        import sys as _s
        _s.path.insert(0, str(Path.home() / ".claude" / "scripts"))
        try:
            from memory_auth import auth_headers, base_url  # type: ignore
            base = base_url()
            hdrs = {"Content-Type": "application/json", **auth_headers()}
        except Exception:
            base = "http://127.0.0.1:8000"
            hdrs = {"Content-Type": "application/json"}

        body = json.dumps({"tags": [f"project-{project_slug}"], "match_all": False}).encode("utf-8")
        req = urllib.request.Request(f"{base}/api/search/by-tag", data=body, headers=hdrs, method="POST")
        with urllib.request.urlopen(req, timeout=MEMORY_FETCH_TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))

        results = data.get("results") or []
        if not isinstance(results, list) or not results:
            return ""

        def _created(item):
            mem = (item or {}).get("memory") or {}
            return mem.get("created_at") or 0

        results.sort(key=_created, reverse=True)
        top = (results[0] or {}).get("memory") or {}
        content = top.get("content") or ""
        return str(content).strip()[:1500]
    except Exception:
        pass
    return ""


def render(local_txt: str, mem_txt: str) -> str:
    """Reiner Merge/Format — keine I/O, damit ohne stdin/Netz testbar."""
    local_txt = (local_txt or "").strip()
    mem_txt = (mem_txt or "").strip()
    if not local_txt and not mem_txt:
        return ""
    parts = ["Resume nach Restart (RC-Session). Du setzt bestehende Arbeit fort — "
             "re-orientiere dich aktiv am folgenden Stand, statt der Nutzer zu fragen was zu tun ist:"]
    if local_txt:
        parts.append("## Lokaler letzter Stand (last.md):\n" + local_txt)
    if mem_txt and mem_txt != local_txt:
        parts.append("## mcp-memory (letzter Checkpoint):\n" + mem_txt)
    parts.append("Mach dort weiter wo aufgehoert. Bei einer echt neuen, unabhaengigen "
                 "der Nutzer-Anfrage: diesen Hinweis ignorieren.")
    return "\n\n".join(parts)
