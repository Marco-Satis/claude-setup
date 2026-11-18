# Betrieb: Checkliste, Steuerung, Moderation, Rechte, Datenschutz, Fairness

> Stand 16.11.2026. Kürzel wie in `obs-technik.md`.

## Inhalt
1. Checkliste vor dem Stream
2. Hotkeys und Stream Deck
3. Chat-Moderation
4. Musik und Rechte
5. Datenschutz
6. Fairness: Stream-Delay gegen Stream-Sniping
7. Nach dem Stream

## 1. Checkliste vor dem Stream (der Nutzer am PC, ca. 5 min)

```
[ ] Windows „Nicht stören“ an, Benachrichtigungen aus (Windows, Discord, Browser, Handy-Spiegelung)
[ ] Discord: Clips aus (NVENC-Konkurrenz, wz framedrops-…-7372), Streamer-Modus an, Mitspieler informiert
[ ] Fremde Aufnahme aus: NVIDIA App Instant Replay, Xbox Game Bar
[ ] Zweitmonitore: nichts Privates, falls Bildschirmaufnahme genutzt wird
[ ] OBS: richtige Szenensammlung + Profil, Szene „Starting“ aktiv
[ ] Audio: Spielton-Quelle wie im Brief (roh/wie gehört), Mic-Pegel −20…−15 dB bei Sprache, Musik leise
[ ] Statistiken-Fenster offen (übersprungene/verworfene Frames)
[ ] Titel, Kategorie, Tags, Content-Classification-Labels im Dashboard gesetzt
[ ] Moderation: AutoMod-Stufe, Blocked Terms, Shield Mode vorbereitet
[ ] Delay gesetzt (Abschnitt 6), falls gewünscht
[ ] Kurzer Ton- und Bildcheck in der Vorschau, dann „Stream starten“
```

## 2. Hotkeys und Stream Deck

Mindest-Belegung: Szenen Starting / Live / BRB / Ending / Privat, Mic stumm umschalten, Spielton umschalten
(roh ↔ wie gehört, falls „wählbar“), Webcam an/aus, Replay/Clip-Marker.

| Weg | Stand | Beleg |
|---|---|---|
| OBS-Hotkeys | Einstellungen → Tastenkürzel; OBS 33 ergänzt Monitoring-Hotkeys je Quelle | [O1] |
| Elgato Stream Deck, OBS-Plugin | 3.0.3.31 vom 03.06.2026, braucht Stream Deck ≥ 6.9; Changelog: auf frühere Version zurückgesetzt wegen Ladefehlern | Elgato Marketplace [O10] `[gelesen über Agent]` |
| Touch Portal / Streamer.bot / Companion | über obs-websocket v5 (Werkzeuge → WebSocket-Servereinstellungen, Passwort setzen) | Touch Portal Doku [O11], OBS-KB Remote Control [O8] |

Hotkeys nicht auf Tasten legen, die CoD nutzt; Kombinationen mit Strg+Alt+F-Tasten `[Praxis]`. Kauf eines
Stream Deck nur auf des Nutzers Ja.

## 3. Chat-Moderation

- **AutoMod** mit Stufe (Twitch empfiehlt für IRL Stufe 2) [T11] `[gelesen]`; **Blocked Terms** (auch Emote-Codes,
  erscheinen als `***`) [T8]; **Chat-Verifizierung** per E-Mail/Telefon [T11]; **Follower-only** mindestens 10 min
  [T11]; **Shield Mode** vorbereiten (Voreinstellung, Aktivierung `/shield`) [T11] und Hilfe-Snippet [T12]
  (Hilfe-Seite selbst nicht gelesen).
- Mods: ein bis zwei vertraute Personen, Rechte im Dashboard; Regeln in einem Panel (`design-assets.md`).
- Bots nur mit offizieller Twitch-Anmeldung, keine Passwort-Weitergabe.

## 4. Musik und Rechte

