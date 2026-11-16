#!/usr/bin/env python3
"""ssh_netcup_guard: PreToolUse-Waechter fuer Fernbefehle vom PC nach netcup.

MB169, der Nutzer 16.11.2026 08:42 „Mb169 ja“ (PC-Pruefung 15.11., Befund H4): Die pauschale Freigabe
`Bash(ssh netcup-marco:*)` erlaubte jeden Fernbefehl ohne Rueckfrage, und weder destructive_command_blocker
noch safety-net pruefen das ssh-Argument. Ersatz: Allowlist plus Blocker.

Entscheidungen (Reihenfolge):
  deny   Datenverlust-Muster im Befehl (rm -r auf ~, /, ~/.claude ..., mkfs, dd auf Geraete, crontab -r,
         Abschalten des Servers, git push --force ...). Claude bekommt den Grund, der Nutzer macht es selbst.
  ask    erkennbar schreibende oder heikle Fernbefehle, Lesen geheimer Pfade, Ausgabe von Umgebungsvariablen,
         scp-Upload, rsync/sftp/sshfs, riskante ssh-Optionen (ProxyCommand, -L/-R, -i, -F ...), heikle
         wz-Befehle (bestaetigen, betrieb, secrets-hash ...). der Nutzer muss bestaetigen.
  allow  nur Bash-Tool und nur, wenn der GANZE Befehl streng geparst werden kann: ssh mit harmlosen Optionen auf
         netcup-marco, Fernbefehl aus der Allowlist (wz-Alltag, reine Lesebefehle), lokal hoechstens
         Filter per Pipe (head, tail, grep, cut, sed -n ...). Kein $, keine Backticks, keine Globs.
  nichts alles andere geht den normalen Weg (auto mode: Classifier, sonst Rueckfrage).
         Flag ~/.claude/flags/ssh_guard_strikt.on macht daraus ask.

Not-Aus: ~/.claude/flags/ssh_guard.off (die pauschale allow-Regel bleibt trotzdem entfernt).
Selbsttest: python ssh_netcup_guard.py --selftest
Einzelprobe: python ssh_netcup_guard.py --probe "<befehl>" [--tool PowerShell]
Protokoll: ~/.claude/logs/ssh_netcup_guard.log (Entscheidung, Grund, Hash und Anfang des Befehls; 512 KB, 1 Vorgaenger).
Eigene Fehler: kein Ergebnis (exit 0) = normaler Weg, nie allow.
"""
import hashlib
import json
import re
import shlex
import sys
import time
from pathlib import Path

HOME = Path.home()
FLAGS = HOME / ".claude" / "flags"
LOG = HOME / ".claude" / "logs" / "ssh_netcup_guard.log"
TOOLS = ("Bash", "PowerShell", "Monitor", "mcp__terminal__run_in_terminal")

# ---------------------------------------------------------------- Erkennung
SSH_WORD = re.compile(r"(?<![\w.-])(?:ssh|scp|sftp|rsync|sshfs|plink|pscp)(?:\.exe)?(?![\w.-])", re.I)
HOST_TOKEN = re.compile(r"netcup|100\.76\.184\.11|159\.195\.72\.217|192\.168\.178\.201|<tailnet>", re.I)
ALLOW_HOSTS = {"netcup-marco", "marco@100.x.y.z", "marco@netcup.<tailnet>.ts.net"}

# Befehlsposition: Anfang, nach Trennzeichen/Quote/Wrapper oder direkt nach dem Hostnamen.
CMDPOS = (r"(?:^|[;&|(){}\n`'\"]|\$\(|\b(?:do|then|else|elif|xargs|sudo|exec|nohup|env|command|builtin|time|nice"
          r"|stdbuf|ionice|watch)\s|(?:netcup[\w.-]*|100\.76\.184\.11|netcup\.<tailnet>\.ts\.net)\s)\s*"
          r"(?:timeout\s+(?:-\S+\s+)*\S+\s+)?(?:/usr)?(?:/s?bin/)?")

ASK_PATTERNS = [
    (CMDPOS + r"(?:rm|rmdir|mv|cp|ln|dd|truncate|shred|unlink|chmod|chown|chgrp|chattr|setfacl|tee|kill|killall"
     r"|pkill|reboot|service|apt|apt-get|aptitude|dpkg|snap|sudo|su|doas|passwd|chpasswd|usermod|useradd|groupadd"
     r"|groupdel|visudo|ufw|iptables|ip6tables|nft|wget|mount|umount|fdisk|parted|mkswap|swapoff|systemd-run"
     r"|loginctl|install|rsync|scp|sftp)(?![\w.-])", "schreibender oder heikler Fernbefehl"),
    (CMDPOS + r"systemctl\s+(?:--?\S+\s+)*(?:start|stop|restart|reload|try-restart|reload-or-restart|enable"
     r"|disable|reenable|mask|unmask|link|daemon-reload|daemon-reexec|kill|edit|set-property|isolate|set-default"
     r"|suspend|hibernate|reset-failed|revert|preset|import-environment|set-environment|unset-environment|reboot)\b",
     "systemctl aendert Dienste"),
    (CMDPOS + r"crontab(?![\w.-])(?!\s+-l\b)", "crontab aendern"),
    (CMDPOS + r"git\s+(?:-C\s+\S+\s+|--?[\w-]+(?:=\S+)?\s+)*(?:push|commit|reset|checkout|clean|rebase|merge|pull"
     r"|rm|mv|restore|switch|apply|am|cherry-pick|revert|filter-branch|gc|prune|update-ref|init|clone|stash(?!\s+list)"
     r"|config(?!\s+(?:--get|-l|--list)))\b", "git aendert das Repo"),
    (CMDPOS + r"(?:pip3?|python3?\s+-m\s+pip)\s+(?:install|uninstall|download)\b", "pip installiert"),
    (CMDPOS + r"npm\s+(?:i|install|uninstall|update|ci|publish|run|exec)\b", "npm"),
    (CMDPOS + r"docker\s+(?:run|rm|rmi|stop|kill|restart|start|exec|compose|system|volume|network|build|pull"
     r"|push|cp|commit|update|prune)\b", "docker aendert Container"),
    (CMDPOS + r"sed\b[^|;&\n]*\s-(?:[a-zA-Z]*i|-in-place)", "sed -i aendert Dateien"),
    (CMDPOS + r"perl\b[^|;&\n]*\s-[a-zA-Z]*i", "perl -i aendert Dateien"),
    (CMDPOS + r"curl\b[^|;&\n]*\s(?:-X\s*(?:POST|PUT|DELETE|PATCH)|-d\b|--data|-F\b|--form|-T\b|--upload-file"
     r"|-o\b|--output|-O\b)", "curl sendet oder schreibt"),
    (CMDPOS + r"claude(?![\w.-])(?!\s+(?:--version|-v|--help|-h)\b)", "Claude-CLI auf netcup"),
    (CMDPOS + r"(?:printenv|env|export\s+-p|declare\s+-[a-zA-Z]*p|typeset|compgen\s+-v)(?![\w.-])",
     "gibt Umgebungsvariablen aus"),
    (CMDPOS + r"set\s*(?:$|[;&|\n'\"])", "gibt Shell-Variablen aus"),
    (r"(?:^|[\s/'\"])wz\s+(?:bestaetigen|betrieb|secrets-hash|init|zurueck|modellwahl|eingang|commit|pflege"
     r"|reindex)\b", "heikler wz-Befehl"),
    (r"(?<![<>&0-9=-])(?:[0-9]?>>?|&>>?)\s*(?!&|/dev/(?:null|stdout|stderr)\b)['\"]?(?:~|/|\$HOME|\.{1,2}/"
     r"|[\w.-]+\.\w{1,6}(?![\w(]))", "Umleitung in eine Datei"),
    (CMDPOS + r"(?:shutdown\s+-r|reboot)\b", "Neustart des Servers"),
]

