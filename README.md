# claude-setup

Ein gewachsenes Claude-Code-Setup: 46 Skills, 19 Agents, 47 Hooks, 15 Regel-Dateien und die
Betriebs-Skripte drumherum. Kein Framework — das hier läuft täglich produktiv auf einem
Linux-Server und einem Windows-PC. Übernommene Fremdanteile stehen in [THIRD_PARTY.md](THIRD_PARTY.md).

Veröffentlicht, weil die interessanten Teile nicht die einzelnen Skills sind, sondern die
Muster dahinter: wie man Regeln durchsetzt, die sonst nach zwanzig Turns vergessen werden,
und wie man merkt, dass eine Automatisierung seit zwei Wochen still nichts tut.

## Was hier drin steckt

```
skills/      46 Skills — Review-Orchestrierung, Prompt-Optimierung, Security-Audits,
             Debugging, Doku-Drift, Tool-Discovery, Website-Analyse
agents/      19 Sub-Agents — spezialisierte Reviewer (async, Security, Performance,
             Dependencies) und Brücken zu anderen Modellen
hooks/       47 Hooks — Lifecycle-Automatisierung: Kontext-Überwachung, Secret-Guards,
             Session-Logging, Compact-Sicherung
rules/       15 globale Regeln, die in jeder Session geladen werden
scripts/     Betriebs-Skripte: Routine-Reporting, Watchdogs, Trust-Guard, Modell-Brücken,
             Repo-Sync
templates/   Projekt-Scaffolding
```

## Drei Muster, die den Unterschied machen

**Aktive Hooks statt passiver Regeln.** Eine Anweisung wie „prüfe die Kontext-Auslastung bei
60 %" steht im Prompt und wird im Arbeitsfluss zuverlässig ignoriert. Dasselbe als
`UserPromptSubmit`-Hook, der den Zustand misst und eine `systemMessage` zurückgibt, greift
jedes Mal. Die Regeln in `rules/` beschreiben Absichten; die Hooks in `hooks/` setzen sie
durch.

**Stille Ausfälle sichtbar machen.** Ein Hook mit einem Gate wie
`if not flag.exists(): sys.exit(0)` sieht im Betrieb genauso aus wie „alles in Ordnung" —
er tut nur nichts mehr. Genau das ist hier zwei Wochen lang unbemerkt passiert.
`scripts/routine_audit.py` prüft deshalb nicht nur, ob Routinen liefen, sondern auch, ob die
Sicherheitsnetze überhaupt scharf sind. Dazu gehört ein Evidenz-Modell, das zwischen „loggt
jeden Lauf" und „loggt nur bei Ereignis" unterscheidet — ohne das erzeugt jede stille
Routine einen Fehlalarm.

**Belegen statt behaupten.** Mehrere Skills verlangen ausgeführte Nachweise statt
Einschätzungen: `review` schreibt eine strukturierte `findings.json` und führt ein
Outcome-Ledger über frühere Befunde, `investigate` verbietet Fixes ohne belegte Ursache,
und die Routinen hinterlassen Reports mit einem Pflicht-Abschnitt „braucht", damit
„braucht nichts" eine ausgesprochene Aussage ist und keine Lücke.

## Nutzung

Einzelne Teile lassen sich direkt übernehmen — ein Skill ist ein Ordner mit `SKILL.md`, ein
Hook eine Python-Datei plus Eintrag in `settings.json`:

```bash
cp -r skills/investigate  ~/.claude/skills/
cp    hooks/context_threshold_warning.py ~/.claude/hooks/
```

Das Setup als Ganzes zu übernehmen ergibt wenig Sinn: vieles ist auf eine konkrete
Infrastruktur zugeschnitten. Die Muster sind übertragbar, die Konfiguration nicht.

## Was fehlt und warum

`settings.json` ist nicht enthalten — sie verdrahtet die Hooks, enthält aber
maschinenspezifische Pfade und Berechtigungen. Als Ersatz dokumentiert
[`hooks/README.md`](hooks/README.md) die vollständige Verdrahtung: welcher Hook an welchem
Event hängt, mit Matcher, Timeout und Zweck — erzeugt aus der real laufenden Konfiguration.

Secrets, Logs, Transcripts, Session-State und Backups fehlen ebenfalls, ebenso einige
persönliche Skills. Pfade sind auf `$HOME` normalisiert, Server- und interne Adressen durch
Platzhalter ersetzt, Daten Dritter entfernt.

Das Repo wird mit [`scripts/setup_repo_sync.py`](scripts/setup_repo_sync.py) aus der laufenden
Installation nachgezogen: kopieren, bereinigen (die Ersetzungsliste ist privat), prüfen
(Secret-Werte aus den env-Dateien, Personendaten, `gitleaks`). Committet wird nur bei null
Befunden; der Pre-Commit-Hook mit `detect-secrets` läuft zusätzlich.

Die Doku ist überwiegend deutsch, weil das Setup deutsch betrieben wird. Code und
Bezeichner sind englisch.

## Lizenz

MIT — siehe [LICENSE](LICENSE).
