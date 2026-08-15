---
name: codex-review
version: 1.0.0
description: |
  Code-Review / Bug-Finding an Codex (GPT-5-Codex-Klasse, code-spezialisiert,
  ChatGPT-Plus-OAuth, kein API-Geld) via codex-bridge auslagern — spart Opus-Tokens
  UND liefert andere Modell-DNA (fängt Bug-Klassen die Claude systematisch übersieht).
  Use when: "codex review", "lass codex den code prüfen", "cross-check den code",
  "second opinion code", "codex-review".
---

# codex-review — Code-Review an Codex auslagern (Token-Spar + Cross-Model)

Zweck: Code-Review/Bug-Finding auf Codex (code-spezialisiert, andere DNA als Claude)
auslagern — spart Opus-Tokens und deckt Fehlerklassen auf, die Claude übersieht.
Codex läuft über die ChatGPT-Plus-Sub → kein API-Geld (nur Plus-Limits).

## Vorgehen
1. **Scope + Fokus:** welche Dateien/welcher Diff? Worauf achten (Korrektheit, Regression,
   Security, konkrete Risiko-Stelle)? Je schärfer der Fokus, desto brauchbarer Codex' Output.
2. **Dispatch** `codex-bridge` (1 Call) mit: Datei-Pfade/Diff · Review-Fokus · Rückgabe-Format
   (Findings mit Severity · Datei:Zeile · Problem · Fix). Datei-Reads im Subagent NUR via
   Read-Tool (kein cat — Security-Flag). Bridge läuft read-only + Usage-Tracking
   (`~/.claude/state/codex_usage.jsonl`).
3. **Findings kritisch einordnen (Pflicht):** Codex liefert manchmal False-Positives auf
   gekürzten/aus-dem-Kontext-Snippets. JEDES Finding gegen die echte Datei verifizieren,
   bevor du fixst. Reale Bugs von Rauschen trennen — nicht blind übernehmen.

## Wann NICHT
- Trivialer/winziger Diff → selbst reviewen (Bridge-Overhead lohnt nicht).
- Wenn Codex nicht erreichbar ist (`codex login` nötig) → sag es klar, KEIN Claude-Fallback
  als „Codex" ausgeben (das ist der ganze Sinn der anderen DNA).

## Abgrenzung
- `review` (Skill) = Claude-Multi-Agent-Orchestrator (Session-Scope, Self-Review-Loop,
  False-Negative-Pass). `codex-review` = ein einzelner Cross-Model-Consult an Codex.
- `gemini-digest` = Bulk-Read/Kontext-Masse (günstig); `codex-review` = Code-Spezialisierung.
- Max. Abdeckung: Fable + Codex + Gemini parallel, dann synthetisieren (wie Session-Review
  2026-07-14) — jeweils False-Positives markieren.

## Beispiel-Triggers
`/codex-review web/routes/dashboard.py` · „lass Codex den WS-Handler cross-checken" ·
„second opinion von Codex auf den Session-Diff"

## Changelog
- v1.0.0 (2026-07-14): Initial — Offload-Skill-Suite (Token-Spar via Gemini/Codex).
