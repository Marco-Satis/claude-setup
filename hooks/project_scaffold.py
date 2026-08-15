#!/usr/bin/env python
"""SessionStart-Hook: richtet fehlende Projektstruktur automatisch ein.

Wenn eine Session in einem Projekt-Verzeichnis OHNE CLAUDE.md startet, legt dieser
Hook eine vorgebaute Skelett-Struktur an (CLAUDE.md + PROGRESS.md + .gitignore) und
weist die Session an, die Platzhalter beim ersten Task mit echtem Projekt-Wissen zu
füllen. So ist jedes neue Projekt sofort konsistent eingerichtet.

SICHERHEIT (mehrere Gates, alle müssen passen, sonst leise raus):
  1. Toggle: ~/.claude/flags/no_auto_scaffold.flag existiert NICHT.
  2. cwd liegt UNTER einem Allowlist-Root (ALLOW_ROOTS) — nie Home/System/Temp.
  3. cwd ist NICHT der Allowlist-Root selbst (kein Scaffold des Containers).
  4. cwd ist kein interner/Junk-Ordner (.claude, node_modules, __pycache__, ...).
  5. CLAUDE.md existiert NICHT bereits (idempotent — nie überschreiben).
  6. cwd sieht nach echtem Projekt aus (Code-/Marker-Dateien vorhanden).

Schreibt NUR fehlende Dateien (atomic .tmp+os.replace), überschreibt nie. Loggt nach
~/.claude/logs/project_scaffold.jsonl. Crash-safe: jeder Fehler -> exit 0, kein
Session-Abbruch.

Input: SessionStart-Hook-JSON via stdin (Feld `cwd`). Output: stdout-Text -> Kontext.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

try:  # Windows-cp1252-Safety: stdout auf UTF-8 (Emoji/→/•/⚠)
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

HOME = Path.home()

# --- Konfiguration (anpassbar) ------------------------------------------------
# Nur unter diesen Wurzeln wird gescaffoldet. Erweitern bei Bedarf.
ALLOW_ROOTS = [
    HOME / "projects",
]
DISABLE_FLAG = HOME / ".claude" / "flags" / "no_auto_scaffold.flag"
TEMPLATE_DIR = HOME / ".claude" / "templates" / "project"
LOG_FILE = HOME / ".claude" / "logs" / "project_scaffold.jsonl"

# Ordnernamen, die nie ein Projekt-Root sind
EXCLUDE_NAMES = {
    ".claude", "node_modules", "__pycache__", ".git", ".ruff_cache",
    "venv", ".venv", "dist", "build", ".pytest_cache", ".mypy_cache",
    "_archive", "_archiv", "templates",
}
# Pfad-Fragmente, die auf interne/abgeleitete Verzeichnisse deuten
EXCLUDE_FRAGMENTS = ("/.claude/", "\\.claude\\", "/node_modules/", "\\node_modules\\",
                     "/.git/", "\\.git\\")

# Datei-Marker, die ein "echtes Projekt" signalisieren
MARKER_FILES = {
    "package.json", "pyproject.toml", "requirements.txt", "Cargo.toml",
    "go.mod", "pom.xml", "build.gradle", "Makefile", "setup.py", ".git",
}
MARKER_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".cs",
    ".rb", ".php", ".cpp", ".c", ".kt", ".swift", ".lua", ".sh", ".ps1",
}

# --- Inline-Fallbacks (falls Template-Datei fehlt) ----------------------------
FALLBACK_CLAUDE = """# {{PROJECT}} — Claude-Projekt-Anweisungen

> v0.1 (AUTO-SCAFFOLD {{DATE}}) | SKELETT — Platzhalter fuellen, dann diese Zeile entfernen.

## Pflicht-Regeln
1. Erst lesen, dann aendern (Always-Read-Never-Guess).
2. Backup vor Edit an gepflegten Files.
3. Atomic-Write fuer State/Config (.tmp + os.replace).
4. Secrets -> ENV + KeePass, nie committen/loggen/chatten.
5. PROGRESS.md aktuell halten.

## Stack / Architektur
<!-- TODO -->

## Run-Commands
<!-- TODO -->

## Pflicht-Anker
Erst lesen dann aendern - Backup vor Edit - Atomic-State - Secrets->KeePass - PROGRESS aktuell.
"""
FALLBACK_PROGRESS = """# PROGRESS — {{PROJECT}}

> Angelegt {{DATE}} (Auto-Scaffold).

## Status
<!-- TODO -->

