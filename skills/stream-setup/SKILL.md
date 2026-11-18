---
name: stream-setup
version: 1.0.1
last-reviewed: 2026-11-16
description: Use when der Nutzer wants to (re)start live streaming or improve his stream — setting up or fixing OBS Studio (encoder, bitrate, scenes, audio tracks, mic filters, plugins), designing a channel look (overlays, webcam frame, alerts, panels, offline banner, emotes, badges, backgrounds, transitions) or preparing stream operations (pre-stream checklist, hotkeys/Stream Deck, moderation, music rights, privacy, stream delay). Not for inventing or checking a gamertag or channel name (gamertag, namensfindung), growing reach or SEO for a website (seo), building a generic web page unrelated to the stream (design-html), or tuning his own headphone/footstep EQ (Audio_Setup project).
when_to_use: stream-setup, streamen, stream einrichten, wieder streamen, live gehen, obs, obs studio, obs einstellungen, obs szenen, encoder, nvenc, av1, bitrate, twitch einstellungen, enhanced broadcasting, stream ruckelt, stream verpixelt, dropped frames, stream audio, spielsound im stream, mikrofon filter, noise suppression, vod spur, twitch vod track, overlay, stream overlay, webcam rahmen, alerts, twitch panels, offline banner, emotes, sub badges, stream design, kanal design, szenenübergang, stinger, stream deck, chat moderation, automod, dmca, musik im stream, stream delay, stream sniping, streamer setup, go live checklist, kick, youtube live
argument-hint: Optional Bereich — technik | audio | design | betrieb | pruefung (ohne Argument voller Ablauf ab Brief)
allowed-tools: Read Grep Glob Bash Write Edit WebFetch WebSearch
user-invocable: true
---

# stream-setup — OBS, Kanal-Design und Stream-Betrieb für der Nutzer

Zweck: des Nutzers Stream (Windows-PC, Call of Duty Warzone/Black Ops, Twitch als Standard) technisch sauber einrichten,
ein eigenständiges Kanal-Design bauen und den Betrieb absichern. Ablauf immer **Brief → Plan → Umsetzung in
Teilschritten → Prüfung mit Testaufnahme**. Fachwerte stehen in `references/`, nicht im Kopf des Modells.

## Vor dem Start

1. **Argument:** `technik`, `audio`, `design`, `betrieb` oder `pruefung` springt in den Teilschritt, aber der Brief
   (Phase 1) wird trotzdem kurz bestätigt. Ohne Argument: voller Ablauf.
2. **Bestand nachschlagen statt raten** (Regel Always-Read-Never-Guess). Für den Brief zählen nur diese sechs
   Einträge; je `wz get <id>` und Prüfdatum ansehen, älter als 30 Tage → im Brief bestätigen lassen:
   `pc-system/marcos-gaming-pc-i5-13600k-rtx-ti-gb-ddr5-auf-mt-s-7175` (Hardware, Netz),
   `pc-system/pc-upgrade-plan-keine-rtx-ti-erhaeltlich-ziel-am5-621d` (Upgrade),
   `audio/equalizer-apo-kette-art-tune-stand-hesuvi-aktiv-9615` und `audio/warzone-audio-voicemeeter-potato-equalizer-apo-und-0b8b` (Audio),
   `pc-system/framedrops-bis-fps-in-cod-bo7-kamen-von-discord-7372` (NVENC-Falle),
   `persoenlich/streaming-und-profil-setup-marco-streamt-baf5` (Stil, zu prüfen).
   Breite Suche (`wz find streaming`, `wz find gpu`) nur, wenn eine ID nicht mehr existiert (`wz get` meldet ersetzt/archiviert).
