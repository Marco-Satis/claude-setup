#!/usr/bin/env python3
"""Tests fuer hooks/auto_backup.py (14.11.2026). Exit 0 = alles gruen.

Alles in einem Wegwerf-Ordner (AUTO_BACKUP_ROOTS zeigt dorthin, Temp-Ausschluss per
AUTO_BACKUP_TEMPDIRS abgeschaltet). Prueft zusaetzlich, dass backup_prune.py das Muster erfasst.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(os.path.dirname(HERE), "auto_backup.py")
PRUNE_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts")
T0 = 1794600000


def run(root, payload, now=T0, raw=None, extra_env=None):
    env = dict(os.environ, AUTO_BACKUP_ROOTS=root, AUTO_BACKUP_TEMPDIRS="", AUTO_BACKUP_JETZT=str(now),
               AUTO_BACKUP_LOG=os.path.join(root, "auto_backup.log"))
    env.update(extra_env or {})
    p = subprocess.run([sys.executable, HOOK], input=raw if raw is not None else json.dumps(payload),
                       capture_output=True, text=True, timeout=15, env=env)
    return p.returncode, p.stdout


def baks(path):
    d = os.path.dirname(path)
    return sorted(f for f in os.listdir(d) if f.startswith(os.path.basename(path) + ".bak.auto."))


def edit(path, tool="Edit", **kw):
    return dict({"hook_event_name": "PreToolUse", "tool_name": tool,
                 "tool_input": {"file_path": path, "old_string": "a", "new_string": "b"}}, **kw)


def main():
    fails, total = 0, 0

    def check(name, cond):
        nonlocal fails, total
        total += 1
        if not cond:
            fails += 1
        print(f"{'ok  ' if cond else 'FAIL'} {name}")

    with tempfile.TemporaryDirectory() as root:
        f = os.path.join(root, "proj", "notiz.md")
        os.makedirs(os.path.dirname(f))
        open(f, "w").write("x")
        rc, out = run(root, edit(f))
        check("1. Edit ohne git -> Backup", rc == 0 and out == "" and baks(f) == [f"notiz.md.bak.auto.{T0}"])
        run(root, edit(f), T0 + 1800)
        check("2. innerhalb 1 h kein zweites", len(baks(f)) == 1)
        run(root, edit(f), T0 + 3700)
        check("3. nach > 1 h neues Backup", len(baks(f)) == 2)
        run(root, edit(f, tool="Write"), T0 + 8000)
        check("4. Write auf bestehende Datei", len(baks(f)) == 3)

        neu = os.path.join(root, "proj", "neu.md")
        run(root, edit(neu, tool="Write"))
        check("5. neue Datei -> nichts", not os.path.exists(neu) and not any("neu.md.bak" in x for x in os.listdir(os.path.dirname(neu))))

        sp = os.path.join(root, "scratch")
        os.makedirs(sp)
        s = os.path.join(sp, "t.txt")
        open(s, "w").write("x")
        run(root, edit(s, scratchpad_dir=sp))
        check("6. Scratchpad -> nichts", baks(s) == [])

        for name in (".env", "config/.env.local", "secrets/x.txt", "key.pem"):
            p = os.path.join(root, "proj", name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w").write("x")
            run(root, edit(p))
            check(f"7. Secret-Ort {name} -> nichts", baks(p) == [])

        for d in ("node_modules", "_archive_alt", ".venv"):
            p = os.path.join(root, "proj", d, "a.py")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w").write("x")
            run(root, edit(p))
            check(f"8. ausgelassener Ordner {d} -> nichts", baks(p) == [])

        with tempfile.TemporaryDirectory() as fremd:
            p = os.path.join(fremd, "a.txt")
            open(p, "w").write("x")
            run(root, edit(p))
            check("9. ausserhalb der Wurzeln -> nichts", baks(p) == [])

        repo = os.path.join(root, "repo")
        os.makedirs(repo)
        subprocess.run(["git", "init", "-q", repo], check=True)
        tr = os.path.join(repo, "tracked.py")
        un = os.path.join(repo, "untracked.py")
        open(tr, "w").write("x")
        open(un, "w").write("x")
        subprocess.run(["git", "-C", repo, "add", "tracked.py"], check=True)
        run(root, edit(tr))
        check("10. git-verfolgt -> nichts", baks(tr) == [])
        run(root, edit(un))
        check("11. im Repo, aber untracked -> Backup", len(baks(un)) == 1)

        rel = os.path.join("proj", "relativ.md")
        open(os.path.join(root, rel), "w").write("x")
        run(root, dict(edit(rel), cwd=root))
        check("12. relativer Pfad + cwd", len(baks(os.path.join(root, rel))) == 1)

        b = baks(f)[0]
        run(root, edit(os.path.join(root, "proj", b)))
        check("13. Backup-Datei selbst -> nichts", not any(x.startswith(b + ".bak") for x in os.listdir(os.path.join(root, "proj"))))

        for raw in ("", "{kaputt", "[]", "null", "{}", json.dumps({"tool_name": "Edit", "tool_input": {}})):
            check(f"14. robust {raw[:20]!r}", run(root, None, raw=raw)[0] == 0)

        # backup_prune erfasst das Muster (Gruppe = Originaldatei, Zeitstempel erkannt).
        # Seit 14.11.: ohne git schuetzt backup_prune manuelle .bak; .bak.auto folgen immer der Normalregel
        # (KEEP=2, 14 Tage), sonst wuechsen sie ohne git endlos.
        sys.path.insert(0, PRUNE_DIR)
        import backup_prune as bp
        bp.ROOTS = [root]
        gruppen = {}
        for pfad, original in bp.walk_backups():
            gruppen.setdefault(original, []).append(bp.TS_RE.findall(os.path.basename(pfad)))
        check("15. backup_prune: .bak.auto.<ts> wird erkannt und der Originaldatei zugeordnet",
              len(gruppen.get(f, [])) == 3 and all(ts for ts in gruppen[f]))
        for k in (1, 2):  # im git-Repo (untracked Datei) wird abgeraeumt: 3 Backups, KEEP=2
            open(f"{un}.bak.auto.{T0 + 4000 * k}", "w").close()
        weg, _, _, _ = bp.plan(now=T0 + 9000)
        check("16. backup_prune im git-Baum: aeltestes von 3 .bak.auto faellt (KEEP=2)",
              [os.path.basename(w) for w in weg if "untracked.py.bak.auto." in w] == [f"untracked.py.bak.auto.{T0}"])
        if hasattr(bp, "in_git"):
            weg2, _, _, _ = bp.plan(now=T0 + 15 * 86400 + 9000)
            check("17. backup_prune ohne git: .bak.auto aelter als 14 Tage werden trotzdem geloescht",
                  bool([w for w in weg2 if "notiz.md.bak.auto." in w]))
    print(f"auto_backup: {total - fails}/{total} ok")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
