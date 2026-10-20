#!/usr/bin/env python
r"""codex_call.py — Wrapper um die OpenAI-Codex-CLI mit Usage-Tracking.

Spiegelt gemini_call.py fuer Provider-Paritaet: jeder Codex-Consult laeuft durch
dieses Script -> deterministisches Logging (sehen ob die ChatGPT-Plus-Limits
reichen). cross_model_skeptic.py --provider codex ruft das hier.

SETUP (einmalig, der Nutzer):
  npm install -g @openai/codex            # Node 18+
  codex login --device-auth               # URL+Code -> Browser-Login (ChatGPT Plus)
Danach laeuft jeder Call ueber die Plus-Sub (kein API-Key noetig). Alternativ
OPENAI_API_KEY env (paid per-Token) — dann CODEX_USE_API=1 setzen.

Loggt nach ~/.claude/state/codex_usage.jsonl (analog gemini_usage.jsonl).
Exit: 0 ok · 3 auth-needed · 4 quota/usage-limit · sonst rc.

--------------------------------------------------------------------------
v2 (2026-08-03) — WARUM DIESE VERSION EXISTIERT
--------------------------------------------------------------------------
Beim Nacht-Review des AudioSetup-Projekts fand Codex rund 10 % der Befunde,
die Fable 5 fand. Nachgemessen war die Ursache NICHT das Modell, sondern der
Aufruf. Drei Belege, alle am 2026-08-03 an codex-cli 0.144.4 verifiziert:

  1. `reasoning effort: none` war der DEFAULT (Banner-Ausgabe). Codex hat also
     ohne jedes Nachdenken gescannt, waehrend Fable mit Extended Thinking und
     Multi-Agent-Fan-Out lief. Groesster Einzelhebel.
  2. Es wurde nie ein Arbeitsverzeichnis gesetzt (`-C/--cd` fehlte, dazu
     `--skip-git-repo-check`) -> der Agent hatte KEINEN Projekt-Root und konnte
     nur lesen, was zufaellig im Prompt stand. Ein agentischer Reviewer ohne
     Dateizugriff ist ein Chatbot.
  3. `codex exec review` — ein dedizierter Review-Modus mit --base/--uncommitted/
     --commit — wurde gar nicht genutzt; alles lief ueber generisches `exec`.

Dazu: Timeout 300 s fuer einen Agenten, der lesen und iterieren will, und keine
strukturierte Ausgabe (--output-schema), also Prosa statt vergleichbarer Findings.

Default-Modell ist `gpt-5.6-sol` (Stand 2026-08-03). Selbstauskunft des Modells
("GPT-5") ist unzuverlaessig — der Banner ist die Quelle.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
try:
    # Gepipte Eingabe ist UTF-8 (cat, git diff, subprocess). Windows dekodierte
    # sonst mit cp1252 -> Mojibake beim fremden Modell; `replace`, damit ein
    # einzelnes kaputtes Byte nicht die ganze Eingabe kostet.
    sys.stdin.reconfigure(encoding="utf-8-sig", errors="replace")
except Exception:
    pass

USAGE_LOG = Path.home() / ".claude" / "state" / "codex_usage.jsonl"
SCHEMA_FINDINGS = Path.home() / ".claude" / "scripts" / "codex_findings_schema.json"

# Ein agentischer Reviewer liest, greppt und iteriert — 300 s schneiden ihn mitten
# im Lauf ab. Kurze Second-Opinions bleiben bei 300 s, Reviews bekommen 30 min.
CODEX_TIMEOUT = int(os.environ.get("CODEX_TIMEOUT", "300"))
CODEX_REVIEW_TIMEOUT = int(os.environ.get("CODEX_REVIEW_TIMEOUT", "1800"))

# Effort je Modus. `none` (CLI-Default) ist fuer Fehlersuche unbrauchbar.
DEFAULT_EFFORT = {
    "review": "high",
    "second-opinion": "high",
    "research": "medium",
    "offload": "low",       # Bulk/mechanisch — hier ist wenig Denken gewollt
    "other": "medium",
}

# Modus -> Codex-Profil (`-p`, layert ~/.codex/<name>.config.toml ueber die Basis).
# Die Politik steht damit in ~/.codex, nicht hier — der Nutzer kann sie pro Maschine
# tunen, ohne dieses (gesyncte) Script anzufassen. Fehlt das Profil auf einer
# Maschine, faellt der Wrapper auf `-c model_reasoning_effort` zurueck.
# Modell je Modus, nur wo es vom Basis-Default abweichen soll (2026-08-25).
# Die Basis-Config faehrt `gpt-5.6-sol`; Bulk/Offload braucht das Flaggschiff
# nicht und wuerde nur das knappe Plus-Kontingent verbrauchen. Leerer Wert
# oder fehlender Modus = Basis-Config gilt, kein `-m`.
MODE_MODEL = {
    "offload": "gpt-5.6-luna",
}

CODEX_HOME = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
MODE_PROFILE = {
    "review": "review",
    "second-opinion": "review",
    "offload": "bulk",
    "research": None,        # Basis-Config (medium) genuegt
    "other": None,
}


def _profile_for(mode: str, explicit: str) -> str:
    name = explicit or MODE_PROFILE.get(mode) or ""
    if name and (CODEX_HOME / f"{name}.config.toml").exists():
        return name
    return ""

_QUOTA_MARKERS = ("rate limit", "rate-limit", "usage limit", "quota", "429",
                  "too many requests", "resource_exhausted", "limit reached")
_AUTH_MARKERS = ("sign in", "signin", "log in", "login", "not authenticated",
                 "unauthenticated", "unauthorized", "authenticate", "device-auth",
                 "no credentials", "please run codex login")


def _read_stdin(grace: float = 5.0) -> str:
    """stdin nur lesen, wenn wirklich etwas anliegt.

    `sys.stdin.isatty()` allein genuegt NICHT — und das ist kein Randfall: laeuft
    der Wrapper im Hintergrund, unter einem Job-Runner oder in einer Agent-Session,
    ist stdin zwar kein TTY, aber ein offener Pipe **ohne Daten**. `read()` wartet
    dann auf ein EOF, das nie kommt. Real passiert am 2026-08-03: der Prozess hing
    2,5 Minuten, ohne codex auch nur ein einziges Mal zu starten — kein Output,
    kein Log-Eintrag, kein Timeout (der greift erst um den codex-Aufruf herum).
    Der Bug steckte schon in v1.

    Regel auf beiden Plattformen: Kommt binnen `grace` das erste Zeichen oder EOF,
    wird bis EOF gelesen; kommt nichts, geht es ohne Eingabe weiter (Hinweis auf
    stderr). Ein Erzeuger, der laenger als `grace` bis zum ERSTEN Zeichen braucht,
    verliert also seine Eingabe — bei `git diff |` oder `cat |` kommen die Daten
    sofort, also ein bewusster, dokumentierter Tradeoff gegen das Haengen.

    Bewusst OHNE Frist fuer das Lesen bis EOF: Schreibt ein Erzeuger etwas und
    haelt den Pipe dann offen, wartet der Wrapper mit ihm (uebliches
    Filter-Verhalten; eine Shell-Pipeline haengt dann ohnehin am Erzeuger). Eine
    Frist schnitte langsame Eingaben ab. Am 2026-09-30 geprueft und verworfen.

    POSIX: `select` beantwortet die Frage exakt (lesbar = Daten oder EOF).
    Windows: `select` kann keine Pipes, deshalb ein Daemon-Thread, der mit
    `read(1)` das erste Zeichen meldet. Bis 2026-09-30 wartete er `grace` lang auf
    das KOMPLETTE `read()`: ein Erzeuger, der sofort schrieb, aber spaeter als
    `grace` fertig wurde, verlor am PC still die ganze Eingabe (gemessen: EOF nach
    7 s -> 0 Zeichen), auf netcup nicht. Dieselbe Sonde lief auf beiden Maschinen.

    Dekodiert wird UTF-8 mit `errors="replace"` (`sys.stdin.reconfigure` oben).
    Vorher: am PC cp1252 -> Mojibake; auf netcup `strict` -> ein einzelnes
    kaputtes Byte warf UnicodeDecodeError, den das `except` hier verschluckte.
    """
    if sys.stdin is None:
        return ""
    try:
        if sys.stdin.isatty():
            return ""
    except Exception:
        return ""

    silent = f"[stdin] {grace:g} s lang nichts auf offenem stdin, weiter ohne Eingabe"

    # Nach dem ersten Zeichen wird OHNE Obergrenze bis EOF gelesen, auf beiden
    # Plattformen: der Erzeuger lebt dann und liefert noch. Hier kein Timeout
    # nachruesten, das schnitte langsame Eingaben ab (genau der Fehler bis 30.09.).
    if os.name != "nt":
        try:
            import select
            ready, _, _ = select.select([sys.stdin], [], [], grace)
            if not ready:
                print(silent, file=sys.stderr)
                return ""
            return sys.stdin.read()
        except Exception as exc:
            print(f"[stdin] Lesefehler ({type(exc).__name__}), weiter ohne Eingabe",
                  file=sys.stderr)
            return ""

    import threading
    box: list[str] = []
    started = threading.Event()  # erstes Zeichen ODER EOF liegt an

    def _slurp() -> None:
        try:
            head = sys.stdin.read(1)
            started.set()
            if head:
                head += sys.stdin.read()
            box.append(head)
        except Exception as exc:
            print(f"[stdin] Lesefehler ({type(exc).__name__}), weiter ohne Eingabe",
                  file=sys.stderr)
        finally:
            started.set()

    t = threading.Thread(target=_slurp, daemon=True)
    t.start()
    if not started.wait(grace):
        print(silent, file=sys.stderr)
        return ""
    t.join()
    return box[0] if box else ""


def _stamp(payload: dict) -> None:
    try:
        USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with USAGE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _build_cmd(codex: str, args, effort: str, out_file: Path | None,
               profile: str = "") -> list[str]:
    """Baut die Kommandozeile. Reihenfolge zaehlt: Subcommand vor den Flags."""
    cmd = [codex, "exec"]

    # Profil zuerst — spaetere -c/-s/-m ueberschreiben es gezielt.
    if profile:
        cmd += ["-p", profile]

    # Arbeitsverzeichnis ZUERST — ohne das hat der Agent keinen Projekt-Kontext.
    if args.repo:
        repo = Path(args.repo).expanduser().resolve()
        cmd += ["-C", str(repo)]
        # Befund 2026-09-30 (Allgemein-Server/IdleSlayer): --repo auf einen Ordner OHNE
        # Git (z. B. Games-Baum am PC) brach mit "Not inside a trusted directory and
        # --skip-git-repo-check was not specified" ab -> Wrapper im ganzen Gamebot-
        # Ordner unbrauchbar. Darum: kein Git-Worktree -> Check ueberspringen.
        try:
            in_git = subprocess.run(["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
                                    capture_output=True, text=True, timeout=10).stdout.strip() == "true"
        except (OSError, subprocess.SubprocessError):
            in_git = False
        if not in_git:
            cmd += ["--skip-git-repo-check"]
    else:
        # Ohne Repo ist der Git-Check hinderlich.
        cmd += ["--skip-git-repo-check"]

    # read-only: Second-Opinion/Review darf NICHT editieren. Bewusster Tradeoff —
    # damit kann Codex auch keine Tests laufen lassen. Fuer einen Lauf, der die
    # Suite ausfuehren soll, --sandbox workspace-write setzen (der Nutzer entscheidet).
    cmd += ["--sandbox", args.sandbox]

    if args.model:
        cmd += ["-m", args.model]
    elif MODE_MODEL.get(args.mode):
        # Kontingent-Schutz (2026-08-25): die Basis-Config steht auf `sol`
        # (der Nutzer-Entscheid). Sol hat auf ChatGPT-Plus die kleinste Zuteilung
        # der Familie — veroeffentlichte Spanne 10-100 lokale Nachrichten pro
        # 5-h-Fenster gegenueber 250-2000 bei luna, dazu ein nicht
        # veroeffentlichtes Wochenlimit. Bulk-Arbeit auf dem Flaggschiff
        # laufen zu lassen verbrennt genau dieses Kontingent ohne Gegenwert:
        # `offload` faehrt ohnehin mit niedrigem Effort. Darum hier
        # herunterschalten, statt die Basis-Config aufzuweichen.
        cmd += ["-m", MODE_MODEL[args.mode]]
    # Effort nur explizit setzen, wenn KEIN Profil greift (sonst waere die Politik
    # doppelt gepflegt und driftet) oder der Nutzer ihn per --effort erzwingt.
    if effort and (not profile or args.effort):
        cmd += ["-c", f'model_reasoning_effort="{effort}"']

    if args.mode == "review":
        cmd += ["review"]
        if args.base:
            cmd += ["--base", args.base]
        elif args.uncommitted:
            cmd += ["--uncommitted"]
        elif args.commit:
            cmd += ["--commit", args.commit]

    # --output-schema NUR im generischen exec-Modus. `codex exec review` bringt sein
    # eigenes Ausgabeformat mit (P1/P2/P3 + file:line) und listet die Option nicht;
    # dort gesetzt wird sie wirkungslos durchgereicht. Verifiziert 2026-08-03.
    if args.schema and args.mode != "review":
        schema = SCHEMA_FINDINGS if args.schema == "findings" else Path(args.schema)
        if schema.exists():
            cmd += ["--output-schema", str(schema)]
    if out_file:
        cmd += ["-o", str(out_file)]

    cmd += ["-"]                      # Prompt via stdin, nie via argv
    return cmd


def main() -> int:
    p = argparse.ArgumentParser(description="Codex-CLI wrapper + usage tracker")
    p.add_argument("--mode", default="other",
                   choices=["offload", "second-opinion", "research", "review", "other"])
    p.add_argument("--label", default="")
    p.add_argument("--repo", default="", metavar="DIR",
                   help="Arbeitsverzeichnis des Agenten (-C). OHNE das kein Dateizugriff!")
    p.add_argument("--effort", default="", choices=["", "none", "low", "medium", "high"],
                   help="reasoning effort; leer = Modus-Default (review/second-opinion: high)")
    p.add_argument("--model", default="", help="Modell pinnen (Default der CLI: gpt-5.6-sol)")
    p.add_argument("--sandbox", default="read-only",
                   choices=["read-only", "workspace-write"],
                   help="workspace-write nur wenn Codex Tests ausfuehren soll")
    p.add_argument("--schema", default="",
                   help="'findings' fuer das mitgelieferte Findings-Schema, sonst Pfad zu JSON-Schema")
    p.add_argument("--profile", default="",
                   help="Codex-Profil (~/.codex/<name>.config.toml). Leer = Modus-Default "
                        "(review/second-opinion->review, offload->bulk). 'tests' erlaubt "
                        "Codex das Ausfuehren der Suite (workspace-write!).")
    p.add_argument("--base", default="", help="review: gegen diesen Branch diffen")
    p.add_argument("--uncommitted", action="store_true", help="review: staged+unstaged+untracked")
    p.add_argument("--commit", default="", help="review: genau diesen SHA pruefen")
    p.add_argument("--timeout", type=int, default=0, help="Sekunden; 0 = Modus-Default")
    p.add_argument("prompt", nargs=argparse.REMAINDER, help="Prompt (alles nach --)")
    args = p.parse_args()

    prompt = " ".join(a for a in args.prompt if a != "--").strip()
    if not prompt and args.mode != "review":
        print(json.dumps({"error": "kein prompt (alles nach -- angeben)"}, ensure_ascii=False))
        return 2

    stdin_data = _read_stdin()
    full_input = prompt + (("\n\n=== EINGABE ===\n" + stdin_data) if stdin_data else "")
    est_tokens = (len(prompt) + len(stdin_data)) // 4

    effort = args.effort or DEFAULT_EFFORT.get(args.mode, "medium")
    profile = _profile_for(args.mode, args.profile)
    timeout = args.timeout or (CODEX_REVIEW_TIMEOUT if args.mode == "review" else CODEX_TIMEOUT)

    t0 = time.time()
    rc, out, err = 1, "", ""
    out_file: Path | None = None
    codex = shutil.which("codex")
    if not codex:
        err = "codex-cli nicht gefunden (npm install -g @openai/codex)"
    else:
        out_file = Path(os.environ.get("TMPDIR", "/tmp")) / f"codex_last_{os.getpid()}.txt"
        cmd = _build_cmd(codex, args, effort, out_file, profile)
        if os.name == "nt" and codex.lower().endswith((".cmd", ".bat")):
            cmd = ["cmd", "/c"] + cmd
        # Secrets nicht an Codex vererben: Codex schreibt seine Umgebung im Klartext nach
        # ~/.codex/shell_snapshots (Befund 2026-10-01). Login liegt in auth.json.
        _cenv = {k: v for k, v in os.environ.items()
                 if k in ("OPENAI_API_KEY", "CODEX_API_KEY")
                 or not re.search(r"KEY|TOKEN|SECRET|PASSW|WEBHOOK|CREDENTIAL", k, re.I)}
        # Stufe-2 nur, wo Codex' Memory-MCP den Header aus der Env nimmt (config.toml
        # env_http_headers=MCP_API_KEY, PC-Variante). netcup nutzt den stdio-Adapter,
        # der mcp.env selbst liest -> dort kein Schluessel in die Codex-Umgebung.
        try:
            if "MCP_API_KEY" in (CODEX_HOME / "config.toml").read_text(encoding="utf-8", errors="replace"):
                from memory_auth import get_api_key as _gak
                _mk = _gak()
                if _mk:
                    _cenv["MCP_API_KEY"] = _mk
        except Exception:
            pass
        try:
            proc = subprocess.run(
                cmd, input=full_input, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=timeout, env=_cenv,
            )
            rc, out, err = proc.returncode, proc.stdout or "", proc.stderr or ""
            # -o schreibt nur die letzte Agent-Nachricht — sauberer als stdout,
            # das bei --json auch den Event-Stream enthaelt.
            if rc == 0 and out_file.exists():
                txt = out_file.read_text(encoding="utf-8", errors="replace").strip()
                if txt:
                    out = txt
        except subprocess.TimeoutExpired:
            err = f"timeout nach {timeout}s"
        except Exception as e:
            err = f"exec-fehler: {e}"
        finally:
            try:
                if out_file and out_file.exists():
                    out_file.unlink()
            except Exception:
                pass
    dur = round(time.time() - t0, 1)

    el = (err + " " + out).lower()
    # Quota-Erkennung NUR aus stderr und NUR bei rc != 0 (Fix 2026-08-25,
    # p-856fb92d61). Vorher fehlte beides, und die Folge war teuer: die
    # Codex-CLI schreibt ihre Rate-Limit-Auslastung bei JEDEM Lauf routinemaessig
    # nach stderr ("rate limit ... used_percent"). Der Marker traf also auch bei
    # erfolgreichen Laeufen, `status` liess `quota` ueber `rc == 0` gewinnen, und
    # weiter unten wird bei status=="quota" mit Exit 4 returnt — VOR `print(out)`.
    # Damit wurde die fertige Antwort verworfen und ein Limit gemeldet, das es
    # nicht gab. Belegt am 2026-08-25 (rc=0, 313 s Laufzeit, used_percent 12,
    # rate_limit_reached_type null) und rueckwirkend am 2026-08-03.
    # Die Auth-Pruefung darunter hatte den rc-Test von Anfang an richtig.
    el_err = err.lower()
    quota_hit = any(m in el_err for m in _QUOTA_MARKERS) and rc != 0
    auth_needed = any(m in el for m in _AUTH_MARKERS) and rc != 0
    status = ("quota" if quota_hit else "auth-needed" if auth_needed
              else "ok" if rc == 0 else "error")

    _stamp({
        "ts": datetime.now(timezone.utc).isoformat(), "provider": "codex",
        "mode": args.mode, "label": args.label, "prompt_chars": len(prompt),
        "stdin_bytes": len(stdin_data), "est_tokens": est_tokens,
        "duration_s": dur, "rc": rc, "status": status,
        "quota_hit": quota_hit, "auth_needed": auth_needed,
        # v2: ohne diese drei ist im Nachhinein nicht rekonstruierbar, WARUM ein
        # Lauf schlecht war — genau das Problem beim Nacht-Review.
        # Bei aktivem Profil erzwingt ~/.codex/<name>.config.toml den Effort, nicht
        # dieser Code. Dann NICHT die hiesige Zahl loggen — sie waere geraten, sobald
        # der Nutzer das Profil aendert. Ehrlicher: die Quelle nennen.
        "effort": (args.effort or (f"profil:{profile}" if profile else effort)),
        "model": args.model or "cli-default",
        "profile": profile or "(basis-config)",
        "repo": args.repo or "", "sandbox": args.sandbox, "schema": bool(args.schema),
    })

    if status == "auth-needed":
        print("[codex] Login fehlt: `codex login --device-auth` ausfuehren "
              "(URL+Code -> Browser, ChatGPT Plus). Dann erneut.", file=sys.stderr)
        return 3
    if status == "quota":
        print("[codex] ChatGPT-Plus-Limit getroffen (5h-Fenster). Spaeter erneut "
              "oder Pro erwaegen. ai_usage.py zeigt den Trend.", file=sys.stderr)
        return 4
    if rc != 0:
        # 200 Zeichen schnitten die eigentliche Meldung ab — der Banner allein ist
        # ~180 Zeichen lang, die API-Fehlermeldung stand dahinter (2026-08-03).
        # Deshalb Kopf UND Ende zeigen: der Fehler steht praktisch immer am Ende.
        msg = err.strip()
        shown = msg if len(msg) <= 1200 else msg[:300] + "\n  […]\n" + msg[-900:]
        print(f"[codex] Fehler (rc={rc}):\n{shown}", file=sys.stderr)
        return rc

    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
