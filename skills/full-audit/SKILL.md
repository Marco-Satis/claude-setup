---
name: full-audit
version: 2.3.0
last-reviewed: 2026-08-13
description: Echter Multi-Agent-Schwarm fuer komplette Projekt-Audits. Parallel-dispatcht 5 Spezial-Reviewer (security, async, dependency, audio-pipeline, perf), synthetisiert Ergebnisse via synthesizer-Agent, dann Pflicht-Iterativer-Self-Review-Loop (Phase 3.5, Cap 4, analog /review v3.0 fuer Schwarm-Scope). Nutze fuer Pre-Release, Quartals-Reviews oder nach groesseren Refactors.
when_to_use: full audit (komplette Codebase), schwarm review (5 parallele Spezial-Reviewer), pre-release audit, quartals-review, master review der gesamten Projekt-Architektur, post-refactor audit groesserer Aenderungen (>10 Files). Fuer Session-Diff oder inkrementellen Pre-Commit-Check siehe review-Skill.
argument-hint: Optional Pfad-Filter (z.B. "modules/database") oder Scope ("full" | "discord" | "footstep")
userInvocable: true
allowed-tools: Read Glob Grep Bash Write Agent
---

# Full-Audit — Multi-Agent-Schwarm-Orchestrator

Du dispatchst 5 unabhaengige Reviewer parallel, sammelst deren Reports und
laesst synthesizer einen Master-Report bauen. Du selbst machst KEIN Review —
nur Koordination und Synthese-Bewertung.

> **Projekt-Ebene mitfahren (ab review v4.5, 2026-08-02).**
> Die 5 Reviewer hier decken **Code** ab. Architektur/Duplikate, Doku-Drift, Config/Env/Deploy,
> Repo-Hygiene, Betrieb und Ziel-Abgleich stehen als **Achsen E-J** kanonisch in
> [`_shared/projekt-achsen.md`](../_shared/projekt-achsen.md) (Vorlauf-Befehle inkl. `$PRUNE`,
> Delegations-Tabelle, Kriterien je Achse), Severity-Anker als **K2p** in
> [`_shared/severity-anchors.md`](../_shared/severity-anchors.md). Ablaufsteuerung — Gating,
> Council-Trigger C1-C5, Ehrlichkeits-Pflicht — siehe [`review/SKILL.md`](../review/SKILL.md)
> Phase 1E/4.6 und K6.
>
> Bei `full`-Scope alle sechs Achsen **voll** mitfahren (mechanischer Vorlauf zuerst, dann
> bewerten — nie umgekehrt) und als Master-Section „Projekt-Achsen (E-J)" ausweisen.
> **Hier nichts duplizieren** — geaendert wird nur im Shared-File, sonst driften die Skills
> auseinander (Audit-Fund M1-Muster).
>
> Abgrenzung: `/review projekt` = ein Orchestrator, alle Achsen, Selbstlern-Schleife + findings.json ·
> `full-audit` = 5-Agent-Schwarm mit eigenen Reviewer-Reports fuer Quartals-/Pre-Release-Audits.

## Vor dem Start

- **Repo-Root identifizieren**: aus cwd ableiten (Discord_Bots, FootstepAnalyzer, etc.)
- **Scope-Argument auswerten**:
  - `full` (default): alle Domaenen
  - `discord`: nur Discord_Bots-relevante Reviewer (skip audio-pipeline)
  - `footstep`: nur FootstepPro-relevante Reviewer (skip async)
  - Pfad-Filter: ggf. an Reviewer als `path:` weitergeben
- **Output-Ordner anlegen**:
  `<cwd>/audits/full_audit_<YYYY-MM-DD-HHMM>/` mit Subfolders pro Reviewer

## 4-Phasen-Workflow

### Phase 1 — Dispatch (parallel)

**Schicke 5 Agent-Calls in EINEM Message-Block** (max-Parallelitaet 5, Anthropic-Best-Practice):

| # | Agent | Auftrag |
|---|-------|---------|
| 1 | `security-reviewer` | SAST, CWE-Mapping, Secret-Scan, Threat-Modeling |
| 2 | `async-reviewer` | Async-Korrektheit, Race-Conditions, Discord-Rate-Limits, RCON-Leaks |
| 3 | `dependency-auditor` | pip-audit, Slopsquatting-Check, Lockfile-Pinning |
| 4 | `audio-pipeline-reviewer` (nur bei FootstepPro) ODER `review-agent` (Discord_Bots) | DSP-Korrektheit ODER generische Code-Quality |
| 5 | `perf-agent` | cProfile-Hotspots, Memory-Leak-Scan, tracemalloc-Snapshots |

