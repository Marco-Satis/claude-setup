# Severity-Anker — kanonische Quelle (review-Familie)

> **Single-Source-of-Truth** für Severity-Skala, Kalibrierungs-Anker und
> Anti-Patterns. Genutzt von `/review`, `/quick-review`, `/full-audit`,
> `/security-audit`. **Recalibration NUR hier** — die Skills referenzieren diese
> Datei statt zu kopieren (verhindert Cross-Skill-Drift; Audit-Fund M1 2026-06-03).

## K1 — Severity-Skala

| Severity | Wann |
|----------|------|
| **CRITICAL** | Active Exploit ohne Pre-Conditions, sofort fixen, kein Workaround |
| **HIGH** | Exploitable unter realistischen Bedingungen ODER grosser Data-Loss-Risk |
| **MEDIUM** | Plausibles Risiko mit Workaround/Pre-Conditions ODER strukturelle Schwaeche die waechst. Fix wenn Aufwand < 30 min |
| **LOW** | Polish, Resilience, Future-Proofing. Backlog |
| **INFO** | Beobachtung ohne Risiko, aber nennenswert |

## K2 — Severity-Anker (die EINE Liste)

Jedes HIGH/CRITICAL gegen diese Anker pruefen (in Self-Review-Pass Pflicht):

| Befund | Severity |
|---|---|
| Hardcoded Pfad der bei Upgrade bricht | MEDIUM |
| Magic Number ohne Konstante | LOW |
| Fehlende Tests bei Security-/Auth-/DB-Code | MEDIUM |
| Fehlende Tests bei Util-Code | LOW |
| Bare-except: pass in Persistence/Security/Auth-Code | HIGH |
| Bare-except: pass in Diagnose/Logger-Tool | LOW |
| Silent-Swallow: Error-Branch logged nichts UND wirft nichts | MEDIUM |
| Doku-Drift (Rule verschwand beim Refactor) | MEDIUM |
| Duplicate-Install (System + venv) | MEDIUM (Update-Drift) — **nie LOW** |
| Funktion tut Gegenteil von Docstring/Description | HIGH |
| Vertrags-Drift Return-Type (silent-None statt int) | MEDIUM |
| Dead-Param (deklariert, nie verwendet) | LOW |
| Branch nie getroffen + keine Test-Coverage in Security/Auth/Persistence | MEDIUM |
| Branch nie getroffen in Util/Diagnose | LOW |
| Off-by-one in produktiven Loops | MEDIUM (HIGH wenn Datenverlust) |
| Daten-Pfad bricht im Hop ab (session.add ohne commit, write ohne flush) | HIGH |
| Daten-Pfad routet bei Fehler ins Nichts (silent drop ohne Notify) | MEDIUM (HIGH wenn Audit-/Security-relevant) |
| Race-Condition shared-state ohne Lock (Sync, Multi-Thread/Subprocess) | HIGH |
| Loop ohne klaren Termination-Pfad | MEDIUM |
| Caller ruft geaenderte Signatur falsch auf (Runtime-Fehler) | HIGH |
| Caller verarbeitet geaendertes Return-Shape falsch (still-falsch) | HIGH |

### K2p — Projekt-Achsen-Anker (E-J, ab review v4.5)

Fuer die Projekt-Ebene (Architektur, Doku, Config, Hygiene, Betrieb, Ziel). Gleiche
Kalibrier-Pflicht wie oben: jedes HIGH/CRITICAL dagegen pruefen.

