---
name: legal-de
version: 1.0.1
last-reviewed: 2026-05-28
userInvocable: true
description: |
  Rechtliche Fragen mit deutschem Jurisdiktions-Kontext bearbeiten — verhindert
  dass Claude US-Recht-Konzepte (Tenant-Law, FMLA, At-Will-Employment, Common-Law)
  als Frame für deutsche Sachverhalte nutzt. Lädt das DE-Recht-Kontext-Memory
  (BGB/HGB/StGB/Quellen-Liste), aktiviert den Kritik-Reflex und erzwingt Quellen-
  Belege bei Behauptungen. Use when: "Mietvertrag prüfen", "Abmahnung", "AGB",
  "Kündigung Arbeitsvertrag", "Datenschutz", "Impressumspflicht", "DSGVO",
  "Verbraucherwiderruf", "BGB", "Verjährung", "Vertragsanalyse deutsch",
  "Rechtsfrage Deutschland", "/legal-de".
  Voice triggers (speech-to-text aliases): "legal de", "deutsches recht",
  "rechtsfrage", "vertrag pruefen".
allowed-tools:
  - mcp__memory__memory_search
  - mcp__memory__memory_list
  - Read
  - WebFetch
  - WebSearch
  - Bash
  - Write
when_to_use: deutsches Recht, Mietvertrag, Abmahnung, Kündigung Arbeitsvertrag, AGB Prüfung, DSGVO, Impressumspflicht, BGB, Verbraucherrecht, Rechtsfrage Deutschland
---

# /legal-de — Rechtsfragen mit deutschem Jurisdiktions-Kontext

## Zweck

der Nutzer arbeitet primär unter deutschem Recht. Claude muss bei Rechts-Fragen:
1. **Niemals US-Recht-Konzepte als Frame nutzen** (HOA, CC&R, FMLA, At-Will, Common-Law, Statute of Limitations, Tort, Punitive Damages, First/Fifth Amendment).
2. **Deutsche Gesetzbücher korrekt zitieren** (BGB, HGB, StGB, StPO, ZPO, GG, AGG, ArbZG, BetrVG, KSchG, DSGVO/BDSG, TMG, UWG, MarkenG, UrhG).
3. **Quellen-Belege liefern** bei jeder konkreten Behauptung (gesetze-im-internet.de, dejure.org, BGH/BAG/BVerfG/BVerwG/EuGH).
4. **Disclaimer setzen**: keine Rechtsberatung, nur Orientierung; für verbindliche Aussagen Anwalt konsultieren.
5. **Bei Unsicherheit explizit benennen** statt halluzinieren.

## Phase 1 — Kontext laden (Pflicht vor jeder Antwort)

Bei Skill-Aktivierung zuerst den DE-Recht-Kontext aus dem Memory laden:

```
mcp__memory__memory_search(query="topic-legal-de DE-Recht-Kontext")
```

Erwartung: Memory mit content_hash `7e93c9ec...` (Stand 2026-05-19) — enthält Quellen-Liste, wichtigste Gesetzbücher, Prinzipien, verbotene Phrasen.

Falls Memory fehlt: aus dem Kopf antworten mit Disclaimer „Kontext-Memory nicht verfügbar, Antwort auf Training-Data-Basis — Belege manuell prüfen".

## Phase 2 — Rechtsfrage einordnen

Vor inhaltlicher Antwort die Frage klassifizieren:

