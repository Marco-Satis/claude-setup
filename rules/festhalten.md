# Alles Nützliche festhalten (Global Rule)

> der Nutzer 2026-11-16, 21:24 und 21:33: „Es geht mir nicht nur um Entscheidungen, sondern alles soll festgehalten werden:
> alles, was für dich nützlich ist, was für die Session nützlich ist, aber auch meine Entscheidungen … was Änderungen
> sind, was Neues gemacht wird oder Sonstiges.“ Befund 16.11.: Von 111 wz-Einträgen der letzten 7 Tage stammten 70 aus
> der Setup-Zentrale; die PC-Sessions hielten fast nichts selbst fest. Die automatischen Mitschriften (`session_logger`,
> 2.738 in einer Woche) enthalten nur Zähler und Schlagworte, keine Inhalte.

## Kernregel

Jede Session hält im selben Zug fest, was sie oder eine andere Session später brauchen könnte, nicht erst am Ende
der Arbeit und nicht nur auf Zuruf. Der Stop-Hook `hooks/wissen_schreibpflicht.py` erzwingt das: Nach einer Nachricht
des Nutzers mit Auftrag oder Festlegung, nach jeder Änderung (Edit/Write, git, Dienste, Aufgaben, Installationen,
Verschieben) und nach Zügen mit vielen Werkzeugaufrufen blockt er das Zugende einmal, wenn nichts geschrieben wurde.

## Was festgehalten wird

| Art | Beispiel |
|---|---|
| des Nutzers Entscheidung, Wunsch, Korrektur, Vorliebe | „Werbevideos für alle drei Bots erlaubt“, „richtiges Deutsch“ |
| Änderung | was, wo (Pfad), warum, Sicherung bzw. Rückweg |
| Neues | Datei, Skript, Hook, Dienst, Routine, Aufgabe, Konto, Ordnerumzug |
| Befund und Ursache | „Hook gab systemMessage aus, das Modell sah es nie“ |
| Fehler mit Lösung und Lehre | Fehlermeldung wörtlich, Fix, was künftig anders läuft |
| Sackgasse | was nicht funktioniert hat und warum, damit es keiner wiederholt |
| Wert | gemessene Zahl, Pfad, Port, Version, funktionierender Befehl |
| Offener Punkt | was fehlt, wer dran ist, nächster Schritt, Frist |
| Zusammenhang | welche anderen Projekte, Sessions oder Routinen betroffen sind |

Nicht festgehalten werden Secret-Werte, Inhalte fremder Mails oder Personendaten Dritter, reine Fragen ohne neues Wissen
und Zwischenstände, die im selben Zug überholt sind.

## Wohin

1. **Dauerhaftes** (Entscheidung, Wert, Ort, Ablauf, Lehre): `wz neu` auf netcup; am PC per `ssh netcup-marco "wz neu …"`
   bzw. `wz neu --aus <datei.json>`. Ein Sachverhalt je Eintrag, Quelle in der Faktzeile.
2. **Verlauf und Stand** (was heute passiert ist, Zwischenergebnisse, offene Punkte): `mcp__memory__memory_store` mit
   Tag `project-<projekt>` und einem Inhalt, der ohne den Chat verständlich ist.
3. **Setup-Änderungen** zusätzlich als mcp-Memory mit Tag `setup-change` (erreicht alle laufenden Sessions).
4. Projektdateien wie PROGRESS.md, HANDOVER oder JOURNAL ersetzen das nicht, sie ergänzen es.

## Lesen gehört dazu

`hooks/memory_delta_watch.py` meldet jeder Session alle 2 min neue `setup-change`-Memories und neue wz-Einträge anderer
Sessions ([WISSEN-DELTA]); der PC bekommt die wz-Kopfdaten über `~/.claude/state/wz_delta.json`. Betrifft ein Eintrag
das eigene Thema, liest die Session ihn mit `wz get`, bevor sie weiterarbeitet. Vor jeder Antwort gilt außerdem
„Bestand zuerst“ ([reuse-leiter](reuse-leiter.md)).

Aus: `touch ~/.claude/flags/wissen_schreibpflicht.off` (nur der Hook; die Regel gilt weiter).
