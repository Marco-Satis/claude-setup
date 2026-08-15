#!/usr/bin/env python3
"""PreToolUse-Hook (Bash): blockt destruktive Kommandos via exit 2.

Historie:
- 2026-07-07 (p-275916a5eb): Inline-Bash-Blocker aus settings.json ersetzt
  (der las $CLAUDE_TOOL_INPUT_command — kein Teil des Hook-Interfaces → No-Op).
- 2026-07-21 (Fixsweep, Audit-Finding H-3 / verdicts_merged.json
  'destructive_command_blocker laesst kanonische Katastrophen-Formen durch'):
  Komplett-Haertung. Vorher ALLOWED: `rm -rf /*`, `rm -rf ~/*`,
  `git push origin +main`, `find / -delete`. Neu:
  * Token-basierte Analyse statt blankem Substring-Regex (shlex, quote-aware
    Segment-Split auf ; | & \n) — Kommando-Position zaehlt, nicht Substring.
  * rm: -r/-R/--recursive UND -f/--force in beliebiger Reihenfolge/Cluster
    auf /, /*, ~, ~/*, $HOME, $HOME/*, expandiertem Home-Pfad, . / .. → deny.
  * find … -delete ausserhalb /tmp bzw. nicht-rein-relativer Pfade → deny.
  * git push: +<refspec> (Force via Refspec-Plus) sowie --force/-f — beides
    nur erlaubt mit --force-with-lease → sonst deny.
  * git reset --hard: NUR Warnung (systemMessage, kein Block) — zu viele
    legitime Faelle.
  * Shell-Wrapper (bash/sh/zsh/… -c "…", eval …) und Command-Substitution
    ($(…), `…`) werden rekursiv analysiert.

Quote-Literal-Tradeoff (dokumentiert, bewusst):
  Die Token-Analyse prueft nur die Kommando-Position. Reine Daten-Strings wie
  `echo "rm -rf /"` oder ein Commit-Message-Text blocken NICHT mehr (das war
  die False-Positive-Klasse aus dem Audit: Testscript geblockt, weil
  'git push --force' als Datenstring vorkam). Der Preis: destruktiver Code in
  Interpreter-One-Linern (`python -c "os.system('rm -rf /')"`) und via
  xargs-Stdin (`… | xargs rm -rf`) wird NICHT erkannt — diese Klassen deckt
  das (aktuell deaktivierte) safety-net-Plugin mit echtem Parser ab.
  bash -c "…" / eval / $(…) werden dagegen bewusst rekursiv mitgeprueft,
  weil deren String-Inhalt ausgefuehrt wird.

Best-effort: unerwarteter Fehler → exit 0 (Hook darf Session nie brechen).
Bei nicht-parsebaren Segmenten (shlex-Fehler) greift ein konservativer
Regex-Fallback statt fail-open.
Block: Meldung auf stderr + exit 2. Warnung: systemMessage-JSON + exit 0.
"""
import json
import os
import re
import shlex
import sys

MAX_DEPTH = 6

HOME = os.path.expanduser("~")

# Wrapper, die vor dem eigentlichen Kommando stehen koennen.
WRAPPERS = {"sudo", "doas", "command", "nohup", "time", "nice", "ionice",
            "stdbuf", "env", "timeout"}
# Shells, deren -c-Argument als Kommando-Text rekursiv analysiert wird.
SHELLS_WITH_C = {"bash", "sh", "zsh", "dash", "ksh", "ash", "busybox"}


def cmd_name(token):
    base = os.path.basename(token.strip())
    if base.lower().endswith(".exe"):
        base = base[:-4]
    return base


def skip_wrappers(tokens):
    """Entfernt fuehrende VAR=…-Assignments und Wrapper (sudo, env, timeout …)."""
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*=.*", t):
            i += 1
            continue
        name = cmd_name(t)
        if name in WRAPPERS:
            i += 1
            # Flags des Wrappers ueberspringen
            while i < len(tokens) and tokens[i].startswith("-"):
                i += 1
            # timeout hat ein Pflicht-Argument (Dauer)
            if name == "timeout" and i < len(tokens):
                i += 1
            # env: weitere VAR=…-Assignments
            if name == "env":
                while i < len(tokens) and re.fullmatch(
                        r"[A-Za-z_][A-Za-z_0-9]*=.*", tokens[i]):
                    i += 1
            continue
        break
    return tokens[i:]


