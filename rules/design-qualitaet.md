# Sichtbare Ergebnisse: Profi-Niveau als Mindestmaß (Global Rule)

> der Nutzer 2026-11-13, bestätigt (wz `setup/mindestmass-sichtbarer-ergebnisse-erfahrene-4bef`): Erfahrene Designer und
> Entwickler dürfen auf den ersten Blick nicht erkennen, dass KI beteiligt war. Das ist das Mindestmaß.

## Kernregel

1. **Nichts Sichtbares ungesehen übergeben.** Oberflächen, Seiten, Dashboards, Grafiken und Animationen werden vor
   der Übergabe gerendert und mit dem Read-Tool angesehen: Handy- und Desktopbreite (390/1280 px), bei Animationen
   mehrere Zeitpunkte, nie `--virtual-time-budget`. Echtzeit für Ruckeln, Schrittbilder für die Kurve.
   Auf netcup: `node ~/.claude/scripts/visual_sheet.mjs <seite> --pruefen`, Bewegung bewerten nach
   `visual_sheet_checkliste.md`; am PC entfällt der Aufruf (Claude in Chrome). Office-Dateien: [docx-visual-check](docx-visual-check.md).
2. **Gegen KI-Merkmale prüfen**, nicht nur „sieht ordentlich aus“. Quelle ist die Anti-KI-Checkliste
   `~/.claude/templates/anti_ki_checkliste.md` (impeccable + frontend-design; ein harter oder drei weiche Befunde =
   durchgefallen). `design-taste-frontend` ist nachrangig, Barrierefreiheit (WCAG 2.2) geht vor.
   **Tor:** Befund → verbessern, neu rendern, erneut ansehen, höchstens 3 Runden; ein Restbefund danach steht im
   Übergabesatz. Das Tor gilt ausdrücklich auch für Artifacts und geht dem „check once“ und den Standardschriften
   (Inter, Space Grotesk) aus `artifact-design` vor.
3. **Von echten Vorbildern ausgehen**, wenn Qualität zählt: fremde Seiten mit `site-anatomy` zerlegen, Technik mit
   `leanrea`, dann im eigenen Design umsetzen (keine Marken- oder Logoübernahme). Bei Stufe V (ganze Seite, Dashboard,
   neues Artifact) ist ein Vorbild Standard, ohne nur auf des Nutzers ausdrückliches „ohne Vorbild“.
4. **Bewegung:** Status- und Daueranimationen folgen WCAG 2.2.2 (über 5 s → Pause/Stopp-Möglichkeit) und
   `prefers-reduced-motion`; dafür gehen WCAG und `impeccable` vor `design-taste-frontend` (entschieden 13.11., MB84).
   Endlos-Schleifen und Overshoot nur als Deko und immer mit Reduced-Motion-Variante.
5. Erst danach der Nutzer zeigen, mit einem Satz, was geprüft wurde.

Ausbau: Kontaktbogen für Animationen ist umgesetzt (G246, Punkt 1; Checkliste `~/.claude/scripts/visual_sheet_checkliste.md`,
Bericht `PLAENE/G246_BAUBERICHT_2026-11-13.md`). Anti-KI-Checkliste, `--pruefen` und Zweitblick kommen aus G247 Phase 1,
der Sperr-Hook `design_tor.py` aus Phase 2 (`~/projects/Skills_&_Co/PLAENE/PLAN_G247_DESIGN_QUALITAET_2026-11-13.md`).
