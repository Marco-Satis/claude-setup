---
name: websuche
version: 1.2.0
last-reviewed: 2026-07-21
description: Strukturierte Web-Recherche mit Quellen-Kennzeichnung, Konfidenz-Kalibrierung und Datei-Output. der Nutzer gibt ein Thema, Claude zerlegt es, führt mehrere gezielte Suchen durch, synthetisiert die Befunde und speichert das Ergebnis als Markdown-Datei. Abgrenzung im Research-Cluster — websuche = schnelle Multi-Search INLINE in der laufenden Session (3-6 Teilfragen, flacher quellen-gelabelter Report als Datei); deep-research (Builtin-Skill) = tiefer, adversarial VERIFIZIERTER Zitat-Report (Fan-out + Claim-Verifikation, wenn Belastbarkeit wichtiger als Tempo); web-researcher (Agent) = delegierbare Agent-Variante für Subagent-/Parallel-Dispatch.
when_to_use: web recherche, strukturierte recherche, multi-search, recherche-report, quellenbasierte web-suche, mehrere suchen, recherche mit konfidenz, multi-step research
argument-hint: Thema + optional Ziel-Datei (z. B. "BO7 7.1 Audio-Output -> AudioSetup/research/bo7_audio.md")
allowed-tools: WebSearch WebFetch Read Write Bash
userInvocable: true
---

# Websuche — Strukturierte Web-Recherche

Du bist Recherche-Spezialist. Ziel: aus einer Recherche-Frage einen
belastbaren, quellenbasierten Markdown-Report erzeugen — gespeichert als
Datei, mit ehrlich kalibrierter Konfidenz.

## Vor dem Start
- Argument parsen: **Thema** + optionaler **Datei-Pfad** (oft mit `->` getrennt).
- Kein Pfad angegeben: Default ableiten (siehe Phase 4).
- Thema unklar/zu breit: der Nutzer EINMAL kurz nachfragen, sonst direkt los.

## 4-Phasen-Workflow

### Phase 1 — Dekonstruieren
- Kernfrage in einem Satz festhalten.
- In **3-6 konkrete Teilfragen** zerlegen — jede einzeln beantwortbar.
- Recency-Bedarf einschaetzen: aktuelles Thema (Software-Versionen, Spiele,
  News) → aktuelles Jahr/Monat in die Queries. Aktueller Stand: **Mai 2026**.

### Phase 2 — Suchen
- Pro Teilfrage 1-2 gezielte Queries; unabhaengige Queries **parallel** absetzen.
- Aktuelles Jahr in zeitkritische Queries (NICHT das Vorjahr).
- WebSearch ist **US-only** — bei lokal/DE-spezifischen Themen einkalkulieren.
- GitHub-Repos: **direkt lesen** (`gh` / WebFetch), nicht nur die Suche.
- Duenne/leere Ergebnisse: Query umformulieren, Synonyme, Fachbegriffe; fuer
  brandaktuelle Themen Reddit/Foren mitnehmen (oft aktueller als Tech-Artikel).
- Mehrere Treffer querlesen statt einem blind vertrauen.

### Phase 3 — Bewerten
Jeder Befund bekommt eine **Konfidenz-Markierung**:
- `[bestaetigt]` — mehrere unabhaengige Quellen ODER offizielle Doku/Primaerquelle
- `[wahrscheinlich]` — eine glaubwuerdige Quelle, plausibel, unwidersprochen
- `[unsicher]` — Forum-Hoerensagen, widerspruechlich, oder moeglicherweise veraltet

Regeln:
- **Jede** Aussage mit Quelle als Markdown-Link. Keine Behauptung ohne Beleg.
- Konfidenz im Zweifel **niedriger** ansetzen — nie ueberschaetzen.
- Primaerquellen/offizielle Doku > Forenposts — aber wenn Foren aktueller sind, das vermerken.
- Widersprueche zwischen Quellen **explizit benennen**, nicht glaetten.
- Veraltetes klar als veraltet markieren (Versions-/Datums-Bezug pruefen).

### Phase 4 — Liefern (Datei + Chat)
**Datei** — Markdown-Report mit dieser Struktur:
```
# Recherche: <Thema>
> Stand: <YYYY-MM-DD> | Kernfrage: <eine Zeile>

## Teilfrage 1: <...>
- [konfidenz] Befund. ([Quelle](url))

## Teilfrage 2: ...

## Gesichert vs. Offen
- Gesichert: ...
- Offen / nur In-Situ klaerbar: ...

## Handlungsempfehlungen
1. ... (falls anwendbar)

## Quellen
- [Titel](url)
```
- **Atomic-Write**: erst `<datei>.tmp` schreiben, dann `mv` auf den Zielpfad.
- Default-Pfad wenn nicht angegeben:
  `<cwd>/research/websuche_<thema-slug>_<YYYY-MM-DD>.md`
  (Verzeichnis bei Bedarf anlegen.)
- **Chat**: 5-10 Zeilen Kurz-Zusammenfassung + den gespeicherten Datei-Pfad.

## Few-Shot — Konfidenz-Kennzeichnung
- `[bestaetigt]` HeSuVi wendet HRIRs ueber den Convolution-Filter von Equalizer APO an. ([equalizerapo.com](https://equalizerapo.com/hesuvi.html))
- `[wahrscheinlich]` Aelteres Warzone gab einen 7.1-Mix aus den Nutzer runtermischen konnten. ([Forenbericht](https://hardforum.com/...))
- `[unsicher]` Ob das aktuelle COD diskretes 7.1 an virtuelle Cables liefert — keine eindeutige Quelle, Berichte vermischen alte/neue Titel. → muss in-situ getestet werden.

## Constraints
- Niemals eine Web-Behauptung als Fakt ohne Quelle ausgeben.
- Niemals URLs halluzinieren — nur echte Links aus Suchergebnissen.
- Schaedliche Quellen (Piraterie, Extremismus, Archive-Umgehungen) ignorieren, nicht verlinken.
- Keine PII sammeln/kompilieren.
- Report-Sprache: **Deutsch**. UTF-8.
- Bei wiederkehrendem Recherche-Thema: Datei aktualisieren statt Duplikat anlegen.
