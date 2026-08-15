#!/usr/bin/env bash
# routine_md.sh — Standard-Report einer Server-Routine ins Projekt schreiben.
# Konvention seit 2026-08-14 (der Nutzer): jede Routine auf dem Server hinterlaesst am
# Ende eine MD in ~/projects/Skills_&_Co/ROUTINE_REPORTS/, weil der Nutzer die Laeufe
# selbst nicht sieht. Claude liest sie zu Session-Beginn (routine_audit.py).
#
# Aufruf:   <body auf stdin> | routine_md.sh <name> <STATUS>
#   name    kurzer Routine-Name (wird Dateiname: <name>_<datum>.md)
#   STATUS  OK | WARN | FAIL
#
# Der Body ist freies Markdown. Enthaelt er einen Abschnitt `## BRAUCHT`, sammelt
# routine_audit.py dessen Zeilen ein und zeigt sie der Nutzer als Handlungsbedarf.
# Fehlt der Abschnitt, wird er automatisch mit "nichts" ergaenzt — so ist die
# Aussage "diese Routine braucht nichts" explizit statt bloss abwesend.
set -uo pipefail
NAME="${1:-unbenannt}"
STATUS="${2:-OK}"
DIR="$HOME/projects/Skills_&_Co/ROUTINE_REPORTS"
DATE="$(date +%Y-%m-%d)"
OUT="$DIR/${NAME}_${DATE}.md"

mkdir -p "$DIR" || exit 0   # best-effort: eine Routine darf nie am Report scheitern
BODY="$(cat)"

{
  echo "# ${NAME} — ${DATE} $(date +%H:%M)"
  echo
  echo "**Status:** ${STATUS}  ·  **Host:** $(hostname)  ·  **Plan:** ${ROUTINE_PLAN:-siehe crontab}"
  echo
  echo "$BODY"
  case "$BODY" in
    *"## BRAUCHT"*) : ;;
    *) printf '\n## BRAUCHT\n_(nichts — Routine lief eigenstaendig durch)_\n' ;;
  esac
} > "$OUT" 2>/dev/null || exit 0

exit 0