DENY_PATTERNS = [
    (r"(?<![\w.-])mkfs(?:\.\w+)?(?![\w.-])", "mkfs formatiert ein Dateisystem"),
    (r"(?<![\w.-])dd\b[^;|&\n]*\bof=/dev/", "dd schreibt auf ein Geraet"),
    (r">\s*/dev/(?:sd|nvme|vd|xvd|mmcblk)", "Umleitung auf ein Geraet"),
    (r"(?<![\w.-])wipefs(?![\w.-])", "wipefs"),
    (r"(?<![\w.-])crontab\s+(?:-\w*\s+)*-\w*r\w*(?![\w-])", "crontab -r loescht alle Cronjobs"),
    (r":\(\)\s*\{", "Fork-Bombe"),
    (r"(?<![\w.-])ch(?:mod|own)\s+(?:-\S+\s+)*-\w*R\w*\s+\S+\s+(?:/|~/?|\$HOME/?|/home(?:/marco)?/?)(?=\s|$|['\";|&])",
     "chmod/chown -R auf ~ oder /"),
    (r"(?<![\w.-])(?:userdel|deluser)(?![\w.-])", "Benutzer loeschen"),
    (r"(?<![\w.-])ufw\s+(?:--force\s+)?(?:disable|reset)\b", "Firewall abschalten"),
    (r"(?<![\w.-])iptables\s+(?:-t\s+\w+\s+)?-F\b", "Firewall-Regeln leeren"),
    (r"(?<![\w.-])find\s+(?:~|/|\$HOME)\S*\s[^;|&\n]*-delete\b", "find -delete auf ~ oder /"),
    (r"(?<![\w.-])git\b[^;|&\n]*\bpush\b[^;|&\n]*(?:--force\b|--force-with-lease\b|\s-f\b|\s\+\S)",
     "git push --force"),
    (r"filter-repo|filter-branch", "Git-Historie umschreiben"),
    (r"(?<![\w.-])(?:poweroff|halt)(?![\w.-])|(?<![\w.-])shutdown(?![\w.-])(?!\s+-r\b)|systemctl\s+(?:\S+\s+)*"
     r"(?:poweroff|halt)\b", "Server abschalten"),
]

CRIT_TARGETS = {"/", "/*", "~", "~/*", "~/.claude", "~/.claude/*", "~/projects", "~/projects/*", "~/wissen",
                "~/wissen/*", "~/.ssh", "~/.local", "~/.config", "~/backups", "/home", "/home/*", "/etc", "/var",
                "/usr", "/root", "/opt", "/boot", "/srv", ".", "..", "*", "./*"}

# Geheime Pfade: nur in pfadartigen Woertern gesucht (enthaelt / oder ~ oder beginnt mit .)
SENS_STRONG = re.compile(
    r"\.env(?:$|[./])|(?:^|/)secrets?(?:/|$)|\.ssh(?:/|$)|id_rsa|id_ed25519|id_ecdsa|\.pem$|\.key$|\.p12$|\.pfx$"
    r"|\.kdbx|\.keyx|\.gnupg|\.gpg$|auth\.json|credentials\.json|\.netrc|\.git-credentials|_history$"
    r"|\.claude\.json|rclone\.conf|gh/hosts\.yml|\.npmrc|\.pypirc|\.docker/config|/etc/shadow|sudoers"
    r"|environ$|ntfy_eigen|\.pass$|syncthing/config|\.n8n(?:/|$)|wg0\.conf|/etc/wireguard|cookies"
    r"|\.bashrc|\.bash_profile|\.profile$|\.zshrc|codex/config", re.I)
SENS_WEAK = re.compile(r"secret|credential|token|passw|apikey|api_key", re.I)
SENS_EXEMPT = re.compile(r"\.env\.(?:example|sample|template|dist)$", re.I)
CODE_EXT = re.compile(r"\.(?:py|pyc|js|mjs|ts|tsx|jsx|css|scss|md|html|htm|jinja|j2|sh|ps1|go|rs|java|rb|php|vue"
                      r"|svelte|ya?ml|toml|lock|log)$", re.I)
PATHISH = re.compile(r"[\w.~$/+@%:-]*[/~][\w.~$/+@%:-]*|(?<![\w])\.[\w.-]+")


def sensitive_in(text):
    for m in PATHISH.finditer(text):
        tok = m.group(0)
        if SENS_EXEMPT.search(tok):
            continue
        if SENS_STRONG.search(tok):
            return tok
        if SENS_WEAK.search(tok) and not CODE_EXT.search(tok):
            return tok
    return None


# ---------------------------------------------------------------- strenger Lexer (Bash-Teilmenge)
class Reject(Exception):
    pass


