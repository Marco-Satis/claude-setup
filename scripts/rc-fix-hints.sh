#!/usr/bin/env bash
# rc-fix-hints.sh — erzeugt zum aktuellen Ausfall die passenden Copy-Paste-Befehle.
#
# Hintergrund (2026-08-14): der Nutzer kann seit heute vom Handy aus Befehle auf dem Server
# ausfuehren. Damit ist ein Alarm nicht mehr nur Kenntnisnahme, sondern Handlungsaufruf —
# vorausgesetzt, die Mail enthaelt etwas Ausfuehrbares statt Diagnose-Prosa. Der Incident
# vom 14.08. (Crash-Loop 04:30-07:05, 453 Restarts) waere so in einer Minute erledigt
# gewesen: Mail lesen, eine Zeile absetzen, fertig.
#
# Aufruf:  rc-fix-hints.sh "<bad-hosts>" "<loud-hosts>"
#          (Kurznamen ohne claude-rc-Praefix, wie im Watchdog gesammelt)
# Ausgabe: fertiger Textblock fuer die Alarm-Mail. Zeilen bewusst kurz — wird auf
#          einem Handy-Display gelesen.
set -uo pipefail
BAD="${1:-}"
LOUD="${2:-}"

# Symptom je Host aus dem Journal bestimmen. Reihenfolge = Spezifitaet: die konkrete
# Fehlermeldung schlaegt die generische "laeuft nicht"-Diagnose.
symptom_of() {
  local h="$1" j
  j="$(journalctl --user -u "claude-rc-$h.service" -n 40 --no-pager 2>/dev/null)"
  case "$j" in
    *"Workspace not trusted"*)  echo "trust" ;;
    *"must be logged in"*)      echo "auth" ;;
    *"Error: "*)                echo "error" ;;
    *)                          echo "down" ;;
  esac
}

emit_for() {
  local h="$1" s
  s="$(symptom_of "$h")"
  echo
  case "$s" in
    trust)
      local wd
      wd="$(systemctl --user show "claude-rc-$h.service" -p WorkingDirectory --value 2>/dev/null)"
      echo "[$h] Workspace not trusted — Trust-Eintrag fehlt fuer ${wd:-(Pfad siehe Fehlermeldung)}"
      # Pfad zur LAUFZEIT aufloesen statt einbacken: sonst steht bei leerem
      # WorkingDirectory ein kaputter Befehl in der Mail, den der Nutzer blind abschickt.
      echo "  /usr/bin/python3 ~/.claude/rc-trust-guard.py \"\$(systemctl --user show claude-rc-$h.service -p WorkingDirectory --value)\" && systemctl --user reset-failed claude-rc-$h.service && systemctl --user restart claude-rc-$h.service"
      echo "  (Der Guard sollte das seit 14.08. selbst tun — wenn diese Zeile noetig war, ist er defekt.)"
      ;;
    auth)
      echo "[$h] Claude-Auth tot — /login ist interaktiv, laesst sich NICHT per Einzeiler heilen."
      echo "  ssh netcup, dann:  claude"
      echo "  darin /login, die URL in CHROME oeffnen (nicht Opera GX -> PKCE-400)."
      echo "  Danach heilen sich alle Hosts selbst (Restart=always)."
      ;;
    error|down)
      echo "[$h] laeuft nicht — Neustart und Blick ins Log:"
      echo "  systemctl --user reset-failed claude-rc-$h.service && systemctl --user restart claude-rc-$h.service"
      echo "  journalctl --user -u claude-rc-$h.service -n 25 --no-pager"
      ;;
  esac
}

echo "SOFORT-FIX (copy-paste, laeuft auch vom Handy):"

for h in $BAD; do emit_for "$h"; done

for entry in $LOUD; do
  h="${entry%%(*}"
  case " $BAD " in
    *" $h "*) continue ;;   # schon oben behandelt
  esac
  echo
  echo "[$h] crash-loopt trotz 'running' ($entry) — Zaehler zuruecksetzen und neu starten:"
  echo "  systemctl --user reset-failed claude-rc-$h.service && systemctl --user restart claude-rc-$h.service"
done

cat <<'EOF'

Wenn nichts davon greift:
  systemctl --user list-units 'claude-rc-*' --no-pager
  ~/.claude/rc-fix-invisible.sh --dry-run

Nebenbaustelle, die zweimal am 14.08. auffiel — Memory-Service haengt still
(Port lauscht, HTTP antwortet nicht). Pruefen und ggf. neu starten:
  curl -s -m 5 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/api/health
  systemctl --user restart mcp-memory.service
EOF