| Punkt | Inhalt | Beleg |
|---|---|---|
| Grundregel | Keine aufgenommene Musik ohne Rechte; >99 % der DMCA-Meldungen betrafen Hintergrundmusik | Twitch-Blog 11.11.2020 [T13] `[gelesen über Agent]` |
| Folgen | Meldung → Verwarnung; **drei Verwarnungen = wiederholter Verstoß → Kontozugang wird beendet**; Gegendarstellung oder Rücknahme durch Rechteinhaber möglich | DMCA-Richtlinien (DE) [T14] `[gelesen]` |
| VOD-Spur | schützt nur das VOD, nicht den Live-Stream | `audio-kette.md` Abschnitt 6 |
| StreamBeats | kostenlos, ohne Namensnennung, für Streams; **keine Garantie**: „working to keep safe via Audible Magic“, VODs können trotzdem stummgeschaltet werden | streambeats.com Lizenz + FAQ [M1] `[gelesen über Agent]` |
| Soundtrack by Twitch | eingestellt; Datum nur aus Sekundärquellen (2023), Twitch-Ankündigung nicht gefunden | [T15] |
| Epidemic Sound, Pretzel, NCS, Monstercat | im Twitch-Blog 2020 als lizenzierte Quellen genannt; aktuelle Lizenzbedingungen **nicht gelesen** → vor Abo prüfen, Abo nur mit des Nutzers Ja | [T13] |
| Spielmusik | CoD-Menümusik im Spiel-Ton ist Teil des Spiels; separat abgespielte Soundtracks sind normale Musik | `[Praxis]`, nicht belegt |

## 5. Datenschutz

- Nichts Privates im Bild: Benachrichtigungen, Discord-Fenster mit Namen/Servern, Browser-Tabs, Taskleiste,
  Dateinamen, Standort, Echtname. Bildschirmaufnahme meiden, Spiel-/Fensteraufnahme bevorzugen.
- Webcam-Hintergrund prüfen (Post, Fotos, Fenster mit Aussicht).
- Stimmen Dritter (Discord, Mitbewohner) nur mit Einverständnis; Discord auf eigener Spur.
- Stream-Key nie zeigen (OBS-Einstellungen nicht live öffnen; wenn passiert: sofort im Dashboard neu erzeugen).
- Nach einem Leak eines Schlüssels: Regel `secret-handling.md`.

## 6. Fairness: Stream-Delay gegen Stream-Sniping

| Punkt | Inhalt | Beleg |
|---|---|---|
| OBS-Delay | Einstellungen → Erweitert → Stream-Verzögerung: Dauer, „Schnittpunkt beibehalten (Verzögerung erhöhen) beim Wiederverbinden“, Speicher-Schätzung; für alle verfügbar; Änderung erst beim nächsten Start | OBS-Quelltext-Texte [O12] `[gelesen über Agent]`, libobs `obs_output_set_delay` (context7) |
| Twitch-Delay | nur Partner, bis 15 min, „to ensure fairness during competitive play“ | Twitch-Partnerseite [T6] `[gelesen]` |
| CoD-Regeln | Die Call of Duty Security & Enforcement Policy nennt Stream-Sniping **nicht** (gelesen 16.11.2026) → Delay ist Eigenschutz, keine Pflicht; Sniper melden über die normale Spieler-Meldung | Activision [M2] `[gelesen über Agent]` |
| Abwägung | Delay senkt Chat-Interaktion. Battle Royale: 60–120 s reichen meist gegen Positions-Sniping `[Praxis]`; Just Chatting ohne Delay | — |
| EB + Delay | Zusammenspiel nicht belegt → im Testlauf prüfen | — |

Eigene Szene „Privat“ auch nutzen in Lobby/Squad-Auswahl, wenn Namen oder Einladungen sichtbar sind.

## 7. Nach dem Stream

Ending-Szene → Raid → Stream beenden → Aufnahme sichern. Kurznotiz (was hakte, Statistiken-Werte) nach
`~/projects/Stream/LOG.md`; wiederkehrende Probleme in den Plan aufnehmen.
