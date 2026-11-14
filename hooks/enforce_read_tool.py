#!/usr/bin/env python
"""PreToolUse-Hook (Bash): blockt REINE Datei-Reads via Shell und erzwingt das Read-Tool.

der Nutzer 2026-06-05: setzt die `rules/subagent-file-reads.md`-Doktrin aktiv durch
(vorher rein passive Regel — entgegen der Active-Enforcement-Doktrin). Shell-Reads
via `cat`/`head`/`tail`/`Get-Content`/`gc` auf eine Datei triggern des Nutzers
Read-Deny-Security-Flag (p-a52a0b0780). Read-Tool umgeht das + integriert sich in
Permission-UI + File-State-Tracking.

v2 (2026-11-14, der Nutzer „1 bis 5 ja“ 10:46, Messung REGEL_EINHALTUNG_2026-11-14.md):
Bisher liess der Hook jeden Befehl mit `|`, `>`, `$(` oder mehreren Gliedern durch und
fing so nur 9 von 154 Shell-Reads. Jetzt wird die Befehlskette zerlegt (`;`, `&&`, `||`,
`&`, Zeilenumbruch, Klammern) und JEDES Glied geprueft:
  `cd x && sed -n 1,20p f` · `cat f 2>/dev/null` · `head f; tail g` · `echo; cat f`
  · `if …; then cat f; fi` · `for f in …; do head -3 "$f"; done`  → geblockt.

Geblockt (exit 2) wird ein Glied, das allein steht (keine Pipe) und eine Datei liest:
  `cat f` · `head -n 20 x.md` · `tail x.log` · `less/more f` · `Get-Content f` · `gc f`
  · `sed -n '1,50p' f` · `sed 's/a/b/' f` (ohne -i) · `awk '{print $1}' f` (nur print)
  Stderr-Umleitungen (`2>/dev/null`, `2>&1`) aendern daran nichts.

NICHT geblockt (exit 0):
  - Pipes: `git log | head`, `cmd | sed …`, auch `cat f | grep x` (Verarbeitung)
  - stdout in eine Datei: `cat a b > c`, `cat f >> g`, `cat > f <<EOF`
  - Heredoc/Herestring: `cat <<EOF … EOF` (Heredoc-Inhalte werden nicht geprueft)
  - Command-/Prozess-Substitution: `x=$(cat f)`, `diff <(cat a) <(cat b)`
  - `tail -f/-F`, `sed -i`, awk mit echter Logik (`awk '{s+=$1} END{print s}' f`)
  - `sudo`/`doas`/`su` (das Read-Tool kann Root-Dateien nicht lesen), `bash -c '…'`
  - grep/rg (Suche ist erlaubt), `type <befehl>` (bash-Builtin), alles andere
Best-effort: jeder interne Fehler -> exit 0 (Session-Betrieb geht vor).
Regressionstests: hooks/tests/test_enforce_read_tool.py
"""
from __future__ import annotations

import json
import re
import shlex
import sys

READ_CMDS = {"cat", "head", "tail", "get-content", "gc", "less", "more", "bat"}
SED_NAMES = {"sed", "gsed"}
AWK_NAMES = {"awk", "gawk", "mawk", "nawk"}
PRIV = {"sudo", "doas", "su", "pkexec", "runuser"}
WRAPPERS = {"command", "nice", "nohup", "stdbuf", "env", "ionice", "time", "timeout"}
KEYWORDS = {"{", "}", "!", "then", "do", "else", "elif", "time"}
SUBST = "__SUBST__"


def _sed_awk_split(toks: list, consume_next: frozenset, script_flags: tuple) -> tuple:
    """-> (skript_oder_None, [datei-argumente]) eines sed/awk-Aufrufs (toks ohne Befehlsnamen).

    Flags (`-...`) filtern; Flags in `consume_next` verbrauchen das Folge-Token (`-e 'expr'`,
    `awk -v x=1`, `-F :`). Kommt das Skript nicht per Flag, ist das ERSTE bare Token das Skript.
    """
    script = None
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
            script_via_flag = True
            script = t
            continue
        files.append(t)
    return script, files


# Kompatibilitaet zur v1-Signatur (falls ein anderes Skript sie importiert)
def _sed_awk_file_args(stripped: str, consume_next: frozenset, script_flags: tuple) -> list:
    return _sed_awk_split(stripped.split()[1:], consume_next, script_flags)[1]


