# Skill-Dispatch bei Namens-/Trigger-Kollisionen (Global Rule)

> Neu 2026-07-21 (Fix S-1 aus TikTok-Audit). CLI-Builtins (`review`, `code-review`, `security-review`, `loop`, `deep-research`) sind nicht deaktivierbar — diese Tabelle macht den kanonischen Dispatch eindeutig.

## Dispatch-Tabelle: Intent → kanonischer Skill

| Intent | Kanonisch | NICHT nehmen |
|---|---|---|
| „review", „code review", Session-/PR-Review | **der Nutzer `review`-Skill** (Selbstlern-Schleife: findings.json, Outcome-Ledger, Phase-0-Recall) | Builtin `code-review`/`security-review`, Plugin-Reviewer |
| Schneller Einzel-File-/Diff-Check | `quick-review` | Builtin |
| „komplettes Projekt untersuchen" (Code **+** Architektur/Doku/Config/Hygiene/Betrieb/Ziel) | **`/review projekt`** (Achsen A-D + E-J, ab review v4.5) | `full-audit` (deckt nur die Code-Ebene ab) |
| Quartals-/Pre-Release-Audit als 5-Agent-Schwarm | `full-audit` (faehrt Phase 4.6 aus `/review` mit) | — |
| „security audit" (Code/Repo/Diff, SAST) | `security-audit` | `cso` |
| Infrastruktur-/Setup-Security, wiederkehrend, Trend | `cso` | `security-audit` |
| Debugging / „warum kaputt" | `investigate` | superpowers:systematic-debugging zusätzlich laden |
| Schnelle Multi-Search inline, Datei-Report | `websuche` | — |
| Tiefer adversarial verifizierter Zitat-Report | Builtin `deep-research` | — |
| Recherche als delegierter Subagent | `web-researcher`-Agent | — |
| Neuen Skill bauen | `skill-create` | skill-creator-Plugin |
| Recurring-Intervall-Task in DIESER Session | Builtin `loop` | `loopmode` |
| Autonome Bot-Operator-Schleife (Games) | `loopmode` | Builtin `loop` |

| Perspektive zu einer Urteils-Frage im Review | **läuft automatisch** (review K6, Trigger C1–C5, Einzel-Mitglied ~1,5k) | nicht zusätzlich `/council` starten |
| Echte Deliberation zu einer offenen Entscheidung | `/council --duo`/`--triad` (~21–23k) | `--full` (~47k) außer der Nutzer will es ausdrücklich |

## Regel
1. Bei Namens-Gleichheit gewinnt **der Nutzer eigener Skill** (getunte Pipeline) über Builtin/Plugin — außer die Tabelle sagt explizit anders.
2. Nie zwei überlappende Skills für denselben Intent in einem Turn laden.
3. superpowers-Prozess-Skills nur nutzen, wenn kein eigenes Pendant existiert (Pendants: investigate, office-hours, plan-ceo-review, review/quick-review, test-run, skill-create).

## Plugin-Zustand ist PRO MASCHINE (2026-07-29)

`enabledPlugins` steht in `settings.json`, und die synct **nicht**. Diese Regel-Datei synct schon —
deshalb steht hier **keine** pauschale Aussage wie „(deaktiviert)" mehr, die auf der anderen
Maschine falsch wäre.

| Plugin | netcup | PC |
|---|---|---|
| `superpowers` | aus (nach Ernte von 72 Techniken, v6.1.1 gepinnt im `_archive`) | **aktiv** |
| `skill-creator` | aus | **aktiv** |
| `recall` | aus | **aktiv** |
| `security-guidance` | deinstalliert (Fixsweep 21.07.) | **aktiv** |
| `hookify` | deinstalliert, ersetzt durch Cron `weekly_hook_suggest` (Mo 08:00) | **aktiv** |

**Die Dispatch-Regeln oben gelten unabhängig davon.** Wo ein eigener Skill existiert, gewinnt er —
auch auf der Maschine, auf der das Plugin geladen werden *könnte*. Die Tabelle sagt nur, wo ein
Fehlgriff überhaupt möglich ist.

Vor jeder Aussage über Plugin-Zustand: auf der betreffenden Maschine an `settings.json` belegen,
nicht aus Erinnerung. Siehe mcp-Memory `d9b4e09d`.
