# OBS-Technik: Encoder, Bitrate, Szenen, Plugins

> Stand 16.11.2026. Jede Zahl mit Quelle; Kürzel `[gelesen]` = Primärquelle am 16.11. selbst gelesen,
> `[Zusammenfassung]` = nur über eine Zusammenfassung gelesen, `[Praxis]` = Erfahrungswert ohne Primärquelle.
> Quellen-URLs stehen in `quellen.md` unter der Nummer in eckigen Klammern.

## Inhalt
1. Plattform-Grenzen Twitch
2. Encoder-Wahl für des Nutzers GPU
3. Startprofile
4. Szenen-Grundgerüst und Quellen
5. Plugins
6. Typische Fehlerbilder

## 1. Plattform-Grenzen Twitch

| Punkt | Wert | Beleg |
|---|---|---|
| Klassisch (ohne Enhanced Broadcasting), NVENC | 1080p60: 6000 kbps CBR, Keyframe 2 s, B-Frames 2 · 1080p30 und 720p60: 4500 kbps · 720p30: 3000 kbps | Broadcasting Guidelines [T1] `[gelesen]` |
| Ratenkontrolle | CBR, VBR ausdrücklich nicht empfohlen | [T1] `[gelesen]` |
| Audio | AAC-LC, Stereo oder Mono, empfohlen 96 kbps, max. 160 kbps | [T1] `[gelesen]` |
| Max. Sendedauer | 48 h | [T1] `[gelesen]` |
| Enhanced Broadcasting (EB) | ab OBS 30.2; Einstellungen → Stream → Dienst Twitch, „Connect Account“, Abschnitt Multitrack Video → „Enable Enhanced Broadcasting“; Bandbreite/Spuren auf Auto lassen (Werte sind Obergrenzen, kein Ziel) | Enhanced Broadcasting [T2] `[gelesen]` |
| EB automatisch | Gesamtbandbreite 1,5–10,5 Mbps, oberste Spur bis 1080p60, 2–5 Renditions, Encoder-Einstellungen (Preset, Look-ahead, AQ, B-Frames) setzt Twitch je Start neu | [T2] FAQ `[gelesen]` |
| EB Empfehlung Leinwand | Basis- und Ausgabeauflösung beide 1920×1080 oder 1280×720 bei 60 fps; Leinwand darf größer sein (lokale Aufnahme), Stream nie größer als die skalierte Auflösung | [T2] `[gelesen]` |
| 2K (1440p) | nur Affiliate und Partner, nur über EB, HEVC; bis 9 Mbps (1440p) bzw. 7,5 Mbps (1080p); Freischaltung im Creator Dashboard → Stream → Einstellungen prüfen | [T2] `[gelesen]`, Blog 17.06.2026 [T3] `[gelesen]` |
| Dual Format (horizontal + vertikal) | für alle Streamer, braucht EB | [T2], [T3] `[gelesen]` |
| AV1 auf Twitch | **nicht belegt.** Blog 2024 nannte AV1 als Ziel, 2026 nennt nur AVC und HEVC | [T3], [T4] `[gelesen]` |
| EB Audio | nur Stereo/Mono | OBS 30.2 Notes [O5] `[Zusammenfassung]` |
| EB und OBS-Stream-Delay | Verträglichkeit **nicht belegt** → vor dem ersten echten Stream testen | — |
| Transcodes | Partner garantiert, sonst nach Kapazität | Partner-Seite [T6] `[gelesen]` |

Kontrolle während des Streams: Twitch Inspector (`inspector.twitch.tv`), von Twitch selbst empfohlen [T2].

## 2. Encoder-Wahl für des Nutzers GPU

RTX 4070 Ti (Ada) kann in OBS „NVIDIA NVENC H.264“, „HEVC“ und „AV1“ [O2]. Entscheidungsregel:

