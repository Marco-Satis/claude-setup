---
name: security-audit
version: 2.1.0
last-reviewed: 2026-10-18
description: Security-fokussierter Audit — orchestriert security-reviewer-Subagent für SAST (Bandit, Semgrep, detect-secrets), CWE-Mapping, Threat-Reasoning, Secret-Scan, Permission-Audit. Distinkt zu /review (Multi-Achsen) und /full-audit (5 Reviewer parallel). Abgrenzung zu /cso — security-audit = Code-SAST-Wrapper für ein konkretes Repo/Diff ("security audit" dispatcht hierher); /cso = Infrastruktur-/Setup-weiter CSO-Modus (Secrets-Archaeologie, Supply-Chain, CI/CD, daily/monatlich, Trend-Tracking).
when_to_use: security audit, SAST, vulnerability scan, CWE check, secrets scan, threat review, bandit, semgrep, detect-secrets, security review, pre-deploy security, post-incident audit
argument-hint: Optional Scope-Pfad oder "diff" für nur uncommitted Files
allowed-tools: Read Grep Bash Glob Agent Write
userInvocable: true
model: opus
---

# Security-Audit — security-reviewer-Orchestrator

Zweck: Security-tiefen Audit durch `security-reviewer`-Subagent. Master macht Orchestration + Konsolidierung, **keinen eigenen Audit**.

## Vor dem Start (Pre-Flight)

1. **Scope ermitteln:**
   - Kein Argument → aktuelles Repo (Default: cwd)
   - `diff` → nur uncommitted Files via `git diff --name-only`
   - Pfad/Glob → exakt diese Files

2. **SAST-Tool-Check:**
   ```bash
   bandit --version 2>&1 | head -1
   pip show semgrep 2>&1 | head -1
   detect-secrets --version 2>&1 | head -1
   ```
   Bei Tool-Fehlend: Subagent informieren, degraded mode.

3. **Output-Folder:** `~/.claude/reports/security-audit/<YYYY-MM-DD-HHMM>/`

## Phase 1 — Subagent-Dispatch

```
Agent({
  subagent_type: "security-reviewer",
  description: "Security-Audit für <scope>",
  prompt: "Audit-Scope: <files/repo>. SAST-Tools verfügbar: <bandit/semgrep/detect-secrets>.

  Pflicht-Phasen:
  1. Static-Analyse: Bandit + Semgrep + detect-secrets, JSON-Output sammeln
  2. Manueller Code-Walk: Auth/Crypto/SQL/Exec/Token-Pfade
  3. Permission-Audit: nginx-Configs, sudoers, file-permissions
  4. Secret-Pattern-Scan: Git-History + aktuelle Files
  5. CWE-Mapping: jedes Finding mit CWE-Kategorie + Attack-Szenario
  6. KI-Komponenten (LLM-Aufrufe, Agenten, Tool-Use, RAG): Prompt-Injection-Pfade —
     wo erreicht Fremdtext (Web, Datei, Nutzer, Tool-Ausgabe) einen Prompt, der Tools
     ausloesen oder Daten preisgeben kann?

  Coverage-statt-Filtering (Opus-4.7-Recall-Paradox): im Sammel-Schritt jedes Finding
  inkl. unsicherer/low-severity melden mit Konfidenz+Severity — NICHT vorab nach
  Wichtigkeit filtern (Opus 4.7 befolgt 'nur high-severity' zu treu, Recall sinkt).
  Ranking/Filtern passiert in der Konsolidierung.

  Output: REVIEW_REPORT_SECURITY.md mit:
  - Findings-Tabelle (ID, Severity, File:Line, CWE, Was, Warum, Fix, Aufwand)
  - Severity-Skala: CRITICAL/HIGH/MEDIUM/LOW/INFO (kanonisch: `~/.claude/skills/_shared/severity-anchors.md`)
  - Top-Threats-Section mit Attack-Szenario-Beschreibung
  - SAST-Tool-Output-Pfade (Raw-JSONs in RAW_TOOL_OUTPUT/)

  Anti-Patterns vermeiden: Kraft-Adjektive, Production-Ready-Claims, Findings ohne CWE-Mapping,
  Auto-Fix-Vorschläge ohne Risk-Assessment."
})
```

## Phase 1b — Widerlegung (Skeptiker je Finding)

