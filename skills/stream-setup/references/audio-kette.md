# Audio-Kette: Spielton, EQ APO, Mikrofon, Spuren

> Stand 16.11.2026. Kürzel wie in `obs-technik.md`; Quellen-Nummern in `quellen.md`.
> **Gebiet:** EQ APO, HeSuVi, Voicemeeter und das Gerät „Art Tune“ gehören der Session „Audio_Setup“.
> Dieser Skill ändert dort nichts. Er wählt nur die Abgriffsstelle in OBS und meldet Bedarf an „Audio_Setup“.

## Inhalt
1. Ausgangslage bei der Nutzer
2. Was belegt ist und was nicht
3. Abgriff wählen: roh, wie gehört, wählbar
4. Abgriff-Test (Pflicht vor dem ersten Stream)
5. Mikrofon-Kette
6. Spuren, VOD-Spur, Monitoring
7. Pegel und Prüfung

## 1. Ausgangslage bei der Nutzer (aus wz, vor Nutzung per `wz get` auffrischen)

- Ausgabegerät „Art Tune“ mit EQ-APO-Kette: wenige Filter vor HeSuVi, HeSuVi aktiv (8 Kanäle), Haupt-EQ hinter
  HeSuVi, Kopfhörer-Korrektur DT 770 Pro X (wz `audio/equalizer-apo-kette-art-tune-stand-hesuvi-aktiv-9615`).
- Voicemeeter Potato im Autostart, VB-Audio Hi-Fi Cable als Standard (7.1); laut wz ist die heutige
  Signalreihenfolge **nicht bestätigt** (wz `audio/warzone-audio-voicemeeter-potato-equalizer-apo-und-0b8b`).
- Audioverbesserungen am Art-Tune-Gerät müssen an bleiben, sonst läuft EQ APO nicht (wz `audio/art-tune-audioverbesserungen-muessen-an-bleiben-e0c1`).
- Mikrofon Trust GXT 255+ direkt über Windows/Discord, Krisp in Discord an. Krisp wirkt nur in Discord, nicht in OBS.
- Der Klang ist auf Schrittortung im Kopfhörer getrimmt (Subtraktion, HeSuVi-Binaural). Für Zuschauer über
  Lautsprecher oder Handy klingt das ungewohnt. Deshalb ist „roh“ der Standard, „wie gehört“ nur auf ausdrücklichen Wunsch.

**Ungeklärt in wz:** 9615 (22.10.) sagt „Haupt-EQ hinter HeSuVi“, 0b8b Fakt 6 nennt EQ vor/nach HeSuVi „offen“.
0b8b Fakt 3: Aufnahme direkt aus Voicemeeter nach der Verarbeitung entspricht dem gehörten Signal (Kandidat für
„wie gehört“, im Abgriff-Test mit prüfen).

**Erster Schritt (läuft schon in Phase 1 parallel):** Bei „Audio_Setup“ (per `SendMessage`, über „Setup Server“ falls nicht erreichbar) die aktuelle
Kette erfragen: Welches Gerät ist Windows-Standard, wo hängt Voicemeeter, auf welchem Bus läuft das Spiel, gibt es
einen Punkt vor EQ APO, der als eigenes Aufnahmegerät sichtbar ist?

## 2. Was belegt ist und was nicht

| Aussage | Status |
|---|---|
| EQ APO sitzt wahlweise pre-mix (SFX/LFX) und/oder post-mix (EFX/GFX) im Gerätepfad; EFX läuft nach allem Mischen | belegt, EQ-APO-Doku [A1], Microsoft APO-Architektur [A2] |
| WASAPI-Loopback (OBS „Desktop-Audio“ / „Audioausgabe-Aufnahme“) erfasst den Mix, den der Endpunkt spielt | belegt, Microsoft Loopback Recording [A3] |
| Loopback enthält EQ APO und HeSuVi (post-APO) | **nicht belegt.** Microsoft-Q&A-Frage dazu unbeantwortet [A4], OBS-Forum deutet darauf hin [A5], Gegenbehauptung in einem Forum ungeprüft |
| OBS „Anwendungsaudioaufnahme“ (Application Audio Capture, BETA, ab Win10 2004) erfasst vor den Geräteeffekten | **nicht belegt**; plausibel, weil Prozess-Loopback ohne Endpunkt arbeitet [A6], [A7] |
| Bei Anwendungsaudioaufnahme Desktop-Audio global abschalten, sonst Echo/Doppelton | belegt, OBS-KB [A7] |

