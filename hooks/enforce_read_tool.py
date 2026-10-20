#!/usr/bin/env python
"""PreToolUse-Hook (Bash): blockt REINE Datei-Reads via Shell und erzwingt das Read-Tool.

der Nutzer 2026-06-05: setzt die `rules/subagent-file-reads.md`-Doktrin aktiv durch
(vorher rein passive Regel — entgegen der Active-Enforcement-Doktrin). Shell-Reads
via `cat`/`head`/`tail`/`Get-Content`/`gc` auf eine Datei triggern des Nutzers
Read-Deny-Security-Flag (p-a52a0b0780). Read-Tool umgeht das + integriert sich in
Permission-UI + File-State-Tracking.

Geblockt (exit 2 → Befehl wird NICHT ausgefuehrt): ein bare File-Read, z.B.
  `cat datei.py` · `head -n 20 x.md` · `tail x.log` · `Get-Content f` · `gc f`
  sowie PURE-READ-Formen von sed/awk (Fix H-8, 2026-07-21):
  `sed -n '1,50p' f` · `sed 's/a/b/' f` (ohne -i, Output nur ins Terminal)
  · `awk '{print}' f` · `awk -F: '{print $1}' f`.

NICHT geblockt (echte Verarbeitung/Monitoring — exit 0):
  - Pipe / Redirect / Command-Substitution: `cat f | grep x`, `cat > f`, `$(cat f)`
  - Heredoc: `cat <<EOF ... EOF`
  - `tail -f` / `tail -F` (Log-Follow, kein One-Shot-Read)
  - `sed -i` / `--in-place` (Edit, kein Read); sed/awk als Filter in Pipes
    hinter echten Befehlen (`git log | sed -n 1p`)
  - grep/rg GENERELL (Suche ist bewusst erlaubt — Doktrin subagent-file-reads.md
    erlaubt Grep/Glob explizit; Shell-grep ist Such-, kein Read-Werkzeug)
  - Alles andere (git, tests, build, python, ls, find, …)

Bash bleibt erlaubt fuer echte Befehle — nur das reine Datei-Lesen wird auf das
Read-Tool umgeleitet.
"""
from __future__ import annotations

import json
import re
import sys


def _sed_awk_file_args(stripped: str, consume_next: frozenset, script_flags: tuple) -> list:
    """Datei-Argumente eines sed/awk-Aufrufs bestimmen (Skript-Argument abziehen).

    Heuristik: Flags (`-...`) filtern; Flags in `consume_next` verbrauchen zusaetzlich
    das Folge-Token (z.B. `-e 'expr'`, `awk -v x=1`, `-F :`). Wurde das Skript nicht
    schon via Flag uebergeben (`-e`/`-f`/attached `-e'...'`), ist das ERSTE bare
    Token das Skript — alles danach sind Datei-Argumente.
    """
    toks = stripped.split()[1:]
    script_via_flag = False
    for t in toks:
        for f in script_flags:
            if t == f or t.startswith(f + "=") or (len(f) == 2 and len(t) > 2 and t.startswith(f)):
                script_via_flag = True
    files = []
    skip = False
    for t in toks:
        if skip:
            skip = False
            continue
        if t in consume_next:
            skip = True
            continue
        if t.startswith("-") and t != "-":
            continue
        if not script_via_flag:
            script_via_flag = True  # erstes bare Argument = sed/awk-Skript
            continue
        files.append(t)
    return files


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if data.get("tool_name") not in (None, "Bash"):
        # Nur Bash-Tool betrachten; andere Tools (inkl. Read) durchlassen.
        sys.exit(0)
    cmd = (data.get("tool_input", {}) or {}).get("command", "")
    if not isinstance(cmd, str) or not cmd.strip():
        sys.exit(0)

    # Verarbeitung/Output-Umlenkung/Substitution → erlaubt (kein reiner Read).
    if re.search(r"[|>]", cmd) or "<<" in cmd or "$(" in cmd or "`" in cmd:
        sys.exit(0)

    # Erster „echter" Token (führende Variablen-Assignments wie `FOO=bar cat x` überspringen).
    stripped = cmd.strip()
    stripped = re.sub(r"^(?:\w+=[^\s]*\s+)+", "", stripped)
    first = stripped.split(None, 1)[0] if stripped.split() else ""
    first = first.strip("'\"")  # gequotetes "cat" / '/usr/bin/cat' entklammern (Bypass-Luecke)
    base = first.rsplit("/", 1)[-1].lower().strip("'\"")  # /usr/bin/cat → cat

    READ_CMDS = {"cat", "head", "tail", "get-content", "gc", "type", "less", "more"}
    # grep/rg fehlen hier BEWUSST: Suche via Shell-grep bleibt erlaubt
    # (Doktrin subagent-file-reads.md erlaubt Grep/Glob als Such-Werkzeuge —
    # grep ist kein File-Read-Ersatz, sondern Pattern-Suche). Fix H-8 2026-07-21:
    # sed/awk PURE-READ-Formen werden jetzt wie cat/head/tail geblockt; sed -i
    # (Edit) und sed/awk als Pipe-Filter (oben schon exit 0) bleiben erlaubt.
    SED_NAMES = {"sed", "gsed"}
    AWK_NAMES = {"awk", "gawk", "mawk", "nawk"}

    if base in SED_NAMES:
        # sed -i / --in-place = In-Place-Edit, kein Read → erlaubt.
        if re.search(r"(^|\s)-(?:[a-zA-Z]*i\S*|-in-place(?:=\S*)?)(?=\s|$)", stripped):
            sys.exit(0)
        files = _sed_awk_file_args(
            stripped,
            consume_next=frozenset({"-e", "-f", "--expression", "--file"}),
            script_flags=("-e", "--expression", "-f", "--file"),
        )
        if not files:
            sys.exit(0)  # kein Datei-Argument (z.B. `sed --version`, stdin-Filter)
    elif base in AWK_NAMES:
        files = _sed_awk_file_args(
            stripped,
            consume_next=frozenset({"-f", "-v", "-F", "--file", "--assign", "--field-separator"}),
            script_flags=("-f", "--file"),
        )
        if not files:
            sys.exit(0)  # kein Datei-Argument (z.B. `awk --version`, stdin-Filter)
    elif base in READ_CMDS:
        # tail -f / -F = Log-Follow, kein One-Shot-Read → erlaubt.
        if base == "tail" and re.search(r"(^|\s)-[a-zA-Z]*[fF]", stripped):
            sys.exit(0)

        # Es muss ein Datei-Argument geben (sonst z.B. `cat` aus Pipe — schon oben abgefangen).
        rest = stripped.split(None, 1)[1] if len(stripped.split(None, 1)) > 1 else ""
        args = [a for a in rest.split() if not a.startswith("-")]
        if not args:
            sys.exit(0)
    else:
        sys.exit(0)

    sys.stderr.write(
        f"BLOCKED: reiner Datei-Read via Shell (`{base}`) — bitte das Read-Tool nutzen "
        f"(Get-Content/cat/head/tail/sed/awk-Reads triggern des Nutzers Read-Deny-Security-Flag). "
        f"rules/subagent-file-reads.md. Befehl: {stripped[:120]}\n"
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
