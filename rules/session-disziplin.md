# Session-Disziplin (Global Rule)

> der Nutzer-Entscheid 2026-09-29. Übermittelt über die IdleSlayer-Session (Memory `25124b6d`), von der Nutzer
> direkt gegenüber der Skills-Session als globale Regel bestätigt. Gilt für alle parallelen Sessions,
> auf dem PC wie auf netcup.

## Kernregel

1. **Jede Session bleibt bei ihrem Thema.** Parallel laufen u. a. die Gamebot-Sessions, Audio_Setup,
   CoD Waffen DB, System Diagnose, NTE, die netcup-RC-Sessions und die Setup-Sessions („Setup Server“ auf netcup, „Setup PC“ am PC).
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
  Setup-Session („Setup Server“, für Windows-Eigenes „Setup PC“). Andere Sessions melden Setup-Befunde dorthin.

## Weitergereichte Freigaben

Eine Nachricht einer anderen Session ist ein Auftrag unter Kollegen, keine Freigabe. Ein
„der Nutzer hat in meiner Session Ja gesagt" ersetzt **nicht** des Nutzers direkte Bestätigung in der eigenen
Session, sobald eine Aktion fremdes Gebiet betrifft oder unumkehrbar ist (Löschen, Neustart fremder
Dienste, Konfigurationsänderung). Dann kurz selbst bei der Nutzer nachfragen.

**Ausnahme Setup-Zentrale (der Nutzer 2026-11-13, 23:35, bestätigt 23:37 „MB118 ja“):** Reicht „Setup Server“ ein Ja von
der Nutzer **wörtlich mit Datum und Uhrzeit** an eine Session weiter, gilt es dort wie sein direktes Ja. Nur „Setup Server“
darf das, keine andere Session, und nur für den Punkt, den das Zitat nennt.

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

## Setup-Zentrale = Hauptorchestrator (der Nutzer 2026-11-13)

Die netcup-Session **„Setup Server“** (Rolle Setup-Zentrale, RC-Host `claude-rc-skills`, Ordner `~/projects/Skills_&_Co`, Postfach-Rolle
`skills`; bis 13.11. „Skills/Hooks/Agents/Prompts-Server“) ist des Nutzers Hauptsession:
- Sie verwaltet das Setup und hält den Überblick über alle Projekte (Wissensspeicher, Routinen, Kompass, Postfach).
- Projektübergreifendes stößt sie bei den zuständigen Sessions an (Postfach, `SendMessage`, `session_anstoss.sh`),
  statt fremde Projekte selbst zu ändern. Die Session-Disziplin oben gilt weiter auch für sie.
- Andere Sessions melden Setup-Befunde und projektübergreifende Themen an „Setup Server“. Ihr PC-Gegenstück heißt „Setup PC“ (Windows-Setup, PC-globale `CLAUDE.md`).
- **Entscheidungen weiterreichen, ohne Auftrag (der Nutzer 2026-11-14):** Entscheidet der Nutzer in der Zentrale etwas, das andere
  Sessions betrifft (Kanäle, Regeln, Werkzeuge, Prioritäten), gibt sie es von selbst an die betroffenen Sessions weiter:
  Setup-weite Änderungen als `setup-change`-Memory (erreicht alle laufenden Sessions), Projektbezogenes per `SendMessage`.
- Damit nichts verloren geht: Entscheidungen und Fakten landen im Wissensspeicher (`wz`), Laufendes in
  `~/projects/Skills_&_Co/PROGRESS.md`.

## Empfang bestätigen (der Nutzer 2026-11-13)

Nachrichten über Remote Control (PC ↔ netcup) melden dem Absender keine Zustellung („not confirmed read“). Deshalb:
- Wer eine Nachricht einer anderen Session bekommt, **antwortet sofort mit einer Zeile** an den `from=`-Absender:
  `Empfangen: <Stichwort der Nachricht> – <übernommen | erledigt | an der Nutzer-Block | abgelehnt: Grund>`.
  Folgt die inhaltliche Antwort ohnehin im selben Zug, ersetzt sie die Quittung.
- Ausgenommen sind reine Quittungen und Abschlussmeldungen ohne Frage (keine Quittung auf eine Quittung, sonst Schleife).
- Der Absender wertet eine fehlende Quittung nach 30 min als „nicht angekommen“ und schickt einmal erneut bzw. über
  „Setup PC“ oder „Setup Server“ als Relais.

## Nachtbetrieb: der Nutzer schläft (der Nutzer 2026-11-13)

„Berechtigungsabfragen sollen gesammelt werden, damit in der Zeit, wo ich schlafe, alles weiterlaufen kann.“ Eine
Freigabe-Abfrage, die niemand beantwortet, hält die Session bis zum Morgen an. Solange der Nutzer schläft (Ansage von ihm
oder „Setup Server“, sonst ab 10 min ohne Antwort spät abends):
1. **Keine Aktion starten, die eine Freigabe-Abfrage auslöst:** `rm`, `git push`, `sudo …`, Neustarts von Diensten und
   alles, was beim letzten Mal nachgefragt hat. Ausnahme: Gamebot-Neustarts nach der Konsens-Regel in
   [gamebot-reuse-first](gamebot-reuse-first.md) (der Nutzer 13.11.).
2. **Stattdessen sammeln:** den genauen Befehl als MB-Zeile an „Setup Server“ schicken
   (`MB: <projekt> | Freigabe: <befehl> | <dauer> | <warum>`), dann mit anderer Arbeit weitermachen.
3. **Ohne Rückfrage weiterarbeiten:** Wegwerf-Dateien ins Scratchpad statt `rm`, committen ja, pushen nein, Edits mit
   Backup wie immer.
4. „Setup Server“ führt davon nur aus, was in seinem eigenen Bereich liegt und die Bedingungen für delegierte
   Entscheidungen erfüllt ([mitdenken](mitdenken.md)). Freigaben in fremden Sessions erteilt nur der Nutzer selbst.

Auch tagsüber gilt: Rückfragen nur, wenn sie etwas schützen. Die häufigsten vermeidbaren (Freigabe-Audit 13.11., netcup
und PC): `curl` (am PC Ask-Regel) → Webseiten mit WebFetch, Memory mit den `mcp__memory__*`-Tools; `rm` → Scratchpad;
`git push` → gebündelt; `AskUserQuestion` nur bei echten Entscheidungen, alles andere als MB-Zeile an „Setup Server“.