## Offen / naechste Schritte
- [ ] <!-- TODO -->
"""
FALLBACK_GITIGNORE = (
    "__pycache__/\n*.pyc\n.ruff_cache/\nvenv/\n.venv/\n"
    ".env\n.env.*\n*.flag\n*.log\n*.out\n*.err\n_caps/\n"
    ".DS_Store\nThumbs.db\n*.bak\n*.bak.*\n"
)


def load_template(name: str, fallback: str) -> str:
    f = TEMPLATE_DIR / name
    try:
        if f.is_file():
            return f.read_text(encoding="utf-8")
    except Exception:
        pass
    return fallback


def under_allowed_root(d: Path) -> bool:
    for root in ALLOW_ROOTS:
        try:
            r = root.resolve()
            if d == r:
                return False  # Container selbst nicht scaffolden
            if r in d.parents:
                return True
        except Exception:
            continue
    return False


def looks_like_project(d: Path) -> bool:
    try:
        for entry in d.iterdir():
            nm = entry.name
            if entry.is_dir() and nm == ".git":
                return True
            if entry.is_file():
                if nm in MARKER_FILES:
                    return True
                if entry.suffix.lower() in MARKER_EXTS:
                    return True
    except Exception:
        return False
    return False


def atomic_write_if_absent(path: Path, content: str) -> bool:
    """Schreibt nur wenn path NICHT existiert. Atomic. True = geschrieben."""
    if path.exists():
        return False
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, path)
        return True
    except Exception:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        return False


def log_action(cwd: Path, created: list[str]) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": date.today().isoformat(), "cwd": str(cwd), "created": created}
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    if DISABLE_FLAG.exists():
        return 0

    raw_cwd = data.get("cwd") or os.getcwd()
    try:
        cwd = Path(raw_cwd).resolve()
    except Exception:
        return 0

    # Gates
    if cwd.name in EXCLUDE_NAMES or cwd.name.startswith("_") or cwd.name.startswith("."):
        return 0  # interne/Lib-/versteckte Dirs (z.B. _botcore, _archive)
    sp = str(cwd)
    if any(frag in sp for frag in EXCLUDE_FRAGMENTS):
        return 0
    if not under_allowed_root(cwd):
        return 0
    claude_md = cwd / "CLAUDE.md"
    if claude_md.exists():
        # Re-Nudge (Active-Enforcement): Skelett da, aber Platzhalter evtl. ungefuellt.
        try:
            head = claude_md.read_text(encoding="utf-8", errors="replace")[:2000]
        except Exception:
            return 0
        if "AUTO-SCAFFOLD" in head:
            print(
                f"📝 CLAUDE.md in {cwd.name}/ ist noch das Auto-Scaffold-Skelett "
                f"(ungefüllte <!-- TODO -->-Platzhalter). Bevor du die erste "
                f"projekt-bezogene Aufgabe bearbeitest: Projekt mappen "
                f"(Stack/Run-Commands/Konventionen, ggf. via Explore) und die "
                f"Platzhalter füllen, dann die AUTO-SCAFFOLD-Warnzeile entfernen. "
                f"Fertig = kein <!-- TODO --> mehr im File."
            )
        return 0  # nie überschreiben
    if not looks_like_project(cwd):
        return 0

    # Scaffold
    proj = cwd.name
    today = date.today().isoformat()

    def render(tmpl: str) -> str:
        return tmpl.replace("{{PROJECT}}", proj).replace("{{DATE}}", today)

    created: list[str] = []
    if atomic_write_if_absent(cwd / "CLAUDE.md",
                              render(load_template("CLAUDE.md.tmpl", FALLBACK_CLAUDE))):
        created.append("CLAUDE.md")
    if atomic_write_if_absent(cwd / "PROGRESS.md",
                              render(load_template("PROGRESS.md.tmpl", FALLBACK_PROGRESS))):
        created.append("PROGRESS.md")
    if atomic_write_if_absent(cwd / ".gitignore",
                              load_template("gitignore.tmpl", FALLBACK_GITIGNORE)):
        created.append(".gitignore")

    if not created:
        return 0

    log_action(cwd, created)
    print(
        f"🆕 Auto-Scaffold: Projektstruktur in {proj}/ angelegt — {', '.join(created)} "
        f"(waren nicht vorhanden).\n"
        f"Bevor du die erste projekt-bezogene Aufgabe bearbeitest: fülle die "
        f"CLAUDE.md-Platzhalter (Stack/Run-Commands/Konventionen — Projekt ggf. via "
        f"Explore mappen) und entferne dann die AUTO-SCAFFOLD-Warnzeile. "
        f"Fertig = kein <!-- TODO --> mehr im File.\n"
        f"Netcup-Offload-Pflichtregel: ist das Projekt offload-fähig (reiner Code/Doc, "
        f"keine lokale HW), nach dem Füllen die CLAUDE.md nach Netcup (~/projects/{proj}/ "
        f"bzw. das RC-WorkingDirectory) syncen UND den Dir trusten — sonst startet die "
        f"Netcup-RC-Session ohne Projekt-Kontext bzw. gar nicht (untrusted+CLAUDE.md = "
        f"keine Auto-Session). Siehe Memory netcup-offload-claudemd-trust-rule.\n"
        f"(Abschaltbar: Datei ~/.claude/flags/no_auto_scaffold.flag anlegen.)"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # nie die Session crashen
