---
name: review
version: 4.6.0
last-reviewed: 2026-08-13
description: Multi-Agent Projekt- und Code-Review-Orchestrator. Prueft NICHT nur Bugs, sondern das Projekt als Ganzes — Code-Achsen A-D (Correctness, Control-Flow, Data-Flow, Blast-Radius) PLUS Projekt-Achsen E-J (Architektur/Duplikate, Doku- und Instruktions-Drift, Config/Env/Deploy, Repo-Hygiene, Betrieb/Beobachtbarkeit, Ziel-Abgleich) mit mechanischem Vorlauf vor jeder Modell-Bewertung. Weiter mit Session-Gate-Scope (erstes Review der Session = alles zum Session-Thema, NICHT ganzes Repo; danach inkrementell seit letztem Review + Re-Check der Vorbefunde), Git-Hunk-genau mit mtime-Fallback, echtem Sub-Agent-Dispatch + Inline-Fallback, sprach-bewusstem SAST-Routing (Python/PowerShell/JS/Shell), Regression-Tagging via mcp-memory-service, kritisch-ehrlichem Findings-Format ohne Whitewashing, strukturierter findings.json als Single-Source-of-Truth, Pflicht-Self-Review-Loop (Phase 5.5) + Adversarial False-Negative-Pass (Phase 5.6) gegen Uebersehene, Functional-Logic-Flow-Audit (Phase 4.5, Achsen A-D), Fix-Verification-Loop (Phase 7) UND einer Selbstlern-Schleife (Phase 0 Recall + Phase 6.5D Outcome-Ledger + woechentliche Meta-Evolution) die aus verifizierten Outcomes lernt — wiederkehrende False-Positives runterstuft, chronische Hotspots priorisiert, frueher uebersehene Bug-Klassen gezielt prueft.
when_to_use: projekt review / komplettes projekt untersuchen (Scope `projekt` = ganzes Repo, Code-Achsen A-D + Projekt-Achsen E-J), code review (session-bewusst — ERSTES Review der Session scannt alles was zum Session-Thema gehoert (angefasste/besprochene Files, NICHT das ganze Repo — dafuer `all`), jedes weitere nur die Aenderungen seit dem letzten Review + Re-Check ob die Vorbefunde noch existieren), pr review, pre-commit review, session-diff-review, regression check, kritischer review der letzten Aenderungen, /review (fuer Quartals-Audit der gesamten Codebase nutze full-audit)
argument-hint: Optional Scope-Override ("projekt"/"all" = ganzes Projekt inkl. Achsen E-J | "setup" | "discord" | "footstep" | "--since YYYY-MM-DD" | "<pfad-glob>") oder Flags "--projekt" (Achsen E-J auch bei kleinem Scope erzwingen) / "--no-projekt" / "--no-council" (Council-Trigger C1-C5 abschalten; Default ist AN) / "--council" (zusaetzlich die teure Deliberation erlauben) / "--no-loop" / "--no-memory" / "--no-graph" / "--no-problems" / "--no-learn" / "--verify-fixes"
allowed-tools: Read Bash Glob Grep Write Edit Agent
userInvocable: true
model: opus
---

# Review — Multi-Agent Projekt- & Code-Review-Orchestrator v4.6.0

> **Zwei Achsen-Familien (v4.5):** **A-D** fragen „ist dieser Code kaputt?" (Phase 4.5) · **E-J** fragen „ist dieses Projekt in Ordnung?" (Phase 4.6 — Architektur, Doku-Wahrheit, Config/Deploy, Hygiene, Betrieb, Ziel-Treue). Ein Projekt kann bugfrei und trotzdem verrottet sein. Welche E-J laufen, entscheidet das Gating in Phase 1E; `/review projekt` fahrt alle.

> **Was diesen Skill anders macht:** Git-Hunk-genauer Scope, Confirmation-Bias-Schutz durch verbotene Anti-Patterns, Regression-Tracking ueber Sessions, **zwei gegenlaeufige Skeptiker-Paesse** — Phase 5.5 widerlegt Falsch-Positive, Phase 5.6 jagt Uebersehene (False-Negative) — plus sichtbarer Iteration-Trace, `findings.json` als eine Wahrheitsquelle, ein Fix-Verification-Loop der angewendete Fixes funktional gegenprueft, und eine **Selbstlern-Schleife** (Phase 0 Recall ← verifizierte Outcomes) die den Skill mit jedem Review schaerfer macht ohne den Kern aufzublaehen.

---

## KANON — gemeinsame Referenzen (einmal definiert, ueberall referenziert)

Alle Phasen verweisen hierauf statt zu duplizieren. Aenderung hier wirkt skill-weit.

### K1 — Severity-Skala · K2 — Severity-Anker · K3 — Anti-Patterns

