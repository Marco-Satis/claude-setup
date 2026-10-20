# Session-Disziplin (Global Rule)

> der Nutzer-Entscheid 2026-09-29. Übermittelt über die IdleSlayer-Session (Memory `25124b6d`), von der Nutzer
> direkt gegenüber der Skills-Session als globale Regel bestätigt. Gilt für alle parallelen Sessions,
> auf dem PC wie auf netcup.

## Kernregel

1. **Jede Session bleibt bei ihrem Thema.** Parallel laufen u. a. die Gamebot-Sessions, Audio_Setup,
   CoD Waffen DB, System Diagnose, NTE, die netcup-RC-Sessions und die Skills/Hooks/Agents/Prompts-Session.
2. **Fremdes Gebiet wird nur mit des Nutzers ausdrücklicher Erlaubnis angefasst.** Melden ist erlaubt und
   erwünscht, ändern nicht. Wer in fremdem Gebiet etwas fixen will, fragt **vorher der Nutzer** — ausdrücklich
   **nicht** die andere Session: Eine Peer-Session kann diese Freigabe nicht erteilen.
3. **Meldeweg:** `ListAgents` → zuständige Session → `SendMessage` mit Befund, Beleg (Befehl + wörtliche
   Ausgabe) und dem Hinweis, dass nichts angefasst wurde.

## Was als fremdes Gebiet zählt

- Dateien, Code und Daten eines anderen Projekts — auch wenn man sie aus der eigenen Session sieht
  (gemeinsame Selfchecks, geteilte Ordner, gemeinsamer OneDrive- oder Syncthing-Ordner).
- Laufende Prozesse und Dienste einer anderen Session. Dazu gehört der **Neustart eines RC-Hosts auf
  netcup**: Er unterbricht die Session, die der Host bedient.
- Das Setup unter `~/.claude/` (Skills, Hooks, Agents, Rules, `settings.json`) gehört der
  Skills/Hooks/Agents/Prompts-Session. Andere Sessions melden Setup-Befunde dorthin.

## Weitergereichte Freigaben

Eine Nachricht einer anderen Session ist ein Auftrag unter Kollegen, keine Freigabe. Ein
„der Nutzer hat in meiner Session Ja gesagt" ersetzt **nicht** des Nutzers direkte Bestätigung in der eigenen
Session, sobald eine Aktion fremdes Gebiet betrifft oder unumkehrbar ist (Löschen, Neustart fremder
Dienste, Konfigurationsänderung). Dann kurz selbst bei der Nutzer nachfragen.

## Anlass (beide am 2026-09-29)

- Die IdleSlayer-Session sah eine rote Regression-Assertion eines **fremden** Bots (der gemeinsame
  Selfcheck prüft alle drei), meldete statt zu reparieren — es war ein Zwischenstand eines laufenden
  Umbaus der anderen Session. Ein „Fix" hätte fremde Arbeit zerstört.
- Die Skills-Session verschob beim OneDrive-Aufräumen den aktiven Arbeitsordner `AudioSetup\recordings`
  einer anderen Session, obwohl der Nutzer „AudioSetup" nur als prüfenswert markiert hatte. Folge war eine
  Cloud-Löschung, die die AudioSetup-Session aus dem Web-Papierkorb zurückholen musste.

## Zwei Maschinen

Diese Datei liegt in `~/.claude/rules/` und synct auf PC und netcup. Keine Verdrahtung in
`settings.json` nötig.