| Ziel | Encoder | Grund |
|---|---|---|
| Twitch klassisch | NVENC H.264 | Twitch-Klassik nimmt AVC [T1] |
| Twitch mit EB | Encoder setzt Twitch; Dropdown irrelevant | [T2] |
| Twitch 2K | EB + HEVC, nur Affiliate/Partner | [T2], [T3] |
| YouTube | AV1 oder HEVC | NVIDIA-Guide [O3] `[Zusammenfassung]` |
| Lokale Aufnahme (VOD-Schnitt, Clips) | HEVC oder AV1, eigener Encoder unabhängig vom Stream | [O2] |
| x264 (CPU) | **nicht** beim i5-13600K im Shooter; kostet Spiel-FPS | [T1] `[gelesen]`: x264 belastet die CPU stark |

Werbeaussage geprüft: NVIDIA schreibt AV1 sei „~43 % effizienter“ als H.264 bzw. wirke „als hätte man >40 % mehr
Bitrate“ [O3]. Das ist ein Qualitätsäquivalent ohne Messmethode, kein „40 % weniger Bitrate“ (rechnerisch ≈ 30 %
weniger bei gleicher Qualität). Für Twitch ohnehin nicht nutzbar (s. o.).

Bekannte Falle bei der Nutzer: `discord_clips.exe` belegte NVENC und kostete in BO7 bis 40 fps (wz
`pc-system/framedrops-bis-fps-in-cod-bo7-kamen-von-discord-7372`). Vor dem Stream Discord-Clips und andere
Hintergrund-Aufnahmen (NVIDIA App Instant Replay, Xbox Game Bar) aus. Die 4070 Ti hat laut OBS-KB zwei NVENC-Einheiten
(Split Encode „4070 Ti oder höher“) [O4] `[gelesen über Agent]`; zwei parallele Encodes (Stream + Aufnahme) sind damit
tragbar, Fremd-Encoder aber trotzdem aus.

## 3. Startprofile

OBS-Bezeichnungen Stand OBS 33: „Psycho Visual Tuning“ heißt seit 31 **„Adaptive Quantization“** [O1]. Tuning
„Ultra High Quality“ ist laut OBS für Gaming nicht empfohlen [O4].

**Entscheidungsregel (Reihenfolge, erste zutreffende Zeile gilt):**

| Bedingung | Profil |
|---|---|
| Brief verlangt Stream-Delay **oder** VOD-Spur, und der Testlauf zeigt, dass EB damit nicht sauber läuft (Delay greift nicht, VOD hat Musik) | **A** |
| Plattform Twitch, OBS ≥ 30.2, Twitch-Konto in OBS verbunden | **B** (Standard). EB ist laut Twitch-Hilfe „available to all streamers on Twitch“, also **auch ohne Affiliate** [T2] `[gelesen]` |
| Testaufnahme mit A zeigt Blockartefakte in schnellen Szenen bei 6000 kbps | **C** statt A |
| Multistream, anderer Dienst oder Konto nicht verbunden | **A** (bzw. Dienst-Grenzen nachschlagen) |

Rückfall: Läuft B im Testlauf schlechter (Inspector meldet Probleme, OBS meldet Encoding-Überlast, Delay/VOD-Spur
versagen), sofort auf A zurück: Häkchen „Enable Enhanced Broadcasting“ raus, Profil A eintragen, erneut testen.

**A — Twitch klassisch (eigene NVENC-Einstellungen):**
Einstellungen → Ausgabe → Modus Erweitert → Streaming:
`Encoder NVIDIA NVENC H.264 · Ratenkontrolle CBR · Bitrate 6000 kbps · Keyframe-Intervall 2 s · Preset P5 ·
Tuning High Quality · Multipass Two Passes (Quarter Resolution) · Profil high · Look-ahead an ·
Adaptive Quantization an · B-Frames 2`. Video: Basis 2560×1440 (Hauptmonitor), Ausgabe 1920×1080, Filter Lanczos,
60 fps. Audio **128 kbps** AAC: Twitch empfiehlt 96 kbps „for maximum compatibility“, erlaubt bis 160 [T1]; 128 ist
der Kompromiss für Spielton mit vielen Höhen (Schritte, Schüsse) `[Praxis]`. Klingt der Testlauf auf schwachen
Geräten schlecht, auf 96 gehen.

