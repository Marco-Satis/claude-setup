#!/usr/bin/env python3
"""Spiegelt den oeffentlichen Teil von ~/.claude ins Repo claude-setup (der Nutzer-Auftrag 2026-10-20).

Ablauf: kopieren (Allow-/Denylist) -> bereinigen (Ersetzungen aus der privaten Map) -> pruefen
(Secret-Werte, verbotene Muster, Mails/Telefon/IBAN, gitleaks). Committen und pushen macht der
Aufrufer erst danach, ueber den normalen git-Weg mit Pre-Commit-Hooks.

    setup_repo_sync.py [--repo PFAD] [--dry-run] [--check-only]

Exit 0 sauber, 2 Befunde (nichts committen!), 3 Aufruf-/Umgebungsfehler.
Die Ersetzungs- und Verbotsliste liegt in ~/.claude/secrets/setup_repo_sanitize.json, weil sie die
privaten Originalwerte enthaelt; sie darf nie ins Repo.
"""
import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
SRC = HOME / ".claude"
MAP_FILE = SRC / "secrets" / "setup_repo_sanitize.json"

MIRROR_DIRS = ["skills", "agents", "hooks", "rules", "templates"]
DENY = {
    "skills/bewerbung",  # Lebenslauf-Generator mit Adresse/Telefon (Fund 2026-08-15)
    "skills/synced",     # vom claude.ai-Konto synchronisierte Plugin-Kopien, nicht des Nutzers Werk
    # Art. 9 DSGVO: das ADHS-Regelwerk erlaubt Rueckschluesse auf Gesundheit; draussen, bis der Nutzer entscheidet (2026-10-20)
    "skills/i-have-adhd", "skills/knapp", "hooks/knapp_de.py",
}
EXCLUDE = ["*.bak", "*.bak.*", "*.sync-conflict-*", "__pycache__", ".pytest_cache", "*.pyc", "_archive*",
           ".venv", "node_modules", "*.log", "*.jsonl", "MANIFEST.sha256*", "*.tmp", "*.orig", ".DS_Store",
           "review_learned.json", "review_proposals.json"]  # Laufzeitzustand der Review-Lernschleife
# Betriebs-Skripte: bewusst kuratiert (ziel -> quelle relativ zu ~/.claude); der Rest von scripts/ ist privat/infra
SCRIPTS = {
    "scripts/rc-launch.sh": "rc-launch.sh", "scripts/rc-watchdog.sh": "rc-watchdog.sh",
    "scripts/rc-mail.sh": "rc-mail.sh", "scripts/rc-fix-hints.sh": "rc-fix-hints.sh",
    "scripts/rc-trust-guard.py": "rc-trust-guard.py",
    "scripts/routine_audit.py": "scripts/routine_audit.py", "scripts/routine_md.sh": "scripts/routine_md.sh",
    "scripts/routine_wrap.sh": "scripts/routine_wrap.sh", "scripts/weekly_hook_suggest.sh": "scripts/weekly_hook_suggest.sh",
    "scripts/weekly_tool_scout.sh": "scripts/weekly_tool_scout.sh",
    "scripts/skill_trigger_eval.sh": "scripts/skill_trigger_eval.sh", "scripts/docx_render.py": "scripts/docx_render.py",
    "scripts/setup_repo_sync.py": "scripts/setup_repo_sync.py",
    # von Skills/Hooks im Repo vorausgesetzt (codex-msg, gate, websuche, rc-watchdog)
    "scripts/agent_msg.py": "scripts/agent_msg.py", "scripts/codex_call.py": "scripts/codex_call.py",
    "scripts/last30days.py": "scripts/last30days.py", "scripts/rc-liveness.py": "rc-liveness.py",
}
KEEP_REPO_ONLY = {"hooks/README.md"}  # Doku, die es nur im Repo gibt (Verdrahtungs-Referenz statt settings.json)
MAX_FILE = 2_000_000  # Bytes; groessere Dateien sind fast immer Fonts/Fixtures und werden einzeln gemeldet

