# Datenseiten und viele ähnliche Seiten (programmatic SEO)

Gilt z. B. für Waffen-/Loadout-Seiten, Preset-Seiten (FootstepPro je Spiel/Kopfhörer) oder Branchenseiten („KI-Telefon für Zimmerei/Dachdecker/…“).

## Gate vor dem Bau (Pflicht)

Für jeden Seitentyp drei Fragen beantworten. Ein Nein → Seite nicht bauen, zusammenlegen oder `noindex`:

1. Hat jede einzelne Seite **eigene Information**, die es so woanders nicht gibt (Messwerte, Patch-Historie, Vergleich, eigene Erfahrung, echte Fotos)?
2. Würde ein Mensch die Seite **ohne Suchmaschine** nützlich finden?
3. Unterscheiden sich die Seiten in mehr als dem ausgetauschten Keyword?

Grund: Googles Spam-Policy „Scaled Content Abuse“ trifft viele Seiten zur Ranking-Manipulation unabhängig davon, ob Mensch, Skript oder KI sie erstellt hat. Ein Treffer kann die ganze Domain herabstufen.

## Branchenseiten (Voice-Agent je Gewerk)

Nur bauen, wenn je Gewerk echte Unterschiede belegt sind: typische Anrufgründe, Terminarten, Notdienst-Logik, ein echtes Pilot-Beispiel. Sonst eine starke Seite „für Handwerksbetriebe“ mit Abschnitten je Gewerk.

## Dataset-Markup (für offene Datensätze)

Pflicht: `name`, `description` (50–5.000 Zeichen). Empfohlen: `license` (versionierte URL, z. B. `https://creativecommons.org/licenses/by/4.0/`), `creator`, `distribution` mit `contentUrl` + `encodingFormat`, `temporalCoverage`, `dateModified`. Seite crawlbar (kein Login, kein noindex). Ziel: Google Dataset Search.

```json
{
  "@context": "https://schema.org",
  "@type": "Dataset",
  "name": "<Name>",
  "description": "<50–5000 Zeichen: was, woher, wie aktuell>",
  "license": "https://creativecommons.org/licenses/by/4.0/",
  "creator": {"@type": "Person", "name": "<Autor>"},
  "dateModified": "<YYYY-MM-DD>",
  "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": "<URL>"}]
}
```

## Wenn die Daten schon offen auf GitHub liegen

Kopien durch Dritte sind möglich. Vorsprung entsteht durch Aktualität (Patch-Tag), Methode/Quelle offenlegen, eigene Auswertungen und klare Attribution (CC-BY verlangt Namensnennung — Kopierer ohne Nennung verletzen die Lizenz).