def is_danger_rm_target(t):
    """Root/Home/CWD-Formen inkl. Wildcard-Varianten (/* , ~/* , $HOME/*)."""
    if not t:
        return False
    # /  //  /*  /*/ …
    if re.fullmatch(r"/+\**/*", t):
        return True
    # ~  ~/  ~/*
    if re.fullmatch(r"~(/+\**)?/*", t):
        return True
    # $HOME  ${HOME}  $HOME/  $HOME/*
    if re.fullmatch(r"\$\{?HOME\}?(/+\**)?/*", t, re.IGNORECASE):
        return True
    # .  ..  ./  ../  (CWD/Parent — wie im Original-Blocker)
    if re.fullmatch(r"\.\.?/?", t):
        return True
    # expandierter Home-Pfad (/home/<user>, /home/<user>/*)
    if HOME and HOME != "/":
        base = t
        if base.endswith("/*"):
            base = base[:-2]
        try:
            if base and os.path.normpath(base) == os.path.normpath(HOME):
                return True
        except Exception:
            pass
    return False


def check_rm(tokens):
    recursive = force = False
    targets = []
    after_ddash = False
    for t in tokens[1:]:
        if not after_ddash:
            if t == "--":
                after_ddash = True
                continue
            if t.startswith("--"):
                if t == "--recursive":
                    recursive = True
                elif t == "--force":
                    force = True
                continue
            if t.startswith("-") and len(t) > 1:
                flags = t[1:]
                if "r" in flags or "R" in flags:
                    recursive = True
                if "f" in flags:
                    force = True
                continue
        targets.append(t)
    if recursive and force:
        for t in targets:
            if is_danger_rm_target(t):
                return f"rm -rf auf gefaehrlichem Ziel '{t}' (Root/Home/CWD)"
    return None


def is_danger_find_path(p):
    """Erlaubt: /tmp(/…) und rein relative Pfade in cwd. Alles andere: Gefahr."""
    if p.startswith("~") or p.startswith("$"):
        return True
    if p.startswith("/"):
        try:
            norm = os.path.normpath(p)
        except Exception:
            return True
        return not (norm == "/tmp" or norm.startswith("/tmp/"))
    # relativ: nur gefaehrlich, wenn es nach oben ausbricht
    try:
        norm = os.path.normpath(p)
    except Exception:
        return True
    return norm == ".." or norm.startswith("../")


def check_find(tokens):
    if "-delete" not in tokens:
        return None
    paths = []
    for t in tokens[1:]:
        if t in ("-H", "-L", "-P", "-O0", "-O1", "-O2", "-O3"):
            continue
        if t in ("(", "!"):
            break
        if t.startswith("-") and len(t) > 1:
            break
        paths.append(t)
    if not paths:
        paths = ["."]  # GNU-find-Default: cwd → rein relativ → ok
    for p in paths:
        if is_danger_find_path(p):
            return (f"find -delete auf '{p}' (nur /tmp oder rein relative "
                    f"Pfade in cwd erlaubt)")
    return None


