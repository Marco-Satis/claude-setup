#!/usr/bin/env python
"""Stop Hook: loggt Session-Statistiken + persistiert Tier-1-Session-Memory.

Stufe 1 der Self-Learning-Architektur (siehe
`Prompt optimizing/AUDIT_SETUP_2026-05-15/SELF_LEARNING_INTEGRATION.md`).

Erweitert 2026-05-18 fuer 2-Tier-Memory-Architektur (der Nutzer-Vision):
- Auto-Write Tier-1 Session-Memory in mcp-memory-service bei Heuristik-Match
  (>=5 User-Turns ODER >=1 Code-Edit ODER der Nutzer-Trigger im Transcript)
- Tags: session-summary, project-<slug>
- Secret-Scan vor Write (Re-Use der Patterns aus secret_leak_detector.py)

Was geloggt wird (pro Session, JSONL):
- Datum (UTC ISO), session_id, project, tool/file-Stats, Health-Marker

Was NICHT geloggt + NICHT persistiert wird:
- Tool-Outputs (volumioes)
- Prompt-Inhalte / der Nutzer-Eingaben (nur Zaehler + Topic-Hints fuer Memory)
- API-Keys oder andere Secrets (Pattern-Filter vor Memory-Write)

Output: append-only `~/.claude/lessons/sessions.jsonl`
        + optional POST to http://127.0.0.1:8000/api/memories (Tier-1)
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Re-Use der Secret-Patterns aus dem leak-Detector — Single-Source-of-Truth.
# Pfad: gleicher Hooks-Ordner.
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
try:
    from secret_leak_detector import PATTERNS as _SECRET_PATTERNS  # type: ignore
except Exception:
    _SECRET_PATTERNS = []

MAX_FILES_IN_SAMPLE = 10
MEMORY_SERVICE_URL = "http://127.0.0.1:8000/api/memories"
MEMORY_HTTP_TIMEOUT = 8  # Sekunden — Hook ist best-effort, kein Blocking

# G2-Down-Alert (Audit 2026-06-03): zwei Marker, von memory_start_probe gelesen.
# last_session_active = es lief ein Stop (der Nutzer arbeitet); last_capture_ok = ein
# Memory-Write klappte. Probe unterscheidet so "nicht genutzt" von "genutzt aber
# Writes failen still" (Service up, Write kaputt).
_STATE_DIR = Path.home() / ".claude" / "state"
_CAPTURE_OK = _STATE_DIR / "last_capture_ok.json"
_SESSION_ACTIVE = _STATE_DIR / "last_session_active.json"
# Offline-Buffer (2026-06-17): wenn der Server beim Stop-Hook offline ist, wird der
# Memory-Payload hier gepuffert (kein Datenverlust) und die woechentliche Routine
# 'memory-outbox-flush' (scripts/memory_outbox_flush.py) reicht ihn spaeter nach.
_OUTBOX = _STATE_DIR / "memory_outbox"

# Boot-robuste, NICHT-gesyncte lokale Resume-Notiz (Continuity 2026-07-19).
# Bewusst ~/.cache (NICHT ~/.claude oder cwd = Syncthing-synchron -> .sync-conflict).
_RC_STATE_DIR = Path.home() / ".cache" / "claude-rc-state"


def write_last_session(cwd: str, project: str, turn: dict, date_iso: str) -> None:
    """Schreibt atomisch eine kompakte Resume-Notiz pro cwd. Secret-gated,
    best-effort (crasht den Stop-Hook nie). Ueberlebt SIGTERM-Kill (im Gegensatz
    zum graceful SessionEnd-Rollup) und wird von rc-session-resume.py gelesen."""
    try:
        slug = re.sub(r"[^a-z0-9-]", "-", (cwd or "unknown").lower()).strip("-")[:80] or "unknown"
        lines = [f"# Last session — {project} ({date_iso[:16]}Z)"]
        if turn.get("intent"):
            lines.append(f"Letzte Anfrage: {turn['intent']}")
        if turn.get("files"):
            names = ", ".join(os.path.basename(p) for p in turn["files"][:10])
            lines.append(f"Zuletzt geaendert ({len(turn['files'])}): {names}")
        if turn.get("commits"):
            lines.append("Commits: " + " | ".join(str(c) for c in turn["commits"][:6]))
        if turn.get("stand"):
            lines.append(f"Stand: {str(turn['stand'])[:700]}")
        body = "\n".join(lines)
        leak, _pat = contains_secret(body)
        if leak:
            return
        d = _RC_STATE_DIR / slug
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / "last.md.tmp"
        tmp.write_text(body, encoding="utf-8")
        os.replace(tmp, d / "last.md")
    except Exception:
        pass


def _stamp_state(path: Path) -> None:
    """Atomic Best-Effort-Timestamp (epoch). Darf Hook nie crashen."""
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"ts": datetime.now(timezone.utc).timestamp()}),
                       encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        pass

# Heuristik-Schwellen fuer Tier-1-Persistenz
PERSIST_MIN_USER_TURNS = 5
MARCO_TRIGGERS = (
    "save as memory",
    "/memory-save",
    "save memory",
    "persistiere memory",
    "memory speichern",
    "merk dir das",
)

# Topic-Tag-Extraktion: explizite Keywords zu kanonischen Tags
TOPIC_KEYWORD_MAP = {
    "memory": "topic-memory",
    "mcp-memory-service": "topic-memory",
    "session-memory": "topic-memory",
    "discord": "topic-discord-bots",
    "minecraft": "topic-minecraft",
    "n8n": "topic-n8n",
    "pipeline": "topic-pipeline",
    "fastapi": "topic-fastapi",
    "footstep": "topic-footstep",
    "memory-architektur": "topic-memory-architecture",
    "memory-architecture": "topic-memory-architecture",
    "rcon": "topic-minecraft",
    "satisfactory": "topic-satisfactory",
    "tiktok": "topic-tiktok",
}

# Max-Laenge der Session-Memory Content-Body (UTF-8 Zeichen)
MEMORY_CONTENT_MAX = 1800


def _load_records(transcript_path: Path) -> list[dict]:
    """Transcript EINMAL lesen + parsen, dann an alle Auswerter geben.

    Perf-Fix 2026-06-04 (p-fffd6ec1f4): vorher oeffneten 6 Funktionen das
    Transcript je separat (~442ms/Pass -> ~2.7s/Stop bei 49MB). Jetzt 1 Pass.
    Skip blank/unparseable Zeilen (gleiche Toleranz wie die alten Einzel-Reader).
    Whole-Transcript (kein Tail): die Auswerter brauchen Gesamt-Stats
    (Turn-Count, Topics, alle Tools) — ein Tail wuerde Behavior aendern.
    """
    records: list[dict] = []
    try:
        with transcript_path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if isinstance(rec, dict):
                    records.append(rec)
    except Exception:
        pass
    return records


def count_user_turns(records: list[dict]) -> int:
    """Zaehlt user-role-Messages (der Nutzer-Turns) im vorgeparsten Transcript."""
    count = 0
    for rec in records:
        msg = rec.get("message") or {}
        if isinstance(msg, dict) and msg.get("role") == "user":
            # Nur echte User-Eingaben, keine Tool-Results
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                count += 1
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        count += 1
                        break
    return count


def detect_marco_trigger(records: list[dict]) -> bool:
    """Sucht im Transcript nach der Nutzer-Triggern fuer explizites Memory-Save."""
    for rec in records:
        msg = rec.get("message") or {}
        if not isinstance(msg, dict) or msg.get("role") != "user":
            continue
        content = msg.get("content")
        texts: list[str] = []
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    t = c.get("text") or ""
                    if t:
                        texts.append(t)
        for t in texts:
            lower = t.lower()
            for trig in MARCO_TRIGGERS:
                if trig in lower:
                    return True
    return False


def extract_topic_tags(records: list[dict], max_tags: int = 5) -> list[str]:
    """Extrahiert Topic-Tags aus dem Transcript via Keyword-Map."""
    found: set[str] = set()
    for rec in records:
        msg = rec.get("message") or {}
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        texts: list[str] = []
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    t = c.get("text") or ""
                    if t:
                        texts.append(t)
        for t in texts:
            lower = t.lower()
            for kw, tag in TOPIC_KEYWORD_MAP.items():
                if kw in lower:
                    found.add(tag)
                    if len(found) >= max_tags:
                        return sorted(found)
    return sorted(found)


def build_session_summary(
    records: list[dict],
    project: str,
    stats: dict,
) -> str:
    """Erstellt eine kompakte Summary aus Transcript-Inhalten + Stats."""
    # ALLE echten User-Turns einsammeln (gecappt) + letzten Assistant-Text als
    # "Stand". v2 2026-06-02: nicht mehr nur erste 3 — sonst kein resumebarer Stand.
    user_turns_text: list[str] = []
    last_assistant_text = ""
    for rec in records:
        msg = rec.get("message") or {}
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        text = ""
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    text = (c.get("text") or "").strip()
                    break
        if role == "user":
            # Skip auto-injected system reminders + slash-commands
            if (
                text
                and not text.startswith("<system-reminder>")
                and not text.startswith("<command-")
                and not text.startswith("Caveat:")
            ):
                user_turns_text.append(text[:200])
        elif role == "assistant" and text:
            last_assistant_text = text[:350]

    files_sample = stats.get("files_edited_sample", [])[:8]
    distinct_tools = stats.get("distinct_tools", [])[:10]
    first3 = user_turns_text[:3]
    last3 = user_turns_text[-3:] if len(user_turns_text) > 3 else []

    parts = [
        f"# Session Summary — {project}",
        f"Date: {stats.get('date', '')}",
        f"Tools: {', '.join(distinct_tools)}",
        f"Files edited ({stats.get('files_edited_count', len(files_sample))}): "
        f"{', '.join(os.path.basename(p) for p in files_sample)}",
        "",
        "## Erste Intents:",
    ]
    for i, t in enumerate(first3, 1):
        parts.append(f"  {i}. {t}")
    if last3:
        parts.append("")
        parts.append("## Zuletzt dran (letzte Intents):")
        for t in last3:
            parts.append(f"  - {t}")
    if last_assistant_text:
        parts.append("")
        parts.append(f"## Letzter Stand (Assistant): {last_assistant_text}")

    summary = "\n".join(parts)
    if len(summary) > MEMORY_CONTENT_MAX:
        summary = summary[: MEMORY_CONTENT_MAX - 3] + "..."
    return summary


# Auto-Trigger-Texte die KEIN echter Intent sind (Resume/Slash)
_NON_INTENT = (
    "continue from where you left off",
    "no response requested",
)

# Marker fuer memory_type-Erkennung im Assistant-Stand
_LESSON_MARK = ("lesson", "lehre", "gelernt", "merke")
_DECISION_MARK = ("entscheid", "decision", "gewählt", "gewaehlt", "wir nehmen", "chose")


def extract_last_turn(records: list[dict]) -> dict | None:
    """Extrahiert NUR den letzten Turn (seit der letzten echten User-Eingabe):
    Intent + Assistant-Stand + in DIESEM Turn geaenderte Files + Commits + Tools.
    Das ist die Basis fuer die inkrementelle Per-Turn-Memory (statt Ganzsession-Dump)."""
    msgs: list = []
    for rec in records:
        msg = rec.get("message") or {}
        if not isinstance(msg, dict):
            continue
        role = msg.get("role") or ""
        content = msg.get("content")
        text = ""
        tools: list[tuple[str, dict]] = []
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            chunks = []
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "text":
                    chunks.append(c.get("text") or "")
                elif c.get("type") == "tool_use":
                    tools.append((c.get("name", ""), c.get("input") or {}))
            text = "\n".join(ch for ch in chunks if ch).strip()
        msgs.append((role, text, tools))

    # letzte ECHTE User-Eingabe finden
    last_user = None
    for i in range(len(msgs) - 1, -1, -1):
        role, text, _ = msgs[i]
        if role != "user" or not text:
            continue
        low = text.lower()
        if (text.startswith("<system-reminder>") or text.startswith("<command-")
                or text.startswith("Caveat:") or text.startswith("<local-command")
                or any(n in low for n in _NON_INTENT)):
            continue
        last_user = i
        break
    if last_user is None:
        return None

    intent = msgs[last_user][1][:240]
    assistant_texts: list[str] = []
    files: set[str] = set()
    commits: list[str] = []
    tool_names: list[str] = []
    for role, text, tools in msgs[last_user + 1:]:
        if role == "assistant" and text:
            assistant_texts.append(text)
        for name, inp in tools:
            if name:
                tool_names.append(name)
            fp = inp.get("file_path") if isinstance(inp, dict) else None
            if name in ("Edit", "Write", "NotebookEdit") and fp:
                files.add(fp)
            if name == "Bash" and isinstance(inp, dict):
                cmd = inp.get("command", "") or ""
                if "git commit" in cmd:
                    m = re.search(r'-m\s*["\']([^"\']+)["\']', cmd)
                    commits.append(m.group(1)[:90] if m else "commit")
    stand = (assistant_texts[-1] if assistant_texts else "")[:700]
    return {
        "intent": intent,
        "stand": stand,
        "files": sorted(files),
        "commits": commits,
        "tools": tool_names,
    }


def build_turn_note(project: str, turn: dict, date_iso: str) -> tuple[str, str]:
    """Baut die Per-Turn-Memory + erkennt memory_type. Returns (content, mtype)."""
    parts = [f"# Turn-Delta — {project} ({date_iso[:16]})"]
    if turn["intent"]:
        parts.append(f"Intent: {turn['intent']}")
    if turn["files"]:
        names = ", ".join(os.path.basename(p) for p in turn["files"][:10])
        parts.append(f"Geaendert ({len(turn['files'])}): {names}")
    if turn["commits"]:
        parts.append("Commits: " + " | ".join(turn["commits"][:6]))
    if turn["tools"]:
        uniq = sorted(set(turn["tools"]))
        parts.append(f"Tools: {', '.join(uniq[:12])}")
    if turn["stand"]:
        parts.append(f"Stand: {turn['stand']}")
    content = "\n".join(parts)
    if len(content) > MEMORY_CONTENT_MAX:
        content = content[: MEMORY_CONTENT_MAX - 3] + "..."

    # memory_type NUR aus dem Assistant-Stand ableiten, NICHT aus der Nutzer Intent
    # — sonst taggt ein „Lesson"/„Entscheidung" in der User-Eingabe den Turn-Delta
    # faelschlich als learning/decision (landet sonst im graphify-Tier-Scope).
    low = (turn["stand"] or "").lower()
    if any(m in low for m in _LESSON_MARK):
        mtype = "learning"
    elif any(m in low for m in _DECISION_MARK):
        mtype = "decision"
    else:
        mtype = "observation"
    return content, mtype


def contains_secret(text: str) -> tuple[bool, str | None]:
    """Re-Use der Secret-Patterns. Returns (gefunden, pattern-name)."""
    for name, regex, _ in _SECRET_PATTERNS:
        if re.search(regex, text):
            return True, name
    return False, None


_MEMORY_HEALTH_URL = "http://127.0.0.1:8000/api/health"
_MEMORY_HEALTH_TIMEOUT = 2  # Fast-Fail-Gate (Audit M3): bounded 2s statt 8s/POST
_health_cache = {"checked": False, "up": False}


def _memory_reachable() -> bool:
    """Einmaliger Health-Check (2s), pro Prozess gecacht.

    Verhindert dass ein haengender Memory-Service jeden post_memory-Call die
    vollen 8s blockiert — bei 2 Calls/Turn (per-turn + Checkpoint) sonst bis 16s
    auf JEDEM Stop. Down/connection-refused failt eh schnell; der Gate deckt den
    'up aber haengt'-Fall ab. (Audit-Fund M3 2026-06-03.)
    """
    if _health_cache["checked"]:
        return _health_cache["up"]
    up = False
    try:
        with urllib.request.urlopen(_MEMORY_HEALTH_URL, timeout=_MEMORY_HEALTH_TIMEOUT) as r:
            up = (getattr(r, "status", 200) == 200)
    except Exception:
        up = False
    _health_cache["checked"] = True
    _health_cache["up"] = up
    return up


# Stufe-2 Memory-Auth + zentrale Base-URL (Netcup-Cutover). X-API-Key wenn MCP_API_KEY
# gesetzt, sonst {} (anonym). Import-Fail -> leere Headers + localhost (headless-safe).
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path.home() / ".claude" / "scripts"))
try:
    from memory_auth import auth_headers as _mem_auth_headers, base_url as _mem_base_url
except Exception:
    def _mem_auth_headers() -> dict:
        return {}
    def _mem_base_url() -> str:
        return "http://127.0.0.1:8000"

# Override der Default-Konstanten (oben) auf die zentrale Base-URL.
MEMORY_SERVICE_URL = f"{_mem_base_url()}/api/memories"
_MEMORY_HEALTH_URL = f"{_mem_base_url()}/api/health"


def _buffer_payload(payload: dict, reason: str) -> None:
    """Server offline -> Payload lokal nach _OUTBOX puffern (atomic, best-effort).
    Die Routine 'memory-outbox-flush' reicht ihn spaeter nach. Darf nie crashen."""
    try:
        _OUTBOX.mkdir(parents=True, exist_ok=True)
        meta = payload.get("metadata") or {}
        sid = re.sub(r"[^A-Za-z0-9-]", "", str(meta.get("session_id", "x")))[:16]
        kind = re.sub(r"[^A-Za-z0-9-]", "", str(meta.get("kind", "mem")))[:20]
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        fname = f"{ts}-{kind}-{sid}.json"
        rec = {
            "payload": payload,
            "reason": reason,
            "buffered_at": datetime.now(timezone.utc).isoformat(),
            "attempts": 0,
        }
        tmp = _OUTBOX / (fname + ".tmp")
        tmp.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, _OUTBOX / fname)
    except Exception:
        pass


def post_memory(payload: dict) -> tuple[bool, str]:
    """POST an mcp-memory-service. Returns (success, info)."""
    if not _memory_reachable():
        _buffer_payload(payload, "offline: health-gate")
        return False, "service-unreachable (health-gate, gepuffert)"
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            MEMORY_SERVICE_URL,
            data=data,
            headers={"Content-Type": "application/json", **_mem_auth_headers()},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=MEMORY_HTTP_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
            except Exception:
                return False, f"unparseable response: {body[:120]}"
            if parsed.get("success") is True and parsed.get("content_hash"):
                _stamp_state(_CAPTURE_OK)  # G2: Write klappte
                return True, parsed["content_hash"][:12]
            # Duplicate handling: 200 + success=false + 'duplicate' in message
            msg_l = (parsed.get("message") or "").lower()
            if "duplicate" in msg_l:
                _stamp_state(_CAPTURE_OK)  # G2: Service erreichbar + akzeptiert
                return True, "duplicate-existing"
            return False, f"service-rejected: {parsed.get('message', '?')}"
    except urllib.error.HTTPError as e:
        # p-3ef1bab84f: degraded (kein Crash) + Auth-Fail klar labeln, nicht als
        # 'network' verschleiern -> Stufe-2-Key-Misconfig wird im Result sichtbar.
        if e.code in (401, 403):
            _buffer_payload(payload, f"auth-fail: http {e.code}")
            return False, "degraded: memory-auth (Stufe-2 Key fehlt/falsch in ENV?, gepuffert)"
        return False, f"degraded: http {e.code}"
    except urllib.error.URLError as e:
        _buffer_payload(payload, "offline: network")
        return False, f"degraded: network ({e}) [gepuffert]"
    except Exception as e:
        return False, f"unexpected: {e}"


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    transcript_path = data.get("transcript_path")
    session_id = data.get("session_id", "unknown")
    cwd = data.get("cwd") or os.getcwd()
    project_name = Path(cwd).name if cwd else "unknown"

    if not transcript_path:
        sys.exit(0)
    tp = Path(transcript_path)
    if not tp.exists():
        sys.exit(0)

    tool_count = 0
    distinct_tools: set[str] = set()
    files_edited: set[str] = set()
    read_count = 0
    edit_write_count = 0
    read_files: set[str] = set()
    re_read_after_edit = 0

    # Transcript EINMAL parsen (vorher 6x separat -> ~2.7s/Stop bei 49MB).
    # Dieselbe records-Liste speist Stats-Loop UND den Memory-Block. (p-fffd6ec1f4)
    records = _load_records(tp)
    try:
        for rec in records:
            msg = rec.get("message", {})
            if not isinstance(msg, dict):
                continue
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") != "tool_use":
                    continue
                tool_count += 1
                tname = c.get("name", "")
                if tname:
                    distinct_tools.add(tname)
                inp = c.get("input", {}) or {}
                fp = inp.get("file_path")
                if tname == "Read" and fp:
                    if fp in files_edited:
                        re_read_after_edit += 1
                    read_files.add(fp)
                    read_count += 1
                elif tname in ("Edit", "Write", "NotebookEdit") and fp:
                    files_edited.add(fp)
                    edit_write_count += 1
    except Exception:
        # NICHT sys.exit — partielle Stats sind ok; Memory-Block nutzt dieselbe
        # records-Liste unabhaengig weiter.
        pass

    read_then_verify_ratio = (
        len(files_edited & read_files) / len(files_edited)
        if files_edited
        else None
    )

    entry = {
        "date": datetime.now(tz=timezone.utc).isoformat(),
        "session_id": session_id,
        "project": project_name,
        "tool_count": tool_count,
        "distinct_tools_count": len(distinct_tools),
        "distinct_tools": sorted(distinct_tools),
        "read_count": read_count,
        "edit_write_count": edit_write_count,
        "files_edited_count": len(files_edited),
        "files_edited_sample": sorted(files_edited)[:MAX_FILES_IN_SAMPLE],
        "read_then_verify_ratio": (
            round(read_then_verify_ratio, 3)
            if read_then_verify_ratio is not None
            else None
        ),
        "re_read_after_edit_count": re_read_after_edit,
    }

    lessons_dir = Path.home() / ".claude" / "lessons"
    try:
        lessons_dir.mkdir(parents=True, exist_ok=True)
        log_file = lessons_dir / "sessions.jsonl"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        # Stop-Flow nicht blockieren — Logger ist best-effort.
        # Fix 2026-05-29: Fehler nach stderr (nicht stdout) — sonst landeten bei
        # Log-Fail UND Memory-Write ZWEI JSON-Objekte auf stdout (Hook-Protokoll
        # erwartet genau eines). stderr ist sichtbar in Logs, stört das Protokoll nicht.
        print(f"session_logger Log-Fehler (ignoriert): {e}", file=sys.stderr)
        # NICHT exit — Memory-Write trotzdem versuchen

    # === Auto-Memory (der Nutzer 2026-06-02: "nach jedem Output automatisch") ===
    # Zwei Schichten: (1) Per-Turn-Delta bei JEDEM substanziellen Output =
    # inkrementelle Wissens-Erfassung; (2) periodischer Ganzsession-Checkpoint
    # alle 5 Turns (statt jeden Turn -> kein Dup-Bloat).
    notes: list[str] = []

    def _log_jsonl(name: str, rec: dict) -> None:
        try:
            with (lessons_dir / name).open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass

    try:
        _stamp_state(_SESSION_ACTIVE)  # G2: ein Stop lief = der Nutzer arbeitet
        user_turns = count_user_turns(records)
        marco_triggered = detect_marco_trigger(records)
        project_slug = re.sub(r"[^a-z0-9-]", "-", project_name.lower())[:40]
        topic_tags = extract_topic_tags(records)

        # --- (1) Per-Turn-Delta ---
        turn = extract_last_turn(records)
        if turn:
            write_last_session(cwd, project_name, turn, entry["date"])
        substantive = bool(turn) and (
            bool(turn["files"]) or bool(turn["commits"]) or marco_triggered
            or len(turn["stand"]) > 600 or len(turn["tools"]) >= 3
        )
        if turn and substantive:
            content, mtype = build_turn_note(project_name, turn, entry["date"])
            leak, pat = contains_secret(content)
            if leak:
                _log_jsonl("leaks.jsonl", {
                    "timestamp": entry["date"], "event": "secret_in_turn_delta_blocked",
                    "pattern_name": pat, "session_id": session_id, "project": project_name})
                notes.append(f"turn-delta blocked (secret {pat})")
            else:
                tags = ["session-stand", "auto-captured", f"project-{project_slug}"] + topic_tags
                if marco_triggered:
                    tags.append("marco-trigger")
                ok, info = post_memory({
                    "content": content, "tags": tags, "memory_type": mtype,
                    "conversation_id": session_id,  # bypasst Semantik-Dedup (inkrementell)
                    "metadata": {
                        "session_id": session_id, "kind": "turn-delta",
                        "files": len(turn["files"]), "commits": len(turn["commits"]),
                        "timestamp": entry["date"],
                    },
                })
                notes.append(f"turn-delta {('ok ' + info) if ok else ('fail ' + info)}")
                if not ok:
                    _log_jsonl("memory_write_failures.jsonl", {
                        "timestamp": entry["date"], "session_id": session_id,
                        "project": project_name, "kind": "turn-delta", "info": str(info)[:120]})

        # --- (2) Periodischer Ganzsession-Checkpoint (alle 5 Turns) ---
        if marco_triggered or (user_turns >= PERSIST_MIN_USER_TURNS and user_turns % 5 == 0):
            summary = build_session_summary(records, project_name, entry)
            leak, pat = contains_secret(summary)
            if leak:
                _log_jsonl("leaks.jsonl", {
                    "timestamp": entry["date"], "event": "secret_in_session_summary_blocked",
                    "pattern_name": pat, "session_id": session_id, "project": project_name})
                notes.append(f"checkpoint blocked (secret {pat})")
            else:
                tags = ["session-summary", f"project-{project_slug}"] + topic_tags
                if marco_triggered:
                    tags.append("marco-trigger")
                ok, info = post_memory({
                    "content": summary, "tags": tags, "memory_type": "observation",
                    "metadata": {
                        "session_id": session_id, "kind": "checkpoint",
                        "user_turns": user_turns, "tool_count": tool_count,
                        "files_edited_count": len(files_edited), "code_edits": edit_write_count,
                        "timestamp": entry["date"],
                    },
                })
                notes.append(f"checkpoint {('ok ' + info) if ok else ('fail ' + info)}")
                if not ok:
                    _log_jsonl("memory_write_failures.jsonl", {
                        "timestamp": entry["date"], "session_id": session_id,
                        "project": project_name, "kind": "checkpoint", "info": str(info)[:120]})

        if notes:
            print(json.dumps({"systemMessage": "[session_logger] " + " · ".join(notes)}))
    except Exception as e:
        print(json.dumps({"systemMessage":
                          f"session_logger Memory-Block Fehler ({type(e).__name__}): {str(e)[:80]}"}))
        sys.exit(0)


if __name__ == "__main__":
    main()