_DEVNULL_REDIR = re.compile(r"(?:[12]?>|&>)\s*/dev/null(?=$|[\s;|&)])")
_DUP_REDIR = re.compile(r"(?:2>&1|>&2|1>&2)(?=$|[\s;|&)])")
_EXP_START = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_0123456789{(@*#?$!-")
_UNQUOTED_BAD = set("$`\\*?[]{}()<>!#&")


def lex(s):
    toks = []
    cur = None
    i, n = 0, len(s)

    def flush():
        nonlocal cur
        if cur is not None:
            toks.append(("w", cur))
            cur = None

    while i < n:
        c = s[i]
        if c in " \t":
            flush()
            i += 1
            continue
        if c in "\r\n\x00":
            raise Reject("Zeilenumbruch/Steuerzeichen")
        if cur is None:
            m = _DEVNULL_REDIR.match(s, i) or _DUP_REDIR.match(s, i)
            if m:
                toks.append(("r", m.group(0)))
                i = m.end()
                continue
        if c == "'":
            j = s.find("'", i + 1)
            if j < 0:
                raise Reject("offenes Hochkomma")
            seg = s[i + 1:j]
            if any(x in seg for x in "\r\n\x00"):
                raise Reject("Zeilenumbruch in Quote")
            cur = (cur or "") + seg
            i = j + 1
            continue
        if c == '"':
            j = i + 1
            out = []
            while True:
                if j >= n:
                    raise Reject("offenes Anfuehrungszeichen")
                d = s[j]
                if d == '"':
                    break
                if d in "\r\n\x00":
                    raise Reject("Zeilenumbruch in Quote")
                if d == "`":
                    raise Reject("Backtick")
                if d == "$":
                    if j + 1 < n and s[j + 1] in _EXP_START:
                        raise Reject("Expansion")
                    out.append(d)
                    j += 1
                    continue
                if d == "\\":
                    if j + 1 >= n:
                        raise Reject("Backslash am Ende")
                    e = s[j + 1]
                    if e in "\r\n":
                        raise Reject("Zeilenfortsetzung")
                    out.append(e if e in '$`"\\' else "\\" + e)
                    j += 2
                    continue
                out.append(d)
                j += 1
            cur = (cur or "") + "".join(out)
            i = j + 1
            continue
        if s.startswith("&&", i) or s.startswith("||", i):
            flush()
            toks.append(("op", s[i:i + 2]))
            i += 2
            continue
        if c in "|;":
            flush()
            toks.append(("op", c))
            i += 1
            continue
        if c in _UNQUOTED_BAD:
            raise Reject(f"Zeichen {c!r}")
        cur = (cur or "") + c
        i += 1
    flush()
    return toks


def split_cmds(toks):
    """-> [(verbindung_davor, woerter)]; Umleitungen nach /dev/null bzw. 2>&1 fallen weg."""
    cmds, words, conn = [], [], None
    for kind, val in toks:
        if kind == "w":
            words.append(val)
        elif kind == "op":
            if not words:
                raise Reject("leerer Befehl")
            cmds.append((conn, words))
            words, conn = [], val
    if not words:
        raise Reject("leerer Befehl")
    cmds.append((conn, words))
    return cmds


# ---------------------------------------------------------------- heredoc (nur lokal, nur fuer `bash -s`)
_HEREDOC = re.compile(r"<<(-?)\s*(?:'([A-Za-z_]\w*)'|\"([A-Za-z_]\w*)\"|([A-Za-z_]\w*))")
HD_MARK = "\x01HD\x01"


def split_heredoc(cmd):
    if "<<" not in cmd:
        if "\n" in cmd or "\r" in cmd:
            raise Reject("mehrzeilig ohne heredoc")
        return cmd, None
    first, sep, rest = cmd.partition("\n")
    first = first.rstrip("\r")
    if "<<<" in first or not sep:
        raise Reject("here-string/heredoc")
    hits = list(_HEREDOC.finditer(first))
    if len(hits) != 1:
        raise Reject("heredoc-Anzahl")
    m = hits[0]
    dash, d1, d2, d3 = m.groups()
    delim = d1 or d2 or d3
    lines = rest.split("\n")
    body = None
    for idx, line in enumerate(lines):
        cmp_ = line.rstrip("\r")
        if dash:
            cmp_ = cmp_.lstrip("\t")
        if cmp_ == delim:
            if "\n".join(lines[idx + 1:]).strip():
                raise Reject("Text nach heredoc")
            body = [x.rstrip("\r") for x in lines[:idx]]
            break
    if body is None:
        raise Reject("heredoc-Ende fehlt")
    if not (d1 or d2) and re.search(r"[$`\\]", "\n".join(body)):
        raise Reject("heredoc ungequotet mit Expansion")
    head = first[:m.start()] + " " + HD_MARK + " " + first[m.end():]
    return head, body


# ---------------------------------------------------------------- Pruefung der Woerter
_DURATION = re.compile(r"^\d+(?:\.\d+)?[smhd]?$")


def strip_timeout(words):
    if not words or words[0] != "timeout":
        return words
    k = 1
    while k < len(words) and words[k].startswith("-"):
        w = words[k]
        if w in ("--foreground", "--preserve-status", "-v", "--verbose"):
            k += 1
        elif w in ("-k", "-s") and k + 1 < len(words):
            ok = _DURATION.match(words[k + 1]) if w == "-k" else re.match(r"^[A-Z0-9]+$", words[k + 1])
            if not ok:
                raise Reject("timeout-Option")
            k += 2
        elif re.match(r"^--kill-after=\d+(?:\.\d+)?[smhd]?$|^--signal=[A-Z0-9]+$", w):
            k += 1
        else:
            raise Reject("timeout-Option")
    if k >= len(words) or not _DURATION.match(words[k]):
        raise Reject("timeout-Dauer")
    rest = words[k + 1:]
    if not rest:
        raise Reject("timeout ohne Befehl")
    return rest


_SSH_FLAGS = re.compile(r"^-[Tqnx]+$")
_SSH_O_OK = {
    "batchmode": re.compile(r"^(?:yes|no)$", re.I),
    "connecttimeout": re.compile(r"^\d{1,4}$"),
    "serveraliveinterval": re.compile(r"^\d{1,4}$"),
    "serveralivecountmax": re.compile(r"^\d{1,3}$"),
    "connectionattempts": re.compile(r"^\d{1,2}$"),
    "loglevel": re.compile(r"^(?:error|quiet|fatal)$", re.I),
    "stricthostkeychecking": re.compile(r"^(?:yes|accept-new)$", re.I),
}


def parse_ssh(words):
    words = strip_timeout(words)
    if not words or words[0] not in ("ssh", "ssh.exe"):
        raise Reject("erster Befehl ist kein ssh")
    k = 1
    while k < len(words) and words[k].startswith("-"):
        w = words[k]
        if _SSH_FLAGS.match(w):
            k += 1
            continue
        if w.startswith("-o"):
            val = w[2:] if len(w) > 2 else (words[k + 1] if k + 1 < len(words) else None)
            if val is None:
                raise Reject("-o ohne Wert")
            key, eq, v = val.partition("=")
            chk = _SSH_O_OK.get(key.lower())
            if not eq or not chk or not chk.match(v):
                raise Reject(f"ssh-Option {key}")
            k += 1 if len(w) > 2 else 2
            continue
        if w.startswith("-p"):
            port = w[2:] if len(w) > 2 else (words[k + 1] if k + 1 < len(words) else "")
            if port not in ("<ssh-port>", "22"):
                raise Reject("Port")
            k += 1 if len(w) > 2 else 2
            continue
        raise Reject(f"ssh-Option {w}")
    if k >= len(words) or words[k] not in ALLOW_HOSTS:
        raise Reject("Host nicht in der Allowlist")
    rest = words[k + 1:]
    if not rest:
        raise Reject("ohne Fernbefehl")
    if rest[0].startswith("-"):
        raise Reject("Option nach dem Host")  # OpenSSH parst Optionen nach dem Ziel erneut
    return rest


WZ_PROGS = {"~/.local/bin/wz", "$HOME/.local/bin/wz", "wz"}
WZ_ALLOW = {"find", "get", "wo", "nachbarn", "neu", "set", "archiv", "historie", "bereich", "merk", "verify",
            "lint", "-h", "--help"}
PLAIN_READ = {"echo", "printf", "true", "pwd", "whoami", "id", "uname", "uptime", "free", "df", "du", "wc",
              "md5sum", "sha1sum", "sha256sum", "stat", "file", "ls", "readlink", "realpath", "basename", "dirname",
              "sleep", "nproc", "lsb_release", "which", "cut", "tr", "head", "tail", "cat", "nl", "diff", "cmp",
              "pgrep", "cd", "column"}
SYSTEMCTL_SUB = {"status", "is-active", "is-enabled", "is-failed", "list-units", "list-timers", "list-unit-files",
                 "list-sockets", "show", "cat", "list-dependencies"}
SYSTEMCTL_FLAGS = re.compile(r"^(?:--user|--no-pager|--full|-l|--all|-a|--plain|--no-legend|-q|--quiet|--value"
                             r"|--lines=\d+|-n\d*|--state=[\w,-]+|--type=[\w,-]+|-t|--property=[\w,]+|-p)$")
JOURNAL_FLAGS = re.compile(r"^(?:--user|--no-pager|-q|--quiet|-r|--reverse|-e|-x|-k|--utc|--no-hostname|-f"
                           r"|--follow|-b|--boot(?:=\S+)?|-n\d*|--lines=\d+|-u|--unit=\S+|--user-unit(?:=\S+)?"
                           r"|--since(?:=.+)?|-S|--until(?:=.+)?|-U|-o|--output=\w+(?:-\w+)*|-p|--priority=\w+"
                           r"|-g|--grep=.+|-t|--identifier=\S+|--case-sensitive(?:=\w+)?)$")
JOURNAL_TAKES_VALUE = {"-u", "-n", "-S", "-U", "-o", "-p", "-g", "-t", "--since", "--until", "--user-unit", "-b"}
GIT_SUB = {"status", "log", "diff", "show", "rev-parse", "ls-files", "describe", "shortlog", "blame"}
GIT_BAD_ARG = re.compile(r"^(?:--output|--ext-diff|-c$|--exec-path|--upload-pack|--receive-pack|-O|"
                         r"--open-files-in-pager|--no-index)")
FIND_BAD = {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"}
SAFE_SED = re.compile(
    r"^(?:(?:\d+|\$|/[^/\n]*/)(?:,(?:\d+|\$|/[^/\n]*/))?\s*[pdq]"
    r"|s(?P<d>[/|#,:@])(?:(?!(?P=d)).)*(?P=d)(?:(?!(?P=d)).)*(?P=d)[gIip0-9]*)$")


def _short_letters(w):
    """Buchstaben eines Kurzoptions-Buendels bis zur ersten Ziffer (-m3 -> 'm')."""
    m = re.match(r"^-([A-Za-z]+)", w)
    return m.group(1) if m and not w.startswith("--") else ""


def check_grep(args, remote):
    pos = []
    takes = {"-e", "-m", "-A", "-B", "-C", "--max-count", "--after-context", "--before-context", "--context",
             "--regexp", "--label", "--color", "--colour"}
    has_e = False
    k = 0
    while k < len(args):
        a = args[k]
        if a.startswith("--"):
            name = a.split("=", 1)[0]
            if name in ("--recursive", "--dereference-recursive", "--directories", "--devices", "--file",
                        "--include-dir"):
                raise Reject("grep rekursiv/Datei")
            if name == "--regexp":
                has_e = True
            if name in takes and "=" not in a:
                k += 2
                continue
        elif a.startswith("-") and a != "-":
            letters = _short_letters(a)
            if set(letters) & set("rRdDf"):
                raise Reject("grep -r/-f")
            if "e" in letters:
                has_e = True
            if letters and letters[-1] in "emABC" and a == "-" + letters:
                k += 2
                continue
        else:
            pos.append(a)
        k += 1
    if not remote:
        if len(pos) > (0 if has_e else 1):
            raise Reject("lokales grep liest Dateien")


def check_sed(args, remote):
    script = None
    for a in args:
        if a in ("-n", "-E", "-r", "--quiet", "--silent", "-u", "--regexp-extended", "-nE", "-En"):
            continue
        if a.startswith("-"):
            raise Reject("sed-Option")
        if script is None:
            script = a
            continue
        if not remote:
            raise Reject("lokales sed liest Dateien")
    if script is None:
        raise Reject("sed ohne Skript")
    for part in script.split(";"):
        if not SAFE_SED.match(part.strip()):
            raise Reject("sed-Skript nicht harmlos")


def check_local_filter(words):
    prog, args = words[0], words[1:]
    if prog in ("head", "tail"):
        for k, a in enumerate(args):
            if re.match(r"^-[nc]?\d*$|^--lines=\d+$|^--bytes=\d+$|^-q$", a):
                continue
            if a.isdigit() and k > 0 and args[k - 1] in ("-n", "-c"):
                continue
            raise Reject(f"{prog}-Argument")
    elif prog in ("wc", "sort", "uniq"):
        for a in args:
            if not a.startswith("-") or re.match(r"^(?:-o|--output|--compress-program|--files0-from|-T"
                                                 r"|--temporary-directory)", a):
                raise Reject(f"{prog}-Argument")
    elif prog == "cut":
        k = 0
        while k < len(args):
            a = args[k]
            if a in ("-d", "-f", "-c", "-b"):
                k += 2
                continue
            if re.match(r"^-[dfcb].+$|^--(?:delimiter|fields|characters|bytes)=.+$|^-s$|^--only-delimited$", a):
                k += 1
                continue
            raise Reject("cut-Argument")
    elif prog == "tr":
        pass
    elif prog in ("grep", "egrep", "fgrep"):
        check_grep(args, remote=False)
    elif prog == "sed":
        check_sed(args, remote=False)
    elif prog == "cat":
        if args:
            raise Reject("lokales cat mit Argument")
    else:
        raise Reject(f"lokaler Filter {prog}")


def check_remote_simple(words):
    words = strip_timeout(words)
    for w in words:
        if sensitive_in(w) or "\x01" in w:
            raise Reject("geheimer Pfad")
    prog, args = words[0], words[1:]
    if prog in WZ_PROGS:
        if not args or args[0] not in WZ_ALLOW:
            raise Reject("wz-Befehl nicht in der Allowlist")
        return
    if prog in PLAIN_READ:
        return
    if prog in ("grep", "egrep", "fgrep"):
        return check_grep(args, remote=True)
    if prog == "sed":
        return check_sed(args, remote=True)
    if prog == "find":
        if any(a in FIND_BAD for a in args):
            raise Reject("find mit Aktion")
        return
    if prog == "sort":
        if any(re.match(r"^(?:-o|--output|--compress-program)", a) for a in args):
            raise Reject("sort -o")
        return
    if prog == "uniq":
        if len([a for a in args if not a.startswith("-")]) > 1:
            raise Reject("uniq mit Ausgabedatei")
        return
    if prog == "date":
        if any(re.match(r"^(?:-s|--set|-f|--file)", a) for a in args):
            raise Reject("date -s/-f")
        return
    if prog == "hostname":
        if any(not re.match(r"^(?:-[fsiIdA]|--fqdn|--short)$", a) for a in args):
            raise Reject("hostname-Argument")
        return
    if prog == "command":
        if len(args) >= 2 and args[0] in ("-v", "-V"):
            return
        raise Reject("command")
    if prog == "set":
        if args and all(re.match(r"^[-+][euxo]+$|^pipefail$", a) for a in args):
            return
        raise Reject("set")
    if prog == "ps":
        for a in args:
            if not re.match(r"^(?:aux|ax|-ef|-e|-f|-F|-aux|--forest|-H|-o|-p|-u|-C|--sort=[\w,+-]+|[\w,%:=+-]+)$", a) \
                    or (not a.startswith("-") and "e" in a.lower() and a not in ("-ef",)) or "env" in a.lower():
                raise Reject("ps-Argument")
        return
    if prog == "ss":
        for a in args:
            if a.startswith("--") and a.split("=")[0] in ("--kill", "--diag"):
                raise Reject("ss --kill")
            if a.startswith("-") and not a.startswith("--") and set(_short_letters(a)) & set("KD"):
                raise Reject("ss -K/-D")
        return
    if prog == "crontab":
        if args == ["-l"]:
            return
        raise Reject("crontab")
    if prog == "systemctl":
        sub = None
        k = 0
        while k < len(args):
            a = args[k]
            if a.startswith("-"):
                if not SYSTEMCTL_FLAGS.match(a):
                    raise Reject(f"systemctl-Option {a}")
                if a in ("-n", "-t", "-p") and k + 1 < len(args):
                    k += 2
                    continue
            elif sub is None:
                sub = a
            k += 1
        if sub not in SYSTEMCTL_SUB:
            raise Reject("systemctl-Unterbefehl")
        return
    if prog == "journalctl":
        k = 0
        while k < len(args):
            a = args[k]
            if a.startswith("-"):
                if not JOURNAL_FLAGS.match(a):
                    raise Reject(f"journalctl-Option {a}")
                if a in JOURNAL_TAKES_VALUE and k + 1 < len(args):
                    k += 2
                    continue
            k += 1
        return
    if prog == "docker":
        if args[:1] in (["ps"], ["images"], ["logs"], ["inspect"], ["version"], ["info"]) or \
                args[:2] == ["stats", "--no-stream"]:
            return
        raise Reject("docker-Unterbefehl")
    if prog == "git":
        k = 0
        while k < len(args) and args[k].startswith("-"):
            if args[k] == "-C" and k + 1 < len(args):
                k += 2
            elif args[k] in ("--no-pager", "-P"):
                k += 1
            else:
                raise Reject(f"git-Option {args[k]}")
        if k >= len(args) or args[k] not in GIT_SUB:
            raise Reject("git-Unterbefehl")
        if any(GIT_BAD_ARG.match(a) for a in args[k + 1:]):
            raise Reject("git-Argument")
        return
    raise Reject(f"Fernbefehl {prog} nicht in der Allowlist")


def check_remote(remote_str, body):
    if body is not None:
        if remote_str.split() not in (["bash", "-s"], ["bash"], ["sh", "-s"], ["sh"]):
            raise Reject("heredoc nur fuer bash -s")
        cmds = []
        for line in body:
            st = line.strip()
            if not st or st.startswith("#"):
                continue
            cmds.extend(split_cmds(lex(st)))
        if not cmds:
            raise Reject("leeres Skript")
    else:
        cmds = split_cmds(lex(remote_str))
    for _conn, words in cmds:
        check_remote_simple(words)


def allow_parse(cmd):
    """True, wenn der ganze Befehl streng geparst werden kann und nur Erlaubtes enthaelt; sonst Reject."""
    head, body = split_heredoc(cmd)
    cmds = split_cmds(lex(head))
    conn0, ssh_words = cmds[0]
    if any(w == HD_MARK for w in ssh_words):
        if body is None:
            raise Reject("Marker ohne heredoc")
        ssh_words = [w for w in ssh_words if w != HD_MARK]
    elif body is not None:
        raise Reject("heredoc nicht am ssh-Befehl")
    remote_words = parse_ssh(ssh_words)
    for conn, words in cmds[1:]:
        if conn != "|":
            raise Reject("lokale Verkettung")
        if any("\x01" in w for w in words):
            raise Reject("heredoc an Filter")
        check_local_filter(words)
    for w in remote_words:
        if "\x01" in w:
            raise Reject("heredoc im Fernbefehl")
    check_remote(" ".join(remote_words), body)
    return True


# ---------------------------------------------------------------- Muster-Stufen
_SSH_OPT_GROUP = re.compile(r"(?<![\w.-])ssh(?:\.exe)?((?:\s+-\S+(?:\s+(?!-)[^\s'\";|&]+)?)*)", re.I)
_SSH_O_SAFE = set(_SSH_O_OK) | {"requesttty", "compression", "ipqos", "tcpkeepalive", "addressfamily"}
_SSH_ASK_LETTERS = set("FESwLRDJWMNfiAXYIgOsl")
_SSH_ARG_LETTERS = set("BbcDEeFIiJLlmOoPpQRSWw")


def risky_ssh_option(text):
    for m in _SSH_OPT_GROUP.finditer(text):
        toks = m.group(1).split()
        k = 0
        while k < len(toks):
            t = toks[k].strip("'\"")
            if not t.startswith("-"):
                k += 1
                continue
            if t.startswith("-o"):
                val = t[2:] if len(t) > 2 else (toks[k + 1].strip("'\"") if k + 1 < len(toks) else "")
                key, _, v = val.partition("=")
                key = key.lower()
                if key not in _SSH_O_SAFE or (key == "stricthostkeychecking" and v.lower() not in ("yes",
                                                                                                  "accept-new")):
                    return f"ssh -o {key}"
                k += 1 if len(t) > 2 else 2
                continue
            letters = t[1:]
            if letters and letters[0] in _SSH_ARG_LETTERS:
                if letters[0] in _SSH_ASK_LETTERS:
                    return f"ssh -{letters[0]}"
                k += 1 if len(letters) > 1 else 2
                continue
            bad = set(letters) & _SSH_ASK_LETTERS
            if bad:
                return f"ssh -{''.join(sorted(bad))}"
            k += 1
    return None


def scp_upload(text):
    for m in re.finditer(r"(?<![\w.-])(?:scp|pscp)(?:\.exe)?\s+([^;|&\n]*)", text, re.I):
        args = [a.strip("'\"") for a in m.group(1).split() if not a.startswith("-")]
        if args and HOST_TOKEN.search(args[-1]) and ":" in args[-1]:
            return True
    return False


def deny_reason(text):
    for m in re.finditer(CMDPOS + r"rm(?![\w.-])", text):
        seg = re.split(r"[;&|\n)]", text[m.end():], maxsplit=1)[0]
        toks = [t.strip("'\"") for t in seg.split()]
        flags = "".join(t[1:] for t in toks if t.startswith("-") and not t.startswith("--"))
        longs = [t for t in toks if t.startswith("--")]
        if "r" in flags or "R" in flags or "--recursive" in longs:
            for t in toks:
                if t.startswith("-"):
                    continue
                norm = t.replace("${HOME}", "~").replace("$HOME", "~").replace("$HOME", "~")
                norm = norm if norm in ("/", "/*") else norm.rstrip("/") or "/"
                if norm in CRIT_TARGETS:
                    return f"rm -r auf {t}"
    for pat, why in DENY_PATTERNS:
        if re.search(pat, text):
            return why
    return None


def ask_reason(text):
    tok = sensitive_in(text)
    if tok:
        return f"geheimer Pfad ({tok[:40]})"
    if re.search(r"(?<![\w.-])(?:rsync|sftp|sshfs)(?:\.exe)?(?![\w.-])", text, re.I):
        return "rsync/sftp/sshfs"
    if scp_upload(text):
        return "scp-Upload nach netcup"
    r = risky_ssh_option(text)
    if r:
        return f"riskante ssh-Option ({r})"
    if re.search(r"(?<![\w.-])ssh(?:\.exe)?\s+(?:-\S+\s+(?:\S+\s+)?)*netcup-botuser", text):
        return "Zugang als botuser"
    for pat, why in ASK_PATTERNS:
        if re.search(pat, text, re.M):
            return why
    return None


# ---------------------------------------------------------------- nachsichtige Zerlegung fuer deny/ask
# Zerlegt den Bash-Befehl wie die Shell (Quotes, Trenner, heredocs), folgt ssh in den Fernbefehl und
# bash -c / eval / heredoc-Skripten. Geprueft werden nur Befehlswoerter, die auf netcup laufen; Text in
# Anfuehrungszeichen (z. B. wz-Eintraege) loest so keine Fehlalarme aus. Faellt die Zerlegung aus,
# greifen die Textmuster oben (deny_reason/ask_reason).
_HD_ANY = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z_]\w*)\2")
_PUNCT = set(";&|<>()")


def _quotes_closed(prefix):
    q = None
    i = 0
    while i < len(prefix):
        c = prefix[i]
        if q is None:
            if c == "\\":
                i += 2
                continue
            if c in "'\"":
                q = c
        elif q == "'":
            if c == "'":
                q = None
        else:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                q = None
        i += 1
    return q is None


def _extract_heredocs(s):
    lines = s.split("\n")
    out, bodies = [], {}
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\r")
        i += 1
        parts, last = [], 0
        for m in _HD_ANY.finditer(line):
            if line[m.start():].startswith("<<<") or (m.start() > 0 and line[m.start() - 1] == "<"):
                continue
            if not _quotes_closed(line[:m.start()]):
                continue
            key = f"__HD{len(bodies)}__"
            parts.append(line[last:m.start()])
            parts.append(f" {key} ")
            last = m.end()
            dash, delim = m.group(1), m.group(3)
            body, closed = [], False
            while i < len(lines):
                ln = lines[i].rstrip("\r")
                i += 1
                if (ln.lstrip("\t") if dash else ln) == delim:
                    closed = True
                    break
                body.append(ln)
            if not closed:
                raise ValueError("heredoc ohne Ende")
            bodies[key] = body
        parts.append(line[last:])
        out.append("".join(parts))
    return "\n".join(out), bodies


def _mask_newlines(s):
    """Unquotierte Zeilenumbrueche -> ' ; ', Kommentare entfernen. ValueError bei offenen Quotes."""
    out = []
    q = None
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if q is None:
            if c == "\\" and i + 1 < n:
                if s[i + 1] == "\n":
                    i += 2
                    continue
                out.append(s[i:i + 2])
                i += 2
                continue
            if c in "'\"":
                q = c
            elif c == "\n":
                out.append(" ; ")
                i += 1
                continue
            elif c == "#" and (i == 0 or s[i - 1] in " \t;&|()\n"):
                j = s.find("\n", i)
                i = n if j < 0 else j
                continue
        elif q == "'":
            if c == "'":
                q = None
        else:
            if c == "\\" and i + 1 < n:
                out.append(s[i:i + 2])
                i += 2
                continue
            if c == '"':
                q = None
        out.append(c)
        i += 1
    if q is not None:
        raise ValueError("offene Quotes")
    return "".join(out)


def _ltoks(s):
    lx = shlex.shlex(s, posix=True, punctuation_chars=";&|<>()")
    lx.whitespace_split = True
    lx.commenters = ""
    return list(lx)


def _simple_cmds(toks):
    """-> (liste_einfacher_befehle, ausgabe_ziele, eingabe_ziele)"""
    cmds, cur, outs, ins = [], [], [], []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t and set(t) <= _PUNCT:
            if (set(t) & set("<>")) and not (set(t) & set("();|")):
                if cur and re.fullmatch(r"\d", cur[-1]):
                    cur.pop()  # 2>... : die Ziffer gehoert zur Umleitung
                nxt = toks[i + 1] if i + 1 < len(toks) else ""
                if ">" in t:
                    if not (t.endswith("&") and re.match(r"^\d+$|^-$", nxt)):
                        outs.append(nxt)
                else:
                    ins.append(nxt)
                i += 2
                continue
            if cur:
                cmds.append(cur)
                cur = []
            i += 1
            continue
        cur.append(t)
        i += 1
    if cur:
        cmds.append(cur)
    return cmds, outs, ins


_WRAP_SKIP = {"then", "do", "else", "elif", "if", "while", "until", "!", "{", "}", "time", "exec", "nohup",
              "builtin", "coproc"}
_WRAP_OPTS = {"nice", "ionice", "stdbuf", "xargs", "watch", "chronic", "setsid", "unbuffer", "flock"}
_WRAP_ARG = {"-n", "-c", "-I", "-P", "-d", "-a", "-E", "-L", "-s", "-o", "-e", "-w", "--max-args", "--max-procs",
             "--delimiter", "--arg-file", "--replace", "--interval"}


def _effective(words):
    """Wrapper (sudo, env, timeout, xargs ...) und Zuweisungen abstreifen. -> (befehl, sudo_benutzt)"""
    k, sudo, n = 0, False, len(words)
    while k < n:
        w = words[k]
        b = w.rsplit("/", 1)[-1].lower()
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w):
            k += 1
            continue
        if b in _WRAP_SKIP:
            k += 1
            continue
        if b == "command":
            if k + 1 < n and words[k + 1] in ("-v", "-V"):
                return words[k:], sudo
            k += 1
            continue
        if b in ("sudo", "doas", "su", "pkexec", "runuser"):
            sudo = True
            k += 1
            while k < n and words[k].startswith("-"):
                if b == "su" and words[k] in ("-c", "--command") and k + 1 < n:
                    return ["bash", "-c", words[k + 1]], sudo
                k += 2 if words[k] in ("-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U", "-l") else 1
            if b == "su":
                return [], sudo
            continue
        if b == "env":
            k += 1
            while k < n and (words[k].startswith("-") or "=" in words[k]):
                k += 2 if words[k] in ("-u", "-C", "--unset", "--chdir") else 1
            if k >= n:
                return ["env"], sudo
            continue
        if b in _WRAP_OPTS:
            k += 1
            while k < n and (words[k].startswith("-") or re.match(r"^\d+$", words[k])):
                k += 2 if words[k] in _WRAP_ARG else 1
            if b == "flock" and k < n:
                k += 1
            continue
        if b == "timeout":
            k += 1
            while k < n and words[k].startswith("-"):
                k += 2 if words[k] in ("-k", "-s") else 1
            k += 1
            continue
        return words[k:], sudo
    return [], sudo


