#!/usr/bin/env python3
"""grep_complexity_guard.py — blockt das grep-Muster, das den Server lahmgelegt hat.

Vorfall 2026-08-17: ein `grep -oiE ".{0,90}Claude-for-OSS.{0,90}"` wuchs ueber
zehneinhalb Stunden auf 12,8 GiB und riss saemtliche RC-Sessions in die
cgroup-Drossel. Ein zweiter Lauf am selben Abend erreichte 8,7 GiB in 66
Sekunden.

WARUM DAS KEIN NORMALES grep IST: `grep` ist in dieser Shell eine Funktion, die
die Claude-Binary selbst aufruft (`exec -a ugrep "$CLAUDE_CODE_EXECPATH" …`) —
ein Multi-Call-Binary. Darin steckt ugrep 7.5.0. Dessen DFA-Konstruktion
uebersetzt `.` UTF-8-bewusst in eine Mehrbyte-Zeichenklasse; eine gebundene
Wiederholung `{0,N}` darauf explodiert. Die eingebaute Komplexitaetsgrenze
greift ERST NACH der Allokation — der Prozess belegt also zuerst Gigabytes und
meldet dann "exceeds complexity limits".

Gemessen (general-Session, gleiche Datei, gleicher Flagsatz):
    .{0,10}  19 ms      .{0,60}    750 ms
    .{0,30}  54 ms      .{0,70}  3.359 ms
    .{0,40}  79 ms      .{0,80} 15.029 ms  -> Abbruch
                        .{0,90} 19.833 ms  -> Kernel-Kill bei 3 GiB
GNU-grep erledigt `.{0,90}` mit demselben Muster in 117 ms.

Es kippt zwischen 70 und 80. Die Schwelle hier liegt bei 60 — mit Abstand, weil
mehrere solcher Gruppen im selben Muster sich multiplizieren statt zu addieren
(der Originalbefehl hatte zwei und kam nie bis zur Fehlermeldung).

Nicht blockiert werden: `command grep` und `/usr/bin/grep` (echtes GNU-grep),
`rg`, sowie Aufrufe mit `-P` (PCRE2-JIT statt DFA). Damit bleibt fuer jeden
legitimen Fall ein Weg offen — der Hook nimmt nichts weg, er lenkt um.

Best-effort: jeder Fehler -> Exit 0, niemals ein Kommando wegen eines Defekts
in dieser Datei blockieren.
"""
import json
import re
import sys

# Gebundene Wiederholung auf einem Punkt: .{0,90} / .{5,90} / .{,90}
BOUNDED_DOT = re.compile(r"\.\s*\{\s*\d*\s*,\s*(\d+)\s*\}")
LIMIT = 60

# Aufrufe, die NICHT durch die Shell-Funktion laufen bzw. eine andere Engine nutzen.
SAFE = (
    re.compile(r"\bcommand\s+grep\b"),
    re.compile(r"(^|\s)/(usr/)?bin/grep\b"),
    re.compile(r"\bgrep\b[^|;&]*\s-\w*P"),   # -P => PCRE2-JIT
    re.compile(r"\brg\b"),
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command", "")
    if not cmd or "grep" not in cmd:
        return 0
    if any(p.search(cmd) for p in SAFE):
        return 0

    worst = 0
    for m in BOUNDED_DOT.finditer(cmd):
        try:
            worst = max(worst, int(m.group(1)))
        except ValueError:
            continue
    if worst <= LIMIT:
        return 0

    print(
        f"BLOCKIERT: `grep` mit `.{{0,{worst}}}` — das ist das Muster, das am 2026-08-17\n"
        f"den Server lahmgelegt hat (12,8 GiB, 10,5 h, alle RC-Sessions eingefroren).\n"
        f"\n"
        f"`grep` ist hier nicht GNU-grep, sondern das eingebettete ugrep 7.5.0. Bei einer\n"
        f"gebundenen Wiederholung auf `.` jenseits von ~70 explodiert dessen Automaten-\n"
        f"Konstruktion, und die Komplexitaetsgrenze greift erst NACH der Allokation.\n"
        f"\n"
        f"Wähle einen dieser Wege — alle drei liefern dasselbe Ergebnis in Millisekunden:\n"
        f"  command grep …    echtes GNU-grep (117 ms fuer genau dieses Muster)\n"
        f"  grep -P …         PCRE2 statt DFA\n"
        f"  rg …              ripgrep\n"
        f"Oder die Spanne unter {LIMIT} druecken, falls sie ohnehin zu weit gefasst war.",
        file=sys.stderr,
    )
    return 2   # PreToolUse: 2 = blockieren, stderr geht an Claude


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # best-effort
        print(f"grep_complexity_guard: uebersprungen ({exc.__class__.__name__})", file=sys.stderr)
        sys.exit(0)
