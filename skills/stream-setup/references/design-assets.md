# Design: Marke, Overlays, Twitch-Grafiken

> Stand 16.11.2026. Kürzel wie in `obs-technik.md`. Verbindlich bleibt `~/.claude/rules/design-qualitaet.md`.

## Inhalt
1. Marke aus dem Gamertag
2. Twitch-Größen (Kanalseite, Emotes, Badges)
3. Overlay, Webcam-Rahmen, Alerts, Übergänge
4. Lesbarkeit: 720p und Handy
5. Prüfablauf (Tor)

## 1. Marke aus dem Gamertag

Voraussetzung: fester Name aus dem Skill `gamertag`. Ohne Namen nur Platzhalter, keine Logo-Arbeit.

1. **Kern in drei Wörtern** aus Brief und Name (z. B. Spielweise, Ton, Bild). Daraus Bildsprache ableiten.
2. **Vorbild:** zwei bis drei Kanäle/Seiten, die der Nutzer mag, mit `site-anatomy` zerlegen; Schriftpaarung, Farbrollen,
   Abstände, Bewegung übernehmen als Prinzip, nie Logos, Marken oder Assets.
3. **Farben als Rollen**, nicht als Liste: Grund (dunkel, nicht reines Schwarz), Fläche, Text, eine Akzentfarbe,
   ein Signal für Alerts. Altstand 09/2025: Türkis `#40E0D0`/`#82FEFF`, Dark/Neon, HUD mit Hexagonen
   (wz `persoenlich/streaming-und-profil-setup-marco-streamt-baf5`, über ein Jahr alt → bei der Nutzer bestätigen).
   Twitch hat eine eigene Akzentfarbe im Dashboard (Settings → Channel → Brand) [T5]; dieselbe Akzentfarbe nutzen.
   Kontrast Text/Grund ≥ 4,5:1 (WCAG 2.2), auch auf Spielbild-Hintergrund mit Unterlage.
4. **Schrift:** eine Display-Schrift für Name/Titel, eine gut lesbare Grotesk für Zahlen und Text; Lizenz muss
   Einbettung in Grafiken/Video erlauben (Google Fonts: OFL). Keine Reflex-Schriften laut Anti-KI-Checkliste.