Muster übernommen aus `cloudflare/security-audit-skill` (MIT), Phase 3 „Independently validate every
candidate", vereinfacht auf unseren Read-only-Rahmen. Grund: Phase 1 meldet bewusst breit
(Coverage statt Filtering) — ohne Gegenprüfung landen Falsch-Positive ungefiltert im Bericht.

1. **Wer wird geprüft:** jedes Finding CRITICAL/HIGH/MEDIUM einzeln. LOW/INFO nur, wenn es ≤ 10 sind;
   sonst bleiben sie als `ungeprüft` markiert und der Bericht nennt die Zahl (keine stille Kappung).
2. **Wer prüft:** je Finding ein **frischer** `security-reviewer`-Subagent, der es nicht gefunden hat.
   Er bekommt nur: das Finding (File:Line, Beschreibung, CWE, Szenario), die zitierten Pfade und
   nötige Architektur-Fakten — **nie** das Urteil eines anderen Skeptikers. Parallel dispatchen.
3. **Prompt (wörtlich übernehmen):**
   ```
   Du hast dieses Finding nicht geschrieben. Versuch es aus dem Quellcode zu WIDERLEGEN.
   Read-only: keinen Zielcode ausführen, keine Netzwerkzugriffe, keine Live-Endpunkte.
   1. Jede zitierte Stelle frisch mit dem Read-Tool lesen: existiert sie, zeigt sie das Behauptete?
      Ist der Einstieg wirklich ein Eingang niedrigeren Vertrauens, das Ende wirklich die Senke?
   2. Die stärksten Kontrollen auf dem Pfad rekonstruieren (Validierung, Auth, Normalisierung,
      Framework-Schutz, Deploy-Schicht wie nginx/Tailscale/Bindung an 127.0.0.1).
   3. Severity, Impact und Fix dürfen nur behaupten, was belegt ist — nichts hochrechnen.
   4. Hängt das Urteil an einem Fakt außerhalb des Codes (Deploy, Provider, Laufzeit),
      nicht raten: needs_validation mit dem exakten fehlenden Fakt und einem gefahrlosen Prüfplan.
   Antwort genau ein JSON-Objekt, keine Prosa drumherum:
   {"decision": "confirmed|needs_validation|rejected", "grund": "...", "korrektur": {...}}
   ```
4. **Auswertung:**
   - `confirmed` → bleibt, ggf. mit korrigierter Severity/Beschreibung des Skeptikers.
   - `needs_validation` → eigene Liste **ohne Severity**, mit fehlendem Fakt + Prüfplan. Kein Parkplatz
     für Spekulation: ohne konkreten fehlenden Fakt gilt `rejected`.
   - `rejected` → raus aus den Findings, in den Anhang „Widerlegt" mit Begründung (für Rückverfolgung).
   - Antwort ohne gültiges JSON → einmal mit frischem Skeptiker wiederholen, sonst `ungeprüft`.
5. Ergebnis in den Report: Abschnitt `## Widerlegung` mit Zählern
   (geprüft / bestätigt / needs_validation / widerlegt / ungeprüft).

## Phase 2 — Konsolidierung

1. Subagent-Output einlesen: `<audit-folder>/REVIEW_REPORT_SECURITY.md` plus Phase-1b-Urteile.
   Grundlage aller folgenden Schritte sind nur die **bestätigten** Findings.
2. Findings-Counts pro Severity zählen
3. **Cross-Check:**
   - CRITICAL ohne CWE-Mapping → Subagent nachfragen
   - Token-Finding ohne SHA256-Hash (nur Pattern) → ok, kein Wert leaken
   - Permission-Findings → mit `.claude/rules/server-edits.md`-Standards abgleichen
4. **Discord-Notify** bei CRITICAL/HIGH über `~/.claude/rc-notify.sh "<Titel>" "<Text>"` (kanonischer Kanal, siehe [`rules/discord-notify-channel.md`](../../rules/discord-notify-channel.md)). Auf dem PC ist der Wrapper ein No-op — dort `CLAUDE_DISCORD_BOT_TOKEN`/`CLAUDE_DISCORD_CHANNEL_ID`. Kein Weg verfügbar → Notify skippen **mit Notiz im Report**. <!-- korrigiert 2026-08-02: stand `DISCORD_NOTIFY_WEBHOOK`, die Variable existiert im Setup nirgends → Notify war ein stiller No-op -->
   Niemals den Webhook-Wert loggen oder in den Report schreiben.

