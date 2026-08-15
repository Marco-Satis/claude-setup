#!/usr/bin/env bash
# RC-Watchdog: erkennt haengende/crash-loopende claude-rc-*-Hosts und ALARMIERT.
# Heilt bewusst NICHT selbst — der haeufigste Grund ist ein toter OAuth-Token, und
# /login ist zwingend interaktiv. Zweck: Ausfall in Minuten statt Stunden sichtbar.
# Incident 2026-07-23: 2h46 stille Downtime, 13910 Fehlerzeilen, niemand hat's gemerkt.
#
# Eskalation (P3, 2026-08-14, der Nutzer-Entscheid: E-Mail): Incident 14.08. — Discord-
# Meldungen um 04:40 + 05:10 kamen an, wurden aber nicht bemerkt; Loop lief bis 07:05
# (453 Restarts). Deshalb zweite Stufe: haelt "bad" ueber ESCALATE_AFTER Checks an
# ODER crash-loopt ein Host mit NRestarts >= NRESTART_LOUD, geht zusaetzlich eine
# E-Mail raus (rc-mail.sh, eigener Kanal — Discord koennte ja selbst der Ausfall sein).
set -uo pipefail
NOTIFY="$HOME/.claude/rc-notify.sh"
MAIL="$HOME/.claude/rc-mail.sh"
LOG="$HOME/.claude/logs/rc-health.log"
LAST="$HOME/.claude/.rc-watchdog.last"
# Aktive RC-Hosts = die ENABLED Units, nicht eine Liste hier (2026-08-14).
# Wer eine Sitzung stilllegt (`rc-session.sh stop <name>` -> disable), soll sie
# nicht zusaetzlich aus zwei Skripten austragen muessen — sonst meldet der
# Watchdog sie als Ausfall und das Autoupdate startet sie beim naechsten
# Versionswechsel wieder. Zurueck kommt sie mit `enable`, ebenfalls ueberall.
HOSTS="$(systemctl --user list-unit-files 'claude-rc-*.service' --state=enabled --no-legend 2>/dev/null \
         | awk '{print $1}' | grep -v watchdog | tr '\n' ' ')"
[ -z "${HOSTS// /}" ] && HOSTS="claude-rc-general claude-rc-discord"   # Notnagel
REALERT=1800        # Discord: fruehestens alle 30 min erneut
ESCALATE_AFTER=3    # Checks im 5-min-Takt -> Mail nach ~15 min Dauer-bad
REMAIL=3600         # Mail: fruehestens jede Stunde erneut
NRESTART_LOUD=20    # dreistellige Loops nicht abwarten: ab 20 sofort Mail
mkdir -p "$(dirname "$LOG")"

bad=""
loud=""
for h in $HOSTS; do
  if [ "$(systemctl --user show "$h" -p SubState --value 2>/dev/null)" = "running" ]; then
    # laeuft — aber crash-loopt es? NRestarts bleibt ueber Loops hinweg hoch.
    nr="$(systemctl --user show "$h" -p NRestarts --value 2>/dev/null)"
    [ "${nr:-0}" -ge "$NRESTART_LOUD" ] 2>/dev/null && loud="$loud ${h#claude-rc-}(NRestarts=$nr)"
  else
    bad="$bad ${h#claude-rc-}"
    nr="$(systemctl --user show "$h" -p NRestarts --value 2>/dev/null)"
    [ "${nr:-0}" -ge "$NRESTART_LOUD" ] 2>/dev/null && loud="$loud ${h#claude-rc-}(NRestarts=$nr)"
  fi
done
authfails="$(journalctl --user -u 'claude-rc-*' --since "-6min" --no-pager 2>/dev/null | grep -c "must be logged in")"

now="$(date +%s)"
# State-Datei: "state ts badcount lastmail" — aeltere 2-Feld-Form liest sich mit Defaults.
prev_state="none"; prev_ts=0; badcount=0; lastmail=0
[ -r "$LAST" ] && read -r prev_state prev_ts badcount lastmail <"$LAST"
: "${prev_ts:=0}"; : "${badcount:=0}"; : "${lastmail:=0}"

if [ -n "$bad" ] || [ "$authfails" -gt 3 ] || [ -n "$loud" ]; then
  state="bad"
  badcount=$((badcount + 1))
  reason="nicht running:${bad:- -} | 'must be logged in' letzte 6min: $authfails${loud:+ | crash-loop:$loud}"

  # Stufe 1: Discord (wie bisher)
  if [ "$prev_state" != "bad" ] || [ $((now - prev_ts)) -ge "$REALERT" ]; then
    if [ "$authfails" -gt 3 ]; then
      "$NOTIFY" "RC-Hosts DOWN — Claude-Auth tot" \
        "$reason
Fix: ssh netcup -> 'claude' -> /login -> URL in CHROME (nicht Opera GX, PKCE-400). Danach heilen sich die Services selbst (Restart=always)."
    else
      "$NOTIFY" "RC-Hosts DOWN" "$reason
Pruefen: systemctl --user status claude-rc-<name> ; journalctl --user -u claude-rc-<name> -n 25"
    fi
    prev_ts="$now"
  fi

  # Stufe 2: E-Mail — bei Dauer-bad oder lauter Crash-Loop, gedrosselt auf REMAIL.
  if { [ "$badcount" -ge "$ESCALATE_AFTER" ] || [ -n "$loud" ]; } \
     && [ $((now - lastmail)) -ge "$REMAIL" ]; then
    # Seit 2026-08-14 kann der Nutzer vom Handy aus Befehle auf dem Server absetzen.
    # Die Mail traegt deshalb fertige Copy-Paste-Zeilen statt Diagnose-Prosa —
    # rc-fix-hints.sh bestimmt aus dem Journal die Symptomklasse je Host und
    # liefert genau die Befehle, die dazu passen.
    hints="$("$HOME/.claude/rc-fix-hints.sh" "$bad" "$loud" 2>/dev/null)"
    "$MAIL" "RC-Hosts DOWN seit ${badcount} Checks" \
      "$reason

Discord-Alarme liefen bereits (Stufe 1), das hier ist die Eskalation.

${hints:-Keine Fix-Hinweise ermittelbar — bitte manuell nachsehen:
  systemctl --user list-units 'claude-rc-*' --no-pager}"
    lastmail="$now"
  fi
  echo "$state $prev_ts $badcount $lastmail" >"$LAST"
else
  state="ok"
  if [ "$prev_state" = "bad" ]; then
    "$NOTIFY" "RC-Hosts wieder OK" "Alle 7 claude-rc-*-Services running, keine Auth-Fehler."
    # Entwarnung auch per Mail — aber nur, wenn vorher eine Mail rausging.
    [ "$lastmail" -gt 0 ] && "$MAIL" "RC-Hosts wieder OK" "Alle 7 claude-rc-*-Services running. Ausfall dauerte ca. $((badcount * 5)) min ($badcount Checks)."
  fi
  echo "$state $now 0 0" >"$LAST"
fi
exit 0
