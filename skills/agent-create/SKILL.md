---
name: agent-create
version: 2.0.2
last-reviewed: 2026-06-01
description: Erstellt einen neuen Sub-Agent nach der Nutzer Standard-Pattern — vollständiges Frontmatter (name, version, tools, model, maxTurns), klare Rolle, 5–8 Wichtigste-Regeln, Rules-Cross-References. Verifiziert YAML-Validität nach Write.
when_to_use: neuen sub-agent erstellen, agent anlegen, agent scaffold, neuen .claude/agents/-file erstellen, subagent template, sub-agent bauen
argument-hint: Optional Agent-Name + Domain — bei fehlend interaktive Fragen
allowed-tools: Read Write Edit Bash Glob
userInvocable: true
---

# Agent-Create — Neuen Sub-Agent erstellen

Zweck: Sub-Agent mit allen Pflicht-Feldern, korrektem Frontmatter und Modell-/Tool-Konventionen anlegen.

## Vor dem Start (Pre-Flight)

1. Argument auswerten: `name` + grobe `domain`-Beschreibung
2. Bei fehlend: der Nutzer interaktiv fragen
3. **Scope-Entscheidung:**
   - Global (`~/.claude/agents/<name>.md`) — Sub-Agent für alle Projekte
   - Projekt-spezifisch (`<projekt>/.claude/agents/<name>.md`)
4. **Namens-Check:** kebab-case, max 30 Zeichen, kein Konflikt mit existierendem Agent
5. **Klarstellungs-Fragen (max 5):**
   - Domain/Rolle in 1 Satz
   - Modell-Klasse: A (Haiku, mechanisch) / B (Sonnet, Standard) / C (Opus high, Bug-Detection) / D (Opus max, Architektur)
   - Tools nötig: nur Read/Grep oder auch Write/Edit/Bash/Glob/Agent
   - maxTurns: Default 50, mehr (100+) bei langen Refactors oder Multi-File-Audits
   - 5–8 Wichtigste-Regeln (was muss der Agent IMMER beachten?)

## Workflow

### Phase 1 — Scaffold-Generierung

Frontmatter-Pflicht-Felder:

```yaml
---
name: <kebab-case-name>
version: 1.0.0
description: <Trigger-Beschreibung — wann wird der Agent eingesetzt? Max 2 Sätze.>
tools: Read, Write, Edit, Bash, Glob, Grep    # nur die wirklich gebrauchten (komma-separiert)
model: <haiku|sonnet|opus|fable|inherit>       # Familien-ALIAS (Pinning-Politik 2026-06-12), Klasse A/B/C/D/F
maxTurns: 50                              # Default; bei Refactors höher
---
```

**Modell-Routing** (Konvention — IMMER Familien-Aliase, Voll-Versions-IDs nur bei bewusstem Reproduzierbarkeits-Pinning; Pinning-Politik 2026-06-12):
- `haiku` — Klasse A: mechanische Refactors, git-Operationen, simples Find-Replace
- `sonnet` — Klasse B: Standard-Code-Reviews, Test-Generierung, Docs
- `opus` — Klasse C: Multi-File-Bug-Detection, Security-Audits, Async-Korrektheit
- `opus` — Klasse D: Architektur-Entscheidungen, Synthese-Aufgaben (höchste Sorgfalt). „Max" = Effort/Routing-Stufe zur Laufzeit, KEIN Model-Suffix.
- `fable` — Klasse F: Long-Horizon-Autonomie, Multi-Agent-Orchestrierung (teuer — nur wenn Klasse D nicht reicht)
- `inherit` — Agent läuft auf dem Session-Modell (Default wenn unsicher)
Aliase lösen serverseitig auf die neueste Generations-Version auf → Generations-Bumps ritten automatisch mit.

### Phase 2 — Body-Struktur (Pflicht-Sektionen)

