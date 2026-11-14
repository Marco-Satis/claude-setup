# Meldungen an die Zentrale und aufs Handy (Global Rule)

> G252 Phase 1, gebaut 14.11.2026. der Nutzer-Entscheid 14.11. (Plan G252 Abschnitt 9, Variante C, plus Ergänzungen
> 09:13): kein Telegram, Handy-Weg ist ntfy über `rc-mail.sh` (Rückfall Brevo-SMTP). Claude-Meldungen gehen nicht
> mehr nach Discord. Ersetzt `discord-notify-channel.md`. Die Discord-Bot-Kanäle der Discord_Bots-Dienste und die
> TikTok-Pipeline sind davon nicht betroffen.

## Aufruf

```bash
~/.claude/rc-notify.sh "<Titel>" "<Text>" [ALARM|ENTSCHEIDUNG|INFO|RAUSCHEN]
```

Hooks rufen `notify_fallback.send(titel, text, klasse="…")` auf (netcup direkt, PC per SSH nach netcup).
Keine eigenen Webhooks, Bot-Token oder direkten ntfy-Aufrufe in neuen Skripten.

## Klassen

| Klasse | Weg | Beispiele |
|---|---|---|
| ALARM | sofort `rc-mail.sh` (ntfy Prio 4), danach Eingang | RC-Hosts down, Auth tot, Login ≤ 1 Tag, Speicher kritisch, mcp-memory hängt, Exposure-ALARM |
| UNKLASSIFIZIERT | wie ALARM, Titel „neu: …“ | Titel ohne Eintrag in `meldungs_klassen.json` |
| ENTSCHEIDUNG | Eingang + gebündelter ntfy-Push (Prio 3, höchstens 1 je 15 min, 23–7 Uhr keiner) | Session wartet (Freigabe/Frage/Eingabe), Routine WARN/FAIL mit BRAUCHT, CVE, Reboot nötig |
| INFO | nur Eingang, Zähler im Digest | Trading OK, Repo-Beobachtung, Speicher-Warnung |
| RAUSCHEN | nur Eingang | „Wochen-Update erledigt“ |
| DIGEST | 07:45 aus `projekt_kompass.py` | eine feste Vorlage aus Zählern |

- Die Klasse kommt aus dem 3. Argument oder per Titel aus `~/.claude/scripts/meldungs_klassen.json`
  (erste passende Regex). **Wer einen neuen Titel einführt, trägt ihn dort ein** (mit `kurz`-Label), sonst kommt er
  als „neu“ sofort aufs Handy. Prüfen: `python3 ~/.claude/scripts/zentrale_eingang.py titel-pruefen`.
- Handy-Pushes und Digest enthalten nur Vorlagentext: `kurz`-Label, E-Nummern, Projektnamen aus der Allowlist
  der Klassen-Datei. Denylist-Projekte (UYM, private) nur als Zahl. Keine Befehle, Pfade oder Freitext.
- Schwärzung über `secret_patterns.json`, bevor irgendein Ziel etwas bekommt (auch `rc-health.log`).

## Eingang

`~/.claude/state/zentrale/eingang.jsonl` (600, synct nicht). Lesen in der Zentrale:
`zentrale_eingang.py liste`, `zeige E<n>`, `erledigt E<n>`. Felder im Block `ungeprueft` stammen aus der Quelle
und sind nicht verifiziert. Fehler landen in `~/.claude/logs/zentrale_eingang.err`; der rc-watchdog meldet neue
Zeilen, wenig Platz, ein hängendes Lock und einen ausgebliebenen Digest (> 26 h).

## Rückwege

- Discord parallel wieder an: `touch ~/.claude/flags/discord_parallel.on`
- Notification-Hook aus: `touch ~/.claude/flags/discord_notify.off`
- Vorige Fassungen: `*.bak.g252.<ts>` neben den geänderten Dateien