3. **Bestand Stand 16.11.2026** (Startwerte, vor Nutzung per `wz get` auf Aktualität prüfen):

   | Bereich | Wert | Quelle |
   |---|---|---|
   | CPU / GPU | i5-13600K, ASUS TUF RTX 4070 Ti 12 GB (Ada, 8. Gen NVENC: H.264, HEVC, AV1) | wz `pc-system/marcos-gaming-pc-i5-13600k-rtx-ti-gb-ddr5-auf-mt-s-7175` |
   | Upgrade geplant | AM5 9850X3D + RTX 5080, neuer OLED-Hauptmonitor | wz `pc-system/pc-upgrade-plan-keine-rtx-ti-erhaeltlich-ziel-am5-621d`, `pc-system/oled-hauptmonitor-recherche-favoriten-asus-26e3` |
   | Monitore | ASUS VG27AQM1A 1440p 260 Hz (Mitte), 2× AOC 27" 144 Hz | wz `persoenlich/marcos-peripherie-asus-vg27aqm1a-1440p-logitech-2ae9` |
   | Netz | 1 Gbit/s down, Upload 55 Mbit/s **ungeprüft (laut ChatGPT)**, LAN an FRITZ!Box | wz `…-7175` Fakten 9 und 12 |
   | Audio Spiel | Gerät „Art Tune" (EQ APO, HeSuVi aktiv), Voicemeeter Potato, VB-Audio Hi-Fi Cable. **Ungeklärt:** 9615 sagt „Haupt-EQ hinter HeSuVi“ (22.10.), 0b8b Fakt 6 nennt EQ vor/nach HeSuVi „offen“ → Audio_Setup fragen. 0b8b Fakt 3: Aufnahme direkt aus Voicemeeter nach der Verarbeitung = gehörtes Signal (Kandidat für „wie gehört“) | wz `audio/equalizer-apo-kette-art-tune-stand-hesuvi-aktiv-9615`, `audio/warzone-audio-voicemeeter-potato-equalizer-apo-und-0b8b` |
   | Mikrofon | Trust GXT 255+ Onyx, direkt Windows/Discord (Krisp an, AGC aus), nicht über Voicemeeter | wz `…-0b8b` Fakt 7 |
   | Bekannte Falle | Discord-Clips (`discord_clips.exe`) belegte NVENC und kostete in BO7 bis 40 fps | wz `pc-system/framedrops-bis-fps-in-cod-bo7-kamen-von-discord-7372` |
   | Stil (**zu prüfen**, kein Bestand) | Stand 09/2025: Türkis `#40E0D0`/`#82FEFF`, Dark/Neon, HUD mit Hexagonen; über ein Jahr alt, gilt erst nach des Nutzers Bestätigung im Brief | wz `persoenlich/streaming-und-profil-setup-marco-streamt-baf5` |

   „Art Tune" ist nur ein vorläufiger interner Name (wz `audio/art-tune-ist-nur-ein-vorlaeufiger-interner-name-c89d`):
   nie in Overlays, Panels oder sichtbare Szenennamen übernehmen.
4. **Gebiet:** Am Audio-Setup (EQ APO, HeSuVi, Voicemeeter) selbst ändert dieser Skill **nichts**. Das gehört der
   Session „Audio_Setup“ (Session-Disziplin). Dieser Skill legt nur fest, wo OBS abgreift, und meldet Bedarf dorthin.
5. **Gamertag/Kanalname** kommt aus dem Skill `gamertag`. Ohne festen Namen läuft Technik und Betrieb normal, Design
   bekommt nur Platzhalter und bleibt in Phase 3c stehen.

## Phase 1 — Brief

Ablauf in dieser Reihenfolge:

1. **Ordner anlegen** (idempotent, synct über `~/projects` zum PC). `~/projects/Stream/` ist des Nutzers Stream-Projekt;
   geführt wird es von einer eigenen Stream-Session, solange es die nicht gibt, von der aufrufenden Session:
   ```bash
   mkdir -p ~/projects/Stream/tests ~/projects/Stream/assets
   ```
2. **Brief-Entwurf schreiben**, bevor der Nutzer gefragt wird: `~/projects/Stream/BRIEF_<datum>.md` mit allen 10 Slots;
   was der Bestand belegt, ist ausgefüllt (mit wz-ID), alles andere steht als `OFFEN`.
3. **Parallel Audio_Setup fragen** (per `SendMessage`, über „Setup Server“, falls nicht erreichbar): aktuelle
   Signalkette, Windows-Standardgerät, Bus des Spiels, Punkt vor EQ APO als eigenes Aufnahmegerät, EQ vor/nach HeSuVi
   (wz-Widerspruch oben). Die Antwort fließt in 3b, wartet aber nicht auf der Nutzer.