```markdown
# <Agent-Name> Sub-Agent

<1-2-Satz Rollen-Beschreibung — was kann der Agent, was nicht>

## Wichtigste Regeln

1. <Pflicht-Regel mit konkretem Beispiel>
2. <...>
5–8 Regeln, nach Priorität sortiert

## Cross-References zu Rules

- `<scope>/.claude/rules/<rule>.md` — wann der Agent diese Regel anwendet

## Anti-Patterns

| Anti-Pattern | Was tun stattdessen |
|---|---|
| <konkretes Anti-Pattern> | <Ersatz> |

## Output-Format

<Was liefert der Agent, in welchem Format>

## Beispiel-Trigger

- „Use the <name> subagent for X"
- Auto-Trigger bei <Bedingung>

## Changelog

- v1.0.0 (<datum>): Erste Version.
```

### Phase 3 — Write + Verify

1. Verzeichnis: `mkdir -p <scope>/.claude/agents/`
2. File schreiben: `<scope>/.claude/agents/<name>.md`
3. **YAML-Validität prüfen:**
   ```bash
   python -c "import yaml; d=yaml.safe_load(open('<path>').read().split('---')[1]); print('OK:', list(d.keys()))"
   ```
4. Pflicht-Felder-Check: `name`, `version`, `description`, `tools`, `model` müssen vorhanden sein
5. der Nutzer zeigen + Approval

### Phase 4 — Integration

1. Agent in globaler CLAUDE.md unter „Globale Sub-Agents" eintragen (falls global)
2. `plugin_hash_snapshot.py --update` für Hash-Drift-Detection
3. Test-Trigger: in neuer Session den Agent via `Use the <name> subagent` aufrufen

## Anti-Patterns (was NICHT tun)

| Anti-Pattern | Korrektur |
|---|---|
| Frontmatter ohne `version` | Pflicht: Semver `1.0.0` bei Erstellung |
| `tools: *` (Wildcard) | Nur Tools die wirklich gebraucht werden |
| `model` ohne Modell-Klasse-Begründung im Body | Im Body 1 Satz: „Klasse X weil Y" |
| `maxTurns: 999` ohne Grund | Default 50, höher nur bei dokumentiertem Use-Case |
| Body mit „du tust X, Y, Z" generisch | Konkrete Regeln mit Code-Beispielen |
| Sub-Agent ohne Output-Format | Pflicht: was kommt zurück, in welcher Struktur |
| Sub-Agent ohne Cross-Reference zu Rules | Rules + Conventions explizit referenzieren |

## Versions-Pflege bei späteren Updates

Bei jedem Edit:
1. Backup: `cp -a <agent>.md <agent>.md.bak.$(date +%s)`
2. `version`-Bump (Semver-Regeln wie bei `/skill-create`)
3. Changelog-Sektion erweitern

## Constraints

- **YAML-Validierung nach Write** Pflicht
- **Backup bei Updates** bestehender Agents
- **Pattern-Konsistenz** mit anderen Agents in `~/.claude/agents/` prüfen
- **Modell-Klasse explizit begründen** im Body (sonst Drift)
- **Token-Effizienz:** Body knapp, Beispiele in Cross-Reference-Rules statt inline

## Beispiel-Triggers

- `/agent-create` — interaktiv
- `/agent-create dashboard-reviewer FastAPI-Routes-Auditor` — mit Args
- `/agent-create new-agent "kurze Beschreibung"` — quoted Args

## Changelog

- **v2.0.1** (2026-05-28): Lyra-Audit-Fix — Klasse-D-Modell `claude-opus-4-7-max` → `claude-opus-4-7` (invalider Alias, kein Agent nutzte ihn; „max" ist Effort, kein Model-Suffix).
- **v2.0.0** (2026-05-17): Major-Rewrite — vollständiges Frontmatter-Template, 4-Phasen-Workflow (Scaffold / Body / Write+Verify / Integration), YAML-Validierung-Pflicht, Modell-Klassen-Konvention dokumentiert, Anti-Patterns-Tabelle, Versions-Pflege.
- **v1.0.0** (2026-05-16): Erste Version.
