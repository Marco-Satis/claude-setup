#!/usr/bin/env bash
# skill_trigger_eval.sh — Trigger-Eval fuer eine Skill-Description (A3.7, der Nutzer-Ja 2026-10-18).
#
# Nutzt run_eval.py aus Anthropics skill-creator (installierter Marketplace, nicht kopiert) und
# schirmt dessen `claude -p`-Aufrufe ab:
#   --no-session-persistence           sonst bleibt pro Query und Wiederholung ein Transkript liegen
#   --settings {"disableAllHooks":true} sonst schreiben unsere Hooks Turn-Deltas in mcp-memory
# Laeuft in einem Wegwerf-Projektordner, damit run_eval.py seine Temp-Commands nicht ins echte
# Projekt legt.
#
#   skill_trigger_eval.sh <eval_set.json> <skill-dir> [weitere run_eval.py-Optionen]
#
# eval_set.json: [{"query": "...", "should_trigger": true}, ...]
# Grenze: Ist der Skill schon installiert, konkurriert das Original mit der Test-Kopie und kann
# Treffer "stehlen" (falsch-negativ). Neue Skills deshalb VOR der Installation testen.
set -euo pipefail
[ $# -ge 2 ] || { echo "Aufruf: $0 <eval_set.json> <skill-dir> [optionen]" >&2; exit 2; }
EVAL=$(readlink -f "$1"); SKILL=$(readlink -f "$2"); shift 2
SC="$HOME/.claude/plugins/marketplaces/anthropic-agent-skills/skills/skill-creator"
[ -f "$SC/scripts/run_eval.py" ] || { echo "skill-creator-Marketplace fehlt: $SC" >&2; exit 1; }
REAL=$(command -v claude)

WORK=$(mktemp -d "${TMPDIR:-/tmp}/skill_eval.XXXXXX")
# claude legt auch ohne Persistenz einen leeren Projektordner an; rmdir entfernt ihn nur, wenn leer
SLUG="$HOME/.claude/projects/$(printf '%s' "$WORK/proj" | tr '/._' '---')"
trap 'rm -rf -- "$WORK"; rmdir -- "$SLUG/memory" "$SLUG" 2>/dev/null || true' EXIT
mkdir -p "$WORK/bin" "$WORK/proj/.claude"
cat > "$WORK/bin/claude" <<EOF
#!/usr/bin/env bash
exec "$REAL" "\$@" --no-session-persistence --settings '{"disableAllHooks":true}'
EOF
chmod +x "$WORK/bin/claude"

# run_eval.py startet per Default 10 Worker, die alle ihren Test-Command (<name>-skill-<uuid>) in
# DENSELBEN Ordner legen. Claude sieht dann mehrere gleich beschriebene Skills und waehlt oft die ID
# eines anderen Laufs -> als "nicht ausgeloest" gezaehlt (gemessen 20.10. an site-anatomy: parallel
# 1/9 bzw. 0/9 Soll-Treffer, seriell 8/9 bei gleicher Description).
# Zweite Grenze: Gezaehlt wird nur der ERSTE Tool-Aufruf. Sammelt Claude erst Kontext (Bash/Grep)
# und ruft den Skill danach auf, zaehlt das als Fehlschlag -> Fehlschlaege einzeln nachproben.
# Deshalb seriell, ausser der Aufrufer setzt --num-workers ausdruecklich.
case " $* " in *" --num-workers "*) ;; *) set -- "$@" --num-workers 1 ;; esac

cd "$WORK/proj"
PATH="$WORK/bin:$PATH" PYTHONPATH="$SC" python3 -m scripts.run_eval \
  --eval-set "$EVAL" --skill-path "$SKILL" "$@"
