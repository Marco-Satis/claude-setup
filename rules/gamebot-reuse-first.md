# Gamebot Reuse-first (Global Rule)

Auto-applied in den Gamebot-Projekten (cellsurvivor / survivorio / idleslayer) und beim loopmode-Betrieb.

## Das geteilte Grundgerüst heißt `_botcore/`

`C:\Users\der Nutzer\OneDrive\Dokumente\Games\_botcore\` — **nicht** `gamebot_core/`.

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

Zweck: async-Kanal zwischen den parallel laufenden Bot-Sessions — die Sessions können nicht live
miteinander reden, aber `memory_delta_watch` pusht neue Memories mid-session in die anderen.

## Parallel-Session-Disziplin (wichtig)

Die drei Bots laufen in **getrennten Sessions gleichzeitig**. Vor einem Edit an einer fremden Bot-Datei
(`idleslayer.py`, `run.py`, `cs_bot.py` einer anderen Session) die Änderungszeit prüfen — ist die Datei
gerade frisch geändert, arbeitet dort jemand. Dann **nicht** editieren, sondern der Nutzer fragen bzw. die
zuständige Session machen lassen. Gleichzeitige Edits zerstören Arbeit.

Für `_botcore/` gilt das doppelt: ein Edit dort wirkt auf ALLE drei Bots → Backup + alle Konsumenten
gegenchecken.
