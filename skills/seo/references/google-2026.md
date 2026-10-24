# Was Google selbst sagt (Stand Oktober 2026)

Quelle der Zusammenfassung: Recherche `~/projects/Skills_&_Co/research/SEO_RECHERCHE_2026-10-24.md`. Vor dem Zitieren einer Zahl die verlinkte Primärquelle öffnen; Google ändert Doku ohne Ankündigung.

## Kernregeln

| Thema | Regel | Quelle |
|---|---|---|
| KI-Suche | Für AI Overviews / AI Mode gibt es keine Extra-Anforderungen: indexierbar + snippet-fähig genügt. Kein Spezialschema, kein llms.txt, kein „Chunking“. | [AI features](https://developers.google.com/search/docs/appearance/ai-features), [AI Optimization Guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide) |
| E-E-A-T | Kein einzelner Rankingfaktor. Trust zählt am meisten, bei YMYL (Geld, Gesundheit, Recht) stärker. Sichtbar machen: **Who** (Autor mit echter Bio), **How** (wie entstanden, inkl. KI-Mitarbeit), **Why** (Zweck = Nutzern helfen). | [Creating helpful content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content) |
| KI-Inhalte | Erlaubt. Vor Veröffentlichung manuell faktenprüfen — auch Titel, Meta-Description, strukturierte Daten, Alt-Texte. | [Using gen AI content](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content) |
| Scaled Content Abuse | Viele Seiten hauptsächlich zur Ranking-Manipulation sind Spam, **egal wie erstellt** (Hand, Skript, KI). Gefahr: Varianten-Seiten je Keyword, umformulierte/übersetzte Fremddaten, Seiten nur für KI-„Fan-out“-Fragen. | [Spam Policies](https://developers.google.com/search/docs/essentials/spam-policies) |
| Weitere Spam-Arten | Expired Domain Abuse, Site Reputation Abuse (fremde Inhalte auf starker Domain), gekaufte Links, Cloaking, versteckter Text. | dito |
| Strukturierte Daten | Für KI-Funktionen nicht nötig, für Rich Results weiter sinnvoll. Muss dem sichtbaren Text entsprechen. | [AI features](https://developers.google.com/search/docs/appearance/ai-features) |
| Core Web Vitals | LCP ≤ 2,5 s · INP ≤ 200 ms (schlecht > 500 ms) · CLS ≤ 0,1, jeweils 75. Perzentil Felddaten. | [web.dev INP](https://web.dev/articles/inp) |
| Core Updates 2026 | März (27.03.–08.04.) und Mai (21.05.–02.06.); keine neuen Regeln, Verweis auf Helpful-Content-Doku. | Fachpresse, `[wahrscheinlich]` |
| Messung KI-Traffic | Steckt im normalen Search-Console-Leistungsbericht. Zusätzlich seit 03.06.2026 „Generative AI performance“-Bericht, nur für einen Teil der Properties. | [Google-Blog](https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports) |

## Prioritäten bei jedem Audit

1. **Crawlbar und indexierbar:** robots.txt sperrt nichts Wichtiges, Sitemap vorhanden und erreichbar, kein versehentliches `noindex`, Canonical zeigt auf sich selbst, HTTPS ohne Mixed Content, eine Hostvariante (www oder ohne) mit 301.
2. **Technik:** Mobildarstellung (Viewport), Geschwindigkeit, keine Weiterleitungsketten, Soft-404 vermeiden.
3. **On-Page:** einzigartiger Title (≈ 50–60 Zeichen, Kernbegriff vorn), Meta-Description (≈ 120–155 Zeichen, Nutzen + Handlung), genau eine H1, logische H2/H3, sprechende URLs, Alt-Texte, interne Links zu den Kernseiten.
4. **Inhalt:** trifft die Suchintention, eigener Mehrwert (eigene Daten, Erfahrung, Messwerte, Fotos), Who/How/Why sichtbar, aktuell.
5. **Autorität:** echte Erwähnungen und Links (Verzeichnisse der Branche, Partner, Fachartikel, Awesome-Listen). Keine gekauften Links.

## Was Google ausdrücklich NICHT braucht

- llms.txt (nicht genutzt), „KI-optimiertes Umschreiben“, künstliche Erwähnungen in Foren, Tools mit „KI-Ranking-Score“ (kein Drittanbieter hat Zugriff auf Googles Systeme).
