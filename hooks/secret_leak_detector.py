#!/usr/bin/env python
"""UserPromptSubmit Hook: erkennt API-Keys / Tokens / Secrets im User-Prompt.

der Nutzer hat am 2026-05-16 versehentlich seinen Anthropic-API-Key in den Chat
gepostet. Lesson: passive Rule 4 ('Token-Push-Verbot') in CLAUDE.md reichte
nicht — der Leak landete trotzdem im Transcript, in PreCompact-Backups und
in Anthropics Server-Logs.

Dieser Hook ist Active-Enforcement: bei jedem User-Prompt scannt er nach
typischen Secret-Patterns. Bei Treffer wird eine SystemMessage zurueck-
gegeben die Claude (mich) anweist:
  1. den Wert NICHT in Tool-Calls / Bash-Commands wiederzuverwenden
  2. der Nutzer SOFORT zur Rotation aufzufordern
  3. nur Pattern-Type + Praefix-Hash zu logging, niemals den Wert selbst

Nicht-blockierend (kein exit 2) — der Nutzer soll seine Prompts senden koennen.
Aber das Lesson-Signal (Pattern-Type) wird in ~/.claude/lessons/leaks.jsonl
geloggt fuer Self-Learning Stufe 2 (Constraint-Violation-Tracking).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Token-Patterns — explizit, nur eindeutige Praefixe
# Reihenfolge: spezifischste zuerst, sonst greift generisches Pattern zu frueh
# Magic-Number-Q5-Fix: Mindest-Prompt-Laenge unter der Pattern-Suche skippt.
# 20 Zeichen weil kurze Replies wie "ja", "weiter", "ok danke" Pattern-Scans
# sparen und sowieso keine vollstaendigen Tokens enthalten koennen.
MIN_PROMPT_LEN = 20

# SEC-004 (2026-05-16): Single-Source-of-Truth fuer Secret-Patterns
# Patterns werden aus ~/.claude/scripts/secret_patterns.json geladen.
# Bei JSON-Lese-Fehler: Fallback auf hartcodierte Liste damit Hook nie ausfaellt.
_PATTERNS_JSON = Path.home() / ".claude" / "scripts" / "secret_patterns.json"

_FALLBACK_PATTERNS: list[tuple[str, str, str]] = [
    ("Anthropic API Key", r"\bsk-ant-api\d{2}-[A-Za-z0-9_\-]{40,}\b", "sk-ant-..."),
    ("OpenAI Project Key", r"\bsk-proj-[A-Za-z0-9_\-]{40,}\b", "sk-proj-..."),
    ("OpenAI API Key (legacy)", r"\bsk-(?!ant-|proj-)[A-Za-z0-9]{48}\b", "sk-..."),
    ("GitHub PAT Classic", r"\bghp_[A-Za-z0-9]{36}\b", "ghp_..."),
    ("GitHub Fine-grained PAT", r"\bgithub_pat_[A-Za-z0-9_]{82,}\b", "github_pat_..."),
    ("GitHub OAuth Token", r"\bgho_[A-Za-z0-9]{36}\b", "gho_..."),
    ("GitHub App Token", r"\bghs_[A-Za-z0-9]{36}\b", "ghs_..."),
    ("Discord Bot Token", r"\b(?!eyJ)[A-Za-z0-9_\-]{24,28}\.[A-Za-z0-9_\-]{6,8}\.[A-Za-z0-9_\-]{27,}\b", "<discord>"),
    ("AWS Access Key ID", r"\bAKIA[0-9A-Z]{16}\b", "AKIA..."),
    ("Slack Token", r"\bxox[abcdeprsv]-[A-Za-z0-9\-]{10,}\b", "xox?-..."),
    ("Google API Key", r"\bAIza[0-9A-Za-z_\-]{35}\b", "AIza..."),
]


def _load_patterns() -> list[tuple[str, str, str]]:
    """Lade Patterns aus JSON; bei Fehler Fallback auf hartcodierte Liste."""
    try:
        data = json.loads(_PATTERNS_JSON.read_text(encoding="utf-8"))
        patterns = data.get("patterns", [])
        if patterns:
            return [(p["name"], p["regex"], p["display"]) for p in patterns]
    except (OSError, json.JSONDecodeError, KeyError):
        pass
    return _FALLBACK_PATTERNS


PATTERNS: list[tuple[str, str, str]] = _load_patterns()


def hash_prefix(value: str) -> str:
    """Stable Hash des VOLLEN Werts - erste 8 Hex-Chars als Identifier.

    Fix S2 (2026-05-16): vorher Hash ueber erste 12 Chars - das machte alle
    Tokens mit gleichem Praefix (z.B. alle Anthropic-Keys: 'sk-ant-api03-')
    forensisch ununterscheidbar. Jetzt: voller Wert -> SHA256 -> erste 8 Hex.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def log_leak(pattern_name: str, prefix_hash: str, context_excerpt: str) -> None:
    """Append-Only-Log fuer Constraint-Violation-Tracking (Self-Learning Stufe 2)."""
    lessons_dir = Path.home() / ".claude" / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    log_file = lessons_dir / "leaks.jsonl"

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "secret_leak_in_user_prompt",
        "pattern_name": pattern_name,
        "prefix_hash": prefix_hash,
        # context_excerpt: max 40 chars, Wert maskiert
        "context_excerpt": context_excerpt[:40].replace("\n", " "),
    }
    try:
        with log_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        # Logging-Fehler darf User-Prompt nicht blockieren
        pass


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    prompt = data.get("prompt", "") or ""
    if not prompt or len(prompt) < MIN_PROMPT_LEN:
        sys.exit(0)

    findings: list[tuple[str, str, str]] = []  # (name, praefix-anzeige, prefix-hash)

    for name, regex, display in PATTERNS:
        for match in re.finditer(regex, prompt):
            value = match.group(0)
            h = hash_prefix(value)
            # Erste 7 Zeichen + "..." als sichtbares Mini-Snippet
            visible = value[:7] + "..." if len(value) > 10 else display
            findings.append((name, visible, h))
            # Excerpt fuer Log — Wert selbst durch [REDACTED] ersetzen
            excerpt = prompt[max(0, match.start() - 15) : match.start()] + "[REDACTED]"
            log_leak(name, h, excerpt)
            break  # nur erstes Match pro Pattern, sonst spammt der Log

    if not findings:
        sys.exit(0)

    # SystemMessage zusammenbauen — KEIN Token-Wert, nur Pattern-Name + Hash
    lines = ["[SECRET-LEAK-DETECTED] Im User-Prompt wurde mindestens ein Secret-Pattern gefunden:"]
    for name, visible, h in findings:
        lines.append(f"  - {name}: prefix={visible} hash={h}")
    lines.extend(
        [
            "",
            "Universal Rule 4 (erweitert 2026-05-16): Tokens niemals im Claude-Chat posten.",
            "Reaktion fuer Claude (mich):",
            "  1. Diesen Wert NICHT in Bash/Tool-Calls verwenden (selbst nicht zum Testen).",
            "  2. der Nutzer SOFORT zur Rotation auffordern (Console -> Revoke -> neuer Key).",
            "  3. Den Wert selbst NICHT in der Antwort wiederholen — nur Pattern-Type.",
            "  4. Sicheren Setz-Workflow vorschlagen: Read-Host + SetEnvironmentVariable.",
            "",
            "Ein Eintrag wurde in ~/.claude/lessons/leaks.jsonl geloggt (Pattern-Name + Hash, nicht der Wert).",
        ]
    )

    msg = "\n".join(lines)
    print(json.dumps({"systemMessage": msg}))


if __name__ == "__main__":
    main()