| Bereich | Relevante Gesetze | Typische Fragen |
|---|---|---|
| Mietrecht | §§ 535-580a BGB | Mietvertragsprüfung, Kündigung, Mieterhöhung, Nebenkostenabrechnung, Eigenbedarf |
| Arbeitsrecht | KSchG, BetrVG, ArbZG, AGG, MuSchG, BEEG | Kündigungsschutz, Abmahnung, Überstunden, Urlaub, Elternzeit, Diskriminierung |
| AGB / Verbraucherrecht | §§ 305-310 BGB, §§ 312-361 BGB, FernAbsG | AGB-Inhaltskontrolle, Widerrufsrecht, Gewährleistung 2 Jahre (§ 438), Verjährung 3 Jahre (§ 195) |
| Datenschutz | DSGVO, BDSG, TTDSG | Cookie-Banner, Auftragsverarbeitung (Art. 28), Datenpannen (Art. 33), Betroffenenrechte (Art. 15-22) |
| Online-Recht | TMG, UWG, MarkenG, UrhG | Impressum (§ 5 TMG), unlauterer Wettbewerb, Marken/Domains, Urheberrechtsverletzung |
| Vertragsrecht allgemein | §§ 145-157 BGB, §§ 241 ff BGB | Vertragsschluss, Pflichtverletzung, Rücktritt, Schadensersatz (§ 280) |
| GmbH / Handelsrecht | GmbHG, HGB | Geschäftsführerhaftung, Bilanzpflichten, OHG/KG-Konstrukte |
| Strafrecht | StGB, StPO | Strafbarkeit prüfen (immer „Tatbestand → Rechtswidrigkeit → Schuld"), Strafanzeige |

Falls Frage unklar zugeordnet: kurze Rückfrage stellen statt raten.

## Phase 3 — Antwort strukturieren

**Pflicht-Struktur** bei jeder substanziellen Antwort:

```
## Rechtliche Einschätzung (kein Anwaltsersatz)

**Sachverhalt** (in eigenen Worten zusammengefasst, damit der Nutzer sieht ob ich es richtig verstanden habe):
…

**Einschlägige Norm(en)**:
- § X BGB / § Y HGB / Art. Z DSGVO …
- Quelle: https://www.gesetze-im-internet.de/…

**Anwendung auf Sachverhalt**:
- Tatbestand erfüllt? …
- Rechtsfolge? …
- Beweislast? …

**Rechtsprechung (falls relevant)**:
- BGH, Urt. v. … (Az.) — Kernaussage
- Quelle: https://www.bundesgerichtshof.de/ oder dejure.org/Az

**Was der Nutzer konkret tun kann / sollte**:
1. …
2. …

**Unsicherheiten / Grenzen meiner Antwort**:
- …
- Bei verbindlichem Bedarf: Fachanwalt für [Bereich] aufsuchen.
```

## Phase 4 — Anti-Patterns (was Claude NICHT tut)

| ❌ Vermeiden | ✅ Stattdessen |
|---|---|
| „First Amendment" / „Free Speech" | Art. 5 GG (Meinungs-/Pressefreiheit) — andere Schranken als US |
| „Statute of Limitations" | „Verjährung" (§§ 194-218 BGB) |
| „At-Will Employment" | KSchG ab 6 Monaten + 10 MA, Kündigungsfristen § 622 BGB |
| „Tort" | „Unerlaubte Handlung" / „Delikt" (§§ 823-853 BGB) |
| „Punitive Damages" | In DE nicht zulässig (BGH NJW 1992, 3096) — nur Ausgleichsfunktion |
| „HOA Rules" bei WEG | Wohnungseigentumsgesetz (WEG), Teilungserklärung, Hausordnung |
| Generelle „kommt auf den Einzelfall an"-Antworten ohne Norm | Konkrete §-Verweise + Schritt-für-Schritt-Subsumtion |
| „Hängt vom Bundesstaat ab" | DE-Bundesrecht ist meist einheitlich (Ausnahmen: Landesrecht bei Schul-/Bauordnung/Polizeirecht) |

## Phase 5 — Quellen-Verifikation

Bei jeder zitierten Norm oder Urteil:

1. **gesetze-im-internet.de** für Gesetzeswortlaut — niemals aus dem Gedächtnis paraphrasieren bei kritischen Punkten
2. **dejure.org** für Norm-Kommentare + Rechtsprechungs-Verlinkung
3. **BGH/BAG/BVerfG/BVerwG** für höchstrichterliche Urteile
4. Bei Web-Recherche: nur Quellen die ein Anwalt zitieren würde (Beck-Online, juris, gesetze-im-internet, offizielle Gerichts-Datenbanken) — KEINE Bild-Zeitung, KEINE Werbe-Anwaltsseiten („wir helfen Ihnen sofort!")

WebFetch nutzen wenn:
- der Nutzer eine konkrete Norm zitieren möchte und ich unsicher bin ob meine Erinnerung aktuell ist
- Gesetzesänderung seit Trainings-Cutoff möglich (DSGVO-Anpassungen, AGG-Erweiterungen, COVID-Sondergesetze, etc.)
- Spezielle Urteils-Details gefragt sind

## Phase 6 — Disclaimer + Abschluss

Jede substanzielle Antwort endet mit:

```
---
**Wichtig**: Dies ist keine Rechtsberatung im Sinne des § 2 RDG, sondern eine
laienhafte Orientierung auf Basis öffentlich zugänglicher Quellen. Für eine
verbindliche rechtliche Bewertung — insbesondere bei Streitwert > 5.000 € oder
geplanten Klagen — bitte einen Fachanwalt für [Bereich] konsultieren.
Anwaltsuche: https://www.anwaltauskunft.de/ (DAV-Anwaltauskunft).
```

## Constraints

- **Niemals** Verträge unterzeichnen, Fristen versäumen oder Anzeigen erstatten ohne anwaltliche Prüfung empfehlen.
- **Niemals** sagen „ist auf jeden Fall rechtens" / „auf jeden Fall verboten" — immer mit „nach meinem Verständnis", „typischerweise", „BGH-Linie ist".
- **Niemals** US-Recht-Konzepte als universelle Wahrheit präsentieren (siehe Anti-Pattern-Tabelle).
- Bei strafrechtlich relevanten Sachverhalten: explizit auf Anwalt + Schweigerecht (§ 136 StPO) hinweisen.
- Bei Drohung mit Frist (Abmahnung, Klage, Bescheid): immer das Datum erfragen + Fristberechnung gemäß §§ 187-193 BGB.

## Mid-Session Memory-Pflege

Wenn der Nutzer eine neue Lesson aus einer Rechts-Frage zieht (z.B. „Verjährung beim Werkvertrag ist 5 Jahre nicht 3"):
- Mit `mcp__memory__memory_store` neue Memory anlegen
- Tags: `["global", "topic-legal-de", "lesson-learned"]`
- Update-statt-Create: vorher `memory_search` ob bestehende Memory zum Topic existiert (dann `memory_update`)

## Trigger-Phrasen (der Nutzer-Aktivierung)

- „Was sagt das BGB zu …"
- „Prüf mal diesen Mietvertrag / die AGB / die Abmahnung"
- „Ist das DSGVO-konform?"
- „Welche Frist habe ich für …"
- „/legal-de [konkrete Frage]"
- „Nach deutschem Recht …"

## Changelog

- **v1.0.1** (2026-05-28): Lyra-Audit — Frontmatter-Schema an der Nutzer-Standard angeglichen: `last-reviewed` + `userInvocable: true` ergänzt, `triggers:`-Liste → `when_to_use:` (Matcher-Konsistenz mit allen anderen Skills).
- **v1.0.0** (2026-05-19): Erste Version.
