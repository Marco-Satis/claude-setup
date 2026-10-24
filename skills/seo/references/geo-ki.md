# Sichtbarkeit in KI-Assistenten (ChatGPT, Perplexity, Claude, Copilot, Google AI Mode)

## Belegt

| Maßnahme | Warum | Konfidenz |
|---|---|---|
| Crawler in robots.txt zulassen: `OAI-SearchBot` (ChatGPT-Suche), `PerplexityBot`, `Claude-SearchBot`/`ClaudeBot`, `Googlebot`, `Bingbot` | Wer `OAI-SearchBot` sperrt, erscheint nicht in ChatGPT-Suchantworten. Training (`GPTBot`, `ClaudeBot`, `Google-Extended`) ist getrennt steuerbar — Training sperren und Suche erlauben ist möglich. Wirkung nach ca. 24 h. | wahrscheinlich (OpenAI-Bots-Doku) |
| CDN/Firewall prüfen | Cloudflare & Co. blocken KI-Bots teils per Voreinstellung, unabhängig von robots.txt. | wahrscheinlich |
| Inhalt ohne JavaScript lesbar | Viele KI-Crawler rendern kein JS. Kerninhalt und Preise im HTML. | wahrscheinlich |
| Klare, prüfbare Fakten | Leistungsgebiet, Preise/Preisrahmen, Öffnungszeiten, Qualifikationen, Kompatibilität — KI-Antworten zitieren konkrete Aussagen. | wahrscheinlich |
| Bing Webmaster Tools | Copilot und Teile von ChatGPT stützen sich auf den Bing-Index; Bing hat seit Feb. 2026 einen „AI Performance“-Bericht (CSV). | wahrscheinlich |

## Unbelegt oder Hype

- **llms.txt:** Google nutzt es nicht; Studien zeigen kaum Abrufe und keine Korrelation mit Zitaten. Höchstens anlegen, wenn es 5 Minuten kostet — kein Erfolgsversprechen.
- **„Präsenz auf Reddit/YouTube/Wikipedia hebt KI-Zitate“:** plausibel für die Auffindbarkeit beim Menschen, für KI-Rankings nicht belegt. Auf Reddit nur ehrlich als Entwickler auftreten (Selbstwerbungsregeln der Subreddits lesen), sonst Bann.
- **GEO-Studie (Princeton 2024):** Statistiken/Zitate/Quellen halfen in einer Simulation mit älteren Modellen; Effektgröße heute unsicher. Trotzdem gute Praxis, weil es auch Menschen überzeugt.
- **KI-Sichtbarkeits-Scores** von Tools: nicht verifizierbar.

## Ohne eigene Website

Ehrlich sagen: praktisch nicht steuerbar. KI-Suchen zitieren, was crawlbar existiert. Drittquellen (GitHub-README, Branchenverzeichnisse, Innungsseiten, Fachartikel) können erwähnen, ersetzen aber keine eigene Seite mit Preisen, Leistung und Kontakt.

## Test ohne Score

Typische Kundenfragen (3–5 Formulierungen) in ChatGPT-Suche, Perplexity und Google AI Mode stellen, Antworten und genannte Quellen protokollieren, nach 30 Tagen wiederholen. Ergebnisse schwanken — nur Tendenzen berichten, keinen Score.

## Beispiel robots.txt (Suche erlauben, Training optional sperren)

```
User-agent: *
Allow: /

User-agent: GPTBot
Disallow: /

User-agent: Google-Extended
Disallow: /

Sitemap: https://<domain>/sitemap.xml
```

`OAI-SearchBot`, `PerplexityBot` und `Claude-SearchBot` fallen unter `*` und sind damit erlaubt. Training-Sperre ist des Nutzers Entscheidung (Vorteil: Inhalte nicht im Training; Nachteil: Modelle kennen das Produkt weniger aus dem Gedächtnis).
