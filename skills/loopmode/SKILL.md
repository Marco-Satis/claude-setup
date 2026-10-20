---
name: loopmode
description: Aktiviert Loop-Mode für GENAU diese Session (autonome Bot-Operator-Tick-Schleife mit Auto-Fix). Setzt LOOP_RUN.flag, legt einen recurring CronCreate-Antrieb (TICK, ~15min, off-round/pro-Bot gestaffelt) an — CronCreate weil es bei idle REPL feuert (ScheduleWakeup weckt ruhende Session nicht zuverlässig), Context-Nag-Hook für diese session_id aus. Mission — Bot kritisch beobachten, Spielfehler root-causen + fixen, Spielverständnis erweitern. Survivability-first — LOOP_TICK.md hart klein (Guard), Detail ins JOURNAL, sonst stirbt die Session am Kontext. 1 gegateter, verifizierter Fix/Tick (Reviewer-Gate + Delta-Verify + Attempt-Cap). Trigger /loopmode <spiel> mit spiel ∈ cellsurvivor|survivorio|idleslayer. Stoppen mit /loopstop.
---

# /loopmode — Loop-Mode aktivieren (session-scoped, mit Auto-Fix)

Macht GENAU diese Session zur autonomen Operator-Tick-Schleife für ein Spiel. Andere Sessions bleiben unberührt.

**Mission der Session** (kein passiver Health-Pinger): den Bot **kritisch beobachten** → **Spielfehler erkennen** (falsche Nav, false-done/false-win, stuck, dumme Tode, schwache Picks) → **Root-Cause** im Code/Detektor finden (nie Band-Aid) → **fixen** (Auto-Fix-Policy unten) → **Spielverständnis erweitern**, wenn keine Bugs offen sind.

