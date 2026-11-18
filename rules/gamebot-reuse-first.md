# Gamebot Reuse-first (Global Rule)

Auto-applied in den Gamebot-Projekten (cellsurvivor / survivorio / idleslayer) und beim loopmode-Betrieb.

## Das geteilte Grundgerüst heißt `_botcore/`

`C:\Users\<user>\Games\_botcore\` — **nicht** `gamebot_core/`.

Der ursprüngliche Handoff (2026-07-24) schlug ein neues `gamebot_core/` vor, weil er ohne Kenntnis der
PC-Struktur entworfen wurde. Discovery am 2026-07-24 zeigte: `_botcore/` existiert seit Monaten mit 17
Modulen und wird von Survivor_io (10 Dateien) und IdleSlayer (3) importiert. Ein zweites Paket anzulegen
wäre genau das Duplikat, das diese Regel verhindern soll → **`_botcore` ist die kanonische Basis.**

Kern-Module: `core.py` (Device/ADB/Screen/OCR/region_match), `loop_watchdog.py`, `diagnose.py`,
`selfcheck.py`, `game_template.py`, `package_watch.py`, `loop_observer.py`, `canary.py`, `experiment.py`,
`postmortem.py`, `host_guard.py`, `digest.py`, `self_audit.py`, `change_budget.py`, `steplog.py`,
`overnight_monitor.py`, `loop_tick_guard.py`.

**Bekannte Abweichung:** CellSurvivor hält eine eigene Kopie in `CellSurvivor/bots/core.py`. Das ist das
einzige echte Duplikat des Kerns. Nicht ungefragt migrieren — der Bot läuft produktiv und die Kopie ist
divergiert; Migration nur als bewusster, getesteter Schritt (der Nutzer entscheidet).

## Regel

Vor dem Vorschlag eines anderen Systems / einer anderen Methode ODER dem Bau eines Helpers:

1. `mcp__memory__memory_search` mit Tag `gamebot-framework` prüfen.
2. `_botcore/` mit Grep/Glob durchsuchen.

Existiert eine Funktion die den Bedarf deckt → **wiederverwenden oder erweitern**, nicht neu bauen.

Eine Alternative NUR vorschlagen, wenn ein **konkreter, verifizierter Vorteil** benennbar ist
(gemessen/belegt, nicht Bauchgefühl). Dann: bestehende Lösung weiter nutzen UND die Alternative als
**1-Zeiler-Tradeoff** flaggen (Vorteil + Kosten), der Nutzer entscheidet. **Nie still ersetzen.**

Neue wiederverwendbare Funktion gehört nach `_botcore/` (nicht in einen einzelnen Bot), danach eine
`gamebot-framework`-Memory schreiben (Konvention unten).

## Reuse-first heißt NICHT Kritik unterdrücken

Ehrliches Flaggen einer echt besseren Methode bleibt Pflicht — als geflaggter Tradeoff, nicht als
kommentarloser Umbau. Wenn das Bestehende nachweislich kaputt ist, sag es.

## Capability-Memory-Konvention

Bei jeder neuen/geänderten wiederverwendbaren `_botcore`-Funktion sofort `mcp__memory__memory_store`:

- **Tags:** `gamebot-framework,global` (+ optional Bot-Name)
- **Inhalt:** Funktionsname · Zweck (1 Satz) · Ort (`datei:symbol`) · Signatur · kurze Nutzungsnotiz

Zweck: Nachschlagekanal zwischen den parallel laufenden Bot-Sessions. **Einen Mid-Session-Push gibt es dafür
nicht:** `memory_delta_watch` beobachtet nur den Tag `setup-change` (`WATCH_TAGS`, geprüft 15.11.2026). Neue
Funktionen sehen die anderen Sessions beim nächsten Start (SessionStart-Hook `gamebot_framework_inventory.py`
liest `_botcore` ein) oder per `memory_search` mit Tag `gamebot-framework` vor dem Bauen.

## Parallel-Session-Disziplin (wichtig)

Die drei Bots laufen in **getrennten Sessions gleichzeitig**. Vor einem Edit an einer fremden Bot-Datei
(`idleslayer.py`, `run.py`, `cs_bot.py` einer anderen Session) die Änderungszeit prüfen — ist die Datei
gerade frisch geändert, arbeitet dort jemand. Dann **nicht** editieren, sondern der Nutzer fragen bzw. die
zuständige Session machen lassen. Gleichzeitige Edits zerstören Arbeit.

**Seit 2026-11-13 (der Nutzer, Games\CLAUDE.md v2.2): `_botcore/` ändert nur die Session „Bot_Core“.** Die Bot-Sessions
melden Bedarf dorthin; der Hook `gamebot_core_guard` blockt Edits aus den Bot-Ordnern.

Für `_botcore/` gilt das doppelt: ein Edit dort wirkt auf ALLE drei Bots → Backup + alle Konsumenten
gegenchecken.

## Bot-Neustarts im Konsens (der Nutzer 2026-11-13, 23:29)

„Die Bots sollen sich für Neustarts untereinander absprechen. Wenn alle drei das Okay geben, wird neu gestartet, ohne
jedes Mal meine Bestätigung. Bot_Core kann zustimmen, wenn nötig.“ Eine Bot-Session (Cell Survivor, IdleSlayer_bot,
Survivor.io_Bot) startet ihren **eigenen** Bot ohne der Nutzer neu, wenn alles davon gilt:
1. **Grund:** ein fertiger, gegateter Fix (Selfcheck/Tests grün) oder ein Hänger, der anders nicht zu lösen ist.
2. **Absprache:** Sie schickt den beiden anderen Bot-Sessions `Neustart-Anfrage: <bot> | <grund> | <dauer>`. Beide
   antworten `OK Neustart <bot>` oder `NEIN Neustart <bot>: <grund>` (z. B. laufender Kampf, gemeinsames ADB/Emulator
   gerade belegt). Betrifft der Neustart Startsteuerung, Watchdog-Kette, `_botcore` oder mehr als einen Bot, muss
   zusätzlich **Bot_Core** mit OK antworten.
3. **Ohne alle OKs kein Neustart:** Fehlt eine Antwort nach 10 min oder kommt ein NEIN, MB-Zeile an „Bot_Core“ (leitet an „Setup Server“ weiter).
4. **Nur der Standardweg** (Bot-Prozess beenden, Watchdog startet neu, bzw. `BOTS_RESTART_DETACHED.ps1`), **Fixes
   bündeln** (der Nutzer 16.11.2026, 19:02: „lieber gesammelt mehrere Fixe einspielen und dann 4-mal neu starten, anstatt 10-mal
   neu starten für jeden einzelnen Fix“). Keine feste Obergrenze mehr, auch nachts nicht; Richtwert etwa 4 Neustarts je Bot
   und Tag bzw. Nacht, damit keine Farming-Zeit unnötig verloren geht. Ein fertiger Fix wartet, bis ein zweiter dazukommt
   oder ein Hänger ohnehin einen Neustart verlangt; dringend (Geld-/Kaufrisiko, Bot steht) geht sofort. Läuft der Bot nach
   einem Neustart nicht sauber, kein blinder weiterer Versuch, sondern Ursache klären und MB-Zeile. Frist: 5 min ab dem
   Neustart; beim Weg „nur beenden, Watchdog startet neu“ bis 11 min, weil Watchdog-Prüfung und Log-Altersschwelle je
   300 s brauchen (IdleSlayer 13.11.: 8,5 min, normal).
5. **Ergebnis** in einer Zeile an „Bot_Core“, das es an „Setup Server“ weitergibt; der hakt den Punkt im der Nutzer-Block ab.
**Meldeweg (der Nutzer 2026-11-16, 20:47):** „Bot-Sessions an sich werde ich auch nicht remote machen, weil sie es einfach nicht brauchen. Du [Bot_Core] bist remote und fungierst quasi als Sprachrohr für die drei.“ Die drei Bot-Sessions schicken MB-Zeilen, Ergebnisse und Fragen an Bot_Core, die Zentrale schickt ihre Nachrichten an die Bots über Bot_Core. Neustart-Absprachen laufen weiter direkt unter den drei.
**Bot_Core verwaltet (der Nutzer 2026-11-16, 20:51):** „Du bist quasi die Verwaltung mit für die 3 Gamebot-Sessions. Nur wenn du … das nicht entscheiden kannst … meldest du das Ganze an Setup Server.“ Bot_Core entscheidet Bot-Fragen selbst, wenn alles gilt: umkehrbar, keine Löschung, kein Geld/Premium/Konto, nichts gegen des Nutzers Festlegungen (Picks, Loadouts, Spielweise, objective.json), keine Sicherheit gesenkt. Sonst MB-Zeile an „Setup Server“. An die Zentrale gehen nur erledigte der Nutzer-Aufträge, MB-Punkte und was der Nutzer wissen muss, keine reinen Statusmeldungen.
Gilt auch im Nachtbetrieb. Fremde Bots neu starten, Löschen und `_botcore`-Edits außerhalb von Bot_Core bleiben bei
der Nutzer bzw. Bot_Core.
