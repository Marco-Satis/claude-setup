# Vision-Raster (Phase 3)

Material: `<WD>/kopien/tiles/` (Seitenkacheln, Name `<seite>_<breite>_<schema>_tNN.png`) und
`<WD>/kopien/sheets/` (Kontaktbögen der Inhaltsbilder, `sheet_NN.png`). Beides entsteht erst mit
`tile.sh` nach `measure.mjs`. Messwerte: `ergebnis/images.json` (Paletten), `kopien/capture.json`
(Inventar, Seitenverhältnisse, Icons).

Reihenfolge: erst Hell/Dunkel vergleichen (unten), dann alle Kontaktbögen, dann je Breite die
Kacheln der Startseite (hell, dann eine Stichprobe dunkel — entfällt bei byte-identischen
Dunkel-Kacheln), dann Stichproben der Unterseiten. Jedes angesehene Bild landet im
Session-Transcript — nur so viele Kacheln ansehen, wie das Raster braucht.

Jede Aussage `[V]` mit Dateinamen; wo ein Messwert existiert, daneben stellen und Widersprüche nennen.
Liegt neben einem Bogen `sheet_NN.txt`, steht dort die Reihenfolge der Bilder; nur dann ein
Vorschaubild einem Eintrag in `images.json` zuordnen. Ohne diese Datei den Bogen nur gesamt bewerten.

## Vorab 1: Hell/Dunkel vergleichen (ohne Ansehen)

Kacheln per `md5sum` vergleichen, bevor eine einzige angesehen wird:

```bash
T="<WD>/kopien/tiles"; for f in "$T"/*_light_t*.png; do d="${f/_light_t/_dark_t}"; [ -f "$d" ] || continue; [ "$(md5sum <"$f")" = "$(md5sum <"$d")" ] && echo "gleich ${f##*/}" || echo "anders ${f##*/}"; done
```

- Alle `gleich`: Die Dunkel-Stichprobe entfällt. Teil 5 und Teil 22 sagen „kein Dark Mode erkennbar
  (Screenshots identisch)".
- Teilweise `gleich`: nur die `anders`-Paare dunkel ansehen.
- Alle `anders`: Dunkel-Stichprobe wie unten.

## Vorab 2: Banner-Prüfung

Steht in `capture.json` ein `consent.state` (bzw. `consentDark.state`) auf `no_reject_button_found`
oder `reject_failed`: in den Kacheln nachsehen, ob ein Banner Inhalte überdeckt. Betroffene Kacheln
nennen (für Teil 1 und 22) und diese Flächen nicht bewerten. Bei `rejected` und `no_banner` entfällt
die Prüfung.

## Bildsprache (je Kontaktbogen, dann gesamt)

| Kriterium | Ausprägungen (eine wählen, Beispiel nennen) | Gegenprobe [M] |
|---|---|---|
| Licht | natürlich weich · hart/kontrastreich · Studio · gemischt | — |
| Farbtemperatur | warm · neutral · kühl | `palette` in `images.json` |
| Sättigung | gedämpft · natürlich · kräftig · markenfarben eingefärbt | `palette` |
| Motivklasse | Menschen im Alltag · Produkt freigestellt · Produkt im Einsatz · Architektur/Raum · abstrakt/Grafik | — |
| Menschen | Anteil Bilder mit Menschen (geschätzt %) · gestellt vs. authentisch · Blick in Kamera ja/nein · Diversität | — |
| Ausschnitt | eng (Detail/Gesicht) · mittel · weit · Negativraum für Text links/rechts | `objectPosition`, `natural`/`shown` in `capture.json` |
| Behandlung | unbearbeitet · Overlay/Verlauf · Duotone · Maske/Form · Schatten/Rahmen | `kind: css-background` in `capture.json` |
| Konsistenz | einheitlich · zwei Stile · uneinheitlich | Streuung der Paletten |

## Illustration und Icons

- Illustration: vorhanden ja/nein · Stil (flach, isometrisch, 3D, Linie, handgezeichnet) · Farben aus
  Markenpalette ja/nein.
- Icons: Linie vs. Fläche (`stroke`/`fill` der Einträge `kind: icon-svg` in `capture.json`),
  Strichstärke einheitlich, Ecken rund/eckig, Größe (px aus `shown`).

## Gesamtwirkung je Breite

- Erster Bildschirm: Was sieht man zuerst, was als Zweites, wo ist der wichtigste Knopf?
- Squint-Test (Kachel unscharf denken): Welche 3 Flächen dominieren?
- Dichte: luftig · ausgewogen · dicht.
- Umbau Handy → Desktop: Was verschwindet, was ändert die Reihenfolge, wechselt der Bildausschnitt?
- Dunkel-Schema: Gibt es einen echten Dark Mode oder bleibt die Seite hell? Sind die Kacheln laut
  „Vorab 1" identisch, steht die Antwort ohne Ansehen fest. (Farbwerte nur, wenn `design.json`
  `darkMode` enthält; sonst nur diese Sichtprüfung.)

## Ausgabe

Pro Kriterium ein Satz mit Beispiel (Dateiname der Kachel/des Bogens). Am Ende 3–5 Sätze
„Bildsprache in einem Absatz“ — das wird später zum eigenen Bild-Briefing umformuliert, ohne
Motive der Vorlage zu kopieren.
