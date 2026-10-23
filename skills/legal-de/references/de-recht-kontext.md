# DE-Recht-Kontext für legal-de

> Volltext gesichert 2026-10-23 aus mcp-memory 7e93c9ec8e8e (Stand 2026-05-19, TMG→DDG und § 23 GVG am 2026-10-23 nachgezogen), damit der Skill ohne mcp-Store auskommt.

Deutsches Recht — Kontext-Memory für Claude-Sessions (BGB/HGB/StGB/etc.)

ZWECK: Claude soll bei rechtlichen Fragen mit deutschem Kontext NICHT US-Recht-Konzepte als Frame nutzen (US Tenant-Law statt BGB-Mietrecht, US Contract-Law statt §§ 305 ff BGB AGB-Recht, etc.). Anthropic's Claude-for-Legal Plugin-Suite ist US-jurisdiction-locked und löst das nicht.

PRIMÄRE QUELLEN (für Verifikation + Zitation):
- https://www.gesetze-im-internet.de/ — Bundesrecht volltext (kostenlos, offiziell)
- https://www.dejure.org/ — Rechtsprechung + Kommentare + Norm-Verlinkung
- BGH-Datenbank: https://www.bundesgerichtshof.de/ — höchstrichterliche Zivil- & Strafrechtsprechung
- BAG-Datenbank: https://www.bundesarbeitsgericht.de/ — Arbeitsrecht
- BVerfG: https://www.bundesverfassungsgericht.de/ — Verfassungsrecht
- BVerwG: https://www.bundesverwaltungsgericht.de/ — Verwaltungsrecht
- EuGH: https://curia.europa.eu/ — EU-Recht
- juris.de — kommerzielle Datenbank (Pflicht-Zugang für ernsthafte Praxis)

WICHTIGSTE GESETZBÜCHER (Kürzel für Zitation):
- BGB — Bürgerliches Gesetzbuch (Zivilrecht, Schuldrecht, Mietrecht, Erbrecht)
- HGB — Handelsgesetzbuch (Kaufleute, Handelsbücher, OHG/KG)
- StGB — Strafgesetzbuch
- StPO — Strafprozessordnung
- ZPO — Zivilprozessordnung
- GG — Grundgesetz
- AGG — Allgemeines Gleichbehandlungsgesetz
- ArbZG — Arbeitszeitgesetz
- BetrVG — Betriebsverfassungsgesetz
- KSchG — Kündigungsschutzgesetz
- DSGVO/BDSG — Datenschutz
- TKG — Telekommunikationsgesetz
- DDG — Digitale-Dienste-Gesetz (Impressumspflicht; ersetzt seit 14.05.2024 das TMG)
- UWG — Gesetz gegen unlauteren Wettbewerb
- MarkenG — Markengesetz
- UrhG — Urheberrechtsgesetz

ZENTRALE PRINZIPIEN DEUTSCHES RECHT (≠ US-Recht!):
- Schriftform (§ 126 BGB) vs Textform (§ 126b BGB) vs elektronische Form (§ 126a BGB) — strikte Unterscheidung
- Verjährungsfristen: Standard 3 Jahre (§ 195 BGB), Gewährleistung 2 Jahre (§ 438 BGB)
- AGB-Recht: §§ 305-310 BGB (deutlich strenger als US-Standards, salvatorische Klausel ≠ Lückenfüller)
- Verbraucherwiderruf: 14 Tage (§ 355 BGB) bei Fernabsatz
- Mietrecht: Mieterschutz hoch (Kündigungsfristen § 573c BGB, Mieterhöhung §§ 558 ff BGB)
- Arbeitsrecht: Kündigungsschutz nach 6 Monaten + 10 MA-Schwelle (KSchG)
- Datenschutz: DSGVO + BDSG, Auftragsverarbeitung nach Art. 28 DSGVO
- Impressumspflicht: § 5 DDG (früher § 5 TMG, außer Kraft seit 14.05.2024)
- Allgemeines Gleichbehandlungsgesetz: Diskriminierungsverbot bei Beschäftigung + Massengeschäften

KRITIK-REFLEX (für Claude):
1. Vor jeder rechtlichen Aussage prüfen: US- oder DE-Jurisdiktion? Bei der Nutzer IMMER DE.
2. Bei Unsicherheit: Quelle benennen oder explizit "weiß ich nicht sicher" sagen
3. Niemals US-Rechtskonzepte (HOA, CC&R, FMLA, At-Will-Employment) als Frame für DE-Sachverhalt
4. Disclaimer: "Keine Rechtsberatung, nur Orientierung. Für verbindliche Aussagen Anwalt konsultieren."
5. Bei Verträgen: nicht nur den Wortlaut prüfen, sondern auch §§ 305 ff BGB (AGB-Inhaltskontrolle) anwenden
6. Bei Streitwerten oberhalb der Amtsgerichtsgrenze (§ 23 GVG): Hinweis auf Anwaltszwang vor dem Landgericht (§ 78 ZPO). Die Grenze lag lange bei 5.000 €; vor einer Aussage die aktuelle Fassung von § 23 GVG prüfen.

VERBOTENE PHRASEN:
- "First Amendment" / "Fifth Amendment" als Argument bei DE-Sachverhalt
- "Common Law" Konzepte ohne DE-Äquivalent-Übersetzung
- "Statute of Limitations" → korrekt: "Verjährung"
- "Tort" → korrekt: "unerlaubte Handlung" / "Delikt" (§§ 823 ff BGB)
- "Punitive Damages" → in DE nicht zulässig (BGH NJW 1992, 3096)

CROSS-PROJECT: gilt für alle der Nutzer-Projekte bei rechtlichen Fragen (Mietvertrag, Versicherungs-AGBs, GmbH-Verträge, GbR-Konstrukte, Datenschutz für Discord-Bots, etc.)
