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
   - PC: geplante Aufgabe über „Setup PC" mit derselben Regel (Vorlage: `Games/CellSurvivor/backup_prune.ps1`).
4. **„Archivieren statt löschen" gilt für Arbeitsdateien**, nicht für `.bak`-Kopien: Ein Backup ist selbst schon
   die Sicherung und wird nach Ablauf gelöscht.
5. Ausgenommen: `_archive*`/`_archiv*`, `.git`, `.stversions`, Rotations-Backups ohne Zeitstempel, `~/wissen`
   (wz verwaltet seine Historie selbst).

## Weitere Altdateien

Logs, Captures, Debug-Frames und PreCompact-Backups bekommen dieselbe Denkweise: Wer etwas regelmäßig erzeugt,
legt beim Bau eine Obergrenze fest (Anzahl, Alter oder Größe) und hängt sie an eine Routine. PreCompact-Ordner
unter `~/.claude/backups/` räumt `backup_prune.py` nach 14 Tagen mit ab.
