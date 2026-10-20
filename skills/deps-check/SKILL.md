---
name: deps-check
version: 2.0.0
last-reviewed: 2026-05-17
description: Dependency-Vulnerability-Audit — orchestriert dependency-auditor-Subagent für pip-audit (CVE-Scan), Slopsquatting-Detection, Lockfile-Pinning, Outdated-Pakete. Lokal + Server (via SSH). Nutze wöchentlich oder bei CVE-Alerts.
when_to_use: dependency audit, pip-audit, CVE check, slopsquatting detection, lockfile hygiene, package vulnerability, requirements.txt review, npm audit, supply chain audit
argument-hint: Optional requirements-Datei-Pfad oder "server" für Remote-Audit auf netcup-server
allowed-tools: Read Grep Bash Glob Agent Write
userInvocable: true
model: sonnet
---

# Deps-Check — dependency-auditor-Orchestrator

Zweck: Dependency-Audit für lokale und Server-Repos. Master orchestriert `dependency-auditor`-Subagent, **kein eigener Audit**.

## Vor dem Start (Pre-Flight)

1. **Requirements-Datei finden:**
   - Argument-Pfad → direkt
   - Default: `git ls-files | grep -E 'requirements.*\.txt$|pyproject\.toml$|package\.json$'`
2. **Tool-Check:**
   ```bash
   pip-audit --version 2>&1 | head -1
   pip show requirements-detector 2>&1 | head -1
   ```
3. **Output-Folder:** `~/.claude/reports/deps-check/<YYYY-MM-DD-HHMM>/`

## Phase 1 — Subagent-Dispatch

```
Agent({
  subagent_type: "dependency-auditor",
  description: "Dependency-Audit für <files>",
  prompt: "Audit:
  1. pip-audit auf <requirements-file(s)>, JSON-Output sammeln
  2. Slopsquatting-Detection: Tippfehler-ähnliche Namen, typische Squatting-Patterns
     (z.B. 'requets' statt 'requests', 'crypotgraphy' statt 'cryptography')
  3. Lockfile-Pinning-Check: alle Pakete mit `==` gepinnt? (oder `~=` für Range)
  4. Outdated-Check: `pip list --outdated` oder Vergleich gegen PyPI
  5. License-Compatibility-Check (Quick): GPL-Verträglichkeit mit des Nutzers MIT-Code

  Output: REVIEW_REPORT_DEPENDENCIES.md mit:
  - Findings-Tabelle (Severity, Paket, Version, CVE-ID, Fix-Version, Aufwand)
  - Severity-Skala: CRITICAL (RCE/Auth-Bypass) / HIGH (Data-Leak/DoS) / MEDIUM (informational CVE) / LOW (outdated ohne CVE) / INFO
  - Update-Priorität: SOFORT (CRITICAL+HIGH) / DEMNAECHST (MEDIUM) / BACKLOG (LOW+outdated)
  - Slopsquatting-Verdachts-Liste mit Confidence
  - Raw-Outputs in RAW_TOOL_OUTPUT/

  Anti-Patterns vermeiden: Findings ohne CVE-ID, Auto-Update-Empfehlungen ohne Breaking-Change-Hinweis,
  generic 'update everything' statt priorisiert."
})
```

## Phase 2 — Server-Audit (optional, bei Argument `server` oder `all`)

```bash
ssh -p <ssh-port> <user>@<server-ip> \
  "sudo /bin/su - botuser -c 'cd /home/botuser/Discord_Bots && \
   .venv/bin/pip-audit --format json --output /tmp/pip-audit.json'"
scp -P <ssh-port> <user>@<server-ip>:/tmp/pip-audit.json \
  ~/.claude/reports/deps-check/<datum>/RAW_TOOL_OUTPUT/server_pip-audit.json
```

Hinweis: Server hat eigene venvs pro Bot. Pro Bot einzeln:
- monitor-bot, gameserver-bot, admin-bot, web-dashboard

## Phase 3 — Konsolidierung

1. Subagent-Output einlesen
2. Server- vs Lokal-Diff erstellen (Pakete die nur auf Server outdated sind)
3. Update-Roadmap erstellen:
   - SOFORT: alle CRITICAL/HIGH mit konkretem Update-Pfad
   - DEMNAECHST: MEDIUM mit Aufwand-Schätzung
   - BACKLOG: LOW + outdated-ohne-CVE
4. **Discord-Notify** bei CRITICAL/HIGH

## Phase 4 — der Nutzer-Bericht (Chat, max 25 Zeilen)

```
📦 Deps-Check — <scope>
Severity-Counts: 🔴 X | 🟠 Y | 🟡 Z | 🟢 W

SOFORT (CRITICAL/HIGH):
- <paket> <aktuelle-ver> → <fix-ver> (CVE-X — <Risiko in 1 Satz>) — `pip install <paket>>=<ver>`
- ...

Slopsquatting-Verdacht: <X Pakete> (siehe Report)

Server vs Lokal:
- <paket> nur auf Server outdated (Bot: <name>) → Update via SSH

Pfad: ~/.claude/reports/deps-check/<datum>/REVIEW_REPORT_DEPENDENCIES.md

Update-Reihenfolge:
  1. SOFORT-Items hintereinander, je Update Tests laufen lassen
  2. Bei Bot-Restart: monitor-bot zuerst, dann andere
```

## Anti-Patterns (Output-Qualität)

| Anti-Pattern | Korrektur |
|---|---|
| Findings ohne CVE-ID | Pflicht: CVE-X-Y oder GHSA-X bei GitHub-Advisory |
| „Update everything" pauschal | Priorisieren nach Severity; Breaking-Changes flaggen |
| Auto-Update ohne Test-Hinweis | „Update X → vor Deploy: alle 4 test_*.py laufen lassen" |
| Slopsquatting nicht als separates Finding | Eigene Severity-Spalte (HIGH wenn `pip install` lokal lief) |
| Server-Update ohne Restart-Reihenfolge | siehe `.claude/rules/server-edits.md` Service-Restart-Reihenfolge |

## Constraints

- **Keine Auto-Installs** — der Nutzer entscheidet pro Update
- **Server-Updates via SSH** — sudo/-su pattern, kein direkter pip-Call
- **Severity-Skala** kompatibel zu `/review`, `/security-audit`, `/full-audit`
- **Skill-Version-Header** in jedem Report
- **CVE-Datenbank** via pip-audit (NVD + PyPI Advisory DB), nicht halluzinieren

## Beispiel-Triggers

- `/deps-check` — lokal, Default-requirements
- `/deps-check server` — auf netcup-server für alle Bot-venvs
- `/deps-check all` — lokal + Server kombiniert
- `/deps-check requirements-dev.txt` — spezifisches File

## Changelog

- **v2.0.0** (2026-05-17): Standardisierung — Pre-Flight (Tool-Check), expliziter Subagent-Prompt mit 5 Audit-Phasen, Server-Audit-Section, Update-Roadmap-Format, Anti-Patterns-Tabelle, Discord-Notify, version-Frontmatter, argument-hint statt argumentHint.
- **v1.0.0** (2026-05-16): Erste Version — minimaler Subagent-Wrapper.
