---
name: loopstop
description: Stoppt den Loop-Mode DIESER Session und setzt die Loop-Einstellungen zurück. Löscht LOOP_RUN.flag (Master-Schalter) + den recurring CronCreate-Antrieb (CronDelete), re-armt KEINEN Wake mehr, und der Context-Nag-Hook ist für diese Session wieder aktiv. Trigger /loopstop. Stoppt nur die Claude-Operator-Schleife — die Bot-Python-Loops + OS-Watchdogs laufen unabhängig weiter.
---

# /loopstop — Loop-Mode stoppen + zurücksetzen (session-scoped)

Beendet die autonome Tick-Schleife dieser Session sauber und macht die Loop-Einstellungen rückgängig.

## Schritte
1. **Master-Schalter löschen:** lösche `Games/<dir>/LOOP_RUN.flag` des Spiels, das DIESE Session betreibt (aus deiner `START_PROMPT`/`LOOP_TICK.md` bekannt). Unklar welches → der Nutzer fragen. Ohne Flag bricht der nächste TICK sofort ab (Stop-Check in `TICK_PROMPT.md` Schritt 0).
2. **Cron-Antrieb löschen:** `ToolSearch` `select:CronList,CronDelete` → `CronList` → den recurring `TICK <spiel>`-Job per `CronDelete <id>` beenden. Sonst feuert der Cron weiter ins Leere (findet zwar kein `LOOP_RUN.flag` und tickt folgenlos, verbrennt aber Token bei jedem idle-Fire). KEINEN neuen `ScheduleWakeup`/Cron setzen.
3. **Nag-Reset (automatisch):** der Hook hat diese `session_id` beim `/loopstop`-Prompt aus `loopmode_sessions.json` entfernt → der Context-Nag (50/60/70%) ist für diese Session wieder aktiv.
4. **Bestätigen** (max 2 Zeilen): „Loop gestoppt für <spiel>, LOOP_RUN.flag + Cron entfernt, Nag wieder an."

**Wichtig:** Das stoppt nur den **Claude-Operator-Loop** (Monitoring/Verbessern). Die **Bot-Python-Loops** (`run.py --loop`) + OS-Watchdogs (Scheduled Tasks) farmen unabhängig weiter — die separat stoppen (`STOP.flag` im Game-Dir / Task beenden), falls auch das Farmen aus soll.
