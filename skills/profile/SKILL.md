---
name: profile
version: 1.0.0
description: |
  Performance-Profiling + Memory-Leak-Detection via perf-agent-Subagent —
  cProfile-Hotspots, tracemalloc-Snapshot-Diffs, Latenz-Analyse, Pre/Post-Benchmark.
  Schlanker userInvocable Slash-Wrapper um den perf-agent (analog /security-audit
  → security-reviewer). Use when: "profilen", "Performance-Analyse", "Hotspot finden",
  "Memory-Leak suchen", "warum ist das langsam", "Latenz messen", "profile".
---

# profile — Performance-Profiling via perf-agent

Du orchestrierst den `perf-agent`-Subagent für messbasiertes Profiling. Du selbst rätst
nicht über Performance — der Agent misst (Pre/Post-Benchmark).

## Vorgehen
1. **Scope + Symptom ermitteln:** welches Modul/welcher Hot-Path? Symptom (langsame Replies,
   Memory-Wachstum, Latenz-Spike)? Reproduzierbarer Trigger/Input?
2. **Dispatch** `perf-agent` (1 Call) mit: Files/Funktionen · Symptom · Mess-Methode
   (cProfile für CPU-Hotspots, tracemalloc-Snapshot-Diff für Memory-Leaks, Latenz-Timing).
   **Messbasiert, nicht spekulativ** — Pre-Benchmark, Hypothese, Post-Benchmark.
   Datei-Reads im Subagent NUR via Read-Tool (kein cat/Get-Content — Security-Flag).
3. **Ergebnis rahmen:** Top-Hotspots (Funktion · % Zeit · Calls) · Memory-Wachstum
   (Snapshot-Diff, Top-Allokationen) · konkreter Fix-Vorschlag mit erwarteter Delta +
   Aufwand. Kein Fix ohne Messung der Ist-Last.

## Abgrenzung
- `audio-pipeline-reviewer` macht DSP-Code-Review (Sample-Rate/Buffer/FFT) OHNE Profiling.
- `profile` (dieser Skill, perf-agent) macht messbasiertes Profiling mit Pre/Post-Benchmark.

## Constraints
- Immer messen (cProfile/tracemalloc/Timing) statt Hotspots raten.
- Memory-Leak: tracemalloc-Snapshot VOR + NACH dem verdächtigen Pfad, Diff zeigt Wachstum.
- Fix nur vorschlagen wenn der Hotspot gemessen die Last trägt (>~5% oder klares Leak).

## Beispiel-Triggers
`/profile` · „warum ist der Dashboard-Endpoint langsam" · „such ein Memory-Leak im Bot-Prozess"

## Changelog
- v1.0.0 (2026-06-05): Initial — Inventar-Audit G4 (perf-agent ohne Slash-Skill).