def _ssh_split(args):
    """ssh-Argumente -> (host, fernwoerter, riskante_option)"""
    risky = None

    def eat_opts(lst):
        nonlocal risky
        k = 0
        while k < len(lst) and lst[k].startswith("-"):
            t = lst[k]
            if t == "--":
                return k + 1
            if t.startswith("-o"):
                val = t[2:] if len(t) > 2 else (lst[k + 1] if k + 1 < len(lst) else "")
                key, _, v = val.partition("=")
                key = key.strip().split(" ")[0].lower()
                if key not in _SSH_O_SAFE or (key == "stricthostkeychecking"
                                              and v.strip().lower() not in ("yes", "accept-new")):
                    risky = risky or f"-o {key}"
                k += 1 if len(t) > 2 else 2
                continue
            letters = t[1:]
            if letters and letters[0] in _SSH_ARG_LETTERS:
                if letters[0] in _SSH_ASK_LETTERS:
                    risky = risky or f"-{letters[0]}"
                k += 1 if len(letters) > 1 else 2
                continue
            bad = set(letters) & _SSH_ASK_LETTERS
            if bad:
                risky = risky or "-" + "".join(sorted(bad))
            k += 1
        return k

    k = eat_opts(args)
    if k >= len(args):
        return None, [], risky
    host = args[k]
    rest = args[k + 1:]
    rest = rest[eat_opts(rest):]
    return host, rest, risky


