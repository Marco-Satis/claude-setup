#!/usr/bin/env bash
# routine_wrap.sh — beliebige Routine ausfuehren und dabei den Projekt-Report schreiben.
# Konvention seit 2026-08-14 (rules/routine-reports.md).
#
# Warum ein Wrapper statt Edits in jedem Skript: die sieben Bestandsroutinen sind
# Python und Bash, teils produktiv und fremd gepflegt (n8n_stack). Ein Wrapper auf
# Cron-Ebene laesst sie unangetastet, gilt einheitlich und ist in einer Zeile wieder
# entfernbar.
#
# Aufruf:
#   routine_wrap.sh <name> "<plan>" [--quiet-ok] -- <befehl...>
#
#   --quiet-ok   Report NUR schreiben, wenn etwas passiert ist (Exit != 0 oder
#                Ausgabe nicht leer). Fuer haeufige event-only-Routinen — sonst
#                erzeugt eine 5-Minuten-Routine 288 Reports pro Tag.
#
# Die Ausgabe des Befehls wird unveraendert durchgereicht, damit bestehende
# `>> logfile 2>&1`-Umleitungen in der crontab weiter funktionieren.
set -uo pipefail

NAME="${1:?name fehlt}"; shift
PLAN="${1:?plan fehlt}"; shift
QUIET_OK=0
[ "${1:-}" = "--quiet-ok" ] && { QUIET_OK=1; shift; }
[ "${1:-}" = "--" ] && shift

TMP="$(mktemp -t routine_wrap.XXXXXX)" || exec "$@"
START="$(date +%s)"

# Ausgabe gleichzeitig durchreichen (fuer die cron-Umleitung) und mitschneiden.
"$@" > >(tee "$TMP") 2>&1
RC=$?
wait
DUR=$(( $(date +%s) - START ))

OUT="$(cat "$TMP" 2>/dev/null)"
rm -f "$TMP"

if [ "$QUIET_OK" -eq 1 ] && [ "$RC" -eq 0 ] && [ -z "${OUT// }" ]; then
    exit "$RC"      # nichts passiert, kein Report — genau der Sinn von --quiet-ok
fi

STATUS="OK"
[ "$RC" -ne 0 ] && STATUS="FAIL"
# 2026-08-15: Die erste Fassung matchte blank auf "failed" — und stufte damit die
# voellig gesunde Zeile "n8n decision=apply (cur=2.34.5 latest=2.34.6 failed=None)"
# als WARN ein. Ein Fehlalarm pro Tag entwertet die Meldung schneller als gar keine.
# Deshalb: Negativ-Formen vorher entfernen, dann erst suchen. Und nur echte
# Log-Level-Marker bzw. Wortformen zaehlen, keine Teilwoerter.
OUT_SCAN="$(printf '%s' "$OUT" | sed -E 's/(failed|failures|errors)[=:][[:space:]]*(None|none|0|\[\])//g')"
if [ "$STATUS" = "OK" ] && printf '%s' "$OUT_SCAN" \
   | grep -qE "(^|[^A-Za-z])(ERROR|CRITICAL|Traceback|FAILED|Fehler|failed to|error:)([^A-Za-z]|$)"; then
    STATUS="WARN"
fi

{
    echo "## Was lief"
    echo "- Befehl: \`$(printf '%s ' "$@" | sed "s|$HOME|~|g" | cut -c1-160)\`"
    echo "- Exit-Code: $RC  ·  Dauer: ${DUR}s"
    if [ -n "${OUT// }" ]; then
        echo
        echo "## Ausgabe (letzte 15 Zeilen)"
        echo '```'
        printf '%s\n' "$OUT" | tail -15
        echo '```'
    else
        echo "- keine Ausgabe (bei event-only-Routinen der Normalfall)"
    fi
    if [ "$RC" -ne 0 ] || [ "$STATUS" = "WARN" ]; then
        echo
        echo "## BRAUCHT"
        [ "$RC" -ne 0 ] && echo "- Lauf endete mit Exit $RC — Ursache pruefen, Routine hat ihre Aufgabe nicht erledigt"
        [ "$STATUS" = "WARN" ] && echo "- Ausgabe enthaelt Fehler-/Warnhinweise (siehe oben) — pruefen ob folgenreich"
    fi
} | ROUTINE_PLAN="$PLAN" "$HOME/.claude/scripts/routine_md.sh" "$NAME" "$STATUS"

exit "$RC"
