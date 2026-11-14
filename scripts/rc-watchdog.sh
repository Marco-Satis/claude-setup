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
NRESTART_DELTA_LOUD=5   # Zuwachs pro 5-min-Check, ab dem es ein echter Loop ist
                        # (ein Ausfall bringt 170+/h, also ~14 je Check — 5 trennt sauber)
mkdir -p "$(dirname "$LOG")"

# NRestarts wird als ZUWACHS gewertet, nicht als Pegel (Fix 2026-08-20).
# Vorher stand hier `[ "$nr" -ge "$NRESTART_LOUD" ]` auf dem absoluten Wert. Der
# Zaehler faellt nach einem Ausfall aber nicht von selbst zurueck: nach der
# Auth-Nacht liefen alle vier Hosts wieder sauber, trugen aber NRestarts=422-424 —
# und der Watchdog meldete deshalb 33 Checks in Folge "crash-loop" fuer ein
# gesundes System, alle 30 Minuten nach Discord, stuendlich per Mail. Genau diese
# Dauermeldung sorgt dafuer, dass die echte Meldung im Ernstfall uebersehen wird.
# Gezaehlt wird jetzt, was seit dem letzten Lauf DAZUGEKOMMEN ist.
NRSTATE="$HOME/.claude/.rc-nrestarts.state"
declare -A PREV_NR=()
if [ -r "$NRSTATE" ]; then
  while read -r _h _n; do [ -n "${_h:-}" ] && PREV_NR["$_h"]="${_n:-0}"; done <"$NRSTATE"
fi

bad=""
loud=""
: >"$NRSTATE.tmp"
for h in $HOSTS; do
  nr="$(systemctl --user show "$h" -p NRestarts --value 2>/dev/null)"
  nr="${nr:-0}"
  echo "$h $nr" >>"$NRSTATE.tmp"
  prev="${PREV_NR[$h]:-}"
  # Erstlauf: kein Vorwert -> kein Zuwachs behaupten (sonst meldet die erste
  # Ausfuehrung nach einem Neustart den ganzen Verlauf als frischen Loop).
  if [ -n "$prev" ] && [ "$nr" -gt "$prev" ] 2>/dev/null; then
    delta=$((nr - prev))
    [ "$delta" -ge "$NRESTART_DELTA_LOUD" ] && loud="$loud ${h#claude-rc-}(+$delta Neustarts seit letztem Check, gesamt $nr)"
  fi
  [ "$(systemctl --user show "$h" -p SubState --value 2>/dev/null)" = "running" ] || bad="$bad ${h#claude-rc-}"
done
mv -f "$NRSTATE.tmp" "$NRSTATE" 2>/dev/null || true
authfails="$(journalctl --user -u 'claude-rc-*' --since "-6min" --no-pager 2>/dev/null | grep -c "must be logged in")"

# Haengende Sitzungen (2026-08-17): drei Hosts liefen stundenlang, ohne zu
# antworten. SubState sagte "running", NRestarts blieb 0, Restart=always griff
# nicht — der Prozess lebte ja. Die Schleife oben haette das nie gesehen.
# rc-liveness.py macht deshalb einen echten Handshake auf dem Session-Socket;
# ein Prozess im D-State nimmt dort keine Verbindung mehr an.
hung="$(python3 "$HOME/.claude/rc-liveness.py" 2>/dev/null)"

# --- Vorwaerts-Pruefung: laeuft das Refresh-Token bald ab? (2026-08-20) --------
# Alles oberhalb schaut RUECKWAERTS: tote Units, Crash-Loops, "must be logged in"
# der letzten 6 Minuten. Es meldet also erst, wenn der Ausfall schon da ist.
# In der Nacht auf den 20.08. hat genau das 2,5 Stunden und 356 Neustarts gekostet,
# obwohl der Ablaufzeitpunkt die ganze Zeit in ~/.claude/.credentials.json stand:
# refreshTokenExpiresAt = 2026-08-19 21:14:33, gesetzt beim Login am 23.07.
# Das Token laeuft nach rund 28 Tagen hart ab und verlaengert sich NICHT durch
# Benutzung. Ein Browser-Login ist unvermeidbar (RC verlangt full-scope), aber er
# soll zu einem Zeitpunkt stattfinden, den der Nutzer waehlt.
# Gelesen wird ausschliesslich der Zeitstempel — niemals ein Token-Wert.
TOKENWARN_DAYS=5
TOKENSTATE="$HOME/.claude/.rc-tokenwarn.last"
token_rest_days="$(python3 - <<'PY' 2>/dev/null
import json, time
from pathlib import Path
try:
    d = json.loads((Path.home() / ".claude" / ".credentials.json").read_text(encoding="utf-8"))