5. **Logo:** Wortmarke + Kurzzeichen (Monogramm), das bei 28 px als Emote und 72 px als Badge funktioniert.
   Ergebnis: `assets/marke/` mit SVG + PNG und einer einseitigen Markenkarte (Farben, Schriften, Abstände, Do/Don't).

## 2. Twitch-Größen

| Asset | Vorgabe | Beleg |
|---|---|---|
| Profilbild | JPEG, PNG oder GIF, max. 10 MB; Pixelmaß in der Hilfe nicht genannt → quadratisch, 800×800 als Arbeitsgröße `[Praxis]` | Channel Page Setup [T5] `[gelesen]` |
| Profilbanner | empfohlen 1200×480 px; skaliert mit Fensterbreite, Höhe auf 480 px; Motiv links halten, Bild möglichst breit | [T5] `[gelesen]` |
| Video-Player-Banner (Offline) | im Dashboard → Brand; **animiert nicht unterstützt**; Pixelmaß nicht genannt. 1920×1080 stammt aus einem Twitch-Blog 2017 [T7] → Startwert, unverifiziert | [T5] `[gelesen]` |
| Info-Panels | Bild max. 320 px breit, 300 px hoch, < 2,9 MB, größer wird verkleinert | [T5] `[gelesen]` |
| Kanal-Trailer | MP4/MOV/AVI/FLV, H.264, AAC, bis 10 Mbps, bis 1080p60, ≤ 60 s, Musik nach DMCA-Regeln | [T5] `[gelesen]` |
| Emotes statisch | PNG, quadratisch, transparenter Hintergrund; Auto-Resize: ein Bild 112–4096 px; manuell: 28, 56, 112 px; max. 1 MB | Emote Requirements [T8] `[gelesen]` |
| Emotes animiert | GIF, quadratisch; Auto-Resize max. 1 MB, manuell je max. 512 KB; max. 60 Frames; **nicht mehr als 3 Blitze pro Sekunde** | [T8] `[gelesen]` |
| Abo-Abzeichen (Sub-Badges) | PNG, 18×18, 36×36, 72×72 px, je max. 25 KB, transparenter Hintergrund (auch Tier-2/3-Flair) | Subscriber Badge Guide [T9] `[gelesen]` |
| Bit-Abzeichen | 18/36/72 px PNG laut Suchergebnis | [T10] **nicht selbst gelesen** |
| Kanalpunkte-Symbol | Maße in keiner gelesenen Quelle | **offen** → beim Upload im Dashboard ablesen |

Emote-Regeln: Emotes gelten twitchweit, Insider-Witze können abgelehnt werden [T8]; Inhalte müssen die Emote
Guidelines im Safety Center erfüllen (Seite nicht gelesen, siehe `quellen.md`).

## 3. Overlay, Webcam-Rahmen, Alerts, Übergänge

- **Leinwand 1920×1080**, Sicherheitsrand 48 px; CoD-HUD frei lassen: Minimap oben links, Killfeed/Squad, Munition
  unten rechts, Plates/Armor unten Mitte (Lage je Titel im Spiel ablesen, des Nutzers HUD-Einstellungen gelten).
- **Live-Overlay minimal:** eine schmale Leiste oder Ecke, nichts über dem Fadenkreuz-Bereich. Kein Dauer-Ticker.
- **Webcam-Rahmen:** 16:9 oder 4:3 Ausschnitt, Rahmen als PNG mit Transparenz oder Maske; Position dort, wo das Spiel-HUD leer ist.
- **Alerts** (Follow, Sub, Bits, Raid): Browserquelle, HTML aus `design-html` oder Alert-Dienst mit eigener Gestaltung;
  Dauer 3–5 s, Ton leise und kurz, Bewegung ohne Überschwingen (Anti-KI A12), Reduced-Motion-Variante.
- **Übergänge:** Stinger (Video mit Alpha) oder Move Transition; Schnittpunkt mittig, Länge < 1 s `[Praxis]`.
- **Hintergründe für Starting/BRB/Ending/Just Chatting:** ruhiger Loop als Signaturmoment, Pause/Stopp möglich,
  keine Blitze; Loop nahtlos.
- **Dateien:** Overlays als lokale HTML-Dateien in `assets/overlay/` (Browserquelle → „Lokale Datei“), Bilder PNG/WebP,
  Videos WebM (VP9 mit Alpha) für Stinger `[Praxis]`.

## 4. Lesbarkeit: 720p und Handy

Viele Zuschauer sehen eine Transcode-Stufe (EB kann bis 480p/360p ausliefern [T2]) oder das kleine Handybild.

Prüfung je Overlay/Grafik (netcup):
```
# Render: Overlay-HTML bei 1920x1080 per visual_sheet.mjs oder Playwright-Screenshot, dann herunterrechnen
ffmpeg -i overlay_1080.png -vf scale=1280:720:flags=lanczos overlay_720.png
ffmpeg -i overlay_1080.png -vf scale=640:360:flags=lanczos overlay_360.png
```
Bilder mit Read ansehen. Bestanden, wenn bei 640×360 Name, Status-Text und Zahlen ohne Raten lesbar sind und bei
1280×720 nichts verschwimmt. Emotes zusätzlich als 28-px-Fassung auf hellem und dunklem Chat-Grund ansehen;
Badges als 18 px.

## 5. Prüfablauf (Tor)

Nach `~/.claude/rules/design-qualitaet.md` (Stufe V für Gesamtpaket, Stufe L für einzelne Animation):
1. `node ~/.claude/scripts/visual_sheet.mjs <overlay.html> --pruefen --outdir <scratchpad>/pruefung_<name>` (Bash-Timeout 200000).
2. Anti-KI-Checkliste `~/.claude/templates/anti_ki_checkliste.md`, Bewegung `~/.claude/scripts/visual_sheet_checkliste.md` (M1–M12).
3. Zweitblick nach `~/.claude/templates/design_zweitblick.md` (Stufe V: Claude und Codex).
4. Lesbarkeit aus Abschnitt 4.
5. Höchstens 3 Runden, Restbefund in den Übergabesatz.