GENERIC = {
    "mail": re.compile(r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|org)|users\.noreply\.github\.com|anthropic\.com\b)[A-Za-z0-9-]+\.[A-Za-z]{2,}"),
    "telefon": re.compile(r"(?:\+49|\b0049)[ /-]?\d{2,4}[ /-]?\d{4,}|\b01[5-7]\d[ /-]?\d{6,}"),
    "iban": re.compile(r"\bDE\d{2}(?: ?\d{4}){4} ?\d{2}\b"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
PUBLIC_VALUES = {"https://ntfy.sh", "https://ntfy.sh/"}  # oeffentliche Standardwerte in env-Dateien, kein Geheimnis
MAIL_OK = re.compile(r"noreply|no-reply|example|localhost|\.invalid$|@x\.y|user@|name@|you@|foo@|test@", re.I)


def excluded(rel: str) -> bool:
    parts = rel.split("/")
    return any(fnmatch.fnmatch(p, pat) for p in parts for pat in EXCLUDE)


def desired_files():
    """ziel-relativer Pfad -> Quelldatei"""
    out = {}
    for d in MIRROR_DIRS:
        base = SRC / d
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.is_symlink():
                continue
            rel = f"{d}/{p.relative_to(base).as_posix()}"
            if excluded(rel) or any(rel == x or rel.startswith(x + "/") for x in DENY):
                continue
            out[rel] = p
    for dst, src in SCRIPTS.items():
        p = SRC / src
        if p.is_file():
            out[dst] = p
    return out


def load_map():
    try:
        m = json.loads(MAP_FILE.read_text())
        return [(re.compile(a), b) for a, b in m["replace"]], [re.compile(f) for f in m["forbid"]]
    except (OSError, KeyError, ValueError) as e:
        print(f"Ersetzungs-Map fehlt/ungueltig: {MAP_FILE} ({e})", file=sys.stderr)
        sys.exit(3)


def secret_values():
    """Werte aus den env-Dateien: duerfen nie im Repo stehen (Mindestlaenge gegen Fehltreffer wie 'true')."""
    vals = set()
    files = [f for f in (SRC / "secrets").glob("*.env*") if not f.name.endswith(".example")]
    files += [HOME / "mcp-memory" / "mcp.env"]
    for f in files:
        try:
            for line in f.read_text(errors="replace").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    v = line.split("=", 1)[1].strip().strip("'\"")
                    if len(v) >= 8 and v not in PUBLIC_VALUES:
                        vals.add(v)
        except OSError:
            pass
    return vals


def sanitize(data: bytes, repl):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data, False
    text = text.replace("\r\n", "\n")  # Windows-Zeilenenden aus PC-Edits: im Repo einheitlich LF
    for rx, to in repl:
        text = rx.sub(to, text)
    return text.encode("utf-8"), True


def scan(repo: Path, forbid, secrets):
    findings = []
    for p in sorted(repo.rglob("*")):
        rel = p.relative_to(repo).as_posix()
        if not p.is_file() or rel.startswith(".git/") or rel == ".secrets.baseline":
            continue
        data = p.read_bytes()
        if len(data) > MAX_FILE:
            findings.append((rel, "gross", f"{len(data)} Bytes"))
        text = data.decode("utf-8", errors="replace")
        for v in secrets:
            if v in text:
                findings.append((rel, "secret-wert", f"Wert aus env-Datei (Laenge {len(v)})"))
        for rx in forbid:
            if rx.search(text):
                findings.append((rel, "verboten", rx.pattern))
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".avif", ".ttf", ".otf", ".woff", ".woff2", ".ico", ".gif"):
            continue
        for name, rx in GENERIC.items():
            for m in rx.finditer(text):
                hit = m.group(0)
                if name == "mail" and MAIL_OK.search(hit):
                    continue
                findings.append((rel, name, hit[:3] + "…"))  # nie den ganzen Wert ausgeben
    gl = shutil.which("gitleaks")
    if gl:
        # nur was ins Repo gehoert: .secrets.baseline (lokal, gitignored) enthaelt Hashes und schlaegt sonst an
        targets = [repo / d for d in MIRROR_DIRS + ["scripts"] if (repo / d).is_dir()] + [repo / "README.md"]
        for t in targets:
            r = subprocess.run([gl, "dir", str(t), "--no-banner", "--redact", "--exit-code", "9"],
                               capture_output=True, text=True)
            if r.returncode == 9:
                findings.append((f"(gitleaks {t.name})", "leak", (r.stdout + r.stderr).strip().splitlines()[-1][:200]))
    else:
        findings.append(("(gitleaks)", "fehlt", "gitleaks nicht installiert"))
    return findings


EVENT_ORDER = ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop",
               "StopFailure", "SubagentStop", "PreCompact", "SessionEnd", "Notification"]
HOOKS_INTRO = """# Hooks \u2014 Verdrahtung

Die `settings.json` ist nicht Teil dieses Repos: sie enth\u00e4lt maschinenspezifische Pfade
und Berechtigungen. Diese Tabelle ersetzt sie als Referenz \u2014 sie wird bei jedem Sync aus der
real laufenden Konfiguration erzeugt und zeigt, an welchem Event jeder Hook h\u00e4ngt.

Ein Hook wird eingeh\u00e4ngt, indem in `~/.claude/settings.json` unter `hooks.<Event>` ein
Eintrag mit `type: "command"` und dem Aufruf steht. R\u00fcckgabe \u00fcber stdout als JSON;
`{"systemMessage": "..."}` erscheint im n\u00e4chsten Turn als injizierte Notiz.
"""