**Preset-Kriterium P5 → P6 (messbar):** Nach 15 min echtem Spiel mit Stream bzw. Testaufnahme:
OBS → Ansicht → Statistiken „Übersprungene Frames aufgrund von Encoding-Verzögerung“ = 0 **und** keine Meldung
„Encoding überlastet“ **und** GPU-Auslastung „Video Encode“ im Task-Manager (Leistung → GPU) unter 60 % `[Praxis]`
→ P6 testen, gleiche Messung wiederholen. Eine Bedingung verfehlt → zurück auf P5 (bei Überlast weiter P4).
Quellen: Twitch-Werte [T1]; OBS-Standards P5/hq/qres/B-Frames 2/AQ/Look-ahead [O6] `[gelesen über Agent]`;
NVIDIA rät P6 und B-Frames 4 mit Look-ahead [O3] `[Zusammenfassung]` — Abweichung bewusst: erst P5, dann hoch,
wenn die GPU beim Spielen Luft hat.

**B — Twitch mit Enhanced Broadcasting:** Basis und Ausgabe 1920×1080, 60 fps, EB an, Auto. Encoder-Felder nicht
weiter tunen, Twitch überschreibt sie [T2]. Twitch gibt für EB 1,5–10,5 Mbps Gesamtbandbreite an [T2]; Upload muss
das mit Reserve tragen.

**2K (1440p) — nur Affiliate/Partner, für der Nutzer derzeit nicht relevant** (Status laut Brief klären; ohne Affiliate
gibt Twitch kein 2K [T2]). Falls später: EB, Basis 2560×1440, Freischaltung im Dashboard prüfen, Upload ≥ 20 Mbit/s
einplanen (Beta-Wert aus zweiter Hand, OBS-Forum [O9], **unverifiziert**).

**C — Bewegungsreicher Shooter mit knappem Upload:** 1664×936 bei 60 fps auf 6000 kbps ist verbreitete Praxis gegen
Blockartefakte `[Praxis]`. Erst mit Testaufnahme A gegen C vergleichen, nicht pauschal setzen.

**Upload vorher messen:** wz-Wert 55 Mbit/s stammt aus ChatGPT, ungeprüft. der Nutzer misst am PC (Speedtest per LAN,
mehrfach, abends). Faustregel: Stream-Bitrate ≤ 50–70 % des stabilen Uploads `[Praxis]`.

**Leistung prüfen:** OBS → Ansicht → Statistiken: „Übersprungene Frames (Encoding-Verzögerung)“ und „Verworfene
Frames (Netzwerk)“ müssen bei 0 bis < 0,1 % bleiben `[Praxis]`. Spiel-FPS-Cap (der Nutzer: 141 bzw. passend zum Monitor)
lässt der GPU Luft für OBS-Komposition.

## 4. Szenen-Grundgerüst und Quellen

Szenensammlung „Stream <Name>“, Szenen über verschachtelte Szenen (eine Quelle einmal pflegen, überall nutzen):

| Szene | Inhalt | Ton |
|---|---|---|
| `Starting` | Hintergrund (Loop), Countdown/Titel, Musik (lizenzfrei), Social-Leiste | Musik, Mic stumm |
| `Live – Game` | Spiel-Capture, Webcam im Rahmen, Alerts, dezente Info-Leiste | Spiel, Mic, Alerts |
| `Live – Game ohne Cam` | wie oben ohne Webcam | wie oben |
| `Just Chatting` | Webcam groß, Chat-Overlay, Hintergrund | Mic, leise Musik |
| `BRB` | Hintergrund, Hinweis, Musik; **Spiel-Capture weg** (Lobby, Menüs, Privates) | Musik, Mic stumm |
| `Ending` | Danke, Raid-Hinweis, nächster Termin | Musik |
| `Privat / Notfall` | nur Grafik „gleich zurück“ | alles stumm außer Musik |

