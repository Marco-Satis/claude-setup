# Festgefahren → Pflicht-Websuche (Global Rule)

> der Nutzer-Entscheid 2026-07-23. Auslöser war der RC-Ausfall desselben Tages: statt die
> Fehlermeldung nachzuschlagen wurde eine plausible, aber **falsche** Ursachen-These
> (OAuth-Refresh-Race) gebaut und schon halb implementiert. Die richtige Ursache stand
> in einer Memory und im Journal. Kosten: eine Fehl-Diagnose plus Arbeit am falschen Fix.

## Kernregel

Wenn ein Problem **nicht gelöst werden kann**, wird recherchiert — nicht geraten.
Nicht erst wenn wir uns im Kreis drehen, sondern **sobald klar ist, dass Wissen fehlt.**

Kanonischer Rechercheur: **`web-researcher`-Agent** via Agent-Tool
(`subagent_type: "web-researcher"`). Delegiert, eigener Kontext, mehrere parallele
Suchen, Report als Datei. Kostet keinen Hauptkontext.

## Pflicht-Auslöser (jeder einzelne genügt)

1. Dieselbe Fehlersignatur ist **3×** aufgetreten → Hook `stuck_detector.py` meldet es.
2. **6 verschiedene** Fehlschläge im 30-Minuten-Fenster → dasselbe, breit statt tief.
3. Ich bin drauf und dran zu schreiben: „vermutlich", „wahrscheinlich liegt es an",
   „könnte daran liegen" — als **Grundlage für eine Änderung**. Vermutung als Fix-Basis
   ist der verbotene Zustand.
4. Ich will einen **Workaround** vorschlagen, statt die Ursache zu verstehen.
5. Ich will melden, dass etwas **nicht geht / nicht lösbar / unklar** ist.
6. Zweite Hypothese, nachdem die erste widerlegt wurde — spätestens dann fehlt Wissen.
7. Es geht um eine **fremde Fehlermeldung** (Tool, Library, API, systemd, Discord, …),
   deren genaue Semantik ich nicht sicher belegen kann.

## Was VOR der Websuche kommt

Websuche ist nicht die erste Station. Reihenfolge:

1. **`mcp__memory__memory_search`** zum Thema — bei Setup/Infra Pflicht, `time_expr: "last 7 days"`.
   Im RC-Fall stand die richtige Antwort dort. Andere Sessions (PC + netcup) ändern parallel.
2. **Primärquellen lokal**: Logs, `journalctl`, Konfiguration, Quellcode. Erst die echte
   Fehlermeldung, dann Theorie — nie Version/Config raten.
3. **context7** bei Library-/Framework-/CLI-Fragen (aktuelle Doku schlägt Trainingswissen).
4. Erst dann **`web-researcher`**.

## Was in den Recherche-Prompt gehört

- Die **wörtliche** Fehlermeldung (nicht paraphrasiert)
- Tool + Version, OS, relevante Config
- Was schon probiert wurde **und warum es scheiterte**
- Die konkrete offene Frage, nicht das Thema allgemein
- Datei-Inhalte nur via Read-Tool lesen (siehe [Subagent-Datei-Reads](subagent-file-reads.md))

## Nach dem Report

Das Ergebnis **explizit gegen die eigene bisherige These prüfen** und einen Widerspruch
benennen, statt ihn zu glätten. Erkenntnis, die eine Fehl-Diagnose korrigiert, gehört
als mcp-Memory gespeichert (bei Setup-Themen mit Tag `setup-change`).

## Abgrenzung

| Situation | Werkzeug |
|---|---|
| Festgefahren, Wissen fehlt (diese Regel) | `web-researcher`-Agent |
| Bewusst tiefer, adversarial verifizierter Zitat-Report | Builtin `deep-research` |
| Schnelle Multi-Search inline | `/websuche` |
| Bug mit lokal ermittelbarer Ursache | `/investigate` (Iron Law: kein Fix ohne Root Cause) |

## Kill-Switch

`touch ~/.claude/flags/stuck_detector.off` — schaltet nur die Hook-Meldung ab,
nicht diese Regel. Schwellen: `CLAUDE_STUCK_THRESHOLD`, `CLAUDE_STUCK_DISTINCT`,
`CLAUDE_STUCK_WINDOW`, `CLAUDE_STUCK_REARM`.
