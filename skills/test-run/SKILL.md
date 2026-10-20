---
name: test-run
version: 1.1.0
description: |
  Test-Generierung + -Ausführung + Coverage-Analyse via test-agent-Subagent.
  Schlanker userInvocable Slash-Wrapper um den test-agent (analog /security-audit
  → security-reviewer). Optionaler TDD-Modus (Red-Green-Refactor) + Test-Anti-
  Pattern-Checkliste. Use when: "Tests schreiben", "Tests ausführen", "Coverage
  prüfen", "Test-Lücken finden", "test-run", "teste das", "TDD", "test-first".
---

# test-run — Test-Generierung/-Ausführung via test-agent

Du orchestrierst den `test-agent`-Subagent für Test-Arbeit. Du selbst schreibst keine
Tests inline — du dispatchst und rahmst das Ergebnis.

## Vorgehen
1. **Scope ermitteln:** welches Modul/welche Files? Default = uncommitted Diff bzw. zuletzt
   geänderte Files (`git diff --name-only`).
2. **Dispatch** `test-agent` (1 Call) mit: Files-Liste · Aufgabe (generieren / ausführen /
   Coverage / Lücken finden / TDD-Modus, s.u.) · Test-Runner-Hinweis (Projekt nutzt ggf. **standalone**
   `python tests/test_x.py`, NICHT pytest — vorher prüfen ob pytest oder standalone).
   Datei-Reads im Subagent NUR via Read-Tool (kein cat/Get-Content — Security-Flag).
3. **Coverage-Rubrik** (Coverage-TYP, kein Quality-Score): `★★★` Behavior+Edge+Error ·
   `★★` Happy-Path · `★` Smoke. `★★` bei Security/Auth/Persistence = MEDIUM-Lücke.
4. **Ergebnis rahmen:** welche Tests generiert/gelaufen, Pass/Fail, Coverage-Lücken je File +
   Aufwand. Fehlschlagender Test auf geändertem Code = HIGH (Regression).

## TDD-Modus (optional) *(geerntet aus superpowers:test-driven-development v6.1.1, 2026-07-21)*
Auf Wunsch („TDD", „test-first") — bei Bugfixes empfohlen. Kernprinzip: **wer den Test nie
fehlschlagen sah, weiß nicht ob er das Richtige testet.**
1. **RED:** einen minimalen Test fürs *gewünschte* Verhalten schreiben (ein Behavior, klarer
   Name, echte Aufrufe statt Mocks wo möglich). Ausführen und Fehlschlag SEHEN — er muss aus
   dem richtigen Grund fehlschlagen (Feature fehlt, nicht Typo/Import-Error). Test passt
   sofort? Dann testet er Bestehendes → Test schärfen.
2. **GREEN:** minimale Implementierung, nur genug für diesen Test (kein YAGNI-Ausbau, keine
   Nebenbei-Refactors). Ausführen: Ziel-Test grün + restliche Suite grün + Output sauber.
3. **REFACTOR:** erst nach grün — Duplikate raus, Namen, Helper extrahieren. Kein neues
   Verhalten; Tests bleiben grün. Dann nächstes Behavior → zurück zu RED.

**Eiserne Regel:** Schlägt GREEN fehl → **Code fixen, nicht den Test.** Einen Test nachträglich
an die Implementierung anpassen NUR mit expliziter Begründung (dokumentiert: Test-Annahme war
nachweislich falsch) — sonst ist es Whitewashing.
**Bugfix:** jeder Fix beginnt mit einem fehlschlagenden Repro-Test (beweist den Fix + verhindert Regression).
**Test schwer zu schreiben?** Design-Signal, nicht Test-Problem: Interface zu kompliziert oder
Code zu gekoppelt (→ Dependency-Injection) — nicht mit Mock-Bergen kompensieren.

Zukunft: TDD-Rollen-Split über zwei Dispatches — test-agent schreibt nur den RED-Test, ein
zweiter (Impl-)Dispatch implementiert ohne den Test anfassen zu dürfen. Verhindert strukturell
den „Test an Impl anpassen"-Bias; relevant sobald Multi-Agent-Flows hier Standard werden.

## Test-Anti-Patterns (Checkliste für test-agent-Output) *(geerntet aus superpowers:test-driven-development v6.1.1, 2026-07-21)*
Generierte wie bestehende Tests dagegen prüfen — Treffer = Finding im Ergebnis-Rahmen:
- **Impl-Spiegel:** Test bildet Implementierungsdetails nach statt Verhalten/Contract zu prüfen
  (bricht bei jedem Refactor, fängt keine echten Bugs).
- **Mock-Behavior testen:** Assertions auf Mock-Existenz/Mock-Calls statt echtem Verhalten.
  Mocks isolieren — sie sind nicht das Testobjekt.
- **Mock-Overuse:** Mock-Setup länger als Test-Logik, oder Test bricht wenn der Mock wegfällt →
  weniger mocken; Integrationstest mit echten Komponenten ist oft simpler. Nur die
  langsame/externe Operation mocken — nie die Methode, auf deren Seiteneffekt der Test angewiesen ist.
- **Unvollständige Mocks:** Mock-Response nur mit den Feldern die der Test gerade kennt →
  Silent-Fails downstream. Komplette echte Struktur spiegeln.
- **Test-only-Methoden in Produktion:** Cleanup/Reset-Helper nur für Tests gehören in
  test-utils, nicht in die Produktionsklasse.

## Constraints
- Test-Generierung NICHT überengineeren — Behavior + Edges + Error-Pfade, keine trivialen Getter-Tests.
- Runner verifizieren (standalone vs pytest) bevor „ausführen" — des Nutzers Projekte nutzen teils standalone.
- MEDIUM+-Coverage-Lücken (Security/Auth/Persistence ohne ★★★) → optional Problem-Tracker.

## Beispiel-Triggers
`/test-run` · „schreib Tests für rbac.py" · „lauf die Tests + zeig Coverage-Lücken"

## Changelog
- v1.1.0 (2026-07-21): TDD-Modus (Red-Green-Refactor, Test-nicht-an-Impl-anpassen-Regel, Repro-Test-Pflicht bei Bugfix) + Test-Anti-Pattern-Checkliste geerntet aus superpowers:test-driven-development v6.1.1 (Plugin wird deaktiviert).
- v1.0.0 (2026-06-05): Initial — Inventar-Audit G4 (test-agent ohne Slash-Skill).
