#!/usr/bin/env bash
# rc-mail.sh — E-Mail-Eskalationskanal (P3, 2026-08-14).
# Zweiter Kanal NEBEN rc-notify.sh (Discord): fuer den Fall, dass Discord selbst
# der ausgefallene/unbemerkte Kanal ist. Kein sudo, kein msmtp — python3 smtplib.
#
# Aufruf:  rc-mail.sh "<Betreff>" "<Text>" [<ntfy-Prioritaet 1-5, Standard 4>]
#          RC_MAIL_CLICK=<url>, RC_MAIL_ACTIONS=<JSON-Liste view-Knoepfe, max 3>: nur https://claude.ai/code/session_*.
#          Eigener ntfy-Server: Flag ~/.claude/flags/ntfy_eigen.on (Volltext, geschwaerzt; 15.11.2026).
#          RC_MAIL_STATUS=1 -> Exit 1, wenn weder ntfy noch SMTP angenommen hat (G252, 14.11.;
#          ohne die Variable bleibt es beim alten Verhalten: immer Exit 0).
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
PRIO="${3:-4}"
case "$PRIO" in [1-5]) ;; *) PRIO=4 ;; esac
PUB_OK=0   # 1 = oeffentlicher Ausfall-Hinweis kam an (dann gilt der Lauf als zugestellt)
fail_exit() { if [ "${RC_MAIL_STATUS:-0}" = "1" ] && [ "$PUB_OK" != "1" ]; then exit 1; fi; exit 0; }

log() { echo "[$(date -Is)] rc-mail: $*" >> "$LOG"; }

# Eigener ntfy-Server (der Nutzer 15.11.2026 06:38, Volltext): aktiv, solange ~/.claude/flags/ntfy_eigen.on existiert.
# Rueckweg in einem Schritt: Flag-Datei wegnehmen (umbenennen), dann gilt wieder nur der Weg darunter.
# Volltext erlaubt, aber geschwaerzt (secret_patterns.json via zentrale_eingang.schwaerzen) und ohne Zeilen,
# die ein Denylist-Projekt aus meldungs_klassen.json nennen (UYM, private). Faellt der eigene Server aus,
# geht nur ein neutraler Hinweis ueber das oeffentliche Topic (kein Volltext dorthin), danach SMTP.
EIGEN_ENV="$HOME/.claude/secrets/ntfy_eigen.env"
EIGEN_FEHLER=0
# RC_MAIL_EIGEN=1 erzwingt den eigenen Weg fuer einen einzelnen Aufruf (Test, ohne das Flag fuer alle zu setzen).
if { [ -e "$HOME/.claude/flags/ntfy_eigen.on" ] || [ "${RC_MAIL_EIGEN:-0}" = "1" ]; } && [ -r "$EIGEN_ENV" ]; then
  if SUBJ="$SUBJECT" BODY="$BODY" PRIO="$PRIO" EIGEN_ENV="$EIGEN_ENV" /usr/bin/python3 -I - <<'PY'
import json, os, re, sys, urllib.request
from pathlib import Path
home = Path.home()
env = {}
for z in Path(os.environ["EIGEN_ENV"]).read_text(encoding="utf-8").splitlines():
    if "=" in z and not z.lstrip().startswith("#"):
        k, v = z.split("=", 1)
        env[k.strip()] = v.strip()
sys.path.insert(0, str(home / ".claude" / "scripts"))
try:
    from zentrale_eingang import schwaerzen
except Exception:
    print("schwaerzen nicht ladbar", file=sys.stderr)
    sys.exit(1)                          # ohne Schwaerzung kein Volltext
try:
    deny = json.loads((home / ".claude/scripts/meldungs_klassen.json").read_text(encoding="utf-8"))["projekte"]["denylist"]
except Exception:
    deny = ["uym", "politik", "bewerbung", "finanz"]
