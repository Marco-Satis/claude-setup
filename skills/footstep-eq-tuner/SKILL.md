---
name: footstep-eq-tuner
version: 2.0.0
last-reviewed: 2026-05-17
description: EQ-Iteration fuer FootstepPro. Nimmt Analyzer-Output + aktuelle EQ-Config, schlaegt 1-3 minimale Pre-EQ/ReaXComp-Aenderungen vor mit erwarteter Score-Delta, inkl. Spatial-Hook-Sanity-Check. Nutze nach jedem v9.x-Test-Recording.
when_to_use: footstep EQ tuning, pre-EQ adjustment, ReaXComp tuning, EQ iteration, footstep score delta, FootstepPro tuning nach test recording
argument-hint: Optional WAV-Pfad oder JSON-Pfad mit Metriken
allowed-tools: Read Grep Glob Bash Write Edit
userInvocable: true
---

# FootstepPro EQ-Tuner

Du hilfst der Nutzer bei der iterativen EQ-Tuning-Schleife: Aufnahme analysieren, gezielt 1-3 Pre-EQ-/ReaXComp-Aenderungen vorschlagen, erwartete Score-Delta abschaetzen.

## Vor dem Start
Datenbasis ist **(Windows-lokal)** — FootstepPro/FootstepAnalyzer liegt nur auf dem PC (EqualizerAPO-Setup, kein Syncthing-Sync, auf netcup nicht vorhanden):
- Aktuelle EQ-Config: `C:\Users\<user>\OneDrive\Dokumente\AudioSetup\FootstepAnalyzer\output\configs\AIW_BO7_v9.*.txt` (Windows-lokal)
- ReaXComp-Config: `C:\Users\<user>\OneDrive\Dokumente\AudioSetup\FootstepAnalyzer\output\configs\REAXCOMP_v9.*.txt` (Windows-lokal)
- Plan-Complete-Targets aus Plan v1.5:
  - foot_wins ≥ 50%
  - competitive_score ≥ 60
  - spatial_health in [-3, -8] dB
  - kf_ratio ≤ -10 dB
  - surface_diversity ≥ 4/7

## Workflow

### 1. Argument auswerten
- WAV-Pfad: `analyzer.py analyze --profile dt770 <wav>` ausfuehren, JSON-Output lesen
- JSON-Pfad: direkt lesen
- Default: neueste Analyse aus `output/cache/`

### 2. Spatial-Hook-Sanity-Check (Plan v1.6 Pflicht)
Pruefe ob das Recording mit/ohne aktivem Spatial-Hook analysiert wurde:
- `metrics.json` -> Felder `surface_diversity_bonus`, `voice_clarity_bonus`, `crate_masking_penalty`, `distance_balance_bonus`
- Wenn alle 4 == 0: Spatial-Hook war inaktiv (oder segments=None) -> Score ist v3-Niveau-konsistent
- Wenn aktiv: VORSICHT bei Score-Vergleich gegen v9.195/v9.200 falls H1 noch nicht gefixt (siehe `spatial-pipeline-helper`)

### 3. Score-Delta-Analyse
Vergleiche gegen Vorgaenger (z.B. v9.195):
- Welche Targets noch NICHT erreicht?
- Welche Frequenz-Baender (B1-B12) brauchen Korrektur?

### 4. Empfehlung (max 3 Aenderungen)
Pro Aenderung:
- Welcher Filter (Pre-EQ Filter N oder ReaXComp Band X)
- Aktueller Wert -> neuer Wert
- Erwartete Score-Delta (qualitativ: +5%, neutral, -2%)
- Begruendung mit Vision-Tabellen-Bezug (z.B. "B7+B8 Schritt-Erhaltung -> KEIN Compressor")

### 5. Strategie-Hybrid 2+3+6+7 einhalten
- **NIE** B7/B8 mit Compressor zerstoeren (Schritte!)
- **NIE** B4-B6 cutten (Operator-Voice + Spatial-ITD)
- **NIE** B10/B11 hart cutten (Spatial-ILD)
- ScoreStreaks: ReaXComp-Compression (dynamisch) statt Pre-EQ-Cut (statisch)
- Wingsuit-Wind: ReaXComp B11 4:1 statt -10 dB Pre-EQ-Cut

## Output
```
🎚 FootstepPro EQ-Tuning fuer <wav-name>

**Aktuelle Metriken vs Targets:**
| Metrik | Wert | Target | Status |
|---|---|---|---|
| foot_wins | XX% | ≥50% | ✅/❌ |
| competitive_score | XX | ≥60 | ✅/❌ |
| spatial_health | XX dB | [-3,-8] | ✅/❌ |
| kf_ratio | XX dB | ≤-10 | ✅/❌ |

**Spatial-Hook Status:** <aktiv/inaktiv> (siehe AUD-H1)

**Top-3 Empfehlungen:**
1. <Filter X | aktuell A | neu B | Delta +X% | Begruendung>
2. ...
3. ...

**Naechster Test:** der Nutzer recordet mit neuer Config, dann erneut /footstep-eq-tuner
```

## Constraints
- NIEMALS automatisch Configs deployen — nur Empfehlung schreiben
- Keine Aenderung ohne Vision-Tabellen-Bezug
- Bei aktivem Spatial-Hook + AUD-H1 noch nicht gefixt: Warning ausgeben
- Auf der Nutzer's konkrete Aufnahme bezogen, keine generischen Tipps