_ASK_VERBS = {"rm", "rmdir", "mv", "cp", "ln", "dd", "truncate", "shred", "unlink", "chmod", "chown", "chgrp",
              "chattr", "setfacl", "tee", "kill", "killall", "pkill", "reboot", "service", "apt", "apt-get",
              "aptitude", "dpkg", "snap", "passwd", "chpasswd", "usermod", "useradd", "groupadd", "groupdel",
              "visudo", "ufw", "iptables", "ip6tables", "nft", "wget", "mount", "umount", "fdisk", "parted",
              "mkswap", "swapoff", "systemd-run", "loginctl", "install", "rsync", "scp", "sftp", "sshfs",
              "at", "batch", "shutdown"}
_SYSTEMCTL_MUT = {"start", "stop", "restart", "reload", "try-restart", "reload-or-restart", "enable", "disable",
                  "reenable", "mask", "unmask", "link", "daemon-reload", "daemon-reexec", "kill", "edit",
                  "set-property", "isolate", "set-default", "suspend", "hibernate", "reset-failed", "revert",
                  "preset", "import-environment", "set-environment", "unset-environment", "reboot", "kexec"}
_GIT_MUT = {"push", "commit", "reset", "checkout", "clean", "rebase", "merge", "pull", "rm", "mv", "restore",
            "switch", "apply", "am", "cherry-pick", "revert", "gc", "prune", "update-ref", "init", "clone", "add",
            "notes", "replace", "worktree", "submodule", "fetch"}
