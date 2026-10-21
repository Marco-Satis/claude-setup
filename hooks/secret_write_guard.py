#!/usr/bin/env python
"""PreToolUse Hook: blockt Secrets die CLAUDE in Dateien/Commands schreiben will.

Finding H-4 (TikTok-Audit 2026-07-20): secret_leak_detector.py bewacht nur den
User-Prompt-Kanal (UserPromptSubmit). Der Pfad 'Claude schreibt Token in Datei /
Bash-Command' (Anti-Patterns aus rules/secret-handling.md: Token in Code-Kommentar,
Token in URL-Parameter) war komplett unbewacht. Dieser Hook ist der zweite
Consumer der Single-Source ~/.claude/scripts/secret_patterns.json.

Verhalten:
  - Matcher: Write | Edit | MultiEdit | Bash (PreToolUse)
  - Scannt tool_input.content / new_string (auch MultiEdit-edits) / command
  - Bei Treffer: permissionDecision=deny (Claude soll den Wert NIE persistieren)
    + Append-Log nach ~/.claude/lessons/leaks.jsonl (Pattern-Name + SHA256-
    Hash-Prefix — NIEMALS der Wert selbst)
  - Ausnahmen: Ziel-Pfade unter ~/.claude/lessons/ sowie *.bak-Backups
    (des Nutzers Backup-Konvention <file>.bak.pre-<tag>.<ts>) werden nicht gescannt
  - Scannt bei Edit bewusst NUR new_string (nicht old_string) — Redaktions-Edits
    die ein Secret AUS einer Datei entfernen bleiben erlaubt.

Best-effort nach des Nutzers Hook-Standard: kaputtes/fehlendes stdin-JSON, Pattern-
Load-Fehler oder Log-Fehler duerfen den Tool-Call niemals crashen -> exit 0.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Unter dieser Textlaenge kann kein vollstaendiges Token enthalten sein
MIN_SCAN_LEN = 20

# SEC-004: Single-Source-of-Truth fuer Secret-Patterns
# (dritter Konsument neben secret_leak_detector.py + managed_agent_quickstart.ps1)
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

# S12 / E1 (2026-10-21): zusaetzliche Klassen aus secret_patterns.json:patterns_neu.
# Wirken NUR mit lokalem Flag (synct nicht); ohne Flag bytegleiches Verhalten.
_FLAG_NEU = Path.home() / ".claude" / "flags" / "secret_patterns_neu.on"
_FALLBACK_PATTERNS_NEU: list[tuple[str, str, str]] = [
    ("Discord Webhook", r"https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/(?:v\d+/)?webhooks/\d{15,22}/[A-Za-z0-9_\-]{40,}", "discord.com/api/webhooks/..."),
    ("Anthropic OAuth Token", r"\bsk-ant-o[ar]t\d{2}-[A-Za-z0-9_\-]{40,}", "sk-ant-o?t..."),
    ("PEM Private Key", r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----(?:\\[rn]|\s)+(?:[A-Za-z][A-Za-z0-9\-]*: [^\\\r\n]{1,200}(?:\\[rn]|\s)+){0,4}[A-Za-z0-9+/=]{40,}", "-----BEGIN ... PRIVATE KEY-----"),
    ("Tailscale Key", r"\btskey-[A-Za-z0-9][A-Za-z0-9_\-]{19,}", "tskey-..."),
    ("JWT", r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{16,}", "eyJ..."),
    ("Hugging Face Token", r"\bhf_[A-Za-z0-9]{30,}\b", "hf_..."),
]

# Tool-Namen die dieser Hook bewacht (alles andere -> sofort allow)
_GUARDED_TOOLS = {"Write", "Edit", "MultiEdit", "Bash"}


def _neu_aktiv() -> bool:
    """Flag fuer patterns_neu (S12) gesetzt? Fehler -> aus (altes Verhalten)."""
    try:
        return _FLAG_NEU.exists()
    except OSError:
        return False


def _load_patterns_neu() -> list[tuple[str, str, str]]:
    """patterns_neu aus JSON; bei Fehler oder leer: hartcodierte Ersatzliste."""
    try:
        data = json.loads(_PATTERNS_JSON.read_text(encoding="utf-8"))
        neu = data.get("patterns_neu", []) if isinstance(data, dict) else []
        if neu:
            return [(p["name"], p["regex"], p["display"]) for p in neu]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        pass
    return _FALLBACK_PATTERNS_NEU


def _load_patterns() -> list[tuple[str, str, str]]:
    """Lade Patterns aus JSON; bei Fehler Fallback auf hartcodierte Liste."""
    base = _load_patterns_basis()
    if _neu_aktiv():
        return base + _load_patterns_neu()
    return base


def _load_patterns_basis() -> list[tuple[str, str, str]]:
    """Bestandsklassen ('patterns'), unveraendert seit 2026-07-21."""
    try:
        data = json.loads(_PATTERNS_JSON.read_text(encoding="utf-8"))
        patterns = data.get("patterns", [])
        if patterns:
            return [(p["name"], p["regex"], p["display"]) for p in patterns]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        pass
    return _FALLBACK_PATTERNS


def _is_exempt_path(file_path: str) -> bool:
    """Ausnahme-Pfade: ~/.claude/lessons/ selbst + *.bak-Backups nicht scannen."""
    if not file_path:
        return False
    try:
        p = Path(file_path).expanduser()
        lessons_dir = (Path.home() / ".claude" / "lessons").resolve()
        try:
            resolved = p.resolve()
        except (OSError, RuntimeError):
            resolved = p
        if str(resolved).startswith(str(lessons_dir) + "/") or resolved == lessons_dir:
            return True
        name = p.name
        # des Nutzers Backup-Konvention: <file>.bak ODER <file>.bak.pre-<tag>.<ts>
        if name.endswith(".bak") or ".bak." in name:
            return True
    except (ValueError, OSError):
        pass
    return False


def hash_prefix(value: str) -> str:
    """SHA256 des vollen Werts -> erste 8 Hex-Chars (forensischer Identifier)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def log_block(pattern_name: str, prefix_hash: str, tool_name: str, target: str) -> None:
    """Append-Only-Log fuer Constraint-Violation-Tracking — nie der Wert selbst."""
    lessons_dir = Path.home() / ".claude" / "lessons"
    try:
        lessons_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "secret_write_blocked",
            "pattern_name": pattern_name,
            "prefix_hash": prefix_hash,
            "tool": tool_name,
            # target: nur Pfad bzw. Kanal-Label, niemals Command-/Content-Inhalt
            "target": target[:120],
        }
        with (lessons_dir / "leaks.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass  # Log-Fehler darf den Hook nicht crashen


def _collect_scan_texts(tool_name: str, tool_input: dict) -> tuple[list[str], str]:
    """Sammle zu scannende Texte + Target-Label je nach Tool."""
    texts: list[str] = []
    target = ""
    if tool_name == "Write":
        target = str(tool_input.get("file_path", "") or "")
        texts.append(str(tool_input.get("content", "") or ""))
    elif tool_name == "Edit":
        target = str(tool_input.get("file_path", "") or "")
        texts.append(str(tool_input.get("new_string", "") or ""))
    elif tool_name == "MultiEdit":
        target = str(tool_input.get("file_path", "") or "")
        edits = tool_input.get("edits", []) or []
        if isinstance(edits, list):
            for e in edits:
                if isinstance(e, dict):
                    texts.append(str(e.get("new_string", "") or ""))
    elif tool_name == "Bash":
        target = "bash_command"
        texts.append(str(tool_input.get("command", "") or ""))
    return texts, target


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    if not isinstance(data, dict):
        sys.exit(0)

    tool_name = str(data.get("tool_name", "") or "")
    if tool_name not in _GUARDED_TOOLS:
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        sys.exit(0)

    texts, target = _collect_scan_texts(tool_name, tool_input)

    # Ausnahme-Pfade nur fuer File-Tools (Bash hat kein file_path-Ziel)
    if tool_name in ("Write", "Edit", "MultiEdit") and _is_exempt_path(target):
        sys.exit(0)

    scan_text = "\n".join(t for t in texts if t)
    if len(scan_text) < MIN_SCAN_LEN:
        sys.exit(0)

    findings: list[tuple[str, str]] = []  # (pattern_name, prefix_hash)
    for name, regex, _display in _load_patterns():
        try:
            match = re.search(regex, scan_text)
        except re.error:
            continue  # kaputtes Einzel-Pattern darf den Rest nicht killen
        if match:
            h = hash_prefix(match.group(0))
            findings.append((name, h))
            log_block(name, h, tool_name, target)

    if not findings:
        sys.exit(0)

    names = ", ".join(sorted({n for n, _ in findings}))
    hashes = ", ".join(h for _, h in findings)
    if _neu_aktiv():
        # S12: Deny-Grund nach BAUPLAN_v4_anhang A12 (nur mit Flag)
        reason = (
            f"Secret-Muster {names} erkannt (Hash {hashes}); nichts geschrieben. "
            "Echter Wert (aus Datei, Ausgabe oder Nachricht uebernommen): Ort statt Wert referenzieren, z. B. ENV-Variable "
            "oder ~/.claude/secrets/<datei>.env (rules/secret-handling.md). "
            "Selbst erfundener Testwert: zur Laufzeit zusammensetzen, z. B. 'sk-ant-' + 'oat01-' + 'A'*95. "
            "Unklar, ob echt: Text so lassen und der Nutzer mit Hash und Zielpfad fragen. "
            "Protokoll: ~/.claude/lessons/leaks.jsonl (nur Muster + Hash)."
        )
    else:
        reason = (
            f"Secret-Pattern {names} erkannt (hash {hashes}) — Wert nicht in "
            "Files/Commands schreiben (rules/secret-handling.md). Stattdessen: "
            "ENV-Variable via Read-Host-Workflow / get_env() referenzieren, nie den "
            "Klartext-Wert persistieren. Geloggt in ~/.claude/lessons/leaks.jsonl "
            "(nur Pattern-Name + Hash)."
        )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            },
            ensure_ascii=False,
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