**Pro Agent gib ueber:**
- Klaren Scope (Pfade, Module, Funktionen)
- **Schreib-Disziplin (v2.3):** „Aendere keine Quelldateien — dein Output ist dein Report, Fixes schlaegst du als Diff vor." Vier dieser fuenf Agents haben `Write`/`Edit` in ihrer Definition; fuenf gleichzeitige Laeufe ohne diese Ansage koennen sich in derselben Datei ueberschreiben, ohne dass der Verlierer es merkt. Soll ein Agent im Ausnahmefall wirklich editieren, bekommt er `isolation: "worktree"` und arbeitet auf einer eigenen Repo-Kopie; der Hauptloop uebernimmt den Diff bewusst. Details + Begruendung: `/review` v4.6, Abschnitt „Schreib-Disziplin bei Parallel-Dispatch".
- Output-Pfad: `<audit-folder>/<agent-name>_report.md`
- Time-Budget-Hinweis: max 15 Minuten pro Reviewer
- Format-Anforderung: Markdown mit Findings-Table (Severity, Pfad:Zeile, Beschreibung, Fix-Vorschlag)
- Coverage-statt-Filtering (Opus-4.7-Recall-Paradox): im Sammel-Schritt jedes Finding inkl. unsicherer/low-severity melden mit Konfidenz+Severity — NICHT vorab filtern. Synthese/Self-Review-Loop rankt. Opus 4.7 befolgt „nur Wichtiges" zu treu → Recall sinkt.
- (review-agent/async-reviewer) Error & Rescue Map (adopt gstack): pro Error-Handling-Funktion Methode→benannte-Exception→Rescue→sichtbares-Outcome; catch-all ohne sichtbare Konsequenz = silent failure (HIGH bei Persistence/Security). Test-Coverage-Rubrik ★★★ Behavior+Edges+Errors / ★★ Happy-Path / ★ Smoke (Coverage-TYP, kein Quality-Score).

**Anti-Patterns vermeiden:**
- KEIN „MUST"/„CRITICAL"-Kraftausdruck im Prompt (Claude 4.6/4.7 ignoriert)
- KEINE Scaffolding-Phrasen wie „Bitte gruendlich analysieren"
- Explizite Output-Struktur statt Floskeln
- Kein 6. Parallel-Agent — Tool-Budget-Overflow ueber 5 nachweislich (Anthropic-Empfehlung)

### Phase 2 — Sammeln

- Auf Completion aller 5 Agent-Calls warten (Background oder synchron)
- Pro Agent: Output-Datei einlesen, Findings-Count zaehlen
- Bei Agent-Failure: in `<audit-folder>/dispatch_failures.md` notieren, weiter mit Rest

### Phase 3 — Synthese

**Synthesizer-Agent aufrufen** (1 Call, sequenziell nach Phase 2):

```
Agent({
  subagent_type: "synthesizer",
  description: "Master-Report aus 5 Reviewer-Outputs",
  prompt: "Lies die 5 Reports in <audit-folder>/. Erzeuge MASTER_REPORT.md mit:
    1. Executive Summary (max 200 Worte)
    2. Cross-Cutting-Findings (Themen die mehrere Reviewer ansprechen)
    3. Severity-Sortierte Top-10 Findings (CRITICAL > HIGH > MEDIUM > LOW)
    4. Tech-Debt-Section (v1.1): aggregierte Liste struktureller Schwaechen
       die kein direktes Risiko sind aber wachsen werden — Duplikate, Magic
       Numbers ohne Konstante, fehlende Type-Hints in oeffentlichen APIs,
       inkonsistente Logger-Verwendung, hardcoded Pfade, fehlende Docstrings
       in kritischen Modulen. Pro Item: File:Zeile + Aufwand-Schaetzung.
    5. Roadmap mit Etappen-Vorschlag (SOFORT / DEMNAECHST / BACKLOG / TECH-DEBT)
    6. Skill-/Hook-Empfehlungen (was haette das Finding praeventiv verhindert?)
    KEINE neuen Findings erfinden, nur konsolidieren."
})
```