except Exception:
    raise SystemExit
exp = (d.get("claudeAiOauth") or {}).get("refreshTokenExpiresAt")
if not isinstance(exp, (int, float)) or exp <= 0:
    raise SystemExit
# Der Wert steht in Millisekunden.
print(f"{(exp / 1000 - time.time()) / 86400:.1f}")
PY
)"
if [ -n "${token_rest_days:-}" ]; then
  # Ganzzahliger Vergleich, damit auch ohne bc/awk verlaesslich.
  rest_int="${token_rest_days%%.*}"
  [ "$rest_int" = "-0" ] && rest_int=-1
  if [ "${rest_int:-99}" -le "$TOKENWARN_DAYS" ] 2>/dev/null; then
    lastwarn=0; [ -r "$TOKENSTATE" ] && read -r lastwarn <"$TOKENSTATE" 2>/dev/null
    : "${lastwarn:=0}"
    if [ $(( $(date +%s) - lastwarn )) -ge 86400 ]; then   # hoechstens einmal taeglich
      if [ "${rest_int:-99}" -lt 0 ]; then
        "$NOTIFY" "Claude-Login ABGELAUFEN" \
          "Das OAuth-Refresh-Token ist seit ${token_rest_days#-} Tagen abgelaufen. Jeder Neustart eines RC-Hosts scheitert ab sofort, und die 12 crontab-Jobs mit 'claude' fallen still mit.
Fix: ssh netcup -> 'claude auth login' -> URL in CHROME (nicht Opera GX, PKCE-400)."
      else
        "$NOTIFY" "Claude-Login laeuft in ${token_rest_days} Tagen ab" \
          "Danach scheitert jeder Neustart eines RC-Hosts, und die crontab-Jobs mit 'claude' fallen still mit (Vorfall 2026-08-20: 2,5 h, 356 Neustarts).
Jetzt in Ruhe erneuern: ssh netcup -> 'claude auth login' -> URL in CHROME (nicht Opera GX, PKCE-400)."
      fi
      date +%s >"$TOKENSTATE"
    fi
  fi
fi

# --- G252 1.13 (14.11.2026): Zentrale ueberwachen -------------------------------------------
# Laeuft vor dem Wartungsfenster-Zweig, damit es auch dort gilt. Jede Meldung hoechstens 1x je Stunde
# (Digest-Totmann 1x je Tag). ALARM ueber rc-notify (pusht sofort per ntfy), Totmann direkt per rc-mail.
ZDIR="${ZENTRALE_DIR:-$HOME/.claude/state/zentrale}"
mkdir -p "$ZDIR" 2>/dev/null && chmod 700 "$ZDIR" 2>/dev/null
z_now="$(date +%s)"
z_drossel() {   # z_drossel <name> <sekunden> -> 0 = jetzt melden (und merken), 1 = still
  local f="$ZDIR/watchdog_$1.last" last=0
  [ -r "$f" ] && read -r last <"$f" 2>/dev/null
  [[ "${last:-0}" =~ ^[0-9]+$ ]] || last=0
  [ $((z_now - last)) -ge "$2" ] || return 1
  echo "$z_now" >"$f"; return 0
}
# (a) Digest-Totmann: letzter erfolgreicher Digest aelter als 26 h. Fehlt die Datei, startet die Uhr jetzt.
if [ ! -e "$ZDIR/digest_letzter" ]; then
  echo "$z_now" >"$ZDIR/digest_letzter"
else
  read -r z_dig <"$ZDIR/digest_letzter" 2>/dev/null
  if [[ "${z_dig:-}" =~ ^[0-9]+$ ]] && [ $((z_now - z_dig)) -gt 93600 ] && z_drossel digest_totmann 86400; then
    "$MAIL" "Digest ausgeblieben" "Der 07:45-Digest kam seit $(( (z_now - z_dig) / 3600 )) h nicht an. Kompass-Report und Log beim Setup Server pruefen."
  fi
fi
# (b) neue Zeilen in den Fehlerdateien des Eingangs (Phase 2: freigabe_eingang.err)
for z_err in "$HOME/.claude/logs/zentrale_eingang.err" "$HOME/.claude/logs/freigabe_eingang.err"; do
  z_key="$(basename "$z_err" .err)"
  z_size=0; [ -r "$z_err" ] && z_size="$(stat -c %s "$z_err" 2>/dev/null || echo 0)"
  z_prev=""; [ -r "$ZDIR/watchdog_${z_key}.size" ] && read -r z_prev <"$ZDIR/watchdog_${z_key}.size"
  echo "$z_size" >"$ZDIR/watchdog_${z_key}.size"
  if [[ "${z_prev:-}" =~ ^[0-9]+$ ]] && [ "$z_size" -gt "$z_prev" ] && z_drossel "err_$z_key" 3600; then
    "$NOTIFY" "Zentrale: Eingang gestoert" "Neue Zeilen in $(basename "$z_err") (+$((z_size - z_prev)) Bytes)." ALARM
  fi
