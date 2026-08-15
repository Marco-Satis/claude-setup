---
name: skill-create
version: 2.2.0
last-reviewed: 2026-07-21
description: Erstellt einen neuen Skill nach der Nutzer Standard-Pattern — vollständiges Frontmatter, Phasen-Struktur, Constraints, Beispiel-Triggers, Versions-Header. Verifiziert YAML-Validität + Schema-Konformität nach Write.
when_to_use: neuen skill erstellen, claude code skill anlegen, skill scaffold, neuen slash-command bauen, SKILL.md erstellen, skill template, command erstellen
argument-hint: Optional Skill-Name + kurze Beschreibung — bei fehlend interaktive Fragen
allowed-tools: Read Write Edit Bash Glob
userInvocable: true
---

# Skill-Create — Neuen Skill nach der Nutzer-Standard

Zweck: Skill mit allen Pflicht-Feldern, korrektem Frontmatter und versionierbar anlegen. Verhindert „halbgar gebaute" Skills.

## Vor dem Start (Pre-Flight)

1. Argument auswerten: `name` + grobe `description`
2. Bei fehlend: der Nutzer interaktiv fragen
3. **Scope-Entscheidung:**
   - Global (`~/.claude/skills/<name>/`) — Skill für alle Projekte
   - Projekt-spezifisch (`<projekt>/.claude/skills/<name>/`) — nur in einem Repo
4. **Namens-Check:**
   - kebab-case, kein Underscore
   - max 30 Zeichen
   - kein Konflikt mit existierendem Skill (`ls ~/.claude/skills/`)
5. **Klarstellungs-Fragen** (interaktiv, max 4):
   - Trigger-Begriffe für `when_to_use` (kommagetrennt)
   - Argumente: keine / optional / required + Format
   - Modell-Empfehlung: default (vererbt) / Haiku / Sonnet / Opus
   - Tools nötig: nur Read/Grep oder auch Write/Edit/Bash?
6. **Anti-Bloat-Gate — braucht es diesen Skill überhaupt?** (geerntet aus superpowers:writing-skills v6.1.1, 2026-07-21)
   - KEIN Skill für: Einmal-Lösungen, Standard-Praxis die das Modell ohnehin kennt, Projekt-Konventionen (→ projekt-CLAUDE.md), mechanisch erzwingbare Regeln (→ Hook via `/hook-create`; Skill-Doku nur für Judgment-Calls)
   - **Ein Skill = ein Job.** Stecken zwei Jobs drin → zwei Skills, mit expliziter Abgrenzung in BEIDEN Descriptions (Muster: `cso` ↔ `security-audit`)
   - Baseline-Frage: würde ein frischer Agent die Aufgabe ohne Skill falsch machen? Wenn nein → kein Skill nötig

## Workflow

### Phase 1 — Scaffold-Generierung

Frontmatter-Pflicht-Felder (Reihenfolge wichtig):

```yaml
---
name: <kebab-case-name>
version: 1.0.0
last-reviewed: <YYYY-MM-DD>
description: <Wann triggert der Skill? Trigger-Beschreibung, nicht Funktions-Summary. Max 2 Sätze.>
when_to_use: <kommagetrennte Trigger-Begriffe + Synonyme>
argument-hint: <falls Argument vorhanden — Format + Default>
allowed-tools: <Read Grep Bash Write Edit — nur die wirklich gebrauchten>
userInvocable: true
model: <haiku|sonnet|opus|fable|inherit>   # NUR setzen wenn explizit nicht der Default; Familien-ALIAS statt Voll-ID (Pinning-Politik 2026-06-12)
---
```

**Description-Trigger-Optimierung** (geerntet aus superpowers:writing-skills v6.1.1, 2026-07-21):

