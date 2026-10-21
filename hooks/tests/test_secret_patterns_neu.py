#!/usr/bin/env python3
"""Testsatz S12 (E1, 2026-10-21): patterns_neu hinter Flag secret_patterns_neu.on.

Prueft secret_write_guard.py und secret_leak_detector.py in einem Sandbox-HOME
(temporaeres Verzeichnis) -- das echte ~/.claude/lessons/leaks.jsonl wird nicht
beruehrt, das echte Flag nicht gesetzt.

  A  ohne Flag bytegleich: alte Hooks (.bak.pre-e1.*) + alte JSON gegen neue
     Hooks + neue JSON ueber denselben Korpus. Verglichen werden Exit-Code,
     stdout, stderr und die Log-Zeilen (ohne Zeitstempel).
  B  mit Flag: jede neue Klasse wird erkannt (Guard: deny, Detector: Meldung
     mit Klassenname), Bestandsklassen weiter erkannt, Negativfaelle bleiben
     still, Guard-Deny-Grund nach Anh. A12.
  C  mit Flag, JSON ohne patterns_neu bzw. kaputt: hartcodierte Ersatzlisten
     greifen.
  D  Log-Hygiene: kein Dummy-Wert in den Sandbox-Logs.

Alle Werte sind SYNTHETISCH und werden erst zur Laufzeit zusammengesetzt, damit
diese Datei at-rest kein Muster trifft. Ausgabe: nur Labels, nie Werte.

Aufruf: python3 ~/.claude/hooks/tests/test_secret_patterns_neu.py [--baseline-ts <ts>]
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REAL = Path.home() / ".claude"
HOOKS = ("secret_write_guard.py", "secret_leak_detector.py")

# --- synthetische Dummy-Werte (nur zur Laufzeit zusammengesetzt) ---
B64 = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo" * 3
NEU_POS = {
    "Discord Webhook": [
        "https://" + "discord.com/api/" + "webhooks/" + "1" * 19 + "/" + "D" * 68,
        "https://" + "ptb.discordapp.com/api/v10/" + "webhooks/" + "2" * 18 + "/" + "x_Y-" * 17,
    ],
    "Anthropic OAuth Token": [
        "sk-ant-" + "oat01-" + "A" * 95,
        "sk-ant-" + "ort01-" + "b_C-" * 20,
    ],
    "PEM Private Key": [
        "-----BEGIN " + "RSA PRIVATE KEY-----\n" + B64 + "\n-----END RSA PRIVATE KEY-----",
        "-----BEGIN " + "OPENSSH PRIVATE KEY-----\n" + B64,
        "-----BEGIN " + "PRIVATE KEY-----\\n" + B64 + "\\n",
        "-----BEGIN " + "RSA PRIVATE KEY-----\nProc-Type: 4,ENCRYPTED\nDEK-Info: AES-128-CBC,0011AABB\n\n" + B64,
        "-----BEGIN " + "PGP PRIVATE KEY BLOCK-----\nVersion: Dummy 1\n\n" + B64,
    ],
    "Tailscale Key": [
        "tskey-" + "auth-" + "kDUMMY1CNTRL-" + "Z" * 30,
        "tskey-" + "a" * 32,
    ],
    "JWT": [
        "eyJ" + "hbGciOiJIUzI1NiJ9" + "." + "eyJ" + "zdWIiOiJkdW1teSJ9" + "." + "S" * 43,
    ],
    "Hugging Face Token": [
        "hf_" + "Q" * 34,
    ],
}
ALT_POS = {
    "Anthropic API Key": "sk-ant-api" + "03-" + "FAKETEST" + "A" * 40,
    "OpenAI Project Key": "sk-" + "proj-" + "FAKETEST" * 6,
    "GitHub PAT Classic": "ghp" + "_" + ("FAKETEST" * 5)[:36],
    "AWS Access Key ID": "AKI" + "A" + "FAKETESTFAKETEST",
    "Google API Key": "AIz" + "a" + ("FAKETEST" * 5)[:35],
    "Slack Token": "xox" + "b-" + "FAKETEST-1234567890",
    "Discord Bot Token": ".".join(["FakeDiscordTokenSegment1", "FakeSg", "FakeDiscordTokenSegment3Long"]),
}
NEG = [
    "https://discord.com/api/webhooks/ ist nur der Pfad, ohne id und token",
    "Webhook-Muster: https://discord.com/api/webhooks/<id>/<token> (Platzhalter)",
    "https://discord.com/channels/123456789012345678/123456789012345678 ist ein Kanal-Link",
    "sk-ant- ist nur ein Praefix, sk-ant-" + "oat01- ohne Wert",
    "-----BEGIN " + "PRIVATE KEY----- steht nur als Kopfzeile in der Doku",
    "-----BEGIN " + "PUBLIC KEY-----\n" + B64,
    "tskey- und tskey-auth- sind nur Praefixe in der Doku",
    "eyJhbGciOi ist ein JWT-Kopf ohne Rest, harmlos",
    "from huggingface_hub import hf_hub_download; hf_token_from_env()",
    "Ganz normaler Text ohne Secrets, laenger als zwanzig Zeichen.",
]
A12_START = "Secret-Muster "
ALT_START = "Secret-Pattern "


def all_values() -> list[str]:
    vals = [v for vs in NEU_POS.values() for v in vs] + list(ALT_POS.values())
    return vals


def guard_payloads() -> list[tuple[str, str, str]]:
    """(label, stdin, klasse|''|'neg')"""
    out = []
    for cls, vals in NEU_POS.items():
        for i, v in enumerate(vals):
            out.append((f"Write {cls} #{i}", json.dumps({"tool_name": "Write", "tool_input": {
                "file_path": "/tmp/s12_notes.md", "content": "wert = '" + v + "'\n"}}), cls))
        out.append((f"Bash {cls}", json.dumps({"tool_name": "Bash", "tool_input": {
            "command": "echo '" + vals[0] + "' > /dev/null"}}), cls))
        out.append((f"Edit {cls}", json.dumps({"tool_name": "Edit", "tool_input": {
            "file_path": "/tmp/s12_app.py", "old_string": "x = None",
            "new_string": "x = '" + vals[0] + "'"}}), cls))
        out.append((f"MultiEdit {cls}", json.dumps({"tool_name": "MultiEdit", "tool_input": {
            "file_path": "/tmp/s12_app.py", "edits": [
                {"old_string": "a", "new_string": "b = 1  # harmlos"},
                {"old_string": "c", "new_string": "k = '" + vals[0] + "'"}]}}), cls))
        out.append((f"Edit Redaktion {cls} (nur old_string)", json.dumps({"tool_name": "Edit", "tool_input": {
            "file_path": "/tmp/s12_app.py", "old_string": "x = '" + vals[0] + "'",
            "new_string": "x = get_env('X')  # [REDACTED]"}}), "neg"))
        out.append((f"Write .bak-Pfad {cls}", json.dumps({"tool_name": "Write", "tool_input": {
            "file_path": "/tmp/s12.json.bak.pre-e1.1792500000", "content": "k = '" + vals[0] + "'\n"}}), "neg"))
    for cls, v in ALT_POS.items():
        out.append((f"Write alt {cls}", json.dumps({"tool_name": "Write", "tool_input": {
            "file_path": "/tmp/s12_alt.py", "content": "k = '" + v + "'\n"}}), cls))
    out.append(("Write alt+neu gemischt", json.dumps({"tool_name": "Write", "tool_input": {
        "file_path": "/tmp/s12_mix.py",
        "content": ALT_POS["AWS Access Key ID"] + "\n" + NEU_POS["Hugging Face Token"][0] + "\n"}}),
        "AWS Access Key ID|Hugging Face Token"))
    for i, t in enumerate(NEG):
        out.append((f"Write neg #{i}", json.dumps({"tool_name": "Write", "tool_input": {
            "file_path": "/tmp/s12_doc.md", "content": t}}), "neg"))
        out.append((f"Bash neg #{i}", json.dumps({"tool_name": "Bash", "tool_input": {
            "command": "printf '%s' " + json.dumps(t)}}), "neg"))
    out.append(("Read mit Wert (unbewacht)", json.dumps({"tool_name": "Read", "tool_input": {
        "file_path": "/tmp/" + NEU_POS["Hugging Face Token"][0]}}), "neg"))
    out.append(("kurz", json.dumps({"tool_name": "Write", "tool_input": {"file_path": "/tmp/x", "content": "kurz"}}), "neg"))
    out.append(("leerer tool_input", json.dumps({"tool_name": "Write", "tool_input": {}}), "neg"))
    out.append(("kaputtes JSON", "{kaputt::: kein json", "neg"))
    out.append(("leeres stdin", "", "neg"))
    return out


def detector_payloads() -> list[tuple[str, str, str]]:
    out = []
    for cls, vals in NEU_POS.items():
        for i, v in enumerate(vals):
            out.append((f"Prompt {cls} #{i}", json.dumps({"prompt": "Hier ist der Wert: " + v + " bitte eintragen"}), cls))
    for cls, v in ALT_POS.items():
        out.append((f"Prompt alt {cls}", json.dumps({"prompt": "Mein Key ist " + v + " danke"}), cls))
    for i, t in enumerate(NEG):
        out.append((f"Prompt neg #{i}", json.dumps({"prompt": t}), "neg"))
    out.append(("Prompt kurz", json.dumps({"prompt": "ok danke"}), "neg"))
    out.append(("Prompt kaputtes JSON", "{kaputt", "neg"))
    return out


def make_home(root: Path, name: str, hooks_src: dict[str, Path], json_src: Path | None,
              json_text: str | None = None, flag: bool = False) -> Path:
    home = root / name
    (home / ".claude" / "hooks").mkdir(parents=True)
    (home / ".claude" / "scripts").mkdir(parents=True)
    (home / ".claude" / "flags").mkdir(parents=True)
    for hook, src in hooks_src.items():
        shutil.copy2(src, home / ".claude" / "hooks" / hook)
    target = home / ".claude" / "scripts" / "secret_patterns.json"
    if json_text is not None:
        target.write_text(json_text, encoding="utf-8")
    elif json_src is not None:
        shutil.copy2(json_src, target)
    if flag:
        (home / ".claude" / "flags" / "secret_patterns_neu.on").touch()
    return home


def run(home: Path, hook: str, stdin: str) -> tuple[int, str, str]:
    env = {"HOME": str(home), "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8"}
    p = subprocess.run([sys.executable, str(home / ".claude" / "hooks" / hook)], input=stdin,
                       capture_output=True, text=True, timeout=20, env=env)
    return p.returncode, p.stdout, p.stderr


def log_lines(home: Path) -> list[str]:
    f = home / ".claude" / "lessons" / "leaks.jsonl"
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
            d.pop("timestamp", None)
            out.append(json.dumps(d, sort_keys=True, ensure_ascii=False))
        except ValueError:
            out.append("<unlesbar>")
    return out


def guard_verdict(rc: int, out: str) -> tuple[str, str]:
    if rc != 0:
        return f"exit{rc}", ""
    out = out.strip()
    if not out:
        return "allow", ""
    try:
        hso = json.loads(out).get("hookSpecificOutput", {})
        if hso.get("permissionDecision") == "deny":
            return "deny", hso.get("permissionDecisionReason", "")
    except ValueError:
        return "badout", ""
    return "allow", ""


def main() -> int:
    ts = None
    if "--baseline-ts" in sys.argv:
        ts = sys.argv[sys.argv.index("--baseline-ts") + 1]
    def bak(p: Path) -> Path:
        if ts:
            return Path(f"{p}.bak.pre-e1.{ts}")
        cands = sorted(glob.glob(f"{p}.bak.pre-e1.*"))
        if not cands:
            raise SystemExit(f"keine Baseline fuer {p.name} (.bak.pre-e1.*)")
        return Path(cands[0])  # aeltestes = Stand vor E1

    json_now = REAL / "scripts" / "secret_patterns.json"
    old_hooks = {h: bak(REAL / "hooks" / h) for h in HOOKS}
    new_hooks = {h: REAL / "hooks" / h for h in HOOKS}
    old_json = bak(json_now)
    print(f"Baseline: {old_json.name.split('.bak.')[1]} | Hooks {', '.join(p.name for p in old_hooks.values())}")

    fails: list[str] = []
    n = 0
    root = Path(tempfile.mkdtemp(prefix="s12test_"))
    try:
        corpora = {"secret_write_guard.py": guard_payloads(), "secret_leak_detector.py": detector_payloads()}

        # --- A: ohne Flag bytegleich (normale JSON, kaputte JSON, fehlende JSON) ---
        variants = [("JSON normal", None), ("JSON kaputt", "{kaputt"), ("JSON fehlt", "")]
        for vlabel, jtext in variants:
            for hook, corpus in corpora.items():
                h_old = make_home(root, f"A_old_{hook}_{vlabel.replace(' ', '_')}", old_hooks, old_json, jtext)
                h_new = make_home(root, f"A_new_{hook}_{vlabel.replace(' ', '_')}", new_hooks, json_now, jtext)
                if jtext == "":
                    (h_old / ".claude/scripts/secret_patterns.json").unlink()
                    (h_new / ".claude/scripts/secret_patterns.json").unlink()
                same = 0
                for label, stdin, _cls in corpus:
                    n += 1
                    if run(h_old, hook, stdin) == run(h_new, hook, stdin):
                        same += 1
                    else:
                        fails.append(f"A {vlabel} {hook}: {label} nicht bytegleich")
                n += 1
                if log_lines(h_old) == log_lines(h_new):
                    same += 1
                else:
                    fails.append(f"A {vlabel} {hook}: leaks.jsonl abweichend")
                print(f"A ohne Flag | {vlabel:11s} | {hook:24s} | bytegleich {same}/{len(corpus) + 1}")

        # --- B: mit Flag ---
        hB = make_home(root, "B_flag", new_hooks, json_now, flag=True)
        hB_noflag = make_home(root, "B_noflag", new_hooks, json_now, flag=False)
        okB = 0
        totB = 0
        for label, stdin, cls in corpora["secret_write_guard.py"]:
            totB += 1
            verdict, reason = guard_verdict(*run(hB, "secret_write_guard.py", stdin)[:2])
            want = "allow" if cls == "neg" else "deny"
            good = verdict == want
            if good and want == "deny":
                good = reason.startswith(A12_START) and all(c in reason for c in cls.split("|"))
            if good:
                okB += 1
            else:
                fails.append(f"B Guard mit Flag: {label} -> {verdict}")
            # Gegenprobe ohne Flag: neue Klassen bleiben unerkannt, alte mit altem Text
            if cls in NEU_POS:
                totB += 1
                v2, r2 = guard_verdict(*run(hB_noflag, "secret_write_guard.py", stdin)[:2])
                if v2 == "allow":
                    okB += 1
                else:
                    fails.append(f"B Guard ohne Flag: {label} -> {v2} (soll allow)")
            elif cls in ALT_POS:
                totB += 1
                v2, r2 = guard_verdict(*run(hB_noflag, "secret_write_guard.py", stdin)[:2])
                if v2 == "deny" and r2.startswith(ALT_START):
                    okB += 1
                else:
                    fails.append(f"B Guard ohne Flag: {label} -> {v2}")
        for label, stdin, cls in corpora["secret_leak_detector.py"]:
            totB += 1
            rc, out, _err = run(hB, "secret_leak_detector.py", stdin)
            if cls == "neg":
                good = rc == 0 and not out.strip()
            else:
                try:
                    msg = json.loads(out).get("systemMessage", "")
                except ValueError:
                    msg = ""
                good = rc == 0 and f"  - {cls}:" in msg
            if good:
                okB += 1
            else:
                fails.append(f"B Detector mit Flag: {label}")
        print(f"B mit Flag  | Testsatz Guard+Detector inkl. Gegenprobe ohne Flag: {okB}/{totB}")
        n += totB

        # --- C: Flag an, JSON ohne patterns_neu bzw. kaputt -> Ersatzlisten ---
        base_only = json.loads(old_json.read_text(encoding="utf-8"))
        for clabel, jtext in [("ohne patterns_neu", json.dumps(base_only)), ("kaputt", "{kaputt")]:
            hC = make_home(root, f"C_{clabel.replace(' ', '_')}", new_hooks, None, jtext, flag=True)
            okC = 0
            totC = 0
            for cls, vals in NEU_POS.items():
                for v in vals:
                    totC += 2
                    verdict, _r = guard_verdict(*run(hC, "secret_write_guard.py", json.dumps(
                        {"tool_name": "Write", "tool_input": {"file_path": "/tmp/c.md", "content": "w = " + v}}))[:2])
                    okC += verdict == "deny"
                    rc, out, _e = run(hC, "secret_leak_detector.py", json.dumps({"prompt": "Wert: " + v + " ende"}))
                    okC += (f"  - {cls}:" in out)
            totC += 1
            verdict, _r = guard_verdict(*run(hC, "secret_write_guard.py", json.dumps(
                {"tool_name": "Write", "tool_input": {"file_path": "/tmp/c.md", "content": "k = " + ALT_POS["Slack Token"]}}))[:2])
            okC += verdict == "deny"
            print(f"C Ersatzliste ({clabel:17s}) | {okC}/{totC}")
            n += totC
            if okC != totC:
                fails.append(f"C Ersatzliste {clabel}: {totC - okC} Fehler")

        # --- D: Log-Hygiene ---
        vals = all_values()
        dirty = 0
        for f in root.glob("*/.claude/lessons/leaks.jsonl"):
            text = f.read_text(encoding="utf-8")
            for v in vals:
                core = v[-16:]
                if core in text:
                    dirty += 1
        n += 1
        print(f"D Log-Hygiene | Dummy-Werte in Sandbox-Logs: {dirty}")
        if dirty:
            fails.append(f"D {dirty} Dummy-Werte in Logs")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print(f"\nPruefungen: {n}, Fehler: {len(fails)}")
    for f in fails:
        print("FAIL", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