def strip_heredocs(cmd: str) -> str:
    """Heredoc-Koerper entfernen (`<<EOF … EOF`, `<<-'X' … X`); der Marker bleibt stehen."""
    out = cmd
    for _ in range(10):
        m = re.search(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z_0-9]*)\1[^\n]*\n", out)
        if not m:
            break
        tag = m.group(2)
        end = re.compile(r"^\s*" + re.escape(tag) + r"\s*$", re.M)
        e = end.search(out, m.end())
        stop = e.end() if e else len(out)
        out = out[:m.end()] + out[stop:]
        # Marker entschaerfen, damit dieselbe Stelle nicht erneut matcht
        out = out[:m.start()] + "<<HEREDOC " + out[m.end():]
    return out


def replace_substitutions(cmd: str) -> str:
    """$(…), `…`, <(…), >(…) durch einen Platzhalter ersetzen (deren Ausgabe wird verarbeitet)."""
    for _ in range(20):
        m = re.search(r"(?:\$|<|>)\(([^()]*)\)", cmd)
        if not m:
            break
        cmd = cmd[:m.start()] + SUBST + cmd[m.end():]
    for _ in range(20):
        m = re.search(r"`[^`]*`", cmd)
        if not m:
            break
        cmd = cmd[:m.start()] + SUBST + cmd[m.end():]
    return cmd


def split_chain(text: str) -> list:
    """Quote-aware Zerlegung -> Liste von Pipelines, jede eine Liste von Befehls-Strings.

    Trennt Pipelines an `;` `&&` `||` `&` Zeilenumbruch `(` `)`, Befehle innerhalb an `|`/`|&`.
    `&` in Umleitungen (`2>&1`, `&>f`, `>&2`) trennt nicht.
    """
    pipelines, cur_pipe, cur = [], [], []
    q = None
    esc = False
    i, n = 0, len(text)

    def end_cmd():
        s = "".join(cur).strip()
        cur.clear()
        if s:
            cur_pipe.append(s)

    def end_pipe():
        end_cmd()
        if cur_pipe:
            pipelines.append(list(cur_pipe))
        cur_pipe.clear()

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        prev = text[i - 1] if i > 0 else ""
        if esc:
            cur.append(ch)
            esc = False
        elif ch == "\\" and q != "'":
            cur.append(ch)
            esc = True
        elif q:
            cur.append(ch)
            if ch == q:
                q = None
        elif ch in ("'", '"'):
            q = ch
            cur.append(ch)
        elif ch == "|":
            if nxt == "|":
                end_pipe()
                i += 1
            else:
                end_cmd()
                if nxt == "&":
                    i += 1
        elif ch == "&":
            if nxt == "&":
                end_pipe()
                i += 1
            elif prev in "<>" or nxt == ">":
                cur.append(ch)
            else:
                end_pipe()
        elif ch in (";", "\n", "(", ")"):
            end_pipe()
        else:
            cur.append(ch)
        i += 1
    end_pipe()
    return pipelines


def _looks_like_path(t: str) -> bool:
    return bool(re.search(r"[/\\]|\.\w{1,6}$", t))


