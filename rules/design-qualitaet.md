# Sichtbare Ergebnisse: Profi-Niveau als Mindestmaß (Global Rule)

> der Nutzer 2026-11-13, bestätigt (wz `setup/mindestmass-sichtbarer-ergebnisse-erfahrene-4bef`): Erfahrene Designer und
> Entwickler dürfen auf den ersten Blick nicht erkennen, dass KI beteiligt war. Das ist das Mindestmaß.

## Kernregel

1. **Nichts Sichtbares ungesehen übergeben.** Oberflächen, Seiten, Dashboards, Grafiken und Animationen werden vor
   der Übergabe gerendert und mit dem Read-Tool angesehen: Desktop- und Handybreite, bei Animationen mehrere Zeitpunkte
   (Bildserie in Echtzeit, nicht `--virtual-time-budget`). Office-Dateien: [docx-visual-check](docx-visual-check.md).
   Animationen auf netcup: `node ~/.claude/scripts/visual_sheet.mjs <seite> [--selector …] [--state …]`, bewerten nach `visual_sheet_checkliste.md`; am PC entfällt der Aufruf (Claude in Chrome).
2. **Gegen KI-Merkmale prüfen**, nicht nur „sieht ordentlich aus“: generische Farbverläufe (v. a. Violett/Cyan),
   Glas-Effekte und Glows ohne Funktion, Standard-Schriften, Drei-Karten-Reihen, Platzhaltertexte, generisches Fade-up,
   Endlos-Animationen ohne Zweck. Die Verbote aus `design-taste-frontend` gelten auch außerhalb von React; seine
   Stil-Empfehlungen (Glas, Dauerbewegung) nicht ungeprüft übernehmen, Barrierefreiheit (WCAG 2.2) geht vor
   (Abgleich läuft in G247, Stand MASSSTAEBE/web-frontend.md). Fällt ein Merkmal auf: verbessern, erneut ansehen.
3. **Von echten Vorbildern ausgehen**, wenn Qualität zählt: fremde Seiten mit `site-anatomy` zerlegen, Technik mit
   `leanrea`, dann im eigenen Design umsetzen (keine Marken- oder Logoübernahme).
4. **Bewegung:** Status- und Daueranimationen folgen WCAG 2.2.2 (über 5 s → Pause/Stopp-Möglichkeit) und
   `prefers-reduced-motion`; dafür gehen WCAG und `impeccable` vor `design-taste-frontend` (entschieden 13.11., MB84).
   Endlos-Schleifen und Overshoot nur als Deko und immer mit Reduced-Motion-Variante.
5. Erst danach der Nutzer zeigen, mit einem Satz, was geprüft wurde.

Ausbau (Kontaktbogen für Animationen, feste Checkliste, Zweitmeinung) folgt aus den Plänen G246/G247 in
`~/projects/Skills_&_Co/PLAENE/`.