**Tech-Debt-Kalibrierung** (v1.1, Adoption aus Cowork `engineering:tech-debt`):
- Tech-Debt-Items sind NICHT identisch mit LOW-Severity-Findings
- Tech-Debt = strukturelle Last die Wartungs-Aufwand erhoeht ueber Zeit
- Beispiele: doppelte SQL-Helper-Funktionen, Logger-Mix (`print` + `logger`),
  Magic-Numbers ohne Konstante, fehlende Tests in alten Modulen
- Roadmap-Vorschlag: 1-2 Tech-Debt-Items pro Sprint adressieren, nicht als
  separaten Refactor-Sprint planen (Big-Bang-Refactor-Anti-Pattern)

### Phase 3.5 — Iterativer Self-Review-Loop (PFLICHT seit v2.0)

Nach Phase 3 (Initial-Synthese durch synthesizer-Agent) wird der Master-Draft **selbst als Vorgabe** in einen mehrstufigen Self-Review-Pass gefuettert. Loop laeuft IMMER, **kein Skip vorgesehen** — sichtbarer Trace verhindert heimliches Umgehen.

**Begruendung fuer groesseren Loop als bei /review (Cap 4 statt 3):** Schwarm-Reports mit 5 parallelen Reviewer-Sichten haben mehr Konsolidierungspotenzial. Cross-Reviewer-Widersprueche (security vs review-agent auf gleicher Stelle, async vs perf bei Hot-Path-Locks) brauchen eigenen Pass. Coverage-Matrix ist 5×N statt 2×N.

#### Loop-Logik (pseudo)

```python
iteration = 1
current_master = <Phase-3-Output von synthesizer>
findings_history = []
TOKEN_BUDGET_PER_ITER = 40000   # Hoeher als /review wegen Schwarm-Scope
TOKEN_BUDGET_TOTAL = 100000     # Additiv zur Initial-Synthese

while iteration <= 4:
    new_findings = self_review_pass(current_master, iteration)

    if not new_findings:
        convergence = "clean"
        break

    if findings_history and (new_findings == findings_history[-1]):
        convergence = "stuck"
        break

    if iter_tokens > TOKEN_BUDGET_PER_ITER:
        convergence = "explosive"
        break

    findings_history.append(new_findings)
    current_master = apply_findings(current_master, new_findings)
    iteration += 1
else:
    convergence = "cap"
```

#### Convergence-Kriterien

| Modus | Ausloeser | Bedeutung |
|---|---|---|
| `clean` | keine neuen Findings, Master konsistent | Idealfall — Master-Report publikationsreif |
| `stuck` | identische Findings 2× hintereinander | Strukturell nicht entfernbar — der Nutzer-Review-Empfehlung |
| `cap` | 4 Iterationen erschoepft | Letzter Stand mit Hinweis ausgeben |
| `explosive` | Iteration produziert auffällig viel Output ODER wiederholt frühere (Richtwert ~40k Token, aber qualitativ — Modell misst eigene Tokens nicht exakt) | Letzte stabile Iteration ausgeben |

#### Self-Review-Fokus pro Iteration