| Befund | Severity |
|---|---|
| **E — Architektur** | |
| Divergiertes Duplikat eines geteilten Kern-Moduls (beide produktiv, Fixes laufen auseinander) | HIGH |
| Byte-identische Kopie einer Datei an 2 Orten (noch nicht divergiert) | MEDIUM |
| Zirkulaerer Import zwischen Modulen | MEDIUM |
| God-File (>1000 LoC, >5 unabhaengige Verantwortlichkeiten) | MEDIUM |
| Layering-Bruch (Low-Level-Modul importiert High-Level/Feature-Modul) | MEDIUM |
| Copy-Paste-Block ≥30 Zeilen in 3+ Files | MEDIUM |
| **F — Doku/Instruktionen** | |
| Doku beschreibt Verhalten das der Code NICHT hat (aktiv falsch, jemand handelt danach) | HIGH |
| Doku nennt Datei/Funktion/Flag der nicht mehr existiert | MEDIUM |
| Neues oeffentliches Modul/Command gar nicht dokumentiert | MEDIUM |
| Veraltete Zeilenzahl/Versionsangabe in Doku | LOW |
| CLAUDE.md/Rule widerspricht dem realen Setup | MEDIUM (HIGH wenn eine Session danach handelt und Daten schreibt) |
| **G — Config/Env/Deploy** | |
| Code liest ENV-Variable die nirgends gesetzt/dokumentiert ist (Dienst startet nicht / laeuft still degraded) | HIGH |
| Secret im Klartext ausserhalb der Secret-Ablage (Repo/Doku/Log) | CRITICAL |
| `.env.example` fehlt Variable die der Code zwingend braucht | MEDIUM |
| Verwaiste ENV-Variable (gesetzt, nirgends gelesen) | LOW |
| Hardcodeter Port/Pfad/Host der mit einer bestehenden Belegung kollidiert | MEDIUM |
| systemd-/Cron-Unit referenziert nicht existierenden Pfad oder Interpreter | HIGH |
| **H — Repo-Hygiene** | |
| `.sync-conflict`-/Konflikt-Kopie im aktiven Quellbaum (Import-/Ausfuehrungs-Risiko) | MEDIUM (HIGH wenn importierbar neben dem Original) |
| Secret-/Credential-Datei getrackt oder nicht ignoriert | CRITICAL |
| Build-/Cache-Artefakt getrackt (`__pycache__`, `*.pyc`, `venv`) | LOW |
| Toter Einstiegspunkt (Script/Hook nirgends referenziert, kein Runner) | LOW (MEDIUM wenn er noch per Cron/Timer laeuft) |
| `.bak`-Halde > 10 Dateien im aktiven Baum | LOW |
| **I — Betrieb/Beobachtbarkeit** | |
| Dienst faellt aus und NICHTS meldet es (kein Log, kein Notify, kein Watchdog) | HIGH |
| Recovery-/Restart-Pfad existiert, wurde aber nie ausgefuehrt/verifiziert | MEDIUM |
| Backup dokumentiert, aber kein verifizierter Restore | MEDIUM |
| Cron/Timer nicht idempotent (Doppel-Lauf beschaedigt State) | HIGH |
| Log ohne Rotation auf wachsendem Pfad | LOW (MEDIUM bei Disk-Druck) |
| **J — Ziel-/Anforderungs-Abgleich** | |
| Dokumentiertes Kern-Feature existiert im Code nicht | HIGH |
| Feature gebaut, aber von nichts aufgerufen (YAGNI-Leiche) | LOW (MEDIUM wenn es Ressourcen verbraucht) |
| Implementierung weicht vom zugrundeliegenden Plan ab, ohne dass die Abweichung begruendet ist | MEDIUM |

## K3 — Anti-Patterns (in JEDEM Review-Output verboten — Confirmation-Bias-Schutz)

| Anti-Pattern | Korrektur |
|--------------|-----------|
| Kraft-Adjektive ohne Beweis ("saubere Architektur", "elegant") | konkrete File:Zeile + warum |
| Score-Vergaben ("90%", "9/10", "B+") | Befunde-Anzahl je Severity |
| Vergleich-Selbstlob ("besser als letztes Review") | gehoert in DIFF_SUMMARY.md |
| Implizite Generalisierung ("im akzeptablen Rahmen") | "akzeptabel WEIL ..." oder "nicht WEIL ..." |
| Findings ohne File:Zeile | "_health.py:139 bare-except — robust gegen Y, brittle gegen Z" |
| Empfehlungs-Floskeln ("sollte ggf. ueberdacht werden") | "Fix in X Min: ..." oder "kein Fix WEIL ..." |
| Production-Ready-Behauptung | weglassen — ist des Nutzers Entscheidung |

---
*Erstellt 2026-06-03 (Audit-Fund M1). Bei Aenderung: nur hier — alle Review-Skills ziehen daraus.*