4. **der Nutzer fragen:** alle `OFFEN`-Slots in **einer** Nachricht, höchstens 10 Punkte (ein Punkt je Slot, Unterfragen
   im selben Slot gebündelt). Fachbegriffe je in einem Halbsatz erklären: NVENC = der Video-Encoder-Chip der
   Grafikkarte, der den Stream ohne Spiel-FPS-Verlust kodiert; Enhanced Broadcasting = OBS schickt mehrere
   Qualitätsstufen selbst an Twitch, Twitch wählt die Einstellungen automatisch.
5. **Brief ergänzen** mit des Nutzers Antworten (Slots von `OFFEN` auf Wert), dann der Nutzer in fünf Zeilen zeigen.

Slots (alle Pflicht):

```
1 Plattform(en):        Twitch | YouTube | Kick | mehrere (Multistream ja/nein)
2 Status Twitch:        Affiliate | Partner | keiner   (bestimmt 2K, Transcodes, Delay)
3 Hardware-Ziel:        heutige (RTX 4070 Ti) | nach geplantem Upgrade (RTX 5080, OLED) | beides
4 Inhalt:               Spiele (Warzone, BO, …), Just Chatting ja/nein
5 Webcam:               ja/nein, Modell, Platz im Bild
6 Ziel-Bild:            z. B. 1080p60 / 936p60 / 720p60 (Profilwahl nach Regel in obs-technik.md)
7 Spielton im Stream:   roh (ohne EQ/HeSuVi) | wie der Nutzer hört | wählbar
8 Name/Marke:           Gamertag fest? Farben/Schrift vorhanden? Stil 09/2025 noch gültig?
9 Overlay-Umfang + Vorbild-Kanäle: welche Teile (Live-Overlay, Alerts, Panels, Emotes, Badges, Offline-Banner,
                        Übergänge) und 2–3 Kanäle/Seiten als Vorbild (Pflicht nach design-qualitaet.md, Stufe V;
                        ohne Vorbild nur auf ausdrückliches „ohne Vorbild“)
10 Steuerung:           Stream Deck | Handy | nur Hotkeys
```

## Phase 2 — Plan

Aus Brief + Bestand einen Plan in Teilschritten (Abschnitte 3a–3d) schreiben, je Schritt: Ziel, konkrete Werte
mit Quelle aus `references/`, wer es tut (Claude am Server / der Nutzer am PC), wie geprüft wird. Datei:
`~/projects/Stream/PLAN_<datum>.md`. der Nutzer bestätigt den Plan, erst dann Umsetzung.

**Wer was tut:** Claude läuft auf netcup und hat **keinen Zugriff auf des Nutzers Windows-PC und OBS**. Jede Einstellung
in OBS, Windows, Twitch-Dashboard und Stream Deck macht der Nutzer selbst. Claude liefert dafür klickgenaue Schritte
(Menüpfad → Feld → Wert) und baut Dateien, die der Nutzer importiert: Grafiken, Overlay-HTML für Browserquellen,
Szenen-Sammlung als JSON nur nach Absprache. Eine Rückmeldung, die PC-Werte ausliest, kann die Session „Setup PC“
liefern (Anfrage per `SendMessage`, Session-Disziplin beachten).

## Phase 3 — Umsetzung in Teilschritten

Je Teilschritt erst die passende Referenzdatei mit dem Read-Tool lesen, dann die Werte aus dem Brief einsetzen.

### 3a Technik (OBS-Einrichtung) → `references/obs-technik.md`

Profil (A klassisch, B Enhanced Broadcasting, C 936p) nach der Entscheidungsregel in Abschnitt 3 der Referenz
wählen, nicht nach Gefühl. Reihenfolge: Plattform-Grenzen prüfen (Twitch-Doku, Stand-Datum notieren) → Encoder wählen → Ausgabe-Auflösung,
FPS, Bitrate, Keyframe → Szenen-Grundgerüst → Quellen → Plugins. Eine Zahl aus `references/` mit Datum älter als
90 Tage wird vor der Weitergabe an der Primärquelle nachgeprüft (Plattformen ändern Grenzen still).

