# des Nutzers Produkte: Zielgruppe, Kanal, Gates (Stand 2026-10-24)

**Rahmen (der Nutzer, 24.10.2026):** Alle Produkte entstehen zuerst für der Nutzer, Familie und Freunde (Eigenbedarf, eigener Einsatz); kommerzielle Nutzung ist Nebenziel. Kein Baustopp wegen fehlender Kundengespräche — Gespräche/Signale laufen nebenher, und „Verkaufsfähigkeit offen halten“ (Konfiguration statt Hardcoding, Daten je Nutzer getrennt, saubere Lizenz, Einrichtungsanleitung) ist die Bau-Regel.

Diese Datei ist eine Übersicht, **nicht** die Quelle. Vor jeder Empfehlung die je Produkt genannte maßgebliche Projektdatei lesen; bei Widerspruch gilt das Projekt. Ist der Stand hier älter als 30 Tage, Abgleich vorschlagen.

## 1. Agent OS + Voice-Agent (ein Produkt)

- **Maßgeblich:** `~/projects/Personal_Agent_OSS/PROGRESS.md`, `_intern/ENTSCHEIDUNGEN_K_*.md`, `_intern/KRITIK_produktplan_2026-10-19.md`, `_intern/MARCO_TODO.md`, `PLAN.md`.
- **Zeitplan:** Verkauf frühestens Mitte/Ende 2027 (Entscheidung K7); bis dahin Name, Domain und Textentwürfe, Live-Schaltung kurz vor Gewerbe/erstem Pilot.
- **Nische (offen, MARCO_TODO K7):** Vorschlag Fahrradwerkstätten (2–10 Leute) als erste Branche; PROGRESS sagt seit 19.10. „Baukasten statt Branche“ — Widerspruch, der Nutzer entscheidet. Verkauft wird ein Branchenpaket, nicht der Baukasten (KRITIK M4).
- **Was:** Self-hosted KI-Assistenz für kleine Betriebe (Fahrradwerkstätten/Handwerk): Die Anrufannahme läuft über einen Telefonie-Anbieter mit KI-Annahme nach Geschäftsschluss (K9, nicht selbst gebaut); der eigene Mehrwert liegt in Terminen, Auswertung und Modulen wie E-Mail/Kalender, Angebote und Freigaben. Technischer Kern ist Open Source (`~/projects/Personal_Agent_OSS`, GitHub `Marco-Satis/personal-agent-oss`). DSGVO als Architekturziel.
- **Wer zahlt:** Inhaber kleiner Betriebe, die Anrufe verpassen (auf der Baustelle, nach Feierabend). Testkunde: Familienbetrieb.
- **Wettbewerb:** fertige Telefon-KI-Dienste ab ca. 10–200 €/Monat; Agenturen mit 499 € Einrichtung + 199 €/Monat (Faktencheck 30.09.2026). Differenzierung muss belegt werden: DSGVO/Self-hosting, Handwerks-Abläufe, persönlicher Ansprechpartner.
- **Kanäle:** (a) Landingpage auf Deutsch für Betriebe („KI-Telefonassistent für Handwerksbetriebe“, Notdienst, Terminannahme), (b) Google-Unternehmensprofil + Servicegebiet, (c) Empfehlungen/Innungen, (d) GitHub/PyPI für Entwickler-Sichtbarkeit der Open-Source-Seite (englisch). Suchbegriffe von Betrieben sind Problembegriffe („Anrufe verpasst Baustelle“, „Telefonservice Handwerker“), nicht Technikbegriffe.
- **Gates:** Floppt-das-Gate über `/office-hours`. ⚠ Offener Widerspruch: Faktencheck empfiehlt einen **bezahlten** Pilot zu kleinem Festpreis, im Projekt ist der Familienbetrieb kostenloser Testkunde. Ein Gratis-Test belegt keine Zahlungsbereitschaft — der Nutzer entscheidet, ob ein zweiter, bezahlter Pilot nötig ist. Recht: KI-Hinweis Art. 50 KI-VO, keine Aufzeichnung ohne Einwilligung, AVV.
- **Öffentlich-Regel:** Im Repo und in Posts das Vorbild (Person, Produkt, Marke) nie nennen (Projekt-CLAUDE.md Regel 7).

## 2. FootstepPro (Audio-Setup)

- **Maßgeblich:** Audio_Setup-Projekt am PC (Session „Audio_Setup“), `wz find FootstepPro`.

- **Ausbau:** Start mit Call of Duty (des Nutzers Hauptspiel), später weitere Competitive Shooter (Valorant, CS2 …) — Spiel als Profil, Anti-Cheat/AGB je Spiel prüfen.
- **Was:** Audio-Kette für Call of Duty/Warzone am PC (Equalizer APO, VoiceMeeter, HeSuVi, eigene Analyse-Werkzeuge), die Schritte besser hörbar und ortbar macht; mit Messmethodik und Analyzer.
- **Wer zahlt:** PC-Spieler mit Headset, die Gegner zu spät hören. Ob sie für Presets zahlen, ist **unbelegt** — viele EQ-Presets gibt es gratis (Foren, YouTube, Headset-Software).
- **Kanäle:** YouTube (Vorher/Nachher-Hörbeispiele, Kopfhörer empfohlen), Reddit/Discord-Communities (ehrlich als Entwickler, Regeln der Subreddits), eine Produktseite mit Download/Anleitung. Suchbegriffe: „warzone footsteps eq“, „hear footsteps better warzone“, „equalizer apo cod settings“, deutsch „Warzone Schritte besser hören“.
- **Gates:** Floppt-das-Gate (Zahlungsbereitschaft gegen Gratis-Presets prüfen; Modell: gratis Basis + bezahltes Profil je Headset? Spende?). Recht: Markennamen nur beschreibend, keine Logos, kein Eingriff ins Spiel behaupten oder anbieten. Messwerte nur mit Methode veröffentlichen.

## 3. Trading-Bots

- **Maßgeblich:** `~/projects/Trading/PROGRESS.md`, `_intern/TRADING_HANDOFF_2026-10-18.md`.

- **Was:** Paper-Trading-Bots auf netcup (Alpaca Paper, Kraken-Simulation), Lernprojekt laut Faktencheck — **kein belegtes Einkommen**.
- **⚠ BaFin-Gate (immer zuerst):** Mit eigenem Geld keine Erlaubnis nötig. Bezahlte Signale, fremdes Geld, Vermögensverwaltung oder Anlageberatung brauchen eine Erlaubnis (KWG bzw. WpIG). Öffentlich geteilte Trades können als Anlageempfehlung gelten (Art. 20 MAR). Rendite-/Gewinnversprechen in Werbung sind irreführend (§ 5 UWG).
- **Was ohne Erlaubnis vermarktbar sein kann (Rechtsprüfung nötig):** die Software selbst als Open-Source-Werkzeug zum Lernen/Backtesting, Bildungsinhalte über Methodik (FernUSG beachten), Erfahrungsberichte mit Paper-Ergebnissen inkl. Hinweis „keine Anlageberatung, vergangene Ergebnisse garantieren nichts“.
- **Kanäle (erst nach Gate):** GitHub (englisch), technischer Blog zu Methodik und Krisentests. Keine Kurs-/Signal-Landingpages.

## 4. Open-Source-Repos (Querschnitt)

`personal-agent-oss` (Teil von Produkt 1) und `CoD_Waffen_DB` (öffentlich, CC-BY-4.0): GitHub-Hygiene laut `github-pypi.md` ist der günstigste erste Schritt, braucht keine Domain.