def check_git(tokens):
    """Returns (block_msg | None, warn_msg | None)."""
    # git-Global-Optionen vor dem Subcommand ueberspringen
    i = 1
    while i < len(tokens):
        t = tokens[i]
        if t in ("-C", "-c", "--git-dir", "--work-tree", "--namespace",
                 "--exec-path"):
            i += 2
            continue
        if t.startswith("-"):
            i += 1
            continue
        break
    if i >= len(tokens):
        return None, None
    sub = tokens[i]
    rest = tokens[i + 1:]

    if sub == "push":
        has_lease = any(a == "--force-with-lease" or
                        a.startswith("--force-with-lease=") for a in rest)
        has_force = any(
            a == "--force" or
            (a.startswith("-") and not a.startswith("--") and "f" in a[1:])
            for a in rest)
        plus_refspec = any(
            not a.startswith("-") and re.fullmatch(r"\+\S+", a)
            for a in rest)
        if not has_lease:
            if plus_refspec:
                return ("git push mit +<refspec> (Force-Push via Refspec-Plus)"
                        " — nutze --force-with-lease", None)
            if has_force:
                return ("git push --force/-f ohne --force-with-lease", None)
        return None, None

    if sub == "reset" and "--hard" in rest:
        # NUR WARNEN: zu viele legitime Faelle (frischer Clone, CI, Recovery).
        return None, ("git reset --hard verwirft alle uncommitteten "
                      "Aenderungen unwiederbringlich — vorher 'git stash' "
                      "oder 'git status' pruefen.")

    return None, None


def check_misc(tokens):
    """Windows-/Disk-Destruktiv-Klassiker aus der Original-Liste,
    jetzt token-basiert (Kommando-Position statt Substring)."""
    name = cmd_name(tokens[0]).lower()
    rest = [t.lower() for t in tokens[1:]]
    if name == "del" and any(t in ("/s", "/q") for t in rest):
        return "del /s|/q"
    if name == "rmdir" and "/s" in rest:
        return "rmdir /s"
    if name == "format" and any(re.fullmatch(r"[a-z]:", t) for t in rest):
        return "format <Laufwerk>"
    if name.startswith("mkfs"):
        return "mkfs"
    if name == "dd" and any(t.startswith("if=") for t in tokens[1:]):
        return "dd if="
    return None


# ---------------------------------------------------------------------------
# Segmentierung + Rekursion
# ---------------------------------------------------------------------------

def split_segments(text):
    """Quote-aware Split auf ; & | und Newlines (ausserhalb von Quotes)."""
    segments = []
    cur = []
    q = None  # aktives Quote-Zeichen oder None
    escape = False
    for ch in text:
        if escape:
            cur.append(ch)
            escape = False
            continue
        if ch == "\\" and q != "'":
            cur.append(ch)
            escape = True
            continue
        if q:
            cur.append(ch)
            if ch == q:
                q = None
            continue
        if ch in ("'", '"'):
            q = ch
            cur.append(ch)
            continue
        if ch in (";", "&", "|", "\n"):
            seg = "".join(cur).strip()
            if seg:
                segments.append(seg)
            cur = []
            continue
        cur.append(ch)
    seg = "".join(cur).strip()
    if seg:
        segments.append(seg)
    return segments


def extract_substitutions(text):
    """Innere Kommandos aus $(…) und `…` herausziehen (werden ausgefuehrt,
    auch innerhalb von Double-Quotes). Gibt (rest_text, [inner, …]) zurueck."""
    inners = []
    # innermost-first, iterativ
    for _ in range(10):
        m = re.search(r"\$\(([^()]*)\)", text)
        if not m:
            break
        inners.append(m.group(1))
        text = text[:m.start()] + " __SUBST__ " + text[m.end():]
    for _ in range(10):
        m = re.search(r"`([^`]*)`", text)
        if not m:
            break
        inners.append(m.group(1))
        text = text[:m.start()] + " __SUBST__ " + text[m.end():]
    return text, inners