Folge: Die Abgriffsstelle wird **gemessen**, nicht behauptet (Abschnitt 4).

## 3. Abgriff wählen

| Wunsch im Brief | Abgriff (zu bestätigen mit Test) | Hinweis |
|---|---|---|
| **roh** (Standard) | „Anwendungsaudioaufnahme“ auf den CoD-Prozess, oder ein Voicemeeter-Bus/virtuelles Kabel vor dem Art-Tune-Gerät, falls „Audio_Setup“ einen solchen nennt | Discord, Browser, Systemtöne bleiben draußen, Datenschutz-Plus |
| **wie gehört** | „Audioausgabe-Aufnahme“ auf „Art Tune“ | enthält vermutlich EQ + HeSuVi-Binaural; enthält auch alles andere, was auf dem Gerät läuft (Discord, Benachrichtigungen) |
| **wählbar** | beide Quellen anlegen, je eine im Stream aktiv, Umschalten per Hotkey; beide auf eigene Aufnahmespuren | nie beide gleichzeitig auf Spur 1 |

Kanäle: Einstellungen → Audio → Kanäle **Stereo**. EB sendet nur Stereo/Mono [O5]. 7.1-Quellen mischt OBS auf Stereo
herunter; HeSuVi liefert ohnehin Stereo-Binaural.

Discord-Stimmen der Mitspieler: eigene Quelle (Anwendungsaudioaufnahme auf Discord) auf eigener Spur, damit sie im
VOD stummgeschaltet werden können. Mitspieler vorher fragen, ob sie im Stream hörbar sein dürfen.

## 4. Abgriff-Test (Pflicht vor dem ersten Stream)

Ziel: belegen, ob eine Quelle EQ APO/HeSuVi enthält. Rosa Rauschen ist flach; jede EQ-Kurve wird im Spektrum sichtbar.

1. Claude erzeugt auf netcup die Testdatei und legt sie in den Sync-Ordner:
   `ffmpeg -f lavfi -i "anoisesrc=color=pink:duration=20:amplitude=0.3" -ac 2 -ar 48000 ~/projects/Stream/tests/pink_20s.wav`
2. der Nutzer spielt sie am PC in einem einfachen Player über das Gerät „Art Tune“. OBS nimmt gleichzeitig auf:
   Spur 3 = Anwendungsaudioaufnahme auf den Player, Spur 4 = Audioausgabe-Aufnahme „Art Tune“, ggf. Spur 5 =
   Voicemeeter-Abgriff. (Aufnahme-Format mkv oder Hybrid-MP4, Spuren 3–5 in den Aufnahme-Einstellungen aktiv.)
3. Claude wertet aus:
   - Spektrum je Spur: `ffmpeg -i test.mkv -filter_complex "[0:a:<n>]showspectrumpic=s=1024x512:legend=1" <scratchpad>/spur<n>.png`, Bilder mit Read vergleichen.
   - Bandpegel je Spur: `ffmpeg -i test.mkv -map 0:a:<n> -af "bandpass=f=<hz>:width_type=o:w=0.5,astats=metadata=0" -f null - 2>&1 | grep "RMS level dB" | tail -1`
     (letzte Zeile = Gesamtwert) für 40, 125, 1000, 4500 und 8000 Hz; Abweichung gegen das Original `pink_20s.wav`.
     `<n>` zählt ab 0 über die Audiospuren der Datei (`ffprobe` zeigt die Reihenfolge).
   - Kanal-Korrelation (HeSuVi ändert L/R stark): `-af aphasemeter=video=0,ametadata=print:key=lavfi.aphasemeter.phase` Mittelwert vergleichen.