_WZ_RISKY = {"bestaetigen", "betrieb", "secrets-hash", "init", "zurueck", "modellwahl", "eingang", "commit",
             "pflege", "reindex"}


def _norm_target(t):
    n_ = t.replace("${HOME}", "~").replace("$HOME", "~").replace("$HOME", "~")
    return n_ if n_ in ("/", "/*") else (n_.rstrip("/") or "/")


def _cluster(a):
    return a[1:] if a.startswith("-") and not a.startswith("--") else ""


def _check_remote_cmd(b, args, res):
    def ask(why):
        res.setdefault("ask", why)

    def deny(why):
        res.setdefault("deny", why)

    pos = [a for a in args if not a.startswith("-")]
    clus = "".join(_cluster(a) for a in args)
    if b == "rm":
        if ("r" in clus or "R" in clus or "--recursive" in args) and any(_norm_target(a) in CRIT_TARGETS
                                                                          for a in pos):
            return deny("rm -r auf kritischem Pfad")
        return ask("rm auf netcup")
    if b.startswith("mkfs") or b == "wipefs":
        return deny("Dateisystem formatieren")
    if b == "dd":
        return deny("dd schreibt auf ein Geraet") if any(a.startswith("of=/dev/") for a in args) else ask("dd")
    if b == "crontab":
        if args == ["-l"]:
            return None
        return deny("crontab -r loescht alle Cronjobs") if "r" in clus else ask("crontab aendern")
    if b in ("userdel", "deluser"):
        return deny("Benutzer loeschen")
    if b == "ufw":
        return deny("Firewall abschalten") if {"disable", "reset"} & set(args) else ask("ufw")
    if b in ("iptables", "ip6tables"):
        return deny("Firewall-Regeln leeren") if ("F" in clus or "--flush" in args) else ask("iptables")
    if b == "find":
        if "-delete" in args and pos and _norm_target(pos[0]) in CRIT_TARGETS | {"~", "/"}:
            return deny("find -delete auf ~ oder /")
        if FIND_BAD & set(args):
            return ask("find mit Aktion")
        return None
    if b == "git":
        k = 0
        while k < len(args) and args[k].startswith("-"):
            if args[k] == "-c":
                ask("git -c")
            k += 2 if args[k] in ("-C", "-c", "--git-dir", "--work-tree", "--namespace") else 1
        sub = args[k] if k < len(args) else ""
        rest = args[k + 1:]
        if sub in ("filter-repo", "filter-branch"):
            return deny("Git-Historie umschreiben")
        if sub == "push" and (any(a in ("--force", "-f", "--force-with-lease") or a.startswith("--force")
                                  or (a.startswith("+") and len(a) > 1) for a in rest) or "f" in "".join(
                _cluster(a) for a in rest)):
            return deny("git push --force")
        if sub in _GIT_MUT:
            return ask(f"git {sub}")
        if sub == "config" and not ({"--get", "-l", "--list", "--get-all", "--get-regexp"} & set(rest)):
            return ask("git config")
        if sub == "stash" and rest[:1] != ["list"]:
            return ask("git stash")
        if sub in ("branch", "tag") and ({"-d", "-D", "-m", "-M", "-c", "-C", "-f", "--delete", "--move", "--force",
                                          "-a", "-s"} & set(rest) or (sub == "tag" and [a for a in rest
                                                                                         if not a.startswith("-")])):
            return ask(f"git {sub} aendert")
        return None
    if b in ("poweroff", "halt"):
        return deny("Server abschalten")
    if b == "shutdown":
        return ask("Neustart des Servers") if ("-r" in args or "--reboot" in args) else deny("Server abschalten")
    if b == "systemctl":
        sub = next((a for a in args if not a.startswith("-")), "")
        if sub in ("poweroff", "halt"):
            return deny("Server abschalten")
        if sub in _SYSTEMCTL_MUT:
            return ask(f"systemctl {sub}")
        return None
    if b in ("chmod", "chown", "chgrp"):
        if ("R" in clus or "--recursive" in args) and any(_norm_target(a) in CRIT_TARGETS for a in pos):
            return deny(f"{b} -R auf ~ oder /")
        return ask(b)
    if b in _ASK_VERBS:
        return ask(f"{b} auf netcup")
    if b in ("pip", "pip3") and args[:1] and args[0] in ("install", "uninstall", "download"):
        return ask("pip installiert")
    if b.startswith("python") and "-m" in args:
        i = args.index("-m")
        if args[i + 1:i + 3] and args[i + 1] == "pip" and args[i + 2:i + 3] and args[i + 2] in ("install",
                                                                                               "uninstall"):
            return ask("pip installiert")
    if b == "npm" and args[:1] and args[0] in ("i", "install", "uninstall", "update", "ci", "publish", "run",
                                                 "exec", "link"):
        return ask("npm")
    if b == "docker" and args[:1] and args[0] in ("run", "rm", "rmi", "stop", "kill", "restart", "start", "exec",
                                                    "compose", "system", "volume", "network", "build", "pull",
                                                    "push", "cp", "commit", "update", "prune", "container",
                                                    "image"):
        return ask("docker aendert")
    if b == "sed" and ("i" in clus or any(a.startswith("--in-place") for a in args)):
        return ask("sed -i")
    if b == "perl" and ("i" in clus or "p" in clus and "i" in clus):
        return ask("perl -i")
    if b == "curl":
        up = [a.upper() for a in args]
        writes = any(a in ("-o", "--output") and (args[i + 1] if i + 1 < len(args) else "") != "/dev/null"
                     for i, a in enumerate(args)) or any(a.startswith("--output=") and a != "--output=/dev/null"
                                                         for a in args)
        if writes or any(a in ("-d", "--data", "--data-raw", "--data-binary", "--data-urlencode", "-F", "--form",
                               "-T", "--upload-file", "-O", "--remote-name", "--json") or a.startswith(
                ("--data", "--json")) for a in args) or any(
                u in ("-XPOST", "-XPUT", "-XDELETE", "-XPATCH") for u in up) or (
                "-X" in args and args.index("-X") + 1 < len(args)
                and args[args.index("-X") + 1].upper() in ("POST", "PUT", "DELETE", "PATCH")):
            return ask("curl sendet oder schreibt")
        return None
    if b == "claude" and not (args[:1] and args[0] in ("--version", "-v", "--help", "-h")):
        return ask("Claude-CLI auf netcup")
    if b in ("printenv",) or (b == "env" and not args) or (b == "export" and (not args or "-p" in args)) \
            or (b in ("declare", "typeset") and (not args or "p" in clus)) or (b == "set" and not args) \
            or (b == "compgen" and "v" in clus):
        return ask("gibt Umgebungsvariablen aus")
    if b == "wz" and args[:1] and args[0] in _WZ_RISKY:
        return ask(f"wz {args[0]}")
    return None


def _has_ansi_c(s):
    """$'...' oder $"..." ausserhalb von Quotes (Bash dekodiert Escapes, shlex nicht)."""
    q = None
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if q is None:
            if c == "\\":
                i += 2
                continue
            if c == "$" and i + 1 < n and s[i + 1] in "'\"":
                return True
            if c in "'\"":
                q = c
        elif q == "'":
            if c == "'":
                q = None
        else:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                q = None
        i += 1
    return False


_LOCAL_READERS = {"cat", "head", "tail", "base64", "xxd", "od", "strings", "gzip", "tar", "zip", "7z", "gpg",
                  "openssl", "type", "more", "less", "dd", "scp", "pscp", "sftp", "rsync", "curl", "ssh", "tee",
                  "cp"}