# Konservativer Regex-Fallback fuer Segmente, die shlex nicht parsen kann
# (z.B. unbalancierte Quotes). Bewusst grob — lieber ein False-Positive als
# fail-open auf einem nicht-analysierbaren Segment.
_FB_TARGET = r"(/+\*?|~(/+\*?)?|\$\{?home\}?(/+\*?)?|\.\.?/?)(\s|$|[;&|)])"
FALLBACK_PATTERNS = [
    (r"(^|[;&|(\s])rm\s+-[a-z-]*r[a-z-]*f[a-z-]*\s+(--\s+)?" + _FB_TARGET,
     "rm -rf auf Root/Home/CWD"),
    (r"(^|[;&|(\s])rm\s+-[a-z-]*f[a-z-]*r[a-z-]*\s+(--\s+)?" + _FB_TARGET,
     "rm -fr auf Root/Home/CWD"),
    (r"(^|[;&|(\s])find\s+(/(?!tmp(/|\s|$))|~|\$home|\.\.)\S*[^\n]*\s-delete(\s|$)",
     "find -delete ausserhalb /tmp"),
    (r"(^|[;&|(\s])git\s+push\s+(?!.*--force-with-lease)"
     r"(.*\s--force(\s|$)|.*\s-[a-z]*f[a-z]*(\s|$)|.*\s\+\S+)",
     "git push --force / +refspec (nutze --force-with-lease)"),
    (r"(^|[;&|(\s])del\s+/[sq]\b", "del /s|/q"),
    (r"(^|[;&|(\s])rmdir\s+/s\b", "rmdir /s"),
    (r"(^|[;&|(\s])format\s+[a-z]:", "format <Laufwerk>"),
    (r"(^|[;&|(\s])mkfs", "mkfs"),
    (r"(^|[;&|(\s])dd\s+if=", "dd if="),
]


def fallback_scan(segment):
    low = segment.lower()
    for pat, name in FALLBACK_PATTERNS:
        try:
            if re.search(pat, low):
                return name
        except Exception:
            continue
    return None


def analyze_text(text, depth, blocks, warns):
    if depth > MAX_DEPTH or not text.strip():
        return
    text, inners = extract_substitutions(text)
    for inner in inners:
        analyze_text(inner, depth + 1, blocks, warns)
    for segment in split_segments(text):
        analyze_segment(segment, depth, blocks, warns)


def analyze_segment(segment, depth, blocks, warns):
    try:
        tokens = shlex.split(segment)
    except ValueError:
        hit = fallback_scan(segment)
        if hit:
            blocks.append(hit)
        return
    if not tokens:
        return
    tokens = skip_wrappers(tokens)
    if not tokens:
        return
    name = cmd_name(tokens[0])

    # Shell-Wrapper: Inhalt von -c wird ausgefuehrt → rekursiv analysieren.
    # Auch Cluster wie -ec / -xc zaehlen (letztes c = command-string).
    if name in SHELLS_WITH_C:
        for j, t in enumerate(tokens):
            if j == 0:
                continue
            is_c = (t == "-c" or
                    (t.startswith("-") and not t.startswith("--")
                     and "c" in t[1:]))
            if is_c and j + 1 < len(tokens):
                analyze_text(tokens[j + 1], depth + 1, blocks, warns)
                break
        return
    if name == "eval":
        analyze_text(" ".join(tokens[1:]), depth + 1, blocks, warns)
        return

    if name == "rm":
        hit = check_rm(tokens)
        if hit:
            blocks.append(hit)
        return
    if name == "find":
        hit = check_find(tokens)
        if hit:
            blocks.append(hit)
        return
    if name == "git":
        block, warn = check_git(tokens)
        if block:
            blocks.append(block)
        if warn:
            warns.append(warn)
        return
    hit = check_misc(tokens)
    if hit:
        blocks.append(hit)


def main():
    try:
        data = json.load(sys.stdin)
        cmd = ((data.get("tool_input") or {}).get("command", "") or "")
    except Exception:
        sys.exit(0)
    if not cmd.strip():
        sys.exit(0)

    blocks, warns = [], []
    try:
        analyze_text(cmd, 0, blocks, warns)
    except Exception:
        # Best-effort: Analyzer-Bug darf die Session nicht brechen —
        # letzter Rettungsanker: Fallback-Regex auf dem Roh-Kommando.
        try:
            hit = fallback_scan(cmd)
            if hit:
                blocks.append(hit)
        except Exception:
            sys.exit(0)

    if blocks:
        print(f"BLOCKED destructive ({blocks[0]}): {cmd[:200]}",
              file=sys.stderr)
        sys.exit(2)
    if warns:
        try:
            print(json.dumps({
                "systemMessage": "destructive_command_blocker WARNUNG: "
                                 + " | ".join(dict.fromkeys(warns))
            }))
        except Exception:
            pass
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