rx = re.compile("|".join(re.escape(d) for d in deny if d), re.I)
def sauber(t: str) -> str:
    zeilen, weg = [], 0
    for z in schwaerzen(t).splitlines():
        if rx.search(z):
            weg += 1
        else:
            zeilen.append(z)
    if weg:
        zeilen.append(f"({weg} vertrauliche Zeile{'n' if weg > 1 else ''} ausgelassen)")
    return "\n".join(zeilen)
def _knoepfe(d, aktiv=True):
    # RC_MAIL_CLICK / RC_MAIL_ACTIONS (Schnittstelle Session-Snapshots, 15.11.2026): nur Links auf
    # claude.ai-Code-Sessions, nur "view", hoechstens 3; alles andere wird verworfen.
    import re
    if not aktiv:
        return d
    rx = re.compile(r"^https://claude\.ai/code/session_[A-Za-z0-9]+$")
    c = (os.environ.get("RC_MAIL_CLICK") or "").strip()
    if c and rx.match(c):
        d["click"] = c
    try:
        acts = json.loads(os.environ.get("RC_MAIL_ACTIONS") or "[]")
    except ValueError:
        acts = []
    out = []
    for a in acts if isinstance(acts, list) else []:
        if (isinstance(a, dict) and a.get("action") == "view" and isinstance(a.get("label"), str)
                and isinstance(a.get("url"), str) and rx.match(a["url"])):
            out.append({"action": "view", "label": a["label"].replace("\n", " ")[:40], "url": a["url"],
                        "clear": bool(a.get("clear", False))})
        if len(out) >= 3:
            break
    if out:
        d["actions"] = out
    return d
prio = int(os.environ.get("PRIO", "4"))
titel = sauber(os.environ.get("SUBJ") or "RC-Alarm").replace("\n", " ")[:200] or "Meldung"
d = {"topic": env["NTFY_EIGEN_TOPIC_MELDUNG"], "title": titel,
     "message": (sauber(os.environ.get("BODY") or "") or "-")[:3900], "priority": prio,
     "tags": ["rotating_light"] if prio >= 4 else ["inbox_tray"]}
d = _knoepfe(d)
for a in d.get("actions", []):
    a["label"] = sauber(a["label"]).replace("\n", " ")[:40] or "Oeffnen"
req = urllib.request.Request(env["NTFY_EIGEN_LOKAL"], data=json.dumps(d).encode(), method="POST",
                             headers={"Content-Type": "application/json",
                                      "Authorization": "Bearer " + env["NTFY_EIGEN_TOKEN"]})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception as e:
    print(f"ntfy-eigen failed: {type(e).__name__}", file=sys.stderr)
    sys.exit(1)
PY
  then
    log "ntfy-eigen gesendet: '$SUBJECT'"
    exit 0
  fi
  log "ntfy-eigen FEHLGESCHLAGEN: '$SUBJECT' — Rueckfall oeffentliches Topic (nur neutraler Hinweis), dann SMTP"
  EIGEN_FEHLER=1
fi
PUB_SUBJECT="$SUBJECT"; PUB_BODY="$BODY"
if [ "$EIGEN_FEHLER" = "1" ]; then
  # Volltext geht nie ans oeffentliche Topic; der Hinweis selbst meldet den Ausfall. SMTP bekommt den Originaltext.
  PUB_SUBJECT="Eigener ntfy-Server nicht erreichbar"
  PUB_BODY="Meldungen kommen per Mail und stehen im Eingang beim Setup Server. Rueckweg: Flag ntfy_eigen.on wegnehmen."
fi