def hook_purpose(path: Path) -> str:
    """Erste Zeile des Moduldocstrings bzw. des ersten Kommentars: kurzer Zweck fuer die Tabelle."""
    import ast
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return ""
    if path.suffix == ".py":
        try:
            doc = ast.get_docstring(ast.parse(text))
        except SyntaxError:
            doc = None
        if doc:
            return doc.strip().splitlines()[0][:140].replace("|", "/")
    for line in text.splitlines()[:15]:
        s = line.strip().lstrip("#/*").strip()
        if s and not s.startswith("!") and "coding" not in s:
            return s[:140].replace("|", "/")
    return ""


def hooks_readme(present) -> str:
    try:
        hooks = json.loads((SRC / "settings.json").read_text()).get("hooks", {})
    except (OSError, ValueError):
        return ""
    out, missing = [HOOKS_INTRO], set()
    for ev in EVENT_ORDER + sorted(set(hooks) - set(EVENT_ORDER)):
        rows = []
        for grp in hooks.get(ev, []):
            matcher = grp.get("matcher") or "\u2014"
            for h in grp.get("hooks", []):
                m = re.search(r"hooks/([A-Za-z0-9_.-]+)", h.get("command", ""))
                if not m:
                    continue
                name = m.group(1)
                if f"hooks/{name}" not in present:
                    missing.add(name)
                    continue
                timeout = h.get("timeout", "\u2014")  # Python 3.10: kein Backslash in f-String-Ausdruecken
                rows.append(f"| `{name}` | `{matcher}` | {timeout} | {hook_purpose(SRC / 'hooks' / name)} |")
        if rows:
            out += [f"\n## {ev}\n", "| Hook | Matcher | Timeout | Zweck |", "|---|---|---|---|", *rows]
    out.append("\n## Nicht in dieser Tabelle\n")
    if missing:
        out.append("Diese Hooks der laufenden Konfiguration fehlen bewusst (installationsgebunden oder pers\u00f6nlich): "
                   + ", ".join(f"`{n}`" for n in sorted(missing)) + ".\n")
    out.append("Die Dateien unter `hooks/tests/` sind Smoke-Tests der Hooks selbst und werden nicht eingeh\u00e4ngt.\n")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(HOME / "projects" / "claude-setup"))
    ap.add_argument("--dry-run", action="store_true", help="nur anzeigen, was sich aendern wuerde")
    ap.add_argument("--check-only", action="store_true", help="nichts kopieren, nur das Repo pruefen")
    a = ap.parse_args()
    repo = Path(a.repo).expanduser().resolve()
    if not (repo / ".git").is_dir():
        print(f"kein git-Repo: {repo}", file=sys.stderr)
        return 3
    repl, forbid = load_map()

    if not a.check_only:
        want = desired_files()
        added = changed = removed = 0
        for rel, src in want.items():
            data, _ = sanitize(src.read_bytes(), repl)
            dst = repo / rel
            old = dst.read_bytes() if dst.exists() else None
            if old == data:
                continue
            added += old is None
            changed += old is not None
            if not a.dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
                os.chmod(dst, src.stat().st_mode & 0o755)
            print(("NEU   " if old is None else "GEAEND") + f" {rel}")
        readme = hooks_readme(set(want))
        if readme:
            data, _ = sanitize(readme.encode("utf-8"), repl)
            dst = repo / "hooks" / "README.md"
            if not dst.exists() or dst.read_bytes() != data:
                changed += 1
                print("GEAEND hooks/README.md (aus settings.json erzeugt)")
                if not a.dry_run:
                    dst.write_bytes(data)
        managed = MIRROR_DIRS + ["scripts"]
        for p in sorted(repo.rglob("*")):
            rel = p.relative_to(repo).as_posix()
            if p.is_file() and rel.split("/")[0] in managed and rel not in want and rel not in KEEP_REPO_ONLY:
                removed += 1
                print(f"WEG   {rel}")
                if not a.dry_run:
                    p.unlink()
        if not a.dry_run:  # leere Ordner nach dem Loeschen entfernen
            for d in sorted({p for p in repo.rglob("*") if p.is_dir() and ".git" not in p.parts}, key=lambda x: -len(x.parts)):
                if not any(d.iterdir()):
                    d.rmdir()
        print(f"\nneu {added}, geaendert {changed}, entfernt {removed}" + (" (Trockenlauf)" if a.dry_run else ""))
        if a.dry_run:
            return 0

    findings = scan(repo, forbid, secret_values())
    for rel, kind, info in findings:
        print(f"BEFUND {kind:12} {rel}: {info}")
    print(f"Pruefung: {len(findings)} Befunde")
    return 2 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