def _analyze(text, remote, depth, bodies, res):
    if depth > 5:
        res.setdefault("ask", "zu tief verschachtelt")
        return
    if _has_ansi_c(text):
        res.setdefault("ask", "ANSI-C-Quoting verdeckt den Befehl")
    cmds, outs, ins = _simple_cmds(_ltoks(_mask_newlines(text)))
    for t in ins:
        tok = sensitive_in(t)
        if tok:
            res.setdefault("ask", f"geheimer Pfad ({tok[:40]})")
    if remote:
        for t in outs:
            tt = t.strip()
            if re.match(r"^/dev/(?:sd|nvme|vd|xvd|mmcblk)", tt):
                res.setdefault("deny", "Umleitung auf ein Geraet")
            elif tt and tt not in ("/dev/null", "/dev/stdout", "/dev/stderr") and not re.match(r"^\d+$|^-$", tt):
                res.setdefault("ask", "Umleitung in eine Datei")
    for words in cmds:
        for w in words:
            if "`" in w:
                for inner in re.findall(r"`([^`]*)`", w):
                    _analyze(inner, remote, depth + 1, bodies, res)
        eff, sudo = _effective(words)
        if sudo and remote:
            res.setdefault("ask", "sudo/su auf netcup")
        if not eff:
            continue
        b = eff[0].rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
        if b.endswith(".exe"):
            b = b[:-4]
        if remote or b in _LOCAL_READERS:
            for w in words:
                tok = sensitive_in(w)
                if tok:
                    res.setdefault("ask", f"geheimer Pfad ({tok[:40]})")
        hds = [a for a in eff[1:] if a in bodies]
        args = [a for a in eff[1:] if a not in bodies]
        if b in ("bash", "sh", "dash", "zsh"):
            if "-c" in args and args.index("-c") + 1 < len(args):
                _analyze(args[args.index("-c") + 1], remote, depth + 1, bodies, res)
            elif hds:
                _analyze("\n".join(bodies[hds[0]]), remote, depth + 1, bodies, res)
            continue
        if b == "eval":
            _analyze(" ".join(args), remote, depth + 1, bodies, res)
            continue
        if b in ("ssh", "plink"):
            host, rest, risky = _ssh_split(args)
            if host and HOST_TOKEN.search(host):
                if risky:
                    res.setdefault("ask", f"riskante ssh-Option ({risky})")
                if "botuser" in host:
                    res.setdefault("ask", "Zugang als botuser")
                if rest:
                    _analyze(" ".join(rest), True, depth + 1, bodies, res)
                    if rest[0] in ("bash", "sh") and hds:
                        _analyze("\n".join(bodies[hds[0]]), True, depth + 1, bodies, res)
            continue
        if b in ("scp", "pscp"):
            if any(a in ("-S", "-F", "-J", "-i") or (a.startswith("-o") and a[2:].split("=")[0].lower()
                                                       not in _SSH_O_SAFE and len(a) > 2) for a in args):
                res.setdefault("ask", "riskante scp-Option")
            if "-o" in args:
                v = args[args.index("-o") + 1] if args.index("-o") + 1 < len(args) else ""
                if v.split("=")[0].lower() not in _SSH_O_SAFE:
                    res.setdefault("ask", "riskante scp-Option")
            pos = [a for a in args if not a.startswith("-")]
            if pos and HOST_TOKEN.search(pos[-1]) and ":" in pos[-1]:
                res.setdefault("ask", "scp-Upload nach netcup")
            if remote:
                res.setdefault("ask", "scp auf netcup")
            continue
        if b in ("rsync", "sftp", "sshfs"):
            res.setdefault("ask", f"{b}")
            continue
        if remote:
            _check_remote_cmd(b, args, res)


def analyze_bash(cmd):
    """-> dict mit 'deny'/'ask' oder None, wenn die Zerlegung scheitert."""
    try:
        text, bodies = _extract_heredocs(cmd)
        res = {}
        _analyze(text, False, 0, bodies, res)
        return res
    except Exception:
        return None


# ---------------------------------------------------------------- Ablauf
def decide(tool, cmd):
    """-> (entscheidung oder None, grund)"""
    if not cmd or not SSH_WORD.search(cmd) or not HOST_TOKEN.search(cmd):
        return None, "kein netcup-ssh"
    if re.search(r":\(\)\s*\{", cmd):
        return "deny", "Fork-Bombe"
    res = analyze_bash(cmd) if tool == "Bash" else None
    if res is None:  # Rueckfall: Textmuster
        why = deny_reason(cmd)
        if why:
            return "deny", why
        why = ask_reason(cmd)
        if why:
            return "ask", why
    else:
        if "deny" in res:
            return "deny", res["deny"]
        if "ask" in res:
            return "ask", res["ask"]
        why = deny_reason(cmd)
        if why:
            return "ask", f"Datenverlust-Muster im Text ({why})"
    if tool == "Bash":
        try:
            allow_parse(cmd)
            return "allow", "Allowlist"
        except Reject as e:
            rest = f"nicht in der Allowlist ({e})"
    else:
        rest = f"Werkzeug {tool}: keine Freigabe durch den Waechter"
    if (FLAGS / "ssh_guard_strikt.on").exists():
        return "ask", rest + ", Strikt-Modus"
    return None, rest


def _log(decision, reason, cmd):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        if LOG.exists() and LOG.stat().st_size > 512 * 1024:
            LOG.replace(LOG.with_suffix(".log.1"))
        head = re.sub(r"\s+", " ", cmd)[:90]
        head = re.sub(r"(?i)(token|passw\w*|secret|key)\s*[=:]\s*\S+", r"\1=<REDACTED>", head)
        h = hashlib.sha256(cmd.encode("utf-8", "replace")).hexdigest()[:10]
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{decision or 'weiter'}\t{reason}\t{h}\t{head}\n")
    except Exception:
        pass


MSG = {
    "deny": "ssh_netcup_guard: blockiert ({}). Solche Befehle auf netcup fuehrt der Nutzer selbst aus.",
    "ask": "ssh_netcup_guard: Rueckfrage noetig ({}). Fernbefehl auf netcup bitte pruefen.",
    "allow": "ssh_netcup_guard: {}",
}


def main():
    try:
        if (FLAGS / "ssh_guard.off").exists():
            return 0
        data = json.loads(sys.stdin.read() or "{}")
        if not isinstance(data, dict):
            return 0
        tool = data.get("tool_name") or ""
        if tool not in TOOLS:
            return 0
        ti = data.get("tool_input") or {}
        cmd = ti.get("command") or ti.get("cmd") or ti.get("script") or ""
        if not isinstance(cmd, str):
            return 0
        decision, reason = decide(tool, cmd)
        if decision is None and reason == "kein netcup-ssh":
            return 0
        _log(decision, reason, cmd)
        if decision is None:
            return 0
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": MSG[decision].format(reason)}}, ensure_ascii=True))
        return 0
    except Exception:
        return 0