done
# (c) Plattenplatz unter ~/.claude/state (< 200 MB frei)
z_frei_kb="$(df -Pk "$HOME/.claude/state" 2>/dev/null | awk 'NR==2 {print $4}')"
if [[ "${z_frei_kb:-}" =~ ^[0-9]+$ ]] && [ "$z_frei_kb" -lt 204800 ] && z_drossel platz 3600; then
  "$NOTIFY" "Zentrale: wenig Platz" "Unter ~/.claude/state sind nur noch $((z_frei_kb / 1024)) MB frei." ALARM
fi
# (d) Eingangs-Lock: wird gehalten und die Info-Datei ist aelter als 60 s
if [ -e "$ZDIR/eingang.lock.info" ] && [ $((z_now - $(stat -c %Y "$ZDIR/eingang.lock.info" 2>/dev/null || echo "$z_now"))) -gt 60 ]; then
  if ! flock -n "$ZDIR/eingang.lock" true 2>/dev/null && z_drossel lock 3600; then
    "$NOTIFY" "Zentrale: Eingangs-Lock haengt" "eingang.lock wird seit ueber 60 s gehalten." ALARM
  fi
fi

now="$(date +%s)"
# State-Datei: "state ts badcount lastmail" — aeltere 2-Feld-Form liest sich mit Defaults.
prev_state="none"; prev_ts=0; badcount=0; lastmail=0
[ -r "$LAST" ] && read -r prev_state prev_ts badcount lastmail <"$LAST"
: "${prev_ts:=0}"; : "${badcount:=0}"; : "${lastmail:=0}"

nhosts=$(echo $HOSTS | wc -w)

# G252 1.1 (der Nutzer 14.11., Frage 2b): Wartungsfenster nach dem 04:30-Update. rc-autoupdate.sh schreibt
# "jetzt + 15 min". Im Fenster nur loggen, State nicht anfassen (danach meldet er sofort, nicht erst nach REALERT).
# Ein Wert mehr als 20 min in der Zukunft ist ungueltig -> ALARM, damit nichts den Watchdog dauerhaft stummschaltet.
WARTUNG="$HOME/.claude/state/rc-wartung.until"
in_wartung=0
if [ -r "$WARTUNG" ]; then
  read -r wbis <"$WARTUNG" 2>/dev/null
  if [[ "${wbis:-}" =~ ^[0-9]+$ ]] && [ "$wbis" -gt "$now" ]; then
    if [ $((wbis - now)) -le 1200 ]; then
      in_wartung=1
    else
      "$MAIL" "Wartungsfenster ungueltig" "rc-wartung.until liegt $(( (wbis - now) / 60 )) min in der Zukunft (erlaubt: 20). Watchdog meldet normal weiter."
    fi
  fi
fi

if [ -n "$bad" ] || [ "$authfails" -gt 3 ] || [ -n "$loud" ] || [ -n "$hung" ]; then
  if [ "$in_wartung" -eq 1 ]; then
    echo "[$(date -Is)] rc-watchdog: Wartungsfenster bis $(date -d "@$wbis" +%H:%M), nur geloggt: nicht running:${bad:- -} auth:$authfails" >>"$LOG"
    exit 0
  fi
  state="bad"
  badcount=$((badcount + 1))
  reason="nicht running:${bad:- -} | 'must be logged in' letzte 6min: $authfails${loud:+ | crash-loop:$loud}${hung:+
haengt (laeuft, antwortet nicht):
$hung}"

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
    # G252 Frage 2a (der Nutzer 14.11.): Alarm sofort aufs Handy (rc-mail.sh = ntfy, Rueckfall SMTP), nicht erst nach 15 min.
    if [ $((now - lastmail)) -ge "$REMAIL" ]; then
      "$MAIL" "RC-Hosts DOWN" "$reason"
      lastmail="$now"
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
    "$NOTIFY" "RC-Hosts wieder OK" "Alle $nhosts claude-rc-*-Services running, keine Auth-Fehler."
    # Entwarnung auch per Mail — aber nur, wenn vorher eine Mail rausging.
    [ "$lastmail" -gt 0 ] && "$MAIL" "RC-Hosts wieder OK" "Alle $nhosts claude-rc-*-Services running. Ausfall dauerte ca. $((badcount * 5)) min ($badcount Checks)."
  fi
  echo "$state $now 0 0" >"$LAST"
fi
exit 0