**Iter 1 → 2: Whitewashing + Severity-Recalibration** (analog /review v3.0 Iter 1)
- Anti-Pattern-Phrasen entfernen (Kraft-Adjektive, Score-Vergaben, Empfehlungs-Floskeln, Production-Ready-Behauptung)
- Executive-Summary NEGATIV-FIRST pruefen (kein „Insgesamt solide…")
- Severity-Anker-Drift pro Finding pruefen (kanonische Kalibrierungs-Anker: `~/.claude/skills/_shared/severity-anchors.md` K2)
- Severity-Inflation/-Deflation aus Sub-Reports erkennen

**Iter 2 → 3: Cross-Reviewer-Konsolidierung + False-Positive-Filter** (neu vs /review wegen 5 Reviewer)
- Cross-Reviewer-Widersprueche aufloesen:
  - security-reviewer sagt CRITICAL, review-agent sagt MEDIUM → Master-Entscheidung mit Begruendung
  - async-reviewer sagt Race-Condition, perf-agent sagt Hot-Path-Lock → konsolidieren ob beides oder eines reicht
- Gleiche Wurzel-Cause in 3+ Files → 1 konsolidiertes Finding "Pattern X in N Files: <Liste>"
- False-Positives erkennen (Tool-Artefakte aus bandit/semgrep/pip-audit die nicht exploitable sind)
- Bei Finding mit grenzwertiger Reproducibility: mit `[VERIFIED: <wie>]` taggen

**Iter 3 → 4: Coverage-Matrix + Tech-Debt-Konsistenz**

Coverage-Matrix bauen: **5 Reviewer-Achsen × N Module**
- Achsen: Security / Async / Dependency / Audio-Pipeline (oder Quality) / Perf
- Module: aus Scope-Argument ermittelte Files-Liste
- Pro Zelle: gepruef / explizit-skipped / nicht-anwendbar (z.B. audio-pipeline auf web/routes nicht-anwendbar)
- Luecken explizit benennen: „Achse X auf Modul Y nicht gepruef WEIL <konkret>"

Tech-Debt-Section pruefen (v1.1-Adoption beibehalten):
- Tech-Debt-Items sind NICHT identisch mit LOW-Findings — strukturelle Last
- Liste konsistent? Aufwand-Schaetzungen plausibel? Roadmap-Verteilung 1-2 Items pro Sprint?

**Iter 4 → final: Final-Polish**
- Roadmap-Sortierung (SOFORT/DEMNAECHST/BACKLOG/TECH-DEBT)
- Skill/Hook-Empfehlungen haben ≥2 Finding-Belege?
- Discord-Notify-Payload korrekt (nur CRITICAL/HIGH triggern)?
- Top-10-Findings-Liste passt zur Severity-Verteilung in Findings-Tabelle?

#### Output-Verhalten (Pflicht-Trace, IMMER sichtbar)

Master-Report bekommt am Ende eine Section **"Self-Review-Loop"** analog /review v3.0:

```markdown
## Self-Review-Loop

**Iterationen:** 3 (convergence: clean)

**Iteration-Trace:**
- Iter 1: 5× Severity-Recalibration (3 HIGH → MEDIUM, 2 MEDIUM → LOW), 2× Whitewashing-Phrase aus Exec-Summary entfernt
- Iter 2: 4 Cross-Reviewer-Widersprueche aufgeloest (security vs review-agent, async vs perf), 8 Findings mit gleicher Wurzel zu 1 Pattern konsolidiert, 3 False-Positives entfernt
- Iter 3 (clean): Coverage-Matrix vollstaendig, Tech-Debt konsistent

**Severity-Adjustments durch Loop:**
- F003 (admin_bot.py:64) HIGH → MEDIUM (Severity-Anker: Hardcoded Pfad)
- F007 (db_manager.py:118) HIGH → MEDIUM (Severity-Anker: f-string SQL aber whitelist-validiert)
- ...

**Cross-Reviewer-Konsolidierungen:**
- F009 (web/routes/sse_route.py:42): security-reviewer CRITICAL + review-agent MEDIUM → konsolidiert HIGH mit Begruendung „exploitable via UNAUTH-User aber Pre-Condition Browser-WebSocket"
- ...

**False-Positives entfernt:**
- F011 (bandit-Output auf subprocess mit konstanten Args, verifiziert)
- F018 (semgrep-FP: f-string in test-Datei)
```

Bei `clean` nach Iter 1: trotzdem Trace mit konkreten Checks.
Bei `stuck`/`cap`/`explosive`: zusaetzlich Verbleibende-Findings-Section + der Nutzer-Empfehlung.

#### Loop-Anti-Patterns

| Pattern | Vermeidung |
|---|---|
| Loop heimlich skippen weil "synthesizer hat schon konsolidiert" | Self-Review-Section ist Pflicht-Output mit Trace |
| Findings neu erfinden im Loop | Nur Iter-Foki anwenden, keine neuen Achsen on-the-fly |
| Cross-Reviewer-Widerspruch nicht aufloesen ("beide haben Recht") | Master-Entscheidung mit konkreter Begruendung Pflicht |
| Coverage-Luecke verstecken | Explizit benennen: „Achse X auf Modul Y nicht gepruef WEIL …" |
| Iter > 25k Tokens nicht abbrechen | `explosive`-Backstop, letzte stabile Iteration ausgeben |

### Phase 3.6 — Cross-Model-FN-Pass (optional, v2.1 — andere Modell-DNA, 2026-06-04)

Analog `/review` Phase 5.6: alle 5 Schwarm-Reviewer sind Claude → teilen Claudes Blind-Spots. EIN externes Modell (Gemini gratis, Codex code-spezialisiert) jagt einen Defekt den der ganze Claude-Schwarm uebersah. „Think-Mode": Diff + nur Finding-Titel (kein Anchoring).

```bash
git diff <range> --unified=0 | python ~/.claude/scripts/cross_model_skeptic.py \
  --findings "<konsolidierte F-IDs + file:line, NUR Titel>" [--provider gemini|codex]
```

- Best-effort: Exit `3`(auth)/`4`(quota)/`1` → degrade, Trace-Notiz „Cross-Model-Pass skipped: <grund>", Audit unberuehrt.
- Ueberlebender Befund → durch den Self-Review-FP-Filter (Phase 3.5), dann in Master + Tracker. Markieren `[cross-model:<provider>]`.
- Lohnt bei grossem Schwarm-Audit (Pre-Release/Quartal) wo die Modell-Diversitaet den meisten Wert bringt. Provider-Wahl: Gemini fuer breit/gratis, Codex fuer subtile Code-Bugs.

### Phase 4 — Liefern

**Chat-Output (max 30 Zeilen):**
```
SCHWARM-AUDIT abgeschlossen: <audit-folder>/

5 Reviewer parallel:
  security-reviewer:   X findings (Y CRITICAL, Z HIGH)
  async-reviewer:      X findings
  dependency-auditor:  X findings
  <domain>-reviewer:   X findings
  perf-agent:          X findings

Self-Review-Loop: <N> Iter (convergence: <clean|stuck|cap|explosive>)
  Iter 1: <kurz>
  Iter 2: <kurz>
  ...

Master-Report: <audit-folder>/MASTER_REPORT.md
Top-3 SOFORT-Aktionen:
  1. ...
  2. ...
  3. ...

Naechster Schritt: der Nutzer priorisiert in MASTER_REPORT.md
```

**Discord-Notify** über `~/.claude/rc-notify.sh "<Titel>" "<Text>"` (kanonischer Kanal, [`rules/discord-notify-channel.md`](../../rules/discord-notify-channel.md)): Titel, Severity-Counts, Top-3 Findings, Master-Pfad. Auf dem PC ist der Wrapper ein No-op → dort `CLAUDE_DISCORD_BOT_TOKEN`/`CLAUDE_DISCORD_CHANNEL_ID`; kein Weg verfügbar → skippen **mit Notiz im Master**. <!-- korrigiert 2026-08-02: stand `DISCORD_NOTIFY_WEBHOOK` — existiert im Setup nirgends, Notify war ein stiller No-op -->
Webhook-Wert nie loggen oder in den Report schreiben.

## Constraints

- **Max 5 parallel Agents** — strict (Anthropic-Best-Practice ueber 80-Tool-Budget-Schwelle)
- **Kein Auto-Apply von Fixes** — nur Report, der Nutzer entscheidet
- **Token-Budget pro Reviewer ≤ 50K** — bei Ueberschreitung fuer scope-Filter argumentieren
- **Phase 3.5 Self-Review-Loop ist PFLICHT** (Cap 4, kein Skip, sichtbarer Trace im Master + Chat)
- **Token-Budget Loop:** 40k/Iter Hard-Cap, 100k Gesamt-Loop (additiv zur Initial-Synthese)
- **Reports versionieren** — Audit-Folder mit Zeitstempel, kein Overwrite
- **Synthesizer macht KEINE eigenen Findings** — nur Konsolidierung
- **Loop macht KEINE neuen Findings** — nur Iter-Foki (Whitewashing/Severity/Cross-Reviewer/Coverage/Polish)

## Few-Shot — Skill-Empfehlungen aus Findings

| Finding-Pattern | Skill/Hook-Empfehlung |
|----------------|----------------------|
| Mehrere f-string SQL-Queries (CWE-89) | Pre-Commit-Hook fuer `\.execute\(f"` Pattern |
| Hardcoded Tokens entdeckt | detect-secrets-hook in Pre-Commit + token-rotation-skill |
| RCON-Connection nicht geschlossen | async-context-manager-Skill + linter-rule |
| Outdated Dependencies (>6 Monate alt) | Weekly /deps-check Scheduled Task |
| Tracemalloc-Snapshots fehlen | /mem-snapshot Skill + Stop-Hook fuer Memory-Spikes |
| Tool-Budget-Overflow (>80 Tools verfuegbar) | MCP-Scoping pro Sub-Agent (`mcpServers: []`) + Plugin-Audit |
| Hook-Failure silent unbemerkt | `~/.claude/hooks/_health_check.py` als SessionStart-Hook |
| Marker-Token-Drift (CLAUDE.md vs Hooks vs Rules) | `claude-md-management:claude-md-improver` monatlich |

## Anti-Patterns (was NICHT tun)

- Kein einzelner "uber-reviewer" der alles macht (Single-Point-of-Context-Failure)
- Keine Reviewer-Outputs in Main-Context laden (>5K Zeilen pro Report moeglich)
- Kein Schwarm-Loop ohne Iterations-Cap (max 3 Schwarm-Runs pro Tag — separate Sache als Phase 3.5 Self-Review-Loop)
- Keine implizite Generalisierung „audit alles" — immer Scope explizit setzen
- Self-Review-Loop NICHT skippen — Phase 3.5 ist Pflicht, Trace ist Pflicht-Output

## Changelog

- **v2.2.0** (2026-08-02): **Projekt-Ebene + Notify-Fix.** Verweist im Kopf auf die kanonischen **Achsen E-J** in `_shared/projekt-achsen.md` (Architektur, Doku-Drift, Config/Env/Deploy, Repo-Hygiene, Betrieb, Ziel-Abgleich) statt sie zu duplizieren — bei `full`-Scope voll mitfahren, mechanischer Vorlauf immer vor der Bewertung. Ablaufsteuerung (Gating, Council-Trigger C1-C5) bleibt in `review/SKILL.md`. **Discord-Notify korrigiert:** stand auf `DISCORD_NOTIFY_WEBHOOK` — diese Variable existiert im Setup nirgends, das Notify war ein stiller No-op; jetzt `rc-notify.sh` bzw. Bot-Token auf dem PC, kein Weg verfuegbar → skippen MIT Notiz.
- **v2.1.0** (2026-06-04): **Phase 3.6 Cross-Model-FN-Pass** (optional) — externes Modell (Gemini gratis / Codex code-spezialisiert) jagt einen Defekt den der ganze Claude-Schwarm uebersah (andere DNA), analog `/review` Phase 5.6. Via `cross_model_skeptic.py`, best-effort (degrade bei auth/quota), Befund durch FP-Filter, `[cross-model:<provider>]`-markiert. Anlass: Multi-AI-Setup live.
- **v2.0.2** (2026-05-29): gstack-Best-of + Audit-Recs — Reviewer-Brief um Error&Rescue-Map + Coverage-Rubrik (★-Typ) + Recall-Paradox-Coverage erweitert; explosive-Backstop qualitativ (Modell misst Tokens nicht exakt).
- **v2.3.0** (2026-08-13): Schreib-Disziplin im Dispatch — vier der fuenf Reviewer haben `Write`/`Edit`; Default ist jetzt read-only (Fix als Diff im Report), echte Edits nur mit `isolation: "worktree"`. Verhindert stille gegenseitige Ueberschreibungen bei 5 parallelen Agents. Quelle: TikTok-Findings-Triage 2026-08-12 (`#60`/`#96`), Begruendung in `/review` v4.6.
- **v2.0.1** (2026-05-29): Lyra-Audit — Recall-Paradox-Coverage im Dispatch, Token-Budget qualitativ.
- **v2.0.0** (2026-05-18): Pflicht-Iterativer-Self-Review-Loop (Phase 3.5) analog /review v3.0 fuer Schwarm-Scope.
  - Cap 4 (groesser als /review weil Schwarm mehr Konsolidierung braucht)
  - Iter-Foki: Iter 1 Whitewashing+Severity, Iter 2 Cross-Reviewer-Konsolidierung+False-Positive, Iter 3 Coverage-Matrix+Tech-Debt-Konsistenz, Iter 4 Final-Polish
  - Token-Budget 40k/Iter, 100k Gesamt-Loop
  - Iteration-Trace Pflicht-sichtbar in MASTER_REPORT.md + Chat-Output
  - Convergence-Modi clean/stuck/cap/explosive
- **v1.2.0** (2026-05-17): Tech-Debt-Section + Kalibrierung (Adoption aus Cowork `engineering:tech-debt`).
- **v1.1.0** (2026-05-15): Initial Schwarm-Pattern (5 parallel + synthesizer).
- **v1.0.0** (2026-05-10): Erste Version.
