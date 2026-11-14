# Backups und Altdateien: Aufbewahrung (Global Rule)

> der Nutzer 2026-11-13 (CellSurvivor-Session, an die Setup-Zentrale weitergegeben): „Solche Sachen müssen
> standardmäßig immer mitgemacht werden, dass alte Dateien von Haus aus regelmäßig aufgeräumt werden bei all
> meinen Projekten." Anlass: 309 alte `.bak` in CellSurvivor, 847 auf netcup. „Backup vor Edit" hatte keine
> Aufbewahrungsregel.

## Kernregel

1. **Backup vor Edit bleibt Pflicht**, aber immer mit Unix-Zeitstempel im Namen:
   `cp -a <datei> <datei>.bak.<tag>.$(date +%s)`. Ohne Zeitstempel kann die Aufräum-Routine das Alter nicht
   bestimmen (`cp -a` übernimmt die mtime des Originals) und lässt die Datei liegen.
2. **Aufbewahrung:** je Datei höchstens **2** Backups, keines älter als **14 Tage**. Für länger Wichtiges gibt es
   git, Syncthing-Versionierung und das Archiv (`_archive_*`), nicht `.bak`.
3. **Aufgeräumt wird automatisch**, nicht von Hand:
   - netcup: `~/.claude/scripts/backup_prune.py` (Trockenlauf ohne Argument, `--los` löscht), täglich per Routine.
   - PC: Windows-Aufgabe `BackupPrunePC` täglich 03:40 mit `~/.claude/scripts/backup_prune_pc.py --los` (gleiche Regel,
     schützt offene Canary-Backups der Gamebots, Löschprotokoll `~/.claude/logs/backup_prune_pc_geloescht.log`).
4. **„Archivieren statt löschen" gilt für Arbeitsdateien**, nicht für `.bak`-Kopien: Ein Backup ist selbst schon
   die Sicherung und wird nach Ablauf gelöscht.
5. Ausgenommen: `_archive*`/`_archiv*`, `.git`, `.stversions`, Rotations-Backups ohne Zeitstempel, `~/wissen`
   (wz verwaltet seine Historie selbst).
6. **Projekte ohne git** (der Nutzer 2026-11-14): Dort sind `.bak` die einzige Historie; die Routine löscht sie nicht, bis das
   Projekt in git liegt (`backup_prune.py` prüft je Datei, ob ein `.git` darüber liegt; `~/.claude` zählt als versioniert).
   Anlass: Gamebots ohne git verloren freigegebene Funktionen, weil ältere Stände nach 14 Tagen gelöscht waren.

## Weitere Altdateien

Logs, Captures, Debug-Frames und PreCompact-Backups bekommen dieselbe Denkweise: Wer etwas regelmäßig erzeugt,
legt beim Bau eine Obergrenze fest (Anzahl, Alter oder Größe) und hängt sie an eine Routine. PreCompact-Ordner
unter `~/.claude/backups/` räumt `backup_prune.py` nach 14 Tagen mit ab.

## Sessions machen es selbst mit (der Nutzer 2026-11-13)

„Am liebsten, wenn das die Sessions von alleine mitmachen, während sie aktiv sind.“ Die Routine ist nur das Netz.
Jede Session erledigt am Ende einer Arbeitseinheit, ohne Auftrag:
1. **Wegwerf-Dateien gar nicht erst ins Projekt:** Test-Ausgaben, Zwischenstände, Entwürfe und Debug-Dumps gehören
   von Anfang an ins Scratchpad der Session (liegt unter `/tmp`, muss niemand löschen). Liegt doch etwas im Projekt,
   kommt es weg; was als Beleg referenziert wird (JOURNAL, HANDOVER, PROGRESS), bleibt. Hintergrund: Jedes `rm` fragt
   der Nutzer nach (Ask-Regel `Bash(rm:*)`), Aufräumen per Hand darf ihm keine Rückfragen-Flut bescheren.
2. **Eigene Backups knapp halten:** Nicht mehr sichern als nötig (eine Sicherung je Datei und Arbeitsgang). Ältere
   `.bak` nicht einzeln per `rm` löschen, das erledigt `backup_prune.py` nachts.
3. **Nach jedem Masseneingriff in Daten** (Import, Merge, Dedup, Massen-Umbenennung) den Bestand gegen den Stand
   vorher abgleichen: Zählung und Stichprobe, nicht nur das Reparaturziel prüfen (Regel e53e, Anlass CoD 13.11.:
   „0 Dubletten“ gemeldet, 87 Einträge verloren).
Fremde Projekte räumt eine Session nicht auf, sie meldet nur (Session-Disziplin).