# ntfy-Push (der Nutzer-Entscheid 2026-10-01): erster Eskalationsweg, aufs Handy per ntfy-App.
# Kein Konto, kein Schluessel — das zufaellige Topic in ~/.claude/secrets/ntfy.env (600)
# ist das Geheimnis. Brevo-SMTP unten bleibt nur Rueckfall, bis mail.env entfernt ist.
NTFY_ENV="$HOME/.claude/secrets/ntfy.env"
if [ -r "$NTFY_ENV" ]; then
  NTFY_TOPIC=$(sed -n 's/^NTFY_TOPIC=//p' "$NTFY_ENV" | head -1)
  NTFY_SERVER=$(sed -n 's/^NTFY_SERVER=//p' "$NTFY_ENV" | head -1)
  if [ -n "$NTFY_TOPIC" ] && SUBJ="$PUB_SUBJECT" BODY="$PUB_BODY" TOPIC="$NTFY_TOPIC" \
       SERVER="${NTFY_SERVER:-https://ntfy.sh}" PRIO="$PRIO" EIGEN_FEHLER="$EIGEN_FEHLER" /usr/bin/python3 - <<'PY'
import json, os, sys, urllib.request
def _knoepfe(d, aktiv=True):
    # RC_MAIL_CLICK / RC_MAIL_ACTIONS (Schnittstelle Session-Snapshots, 15.11.2026): nur Links auf
    # claude.ai-Code-Sessions, nur "view", hoechstens 3; alles andere wird verworfen.
    import re
    if not aktiv:
        return d
    rx = re.compile(r"^https://claude\.ai/code/session_[A-Za-z0-9]+$")
    c = (os.environ.get("RC_MAIL_CLICK") or "").strip()
    if c and rx.match(c):
        d["click"] = c
    try:
        acts = json.loads(os.environ.get("RC_MAIL_ACTIONS") or "[]")
    except ValueError:
        acts = []
    out = []
    for a in acts if isinstance(acts, list) else []:
        if (isinstance(a, dict) and a.get("action") == "view" and isinstance(a.get("label"), str)
                and isinstance(a.get("url"), str) and rx.match(a["url"])):
            out.append({"action": "view", "label": a["label"].replace("\n", " ")[:40], "url": a["url"],
                        "clear": bool(a.get("clear", False))})
        if len(out) >= 3:
            break
    if out:
        d["actions"] = out
    return d
d = {"topic": os.environ["TOPIC"], "title": "[netcup] " + os.environ.get("SUBJ", "RC-Alarm"),
     "message": (os.environ.get("BODY") or "-")[:3500], "priority": int(os.environ.get("PRIO", "4")),
     "tags": ["rotating_light"] if int(os.environ.get("PRIO", "4")) >= 4 else ["inbox_tray"]}
d = _knoepfe(d, aktiv=os.environ.get("EIGEN_FEHLER") != "1")   # neutraler Ausfall-Hinweis ohne Knoepfe
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
    log "ntfy gesendet: '$PUB_SUBJECT'"
    # Bei Ausfall des eigenen Servers zusaetzlich Mail mit dem Originaltext (nicht oeffentlich).
    [ "$EIGEN_FEHLER" = "1" ] || exit 0
    PUB_OK=1
  fi
  log "ntfy FEHLGESCHLAGEN: '$SUBJECT' — Rueckfall SMTP"
fi

if [ ! -r "$ENV_FILE" ]; then
  log "keine $ENV_FILE — Mail '$SUBJECT' uebersprungen (no-op)"
  fail_exit
fi
set -a; . "$ENV_FILE"; set +a
if [ -z "${SMTP_USER:-}" ] || [ -z "${SMTP_APP_PASSWORD:-}" ] || [ -z "${MAIL_TO:-}" ]; then
  log "mail.env unvollstaendig (SMTP_USER/SMTP_APP_PASSWORD/MAIL_TO) — '$SUBJECT' uebersprungen"
  fail_exit
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
if [ "$rc" -eq 0 ]; then log "gesendet: '$SUBJECT' an $MAIL_TO"; else log "SENDEN FEHLGESCHLAGEN: '$SUBJECT' (rc=$rc)"; fail_exit; fi
exit 0