# ---------------------------------------------------------------- Selbsttest
H = "netcup-marco"
CASES = [
    # allow
    ("allow", f"ssh {H} '~/.local/bin/wz find \"Version C MW4 live\" 2>&1 | head -12' 2>&1 | tail -12"),
    ("allow", f"ssh -o BatchMode=yes -o ConnectTimeout=15 {H} '~/.local/bin/wz get audio/x-43bb 2>&1 | grep -i -m3 "
              f"tag' 2>&1 | grep -v -E \"post-quantum|store now|^\\*+$|AUTHORISED\""),
    ("allow", f"timeout 60 ssh -o BatchMode=yes -o ConnectTimeout=8 {H} bash -s <<'EOF' 2>&1 | grep -v -E "
              f"'WARNING|^\\*'\nset -e\n# Kommentar\n~/.local/bin/wz find foo\necho ---\n"
              f"systemctl --user is-active ntfy-eigen\nEOF"),
    ("allow", f"ssh {H} systemctl --user status claude-rc-skills --no-pager -n 20"),
    ("allow", f"ssh {H} \"journalctl --user -u ntfy-eigen -n 50 --no-pager\""),
    ("allow", f"ssh {H} 'git -C ~/projects/x status --short && git -C ~/projects/x log --oneline -5'"),
    ("allow", f"ssh {H} 'ls -la ~/.claude/hooks | head -20'"),
    ("allow", f"ssh {H} md5sum ~/.claude/hooks/notify_fallback.py"),
    ("allow", f"ssh -o BatchMode=yes {H} '~/.local/bin/wz neu --titel \"Test\" --text \"kurzer Text\"'"),
    ("allow", f"ssh {H} 'echo ===RESULT===; uptime; df -h /' | sed -n '/===RESULT===/,$p'"),
    ("allow", f"ssh -p <ssh-port> marco@100.x.y.z 'cat \"$HOME/projects/Skills_&_Co/PROGRESS.md\" | tail -40'"),
    ("allow", f"ssh {H} \"ls ~/x\\\"; touch y\\\"\""),  # ; liegt remote in Anfuehrungszeichen -> harmlos
    ("weiter", f"ssh -p <ssh-port> marco@100.x.y.z 'cat ~/projects/Skills_&_Co/PROGRESS.md'"),  # & remote ungequotet
    ("weiter", f"ssh {H} 'cd ~/projects/Skills_\\&_Co && ls'"),
    # deny
    ("deny", f"ssh {H} 'rm -rf ~'"),
    ("deny", f"ssh {H} rm -rf /"),
    ("deny", f"ssh {H} \"rm -rf ~/.claude\""),
    ("deny", f"ssh {H} 'rm -fr $HOME/'"),
    ("deny", f"ssh {H} 'crontab -r'"),
    ("deny", f"ssh {H} 'mkfs.ext4 /dev/sda1'"),
    ("deny", f"ssh {H} 'dd if=/dev/zero of=/dev/sda bs=1M'"),
    ("deny", f"ssh {H} 'cd ~/p && git push --force origin main'"),
    ("deny", f"ssh {H} 'sudo poweroff'"),
    ("deny", f"timeout 30 ssh -o BatchMode=yes {H} bash -s <<'EOF'\nls\nrm -rf ~/projects\nEOF"),
    # ask
    ("ask", f"ssh {H} 'rm ~/projects/x/file.txt'"),
    ("ask", f"ssh {H} 'systemctl --user restart claude-rc-skills'"),
    ("ask", f"ssh {H} 'cat ~/.claude/secrets/gemini.env'"),
    ("ask", f"ssh {H} 'grep KEY ~/.config/rclone/rclone.conf'"),
    ("ask", f"scp notiz.txt {H}:~/x/"),
    ("ask", f"rsync -a ordner/ {H}:~/y/"),
    ("ask", f"ssh {H} '~/.local/bin/wz bestaetigen setup/x-1234'"),
    ("ask", f"ssh {H} 'echo x > ~/.bashrc'"),
    ("ask", f"ssh {H} 'echo x >> notes.txt'"),
    ("ask", f"ssh {H} \"sed -i s/a/b/ ~/f.txt\""),
    ("ask", f"ssh {H} 'git -C ~/p commit -am x'"),
    ("ask", f"ssh {H} sudo apt upgrade"),
    ("ask", f"ssh {H} 'reboot'"),
    ("ask", f"ssh {H} 'cat key.pub | tee -a ~/.ssh/authorized_keys'"),
    ("ask", f"ssh -o ProxyCommand=calc.exe {H} ls"),
    ("ask", f"ssh -L 8080:127.0.0.1:5678 {H} sleep 60"),
    ("ask", f"ssh -i ~/.ssh/.ssh_botuser_key {H} ls"),
    ("ask", f"ssh {H} printenv"),
    ("ask", f"ssh {H} 'cat /proc/self/environ'"),
    ("ask", f"ssh netcup-botuser 'ls ~'"),
    ("ask", f"ssh {H} 'claude -p hallo'"),
    ("ask", f"ssh {H} 'kill 1234'"),
    ("ask", f"ssh {H} 'curl -X POST http://127.0.0.1:8000/api/x'"),
    ("ask", f"ssh {H} 'set'"),
    # weiter (kein Urteil)
    ("weiter", f"ssh {H} 'for f in a b; do echo $f; done'"),
    ("weiter", f"ssh {H} 'python3 ~/x.py'"),
    ("weiter", f"ssh {H} 'ls' ; echo fertig"),
    ("weiter", f"ssh {H} 'ls $HOME'"),
    ("weiter", f"ssh {H} ls | grep x ~/.ssh/known_hosts_x"),  # lokales Lesen: nicht Sache des Waechters
    ("ask", f"cat ~/.ssh/id_ed25519 | ssh {H} 'cat > /tmp/k'"),
    ("ask", f"ssh {H} 'cat > /tmp/k' < ~/.claude/.credentials.json"),
    ("allow", f"ssh {H} 'crontab -l 2>/dev/null | head -5'"),
    ("allow", f"ssh {H} 'grep -c x f.txt' | grep -v -E \"^\\*+$|AUTH\""),
    ("ask", f"ssh {H} -oProxyCommand=x ls"),
    ("weiter", f"ssh {H} 'grep -r foo ~/.claude'"),
    ("weiter", f"ssh {H} 'cat ~/.claude/s*/x'"),
    ("ask", f"ssh {H} 'find ~ -name x -exec cat {{}} +'"),
    ("weiter", f"ssh {H} \"echo $(whoami)\""),
    ("weiter", f"ssh {H} 'ls' > out.log"),  # lokale Umleitung: Sache des Classifiers
    ("weiter", f"ssh {H} \"ls ~/x\\\"\\\"; touch y\""),  # ; remote ungequotet -> touch nicht erlaubt
    ("weiter", f"ssh {H} 'ls' 2>err.txt"),
    ("ask", f"ssh {H} 'ls > /tmp/liste.txt'"),  # Umleitung auf netcup
    ("allow", f"ssh {H} '~/.local/bin/wz neu --titel \"sed -i > rm -rf\" --text \"a > b.txt\"'"),
    ("allow", f"ssh {H} '~/.local/bin/wz neu --text \"Merke: rm -rf ~ nie\"'"),  # nur Text, wird gespeichert
    ("ask", f"ssh {H} '~/.local/bin/wz neu --text \"x\"; rm -rf ~/tmp/x'"),
    ("ask", f"ssh {H} $'ls\\x3b rm x'"),
    ("deny", f"bash -c \"ssh {H} 'rm -rf ~'\""),
    ("ask", f"ssh {H} 'xargs -I {{}} rm {{}} < liste.txt'"),
    ("ask", f"ssh {H} 'sudo -u botuser ls'"),
    ("deny", f"ssh {H} 'cd ~ && rm -rf *'"),
    ("ask", f"printf 'rm -rf ~/x' | ssh {H} bash -c \"cat; rm y\""),
    ("allow", f"ssh {H} 'grep -c token static/tailwind/_tokens.css'"),
    ("ask", f"ssh {H} 'cat ~/.env.local'"),
    ("allow", f"ssh {H} 'cat ~/projects/x/.env.example'"),
    ("weiter", "grep -n \"ssh netcup-marco\" ~/.claude/CLAUDE.md"),
    ("weiter", "git log --oneline -5"),
    ("weiter", f"ssh {H} 'ls' & echo x"),
    ("weiter", f"ssh {H} 'LD_PRELOAD=/tmp/x.so ls'"),
    ("ask", f"ssh {H} 'wz find x'\nrm -rf ~"),  # lokales rm: destructive_command_blocker; hier Rueckfrage
    ("weiter", f"ssh {H} 'git -C ~/p diff --output=/tmp/x'"),
]
TOOL_CASES = [
    ("PowerShell", "ask", f"ssh {H} 'rm x.txt'"),
    ("PowerShell", "weiter", f"ssh {H} 'ls'"),
    ("Monitor", "deny", f"ssh {H} 'rm -rf ~'"),
]


def selftest():
    fails = 0
    total = 0
    for want, cmd in CASES:
        got, why = decide("Bash", cmd)
        got = got or "weiter"
        total += 1
        if got != want:
            fails += 1
            print(f"FEHLER soll={want} ist={got} ({why}) :: {cmd!r}")
    for tool, want, cmd in TOOL_CASES:
        got, why = decide(tool, cmd)
        got = got or "weiter"
        total += 1
        if got != want:
            fails += 1
            print(f"FEHLER [{tool}] soll={want} ist={got} ({why}) :: {cmd!r}")
    # main() robust gegen kaputte Eingaben
    import io
    import contextlib
    for raw in ("", "{kaputt", "[]", "null", "{}", '{"tool_name": "Bash"}', '{"tool_name": "Bash", "tool_input": 5}'):
        total += 1
        old = sys.stdin
        try:
            sys.stdin = io.StringIO(raw)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main()
            if rc != 0 or buf.getvalue().strip():
                fails += 1
                print(f"FEHLER robust {raw!r}: rc={rc} out={buf.getvalue()!r}")
        finally:
            sys.stdin = old
    print(f"ssh_netcup_guard Selbsttest: {total - fails}/{total} ok")
    return 1 if fails else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.exit(selftest())
    if len(sys.argv) > 2 and sys.argv[1] == "--probe-file":
        # JSON-Liste [{"cmd": "...", "tool": "Bash"}] -> eine Zeile je Befehl (Pruefung ohne Shell-Quoting)
        sys.stdout.reconfigure(encoding="utf-8")
        items = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        out = []
        for it in items:
            d, w = decide(it.get("tool", "Bash"), it.get("cmd", ""))
            out.append({"cmd": it.get("cmd", ""), "tool": it.get("tool", "Bash"), "decision": d or "weiter",
                        "reason": w})
        print(json.dumps(out, ensure_ascii=False, indent=1))
        sys.exit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "--probe":
        sys.stdout.reconfigure(encoding="utf-8")
        tool = sys.argv[sys.argv.index("--tool") + 1] if "--tool" in sys.argv else "Bash"
        d, w = decide(tool, sys.argv[2])
        print(f"{d or 'weiter'}\t{w}")
        sys.exit(0)
    sys.exit(main())