def check_command(cmd: str):
    """-> Befehlsname, wenn das Glied ein reiner Datei-Read ist, sonst None."""
    try:
        toks = shlex.split(cmd, posix=True)
    except ValueError:
        return None
    while toks and toks[0] in KEYWORDS:
        toks = toks[1:]
    while toks and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*=.*", toks[0]):
        toks = toks[1:]
    if not toks:
        return None
    # Wrapper ueberspringen (sudo & Co. -> erlaubt: das Read-Tool kann das nicht)
    for _ in range(4):
        name = toks[0].rsplit("/", 1)[-1].lower() if toks else ""
        if name in PRIV:
            return None
        if name not in WRAPPERS:
            break
        toks = toks[1:]
        while toks and toks[0].startswith("-"):
            toks = toks[1:]
        if name == "timeout" and toks:
            toks = toks[1:]
        while toks and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*=.*", toks[0]):
            toks = toks[1:]
        if not toks:
            return None

    # Umleitungen auswerten
    args, i = [], 1
    while i < len(toks):
        t = toks[i]
        if t.startswith("<<"):
            return None  # Heredoc/Herestring: kein Datei-Read
        m = re.fullmatch(r"(\d*|&)(>>?)(.*)", t)
        if m:
            fd, _, target = m.groups()
            if not target and i + 1 < len(toks):
                target = toks[i + 1]
                i += 1
            if fd == "2" or target in ("&1", "&2"):
                i += 1
                continue  # nur stderr umgelenkt bzw. zusammengefuehrt
            return None  # stdout geht in eine Datei -> Kopie/Schreiben, kein reiner Read
        if t.startswith("<"):
            f = t[1:] or (toks[i + 1] if i + 1 < len(toks) else "")
            if f and not t[1:]:
                i += 1
            if f:
                args.append(f)
            i += 1
            continue
        args.append(t)
        i += 1

    base = toks[0].strip("'\"").rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
    if base.endswith(".exe"):
        base = base[:-4]
    if base == SUBST.lower():
        return None

    if base in SED_NAMES:
        if any(re.fullmatch(r"-(?:[a-zA-Z]*i\S*|-in-place(?:=\S*)?)", a) for a in args):
            return None
        _, files = _sed_awk_split(args, frozenset({"-e", "-f", "--expression", "--file"}),
                                  ("-e", "--expression", "-f", "--file"))
        return base if files else None
    if base in AWK_NAMES:
        script, files = _sed_awk_split(
            args, frozenset({"-f", "-v", "-F", "--file", "--assign", "--field-separator"}), ("-f", "--file"))
        if not files or script is None:
            return None
        # nur reine Ausgabe-Skripte gelten als Read: '{print}', '{print $1}', 'NR>=5&&NR<=9{print}'
        if re.fullmatch(r"\s*(?:NR[\s\d<>=!&|NR]*)?\{\s*print\b[^;{}]*\}\s*|\s*NR[\s\d<>=!&|NR]+\s*", script):
            return base
        return None
    if base == "type":
        files = [a for a in args if not a.startswith("-")]
        return base if files and all(_looks_like_path(a) for a in files) else None
    if base in READ_CMDS:
        if base == "tail" and any(re.fullmatch(r"-[a-zA-Z]*[fF]\w*|--follow(=\S*)?", a) for a in args):
            return None
        files, skip = [], False
        for a in args:
            if skip:
                skip = False
            elif a in ("-n", "-c", "-s", "--lines", "--bytes", "--sleep-interval", "--pid"):
                skip = True  # Optionswert, keine Datei (`head -n 5`)
            elif not a.startswith("-"):
                files.append(a)
        return base if files else None
    return None


def _only_devices(glied: str) -> bool:
    """`cat /dev/null`, `head -c 16 /dev/urandom` sind keine Datei-Reads."""
    try:
        toks = [t for t in shlex.split(glied) if not t.startswith("-")][1:]
    except ValueError:
        return False
    paths = [t for t in toks if "/" in t]
    return bool(paths) and all(t.startswith("/dev/") for t in paths)


def find_pure_read(cmd: str):
    """-> (befehlsname, glied) fuer das erste reine Read-Glied, sonst None."""
    text = replace_substitutions(strip_heredocs(cmd))
    for pipe in split_chain(text):
        if len(pipe) != 1:
            continue  # Pipe = Verarbeitung
        hit = check_command(pipe[0])
        if hit and not _only_devices(pipe[0]):
            return hit, pipe[0]
    return None


def main() -> None:
    for _s in (sys.stdin, sys.stdout, sys.stderr):  # Windows: sonst cp1252 und Umlaute scheitern still
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            sys.exit(0)
        if data.get("tool_name") not in (None, "Bash"):
            sys.exit(0)
        cmd = (data.get("tool_input", {}) or {}).get("command", "")
        if not isinstance(cmd, str) or not cmd.strip():
            sys.exit(0)
        res = find_pure_read(cmd)
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
    if not res:
        sys.exit(0)
    base, glied = res
    sys.stderr.write(
        f"BLOCKED: reiner Datei-Read via Shell (`{base}`, Glied: {glied[:100]}) — bitte das Read-Tool nutzen "
        f"(mit offset/limit fuer Zeilenbereiche). Shell-Reads triggern des Nutzers Read-Deny-Security-Flag; "
        f"rules/subagent-file-reads.md. Pipes (`cmd | head`) und grep bleiben erlaubt.\n"
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