## Phase 3 — der Nutzer-Bericht (Chat, max 30 Zeilen)

```
🔒 Security-Audit — <scope>
Severity-Counts (bestätigt): 🔴 X | 🟠 Y | 🟡 Z | 🟢 W
Widerlegung: N geprüft → B bestätigt, V needs_validation, R widerlegt, U ungeprüft

Top-3 Threats:
1. <file:line> — <CWE-X> — <Attack-Szenario in 1 Satz>
2. ...
3. ...

SAST-Tools: bandit (X findings), semgrep (Y), detect-secrets (Z)

Pfad: ~/.claude/reports/security-audit/<datum>/REVIEW_REPORT_SECURITY.md
Raw-Outputs: ~/.claude/reports/security-audit/<datum>/RAW_TOOL_OUTPUT/

SOFORT-Aktionen:
  1. <konkret>
  2. <konkret>
  3. <konkret>
```

## Anti-Patterns (Output-Qualität)

| Anti-Pattern | Korrektur |
|---|---|
| Findings ohne CWE-Mapping | Pflicht: CWE-ID + Link zur CWE-Datenbank |
| Findings ohne Attack-Szenario bei HIGH/CRITICAL | „Angreifer X kann durch Y Z erreichen" (1 Satz) |
| Token-Werte im Report | NIEMALS — nur Pattern-Type + SHA256-Hash-Prefix |
| „Production-ready"-Aussagen | weglassen — des Nutzers Entscheidung |
| Fix-Vorschläge ohne Risk-Assessment | „Fix: X. Risk: Y wird nicht adressiert, separate Iteration nötig." |
| Generic-Recommendations ohne File:Zeile | Pflicht: konkrete Location |
| Finding ohne Phase-1b-Urteil im Bericht | Pflicht: bestätigt / needs_validation / ungeprüft sichtbar |
| Severity für needs_validation | nein — Severity nur für bestätigte Findings |

## Constraints

- **Read-only.** Niemals Auto-Fixes
- **Severity-Skala + Anker kanonisch** aus `~/.claude/skills/_shared/severity-anchors.md` (geteilt mit `/review` + `/full-audit`)
- **Secret-Patterns** nur via Hash logged (siehe `secret_leak_detector.py`-Konvention)
- **Skill-Version-Header** in jedem Report
- **Bei Token/Key im Code-Snippet:** Subagent muss den Wert in der Ausgabe redacten

## Beispiel-Triggers

- `/security-audit` — aktuelles Repo
- `/security-audit diff` — nur uncommitted Files
- `/security-audit web/routes/` — Glob-Pfad
- `/security-audit modules/database/db_manager.py` — Einzelfile

## Changelog

- **v2.1.0** (2026-10-18): **Phase 1b Widerlegung** — je Finding ab MEDIUM ein frischer Skeptiker, der es aus dem Quellcode widerlegen soll; Urteile confirmed / needs_validation (ohne Severity) / rejected; nur Bestätigtes fließt in Konsolidierung und Bericht. Muster aus `cloudflare/security-audit-skill` (MIT, TikTok-Finding 13.10., der Nutzer-Ja 18.10.), ohne deren Sandbox-/Ausführungsteil, weil dieser Skill read-only bleibt. Dazu Pflicht-Phase 6: Prompt-Injection bei KI-Komponenten.
- **v2.0.4** (2026-08-02): **Discord-Notify korrigiert** — stand auf `DISCORD_NOTIFY_WEBHOOK`, die Variable existiert in des Nutzers Setup nirgends (0 Treffer in `~/.claude`), jedes Notify bei CRITICAL/HIGH war ein stiller No-op. Jetzt kanonisch ueber `~/.claude/rc-notify.sh` (netcup) bzw. `CLAUDE_DISCORD_BOT_TOKEN`/`CHANNEL_ID` (PC); kein Weg verfuegbar → skippen mit Notiz im Report. Webhook-Wert nie loggen.
- **v2.0.0** (2026-05-17): Standardisierung — Pre-Flight-Checks (SAST-Tools), expliziter Subagent-Prompt mit Pflicht-Phasen, Severity-Skala-Cross-Reference zu `/review`, Anti-Patterns-Tabelle, Discord-Notify, Output-Folder-Konvention.
- **v1.0.0** (2026-05-16): Erste Version — minimaler Subagent-Wrapper.
