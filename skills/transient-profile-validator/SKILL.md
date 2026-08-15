---
name: transient-profile-validator
version: 2.0.0
last-reviewed: 2026-05-17
description: Validiert FootstepPro TRANSIENT_PROFILES auf Centroid-Range vs primary_bands-Konsistenz und Sound-Klassen-Kollisionen. Nutze bei jedem Edit von constants.py TRANSIENT_PROFILES oder bevor neue Profile hinzugefuegt werden.
when_to_use: TRANSIENT_PROFILES validation, FootstepPro profile check, centroid-bands consistency, sound class collision, AUD-H3
argument-hint: Optional Profil-Name (default = alle Profile)
allowed-tools: Read Grep Glob Bash Write Edit
userInvocable: true
---

# Transient-Profile-Validator

Pruefst alle FootstepPro TRANSIENT_PROFILES auf interne Konsistenz und Inter-Profile-Kollisionen. Basiert auf REVIEW_REPORT_audio.md v4 (AUD-H3).

## Datenbasis

`C:\Users\der Nutzer\OneDrive\Dokumente\AudioSetup\FootstepAnalyzer\constants.py` **(Windows-lokal** — FootstepPro liegt nur auf dem PC, kein Syncthing-Sync, auf netcup nicht vorhanden**)** — Symbol `TRANSIENT_PROFILES` (Dict). Zeilennummern driften beim Editieren; Position per `grep -n "TRANSIENT_PROFILES" constants.py` bestimmen.

12 BANDS-Definition (zur Centroid-Range-Validation):
- B1 20-80, B2 80-200, B3 200-500, B4 500-800, B5 800-1100, B6 1100-1800
- B7 1800-2100, B8 2100-2500, B9 2500-3500, B10 3500-5000, B11 5000-10000, B12 10000-24000

## Checks

### 1. Centroid-Range-vs-primary_bands-Konsistenz (pro Profil)
Fuer jedes Profil:
- `centroid_range_hz` muss in der Frequenz-Range der `primary_bands` UNION `secondary_bands` liegen
- `centroid_range_hz` darf NICHT signifikant ausserhalb (>20% Drift) liegen

**Beispiel-Failure:** `gunshot_far` mit centroid 50-250 Hz und primary B1+B2 (20-200) — Obergrenze 250 ueberschreitet B2-Hi 200. Tolerable Drift, aber dokumentieren.

### 2. Inter-Profile-Kollisions-Matrix
Fuer jedes Paar (P1, P2) aus TRANSIENT_PROFILES:
- Wenn `primary_bands(P1) == primary_bands(P2)` UND `centroid_range_hz` ueberlappt:
  → Disambiguator pruefen (eines der folgenden):
    - `min_above_noise_db`-Differenz >= 2 dB
    - `surface`-Field unterschiedlich gesetzt
    - `distance`-Field unterschiedlich gesetzt
    - `is_masking_source`-Field unterschiedlich
- Bei fehlendem Disambiguator: KONFLIKT melden

### 3. Bekannte Konflikt-Patterns (AUD-H3 aus v4)
- **footstep_grass:** primary darf NICHT B9 enthalten (Killstreak-Kollision). Erlaubt: B7, B8 in primary; B9 nur in secondary.
- **crate_idle_hum vs footstep_concrete:** beide haben primary B7+B8, ueberlappende centroid_range. Disambiguator-Check: `is_masking_source=True` (crate) vs `surface='concrete'` (footstep) ist OK, aber duration-Filter im segment_classifier waere besser.
- **damage_indicator vs footstep:** damage_indicator hat primary B6+B7+B8, centroid 1500-3500. Ueberlappt mit allen 7 footstep_*-Profilen. Hier ist der Disambiguator das duration_ms-Feld (damage <150ms) — aber segment_classifier wertet duration nicht aus.

### 4. Surface-Field-Konsistenz
Profile mit `surface`-Field muessen einer der 7 erlaubten Werte haben:
`{'concrete', 'metal', 'wood', 'grass', 'sand', 'snow', 'water'}`

### 5. Distance-Field-Konsistenz
Profile mit `distance`-Field muessen einer der erlaubten Werte haben:
`{'near', 'medium', 'far', 'very_far'}` (auch wenn aktuell nur 'near'/'far' aktiv sind)

## Output
```
🔍 TRANSIENT_PROFILES Validation

**Profile-Anzahl:** N
**Konflikt-Matrix:**
| P1 | P2 | Konflikt-Typ | Disambiguator | OK? |

**Inkonsistenzen:**
- <profile>: <was stimmt nicht>

**Empfehlungen:**
- <Konkrete Code-Aenderung>
```

## Constraints
- Read-only — keine Auto-Fixes
- Bei neuem Profil VOR Aufnahme in TRANSIENT_PROFILES: Konflikt-Matrix-Lauf
- segment_classifier.classify_segments wertet `duration_ms` aktuell NICHT aus (per-window vs event-based) — Disambiguator via duration ist nur als TODO-Marker zulaessig, nicht als aktiver Disambiguator
