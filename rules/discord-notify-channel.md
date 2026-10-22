# Discord-Benachrichtigungen — kanonischer Kanal (Global Rule)

> Festgelegt 2026-07-23. Gilt für alle Skripte, Hooks, Cronjobs, Services und Agents.

## Regel

Jede **Informations-Benachrichtigung nach Discord** geht über den gemeinsamen Claude-Notify-Webhook.
Kein zweiter Webhook, kein eigener Bot-Token pro Skript, keine hartcodierte URL.

**Ausnahme:** alles was zur **TikTok-Pipeline** gehört — die hat ihren eigenen Kanal und bleibt getrennt.

## Wie ansprechen

Immer über den Wrapper, nie direkt curl:

```bash
~/.claude/rc-notify.sh "<Titel>" "<Text>"
```

Der Wrapper schreibt zusätzlich `~/.claude/logs/rc-health.log` + `~/.claude/rc-health.state`
und ist no-op-sicher, wenn kein Webhook konfiguriert ist (kein Fehler, nur Log).

Wenn ein Skript den Webhook selbst braucht:

```bash
set -a; . ~/.claude/secrets/routine_webhook.env; set +a
# $CLAUDE_NOTIFY_WEBHOOK  (bevorzugt)
# $DISCORD_ROUTINE_WEBHOOK (Alt-Name, gleicher Wert, für routine_report.py)
```

## Secret-Handling

- URL liegt **ausschließlich** in `~/.claude/secrets/routine_webhook.env` (Permission 600).
- **Nie** in Code, Repo, Doku, Commit, Chat oder Log. Auch nicht in dieser Datei.
- Die URL ist ein Credential: wer sie hat, kann in den Kanal posten (write-only, kein Lesezugriff).
  Bei Exposure → in Discord: Kanal → Integrationen → Webhooks → **URL neu generieren**, dann
  `read -rsp` in die env-Datei. Siehe [Secret-Handling](secret-handling.md).
- ⚠ **Korrigiert 2026-07-28 (F-5 aus dem Inventar-Audit): dieser Kanal ist netcup-only.**
  Die frühere Aussage „`~/.claude/secrets/` synct auf den PC" war falsch, gleich doppelt:
  `.stignore` endet auf Catch-all `**` und inkludiert nur `!/skills !/agents !/hooks !/rules
  !/templates !/scripts !/commands` — `/secrets` ist nicht dabei; zusätzlich schließt `*.env`
  die Datei explizit aus. Auf dem PC existiert `~/.claude/secrets/` gar nicht, ebenso wenig
  `rc-notify.sh`, `rc-watchdog.sh`, `rc-autoupdate.sh`.
  **Folge:** jeder Discord-Notify-Aufruf von der Windows-Seite ist ein stiller No-op
  (der Wrapper ist no-op-sicher, es knallt nicht — es kommt nur nie etwas an).
  Wer von der PC-Seite nach Discord melden will, nutzt den Bot-Token-Weg über die
  ENV-Variablen `CLAUDE_DISCORD_BOT_TOKEN` / `CLAUDE_DISCORD_CHANNEL_ID`
  (so machen es `discord_afk_relay.py`, `bg_needs_input_notify.py` und die Loop-Context-Frühwarnung in
  `context_threshold_warning.py`) — nicht `rc-notify.sh`.
  ⚠ **Stand 2026-10-22: Diese Variablen sind am PC NICHT gesetzt.** Deshalb gilt seit
  2026-10-22 (der Nutzer-Entscheid, Weg A) der Helfer `hooks/notify_fallback.py`: netcup →
  `rc-notify.sh`; Bot-Token gesetzt → Discord-API; sonst Windows → `ssh netcup-marco
  ~/.claude/rc-notify.sh "<titel>" "<text>"` (Webhook bleibt auf netcup, am PC kein Secret).
  Neue Hooks mit Discord-Meldung nutzen `notify_fallback.send(titel, text)`.

## Aktuelle Konsumenten

| Konsument | Zweck |
|---|---|
| `~/.claude/rc-watchdog.sh` | RC-Hosts down / Claude-Auth tot (alle 5 min geprüft) |
| `~/.claude/rc-autoupdate.sh` | Update-Restart wegen toter Auth abgebrochen |
| `~/.claude/scripts/routine_report.py` | Routine-Report (nutzt `DISCORD_ROUTINE_WEBHOOK`) |