Verschachtelte Bausteine: `[S] Webcam`, `[S] Alerts`, `[S] Overlay Live`, `[S] Audio Basis` (Mic + Spiel).

Quellen:
- **Spiel:** Spielaufnahme (Game Capture) auf das CoD-Fenster; wenn schwarz: Fensteraufnahme, letzte Wahl
  Bildschirmaufnahme (zeigt sonst Benachrichtigungen und zweiten Monitor-Inhalt nicht, aber alles auf Monitor 1).
- **Webcam:** Videoaufnahmegerät; Filter Farbkorrektur, ggf. „Bild-Maske/Überblenden“ für den Rahmen aus `design-assets.md`.
- **Overlays, Alerts, Chat:** Browserquelle mit lokaler HTML-Datei oder URL des Alert-Dienstes; Größe = Leinwand
  (1920×1080), „Audio über OBS steuern“ an, damit Alert-Ton im Mixer landet.
- **Audio:** siehe `audio-kette.md`.

## 5. Plugins

Nur von GitHub-Releases des Autors oder der obsproject.com-Ressourcenseite; bei OBS 33 die Windows-Variante für die
neue Ordnerstruktur wählen (OBS 33 lädt alte Pfade noch bis OBS 34) [O1]. Plugins laufen mit vollen Rechten des
OBS-Prozesses.

| Plugin | Zweck | Stand 16.11.2026 | Empfehlung |
|---|---|---|---|
| Move Transition (Exeldro) | Übergänge, Quellen animiert verschieben | 3.2.2 vom 14.11.2026, aktiv [O7] | ja |
| Source Record (Exeldro) | einzelne Szenen/Quellen getrennt aufnehmen | 0.5.0 vom 07.11.2026 [O7] | optional |
| obs-shaderfilter (Exeldro) | Shader-Effekte (Rahmen, Glow) | 2.6.1 vom 24.10.2026 [O7] | sparsam |
| Advanced Scene Switcher (WarmUpTill/SceneSwitcher) | Automatik (z. B. BRB, wenn Spiel minimiert) | 1.37.2 vom 01.11.2026, min. OBS 31.1.1 [O7] | optional |
| Aitum Vertical | zweite, vertikale Leinwand | 1.6.7 vom 27.10.2026 [O7] | nur ohne EB-Dual-Format; Dual Format von Twitch braucht EB [T2] |
| obs-websocket | Fernsteuerung (Stream Deck, Touch Portal, Streamer.bot) | seit OBS 28 eingebaut, Port 4455 [O8] | Passwort setzen |
| **StreamFX** | — | letzter Release 0.12.0b299 (Mai 2023), README 2024: „no plans to further update“ [O7] | **nicht verwenden** |

Eingebaut statt Plugin: Noise Suppression, Kompressor, Limiter (Audio), Stinger-Übergang, Farbkorrektur, Maske.

## 6. Typische Fehlerbilder

| Symptom | Erste Prüfung |
|---|---|
| Stream verpixelt bei Bewegung | Bitrate am Limit → Profil C oder 720p60 testen; Preset höher |
| „Encoding überlastet“ / übersprungene Frames | Fremd-Encoder (Discord Clips, Instant Replay) aus, Preset senken, Spiel-FPS-Cap |
| Verworfene Frames (Netzwerk) | Upload messen, Bitrate senken, LAN statt WLAN, Ingest-Server Auto |
| Game Capture schwarz | OBS als Administrator, Fensteraufnahme probieren; Anti-Cheat-Verhalten von CoD **nicht belegt**, nur testen |
| EB-Stream schlechter als erwartet | Twitch Inspector prüfen; EB wählt Konfiguration je Start neu [T2] |
