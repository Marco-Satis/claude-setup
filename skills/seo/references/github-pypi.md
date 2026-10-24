# GitHub- und PyPI-Sichtbarkeit

## Belegt (GitHub-/Python-Doku)

- **Beschreibung:** ein Satz mit dem Hauptbegriff, den Leute suchen (z. B. „self-hosted AI phone assistant for Claude Code“).
- **Topics:** bis 20, Kleinbuchstaben/Ziffern/Bindestriche, ≤ 50 Zeichen. 10–15 präzise wählen (Technik + Problem + Zielgruppe). Topic-Seiten sind eigene Einstiegspunkte.
- **Social Preview:** PNG/JPG < 1 MB, optimal 1280×640 (min. 640×320). Erscheint beim Teilen in Discord/X/LinkedIn.
- **Website-Feld** (`homepageUrl`) auf Landingpage/Doku setzen — verknüpft Repo und Domain.
- **PyPI:** `readme`/`long_description` mit korrektem Content-Type, `twine check dist/*` vor Upload; `project.urls` (Homepage, Documentation, Source, Issues) und Klassifikatoren (Lizenz, Python-Versionen, Topic) füllen.
- **Lizenzdatei** im Root (GitHub zeigt sie an, Unternehmen filtern danach).

## Praxis (unbelegt, aber günstig)

- README-Reihenfolge: Was (1 Satz) → Warum (Problem) → Demo (GIF/Screenshot) → Quickstart (≤ 5 Befehle) → Beispiele → Doku-Link → Lizenz.
- Getaggte Releases mit Changelog (Aktivitätssignal, Watch-Benachrichtigungen).
- 1–3 passende Awesome-Listen per PR — vorher deren Beitragsregeln lesen.
- GitHub Discussions oder Issue-Vorlagen für Rückmeldungen.
- Keine gekauften Stars (verstößt gegen GitHub-Regeln, wird erkannt).

## Prüfbefehle

```bash
gh repo view <owner/repo> --json description,repositoryTopics,homepageUrl,licenseInfo,latestRelease,stargazerCount
gh release list -R <owner/repo> --limit 5
python3 -m build && python3 -m twine check dist/*   # nur mit des Nutzers Ja installieren, falls build/twine fehlen
```

Repo-Einstellungen ändern (`gh repo edit --add-topic …`, `--description`, `--homepage`) nur mit des Nutzers Ja — öffentliches Repo, Personendaten-Regel des Projekts beachten (z. B. `personal-agent-oss`: Vorbild/Produkt/Marke nie nennen).