**Kanonische Quelle: [`~/.claude/skills/_shared/severity-anchors.md`](../_shared/severity-anchors.md)** (v4.1 — Audit-Fund M1). Dort definiert, von allen Review-Skills geteilt:
- **K1** = Severity-Skala (CRITICAL/HIGH/MEDIUM/LOW/INFO)
- **K2** = Severity-Anker fuer Code-Befunde (die EINE Kalibrier-Liste — „Hardcoded Pfad=MEDIUM", „Bare-except in Persistence=HIGH", „Duplicate-Install nie LOW" usw.)
- **K2p** = Severity-Anker fuer die **Projekt-Achsen E-J** (Phase 4.6) — Architektur/Duplikate, Doku-Drift, Config/Env/Deploy, Repo-Hygiene, Betrieb, Ziel-Abgleich. Nur lesen wenn Phase 4.6 aktiv ist (Gating siehe dort).
- **K3** = verbotene Anti-Patterns (Kraft-Adjektive, Scores, Production-Ready-Behauptung …)

Vor Phase 5 die Datei einmal lesen (1 Read). **Recalibration NUR dort** — kein Cross-Skill-Drift. Phasen referenzieren weiter „K1/K2/K3" = die jeweilige Section dieser Datei.

### K4 — Sprach-bewusstes SAST-Tool-Routing (v4.0)

Pro geaenderter Datei das passende Tool. Verfuegbarkeit in Pre-Flight pruefen; fehlt eins → Notiz "Tool X fehlt fuer .Y-Files", degraded weiter. Python ist nicht der einzige Stack — PowerShell-Hooks + JS-Viewer wurden bisher von KEINEM Tool geprueft.

| Ext | Tool | Findet u.a. |
|---|---|---|
| `.py` | bandit · semgrep · pytest | CWE, subprocess, eval, fehlende Tests |
| `.ps1` `.psm1` | PSScriptAnalyzer (`Invoke-ScriptAnalyzer`) | Invoke-Expression, plaintext-Creds, unsichere Pfade |
| `.js` `.ts` `.mjs` | eslint (oder `npx biome lint`) | XSS, eval, innerHTML, prototype-pollution |
| `.sh` `.bash` | shellcheck | Quoting, Word-Splitting, unsichere Globs |
| `.json` `.yaml` (Config) | manuell + secret-scan | Hardcoded Secrets, fehl-konfigurierte Permissions |

Kein Tool fuer eine Sprache vorhanden → manuelle Achsen (K2/K3 + Phase 4.5) gelten trotzdem, Notiz im Report.

### K5 — Run-Budget (Hard-Backstops, v4.0)

| Grenze | Wert | Bei Ueberschreitung |
|---|---|---|
| pro Reviewer | 15 min | Reviewer abschliessen, Rest als Coverage-Luecke notieren |
| Self-Review-Loop gesamt | ~70k Token / 3 Iter | letzte stabile Iteration ausgeben (Convergence `cap`/`explosive`) |
| Gesamt-Run (alle Phasen) | ~250k Token **soft** | bei Annaeherung: Graphify (6.5B) skippen, dann Projekt-Achsen auf den mechanischen Vorlauf reduzieren (Schritt 1 laeuft immer — kostet fast nichts), dann Sub-Agent-Zahl reduzieren, der Nutzer informieren |
| Projekt-Achsen (4.6) gesamt | ~50k Token | Modell-Bewertung fallen lassen, mechanischen Vorlauf + delegierte Skills behalten, Rest als Coverage-Luecke |
| Council (K6) | **max 3 Einzel-Mitglieder** ≈ 4,5k | Prioritaet C4 > C1 > C5 > C3 > C2; Rest als „getroffen, Deckel" tracen. `/council`-Deliberation zaehlt separat und feuert nie automatisch |
| Wall-Clock Gesamt | ~25 min **soft** | laufende Phase beenden, Report mit Teil-Coverage liefern statt abbrechen |

Bei `all`-Scope + grossem Diff: Budget VORHER schaetzen, bei Risiko der Nutzer warnen (Teil-Scope vorschlagen) bevor der Fan-Out startet. Modell misst eigene Token nicht exakt → Output-Laenge/Wiederholung als qualitatives Signal.

### K6 — Council-Kopplung (v4.5, opt-in)

Das `council`-Plugin (`council@council-of-high-intelligence` v1.2.0, 18 Mitglieder, auf netcup aktiv) ist ein **Deliberations-Mechanismus fuer Urteils-Gabelungen** — nicht fuer Bug-Suche. Ein `.sync-conflict`-File braucht keinen Rat von Sokrates; `grep` findet es, K2p bewertet es. Council lohnt genau dort, wo der Review **urteilen statt messen** muss.

**Default: AN, trigger-gebunden** (der Nutzer-Entscheid 2026-08-02: „soll aktiv bleiben aber aktiv verdrahtet werden"). Kein Vorschlagen, kein Nachfragen — **die Trigger unten feuern selbst**, immer auf dem billigen Einzel-Mitglied-Pfad (~1,5k, Preisklasse eines normalen Reviewers). Kill-Switch `--no-council`.

Die teure Deliberation (`/council`, ~21-23k) feuert **nie automatisch** — die startet nur `--council` oder der Nutzer direkt. Ein Review darf sich selbst eine Perspektive holen; einen Rat einberufen darf es nicht.

### Feuer-Bedingungen (das ist die Verdrahtung)

Jede Zeile ist eine **harte Bedingung auf einem bereits vorliegenden Befund** — nie „bei Bedarf", nie nach Ermessen. Kein Treffer = kein Council-Call, das ist der Normalfall bei kleinen Reviews.

| # | Feuert wenn | Mitglied | Auftrag |
|---|---|---|---|
| C1 | Achse E fand ein **divergiertes Duplikat** ODER einen God-File-Kandidaten >1000 LoC mit ≥5 Verantwortlichkeiten | `council:council-feynman` | „Ist das ein Defekt oder eine bewusste Vereinfachung? Belege mit file:line." |
| C2 | Achse J fand ein **dokumentiertes Feature ohne Code** ODER Code ohne jeden Aufrufer | `council:council-torvalds` | „Ausbauen, entfernen oder Doku korrigieren — was ist billiger?" |
| C3 | Achse I fand einen Dienst/Timer **ohne Log, Notify und Watchdog** | `council:council-taleb` | „Welcher Ausfall dieses Dienstes ist der teure Tail?" |
| C4 | Phase 5.5 machte **≥3 Severity-Adjustments** ODER hat ≥2 HIGH mit `confidence` < 0,7 | `council:council-kahneman` | Auf die **Findings-Tabelle**, nicht auf den Code: „Wo hat der Review sich selbst getaeuscht — Anchoring, Availability, Confirmation?" |
| C5 | Phase 5.6 meldet `clean` **bei Diff > 200 geaenderten Zeilen** | `council:council-socrates` | „Ein sauberer FN-Pass auf einem grossen Diff ist verdaechtig — finde die Annahme, die alle Reviewer geteilt haben." |

**Budget-Deckel: max 3 Einzel-Mitglieder pro Run** (~4,5k, ≈2 % von K5). Mehr Treffer als 3 → nach dieser Reihenfolge priorisieren: C4 > C1 > C5 > C3 > C2. Begruendung fuer C4 zuerst: ein verzerrter Report macht alle anderen Befunde unzuverlaessig. Weggefallene Trigger im Trace nennen („C2, C3 getroffen, wegen Deckel nicht gefahren").

**Trace-Pflicht** in der Master-Section „Council": pro Trigger `gefeuert (Mitglied, Ergebnis) | getroffen aber Deckel | nicht getroffen`. Ein Council-Schritt ohne Trace-Zeile gilt als nicht gelaufen.

| Ankerpunkt | billig: **1 Mitglied** (~1,5k) | teuer: **Deliberation** (~21-23k) | Frage die beantwortet wird |
|---|---|---|---|
| **Phase 4.6 Achse E** (Architektur) | `council:council-feynman` (refuses unexplained complexity) | `--triad architecture` (Aristotle+Ada+Feynman) | „Ist diese Struktur ein Defekt oder eine bewusste Vereinfachung?" — macht aus einem God-File ein Finding oder ein Nicht-Finding |
| **Phase 4.6 Achse J** (Ziel-Abgleich) | `council:council-torvalds` (YAGNI, ship-or-shut-up) | `--triad design` (Rams+Torvalds+Watts), `--duo` bei genau 2 Optionen | „Soll das Projekt das ueberhaupt tun?" — Watts loest Schein-Probleme auf, Torvalds killt tote Features |
| **Phase 5.5** (Severity-Kalibrierung) | `council:council-kahneman` („your own thinking is the first error") | `--triad bias` (Kahneman+Socrates+Watts) | „Wo hat sich der Review selbst getaeuscht?" — Kahnemans Achse **ist** der dokumentierte Fehlermodus dieses Skills |
| **Phase 5.6** (FN-Pass) | `council:council-socrates` (Annahmen zerlegen) | `--profile exploration-orthogonal --triad blind-spots` (Kahneman+Meadows+Socrates) | „Welche Fehlerklasse hat niemand gesucht?" — ergaenzt den Cross-Model-Skeptiker |
| **Achse I** (Betrieb) | `council:council-taleb` (Tail-Risk) | `--triad systems` (Meadows+Lao Tzu+Aristotle) oder `uncertainty` (Taleb+Sun Tzu+Sutskever) | „Welche Rueckkopplung fehlt, welcher Ausfall ist der teure Tail?" |

Die mittlere Spalte ist der Default. Die rechte nur, wenn die Antwort **strittig** ist — dann traegt das Kreuzverhoer den Preis.

### Kosten-Stufen — erst der billigste Weg, der die Frage beantwortet

Die Analyse vom 2026-07-28 (`plugin details`) ergab drei sehr unterschiedliche Preisklassen. **Die teuerste ist selten die noetige:**

| Weg | Kosten | Wann |
|---|---|---|
| **Einzelnes Mitglied als Sub-Agent** — `Agent(subagent_type: "council:council-kahneman", ...)` | **~1,4-1,9k** | Der Normalfall im Review — **wenn verfuegbar, siehe Gate unten.** Die Agents sind plugin-namespaced (kein `install.sh`, `~/.claude/agents/` unberuehrt) — eine Perspektive kostet damit weniger als ein normaler Reviewer-Sub-Agent. |
| `/council --duo` / `--triad` / `--quick` | ~21-23k (Skill-Overhead allein 18,7k) | Nur wenn die **Deliberation** gebraucht wird: Blind-Runde → anonymisiertes Kreuzverhoer → finale Position → Synthese. Das ist der Mechanismus, fuer den der Overhead bezahlt wird. |
| `/council --full` | ~47k | **Nie in einem Review.** Ein Fuenftel des K5-Gesamtbudgets fuer eine Meinung. |

Faustregel: **eine Perspektive → Einzel-Agent. Ein Streit → `/council`.** Der Skill-Overhead lohnt erst, wenn Widerspruch zwischen Mitgliedern der Punkt ist.

**Verfuegbarkeits-Gate (Pflicht, vor jedem Council-Schritt).** Plugin *installiert* heisst nicht Agents *dispatchbar* — **Plugin-Agents registrieren sich beim Session-Start**. Am 2026-08-02 war `council@council-of-high-intelligence` v1.2.0 aktiv und die 18 Agent-Dateien lagen valide im Cache, in der Agent-Liste der laufenden Session stand aber kein `council:*`: die Session lief seit dem 25.07., das Plugin kam am **28.07. 09:11** dazu (alle anderen Plugins: 14./21.07. — die waren gelistet). **In einer frisch gestarteten Session sind die Agents da.** Zusaetzlich ist der Zustand pro Maschine verschieden, weil `settings.json` und `/plugins` nicht syncen.

Deshalb in dieser Reihenfolge, ohne Hard-Fail:

1. **Agent-Liste der laufenden Session pruefen** — steht `council:council-<name>` drin? Ja → billiger Einzel-Agent, fertig.
2. Nein, aber der `council`-Skill ist invocable → `--quick --members <name>` (traegt den Skill-Overhead, liefert dieselbe Perspektive).
3. Beides nicht da → **Council-Schritt entfaellt**, Trace-Notiz „Council nicht verfuegbar (Agents nicht gelistet / Skill nicht invocable)". Der Review laeuft unveraendert weiter — K6 ist Bonus, nie Voraussetzung.

**Nie raten und nie behaupten.** Ein Council-Schritt, der im Report auftaucht, muss wirklich gelaufen sein (Frischer-Beweis-Regel, Phase 7).

(Nebenkosten, nicht Review-spezifisch: das Plugin kostet **~892 Token always-on pro Session** — auch in den Loopmode-Bot-Sessions, in denen nie ein Council tagt.)

**Harte Regeln — sonst wird es Theater:**

1. **Nie `--full`**, max **1** `/council`-Aufruf pro Review (bei `projekt`-Scope max 2). Zaehlt gegen K5. Einzel-Mitglieder als Sub-Agent sind davon nicht betroffen (Preisklasse eines normalen Reviewers).
2. **Was den Council wertvoll macht, ist das Protokoll — nicht die Figur.** Die Pruefung 2026-07-28 ergab: kein Persona-Cosplay, sondern Blind-Runde vor Kreuzverhoer (Anti-Anchoring, dieselbe Logik wie die kuratierten Reviewer-Prompts in Phase 2) plus ein **Enforcement-Scan gegen „premature agreement, repeated claims, missing dissent, unsupported confidence"**. Genau deshalb einsetzen — und deshalb auch **nie das Protokoll abkuerzen** (kein „ich frage schnell im Stil von X", das ist die wertlose Variante).
3. **Evidenz-Labels uebernehmen, nicht uebersetzen.** Der Council labelt jede Aussage `FACT` / `INFERENCE` / `ASSUMPTION` / `UNKNOWN`. Das mappt direkt auf das bestehende `confidence`-Feld und damit auf das Skeptiker-Routing aus Phase 5.5: **FACT → ≥0,9 · INFERENCE → ~0,6 · ASSUMPTION → ≤0,4 · UNKNOWN → kein Finding, sondern eine Coverage-Luecke.** Ein `ASSUMPTION`-Befund geht damit automatisch durch den FP-Filter — das ist keine zusaetzliche Regel, sondern das v4.0-Confidence-Routing, das hier endlich echte Labels bekommt statt geschaetzter Zahlen.
4. **Council-Output zaehlt nur mit `file:line` und pruefbarer Aussage.** Ein Urteil ohne Verortung ist eine Meinung — verworfen, nicht paraphrasiert. K3 gilt unveraendert.
5. **Der Council setzt keine Severity.** Er liefert „Defekt ja/nein + warum"; die Einstufung kommt aus K2/K2p. Fremde Skalen nicht uebernehmen.
6. **Council-Befunde gehen durch den 5.5-FP-Filter** wie Cross-Model-Befunde, markiert `[council:<panel>]`.
7. **Uneinigkeit ist das Ergebnis, nicht die Panne.** Das Council-Verdikt **fuehrt mit dem Ungeloesten** und gibt einen gespaltenen Vote als Split zurueck. Diesen Split **so uebernehmen** — als INFO-Finding „zwei vertretbare Lesarten: <A> vs <B>, der Nutzer entscheidet". Zu einer Empfehlung glaetten waere genau das, was der Enforcement-Scan des Councils verhindern soll.

**Cross-Provider-Bonus:** der Council auto-routet Mitglieder auf verfuegbare Provider (anthropic/openai/google/ollama/nim, `configs/auto-route-defaults.yaml`). Sind fremde Provider detektiert, liefert ein Council-Pass **mehrere Modell-DNAs in einem Aufruf** — dann ist er in Phase 5.6 dem einzelnen `cross_model_skeptic.py`-Aufruf ueberlegen. **Vorher `--dry-route`** (kostet nichts, druckt nur die Verteilung): laeuft alles auf Anthropic, entfaellt der DNA-Vorteil und der billigere Einzel-Skeptiker genuegt.

**Projekt-Pinning:** ein Repo kann `.council.yaml` (Keys `profile`, `triad`, `chairman`, `members`) im Root ablegen; der Council liest sie vor CLI-Defaults. Fuer Repos mit wiederkehrender Gabelung sinnvoll — im Review nur nutzen, nicht anlegen (Review ist read-only).

---

## Pre-Flight-Checks

Vor allem anderen. Bei Fail: im Output dokumentieren, degraded weitermachen.

| # | Check | Pass | Fail |
|---|-------|------|------|
| 1 | Git-Repo? `git -C <root> rev-parse --is-inside-work-tree` | **Git-Diff-Scope (Phase 1A) aktiv** | mtime-Scope (Phase 1B) |
| 2 | Worktree verschachtelt (`<repo>/.claude/worktrees/...`)? | Sub-Agents nutzbar | Inline-Fallback, Notiz "Reviewer-Failures" |
| 3 | Memory-Service: `curl -s ${MCP_MEMORY_BASE_URL:-http://10.0.0.x:8000}/api/health` (Netcup-Primary) | Regression-Tagging aktiv | Skip + Notiz "Memory offline" |
| 4 | SAST-Tools je Sprache (K4): `bandit --version`, `pip show semgrep`, `detect-secrets --version`, `Get-Command Invoke-ScriptAnalyzer`, `npx eslint -v`, `shellcheck -V` — nur fuer im Diff vorkommende Sprachen pruefen | tool-augmentiert | Notiz welche Tools je Sprache fehlten |
| 5 | Concurrent-Lock: `~/.claude/reports/review/.review_lock`? | Lockfile (PID, atomic) anlegen | lebt anderes PID → abort, der Nutzer informieren |

**Lockfile:** `~/.claude/reports/review/.review_lock`, Inhalt `<PID>\n<TS>\n<SCOPE>`. Am Ende loeschen.

---

## Phase 0 — Recall (Selbstlern-Schleife, v4.1)

Bevor du den Scope ermittelst: die eigene Review-Historie zurueckrufen, damit der Review aus vergangenen **verifizierten** Outcomes lernt. Eine Zeile:

```bash
python ~/.claude/scripts/review_learn.py recall --files "<scope-basenames,komma>" --axes "security,quality,flow-A,flow-B,flow-C,flow-D,test,perf,async,audio,dep,arch,docs,config,hygiene,ops,goal"
```

Liefert JSON mit 3 Signalen — jedes fliesst in eine spaetere Phase ein:

| Signal | Wirkung |
|---|---|
| `fp_downrank` | In **Phase 5.5**: genannte Muster NICHT blind HIGH — **runterstufen + flaggen** (nie silent-drop), Sample behalten. Reduziert wiederkehrende False-Positives. |
| `hotspots` | In **Phase 1/5**: chronische Dateien priorisieren, im Master als „chronischer Hotspot (N Reviews)" + Refactor-Hinweis markieren. |
| `blindspots` | In **Phase 2 Reviewer-Prompts + Phase 5.6**: gezielten Check fuer die frueher uebersehene Bug-Klasse injizieren — schliesst genau die Luecke die der FN-Pass fand. |

`have_history: false` / leer (erster Run) → kein Signal, normal weiter. Pflicht-Trace im Master-Section **„Recall (gelernt)"**: welche Signale aktiv waren und wo sie wirkten (auch „keine Historie" explizit). Die gelernte Schicht (`review_learned.json`) ist DATEN — der Kern-Skill bleibt stabil.

---

## Phase 1 — Scope-Ermittlung

### Phase 1.0 — Session-Gate (v4.3, ENTSCHEIDET ZUERST)

**Default-Regel (der Nutzer 2026-06-16):** erstes Review der Session = **alles was zum Thema der Session gehoert** (THEMA-Scope — angefasste/besprochene Files, **NICHT das ganze Repo**); jedes weitere Review der Session = nur was **seit dem letzten Review** geaendert wurde **+ Re-Check der Vorbefunde** (Phase 1D).

1. `session_id` bestimmen: aus `transcript_path`-UUID ODER neuester `*.jsonl` (mtime) in `~/.claude/projects/<projekt-slug>/`.
2. **Session-Marker** `~/.claude/reports/review/.chat_review_marker.json` laden — Map `{ "<session_id>": {"ts":"<iso>","sha":"<git-sha|null>","findings":"<pfad zu findings.json|null>"} }`. Key = `session_id`:
   - **NICHT vorhanden → Modus THEMA** (erstes Review der Session): Scope = alles was die Session angefasst/besprochen hat — (1) `file_path` aus Edit/Write/NotebookEdit-Tool-Calls des Transcripts (`transcript_path`), (2) explizit im Chat genannte Pfade, (3) Domain-Fallback (Files mit `mtime` seit Session-Start) wenn Transcript leer. Dedupe → Exclude. **Nicht das ganze Repo** — nur das Session-Thema (fuer repo-weit gibt es Override `all`). >100 Files → Groessen-Warnung + Gruppierung + Bestaetigung.
   - **vorhanden → Modus INKREMENTELL** (Review lief schon in dieser Session): nur Aenderungen seit `marker.ts`/`marker.sha` (Mechanik 1A/1B) **+ Phase 1D Re-Verify der Vorbefunde** (aus `marker.findings`).
3. **Explizites Override schlaegt das Session-Gate** (`all` = ganzes Repo · `setup`/`discord`/`footstep`/`--since`/`<glob>`) → genau dieser Scope, Gate ignoriert.

### Phase 1A — Git-Diff-Scope (INKREMENTELL-Mechanik, wenn Git-Repo)

Der THEMA-Scope (erstes Review) kommt aus Phase 1.0 (transcript-getrieben, ganze Dateien). 1A/1B liefern nur die Mechanik fuer den INKREMENTELL-Modus (Folge-Reviews) — praeziser als mtime, echte geaenderte **Hunks**:

1. **Diff-Quelle** (erste passende): uncommitted Arbeit (`git status --porcelain` nicht leer) → `git diff HEAD` (staged+unstaged) + untracked Files; sonst (sauberer Tree) → `git diff <marker.sha>..HEAD` (Aenderungen seit letztem Review-SHA; fehlt der SHA → `git diff HEAD~5..HEAD` als grobes Fenster, Hunk-Ledger filtert).
2. **Hunks extrahieren:** `git diff <range> --unified=0` → pro File geaenderte Zeilen-Ranges (`@@ -a,b +c,d @@`) = Hunk-Liste fuers Ledger (1C).
3. **Scope-Files** ∪ explizit im Chat genannte Pfade.
4. Fallback auf 1B wenn `git diff` leer obwohl Aenderung erwartet (z.B. nur in `~/.claude`, nicht das aktive Repo) — beide Roots mergen.

### Phase 1B — mtime-Scope (INKREMENTELL-Mechanik, kein Git / Git leer)

Roots: `~/.claude/`, `<projekt>/.claude/`, `<projekt>/`. Files mit `mtime > marker.ts` unter den Roots + Phase 1D Re-Verify. (THEMA-Scope des ersten Reviews kommt aus Phase 1.0, git-unabhaengig.)

> Begruendung (der Nutzer 2026-06-16): „alles scannen" = **alles was zum Thema der Session gehoert** (angefasste/besprochene Files), NICHT das ganze Repo. Erstes Review deckt das ganze Session-Thema ab (nichts vom Thema faellt durch); danach nur noch das Delta seit dem letzten Review + Re-Check ob die alten Befunde noch existieren (Phase 1D). Fuer repo-weit gibt es das explizite Override `all`.

**Exclude (immer):** `.bak.*`, `~/.claude/projects/`, `node_modules`, `__pycache__`, `*.pyc`, venv, `~/.claude/plugins/cache/`, `~/.claude/plugins/marketplaces/`, `_dist_*`, `graphify-out/`, `*.bak.pre-*`.

### Phase 1C — Hunk-Coverage-Ledger (v4.0)

"Datei reviewed" ≠ "Zeile 40-58 geprueft". Jeder geaenderte Hunk MUSS am Ende einen Status haben — verhindert hand-waving Coverage.

- Aus Phase 1A die Hunk-Liste uebernehmen (`file:start-end`). Kein Git → grobe Granularitaet (ganze geaenderte Datei = 1 Pseudo-Hunk).
- Jeder Hunk bekommt am Review-Ende genau einen Status: `reviewed-clean` | `finding (F<id>)` | `skipped (<grund>)`.
- Landet als Tabelle in `findings.json` (`hunk_ledger`) + Master-Section "Hunk-Coverage". **Ungepruefte Hunks (`skipped` ohne Grund) sind ein Coverage-Finding (LOW).**

### Phase 1D — Re-Verify der Vorbefunde (v4.3, nur Modus INKREMENTELL)

Bei jedem Folge-Review der Session zusaetzlich die Befunde des LETZTEN Runs gegenchecken — **unabhaengig davon ob ein Fix angewendet wurde** (breiter als Phase 7, die nur bei tatsaechlichen Fixes triggert).

1. Vorige `findings.json` laden (Pfad aus `marker.findings`; fehlt → neuesten Review-Folder dieser Session/dieses Projekts in `~/.claude/reports/review/` nehmen; gar keiner → Notiz „keine Vorbefunde", Schritt entfaellt).
2. Pro Finding mit `status` open/verified die `file:line` **frisch mit dem Read-Tool** ansehen — existiert die Stelle noch UND zeigt sie das Problem noch?
   - **noch da** → Finding bleibt offen, in diesen Report uebernehmen (gleiche `F-ID`, Feld `age_reviews += 1`).
   - **weg/behoben** → `resolved` (Stelle gefixt/entfernt/verschoben + verifiziert). Steht ein Fix-Edit dahinter → Phase 7 uebernimmt die funktionale Verifikation.
   - **Datei weg** → `resolved (file entfernt)`.
3. Master-Section **„Vorbefunde re-checked"**: `| F-ID | file:line | Vorher | Jetzt (carried-over/resolved) |` + Zahlen. Carried-over-Findings fliessen in den aktuellen Findings-Satz (keine Doppel-Reportings — gleiche F-ID).
4. Outcome-Ledger (6.5D): `resolved` nach echtem Fix → `verified`; nach Fix wieder aufgetaucht → `regression`.

### Override-Modi & Size-Routing

Override: `projekt` = `all` (ganzes Repo **+ Projekt-Achsen E-J**, Phase 4.6) · `setup` (`~/.claude/`) · `discord`/`footstep` · `--since <date>` · `<glob>`.

### Phase 1E — Achsen-Gating (v4.5, entscheidet WELCHE Achsen laufen)

Der Skill hat zwei Achsen-Familien: **A-D = Code** (Phase 4.5, laufen immer) und **E-J = Projekt** (Phase 4.6). E-J voll auf jedem 3-Datei-Review zu fahren waere Token-Verbrennung ohne Ertrag — deshalb scope-gebunden:

| Scope-Modus | Projekt-Achsen E-J |
|---|---|
| `projekt` / `all` / `--projekt` | **alle E-J voll** (das ist der „komplettes Projekt untersuchen"-Fall) |
| THEMA (erstes Review der Session) | **H mechanisch immer** (kostet Sekunden, kein Modell) · E/F/G/I/J **nur wenn der Scope sie beruehrt** (Trigger-Tabelle unten) |
| INKREMENTELL (Folge-Review) | nur die Achsen deren Trigger im Delta vorkommen |
| `--no-projekt` | keine (Notfall/Token-Druck) — Master vermerkt „Projekt-Achsen uebersprungen (--no-projekt)" |

**Trigger-Tabelle** (Achse laeuft, wenn im Scope vorkommt):

| Achse | Trigger im Scope |
|---|---|
| E Architektur | neues Modul/Package · verschobene/umbenannte Datei · ≥3 geaenderte Files im selben Package |
| F Doku/Instruktionen | `*.md` · geaendertes oeffentliches Symbol/CLI-Flag/Command · `CLAUDE.md`/`rules/`/`SKILL.md` |
| G Config/Env/Deploy | `.env*` · `*.service`/`*.timer`/crontab · `nginx`/`docker`/`compose` · `settings.json` · neue `os.environ`/`getenv`-Stelle |
| H Repo-Hygiene | **immer** (mechanisch, ohne Modell) |
| I Betrieb | Hook · Cron/Timer · Service · Watchdog · Logging-/Notify-Pfad · Backup-Script |
| J Ziel-Abgleich | Plan/Spec/`PROGRESS.md` vorhanden ODER Feature-Arbeit im Diff |

### Phase 1F — `--dry-scope` (v4.5.1, Trockenlauf statt Fehllauf)

Uebernommen vom `--dry-route` des Council-Plugins: **vor** einem Lauf drucken, was passieren wuerde, ohne es zu tun. Ein `projekt`-Scope kostet bis zu 250k Token (K5) — ein falsch geratener Scope ist der teuerste Fehler dieses Skills.

`--dry-scope` fuehrt Phase 0, 1.0-1E aus und **bricht danach ab**. Ausgabe, sonst nichts:

```
Scope-Modus : THEMA | INKREMENTELL | Override:<name>
Files       : <N> (Top-10 + „… und M weitere")
Hunks       : <N> in <M> Files            (nur INKREMENTELL)
Code-Achsen : A-D (immer)
Projekt-Achsen : E,F,H aktiv · G,I,J n.a. (Trigger: <welcher>)
Reviewer    : security, quality, +projekt-reviewer   (Slot 7 ab 2 Achsen)
Council     : <Einzel-Agent verfuegbar (C1-C5 scharf) | nur Skill | nicht verfuegbar: <grund> | aus (--no-council)>
Budget-Schaetzung : ~<X>k Token · Modell <Opus high|medium|Sonnet-Split>
Recall      : <keine Historie | N Outcomes; fp_downrank:A hotspots:B blindspots:C>
```

**Kein Lockfile, kein Marker, kein Report, kein findings.json** — ein Trockenlauf darf keinen Zustand hinterlassen, sonst waere der naechste echte Run faelschlich INKREMENTELL. Kombinierbar mit jedem Scope-Override (`/review projekt --dry-scope`).

Gating-Entscheid **Pflicht-Trace** im Master („Projekt-Achsen: E,F,H aktiv (Trigger: …) · G,I,J n.a. (kein Trigger)") — sonst ist nicht unterscheidbar, ob eine Achse sauber war oder nie lief.

| Diff | Modell | Sub-Agents |
|------|--------|-----------|
| < 10 Files | Opus (high) | 2-3 |
| 10-50 | Opus (medium) | 3-5 |
| 50-200 | Sonnet/Subagent, Opus/Synthese | 5 mit Scope-Splits |
| > 200 | `all`-Bestaetigung erzwingen + Budget-Warnung (K5) | warnen |

---

## Phase 2 — Multi-Agent-Dispatch

**Immer parallel-Dispatch zuerst** (max 5 gleichzeitig). Bei EEXIST/Worktree-Failure: `> Reviewer: <name> (inline-Fallback wegen <grund>)`.

| # | Agent | Phase | Modell | Aktiv bei | Output |
|---|-------|-------|--------|-----------|--------|
| 1 | `security-reviewer` | 1 | Opus | immer | `REVIEW_REPORT_SECURITY.md` |
| 2 | `review-agent` | 1 | Sonnet | immer (fuehrt Phase 4.5 Achsen A-D) | `REVIEW_REPORT_QUALITY.md` |
| 3 | `dependency-auditor` | 1 | Sonnet | nur wenn `requirements/Pipfile/package.json/pyproject` im Diff | `REVIEW_REPORT_DEPENDENCIES.md` |
| 4 | `async-reviewer` | 1 | Opus | Discord_Bots/FastAPI im Diff | `REVIEW_REPORT_ASYNC.md` |
| 5 | `audio-pipeline-reviewer` | 1 | Opus | FootstepPro im Diff | `REVIEW_REPORT_AUDIO.md` |
| 6 | `perf-agent` | **2 (nach Phase 1)** | Opus | `--perf` oder >2k LoC | `REVIEW_REPORT_PERF.md` |
| 7 | `general-purpose` als **projekt-reviewer** | **2 (nach Phase 1)** | Opus | Phase 4.6 aktiv mit ≥2 Achsen (Gating 1E) | `REVIEW_REPORT_PROJEKT.md` |

**Slot 7 (v4.5):** kein neuer Spezial-Agent — `general-purpose` mit dem Achsen-Prompt aus Phase 4.6. Bekommt die **Ergebnisse des mechanischen Vorlaufs** (4.6 Schritt 1) mit in den Prompt und bewertet nur noch, was die Mechanik gefunden hat plus die urteilsbeduerftigen Achsen (E/J). Bei 1 aktiver Achse oder `all`-Scope-Budgetdruck (K5): inline statt Sub-Agent.

`security-reviewer` darf NICHT in einem nicht-Git-Worktree scheitern: **wenn Sub-Agent-Dispatch wegen "not in a git repository" failt, Security-Review INLINE mit echten SAST-Tools fahren** (bandit/semgrep/detect-secrets direkt via Bash), Notiz im Report. Max 5 Phase-1-Slots; `perf-agent` sequenziell danach.

**Sub-Agent Read-Disziplin (Pflicht):** jeder Reviewer-Prompt MUSS anweisen: „Dateien NUR mit dem Read-Tool lesen, KEIN `Get-Content`/`cat`/`type` via Bash/PowerShell." Grund: PowerShell-Reads triggern des Nutzers Read-Deny-Regel + Security-Warnung (mehrfach real passiert).

**Schreib-Disziplin bei Parallel-Dispatch (v4.6):** Die Reviewer laufen gleichzeitig, und mehrere von ihnen (`security-reviewer`, `review-agent`, `async-reviewer`, `audio-pipeline-reviewer`) haben `Write`/`Edit` in ihrer Agent-Definition. Solange sie nur ihren Report schreiben, ist das harmlos — sobald zwei im selben Lauf dieselbe Quelldatei anfassen, ueberschreiben sie sich gegenseitig, und der Verlierer merkt es nicht.

Deshalb gilt pro Reviewer genau eine der beiden Betriebsarten, explizit im Prompt:

1. **Read-only (Default):** „Aendere keine Quelldateien. Dein Output ist dein Report — Fixes schlaegst du als Diff im Report vor." Das ist der Normalfall; Fixes wendet der Hauptloop nach Phase 6 gebuendelt an.
2. **Isoliert schreibend (Ausnahme):** soll ein Agent tatsaechlich editieren, bekommt er `isolation: "worktree"` im Agent-Call und arbeitet auf einer eigenen Kopie des Repos. Der Hauptloop liest den Diff aus dem Worktree und uebernimmt bewusst, statt dass parallele Edits im Arbeitsverzeichnis kollidieren.

Nie beides mischen und nie mehrere schreibende Agents ohne Isolation im selben Dispatch. Kosten der Isolation: ein paar hundert Millisekunden plus Plattenplatz pro Agent — nur einsetzen, wenn wirklich geschrieben wird. Wichtig fuer `~/n8n_stack` und `Games/`: dort laufen Timer bzw. Bot-Loops gegen dieselben Dateien, ein unisolierter Parallel-Edit trifft also nicht nur den anderen Agenten.

### Reviewer-Prompt-Template (verbindlich, jeder Call)

1. Files-Liste (absolute Pfade) + **Hunk-Ranges** (welche Zeilen geaendert — Reviewer fokussiert die)
2. K3 Anti-Patterns (verboten)
3. K4 Sprach-Tool das er fuer diese Files laufen lassen soll
4. Findings-Format (Phase 3) inkl. **Pflicht-Feld `confidence` (0.0-1.0)** pro Finding
5. Read-Disziplin (Read-Tool only)
6. Memory-Service-Search-Anweisung (Regression-Tagging)
7. **Coverage-statt-Filtering (Opus-Recall-Paradox):** „Melde JEDES Finding inkl. unsicher + low-severity — filtere hier NICHT nach Wichtigkeit; Phase 5/5.5 rankt. Gib Konfidenz + geschaetzte Severity an." Sonst sinkt Recall.
8. Time-Budget 15 min (K5)

### Reviewer-Kontext- & Git-Disziplin (geerntet aus superpowers:requesting-code-review v6.1.1, 2026-07-21)

- **Kuratierter Kontext, NIE Session-History:** Reviewer-Sub-Agents bekommen genau das Template oben (Files, Hunks, Anforderungen) — niemals das Session-Transcript oder den eigenen Gedankengang. Haelt den Reviewer auf dem Werkstueck statt auf meinen Hypothesen (Anti-Anchoring) und schont den Orchestrator-Kontext.
- **Git-Read-Only fuer Reviewer:** Sub-Agents duerfen Working-Tree, Index, HEAD und Branch-State NICHT mutieren — Historie nur via `git show`/`git diff`/`git log` inspizieren. Wird eine andere Revision als Arbeitskopie gebraucht: `git worktree add /tmp/review-<sha> <sha>` statt HEAD bewegen. Bei des Nutzers Syncthing-Sync des Working-Trees (git pro Seite, `.git` excluded) waere ein mutierender Reviewer doppelt toxisch (`.sync-conflict`-Risiko). In jeden Reviewer-Prompt aufnehmen.
- **Plan-Abgleich wenn Plan existiert:** liegt der Session ein Plan/Task-Text zugrunde, Implementierung dagegen pruefen — Abweichung entweder explizit als „begruendete Verbesserung" markieren oder als Finding; liegt das Problem im PLAN statt im Code, genau das sagen.

**Zukunft:** bei kuenftigen subagent-driven/Plan-Execution-Flows (task-weise Implementierung, Worktree-Flows) nach JEDEM Task ein Mini-Review ueber die Task-Range (`BASE_SHA..HEAD_SHA` des Tasks) statt Big-Bang-Review am Ende — Fehler kaskadieren sonst in Folge-Tasks. (geerntet aus superpowers:requesting-code-review v6.1.1)

---

## Phase 3 — Findings-Format + findings.json (v4.0)

### Findings-Tabelle (Report-Form)

```
| ID | Severity | Conf | File:Line | CWE/Kat | Was | Warum Risiko | Fix | Aufwand |
```

**Fix-Aufwand-Pflicht:** `< 5 min` · `5-30 min` · `1-2 h` · `> 4 h`.
**Severity:** siehe K1 + K2-Anker. **Confidence:** Reviewer-Schaetzung, steuert Phase 5.5 Skeptiker-Routing (D).
**Schutz-Begruendung (Pflicht ab HIGH, 2026-09-30):** Jedes HIGH/CRITICAL sagt zusaetzlich, **warum kein vorhandener Schutz den Fehler abfaengt** (Validierung, Auth, Typen, Sandbox, Framework-Default, Aufrufer eine Ebene hoeher, Tests) — mit der geprueften Stelle, z. B. „Aufrufer bot.py:120 prueft nur den Typ, kein Test fuer leere Eingabe". Report-Form: in „Warum Risiko"; `findings.json`: Feld `guards` (unter HIGH `null`). Fehlt sie oder steht nur „kein Schutz gefunden" ohne gepruefte Stelle → Phase 5.5 stuft auf MEDIUM herab. Idee aus ECC `agents/code-reviewer.md` („HIGH / CRITICAL Require Proof", MIT).

### findings.json — Single-Source-of-Truth (v4.0)

Report-Markdown, Problem-Tracker-Feed (6.5C), Memory-Write (6.5A) werden ALLE aus **einer** Datei abgeleitet statt 3× denselben Befund neu zu parsen (Drift-Schutz). Pflicht-Emit in Phase 6, Schema:

```json
{
  "review": {
    "scope_mode": "topic | incr-1A | incr-1B | override:<name>",
    "scope": "<topic|auto-incremental|all|...>", "session_id": "<uuid>", "ts": "<iso>",
    "skill_version": "review v4.5.4", "convergence": "clean|stuck|cap|explosive",
    "iterations": 2, "false_negative_pass": "clean|found:<n>",
    "prev_findings_recheck": { "carried_over": 0, "resolved": 0 },
    "recall": { "total_outcomes": 0, "fp_downrank": 0, "hotspots": 0, "blindspots": 0 }
  },
  "findings": [
    { "id": "F001", "severity": "HIGH", "confidence": 0.9,
      "file": "x.py", "line": 64, "category": "CWE-79",
      "axis": "security | quality | flow-A | flow-B | flow-C | flow-D | test | perf | async | audio | dep | arch | docs | config | hygiene | ops | goal",
      "what": "...", "why": "...", "guards": "<ab HIGH: warum kein vorhandener Schutz greift + gepruefte Stelle; sonst null>",
      "fix": "...", "effort": "5-30 min",
      "status": "open|verified|false-positive", "verified": "<wie>",
      "regression_since": null, "tags": ["project-<slug>", "..."] }
  ],
  "hunk_ledger": [ { "file": "x.py", "range": "40-58", "status": "reviewed-clean|finding:F001|skipped:<grund>" } ],
  "council": { "available": "agents|skill-only|no:<grund>|off",
               "fired": [ { "trigger": "C4", "member": "kahneman", "outcome": "2 HIGH->MEDIUM" } ],
               "hit_but_capped": ["C2"], "not_hit": ["C3","C5"] },
  "projekt_axes": { "active": ["E","F","H"], "na": {"G": "kein Trigger", "I": "kein Trigger", "J": "kein Plan/Spec"},
                    "delegated": {"code-doc-sync": "ok|failed:<grund>|n.a."},
                    "prepass": { "sync_conflicts": 0, "bak_files": 0, "tracked_artifacts": 0, "dup_files": 0 } },
  "coverage": { "axes_x_modules": "...", "gaps": ["..."] }
}
```

Liegt im Review-Folder. Phase 6/6.5 lesen NUR von hier.

---

## Phase 4 — Regression-Tagging (Memory)

Wenn Memory-Health passed: pro Finding VOR Reporting suchen — bevorzugt `mcp__memory__memory_search`, sonst `POST ${MCP_MEMORY_BASE_URL:-http://10.0.0.x:8000}/api/search {"query":"<50 Zeichen Beschreibung + file-basename>","n_results":3}`. Match Similarity > 0.75 → Finding `[REGRESSION seit <datum>]` + Master-Section "Regressions". Offline → Notiz "Regression-Check skipped".

---

## Phase 4.5 — Functional-Logic-Flow-Audit (Pflicht, Achsen A-D)

Vom `review-agent` (oder inline). Output → Section "Functional-Logic-Flow" in QUALITY.md + Master-Section "Funktion-Logik-Datenfluss". Severity je Befund aus K2.

### Achse A — Functional-Correctness
Pro geaenderter Funktion/Endpoint/CLI: Tut sie was Docstring/Description/Test verspricht? Alle Params genutzt? Tests decken Claims? Return-Type matcht Hint in ALLEN Branches? Side-Effects (File/DB/Network/State) dokumentiert?

### Achse B — Logic / Control-Flow
Pro Funktion mit ≥2 Branches: Jeder Branch ≥1× erreichbar/getestet? Try-Except **spezifisch** (kein bare/`except Exception`)? Error-Handling greift (logged + rethrown wo relevant, NICHT swallowed)? Edge-Cases (None/leer/0/max-int/Unicode/lang/race)? Off-by-one (`range`-Grenzen, `< vs <=`)? Loop-Termination garantiert?

**Error & Rescue Map** (Zero-Silent-Failures) pro Funktion mit Error-Handling:

| Methode | Exception/Fehlerfall | Rescue-Aktion | sichtbares Outcome |
|---|---|---|---|

Jeder Fehlerpfad: **benannte** Exception (kein catch-all) UND sichtbare Konsequenz. `except Exception: pass` / Fehler ohne Log+Reraise+Signal = silent failure → HIGH (Persistence/Security/Auth) bzw. MEDIUM.

### Achse C — Data-Flow-Coverage (end-to-end)
Pro Daten-Eingangspunkt (User-Input/Webhook/MCP-Call/Endpoint/Discord-Command/File-Read/DB-Query):
1. Pfad rekonstruieren: Input → Validate → Process → Persist/Output, als File:Line-Hops.
2. Pro Hop: Daten kommen an (kein silent-drop)? Format passt zur naechsten Stufe? Fehlerpfad routet korrekt? Persistierung erreicht (commit/flush/response gesendet)?
3. ASCII-Flow im Report:
```
Input: <wo> → Validate: <f:l> → Process: <f:l> → Persist: <f:l>
              ↓ Fail?           ↓ Fail?          ↓ Fail?
            <reaktion>        <reaktion>       <reaktion>
```
**Pflicht:** geaenderter Eingangspunkt → kompletter Pfad bis Persist rekonstruiert ("verfolgt x1→x2→x3 und festgestellt: ..."), nicht "Funktion gereviewed".

### Achse D — Blast-Radius / Caller-Check
Fehler entstehen oft bei den **Aufrufern** wenn sich ein Vertrag aendert. Pro geaendertem oeffentlichen Symbol:
1. Caller finden: `grep -rn "<symbol>"` (+ Imports), Aufrufstellen file:line.
2. Pro Caller: Signatur geaendert → ruft er noch korrekt? Return-Shape geaendert → verarbeitet er es? Side-Effect/Exception geaendert → faengt/erwartet er es? Semantik geaendert → still-falsches Ergebnis?
3. Gebrochener Caller = Finding (K2). **Kein Caller im Diff** → explizit "N Caller geprueft, alle kompatibel". Gilt auch fuer CLI-/Hook-Schnittstellen.

---

## Phase 4.6 — Projekt-Achsen E-J (v4.5 — Review ≠ nur Bugs)

Achsen A-D fragen „ist dieser Code kaputt?". E-J fragen **„ist dieses Projekt in Ordnung?"** — Struktur, Wahrheitsgehalt der Doku, Betriebsfaehigkeit, Hygiene, Ziel-Treue. Ein Projekt kann bugfrei sein und trotzdem verrottet: divergierte Duplikate, Doku die luegt, ENV-Variable die keiner setzt, ein Dienst der still stirbt.

**Gating: Phase 1E entscheidet, welche Achsen laufen.** Severity aus **K2p**. Output → `REVIEW_REPORT_PROJEKT.md` + Master-Section „Projekt-Achsen (E-J)". Findings mit `axis: arch|docs|config|hygiene|ops|goal`.

### Durchfuehrung — kanonisch ausgelagert

Das *Wie* der sechs Achsen (mechanischer Vorlauf inkl. `$PRUNE`-Set, Delegations-Tabelle,
Kriterien je Achse E-J) steht in **[`_shared/projekt-achsen.md`](../_shared/projekt-achsen.md)**.
**Einmal lesen, sobald Phase 4.6
mit ≥1 Achse aktiv ist** (1 Read), analog zum K2-Block vor Phase 5. Ist keine Achse aktiv,
die Datei nicht laden.

Im Kern-Skill bleibt, was den Ablauf steuert: Gating (Phase 1E), Council-Kopplung (K6),
Ehrlichkeits-Pflicht und Reporting. Die Achsen-Details sind Daten — dieselbe Layer-Trennung
wie `review_learned.json` vs. Kern und K2/K2p vs. Phasen.

**Zwei Dinge, die nie in die ausgelagerte Datei wandern, weil sie den Ablauf entscheiden:**

1. **Mechanik vor Modell.** Der Vorlauf (grep/find/Delegation) laeuft **vor** jeder
   Modell-Bewertung; bewertet wird nur Gemessenes. Lehre aus dem `/gate`-Test 2026-07-29:
   ein Modell allein erfand einen Befund und uebersah zwei reale, die `grep` sofort fand.
2. **Plausibilitaets-Gate.** Liegt der groesste „God-File" im Zehntausender-Bereich oder
   heissen die Duplikate nach Paketnamen, ist der `$PRUNE` kaputt — **Befehle korrigieren,
   nicht die Ergebnisse melden.** Fremde Dependencies zu reviewen ist ein Messfehler,
   kein Finding (real passiert beim Verifikationslauf 2026-08-02: `.venv` fehlte im Prune).
### Council an den Urteils-Gabelungen (K6, feuert selbst)

Achsen E, I und J sind die drei, bei denen die Mechanik ausgeht und ein Urteil beginnt: *God-File oder bewusste Vereinfachung? Fehlende Rueckkopplung oder akzeptiertes Restrisiko? Totes Feature oder Reserve?* Dort feuern die Trigger **C1 (E)**, **C3 (I)** und **C2 (J)** aus K6 automatisch — Einzel-Mitglied, ~1,5k, kein Nachfragen. Achsen F, G und H haben bewusst keinen Trigger: dort entscheidet ein Abgleich, keine Meinung.

### Ehrlichkeits-Pflicht dieser Phase

Jede **aktive** Achse endet mit Befund ODER explizitem `keine Befunde >LOW. Geprueft: <was konkret, mit Pfaden/Zahlen>`. Eine Achse ohne beides gilt als **nicht gelaufen** und ist selbst ein Coverage-Finding (LOW) — dieselbe Regel wie beim Hunk-Ledger. Nicht-getriggerte Achsen als `n.a. (kein Trigger)` ausweisen, nicht verschweigen.

---

## Phase 5 — Synthese + Pyramid-Test

`synthesizer` (Opus) konsolidiert oder inline. **Master-Report enthaelt:**
1. **Executive Summary (max 200 Worte, NEGATIV-FIRST):** erst die 3 wichtigsten Risiken, dann was funktioniert. Verboten: mit "Insgesamt solide..." starten.
2. Findings-Tabelle nach Severity (CRITICAL/HIGH oben)
3. Cross-Cutting-Themen (Pattern in mehreren Files)
4. Regressions-Section (falls Memory aktiv)
5. Coverage-Luecken explizit + **Hunk-Coverage-Tabelle** (Phase 1C)
6. Funktion-Logik-Datenfluss (Phase 4.5 Achsen A-D, Diagramme) — auch bei clean: gepruefte Funktionen + Eingangspunkte + Pfade listen
6b. **Projekt-Achsen (E-J)** (Phase 4.6, wenn aktiv): Gating-Trace (welche Achse aktiv/n.a. + Trigger), Zaehlwerte des mechanischen Vorlaufs, Befunde je Achse, delegierte Skills + deren Ergebnis. Nicht-aktive Achsen als `n.a.` ausweisen.
6c. **Council (K6)** — Pflicht-Section sobald der Council verfuegbar ist, auch wenn kein Trigger feuerte:
   ```markdown
   | Trigger | Zustand | Mitglied | Ergebnis |
   |---|---|---|---|
   | C1 Architektur | gefeuert | feynman | F004 als bewusste Vereinfachung entkraeftet [council:feynman] |
   | C4 Bias | gefeuert | kahneman | 2 HIGH auf MEDIUM (Anchoring am Vorreview) |
   | C2 Ziel | getroffen, Deckel | — | nach C1/C4 ausserhalb der 3 |
   | C3 Betrieb · C5 FN | nicht getroffen | — | — |
   ```
   Nichts gefeuert → eine Zeile „kein Trigger getroffen (C1-C5 geprueft)". Council nicht verfuegbar → Grund nennen (Agents nicht gelistet / Skill nicht invocable / `--no-council`).
7. Honest-Roadmap: SOFORT / DEMNAECHST / BACKLOG mit Time-Budgets
8. Skill/Hook-Empfehlungen (max 5, je ≥2 Finding-Belege)
9. Self-Review-Loop-Section (Phase 5.5) + Completeness-Check (Phase 5.6) — beide Pflicht-Trace

**Pyramid-Test (vor Phase 5.5):** Master-Draft muss haben — ≥1 Security-Finding ODER "kein Security >MEDIUM, geprueft: <Achsen>"; analog ≥1 Quality; ≥1 Robustness/Coverage-Hinweis; Functional-Logic-Flow-Section mit A/B/C/D ODER explizit "kein Flow-Finding >MEDIUM, geprueft: <Funktionen+Pfade>"; **je aktiver Projekt-Achse (E-J) ein Befund ODER "keine Befunde >LOW, geprueft: <konkret>" + Gating-Trace fuer die inaktiven**; kein K3-Anti-Pattern enthalten.

**Testing-Coverage-Sub-Check (eigene Master-Section):**
- **Tests AUSFUEHREN, nicht nur Existenz (v3.6):** pro geaendertem Modul mit Tests `pytest <pfad> -q` (bzw. Projekt-Runner). **Fehlschlagender Test auf geaendertem Code = HIGH (Regression).** Smoke-Import (`python -c "import <modul>"`) fuer Scripts/Hooks zaehlt (faengt Syntax-/Import-Bruch). Kein Runner/keine Tests → Existenz-Finding. Delegierbar an `test-agent`.
- Geaenderte Files ohne Test listen; Test-Achse (Unit/Integration/E2E) + Aufwand je File.
- **Coverage-Rubrik** (Coverage-TYP, KEIN Quality-Score): `★★★` Behavior+Edge+Error · `★★` nur Happy-Path · `★` Smoke. `★★` bei Security/Auth/Persistence = MEDIUM-Luecke.

---

## Phase 5.5 — Self-Review-Loop (Pflicht, gegen Falsch-Positive + Whitewashing)

Master-Draft wird selbst als Vorgabe in einen reduzierten Pass gefuettert. Laeuft IMMER (auch `--no-loop` → nur Cap=1 + weniger Verbose, kein echter Skip — Trace bleibt). Sichtbarer Trace verhindert heimliches Skippen.

**Convergence (eines reicht):** `clean` (keine neuen Findings) · `stuck` (2× identische Findings) · `cap` (3 Iter) · `explosive` (auffaellig viel/wiederholter Output ~30k Token-Richtwert, qualitativ). Budget K5.

**Iter 1 → 2: Whitewashing + Severity-Recalibration**
- K3-Anti-Pattern-Phrasen raus; Exec-Summary Negativ-First?
- **Jedes HIGH/CRITICAL gegen K2-Anker** Punkt fuer Punkt; Severity-Inflation (Sub-Agents melden viel HIGH → oft MEDIUM/LOW) UND -Deflation (HIGH im Master verschwunden → gerechtfertigt?).

**Iter 2 → 3: Adversarial False-Positive-Filter + Konsolidierung**
Pro **HIGH/CRITICAL + Finding mit confidence < 0.7** (Confidence-Routing v4.0 — nicht mehr nur Severity) ein **unabhaengiger Skeptiker** (Subagent wenn verfuegbar, sonst inline frischer Blick), Auftrag: das Finding **WIDERLEGEN**.
- Lies NUR file:line + Umgebung frisch (ohne Reviewer-Report): existiert die Stelle, stimmt die Beschreibung, gibt es Guard/Workaround/Default drumherum, Tool-Artefakt (konstante Args, toter Pfad), gilt Pre-Condition real?
- Default: **widerlegt, ausser klar belegbar.** Ueberlebende → `[VERIFIED: <wie>]`; widerlegte → False-Positive raus, Begruendung im Trace.
- High-confidence (≥0.7) HIGH ohne Verdacht: Skeptiker optional (Token sparen), aber im Trace vermerken.

**Council-Bias-Linse — Trigger C4 (K6, feuert selbst):** ≥3 Severity-Adjustments in Iter 1 **oder** ≥2 HIGH mit `confidence` < 0,7 → `council:council-kahneman` als Einzel-Sub-Agent auf die **Findings-Tabelle** (nicht auf den Code): „Wo hat der Review sich selbst getaeuscht — Anchoring, Availability, Confirmation?" ~1,5k, trifft genau den Fehlermodus, den dieser Skill an sich selbst dokumentiert hat. C4 hat im Deckel-Konflikt Vorrang: ein verzerrter Report macht jeden anderen Befund unzuverlaessig.

Konsolidierung: gleiche Wurzel in 3+ Files → 1 Finding "Pattern X in N Files: <Liste>". Gleiche Severity+CWE+Fix → mergen. Widerspruch zwischen Reviewern → Master-Entscheidung mit Begruendung.

**Iter 3 → final: Coverage-Self-Check + Polish**
Coverage-Matrix (Achsen × Module, je Zelle geprueft/skipped/n.a., Luecken explizit) · Hunk-Ledger vollstaendig (kein `skipped` ohne Grund) · Roadmap-Sortierung · Notify-Payload korrekt (nur CRITICAL/HIGH).

**Trace (Pflicht, IMMER sichtbar)** — Master-Section "Self-Review-Loop":
```markdown
**Iterationen:** 2 (convergence: clean)
- Iter 1: Phrase "solide Implementation" entfernt, 3× Recalibration (2 HIGH→MEDIUM, 1 MEDIUM→LOW)
- Iter 2 (clean): keine neuen Findings, Coverage vollstaendig
**Severity-Adjustments:** F003 admin_bot.py:64 HIGH→MEDIUM (K2: Hardcoded Pfad) ...
**False-Positives entfernt:** F008 (bandit subprocess konstante Args, verifiziert)
```
Bei `clean` nach Iter 1: trotzdem Trace "Iter 1 (clean): kein Whitewashing/Drift/FP". Bei `stuck`/`cap`/`explosive`: zusaetzlich "Verbleibende Findings (nicht behoben in N Iter):" + "der Nutzer-Empfehlung: manueller Review".

---

## Phase 5.6 — Adversarial False-NEGATIVE-Pass (Pflicht, v4.0 — gegen Uebersehene)

Gegenstueck zu 5.5: dort werden falsche Findings gekippt, HIER wird ein realer Bug gejagt den **kein Reviewer fand**. Kern von des Nutzers „Fehler schneller + mehr finden".

**Ablauf:**
1. Ein **frischer Skeptiker** (Subagent wenn verfuegbar, sonst inline mit bewusst frischem Blick) bekommt: den **Diff/die Hunks** + die **Finding-Titel-Liste** (NUR Titel + file:line, NICHT die volle Begruendung — sonst ankert er auf bekannten Befunden).
2. Auftrag: „Finde EINEN realen Defekt auf Severity MEDIUM+ den diese Findings NICHT abdecken. Lies den geaenderten Code frisch. Wenn du nach ehrlicher Suche keinen findest: nenne ≥3 konkrete Dinge die du geprueft hast und die sauber sind (file:line + was geprueft)." Kein Defekt-Erfinden — Negative-Evidence ist ein valides, erwuenschtes Ergebnis.
3. Optional zweite Linse bei groesserem Diff: ein Skeptiker mit Logik-Fokus, einer mit Security-Fokus (parallel, je 1 Pass).
3.4. **Council-Blind-Spot-Linse — Trigger C5 (K6, feuert selbst):** meldet dieser Pass `clean` bei einem Diff > 200 geaenderten Zeilen, laeuft `council:council-socrates` als Einzel-Sub-Agent (~1,5k) mit demselben Anti-Anchoring-Input wie Schritt 1 (Diff + NUR Finding-Titel). Begruendung: ein sauberer FN-Pass auf grossem Diff ist das wahrscheinlichste Symptom einer von allen Reviewern geteilten Annahme — und die findet kein Reviewer, der sie teilt. Evidenz-Labels → `confidence` nach K6 Regel 3. Befunde `[council:<panel>]`, durch den 5.5-FP-Filter wie alles andere.
3.5. **Cross-Model-Skeptiker (optional, v4.2 — andere Modell-DNA gegen Claude-systematische Blind-Spots):** Claude-interne Skeptiker teilen ALLE Claudes blinde Flecken. Ein Modell mit anderer DNA (Gemini, kuenftig Codex) faengt eine Fehlerklasse die Claude strukturell uebersieht. „Think-Mode": das externe Modell bekommt Diff + NUR die Finding-Titel (kein Anchoring) und sucht einen uebersehenen Defekt. Aufruf (getrackt via gemini_usage, best-effort):
   ```bash
   git diff <range> --unified=0 | python ~/.claude/scripts/cross_model_skeptic.py \
     --findings "<F-IDs + file:line, NUR Titel; ; -separiert>" \
     --repo <projekt-root> [--provider gemini|codex]
   ```
   **`--repo` mitgeben (v4.5.4).** Ohne den Pfad sieht der Skeptiker nur den Diff auf stdin und kann den umgebenden Code nicht nachlesen — bei Codex heisst das `-C`, und genau dieses Fehlen kostete den AudioSetup-Nacht-Review am 2026-08-02 den Grossteil seiner Befunde. Ein Skeptiker, der nur Diff-Zeilen sieht, findet nur Diff-Zeilen-Fehler.
   Exit `3` (Auth fehlt) / `4` (Quota) / `1` (Fehler/Provider) → **degrade**: Notiz im Trace („Cross-Model-Pass skipped: <grund>"), Review laeuft normal weiter (kein Hard-Fail — externes Modell ist Bonus, nicht Pflicht). Provider-abstrahiert: heute `gemini` (gratis Free-Tier), `--provider codex` sobald Codex-CLI/ChatGPT-Plus eingerichtet — dann nur codex_call.py hinterlegen, Skill unveraendert.
4. **Neuer Befund (intern ODER cross-model) → durch den 5.5-FP-Filter (1×)** schicken (Skeptiker-Gegencheck), ueberlebt er → als Finding in `findings.json` + Master aufnehmen. MEDIUM+ → auch Problem-Tracker (6.5C). Cross-Model-Befunde EXPLIZIT als solche markieren (`[cross-model:gemini]`) — transparent welche DNA ihn fand.
5. Bounded: max 2 Claude-Skeptiker-Agents + max 1 Cross-Model-Pass, je 1 Pass. Kein Loop.

**Trace (Pflicht)** — Master-Section "Completeness-Check (False-Negative-Pass)":
```markdown
**Ergebnis:** found:2 | clean
- Skeptiker-Logik: NEUES Finding F019 session_logger.py:88 — extract_last_turn() bei leerem Transcript IndexError (kein Reviewer fand das). [VERIFIED durch FP-Filter]
- Cross-Model (gemini): NEUES Finding F020 bank.py:3 — Unchecked-Overdraft, balance wird negativ (Claude-Skeptiker uebersahen es, andere Modell-DNA fand es). [VERIFIED durch FP-Filter] [cross-model:gemini]
- Skeptiker-Security (clean): geprueft & sauber — (1) problem.py:40 sha256-ID kollisionsfrei, (2) viewer JSON-embed escaped, (3) hook stdout genau 1 JSON
- Cross-Model-Pass: <ok | skipped: auth-fehlt/quota/provider — degraded, Review unberuehrt>
```
Bei `clean`: Negative-Evidence-Liste ist PFLICHT (≥3 konkrete Checks) — sonst gilt der Pass als nicht ausgefuehrt. Cross-Model-Pass-Status (ok/skipped+grund) IMMER vermerken.

---

## Phase 6 — Lieferung

### Output-Folder
```
~/.claude/reports/review/<scope-slug>_<YYYY-MM-DD>_<HHMM>/
├── findings.json                 # Single-Source-of-Truth (v4.0) — Phase 6.5 liest NUR hier
├── DIFF_SUMMARY.md               # was geaendert + was geprueft (+ Hunk-Ledger)
├── REVIEW_REPORT_SECURITY.md
├── REVIEW_REPORT_QUALITY.md
├── REVIEW_REPORT_{DEPENDENCIES,ASYNC,AUDIO,PERF}.md   # je nach Reviewer
├── REVIEW_REPORT_PROJEKT.md      # Achsen E-J (Phase 4.6), wenn aktiv
├── REVIEW_REPORT_MASTER.md       # Synthese (aus findings.json gerendert)
└── RAW_TOOL_OUTPUT/              # bandit/semgrep/pip-audit/PSScriptAnalyzer/eslint JSONs
```

**findings.json zuerst schreiben, dann MASTER.md daraus rendern** — nicht umgekehrt. Garantiert Konsistenz zwischen Report, Tracker, Memory.

### Header je Report
```
> Reviewer: <name> (<inline-fallback|sub-agent>)
> Skill-Version: review v4.5.4 (= Frontmatter-version, kein Hardcode-Drift)
> Stand: <YYYY-MM-DD HH:MM>
> Scope-Modus: <THEMA (erstes Review der Session) | INKREMENTELL (Delta seit letztem + Re-Verify) | Override:<name>>
> Scope: <auto-diff | all | <override>>  ·  Session-ID: <uuid>
> Self-Review: <N> (convergence: <...>)  ·  False-Negative-Pass: <clean|found:N>
> Projekt-Achsen (4.6): <E,F,H aktiv · G,I,J n.a. (kein Trigger) | uebersprungen (--no-projekt)>
> Council (K6): <C1,C4 gefeuert (feynman, kahneman) · C2,C3,C5 nicht getroffen | nicht verfuegbar: <grund> | aus (--no-council)>
> Recall (gelernt): <keine Historie | N Outcomes; fp_downrank:A hotspots:B blindspots:C aktiv>
```

### Session-Marker (Pflicht)
Nach Synthese, vor Lock-Loeschung: in `.chat_review_marker.json` `"<session_id>": {"ts":"<jetzt-iso>","sha":"<git HEAD oder null>","findings":"<abs-pfad zu findings.json dieses Runs>"}` setzen (Map laden, Key updaten, atomic `.tmp`+`os.replace`). **Setzen des Markers macht den naechsten Call der Session zu Modus INKREMENTELL** (Delta ab diesem SHA + Phase-1D-Re-Verify aus `findings`). Auch bei Override UND beim ersten Full-Run setzen — sonst bleibt jeder Run ein Full-Scan.

### Discord-Notify (bei CRITICAL/HIGH)
**Kanonischer Weg (korrigiert 2026-08-02):** `~/.claude/rc-notify.sh "<Titel>" "<Text>"` — der Wrapper aus [`rules/discord-notify-channel.md`](../../rules/discord-notify-channel.md). Er ist no-op-sicher und loggt zusaetzlich nach `logs/rc-health.log`.

> Bis v4.4 stand hier `DISCORD_NOTIFY_WEBHOOK` — **diese Variable existiert in des Nutzers Setup nirgends** (verifiziert 2026-08-02: kein Treffer in `~/.claude`). Jedes Review-Notify war damit ein stiller No-op. Kanonisch ist `CLAUDE_NOTIFY_WEBHOOK` in `~/.claude/secrets/routine_webhook.env`, angesprochen ueber `rc-notify.sh`.

**Auf dem PC ist `rc-notify.sh` ein No-op** (`~/.claude/secrets/` und die rc-Skripte syncen nicht). Von dort fuehrt der Weg ueber `CLAUDE_DISCORD_BOT_TOKEN` + `CLAUDE_DISCORD_CHANNEL_ID`. Ist keiner der beiden Wege verfuegbar: Notify skippen **mit Notiz im Master** — nicht so tun, als waere gemeldet worden.

Inhalt: Titel, Severity-Counts, Master-Pfad. Nur MEDIUM/LOW → kein Notify (Spam-Schutz).

### Chat-Output (max 30 Zeilen)
Severity-Counts pro Achse (Code A-D **und** Projekt E-J getrennt) · Top-3-Findings (file:line) · Master-Pfad · 3 SOFORT-Aktionen · False-Negative-Pass-Ergebnis · Projekt-Achsen-Gating (aktiv/n.a.) · Persistenz-Status `Memory: N/M | Graph: <pfad|skip> | Tracker: K Probleme`.

---

## Phase 6.5 — Wissens-Persistenz (Pflicht, liest aus findings.json)

Nach Phase 6, vor Lock-Loeschung. Alle drei Teile lesen `findings.json` (kein Re-Parse von Markdown). Degraden mit Notiz wenn Backend fehlt.

### A) Memory-Service-Write (wenn Health passed)
- **1× Review-Rollup** (immer): Scope, Severity-Counts, Top-3, Master-Pfad, Convergence, Scope-Modus, False-Negative-Ergebnis. Tags `["review","session-summary","review-rollup","project-<slug>"]`.
- **Pro HIGH/CRITICAL** (Pflicht) + **MEDIUM** (empfohlen): `"[<Sev>] <file:line> — <was> — <warum> — <fix>"`, Tags `["review","finding","project-<slug>","<sev>","<cwe>"]`. LOW/INFO nur im Report.
- **Secret-Scan vor JEDEM Write:** Content gegen `secret_leak_detector.PATTERNS`; Treffer → nicht schreiben, `[REDACTED]`, Hash nach `~/.claude/lessons/leaks.jsonl`.
- **Update-Discipline:** vor Write `memory_search` (file-basename + issue); Similarity > 0.75 ODER gleicher file:line+CWE → bestehende Memory via `memory_update` erweitern (+`[REGRESSION seit <datum>]`) statt neu.
- **`global`-Tag** wenn cross-project-Lesson (Anti-Pattern, Architektur-Regel, wiederverwendbarer Fix); NICHT bei projekt-spezifischem Einzel-Bug.
- Tools `mcp__memory__memory_store`/`memory_search` statt `Bash(curl)`.

### B) Graphify (wenn verfuegbar)
`graphify --version`/Skill da? sonst skip+Notiz. Lauf auf Review-Folder → `graphify-out/` IN den Folder. Bei >10 Files: gereviewte Source-Files als zweiter Input (Findings linken an Code, god-nodes = haeufig-betroffene Files). Master-Section "Wissensgraph": Pfad + Top-3 Cluster/God-Nodes. Bei K5-Budget-Druck zuerst hier skippen.

### C) Problem-Tracker-Auto-Feed
Jedes **MEDIUM+**-Finding aus `findings.json` als offenes Problem:
```bash
python ~/.claude/scripts/problem.py add --severity <HIGH|MEDIUM|CRITICAL> \
  --project <slug> --location "<file:line>" --source review \
  --title "<was, kurz>" --fix "<konkreter fix>"
```
Code-Findings → projekt-lokal via `--root <projekt>`; Setup/Skills/Hooks/Agents → zentral (kein `--root`). Nur MEDIUM+ (LOW/INFO nur Report). ID content-stabil → re-Review aktualisiert. Tracker fehlt → skip+Notiz.

**Projekt-Achsen-Findings (v4.5.1):** `axis` aus `arch|docs|config|hygiene|ops|goal` wandert als `--source review --title "[<axis>] <was>"` mit, damit im Tracker unterscheidbar bleibt, ob ein Problem im Code oder im Projekt-Zustand liegt. **Zwei Sonderfaelle:**
- `hygiene`-Findings mit mechanischem Beleg (Konflikt-Kopie, getracktes Secret) sind **reproduzierbar** — Fix-Kommando direkt in `--fix` schreiben (`git rm --cached <f>` / `.gitignore`-Zeile), nicht prosaisch beschreiben.
- Der `projekt_axes.na`-Block ist **kein** Tracker-Eintrag, aber Pflicht im Master: eine nicht gelaufene Achse ist eine bekannte Luecke, kein offenes Problem.

**Verhaeltnis zu `projekt_axes` in findings.json:** Der Block ist ein **Report- und Nachvollzieh-Feld** (welche Achse lief, was fand der Vorlauf, welche Delegation griff) — 6.5C liest daraus nur die Findings, 6.5D nur die `axis`-Werte. Er wird bewusst **nicht** in den Tracker gespiegelt: Zaehlwerte sind kein Problem.

### D) Outcome-Ledger schreiben (v4.1 — die Lern-Labels für Phase 0)

Schreibt nur Outcomes mit nachvollziehbarer lokaler Evidenz. `--source` ist ein Herkunftslabel, keine unabhängige Verifikation. `record` verlangt zusätzlich Finding-ID und einen passenden Evidenzbeleg; `rebuild`/`recall` berücksichtigen nur noch vorhandene, unveränderte Belege. Alte unbelegte Zeilen bleiben erhalten und werden als `excluded_outcomes` sichtbar, beeinflussen aber keine neuen Lernsignale. Keine Kern-Skill-Edits durch Lerndaten.

```bash
python ~/.claude/scripts/review_learn.py record \
  --verdict <verified|false-positive|missed|regression> \
  --source <fp-filter|fn-pass|phase7-verify|real-fix> \
  --axis <achse> --category <cwe/kategorie> --file <basename> \
  --severity <S> --review-ts <review-folder-ts> \
  --finding-id <finding-id> --evidence <review-id>/<finding-id>.json
```

Evidenz unter `~/.claude/skills/review/evidence/<review-id>/<finding-id>.json`: bereinigtes JSON mit `finding_id`, `review_ts`, `source`, `verdict` (identisch zum Outcome), `code_sha256` (geprüfte Quellfassung), `basis` (Befehl oder konkrete Begründung) und `result` (Beobachtung). Keine Secrets/Rohlogs. Dies ist eine lokale Belegreferenz mit Inhalts-Hash, kein Wahrheits- oder Same-UID-Angriffsschutz. Dieselbe Finding-ID zählt pro Review nur einmal. Bei fehlendem Beleg keine Lernwirkung, kein stilles Ersatzlabel.

| Verdikt | Wann | Lern-Effekt |
|---|---|---|
| `false-positive` | FP-Filter (5.5) kippte ein Finding | naehrt `fp_downrank` (weniger Wiederhol-FP) |
| `missed` | FN-Pass (5.6) fand einen Bug den KEIN Reviewer sah | naehrt `blindspots` (gezielter Check kuenftig) |
| `verified` | Phase 7 bestaetigte einen Fix / FP-Filter-Ueberlebender | naehrt `hotspots` + bestaetigt Muster |
| `regression` | Finding kam nach Fix wieder | starker Hotspot + Regression-Signal |

Pro Run alle drei Verdikt-Quellen abarbeiten (je 1 `record`-Call pro Outcome). Script fehlt/failt → skip + Notiz (degraded). Master-Section „Recall (gelernt)" am Ende ergaenzen: „N Outcomes in Ledger geschrieben (X FP, Y missed, Z verified)".

**Flags (Default AN):** `--no-graph` · `--no-memory` · `--no-problems` · `--no-learn` (Ledger-Write skippen).

---

## Phase 7 — Fix-Verification-Loop (Pflicht wenn Fixes seit Review angewendet)

Schliesst Find → Fix → **Verify** → (Re-Review). Ein Fix wird nicht „Edit ist da" sondern **funktional** geprueft; Restbefund → automatisch erneut reviewt.

**Trigger:** Files mit `mtime > marker.ts` ODER Tracker-Findings `open → fixed` seit Review-TS. Explizit `--verify-fixes`. Reiner Read-Review ohne Fixes → Phase 7 entfaellt (Notiz).

**Ablauf:**
1. Fix-Scope: adressierte Findings (Tracker fixed seit Review-TS) + geaenderte Hunks. Pro Fix das ORIGINAL-Finding danebenlegen.
2. **Funktionale Verifikation pro Fix** (Verhalten, nicht Syntax) — mind. eine echte Ausfuehrung:
   - betroffene Funktion importieren + mit dem **Finding-Edge-Case** aufrufen (Input der vorher failte → muss jetzt korrekt sein);
   - Hook/Script mit realem Input (Mini-Transcript-Fixture; Hook-Protokoll: genau 1 JSON, kein Block);
   - **Tests ausfuehren** (`pytest <pfad>`/Smoke-Import) — nicht nur Existenz.
   - Drei Checks: (a) Original-Fehlverhalten weg, (b) keine Regression (Nachbar + **Caller** des Symbols intakt — greppen), (c) Fix deckt ALLE Branches/Edge-Cases (nicht nur Happy-Case).
   - Delegierbar an `verify`-Skill / `test-agent`.
3. **Ergebnis je Fix:** verifiziert → Tracker bleibt `fixed`, Note `[VERIFIED: <wie>]`. Unvollstaendig/Regression/neuer Defekt → **NEUES Finding** (Tracker add, MEDIUM+).

3b. **Verifikation in einen bleibenden Test giessen (v4.6, Pflicht bei HIGH+ und bei jedem Finding mit Verdict `regression`):** Der Edge-Case, mit dem du den Fix in Schritt 2 geprueft hast, ist bereits ein fertiger Testfall — er wird als Test **persistiert**, statt mit der Session zu verfallen. Ohne das schuetzt nur das Memory-Tagging vor dem Rueckfall, und das ist eine Notiz, kein Test: es meldet die Regression erst, wenn jemand erneut reviewt.

   Ablauf: Test in die Test-Suite des Projekts schreiben (Namensbezug zum Finding, z.B. `test_regression_<kurzform>`), dann **Red-Green** absichern — Fix revertieren, Test MUSS failen, Fix zurueck, Test MUSS passen. Ein Test, der auch ohne den Fix gruen ist, prueft nichts. Danach im Report als `[REGRESSION-TEST: <pfad>::<name>]` vermerken und im Tracker verlinken.

   Hat das Projekt keinen Test-Runner, ist die naechstbeste Form eine ausfuehrbare Assertion neben dem Code (Muster: `regression_assertions.json` aus `loopmode`, die `selfcheck.py` bei jedem Lauf prueft) — Hauptsache maschinell und wiederholbar. Ist beides nicht moeglich, wird das im Report als offener Punkt benannt statt stillschweigend uebergangen. Delegierbar an `test-agent`.
4. **Re-Trigger (bounded):** ≥1 neues MEDIUM+ → `/review` erneut auf neuen Diff (Phase 1-6.5), Zyklus +1. **Max 2 Zyklen.** Konvergiert nicht → Rest melden + "der Nutzer-Empfehlung: manueller Review".
   - **Projekt-Achsen im Re-Trigger (v4.5.1):** E-J laufen im Folge-Zyklus **nur auf dem Fix-Delta**, nie wieder voll — auch wenn der Ursprungs-Lauf `projekt`-Scope hatte. Ein Fix an drei Dateien aendert weder die Architektur des Repos noch seine Hygiene-Lage. Ausnahme: der Fix beruehrt selbst einen Achsen-Trigger (neue ENV-Variable, verschobenes Modul, geaenderte Unit) → dann diese eine Achse voll, die anderen als `n.a. (Re-Trigger-Delta)`. Ohne diese Regel kosten 2 Zyklen × `projekt`-Scope mehr als der eigentliche Review.
5. Master-Section "Fix-Verification": `| Finding | Verifikation (wie) | Ergebnis | neues Finding? | Re-Triggered? |` + Zyklus-Zaehler.

### Frischer-Beweis-Regel — nie „fertig/gruen/verifiziert" ohne frische Evidenz (geerntet aus superpowers:verification-before-completion v6.1.1, 2026-07-21)

Ergaenzt Phase 7, gilt aber skill-weit fuer JEDE Erfolgs-Behauptung (Fix verifiziert, Tests gruen, Phase abgeschlossen, Marker gesetzt): **keine Completion-Behauptung ohne frischen Beweis aus DIESEM Run.** Wurde der Verifikations-Befehl nicht in diesem Run ausgefuehrt, darf der Erfolg nicht behauptet werden.

**Gate vor jeder Behauptung:** (1) Welcher Befehl beweist sie? → (2) Befehl FRISCH + KOMPLETT ausfuehren → (3) Output + Exit-Code wirklich lesen (Failures zaehlen) → (4) erst DANN behaupten, MIT Evidenz im Report. Schritt uebersprungen = behauptet, nicht verifiziert.

| Behauptung | braucht | reicht NICHT |
|---|---|---|
| „Tests gruen" | frischer Runner-Output dieses Runs: 0 failures | alter Run, „sollte passen" |
| „Fix wirkt" | Original-Symptom/Edge-Case frisch re-getestet | „Code geaendert, also gefixt" |
| „Regressionstest steht" | Red-Green: Fix revertieren → Test MUSS failen → restore → pass | Test passt einmal |
| „Sub-Agent fertig" | Diff/Artefakt selbst gelesen | Agent-Report „success" |
| „Anforderungen erfuellt" | Punkt-fuer-Punkt-Checkliste gegen Vorgabe | „Tests laufen durch" |

**Red-Flag-Woerter** im eigenen Output vor der Verifikation: „sollte", „wahrscheinlich", „muesste jetzt", „sieht gut aus", „Done!" → STOP, erst Gate 1-3. Keine Ausnahmen fuer „nur dieses eine Mal", Muedigkeit oder Teil-Checks — Teil-Verifikation beweist nichts, Umformulierung umgeht die Regel nicht (Geist schlaegt Wortlaut).

**Abgrenzung:** 5.5 prueft den REPORT (Whitewashing/Severity), 5.6 jagt Uebersehene, Phase 7 prueft angewendete FIXES funktional. Alle Pflicht, distinkt.

---

## Eingehendes Reviewer-Feedback — technisch pruefen statt reflexhaft uebernehmen (geerntet aus superpowers:receiving-code-review v6.1.1, 2026-07-21)

Rueckkanal-Disziplin, wenn Feedback ZU einem Review/Fix hereinkommt — von der Nutzer, einem Cross-Model-Skeptiker (Gemini/Codex, Phase 5.6), einem externen Review oder einem Sub-Agent der Findings dieses Skills anficht:

**Ablauf:** komplett lesen → Anforderung in eigenen Worten restaten (oder nachfragen) → gegen die Codebase verifizieren (Read/grep, nicht Erinnerung) → bewerten: technisch korrekt fuer DIESE Codebase? → technische Antwort oder begruendeter Pushback → dann EINZELN umsetzen: Blocker → simple Fixes → komplexe Fixes, jeden Fix einzeln testen (Phase-7-Regeln), keine ungetesteten Sammel-Batches.

**Kein performatives Zustimmen** (analog K3): „Da hast du voellig recht!" / „Guter Punkt!" / Dank-Prosa verboten — stattdessen technisches Restatement, konkrete Rueckfrage, oder einfach der Fix selbst. Korrektes Feedback quittieren mit „Gefixt: <was/wo>".

**Unklare Punkte blockieren ALLES:** bei Multi-Item-Feedback („fix 1-6") mit unklaren Items NICHTS implementieren bevor alle Items geklaert sind — Items haengen oft zusammen, Teilverstaendnis = falsche Implementierung.

**Pushback-Kriterien** (dann mit technischer Begruendung widersprechen — Tests/Caller/Code als Beleg, nicht defensiv):
- Vorschlag bricht bestehende Funktionalitaet (Tests/Caller belegen es)
- Reviewer fehlt Kontext (Legacy-/Kompat-Grund fuer die aktuelle Implementierung existiert)
- YAGNI: vor „richtig implementieren" erst greppen ob das Feature ueberhaupt genutzt wird — ungenutzt → Entfernen vorschlagen statt ausbauen
- technisch falsch fuer diesen Stack / diese Plattform
- kollidiert mit des Nutzers frueherer Architektur-Entscheidung → stoppen, der Nutzer entscheidet

**Quellen-Differenzierung:** der Nutzer = trusted (nach Verstaendnis umsetzen, Scope-Rueckfragen erlaubt) · extern/Cross-Model = skeptisch pruefen (Pushback-Kriterien oben durchgehen) — externe Vorschlaege sind Hypothesen zum Evaluieren, keine Befehle. Nicht verifizierbar ohne X → genau das sagen („kann ich ohne X nicht verifizieren — investigieren/fragen/weiter?") statt blind umsetzen.

**Falscher eigener Pushback:** faktisch korrigieren („Verifiziert — du hattest recht, <grund>. Fixe.") und weiter — keine Entschuldigungs-Prosa, kein Verteidigen des Pushbacks.

---

## Constraints (hart)

- **Read-only.** Niemals Auto-Fixes. Findings + Empfehlungen, der Nutzer entscheidet. (Phase 7 verifiziert, wendet keine neuen Fixes an.)
- **findings.json ist die Wahrheitsquelle** — Report/Tracker/Memory daraus ableiten, nicht parallel pflegen.
- **Lockfile** gegen Concurrent-Runs · **Versionierte Reports** (Timestamp-Folder, kein Overwrite).
- **K3-Anti-Patterns** verpflichtend · **Pyramid-Test** Pflicht vor 5.5.
- **Phase 5.5 (FP) + 5.6 (FN) + Phase 7 (Fix-Verify)** alle PFLICHT, sichtbarer Trace im Master — kein heimliches Skippen.
- **Council (K6) ist verdrahtet, nicht optional:** die Trigger C1-C5 feuern **selbst** auf dem Einzel-Mitglied-Pfad (~1,5k), Deckel 3 pro Run, Kill-Switch `--no-council`. Die teure `/council`-Deliberation feuert **nie automatisch**. Vor jedem Schritt das Verfuegbarkeits-Gate; nicht verfuegbar → Trace-Notiz, Review laeuft unveraendert weiter. Council setzt keine Severity, liefert nur mit `file:line`, gespaltener Vote bleibt Split, Befunde `[council:<panel>]` durch den 5.5-FP-Filter. **Master-Section „Council" ist Pflicht, auch wenn nichts feuerte.**
- **Phase 4.6 (Projekt-Achsen E-J):** Gating nach 1E, aber **Achse H und der mechanische Vorlauf laufen immer** (kosten kein Modell). Reihenfolge ist bindend: **erst messen (grep/find/Delegation), dann bewerten** — nie ein Modell allein ueber Slop/Duplikate/Hygiene urteilen lassen. Gating-Trace + „geprueft: <konkret>" je aktiver Achse sind Pflicht; fehlt beides, gilt die Achse als nicht gelaufen (Coverage-Finding). Delegieren statt nachbauen (`code-doc-sync`, `instructions-drift-check`, `python-env-audit`, `deploy-preflight`) — nie beides fuer dieselbe Sache.
- **Sub-Agents lesen nur mit Read-Tool** (kein PowerShell-Get-Content).
- **security-reviewer Inline-Fallback** wenn nicht-Git-Worktree den Sub-Agent-Dispatch bricht.
- **Sprach-bewusstes Tool-Routing (K4)** — PowerShell/JS/Shell nicht ungeprueft lassen.
- **Fix-Aufwand-Schaetzung** + **Confidence** je Finding · **Skill-Version-Header** je Report.
- **Session-Marker** (ts + git-sha + findings-pfad) nach jedem Run · **Default-Scope: erstes Review der Session = alles zum Session-Thema (NICHT ganzes Repo), danach inkrementell (Git-Hunk-genau) + Phase-1D-Re-Verify der Vorbefunde**. Override (`all`=repo-weit) schlaegt das Gate.
- **Run-Budget K5** beachten, bei `all`-Scope vorher warnen.
- **Wissens-Persistenz 6.5** Pflicht (degraded wenn Backend fehlt).
- **Selbstlern-Schleife (v4.1) Pflicht:** Phase 0 Recall am Anfang (Trace „Recall (gelernt)") + Phase 6.5D Outcome-Write am Ende. **Nur VERIFIZIERTE Outcomes lernen** (Provenance-Gate im Script, kein Bypass). Unterdrueckung gelernter FP-Muster = **runterstufen + flaggen, NIE silent-drop**. Gelernte Schicht (`review_learned.json`) ist Daten — **Kern-SKILL.md wird nie auto-editiert**; Kern-Vorschlaege nur via Wochen-Routine an der Nutzer. Skip nur via `--no-learn`.

## Ehrlichkeits-Klausel

Reviewer ohne signifikante Findings: **nicht erfinden.** Explizit "keine Findings auf MEDIUM+ in <scope>. Geprueft: <≥5 Achsen>. Edge-Cases ohne Treffer: <≥3>." Guter Code: nicht ueberhoehen, nicht relativieren. Gilt auch fuer den False-Negative-Pass (5.6): clean nur mit Negative-Evidence-Liste.

## Self-Improvement — die Selbstlern-Schleife (v4.1)

Drei Stufen, geschlossener Kreis, ehrlich (kein Gewichts-Training — daten-getriebener Recall + gegatete Text-Evolution):

1. **Recall (Phase 0, pro Run):** liest `review_learned.json` → weniger Wiederhol-FP, priorisierte Hotspots, gezielte Blind-Spot-Checks. Sofort wirksam, deterministisch.
2. **Ledger (Phase 6.5D, pro Run):** schreibt die verifizierten Verdikte (5.5 FP-Filter / 5.6 FN-Pass / Phase 7 Fix-Verify) als gelabelte Outcomes. Backbone: `~/.claude/scripts/review_learn.py` (Provenance-Gate, atomic, append-only JSONL + aggregiertes `review_learned.json`).
3. **Meta-Evolution (Wochen-Routine `review-weekly-learn`):** `review_learn.py consolidate` mappt den Ledger auf Kern-Skill-Verbesserungs-Vorschlaege (neuer K2-Anker, neuer Reviewer-Check, Hotspot-Flag). **Gelernte Schicht wird auto-aktualisiert; Kern-SKILL.md-Vorschlaege gehen als Idee an den Problem-Tracker (der Nutzer entscheidet)** — verhindert Re-Bloat + Drift des frisch verschlankten Kerns. Runbook: `~/.claude/skills/review/REVIEW_LEARN_RUNBOOK.md`. Analog zum bewaehrten `lyra-weekly-check`-Muster.

Guardrails (warum es nicht entgleist): nur verifizierte Provenance lernen (gegen Feedback-Loop-Vergiftung) · Unterdrueckung = downrank+flag nie silent-drop (gegen Kalibrierungs-Drift) · gelernte Schicht ≠ Kern (gegen Bloat) · Kern-Aenderungen human-gegated (gegen Overfitting auf des Nutzers Repos).

Zusaetzlich: quartalsweise Anthropic-Best-Practice-Check (analog lyra-weekly-check), Skill-Updates im Changelog.

## Changelog

- **v4.6.0 (2026-08-13):** **Schreib-Disziplin bei Parallel-Dispatch + Regressionstests statt Regressions-Notizen.** Beides aus der TikTok-Findings-Triage 2026-08-12 (Records `#60`/`#96` Worktree-Parallelisierung, `#77` generierte Regressionstests), auf des Nutzers Setup uebertragen statt uebernommen. (1) **Parallel-Dispatch:** vier der Reviewer haben `Write`/`Edit` in ihrer Agent-Definition — solange sie nur Reports schreiben harmlos, aber zwei gleichzeitige Edits an derselben Quelldatei ueberschreiben sich, ohne dass der Verlierer es merkt. Ab jetzt pro Reviewer genau eine Betriebsart, explizit im Prompt: read-only (Default, Fixes als Diff im Report, Hauptloop wendet nach Phase 6 gebuendelt an) ODER `isolation: "worktree"` fuer echte Edits auf einer eigenen Repo-Kopie. Nie mehrere schreibende Agents ohne Isolation. Besonders relevant fuer `~/n8n_stack` (systemd-Timer) und `Games/` (Bot-Loops) — dort kollidiert ein unisolierter Edit nicht nur mit dem anderen Agenten. (2) **Phase 7 Schritt 3b:** der Edge-Case, mit dem ein Fix verifiziert wurde, wird als Test **persistiert** statt mit der Session zu verfallen — Pflicht bei HIGH+ und bei Verdict `regression`. Mit Red-Green-Absicherung (Fix revertieren, Test muss failen), Report-Vermerk `[REGRESSION-TEST: <pfad>::<name>]`, Fallback auf eine maschinell pruefbare Assertion nach dem Muster `regression_assertions.json` aus `loopmode`, und bei Unmoeglichkeit ein offener Punkt im Report statt Schweigen. Begruendung: das bisherige Memory-Regression-Tagging ist eine Notiz, kein Test — es meldet den Rueckfall erst beim naechsten Review. Backup: `SKILL.md.bak.pre-worktree.<ts>`.
- **v4.5.4 (2026-08-03):** **Cross-Model-Skeptiker bekommt `--repo`.** Ohne Projekt-Root sieht der externe Skeptiker nur den Diff auf stdin — bei Codex fehlte damit `-C`, der Agent hatte keinen Dateizugriff und konnte ausschliesslich Diff-Zeilen bewerten. Ursache-Analyse zum AudioSetup-Nacht-Review (Codex fand ~10 % dessen was Fable 5 fand): nachgemessen lag es am Aufruf, nicht am Modell — die Codex-CLI laeuft im Default mit `reasoning effort: none` (am Banner verifiziert), und der Wrapper setzte weder Effort noch Arbeitsverzeichnis. `codex_call.py` v2 setzt beides jetzt modusabhaengig, kennt `--mode review` (nutzt `codex exec review`) und loggt `effort`/`repo`/`model` mit, damit ein schwacher Lauf im Nachhinein erklaerbar ist. `cross_model_skeptic.py`: Codex-Zweig setzte gar kein `--mode` (lief als `other`) — gefixt, plus `--repo`-Durchreichung.
- **v4.5.3 (2026-08-02):** **Council aktiv verdrahtet statt opt-in (der Nutzer: „soll aktiv bleiben aber aktiv verdrahtet werden").** K6 kippt von „Default AUS, vorschlagen" auf **Default AN, trigger-gebunden**: fuenf harte Feuer-Bedingungen auf bereits vorliegenden Befunden — **C1** divergiertes Duplikat/God-File → `feynman`, **C2** dokumentiertes Feature ohne Code / Code ohne Aufrufer → `torvalds`, **C3** Dienst ohne Log+Notify+Watchdog → `taleb`, **C4** ≥3 Severity-Adjustments oder ≥2 HIGH mit confidence <0,7 → `kahneman` (auf die Findings-Tabelle, nicht den Code), **C5** FN-Pass `clean` bei Diff >200 Zeilen → `socrates`. Kein Nachfragen, kein Ermessen. **Deckel 3 Mitglieder/Run (~4,5k ≈ 2 % von K5)**, Prioritaet C4 > C1 > C5 > C3 > C2 (ein verzerrter Report macht jeden anderen Befund unzuverlaessig). Die teure `/council`-Deliberation feuert **nie automatisch** — nur `--council` oder der Nutzer. Kill-Switch `--no-council`. Neu: Pflicht-Master-Section **6c „Council"** (auch wenn nichts feuerte), `council`-Block in findings.json, Header-Zeile, K5-Budgetzeile, `--dry-scope` zeigt die Schaerfe. **Ursache des Verfuegbarkeits-Raetsels gefunden:** Plugin-Agents registrieren sich beim Session-Start — das Plugin kam am 28.07. 09:11, die Session lief seit dem 25.07. (alle anderen Plugins: 14./21.07., die waren gelistet). In einer frischen Session sind die Agents da; das Gate bleibt als Netz.
- **v4.5.2 (2026-08-02):** **Sieben Verbesserungen aus dem eigenen Review des Skills — plus drei im Test gefundene Rezept-Defekte.** (1) **Achsen-Detail ausgelagert** nach `_shared/projekt-achsen.md` (kanonisch, `/review` + `/full-audit` + `/quick-review` ziehen daraus; Kern behaelt Gating, K6, Ehrlichkeits-Pflicht, Reporting) — Kern 80 → 74 KB, gegen das Bloat-Risiko das schon v3.3.1 geflaggt hatte. (2) Neue **Phase 1F `--dry-scope`** (Muster vom `--dry-route` des Councils): druckt Scope, Achsen-Gating, Reviewer, Council-Verfuegbarkeit und Budget-Schaetzung und bricht ab — **ohne Lockfile/Marker/Report**, sonst waere der naechste echte Lauf faelschlich INKREMENTELL. (3) **Council-Verfuegbarkeits-Gate** in K6: Plugin installiert ≠ Agents dispatchbar (am 2026-08-02 war das Plugin aktiv, aber kein `council:*` in der Agent-Liste der Session; Zustand ist pro Maschine und pro Session verschieden, weil `settings.json`/`/plugins` nicht syncen) → Einzel-Agent, sonst `--quick --members`, sonst Schritt entfaellt mit Trace. (4) **Phase-7-Re-Trigger** faehrt E-J nur noch auf dem Fix-Delta (2 Zyklen × `projekt`-Scope kosteten sonst mehr als der Review). (5) **6.5C** nimmt `axis` in den Tracker-Titel und verlangt bei `hygiene`-Findings ein ausfuehrbares Fix-Kommando; `projekt_axes` ist explizit als Report-Feld deklariert (Zaehlwerte sind kein Problem). (6) `/quick-review` v2.2.0 bekommt **Achse 7 Repo-Hygiene** (drei Befehle, kein Modell). (7) **Discord-Notify auch in `/full-audit` und `/security-audit` nachgezogen** — dieselbe Phantom-Variable, derselbe stille No-op. **Vollbetriebs-Test des Vorlaufs** gegen `~/projects/filedrop`: drei Rezept-Defekte gefunden und gefixt — fehlendes `.venv` im Prune, ENV-Regex ohne `[\[\(]` (matchte `os.environ.get(` nie: 4 von 13 Variablen, die 9 fehlenden waeren als Findings gemeldet worden), `.env.example` im Secret-Check (CRITICAL-Fehlalarm). Lehre im Shared-File verankert: ein Vorlauf-Fehler erzeugt **falsche** Findings, die als „gemessen" mehr Vertrauen bekommen als eine Modell-Vermutung.
- **v4.5.1 (2026-08-02):** **Council-Kopplung (K6) + zwei verifizierte Drift-Fixes am Skill selbst.** (1) Neuer KANON-Block **K6**: das `council`-Plugin (v1.2.0, auf netcup aktiv) an fuenf Urteils-Gabelungen — Achse E/I/J, Phase 5.5 (Bias), Phase 5.6 (Blind-Spots). **Kosten-gestaffelt** nach der Analyse vom 2026-07-28: Einzel-Mitglied als namespaced Sub-Agent (`council:council-<name>`, ~1,5k = Preisklasse eines normalen Reviewers) ist der Default, `/council --duo/--triad` (~21-23k, Skill-Overhead allein 18,7k) nur bei echtem Streit, **`--full` (~47k) nie**. Uebernommen aus der Plugin-Pruefung: das Protokoll ist die Substanz (Blind-Runde vor Kreuzverhoer = dieselbe Anti-Anchoring-Logik wie Phase 2; Enforcement-Scan gegen premature agreement/missing dissent), **Evidenz-Labels FACT/INFERENCE/ASSUMPTION/UNKNOWN mappen direkt auf das `confidence`-Feld** und damit auf das v4.0-Skeptiker-Routing (echte Labels statt geschaetzter Zahlen), **gespaltener Vote wird als Split uebernommen** statt zu einer Empfehlung geglaettet. Default AUS, Flag `--council`, vorschlagen statt selbst starten. (2) **Discord-Notify-Fix:** `DISCORD_NOTIFY_WEBHOOK` existiert in des Nutzers Setup **nirgends** (verifiziert) — jedes Review-Notify seit v2.0 war ein stiller No-op. Kanonisch ist jetzt `rc-notify.sh` (netcup) bzw. `CLAUDE_DISCORD_BOT_TOKEN`/`CHANNEL_ID` (PC), mit Pflicht-Notiz im Master wenn kein Weg verfuegbar. (3) Gegengeprueft und **kein** Defekt: `review_learn.py` hat keine Achsen-Allowlist (die 6 neuen Achsen laufen durch), und der Memory-Default `10.0.0.x:8000` ist von netcup aus erreichbar (HTTP 200).
- **v4.5.0 (2026-08-02):** **Projekt-Achsen E-J — Review prueft nicht mehr nur Bugs, sondern das Projekt (der Nutzer: „nicht nur auf bugs gehen sondern das komplette projekt untersuchen").** Neue **Phase 4.6** mit sechs Achsen: **E** Architektur/Struktur (divergierte Duplikate als teuerster Befund, God-Files, Layering/zirkulaere Imports, Copy-Paste), **F** Doku- & Instruktions-Drift (drei Klassen: aktiv-falsch HIGH / verwaist MEDIUM / veraltet LOW; Rules + CLAUDE.md sind code-aequivalent), **G** Config/Env/Deploy (ENV beidseitig, Secret-Ablage, Port-/Pfad-Kollision, Unit-Pfade), **H** Repo-Hygiene (mechanisch, laeuft IMMER — `.sync-conflict`-Kopien, getrackte Secrets/Artefakte, tote Einstiegspunkte), **I** Betrieb/Beobachtbarkeit („merkt jemand wenn es kaputtgeht" — Notify/Watchdog, Recovery je ausgefuehrt, Cron-Idempotenz, No-op-Notify-Kanal), **J** Ziel-/Anforderungs-Abgleich (dokumentiertes Feature ohne Code = HIGH, YAGNI-Leiche, Plan-Abweichung — Problem darf im Plan liegen). **Mechanischer Vorlauf ist Pflicht vor jeder Modell-Bewertung** (Lehre aus dem `/gate`-Test 2026-07-29: Modell erfand 1 Befund und uebersah 2 reale, die `grep` sofort fand). **Reuse-first:** F/G delegieren an `code-doc-sync`, `instructions-drift-check`, `python-env-audit`, `deploy-preflight` statt nachzubauen — nie beides. **Phase 1E Achsen-Gating** verhindert Token-Verbrennung: voll bei `projekt`/`all`/`--projekt`, sonst nur triggernde Achsen (H immer, weil quasi gratis); Gating-Trace Pflicht, damit „sauber" und „lief nie" unterscheidbar bleiben. Neuer Scope `projekt` (= `all` + E-J), Flags `--projekt`/`--no-projekt`. Neu: **K2p**-Anker-Block in `_shared/severity-anchors.md` (kanonisch, kein Skill-lokales Duplikat), Dispatch-Slot 7 `projekt-reviewer` (`general-purpose`, Phase 2, kein neuer Spezial-Agent), `REVIEW_REPORT_PROJEKT.md`, findings.json `axis`-Enum +6 Werte + `projekt_axes`-Block, Master-Section 6b, Pyramid-Test + K5-Budget-Zeile erweitert, Phase-0-Recall lernt die neuen Achsen mit.
- **v4.4.0 (2026-07-21):** **superpowers-Ernte vor Plugin-Deaktivierung (geerntet aus superpowers:requesting-code-review + receiving-code-review + verification-before-completion v6.1.1).** Drei additive Sub-Sektionen, Kern-Phasen/Pipeline unveraendert: (1) Phase 2 „Reviewer-Kontext- & Git-Disziplin" — kuratierter Kontext statt Session-History (Anti-Anchoring), Git-Read-Only fuer Reviewer-Sub-Agents (nie HEAD/Tree mutieren, temp-Worktree fuer andere Revisionen; Syncthing-`.sync-conflict`-Schutz), Plan-Abgleich inkl. „Problem kann im Plan liegen", Zukunfts-Note task-weise Mini-Reviews fuer kuenftige subagent-driven/Worktree-Flows. (2) Phase 7 „Frischer-Beweis-Regel" — keine Erfolgs-/Fertig-Behauptung ohne frische Evidenz aus DIESEM Run: Gate (Befehl→frisch ausfuehren→Output lesen→dann behaupten), Evidenz-Tabelle (Tests/Fix/Red-Green-Regressionstest/Sub-Agent-Report/Anforderungs-Checkliste), Red-Flag-Woerter („sollte"/„wahrscheinlich"), Geist-schlaegt-Wortlaut. (3) neue Sektion „Eingehendes Reviewer-Feedback" — Rueckkanal-Disziplin: verifizieren statt reflexhaft uebernehmen, kein performatives Zustimmen (analog K3), Unklare-Items-blockieren-alles, Pushback-Kriterien inkl. YAGNI-grep, Quellen-Differenzierung der Nutzer (trusted) vs. extern/Cross-Model (skeptisch), faktische Pushback-Korrektur. Bewusst NICHT uebernommen: Critical/Important/Minor-Skala (kollidiert K1/K2), „Strengths zuerst"-Kalibrierung (kollidiert Negativ-First-Regel), GitHub-PR-Thread-Mechanik (kein PR-Zwang), Dispatch-Template code-reviewer.md (Phase 2/3 sind reicher).
- **v4.3.0 (2026-06-16):** **Session-Gate-Scope praezisiert + Phase 1D Re-Verify (der Nutzer).** Erstes Review der Session = **alles was zum Thema der Session gehoert** (angefasste/besprochene Files — transcript-getrieben, wie zuvor Modus B, jetzt klar als THEMA-Scope benannt). **NICHT das ganze Repo** — Klarstellung gg. „Full-Scan"-Missverstaendnis; repo-weit bleibt das explizite Override `all`. Jedes weitere Review der Session = nur das Delta seit dem letzten Review **+ NEU Phase 1D: Re-Verify der Vorbefunde** — laedt die `findings.json` des letzten Runs (Pfad aus dem Marker), checkt jede `file:line` frisch (carried-over = noch da/gleiche F-ID, resolved = weg/gefixt); breiter als Phase 7 (laeuft auch ohne Fix). **Phase 1.0 Session-Gate** entscheidet zuerst (Marker-Lookup → THEMA vs INKREMENTELL), Override schlaegt das Gate; 1A/1B sind jetzt nur noch die INKREMENTELL-Mechanik. Marker speichert zusaetzlich den `findings.json`-Pfad. findings.json: `scope_mode` topic/incr-Werte + neues `prev_findings_recheck`. Outcome-Ledger: resolved-nach-Fix→verified, wieder-da→regression.
- **v4.2.0 (2026-06-04):** **Cross-Model-Skeptiker im FN-Pass (Phase 5.6 Schritt 3.5) — Multi-AI-Anbindung wird real genutzt.** Claude-interne Skeptiker teilen alle Claudes Blind-Spots; ein Modell mit anderer DNA (Gemini gratis, Codex-ready) faengt eine Fehlerklasse die Claude strukturell uebersieht. „Think-Mode": externes Modell bekommt Diff + nur Finding-Titel (kein Anchoring), sucht Uebersehenes. Via `scripts/cross_model_skeptic.py` (provider-abstrahiert: heute gemini via gemini_call.py/getrackt, `--provider codex` vorbereitet). Best-effort: Auth/Quota/Provider-Fehler → degrade + Trace-Notiz, Review unberuehrt. Cross-Model-Befunde `[cross-model:<provider>]`-markiert, gehen durch denselben 5.5-FP-Filter. Verifiziert: Gemini fand im Test einen Overdraft-Bug den der Type-Hint-Finding uebersah. Macht aus „Gemini-Bridge gebaut" → „nuetzt real im Review". **Selbstlern-Schleife (der Nutzer — „dass er sich selbstaendig mit Memory + Graph verbessert / selbstaendig lernt").** Geschlossener Kreis in 3 Stufen: **Phase 0 Recall** (liest verifizierte Outcome-Historie vor jedem Run → wiederkehrende FP runterstufen, chronische Hotspots priorisieren, frueher uebersehene Bug-Klassen gezielt pruefen) · **Phase 6.5D Outcome-Ledger** (schreibt NUR verifizierte Verdikte aus 5.5/5.6/7 — Provenance-Gate im Backbone `review_learn.py` blockt rohe Findings → kein Feedback-Loop) · **Wochen-Routine `review-weekly-learn`** (Stufe 3 Meta-Evolution: `consolidate` schlaegt Kern-Skill-Verbesserungen vor, auto-apply NUR auf gelernte Schicht, Kern-Aenderungen an der Nutzer). Layer-Trennung: `review_learned.json` ist Daten, Kern-SKILL.md bleibt schlank + stabil. Guardrails: verifizierte Provenance · downrank-nie-silent-drop · human-gegate Kern-Edits. Flag `--no-learn`. Neue Datei `scripts/review_learn.py` + `REVIEW_LEARN_RUNBOOK.md`.
- **v4.0.0 (2026-06-03):** **Intensiv-Ueberarbeitung (der Nutzer — „auf einmal statt hier und da", A-H).**
  - **A — Adversarial False-NEGATIVE-Pass (Phase 5.6):** frischer Skeptiker jagt einen realen Bug den KEIN Reviewer fand (bekommt Diff + nur Finding-Titel gegen Ankern). Clean nur mit Negative-Evidence-Liste (≥3 Checks). Gegenstueck zum FP-Filter — Kern von „mehr Fehler finden".
  - **B — Git-Diff-bewusster Scope (Phase 1A):** echte geaenderte Hunks via `git diff` statt mtime; mtime-Fallback (1B) wenn kein Git. Marker speichert jetzt auch git-sha.
  - **C — Hunk-Coverage-Ledger (Phase 1C):** jeder geaenderte Hunk bekommt Status reviewed-clean/finding/skipped → kein „Datei reviewed"-Handwaving; ungepruefte Hunks = Coverage-Finding.
  - **D — Confidence-Routing:** Reviewer-`confidence`-Feld steuert den 5.5-Skeptiker (low-confidence → Skeptiker egal welche Severity; high-confidence HIGH → optional, Token-Spar). War vorher totes Feld.
  - **E — Sprach-bewusstes SAST-Routing (K4):** PSScriptAnalyzer (.ps1), eslint/biome (.js/.ts), shellcheck (.sh) — PowerShell-Hooks + JS-Viewer wurden bisher von KEINEM Tool geprueft.
  - **F — findings.json als Single-Source-of-Truth:** Report/Tracker/Memory aus EINER Datei abgeleitet statt 3× Markdown-Parse → Drift-Schutz.
  - **G — Slimming/Restruktur:** Severity-Anker (war 3× dupliziert Phase 3/4.5/5.5) → ein KANON-Block (K2); Anti-Patterns→K3; Pseudocode-Loop raus → kompakte Convergence-Regel; CAPS-Dichte runter. Eigenes v3.3.1-Changelog hatte das als Overtrigger-Risiko + Token-Waste geflaggt. Zuverlaessigere Instruction-Befolgung (weniger Lost-in-the-Middle).
  - **H — Run-Budget (K5):** Gesamt-Token/Wall-Clock-Backstops mit graceful degrade (Graph zuerst skippen) + `all`-Scope-Vorwarnung.
  - Zusaetzlich verankert: security-reviewer Inline-Fallback bei nicht-Git-Worktree; Sub-Agent Read-Disziplin (Read-Tool only, kein PowerShell-Get-Content).
- **v3.6.0 (2026-06-02):** 3 Recall-Booster — Tests AUSFUEHREN (pytest/Smoke statt Existenz; Fail=HIGH), Adversarial FP-Filter (Phase 5.5), Achse D Blast-Radius/Caller-Check.
- **v3.5.0 (2026-06-02):** Phase 7 Fix-Verification-Loop (Pflicht) — Fixes funktional gegenpruefen, Restbefund → Re-Review (max 2 Zyklen).
- **v3.4.0 (2026-06-02):** Problem-Tracker-Auto-Feed (Phase 6.5 C), MEDIUM+ → `problem.py`, Flag `--no-problems`.
- **v3.3.4 (2026-05-29):** gstack-Best-of (score-frei) — Error & Rescue Map (Achse B), Coverage-Rubrik ★★★/★★/★.
- **v3.3.3 (2026-05-29):** Output-Dir `~/.claude/reviews/` → `~/.claude/reports/review/`.
- **v3.3.1 (2026-05-28):** Lyra-v4.8-Audit — Header-Drift-Fix, Coverage-statt-Filtering (Opus-Recall-Paradox). Flaggte: Anker-3×-Duplikat + CAPS-Overtrigger (→ in v4.0 G behoben).
- **v3.3.0 (2026-05-28):** Wissens-Persistenz Phase 6.5 (Memory + Graphify, Pflicht).
- **v3.2.0 (2026-05-28):** Chat-bewusster Auto-Scope (Modus A/B, Session-Marker).
- **v3.1.0 (2026-05-19):** Functional-Logic-Flow-Audit Phase 4.5 (Achsen A/B/C).
- **v3.0.0 (2026-05-18):** Pflicht-Self-Review-Loop Phase 5.5 (analog Lyra v4.6).
- **v2.0 (2026-05-16):** Major-Rewrite — Auto-Scope, Sub-Agent-Dispatch, Pre-Flight, Regression-Tagging, Anti-Patterns, Severity-Anker, Pyramid-Test, Discord-Notify.
- **v1.0 (2026-04-30):** Erste Version — sequentielle Calls, statischer Scope.

## Beispiel-Triggers
- `/review` — erstes Mal in der Session: alles zum Session-Thema; danach: nur Delta seit letztem Review + Vorbefunde re-checken (mit Pflicht-Loops)
- `/review projekt` — **komplettes Projekt**: ganzes Repo, Code-Achsen A-D **+ Projekt-Achsen E-J** (Architektur, Doku, Config, Hygiene, Betrieb, Ziel-Abgleich). Budget-Warnung K5
- `/review all` — identisch zu `projekt` (Alias)
- `/review --projekt` — Achsen E-J auch im kleinen Session-Scope erzwingen
- `/review --no-projekt` — nur Code-Achsen (Token-Druck)
- `/review projekt --council` — erlaubt zusaetzlich die teure Deliberation (`/council --triad`, ~23k). Ohne das Flag feuern nur die billigen Einzel-Mitglieder C1-C5 (~1,5k je, max 3)
- `/review --no-council` — Council-Trigger abschalten (Default ist AN)
- `/review setup` — nur `~/.claude/`
- `/review cogs/scheduler_cog.py` — einzelnes File
- `/review --since 2026-05-10` · `/review --perf` · `/review --verify-fixes`
- `/review --no-loop` — **NUR Notfall** (Cap=1, Loop laeuft 1× fuer Trace)