- Description beschreibt NUR Trigger-Bedingungen — NIE den Workflow zusammenfassen. Grund: fasst die Description den Prozess zusammen, folgt der Agent der Kurzfassung statt den Skill-Body zu lesen (belegt: „mit Review zwischen Tasks" in der Description → Agent machte 1 Review statt der 2 laut Body).
- Dritte Person. Konkrete Symptome/Situationen statt Abstraktion; das *Problem* beschreiben („Tests mal rot, mal grün"), nicht das Technologie-Symptom — außer der Skill IST technologie-spezifisch, dann explizit benennen.
- `when_to_use` = Keyword-Coverage wie ein Suchender denkt: Fehlermeldungen, Symptome, Synonyme, Tool-/Befehlsnamen.
- **Feuert-NICHT-Check:** 3 Situationen notieren in denen der Skill NICHT feuern soll, dann `grep -il "<trigger-begriff>" ~/.claude/skills/*/SKILL.md` gegen Trigger-Kollisionen mit bestehenden Skills prüfen. Bei Überlappung: Abgrenzungs-Satz in BEIDE Descriptions.
- Bei Disziplin-Skills: Kurz-vor-Verstoß-Symptome mit in die Trigger („use when tempted to skip X").

### Phase 2 — Body-Struktur (Pflicht-Sektionen)

```markdown
# <Skill-Name> — <Kurz-Untertitel>

Zweck: <1-2 Sätze, was macht der Skill konkret>

## Vor dem Start
1. Scope/Argument auswerten
2. Pre-Conditions prüfen
3. Klarstellungs-Fragen falls nötig

## Phase 1 — <erste Phase>
<konkrete Schritte>

## Phase 2 — <zweite Phase>
<konkrete Schritte>

## Output-Format
<wo wird geschrieben, welches Format>

## Constraints
- Read-only oder Edit-allowed?
- Backup-Pflicht?
- Severity-Skala-Kompatibilität?

## Beispiel-Triggers
- `/<name>` — Default-Run
- `/<name> <arg>` — mit Argument
```

**Body-Formulierung — Form an Fehlertyp anpassen** (geerntet aus superpowers:writing-skills v6.1.1, 2026-07-21):

| Beobachteter Fehler des Agenten | Richtige Form | Falsche Form |
|---|---|---|
| Regel wird unter Druck übersprungen (weiß es, tut's trotzdem) | Verbot + Rationalisierungs-Tabelle + Red-Flags; imperative Sprache („MUSS", „keine Ausnahmen") | Weiche Empfehlung („bevorzuge…", „erwäge…") |
| Output hat falsche Form (Bloat, Verdikt vergraben) | Positiv-Rezept: definieren was der Output IST (Teile + Reihenfolge) | Verbotsliste („nicht nacherzählen") — erzeugt messbar MEHR vom Unerwünschten |
| Pflicht-Element wird weggelassen | Struktur: REQUIRED-Feld/Slot im Template | Prosa-Erinnerung neben dem Template |
| Verhalten hängt an Bedingung | Konditional an beobachtbarem Prädikat („wenn X existiert → Y") | Pauschalregel + Ausnahmeklauseln |

Dazu: keine Nuance-Klauseln („nicht X, außer es ist wichtig") — die öffnen die Verhandlung wieder; echte Ausnahme als eigenes Konditional formulieren. Anti-Bloat im Body: Agenten sind schon schlau — jeden Absatz challengen („weiß das Modell das eh?"); EIN exzellentes Beispiel statt drei mittelmäßiger; konsistente Terminologie (ein Begriff pro Konzept); keine zeitgebundenen Infos (veraltet → „Old Patterns"-Abschnitt); Body < 500 Zeilen, darüber in `references/` splitten (max. ein Level tief ab SKILL.md verlinkt, Files > 100 Zeilen mit Inhaltsverzeichnis oben).

### Phase 3 — Write + Verify

1. Verzeichnis anlegen: `mkdir -p <scope>/.claude/skills/<name>/`
2. SKILL.md schreiben mit dem oben generierten Inhalt
3. **YAML-Validität prüfen:**
   ```bash
   python -c "import yaml; data = yaml.safe_load(open('<path>/SKILL.md').read().split('---')[1]); print('OK:', list(data.keys()))"
   ```
4. Pflicht-Felder-Check: `name`, `version`, `description`, `when_to_use`, `userInvocable` müssen vorhanden sein
5. der Nutzer zeigen + fragen ob Anpassungen nötig

### Phase 3.5 — Skill-Test an frischem Subagent (geerntet aus superpowers:writing-skills v6.1.1, 2026-07-21)

Kernprinzip: Ein Skill, den nie ein frischer Agent benutzt hat, ist ungetesteter Code. Vor Phase 4:

1. **Baseline (bei nicht-trivialen Skills idealerweise VOR dem Schreiben):** frischen Subagent (Task-Tool) die Ziel-Aufgabe OHNE Skill lösen lassen. Konkrete Fehler/Auslassungen wörtlich notieren — der Skill adressiert genau DIESE Lücken, nicht hypothetische. Macht die Baseline nichts falsch → zurück zum Anti-Bloat-Gate.
2. **Verify:** frischer Subagent (oder neue Session) bekommt einen realistischen Auftrag — nicht „was sagt der Skill?" (zu akademisch, Agent rezitiert nur):
   - Trigger-Test: findet/lädt er den Skill anhand der Description allein?
   - Compliance-Test: befolgt er die Phasen? Abweichungen wörtlich festhalten.
3. **Test nach Skill-Typ:**

   | Skill-Typ | Test | Erfolgskriterium |
   |---|---|---|
   | Disziplin (Regel mit Umgehungs-Anreiz) | Druck-Szenario mit 3+ kombinierten Drücken (Zeitdruck + Sunk-Cost + Autorität), erzwungene A/B/C-Wahl, „das ist real, entscheide" | Agent folgt Regel trotz Druck + zitiert Skill-Sektion |
   | Technik/Workflow | Anwendungs-Szenario + eine Edge-Case-Variante | Agent wendet Technik korrekt auf neues Szenario an |
   | Referenz | Retrieval-Frage („finde X, wende an") | Agent findet Info + nutzt sie korrekt |

4. **Meta-Test bei Fehlschlag:** den Agent fragen: „Du hattest den Skill und hast trotzdem Y gemacht — wie hätte er formuliert sein müssen?" Drei Antwortklassen: (a) „war klar, hab's ignoriert" → Imperativ/Prinzip verstärken, (b) „hätte X sagen sollen" → Vorschlag wörtlich übernehmen, (c) „Sektion nicht gesehen" → Struktur/Prominenz fixen. Dann re-testen.
5. **Nur Disziplin-Skills:** jede beobachtete Ausrede aus den Testläufen als Zeile in eine Rationalisierungs-Tabelle (`| Ausrede | Realität |`) + Red-Flags-Liste in den Skill zurückschreiben; re-testen bis keine neue Ausrede mehr auftaucht. Reine Referenz-Skills brauchen KEINE Druck-Tests (nur Retrieval).

Zukunft: Micro-Wording-Tests — einzelne Formulierungs-Varianten mit 5+ Wiederholungen pro Variante gegen eine No-Guidance-Kontrolle fahren (zeigt die Kontrolle den Fehler gar nicht erst → Guidance unnötig; Varianz als Metrik: konvergieren die Reps nicht auf dieselbe Form, bindet die Formulierung nicht; automatische Treffer immer manuell nachlesen). Heute für Solo-Betrieb Overkill; wird relevant sobald Disziplin-Skills systematisch gehärtet werden — billig umsetzbar über die vorhandene `claude -p`-Batch-Infrastruktur (mit `--no-session-persistence`). (geerntet aus superpowers:writing-skills v6.1.1, 2026-07-21)

### Phase 4 — Integration

1. Skill in globaler CLAUDE.md unter „Globale Slash-Commands" eintragen (falls global)
2. Falls projekt-spezifisch: in projekt-CLAUDE.md eintragen
3. `plugin_hash_snapshot.py --update` ausführen damit der neue Skill in Hash-Drift-Detection erfasst wird
4. Test-Trigger: in neuer Session `/<name>` aufrufen + sehen ob Skill geladen wird

## Anti-Patterns (was NICHT tun)

| Anti-Pattern | Korrektur |
|---|---|
| Description als Funktions-Summary statt Trigger | „Wann triggert der Skill?" formulieren, nicht „Was macht der Skill?" |
| Frontmatter ohne `version` | Pflicht: Semver `1.0.0` bei Erstellung |
| Frontmatter ohne `last-reviewed` | Pflicht: aktuelles Datum |
| `allowed-tools: *` (Wildcard) | Nur Tools die wirklich gebraucht werden — Token-Listing-Effizienz |
| Skill ohne `Constraints`-Section | Pflicht: zumindest Read-only / Write-allowed klären |
| Vage when_to_use („für alles möglich") | Konkrete kommagetrennte Trigger-Begriffe |
| Hardcoded Pfade ohne `~/` Tilde-Expansion | Tilde verwenden, dann auf Windows + Linux portabel |
| Skill mit Sub-Agent-Dispatch ohne Inline-Fallback | Beide Pfade dokumentieren (Worktree-Worktree-Issue) |
| Narrativ-Beispiel („in Session X fanden wir…") | Wiederverwendbares Muster formulieren, keine Einzelfall-Story |
| Referenz-Files verschachtelt (SKILL.md → a.md → b.md) | Referenzen max. ein Level tief, direkt aus SKILL.md verlinkt — sonst liest der Agent nur `head`-Fragmente |

(Letzte 2 Zeilen geerntet aus superpowers:writing-skills v6.1.1, 2026-07-21)

## Gestaltungs-Prinzipien *(geerntet aus superpowers:writing-skills/anthropic-best-practices v6.1.1, 2026-07-21)*

1. **Degrees of Freedom — Spezifizität an Fragilität koppeln:** HIGH freedom (Heuristik-Prosa) für robuste Aufgaben mit vielen validen Wegen · MEDIUM (Template/Pseudocode mit Parametern) für bevorzugte Muster mit erlaubter Variation · LOW („führe exakt dieses Script aus, nicht modifizieren") für fragile/kritische Operationen wo Abweichung = Bruch. Falsche Stufe = Hauptursache für Skill-Versagen.
2. **Feedback-Loop-Pattern:** Wo Output validierbar ist, in den Skill einbauen: Validator laufen lassen → Fehler fixen → wiederholen. Bei mehrstufigen Aufgaben: analyze → Plan-File schreiben → Plan validieren → ausführen → verifizieren (verifizierbare Zwischen-Artefakte). Validator-Scripts verbose halten — stumme Validatoren erzeugen Rate-Schleifen.
3. **Utility-Scripts im Skill:** Fehlerfälle im Script LÖSEN, nicht an den Agent zurückwerfen („solve, don't punt"). Keine Voodoo-Konstanten (`TIMEOUT = 47 # warum 47?` — jeden Wert begründen). Intent klar trennen: „Führe analyze_form.py AUS" (execute) vs. „Lies analyze_form.py als Referenz" (read) — sonst rät der Agent.
4. **Kein `@`-Link auf andere Skills/Files:** `@pfad`-Syntax force-loadet sofort und verbrennt Kontext bevor er gebraucht wird — Referenzen als normaler Pfad-Text nennen, der Agent lädt bei Bedarf via Read.
5. **Persuasions-Prinzipien (Disziplin-Skills, Zukunft):** Kombination Authority+Commitment+Social-Proof wirkt für Regel-Compliance; NIEMALS Liking (erzeugt Sycophancy) und Reciprocity nur sparsam (wirkt manipulativ). Relevant sobald Disziplin-Skills systematisch gehärtet werden.

## Versions-Pflege bei späteren Updates

Bei jedem späteren Edit an einem existierenden Skill:
1. Backup: `cp -a SKILL.md SKILL.md.bak.review-$(date +%s)`
2. `version`-Bump nach Semver:
   - PATCH (1.0.0 → 1.0.1): Typo, kosmetisch
   - MINOR (1.0.0 → 1.1.0): Neue Feature/Sektion ohne Breaking Change
   - MAJOR (1.0.0 → 2.0.0): Breaking-Change (Argument-Format geändert, Output-Pfad geändert)
3. `last-reviewed` auf aktuelles Datum
4. Changelog-Sektion am Ende des Skills ergänzen mit Eintrag
5. **Re-Test bei MINOR/MAJOR:** geänderte/neue Sektionen zählen wie Neuerstellung — Phase 3.5 kompakt wiederholen (frischer Subagent, mindestens Trigger- + Compliance-Test der geänderten Stelle); ein ungetesteter Edit ist derselbe Verstoß wie ein ungetesteter neuer Skill (geerntet aus superpowers:writing-skills v6.1.1, 2026-07-21)

## Constraints

- **YAML-Validierung nach Write** ist Pflicht
- **Subagent-Test vor Integration** (Phase 3.5) bei nicht-trivialen Skills — mindestens Trigger- + Compliance-Test (geerntet aus superpowers:writing-skills v6.1.1, 2026-07-21)
- **Backup bei Updates** existierender Skills
- **Pattern-Konsistenz** mit anderen Skills in `~/.claude/skills/` prüfen
- **Token-Effizienz:** Description max 2 Sätze, kein Bloat
- **Keine `model:` ohne Begründung** im Body
- **Quellen** für Anthropic-Skill-Standards: https://docs.claude.com/en/docs/claude-code/skills (bei Drift überprüfen)

## Beispiel-Triggers

- `/skill-create` — interaktiver Workflow
- `/skill-create db-explore sqlite inspection` — direkt mit Args
- `/skill-create new-skill-name "kurze Beschreibung"` — quoted Args

## Changelog

- **v2.2.0** (2026-07-21): Fidelity-Nachernte (Verifier-Befund): Gestaltungs-Prinzipien-Sektion — Degrees of Freedom, Feedback-Loop/Plan-Validate-Execute, Script-Guidance (solve-don't-punt, Voodoo-Konstanten, Execute-vs-Read-Intent), @-Link-Verbot, Persuasions-Prinzipien (Negativ-Regeln Liking/Reciprocity).
- **v2.1.0** (2026-07-21): Superpowers-Harvest (geerntet aus superpowers:writing-skills v6.1.1): Anti-Bloat-Gate im Pre-Flight (ein Skill = ein Job, mechanische Regeln → Hook, Baseline-Frage), Description-Trigger-Optimierung (nie Workflow-Summary — Agent folgt sonst der Kurzfassung statt dem Body, Feuert-NICHT-Check mit Kollisions-Grep, Keyword-Coverage), Body-Formulierungs-Tabelle (Form an Fehlertyp: Verbot vs. Positiv-Rezept vs. Struktur-Slot vs. Konditional; keine Nuance-Klauseln; <500 Zeilen + references/-Regeln), neue Phase 3.5 Skill-Test an frischem Subagent (Baseline/Verify/Typ-Tabelle/Meta-Test/Rationalisierungs-Tabelle; Zukunft: Micro-Wording-Tests via claude -p-Batch), Re-Test-Pflicht bei MINOR/MAJOR-Edits, 2 neue Anti-Pattern-Zeilen (Narrativ-Beispiel, verschachtelte Referenzen).
- **v2.0.0** (2026-05-17): Major-Rewrite nach Cowork-Skill-Vergleich (anthropic-skills:skill-creator). Vollständiges Frontmatter (version, last-reviewed, allowed-tools). 4-Phasen-Workflow (Scaffold / Body-Struktur / Write+Verify / Integration). YAML-Validierung als Pflicht-Step. Versions-Pflege-Pattern für Updates. Anti-Patterns-Tabelle. Beispiel-Triggers.
- **v1.0.0** (2026-05-16): Erste Version nach ai-coding-starter-kit-Pattern.
