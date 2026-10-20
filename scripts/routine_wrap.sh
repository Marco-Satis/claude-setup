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
FINDINGS_OK=0
while [ $# -gt 0 ]; do
    case "${1:-}" in
        --quiet-ok)    QUIET_OK=1; shift ;;
        --findings-ok) FINDINGS_OK=1; shift ;;
        --)            shift; break ;;
        *)             break ;;
    esac
done

# Cron-Token laden, falls vorhanden (2026-08-20).
#
# Warum hier und nicht global: In der Auth-Nacht vom 20.08. fielen mit dem
# abgelaufenen RC-Login auch die Cron-Routinen aus, die intern `claude -p` rufen
# (weekly_tool_scout, weekly_hook_suggest, die n8n-Pipeline) — still, ohne Alarm.
# Sie brauchen den full-scope RC-Token gar nicht; Inferenz ist ihr ganzer Bedarf.
# Ein eigener langlebiger Token (`claude setup-token`, Scope user:inference)
# entkoppelt sie davon.
#
# Die Variable darf NIEMALS global gesetzt werden: Remote Control wuerde sie
# adoptieren und wegen zu kleinem Scope verweigern ("Remote Control requires a
# full-scope login token"). Deshalb steht sie hier, im Wrapper, den ausschliesslich
# Cron-Routinen aufrufen — und nur fuer die Dauer des jeweiligen Laufs.
if [ -r "$HOME/.claude/secrets/cron_token.env" ]; then
    # shellcheck disable=SC1091
    . "$HOME/.claude/secrets/cron_token.env"
    export CLAUDE_CODE_OAUTH_TOKEN
fi

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

# Exit-Code-Deutung (2026-08-18): Nicht jedes "Exit 1" ist ein Absturz. Mehrere
# Routinen nutzen Exit 1 als "ich habe etwas GEFUNDEN" — pipeline_selfcheck
# (`return 1 if problems else 0`) und hook_health_check (`return 1 if failures`).
# Die erste Fassung stufte beide als FAIL ein und schrieb "Routine hat ihre
# Aufgabe nicht erledigt" — das Gegenteil war der Fall: sie hat ihre Aufgabe
# erledigt und berichtet. Zwei Fehlalarme an einem Morgen, beide kosteten
# Nachforschung. Mit --findings-ok wird Exit 1 als Befund (WARN) gewertet,
# jeder andere Exit-Code bleibt FAIL.
STATUS="OK"
if [ "$RC" -ne 0 ]; then
    if [ "$FINDINGS_OK" -eq 1 ] && [ "$RC" -eq 1 ]; then
        STATUS="WARN"
    else
        STATUS="FAIL"
    fi
fi
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
        if [ "$RC" -ne 0 ] && [ "$STATUS" = "FAIL" ]; then
        echo "- Lauf endete mit Exit $RC — Ursache pruefen, Routine hat ihre Aufgabe nicht erledigt"
    elif [ "$RC" -eq 1 ] && [ "$FINDINGS_OK" -eq 1 ]; then
        echo "- Routine meldet einen Befund (Exit 1) — sie lief korrekt, hat aber etwas gefunden (siehe Ausgabe)"
    fi
        [ "$STATUS" = "WARN" ] && echo "- Ausgabe enthaelt Fehler-/Warnhinweise (siehe oben) — pruefen ob folgenreich"
    fi
} | ROUTINE_PLAN="$PLAN" "$HOME/.claude/scripts/routine_md.sh" "$NAME" "$STATUS"

exit "$RC"