### 3b Audio-Kette → `references/audio-kette.md`

Antwort von Audio_Setup (aus Phase 1) einarbeiten, dann Entscheidung „Spielton roh oder mit EQ/HeSuVi“ aus dem Brief umsetzen, Spuren-Plan (Stream, VOD, Aufnahme) festlegen,
Mikrofon-Filterkette, Monitoring ohne Echo. Die Abgriffsstelle gegenüber EQ APO ist der fehleranfälligste Punkt:
Annahme aus der Referenz **in Phase 4 mit einer Testaufnahme belegen**, nie nur behaupten.

### 3c Design → `references/design-assets.md`

1. Marke ableiten: Gamertag (fertig aus `gamertag`) → Farben, Schrift, Logo-Idee, Bildsprache.
2. Vorbild: zwei bis drei Kanäle oder Seiten, die der Nutzer mag, mit `site-anatomy` zerlegen (Stufe V aus
   `~/.claude/rules/design-qualitaet.md`; ohne Vorbild nur auf des Nutzers ausdrückliches „ohne Vorbild“).
3. Assets in den Twitch-Größen aus der Referenz bauen. Overlays und Alerts als HTML für die OBS-Browserquelle über
   `design-html`; Stilquellen `impeccable` und `frontend-design`.
4. Tor nach `~/.claude/rules/design-qualitaet.md`: rendern, mit Read ansehen, Anti-KI-Checkliste
   (`~/.claude/templates/anti_ki_checkliste.md`), Bewegung nach `~/.claude/scripts/visual_sheet_checkliste.md`,
   Zweitblick nach `~/.claude/templates/design_zweitblick.md`. Zusätzlich die Stream-Prüfungen aus der Referenz:
   Lesbarkeit bei 720p-Ausgabe und auf Handybreite, Emotes bei 28 px.

### 3d Betrieb → `references/betrieb.md`

Checkliste vor dem Stream, Hotkeys/Stream Deck, Moderation, Musik und Rechte, Datenschutz, Fairness (Delay).

## Phase 4 — Prüfung (Pflicht, keine Übergabe ohne)

Eine **Testaufnahme** ersetzt keinen Live-Test, aber sie fängt die meisten Fehler ab. der Nutzer macht am PC:

1. Aufnahme 2–3 min mit derselben Ausgabe wie der Stream (gleicher Encoder, gleiche Spuren), mit Spiel, Mikrofon,
   einem Alert und einem Szenenwechsel. Danach ein kurzer echter Testlauf zu Twitch mit Twitch Inspector
   (`inspector.twitch.tv`, von Twitch empfohlen) und OBS-Statistiken (verworfene Frames, Encoding-Überlast);
   dabei VOD-Spur und Delay mit prüfen, deren Zusammenspiel mit Enhanced Broadcasting unbelegt ist.
2. Datei an Claude: in den Syncthing-Ordner `~/projects/Stream/tests/` legen (synct nach netcup).
3. Claude prüft auf netcup mit Werkzeugen, die es dort gibt:
   - `ffprobe -hide_banner <datei>`: Auflösung, FPS, Codec, Anzahl Audiospuren, Samplerate.
   - Bild: `ffmpeg -ss <t> -i <datei> -frames:v 1 <scratchpad>/frame_<t>.png` an 3–4 Zeitpunkten, Bilder mit Read
     ansehen: Overlay lesbar, nichts Privates sichtbar (Benachrichtigungen, Discord-Namen, Taskleiste), Webcam-Rahmen sitzt.
   - Ton je Spur: `ffmpeg -i <datei> -map 0:a:<n> -af ebur128=framelog=quiet -f null -` → Lautheit (Ziel siehe
     `references/audio-kette.md`), Spitzenpegel; Spur ohne Musik auf der VOD-Spur stichprobenartig gegenhören lassen.
   - Spielton roh oder mit EQ? Gegen die Entscheidung im Brief prüfen (Verfahren in `references/audio-kette.md`).
