---
name: spatial-pipeline-helper
version: 2.0.0
last-reviewed: 2026-05-17
description: DSP-Korrektheit-Check fuer FootstepPro Spatial-Pipeline. Validiert spatial_health-Adjustment, prueft TRANSIENT_PROFILES-Centroid-Konflikte, schaetzt Performance-Impact von analyze_spatial. Nutze bei Edits an spatial_analyzer.py oder metrics.py:spatial_health.
when_to_use: footstep spatial, DSP pipeline check, spatial_analyzer review, TRANSIENT_PROFILES centroid conflict, audio pipeline audit, spatial_health AUD-H1
argument-hint: Optional File-Pfad (default = beide pruefen)
allowed-tools: Read Grep Glob Bash Write Edit
userInvocable: true
---

# Spatial-Pipeline-Helper — FootstepPro DSP-Check

Du pruefst die Spatial-Pipeline-Komponenten von FootstepPro auf bekannte Drift-Muster aus REVIEW_REPORT_audio.md (v4 / 2026-05-05).

## Vor dem Start
Datenbasis ist **(Windows-lokal)** — FootstepPro/FootstepAnalyzer liegt nur auf dem PC (EqualizerAPO-Setup, kein Syncthing-Sync, auf netcup nicht vorhanden). In netcup-Sessions nur mit explizit bereitgestellten Dateien arbeiten:
- Aktuelles File: `C:\Users\der Nutzer\OneDrive\Dokumente\AudioSetup\FootstepAnalyzer\spatial_analyzer.py` (Windows-lokal)
- Score-Logik: `C:\Users\der Nutzer\OneDrive\Dokumente\AudioSetup\FootstepAnalyzer\metrics.py` (Windows-lokal; Funktionen `spatial_health` + `compute_psychoacoustic_metrics`)
- Profile: `C:\Users\der Nutzer\OneDrive\Dokumente\AudioSetup\FootstepAnalyzer\constants.py` (Windows-lokal; TRANSIENT_PROFILES)

## Checks

### 1. spatial_health-Adjustment-Asymmetrie (AUD-H1)
Lies `metrics.py` und pruefe ob `spatial_health(levels, spatial=...)` Adjustment direkt auf `result` addiert (FALSCH) ODER als separater Bonus auf `spatial_bonus`-Score (RICHTIG).

**Falsch (Sabotage-Risiko):**
```python
result = spatial_db - foot_db
result += iacc_bonus + spread_bonus  # schiebt aus Idealband [-8,-3] heraus
```

**Richtig:**
```python
sh = spatial_health(bands.levels)  # ohne spatial-Argument
# ... Score-Mapping ergibt spatial_bonus ...
if spatial is not None and not spatial.is_mono:
    spatial_bonus = min(100.0, spatial_bonus + iacc_bonus_pts + spread_bonus_pts)
```

### 2. TRANSIENT_PROFILES-Konflikt-Matrix (AUD-H3)
Lies `constants.py:TRANSIENT_PROFILES` und baue eine Konflikt-Matrix:
- Profile mit gleichen `primary_bands` UND ueberlappenden `centroid_range_hz`
- Speziell: `footstep_grass` darf B9 NICHT in primary haben (Killstreak-Kollision)
- Speziell: `crate_idle_hum` und `footstep_concrete` duerfen sich nicht in primary_bands UND centroid_range gleichzeitig ueberlappen ohne Disambiguierung (z.B. min_above_db-Differenz >=2 oder duration-Filter)

### 3. Performance-Estimate (AUD-H2)
Bei einer Aufnahmen-Laenge L (in Sekunden) bei sr=48000:
- ITD-Loop: n_windows × ~2 ms (FFT-correlate 24k Samples)
- ILD-Loop: 12 × n_windows × ~80 us (per-window RMS)
- n_windows ≈ (L × 48000 - 24000) / 2400 + 1

Bei L=1800 (30 Min): ~140 s. Empfohlene Vektorisierung via `sliding_window_view`.

### 4. ITD-Vorzeichen-Konvention
ITD-Test soll mit Rauschen (nicht Sinus!) erfolgen:
```python
L = np.random.randn(96000)
R = np.roll(L, 30)  # R kommt 30 Samples spaeter
# Erwartung: ITD ≈ -0.625 ms (negativ = L fuehrt)
```
Bei Sinus-Tests ist Cross-Correlation aliasinganfaellig (Periode-Aliasing).

## Output
```
🎚 Spatial-Pipeline-Check

✅ AUD-H1 spatial_health Adjustment: <PASS|FAIL — Begruendung>
✅ AUD-H3 TRANSIENT_PROFILES Konflikte: <PASS|FAIL — Liste der Konflikte>
ℹ AUD-H2 Performance-Estimate: ~<X> s fuer 30-Min Stereo
✅ ITD-Vorzeichen-Konvention: <PASS|FAIL>

**Empfehlungen:** ...
```

## Constraints
- Read-only — keine Auto-Fixes
- Niemals `spatial=None`-Default in Code aendern ohne der Nutzer-Approval
- Bei TRANSIENT_PROFILES-Konflikten: zuerst dokumentieren, dann erst diskutieren