4. Urteil je Quelle: „roh“ (Spektrum ≈ Original, Korrelation ≈ Original) oder „mit Kette“. Ergebnis in den
   Prüfbericht und, weil es dauerhaft gilt, als wz-Eintrag (`wz neu --area audio …`, Quelle: Testdatei).

## 5. Mikrofon-Kette

OBS-Quelle „Audioeingabe-Aufnahme“ auf das Trust GXT 255+. Filter (Rechtsklick → Filter). Die OBS-Doku nennt die
Filter, aber **keine Reihenfolge** [A8]; Reihenfolge unten ist `[Praxis]`:

| # | Filter | Startwert | Beleg |
|---|---|---|---|
| 1 | Verstärkung (Gain) | so, dass normale Sprache im Mixer um −20 bis −15 dB liegt, Spitzen nicht über −6 dB | `[Praxis]` |
| 2 | Rauschunterdrückung | RNNoise (Standard) oder NVIDIA Noise Removal; NVIDIA braucht das Broadcast-SDK-Redistributable und Tensor-Kerne (4070 Ti hat sie) | OBS-KB [A9], NVIDIA Maxine [A10] |
| 3 | Noise Gate oder Expander | Expander klingt natürlicher; Schwelle knapp über Grundrauschen | `[Praxis]` |
| 4 | Kompressor | Ratio 3:1–4:1, Attack 6 ms, Release 60 ms, 3–6 dB Reduktion bei normaler Sprache | `[Praxis]` |
| 5 | Limiter | Schwelle −1 dB bis −2 dB, Release 60 ms | `[Praxis]` |

Pegelanzeige im Mixer liegt hinter den Filtern [A11]. Spiel-Ton wird **nicht** komprimiert (Dynamik ist Teil des Spiels).

## 6. Spuren, VOD-Spur, Monitoring

Einstellungen → Ausgabe → Erweitert. Erweiterte Audioeigenschaften (Zahnrad im Mixer) ordnen Quellen den Spuren zu.

| Spur | Inhalt | Wofür |
|---|---|---|
| 1 | Spiel + Mic + Alerts + Musik + Discord (falls erlaubt) | Live |
| 2 | wie 1, **ohne Musik** | Twitch-VOD-Spur |
| 3 | Spiel | Aufnahme/Schnitt |
| 4 | Mikrofon | Aufnahme/Schnitt |
| 5 | Discord | Aufnahme/Schnitt, stummschaltbar |
| 6 | Musik + Alerts | Aufnahme/Schnitt |

Twitch-VOD-Spur aktivieren: Einstellungen → Stream → Twitch-Konto verbinden; Ausgabe → „Eigene Encoder-Einstellungen
aktivieren“ → „Twitch-VOD-Spur“; Spur 1 = live, Spur 2 = VOD [A12] `[gelesen über Agent]`. Ob die VOD-Spur zusammen mit
Enhanced Broadcasting funktioniert, steht in keiner gelesenen Quelle → im Testlauf prüfen (VOD nachträglich anhören).
Die VOD-Spur schützt nur das VOD; Musik im Live-Stream bleibt DMCA-relevant (`betrieb.md`).

Monitoring: Einstellungen → Audio → Erweitert → Monitoring-Gerät = Kopfhörer. Mikrofon „Monitor aus“. Ist das
Monitoring-Gerät zugleich als Desktop-Audio erfasst, entsteht Doppelton; OBS 32 verhindert das bei „Monitor und
Ausgabe“ [O1], trotzdem beim Testlauf prüfen. OBS 33 hat Hotkeys je Quelle für das Monitoring [O1].

## 7. Pegel und Prüfung

- Ziel Lautheit gesamt Spur 1: um −16 bis −14 LUFS integriert, True Peak ≤ −1 dBTP `[Praxis]`; Twitch nennt keinen
  Lautheitswert (Broadcasting Guidelines [T1] gelesen, nichts dazu).
- Stimme muss über Spiel liegen: Mic etwa 6–10 LU lauter als Spiel in Sprechpausen-freien Abschnitten `[Praxis]`.
- Messung in Phase 4: `ffmpeg -i <aufnahme> -map 0:a:<n> -af ebur128=peak=true -f null -` je Spur.
