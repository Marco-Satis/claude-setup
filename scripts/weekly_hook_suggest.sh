#!/usr/bin/env bash
# Woechentliche Hook-Vorschlags-Routine.
# Ersetzt das hookify-Plugin (Dauer-Analyse auf jedem Event) durch EINEN
# gebuendelten Lauf pro Woche: verdichtet die letzten 7 Tage zu einem Digest
# und laesst headless claude 0-5 konkrete Guardrail-Hooks vorschlagen.
# Best-effort, bricht die Cron nie hart ab. Nichts wird automatisch verdrahtet.
set -uo pipefail

CLA="$HOME/.local/bin/claude"
PY="/usr/bin/python3"
EXTRACT="$HOME/.claude/scripts/hook_suggest_extract.py"
LOG="$HOME/.claude/logs/weekly_hook_suggest.log"
OUTDIR="$HOME/projects/Skills_&_Co/HOOK_SUGGESTIONS"
DATE="$(date +%Y-%m-%d)"
REPORT="$OUTDIR/HOOK_SUGGESTIONS_$DATE.md"

mkdir -p "$OUTDIR" "$(dirname "$LOG")"
echo "[$(date -Is)] start" >> "$LOG"

DIGEST="$("$PY" "$EXTRACT" 2>>"$LOG")"
if [ -z "${DIGEST// }" ]; then
    echo "[$(date -Is)] leerer Digest — abgebrochen" >> "$LOG"
    exit 0
fi

INSTRUCTION="Du bist Hook-Vorschlags-Analyst fuer der Nutzer Claude-Code-Setup (Server 'netcup', Ubuntu). Der angehaengte Digest enthaelt secret-redigiert die Tool-Nutzung, Ablehnungen und Fehler der letzten 7 Tage aus seinen Sessions.

Aufgabe: Schlage 0-5 KONKRETE Guardrail-Hooks vor, die wiederkehrende Probleme verhindern oder Reibung reduzieren wuerden (z.B. ein PreToolUse-Guard gegen einen Befehl der wiederholt abgelehnt wurde, oder ein Reminder fuer ein oft wiederholtes Muster).

Regeln:
- NUR bei ECHTEM wiederkehrendem Muster vorschlagen. 'Keine Vorschlaege diese Woche' ist eine valide, gute Antwort — erfinde keine Muster.
- Schlage NICHTS vor, das ein bereits vorhandener Hook (Liste im Digest) schon abdeckt.
- Pro Vorschlag: Event (SessionStart/PreToolUse/PostToolUse/Stop/UserPromptSubmit) - Matcher (Tool) - Zweck (1 Satz) - Skizze (1 Satz, Stil von der Nutzer hook-create) - Evidenz (welche Digest-Zeile/Zahl).
- Kurz, Deutsch, kein Geschwafel."

PROMPT="$INSTRUCTION

=== DIGEST ===
$DIGEST"

# Primaer: headless Claude (beste Qualitaet). Fallback: lokales Modell (ollama, quota-frei/offline),
# falls Claude nicht erreichbar oder leer (Cloud down, rate-limited, auth abgelaufen).
ENGINE="claude"
# --no-session-persistence (2026-08-13): ohne den Flag hinterlaesst jeder headless-Lauf
# ein persistentes Transcript-jsonl — woechentlich eins, das nie jemand liest. Dieselbe
# Lehre wie in der n8n-Pipeline (Memory `n8n-claude-p-transcript-bloat`, dort 2310 Dateien
# / 123 MB, bevor es auffiel).
RESULT="$("$CLA" -p "$PROMPT" --no-session-persistence 2>>"$LOG")"
if [ -z "${RESULT// }" ]; then
    echo "[$(date -Is)] claude -p leer/fehlgeschlagen -> lokaler Fallback (ollama qwen2.5:7b)" >> "$LOG"
    ENGINE="lokales Modell (qwen2.5:7b, Offline-Fallback)"
    RESULT="$(printf '%s' "$DIGEST" | "$PY" "$HOME/.claude/scripts/ollama_call.py" --mode fallback --model qwen2.5:7b --max-tokens 900 --label weekly_hook_suggest -- "$INSTRUCTION" 2>>"$LOG")"
fi
[ -z "${RESULT// }" ] && RESULT="_(weder Claude noch lokales Modell lieferten ein Ergebnis — siehe Log)_"

{
    echo "# Hook-Vorschlaege — Woche $DATE"
    echo ""
    echo "> Auto-generiert von weekly_hook_suggest.sh (ersetzt hookify). Engine: $ENGINE. Vorschlaege sind KANDIDATEN — mit /hook-create umsetzen; nichts wird automatisch verdrahtet."
    echo ""
    echo "$RESULT"
} > "$REPORT"

echo "[$(date -Is)] done -> $REPORT" >> "$LOG"
