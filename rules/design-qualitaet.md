# Sichtbare Ergebnisse: Profi-Niveau als Mindestmaß (Global Rule)

> der Nutzer 2026-11-13, bestätigt (wz `setup/mindestmass-sichtbarer-ergebnisse-erfahrene-4bef`): Erfahrene Designer und
> Entwickler dürfen auf den ersten Blick nicht erkennen, dass KI beteiligt war. Das ist das Mindestmaß.

## Kernregel

1. **Nichts Sichtbares ungesehen übergeben.** Oberflächen, Seiten, Dashboards, Grafiken und Animationen werden vor
   der Übergabe gerendert und mit dem Read-Tool angesehen: Handy- und Desktopbreite (390/1280 px), bei Animationen
   mehrere Zeitpunkte, nie `--virtual-time-budget`. Echtzeit für Ruckeln, Schrittbilder für die Kurve.
   Auf netcup: `node ~/.claude/scripts/visual_sheet.mjs <seite> --pruefen --outdir <scratchpad>/pruefung_<name>`
   (Bash-Timeout 200000; mit `--outdir` überlebt das Protokoll samt Bildbelegen bis zum Stempel), Bewegung bewerten
   nach `visual_sheet_checkliste.md`; am PC entfällt der Aufruf (Claude in Chrome). Office-Dateien: [docx-visual-check](docx-visual-check.md).
2. **Gegen KI-Merkmale prüfen**, nicht nur „sieht ordentlich aus“. Quelle ist die Anti-KI-Checkliste
   `~/.claude/templates/anti_ki_checkliste.md` (impeccable + frontend-design; ein harter oder drei weiche Befunde =
   durchgefallen). `design-taste-frontend` ist nachrangig, Barrierefreiheit (WCAG 2.2) geht vor.
   **Tor:** Befund → verbessern, neu rendern, erneut ansehen, höchstens 3 Runden; ein Restbefund danach steht im
   Übergabesatz. Das Tor gilt ausdrücklich auch für Artifacts und geht dem „check once“ und den Standardschriften
   (Inter, Space Grotesk) aus `artifact-design` vor.
   **Stufen** (G247 Plan 5.4, Pflichtteile im Gerüst `pruefung.md`): K Text-, Farb-, Abstandsfix (A1–A15);
   L Komponente, Animation (dazu M1–M12 und Zweitblick Claude); V ganze Seite, Dashboard, neues Artifact (dazu
   Vorbild, Zwei-Durchgänge-Plan, Zweitblick Claude und Codex). Zweitblick nach `~/.claude/templates/design_zweitblick.md`.
3. **Von echten Vorbildern ausgehen**, wenn Qualität zählt: fremde Seiten mit `site-anatomy` zerlegen, Technik mit
   `leanrea`, dann im eigenen Design umsetzen (keine Marken- oder Logoübernahme). Bei Stufe V ist ein Vorbild
   Standard; ohne Vorbild nur auf des Nutzers ausdrückliches „ohne Vorbild“.
4. **Bewegung:** Kein Überschwingen oder Federn (Anti-KI A12, hart). Dauerbewegung nur als ein benannter
   Signaturmoment, über 5 s mit Pause- oder Stopp-Möglichkeit (WCAG 2.2.2) und immer mit Reduced-Motion-Variante;
   dafür gehen WCAG und `impeccable` vor `design-taste-frontend` (MB84; Fassung von der Nutzer am 14.11. bestätigt, MB133).
5. Erst danach der Nutzer zeigen, mit einem Satz, was geprüft wurde.

Ausbau: Kontaktbogen für Animationen ist umgesetzt (G246, Punkt 1; Checkliste `~/.claude/scripts/visual_sheet_checkliste.md`,
Bericht `PLAENE/G246_BAUBERICHT_2026-11-13.md`). Anti-KI-Checkliste, `--pruefen` und Zweitblick kommen aus G247 Phase 1,
der Sperr-Hook `design_tor.py` aus Phase 2 (`~/projects/Skills_&_Co/PLAENE/PLAN_G247_DESIGN_QUALITAET_2026-11-13.md`).
