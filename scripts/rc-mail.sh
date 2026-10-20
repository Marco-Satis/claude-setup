#!/usr/bin/env bash
# rc-mail.sh — E-Mail-Eskalationskanal (P3, 2026-08-14).
# Zweiter Kanal NEBEN rc-notify.sh (Discord): fuer den Fall, dass Discord selbst
# der ausgefallene/unbemerkte Kanal ist. Kein sudo, kein msmtp — python3 smtplib.
#
# Aufruf:  rc-mail.sh "<Betreff>" "<Text>"
# Secrets: ~/.claude/secrets/mail.env (Permission 600, synct NICHT — netcup-only,
#          wie routine_webhook.env). Noetig: SMTP_USER, SMTP_APP_PASSWORD, MAIL_TO.
#          Gmail: App-Passwort unter https://myaccount.google.com/apppasswords
#          (braucht aktivierte 2FA), NICHT das Kontopasswort.
# No-op-sicher: fehlt die env-Datei oder eine Variable -> Log-Zeile, Exit 0.
set -uo pipefail
ENV_FILE="$HOME/.claude/secrets/mail.env"
LOG="$HOME/.claude/logs/rc-health.log"
SUBJECT="${1:-RC-Alarm}"
BODY="${2:-}"

log() { echo "[$(date -Is)] rc-mail: $*" >> "$LOG"; }

# ntfy-Push (der Nutzer-Entscheid 2026-10-01): erster Eskalationsweg, aufs Handy per ntfy-App.
# Kein Konto, kein Schluessel — das zufaellige Topic in ~/.claude/secrets/ntfy.env (600)
# ist das Geheimnis. Brevo-SMTP unten bleibt nur Rueckfall, bis mail.env entfernt ist.
NTFY_ENV="$HOME/.claude/secrets/ntfy.env"
if [ -r "$NTFY_ENV" ]; then
  NTFY_TOPIC=$(sed -n 's/^NTFY_TOPIC=//p' "$NTFY_ENV" | head -1)
  NTFY_SERVER=$(sed -n 's/^NTFY_SERVER=//p' "$NTFY_ENV" | head -1)
  if [ -n "$NTFY_TOPIC" ] && SUBJ="$SUBJECT" BODY="$BODY" TOPIC="$NTFY_TOPIC" \
       SERVER="${NTFY_SERVER:-https://ntfy.sh}" /usr/bin/python3 - <<'PY'
import json, os, sys, urllib.request
d = {"topic": os.environ["TOPIC"], "title": "[netcup] " + os.environ.get("SUBJ", "RC-Alarm"),
     "message": (os.environ.get("BODY") or "-")[:3500], "priority": 4, "tags": ["rotating_light"]}
req = urllib.request.Request(os.environ["SERVER"], data=json.dumps(d).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception as e:
    print(f"ntfy failed: {type(e).__name__}", file=sys.stderr)
    sys.exit(1)
PY
  then
    log "ntfy gesendet: '$SUBJECT'"
    exit 0
  fi
  log "ntfy FEHLGESCHLAGEN: '$SUBJECT' — Rueckfall SMTP"
fi

if [ ! -r "$ENV_FILE" ]; then
  log "keine $ENV_FILE — Mail '$SUBJECT' uebersprungen (no-op)"
  exit 0
fi
set -a; . "$ENV_FILE"; set +a
if [ -z "${SMTP_USER:-}" ] || [ -z "${SMTP_APP_PASSWORD:-}" ] || [ -z "${MAIL_TO:-}" ]; then
  log "mail.env unvollstaendig (SMTP_USER/SMTP_APP_PASSWORD/MAIL_TO) — '$SUBJECT' uebersprungen"
  exit 0
fi
# Relay-Kennung als Absender ist der Fall, der still scheitert: SMTP sagt 250,
# der Relay verwirft danach. Laut melden statt hoffen (Befund 2026-08-17).
case "${SMTP_USER}" in
  *smtp-brevo.com|*sendgrid.net|apikey)
    [ -z "${MAIL_FROM:-}" ] && log "WARNUNG: SMTP_USER ist eine Relay-Kennung und MAIL_FROM fehlt — '$SUBJECT' wird sehr wahrscheinlich still verworfen"
    ;;
esac

SUBJ="$SUBJECT" BODY="$BODY" /usr/bin/python3 - <<'PY'
import os, smtplib, ssl, sys
from email.message import EmailMessage
from email.utils import formatdate

msg = EmailMessage()
# From != SMTP_USER: bei Relays wie Brevo ist SMTP_USER eine Login-Kennung
# (<relay-login>@smtp-brevo.com), keine Adresse. Der Relay nimmt die Transaktion an und
# verwirft die Mail danach still, wenn der Absender kein verifizierter Sender des
# Kontos ist — SMTP meldet Erfolg, es kommt nie etwas an (Befund 2026-08-17).
# MAIL_FROM setzen; nur als Rueckfall SMTP_USER (korrekt bei Gmail & Co).
msg["From"] = os.environ.get("MAIL_FROM") or os.environ["SMTP_USER"]
msg["To"] = os.environ["MAIL_TO"]
msg["Subject"] = "[netcup RC] " + os.environ.get("SUBJ", "RC-Alarm")
msg["Date"] = formatdate(localtime=True)
msg.set_content(os.environ.get("BODY", "") + "\n\n-- rc-mail.sh, netcup-server")

host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
port = int(os.environ.get("SMTP_PORT", "587"))
try:
    with smtplib.SMTP(host, port, timeout=20) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_APP_PASSWORD"])
        s.send_message(msg)
except Exception as e:
    print(f"send failed: {e.__class__.__name__}: {e}", file=sys.stderr)
    sys.exit(1)
PY
rc=$?
if [ "$rc" -eq 0 ]; then log "gesendet: '$SUBJECT' an $MAIL_TO"; else log "SENDEN FEHLGESCHLAGEN: '$SUBJECT' (rc=$rc)"; fi
exit 0