4. Befund → zurück in den betroffenen Teilschritt, neu aufnehmen, höchstens drei Runden; Restbefund steht im Bericht.

## Output-Format

- Brief, Plan, Prüfbericht: `~/projects/Stream/` (`BRIEF_`, `PLAN_`, `PRUEFUNG_<datum>.md`).
- Assets: `~/projects/Stream/assets/<bereich>/` mit Größe im Namen (`emote_gg_112.png`).
- Prüfbericht = feste Teile: (1) Urteil eine Zeile, (2) Tabelle Prüfpunkt | Soll | Ist | Beleg, (3) was nur der Nutzer am
  PC tun kann, als nummerierte Klickliste.
- Antwort an der Nutzer: kurz, was erledigt ist, was er am PC tun muss, was offen ist.

## Constraints

- **Kein Zugriff auf den PC:** Nie behaupten, eine OBS- oder Windows-Einstellung sei gesetzt. Gesetzt ist nur, was
  der Nutzer bestätigt oder die Testaufnahme belegt.
- **Audio-Setup gehört „Audio_Setup“:** Kein Edit an EQ-APO-Configs, HeSuVi, Voicemeeter. Bedarf melden.
- **Plugins nur aus seriösen Quellen** (obsproject.com-Ressourcen mit verlinktem Repo, GitHub-Releases des Autors);
  eingestellte Plugins (Status in `references/obs-technik.md`) nicht empfehlen.
- **Plattformwerte sind zeitgebunden:** Jede Zahl trägt Quelle und Stand; Werte älter als 90 Tage vor Weitergabe
  nachprüfen. Werbeaussagen (Encoder-Vergleiche, „beste Qualität“) nur mit Primärquelle weitergeben.
- **Keine Zugangsdaten:** Stream-Key nie in Chat, Datei oder Repo. der Nutzer trägt ihn in OBS selbst ein.
- **Keine Käufe oder Abos** ohne des Nutzers Ja (Musik-Lizenzen, Alert-Dienste, Stream Deck, Plugins mit Bezahlschranke).
- **Datenschutz Dritter:** Keine Namen, Discord-Handles oder Gesichter Dritter in Assets oder Testbildern weitergeben.
- Design-Tor aus `rules/design-qualitaet.md` gilt voll; Bewegung ohne Überschwingen, Dauerbewegung nur mit
  Reduced-Motion-Variante bzw. abschaltbar.
- Read-only am Setup unter `~/.claude/`; geschrieben wird nur in `~/projects/Stream/` und im Scratchpad.

## Beispiel-Triggers

- `/stream-setup` — voller Ablauf ab Brief
- `/stream-setup technik` — OBS-Encoder, Bitrate, Szenen für die aktuelle Hardware
- `/stream-setup audio` — „mein Spielsound klingt im Stream komisch“, VOD ohne Musik
- `/stream-setup design` — Overlays, Emotes, Panels, Offline-Banner zum fertigen Gamertag
- `/stream-setup pruefung` — Testaufnahme auswerten
- Natürlich: „Ich will wieder auf Twitch streamen, hilf mir OBS einzurichten.“

## Changelog

- **v1.0.1** (2026-11-16): Nach zwei Fremdtests: Profil-Entscheidungsregel A/B/C (EB für alle Streamer belegt),
  Audio 160 → 128 kbps, Preset-Kriterium messbar, 2K klar nur Affiliate/Partner, Rückfall EB → A, `mkdir` ausdrücklich,
  Stil als „zu prüfen“, Brief mit 10 Slots (Webcam, Overlay-Umfang, Vorbild, Hardware-Ziel) als Entwurf vor den
  Fragen, Audio_Setup-Anfrage parallel in Phase 1, wz-Widerspruch EQ/HeSuVi als ungeklärt, Kurzliste der wz-IDs.
- **v1.0.0** (2026-11-16): Erste Version (Anlass der Nutzer 16.11. 19:06: Hilfe bei Design und Einrichtung, falls er
  wieder streamt). Referenzen: obs-technik, audio-kette, design-assets, betrieb, quellen.