**Survivability ist Regel 1:** die Sessions starben früh, weil `LOOP_TICK.md` zur Kontext-Halde wurde. Der Per-Tick-Read MUSS klein bleiben (Schema unten, OVERWRITE, Guard erzwingt es); alles Detail → `JOURNAL_<dir>.md`. **Pflicht-Read pro Tick sind ZWEI kleine Dateien: `LOOP_TICK.md` UND `WIRING.md`** — Letztere ist der Ledger der absichtlich gebauten/verdrahteten Teile (≤40 Zeilen). Sie überlebt den Auto-Compact, der dir sonst das WARUM zu fertigem Code nimmt (belegt: `_bots_control.py` 2026-06-16 als „unerklärt" entfernt → Cold-Boot startete Bots nicht). `WIRING.md` ist per Definition klein → die Regel „danach NIE wieder die großen Docs pro Tick" bleibt unberührt gültig. Vollzug + harte Regeln stehen in `Games/TICK_PROMPT.md`.

## Argument
`<spiel>` ∈ `cellsurvivor` | `survivorio` | `idleslayer`. Fehlt es → der Nutzer fragen, welches Spiel diese Session betreibt.
Spiel-Dir: cellsurvivor→`CellSurvivor` · survivorio→`Survivor_io` · idleslayer→`IdleSlayer`.
Basis: `C:\Users\<user>\OneDrive\Dokumente\Games\<dir>` (Windows-lokal — Bots/Emulator laufen auf dem PC). **Nicht verwechseln mit dem Syncthing-Folder `games`** (PC-Share → netcup `~/Games`): der zeigt auf einen *anderen* Ordner und enthält global nur 2 Dateien, keinen Bot-Code. Eine netcup-Session kann Gamebot-Arbeit deshalb **nicht** verifizieren — dort immer in der PC-Session nachfragen statt aus einem Nicht-Treffer zu schließen.

## Schritte
1. **Master-Schalter setzen:** schreibe `Games/<dir>/LOOP_RUN.flag` mit aktuellem Zeitstempel. Solange diese Datei existiert, läuft der Loop; `/loopstop` löscht sie.

   **Kontext-Canary scharfstellen (der Nutzer 2026-08-12):** ab jetzt beginnt in dieser Session **jede** Antwort mit `der Nutzer,` — auch Tick-Meldungen. Der Stop-Hook `context_canary.py` liest diesen Marker: solange er da ist, hält die Session ihre Anweisungen; verschwindet er still, meldet der Hook Drift und erzwingt einen Memory-Checkpoint, bevor der Kontext weg ist. Das ist der Sensor gegen die Compact-Amnesie, an der die Gamebot-Sessions bisher Gebautes verloren haben. Der Marker kostet zwei Zeichen pro Antwort — in einer Loop-Session liest ohnehin niemand mit.
   *Nicht verwechseln mit `canary.py <spiel>`* (Schritt 6 der Auto-Fix-Policy) — das misst Bot-Performance gegen Baseline, der Kontext-Canary misst Instruktions-Drift der Session.
2. **Nag-aus (automatisch):** der Hook `context_threshold_warning.py` hat diese `session_id` bereits beim `/loopmode`-Prompt als Loop-Mode markiert (`state/loopmode_sessions.json`) → keine `[CONTEXT-*]`-Stops mehr in dieser Session bis `/loopstop`. Kontext-Management übernimmt der projekt-scopede Auto-Compact (`Games/.claude`).

   **Auto-Compact-Schwelle verifizieren (neu 2026-08-14, natives Sicherheitsnetz):** Die Stufenregel unten bereitet ab 70 % den Übergang vor (HANDOVER.md, DEFERRED.md) — aber den `/compact` selbst kann die Session nicht auslösen, und bei einem 24/7-Loop sitzt der Nutzer oft nicht am PC, wenn die 80-%-Meldung kommt. Deshalb MUSS der native Auto-Compact als Fallback **bei ~85 %** feuern (nach der 80-%-Snapshot-Stufe, vor dem Kontext-Tod). Prüfung bei Aktivierung: existiert in `Games/.claude/settings.local.json` der Eintrag `"env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "85"}`? **Fehlt er → als allererste Zeile der Aktivierungs-Antwort an der Nutzer melden** (eine Zeile, mit fertigem JSON-Schnipsel zum Einfügen — die Session in `Games/` kann die Datei auch selbst anlegen, `settings.local.json` ist maschinenlokal und triggert keinen Workspace-Trust). Alternative für die laufende Session: der Nutzer tippt `/autocompact` (nativ, UI-Ebene). Warum 85 und nicht 60 wie im Discord-Bots-Projekt: der Loop WILL die Stufen 55/70/80 durchlaufen (kontrollierte Übergabe schlägt frühen Blind-Compact); der Override ist die Reißleine dahinter, nicht der Normalweg.

   **Feste Compact-Regel (der Nutzer 2026-07-28) — drei Stufen, nicht verhandelbar:**

   | Context | Stufe | Was gilt |
   |---|---|---|
   | ab **55 %** | `[LOOP-CTX]` | leicht ticken: 1 kleine Aktion/Tick, Tool-Output in Dateien, keine Marathons in einem Turn |
   | ab **70 %** | `[LOOP-DEFER]` | **MONITOR-ONLY.** Erlaubt: Bot-Health (läuft er, Log-Stale, FROZEN/Crash), Kurz-Diagnose aus vorhandenen Logs, 1-Zeilen-State-Save, `WIRING.md`-Eintrag für Fertiges. Verboten: neue Fixes, Root-Cause-Marathons, Refactors, Screenshots, Voll-Logs, große Reads |
   | ab **80 %** | `[LOOP-PRECOMPACT]` | zusätzlich Memory-Snapshot ziehen, dann nur noch winzige Aktionen |

   **Nahtloser Übergang (der Nutzer 2026-07-28):** ab 70 % führt der Tick zusätzlich `Games/<dir>/HANDOVER.md` (OVERWRITE, ~40 Zeilen) — `LAUFENDE ARBEIT` · `HYPOTHESEN` (`[ausgeschlossen]`/`[offen]` + Beleg) · `HALBFERTIG` (datei:symbol + Status) · `NÄCHSTER SCHRITT` (genau eine Aktion) · `MARCO OFFEN` · `BELEGE`. Der Inject-Hook gibt sie nach dem Compact zurück, der erste Tick knüpft dort an. Arbeitsteilung der vier Dateien: `WIRING.md` = was absichtlich gebaut **ist** · `DEFERRED.md` = was bewusst **geparkt** ist · `HANDOVER.md` = wo die Session gerade **mitten drin** steckt · `WIRING_PENDING.md` = welche Dateien vor dem Compact **angefasst** wurden.

   **Compact-Meldung im Tick (der Nutzer 2026-07-28):** ab 70 % beginnt **jede** Tick-Antwort mit `[COMPACT SINNVOLL] Context ~X% — /compact wäre jetzt gut`, ab 80 % mit `[COMPACT BITTE] Context ~X% — bitte /compact ausführen`. Den exakten Wortlaut liefert der Hook mit; die Zeile steht **jeden Tick** da, solange die Schwelle hält, und zählt nicht gegen die 2-Zeilen-Grenze. der Nutzer führt den Compact selbst aus, sobald er sie sieht — die Session kann `/compact` nicht auslösen. Reagiert niemand, greift bei ~85 % der native Auto-Compact (Override aus Schritt 2) — dank der 80-%-Stufe sind Snapshot + HANDOVER.md dann bereits gezogen, der Inject-Hook stellt sie nach dem Compact zurück.

   Ab 70 % wird **jede** Aufgabe — eigene Idee wie der Nutzer-Auftrag — als **eine Zeile** nach `Games/<dir>/DEFERRED.md` geparkt statt begonnen:
   `- [ ] <Aufgabe> | warum | woran erkennbar dass sie erledigt ist`
   Nach dem Compact injiziert `gamebot_wiring_inject.py` die Datei zurück; abgearbeitet wird sie **nach** dem Health-Check, von oben. Erledigtes abhaken (`- [x]`), nicht löschen.
   Zweck: der Nutzer erklärt eine Sache **einmal**. Was geparkt ist, überlebt den Compact — er muss es nicht zum zehnten Mal wiederholen.
   Beim ersten Erreichen von 70 % und 80 % geht **eine** Discord-Nachricht raus (einmal pro Stufe, kein Tick-Spam), weil der Nutzer bei 24/7-Loops nicht am PC sitzt und die Terminal-Warnung nicht sieht.
3. **Auto-Fix ist AN (intrinsisch):** dieser Modus fixt gefundene Probleme automatisch (Policy unten). Opt-out pro Spiel: Zeile `AUTOFIX=off` in `LOOP_TICK.md` → dann nur beobachten/loggen, kein Auto-Edit. Default ohne diese Zeile = AN.
4. **Onboarding nur falls nötig:** fehlt `Games/<dir>/LOOP_TICK.md` oder ist `FOCUS=INIT` → einmalig `START_PROMPT.md` + `GAME_MODEL.md` (Spiel-Verständnis) + `_botcore/LESSONS.md` (Cross-Game-Lektionen) + Pflicht-Docs lesen, erste State im **LOOP_TICK-Schema** schreiben (`TICKN`/`FOCUS`/`NEXT`/`LAST`/`PROGRESS` je 1 Zeile + `OPEN`-Block ≤5 Bullets; Detail/Historie → `JOURNAL_<dir>.md`; `loop_tick_guard.py` hält's klein). **Danach NIE wieder die großen Docs pro Tick** (Minimal-Kontext = lange Loop-Laufzeit).
5. **Cron-Antrieb setzen (NICHT ScheduleWakeup):** `ScheduleWakeup` weckt eine **ruhende** Session nicht zuverlässig (Loop schläft ein wenn die REPL idle ist). `CronCreate` feuert dagegen **während die REPL idle ist** → verlässlicher Loop-Antrieb.
   - **Tools laden:** `ToolSearch` mit `select:CronCreate,CronList,CronDelete`.
   - **Erst prüfen (idempotent):** `CronList` — existiert schon ein recurring `TICK <spiel>`-Job, NICHT neu anlegen (kein Doppel-Antrieb).
   - **Sonst anlegen:** `CronCreate` mit `recurring: true`, `prompt: "TICK <spiel>"`, und dem **off-round + pro-Bot gestaffelten** Cron-Ausdruck für DEIN Spiel (nie :00/:30; jeder Bot eigene Minuten, damit die 3 Loops nicht gleichzeitig feuern):
     - cellsurvivor → `"13,28,43,58 * * * *"`
     - survivorio   → `"8,23,38,53 * * * *"`
     - idleslayer   → `"3,18,33,48 * * * *"`
     (~15-Min-Takt.) Job-ID merken/bestätigen.
   - **Alten One-Shot aufräumen:** falls ein früherer `ScheduleWakeup`/One-Shot-`TICK <spiel>` in `CronList` steht → `CronDelete` (nur der recurring Cron treibt).
   - **Ab jetzt KEIN `ScheduleWakeup` mehr armen** — der Cron treibt jeden Tick.
   - **Grenzen (dem User klar sagen):** Cron ist **session-only** (nicht auf Disk, stirbt wenn die Claude-App/Session ganz schließt — überlebt nur Idle-Phasen), **Auto-Ablauf nach 7 Tagen** (dann neu setzen). Echt-unabhängiger Dauer-Farm bleibt der **Bot-eigene Watchdog** (`BOTS_START.bat` / `loop_watchdog.py`), NICHT der Cron — der Cron treibt nur *Claudes Aufsicht*, nicht den Bot.
6. **Bestätigen** (max 2 Zeilen): „Loop-Mode aktiv für <spiel>, Auto-Fix AN, Nag aus, Cron-Antrieb <job-id> (~15 Min, session-only/7-Tage)."

Ab dann treibt `Games/TICK_PROMPT.md` jeden Cron-Tick. Stoppen jederzeit mit `/loopstop` (löscht `LOOP_RUN.flag`; den Cron zusätzlich via `CronDelete` beenden).

## Werkzeuge & Artefakte (in `Games/_botcore` bzw. Spiel-Dir)
- `loop_observer.py` — Always-on Beobachter: `metrics.jsonl` (Mess-Reihe) + `incidents.jsonl` (Anomalie-Queue, inkl. **`drift`** = Detection-Fail-Rate-Spike = Spiel-Update-Verdacht); `--scan`/`--report`/`--ack`/`--watch` (Overnight).
- `canary.py` — Auto-Revert nach Fix bei Metrik-Regression (Watchdog-Lektion: Recovery ohne Eskalation kann zerstören).
- `host_guard.py` — `rotate <spiel>` (Log-Rotation > 15MB) + `check` (Disk/Emulator-RAM/Log-Größe → `HOST_WARN.flag`).
- `digest.py` — Eskalations-Queue (`decide`/`decisions`/`resolve`, Dinge die der Nutzer entscheiden muss) + `digest` (Tagesreport, inkl. Objective-Fortschritt).
- `experiment.py` — A/B-Strategie-Test (Metrik entscheidet, Bot liest `ab_active.json`) statt Hunch.
- `change_budget.py` — max N Auto-Edits/Tag + Spend-Guard (Premium/Gems nie autonom).
- `self_audit.py` — Meta-Tick: eigene Fix-Erfolgsrate + Whack-a-Mole-Erkennung.
- `postmortem.py` — bei Tod/Run-Verlust Aktions-Sequenz davor offline analysieren → Todes-Muster → Fix-Hypothese.
- `objective.json` (Spiel-Dir) — North-Star pro Spiel; ohne Ziel ist „effektiv" undefiniert.
- `loop_tick_guard.py` — hält `LOOP_TICK.md` klein (Overflow → JOURNAL).
- `selfcheck.py` — Gate inkl. **data-driven Regression-Net** (`<dir>/regression_assertions.json`).
- Wissen: `GAME_MODEL.md` (Spiel-Verständnis, verfeinern) · `_botcore/LESSONS.md` (Cross-Game) · `fehler-ledger.json` (Bug-Wahrheit) · `JOURNAL_<dir>.md` (Historie).

## Auto-Fix-Policy (was der Loop selbst repariert)
Der Tick wählt pro Wake GENAU EINE Aktion. Ist ein Problem offen, ist diese Aktion **ein Fix-Versuch** dafür — gegated, verifiziert, gedeckelt. Vollzug steht in `TICK_PROMPT.md` (ABLAUF Schritt 5–6).

**Problem-Quellen (Priorität absteigend):**
1. `diagnose.py` health-kritisch (Bot DEAD / blackscreen / RAM-Spike / stuck) → Betrieb zuerst: `diagnose.py --heal`. Höchste Prio.
2. `fehler-ledger.json` Einträge mit `fix_status` = `offen` oder `reopened`, nach Severity sortiert.
3. `selfcheck.py` / game-automation-reviewer Findings → erst als **VERIFIZIERTEN** Ledger-Eintrag erfassen (Beleg-Pfad), dann wie #2 behandeln.

**Fix-Ablauf (1 Problem pro Tick):**
1. Top-offenes Problem nach Priorität wählen.
2. **Backup vor Edit:** `cp -a <file> <file>.bak.autofix.$(date +%s)` (revertierbar).
3. EINE minimale **offline** Code-Änderung (greift beim nächsten Loop-Reload). Nie mid-combat-Live-State editieren; Screencap nur in Lobby.
4. **Gate vor Übernahme:** `selfcheck.py` + game-automation-reviewer müssen grün sein (keine Regression). Output in Datei, 1 Zeile zurück. Rot → Edit verwerfen (Backup zurückspielen), Versuch zählt als Fehlversuch.
5. Ledger-Status `offen` → `behoben_pending_deploy` + **`canary`-Block** setzen (`deploy_ts`, `metric` aus `metrics.jsonl`, `baseline`, `direction` up/down, `backup`-Pfad, `target`-Pfad).
6. **Verify nächster Tick (Canary):** `python canary.py <spiel>` misst gegen Baseline → besser/gleich = `behoben_validiert`, schlechter = **auto-REVERT** (Backup zurück) + `reopened`. Bei `behoben_validiert`: **Regression-Assertion** an `<dir>/regression_assertions.json` anhängen (`must_absent`/`must_present` → `selfcheck.py` schützt dauerhaft gegen Rückfall). „Done" nur mit Diff + Reload + gemessenem Delta.
7. **Attempt-Cap (= Ledger `eskalation_schwelle_S`, Default 3):** nach 3 Fehlversuchen → Status `BLOCKED`, `python ~/.claude/scripts/problem.py add --severity MEDIUM --project games-<spiel> --source loopmode-autofix --title "<kurz>" --fix "<konkret>"`, NICHT weiter retryen → nächstes Problem.

**DEPLOY = Bot KILLEN, NIE bg-launchen (Prozess-Hygiene — Pflicht, der Nutzer 2026-07-15):** Eine Code-Änderung greift erst beim Bot-**Neustart**. Den Neustart macht **der detached Watchdog** (`watchdog.py`/`loop_watchdog.py`, von `BOTS_START.bat` gestartet, `restart_bot` nutzt `DETACHED_PROCESS`). Der Operator **killt NUR den alten Bot-Prozess** (`psutil` `terminate`, gefiltert auf `name=='python.exe'/'pythonw.exe'` + Script-Basename, eigene pid aus) — der Watchdog respawnt ihn binnen ~180s **detached** mit neuem Code.
- **NIEMALS** den Bot selbst per `run_in_background`/Bash-bg **starten**. Ein so gestarteter Bot ist ein **KIND der claude.exe** → hält die Session offen → **blockiert Claude-Updates/-Neustart** (Windows-File-Lock auf die laufende claude.exe; verifiziert 2026-07-15: `run.py`/`cs_bot` als Claude-Kind hingen die Updates). Symptom für der Nutzer: „will Claude updaten, hängt, erst nach Kill aller Bots gehts."
- **Kein Watchdog aktiv** (pid-Check leer)? → im `LAST` für der Nutzer flaggen („`BOTS_START.bat` doppelklicken") — **NICHT** selbst bg-launchen. Lieber Bot kurz aus als ein Claude-Kind-Bot.
- Gilt auch für den **Emulator/das Game**: nach Reboot NICHT aus Claude relaunchen wenn vermeidbar — Watchdog/`BOTS_START.bat`. Details: mcp-memory `4313aaa6`.

**NIEMALS auto-fixen (→ nur Ledger + `problem.py` + im LAST für der Nutzer flaggen, KEIN Auto-Edit):**
- Destruktiv/irreversibel: Daten/Saves löschen, Schema-Migration, Multi-File-Refactor (> 2 Files).
- Außerhalb `Games/<dir>` bzw. `Games/_botcore` (z.B. `~/.claude`-Config, andere Projekte).
- Secrets/Credentials, Netzwerk/Firewall, Account-/Device-Settings.
- Unklare Root-Cause / keine VERIFIZIERTE Signatur → erst diagnostizieren, nie blind patchen (Ledger-Regel: nur verifizierte Fehler).

**Protokoll:** jeder Auto-Fix → Detail an `JOURNAL_<dir>.md` anhängen (Datei) + 1-Zeilen-`LAST` in `LOOP_TICK.md` + **bei einem fertigen/verdrahteten Teil eine Zeile in `WIRING.md` (Zustand, nicht Historie: `SYMBOL | Datei | verdrahtet in | Grund`)** — sonst entfernt ein späterer Tick den Code als „unerklärt". Kein Chat-Dump (Loop-Disziplin).
