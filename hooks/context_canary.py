#!/usr/bin/env python
"""Stop-Hook: Context-Canary — erkennt stillen Instruktions-Drift vor der ersten Halluzination.

Technik nach Peter Steinberger (OpenClaw): eine Anweisung, die JEDE Antwort betrifft, wird zum
Sensor. Solange sie greift, ist die Session gesund; die erste Antwort ohne sie kommt typischerweise
ein bis zwei Turns bevor das Modell anfaengt, sichtbar falsch zu liegen.

der Nutzer-Entscheid 2026-08-12: zwei Canaries, Reaktion = warnen UND Checkpoint erzwingen.

1. STIL-CANARY (global, gated auf ~/.claude/.caveman-active)
   Der Caveman-Modus ist bereits eine "EVERY RESPONSE"-Anweisung — also ein Canary, der ohne
   zusaetzliches Rauschen in den Antworten auskommt. Gemessen wird Artikel- + Fuellwort-Dichte
   der Prosa (Code, Tabellen, URLs raus). Kippt der Stil still auf normale Prosa, steigt die Dichte.

   Kalibriert auf der Nutzer echten Transcripts (2026-08-12, 1457 Fenster-Vergleiche ueber alle
   Sessions): natuerliche Schwankung INNERHALB einer Session p95=+6.3, p99=+8.2, max=+9.6.
   Ein globaler Schwellwert taugt nicht — Caveman-Median 5.9 und Nicht-Caveman-Median 9.1
   ueberlappen im Band 4.5-13.5. Deshalb Vergleich gegen die SESSIONEIGENE Baseline.

2. NAMENS-CANARY (nur Loop-Sessions, gated auf Games/<dir>/LOOP_RUN.flag)
   Steinbergers Original, binaer statt heuristisch: die Antwort beginnt mit der Nutzer Namen. Kostet
   sichtbares Rauschen, deshalb nur dort, wo Drift real weh tut — autonome Bot-Operator-Schleifen,
   in denen niemand mitliest. Voraussetzung: die Regel steht in der CLAUDE.md/dem TICK_PROMPT des
   jeweiligen Spiels. Fehlt sie dort, meldet der Hook nichts (kein Alarm ohne Sensor).

Best-effort: darf eine Session NIE blockieren (alle Fehler -> exit 0).
Kill-Switch: touch ~/.claude/flags/context_canary.off

Stdin (Stop-Event): {transcript_path, session_id, cwd, ...}
Stdout: hoechstens ein JSON-Objekt {"systemMessage": "..."} (Hook-Protokoll).
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
try:
    import session_logger as sl
except Exception:
    sys.exit(0)

FLAG_OFF = Path.home() / ".claude" / "flags" / "context_canary.off"
CAVEMAN_ACTIVE = Path.home() / ".claude" / ".caveman-active"
GAMES_DIR = Path.home() / "Games"
STATE_FILE = Path.home() / ".claude" / "state" / "context_canary.json"
LOG_FILE = Path.home() / ".claude" / "logs" / "context_canary.jsonl"

# Schwelle aus der Kalibrierung: p99 der natuerlichen Schwankung (+8.2) abgerundet.
DRIFT_DELTA = 8.0
# Der Stil-Canary schaerft sich nur, wenn Caveman in dieser Session ueberhaupt gegriffen hat.
BASELINE_MAX = 7.0
# Kuerzere Antworten sind statistisch nicht bewertbar.
MIN_WORDS = 40
# Erst ab so vielen bewertbaren Antworten gibt es eine belastbare Baseline.
MIN_SAMPLES = 6
# Nach einer Warnung so viele Antworten Ruhe, bevor erneut gewarnt wird.
REARM_AFTER = 10

_ARTICLES = set("der die das den dem des ein eine einen einem eines einer the a an".split())
_FILLER = set((
    "eigentlich natuerlich natürlich gerne selbstverstaendlich selbstverständlich "
    "letztlich tatsaechlich tatsächlich sozusagen quasi grunde "
    "basically just really actually simply certainly"
).split())

_FENCE = re.compile(r"```.*?```", re.S)
_INLINE = re.compile(r"`[^`]*`")
_URL = re.compile(r"https?://\S+")
_WORD = re.compile(r"[A-Za-zÄÖÜäöüß]+")


def _prose_only(text: str) -> str:
    """Code, Inline-Code, URLs, Tabellen und Ueberschriften raus — nur Fliesstext bleibt.

    Ohne das misst der Canary Code-Kommentare und Markdown-Tabellen mit und schlaegt bei jeder
    code-lastigen Antwort aus.
    """
    t = _FENCE.sub(" ", text)
    t = _INLINE.sub(" ", t)
    t = _URL.sub(" ", t)
    keep = [ln for ln in t.split("\n") if not ln.lstrip().startswith(("|", "#", "- [", "> "))]
    return "\n".join(keep)


def _density(text: str) -> float | None:
    """Artikel- + doppelt gewichtete Fuellwort-Dichte pro 100 Woertern. None = nicht bewertbar."""
    words = _WORD.findall(_prose_only(text).lower())
    if len(words) < MIN_WORDS:
        return None
    articles = sum(1 for w in words if w in _ARTICLES)
    filler = sum(1 for w in words if w in _FILLER)
    return (articles + 2 * filler) / len(words) * 100


def _assistant_texts(records: list[dict]) -> list[str]:
    out: list[str] = []
    for rec in records:
        msg = rec.get("message") or {}
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            txt = content
        elif isinstance(content, list):
            txt = "\n".join(
                c.get("text") or "" for c in content
                if isinstance(c, dict) and c.get("type") == "text"
            )
        else:
            continue
        if txt.strip():
            out.append(txt)
    return out


def _loop_session(cwd: str) -> bool:
    """Laeuft in dieser Umgebung eine Bot-Operator-Schleife? (loopmode setzt LOOP_RUN.flag)"""
    try:
        here = Path(cwd).resolve()
        for parent in (here, *here.parents):
            if (parent / "LOOP_RUN.flag").exists():
                return True
        if GAMES_DIR.is_dir():
            return any(GAMES_DIR.glob("*/LOOP_RUN.flag"))
    except Exception:
        pass
    return False


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Nur die letzten 50 Sessions behalten — die Datei soll nicht wachsen.
        if len(state) > 50:
            state = dict(sorted(state.items(), key=lambda kv: kv[1].get("ts", ""))[-50:])
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _log(entry: dict) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _checkpoint(records: list[dict], project: str, session_id: str, reason: str) -> str:
    """Erzwungener Memory-Checkpoint — sichert den Stand VOR dem Kontextverlust.

    Reuse derselben Kette wie precompact_memory.py (Single-Source): build_session_summary,
    contains_secret als Gate, post_memory.
    """
    date_iso = datetime.now(timezone.utc).isoformat()
    try:
        summary = sl.build_session_summary(records, project, {
            "date": date_iso, "files_edited_sample": [], "files_edited_count": 0,
            "distinct_tools": [],
        })
    except Exception as e:
        return f"Checkpoint-Fehler ({str(e)[:60]})"

    leak, pattern = sl.contains_secret(summary)
    if leak:
        _log({"ts": date_iso, "event": "checkpoint_blocked_secret",
              "pattern_name": pattern, "session_id": session_id})
        return f"Checkpoint geblockt (Secret {pattern})"

    slug = re.sub(r"[^a-z0-9-]", "-", project.lower())[:40]
    ok, info = sl.post_memory({
        "content": summary,
        "tags": ["session-summary", "context-canary", f"project-{slug}"] + sl.extract_topic_tags(records),
        "memory_type": "observation",
        "metadata": {"session_id": session_id, "kind": "canary-checkpoint",
                     "reason": reason, "timestamp": date_iso},
    })
    return "Checkpoint gesetzt" if ok else f"Checkpoint fehlgeschlagen ({info})"


def main() -> None:
    if FLAG_OFF.exists():
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    transcript_path = data.get("transcript_path")
    session_id = data.get("session_id", "unknown")
    cwd = data.get("cwd") or os.getcwd()
    project = Path(cwd).name if cwd else "unknown"
    if not transcript_path or not Path(transcript_path).exists():
        sys.exit(0)

    records = sl._load_records(Path(transcript_path))
    if not records:
        sys.exit(0)
    texts = _assistant_texts(records)
    if not texts:
        sys.exit(0)

    state = _load_state()
    seen = state.get(session_id, {})
    if len(texts) - seen.get("warned_at", -REARM_AFTER) < REARM_AFTER:
        sys.exit(0)

    tripped: str | None = None

    # --- Namens-Canary (Loop-Sessions, binaer) ---------------------------------
    if _loop_session(cwd):
        head = texts[-1].lstrip()[:40].lower()
        armed = any("marco" in t.lstrip()[:40].lower() for t in texts[:-1][-5:])
        if armed and "marco" not in head:
            tripped = "Namens-Canary: die Antwort beginnt nicht mehr mit dem Namen"

    # --- Stil-Canary (global, gated auf Caveman) -------------------------------
    if tripped is None and CAVEMAN_ACTIVE.exists():
        scored = [d for d in (_density(t) for t in texts) if d is not None]
        if len(scored) >= MIN_SAMPLES:
            baseline = statistics.median(scored[: max(3, len(scored) // 3)])
            current = statistics.median(scored[-3:])
            if baseline <= BASELINE_MAX and current - baseline >= DRIFT_DELTA:
                tripped = (f"Stil-Canary: Prosa-Dichte {current:.1f} gegen Session-Baseline "
                           f"{baseline:.1f} (+{current - baseline:.1f}, Schwelle +{DRIFT_DELTA})")

    if tripped is None:
        sys.exit(0)

    result = _checkpoint(records, project, session_id, tripped)
    state[session_id] = {"warned_at": len(texts), "ts": datetime.now(timezone.utc).isoformat()}
    _save_state(state)
    _log({"ts": datetime.now(timezone.utc).isoformat(), "event": "canary_tripped",
          "session_id": session_id, "project": project, "reason": tripped, "checkpoint": result})

    print(json.dumps({"systemMessage":
                      f"[context_canary] Drift-Signal — {tripped}. {result}. "
                      f"Die Session hat womoeglich frueher gegebene Anweisungen verloren: "
                      f"laufenden Stand pruefen, bevor du weiterbaust."}))


if __name__ == "__main__":
    main()
