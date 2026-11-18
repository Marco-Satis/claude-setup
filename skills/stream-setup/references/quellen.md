# Quellen und Lücken (Stand 16.11.2026)

`[gelesen]` = am 16.11.2026 in dieser Skill-Erstellung selbst gelesen (help.twitch.tv per Headless-Browser, da
WebFetch dort nur eine leere JS-Hülle erhält). `[Agent]` = von einem Recherche-Agenten gelesen, Werte stichprobenhaft
übernommen. `[Snippet]` = nur Suchergebnis-Auszug.

## Twitch
- [T1] Broadcasting Guidelines — https://help.twitch.tv/s/article/broadcasting-guidelines `[gelesen]`
- [T2] Enhanced Broadcasting with Multiple Encodes — https://help.twitch.tv/s/article/enhanced-broadcasting (Weiterleitung von `multiple-encodes`) `[gelesen]`
- [T3] Twitch-Blog 17.06.2026 Dual Format und 2K — https://blog.twitch.tv/en/2026/06/17/introducing-dual-format-and-2k-streaming-on-twitch/ `[Agent]`
- [T4] Twitch-Blog 08.01.2024 Enhanced Broadcasting Beta — https://blog.twitch.tv/en/2024/01/08/introducing-the-enhanced-broadcasting-beta/ `[Agent]`
- [T5] Channel Page Setup — https://help.twitch.tv/s/article/channel-page-setup `[gelesen]`
- [T6] Twitch Partner-Programm — https://www.twitch.tv/p/en/partners `[gelesen]`
- [T7] Twitch-Blog 22.06.2017 Offline-Seite — https://blog.twitch.tv/en/2017/06/22/put-your-channel-page-to-work-while-youre-afk-b1e9b0ffc7b4/ `[Agent]`, veraltet
- [T8] Emote Formatting & Instant Emote Upload Requirements — https://help.twitch.tv/s/article/emote-guidelines `[gelesen]`
- [T9] Subscriber Badge Guide — https://help.twitch.tv/s/article/subscriber-badge-guide `[gelesen]`
- [T10] Custom Bit Badges Guide — https://help.twitch.tv/s/article/custom-bit-badges-guide `[Snippet]`
- [T11] Twitch-Blog 11.05.2026 IRL Takeover (Moderations-Empfehlungen) — https://blog.twitch.tv/en/2026/05/11/the-irl-takeover-is-here/ `[Agent]`
- [T12] Setting Up Moderation — https://help.twitch.tv/s/article/setting-up-moderation-for-your-twitch-channel `[Snippet]`
- [T13] Twitch-Blog 11.11.2020 Musik und Urheberrecht — https://blog.twitch.tv/en/2020/11/11/music-related-copyright-claims-and-twitch/ `[Agent]`
- [T14] DMCA-Richtlinien — https://legal.twitch.com/legal/dmca-guidelines/ `[gelesen]` (deutsche Fassung, Abschnitt „Richtlinie für wiederholte Verstöße“)
- [T15] Soundtrack by Twitch, Start — https://blog.twitch.tv/en/2020/09/30/introducing-soundtrack-by-twitch-rights-cleared-music-for-all-twitch-creators/ `[Agent]`; Einstellung nur Sekundärquellen

## OBS, NVIDIA, Plugins
- [O1] OBS-Releases 31.0/32.0/32.1/33.0/33.0.1 — https://github.com/obsproject/obs-studio/releases `[Agent]` (33.0.1 vom 29.10.2026 aktuell)
- [O2] OBS-Locale (Encoder-Namen) — https://github.com/obsproject/obs-studio/blob/master/frontend/data/locale/en-US.ini `[Agent]`
- [O3] NVIDIA Broadcasting Guide — https://www.nvidia.com/en-us/geforce/guides/broadcasting-guide/ `[Agent, nur Zusammenfassung]`
- [O4] OBS-KB Advanced NVENC Options — https://obsproject.com/kb/advanced-nvenc-options `[Agent]`
- [O5] OBS 30.2 Release Notes (Multitrack Video, VOD-Track-Umbau) — https://obsproject.com/blog/obs-studio-30-2-release-notes `[Agent]`
- [O6] OBS NVENC-Standardwerte — https://github.com/obsproject/obs-studio/blob/master/plugins/obs-nvenc/nvenc-properties.c `[Agent]`
- [O7] Plugins: https://github.com/exeldro/obs-move-transition · https://github.com/exeldro/obs-source-record · https://github.com/exeldro/obs-shaderfilter · https://github.com/WarmUpTill/SceneSwitcher · https://github.com/Aitum/obs-vertical-canvas · https://github.com/Xaymar/obs-StreamFX `[Agent, GitHub-API]`
- [O8] obs-websocket / OBS-KB Remote Control — https://github.com/obsproject/obs-websocket · https://obsproject.com/kb/remote-control-guide `[Agent]`
- [O9] OBS-Forum 1440p-Beta (zweite Hand) — https://obsproject.com/forum/threads/enhanced-broadcast-doesnt-allow-me-to-stream-to-twitch-at-1440p.184630/ `[Agent]`
- [O10] Elgato OBS-Plugin — https://marketplace.elgato.com/product/obs-studio-35615969-830f-45c9-ba0a-1a295bba7fec `[Agent]`
- [O11] Touch Portal OBS — https://www.touch-portal.com/docs/obs/ `[Agent]`
- [O12] OBS Stream-Delay-Texte: siehe [O2]; libobs `obs_output_set_delay` über context7 `/websites/obsproject` `[gelesen]`

## Audio
- [A1] Equalizer APO Doku — https://sourceforge.net/p/equalizerapo/wiki/Documentation/ `[Agent]`
- [A2] Microsoft APO-Architektur — https://learn.microsoft.com/en-us/windows-hardware/drivers/audio/audio-processing-object-architecture `[Agent]`
- [A3] Microsoft Loopback Recording — https://learn.microsoft.com/en-us/windows/win32/coreaudio/loopback-recording `[Agent]`
- [A4] Microsoft Q&A „Are APO effects captured too?“ (unbeantwortet) — https://learn.microsoft.com/en-us/answers/questions/689393/ `[Agent]`
- [A5] OBS-Forum EQ APO in Aufnahme — https://obsproject.com/forum/threads/how-to-prevent-apo-equalizer-eq-from-being-apply-to-obs-internal-audio-recording.163980 `[Agent]`
- [A6] Microsoft ApplicationLoopback-Beispiel — https://github.com/microsoft/windows-classic-samples/tree/main/Samples/ApplicationLoopback `[Agent]`
- [A7] OBS-KB Application Audio Capture — https://obsproject.com/kb/application-audio-capture-guide `[Agent]`
- [A8] OBS-KB Filters Guide — https://obsproject.com/kb/filters-guide `[Agent]`
- [A9] OBS-KB Noise Suppression — https://obsproject.com/kb/noise-suppression-filter `[Agent]`
- [A10] NVIDIA Maxine Audio Effects SDK — https://docs.nvidia.com/deeplearning/maxine/audio-effects-sdk/index.html `[Agent, teilweise]`
- [A11] OBS-KB Audio Mixer Technical Details — https://obsproject.com/kb/audio-mixer-technical-details `[Agent]`
- [A12] OBS-KB Twitch VOD Track — https://obsproject.com/kb/twitch-vod-track-guide `[gelesen, Zusammenfassung]`

## Musik, Spielregeln
- [M1] StreamBeats Lizenz/FAQ — https://www.streambeats.com/licensing · https://www.streambeats.com/faq `[Agent]`
- [M2] Call of Duty Security & Enforcement Policy — https://support.activision.com/articles/call-of-duty-security-and-enforcement-policy `[Agent]`

## Nicht gelesen oder offen (mit Grund)
| Quelle | Grund | Was der Nutzer tun kann |
|---|---|---|
| Twitch Music Guidelines (safety.twitch.tv, legal.twitch.com/…/music) | 404 bzw. Access Denied | im Browser am PC „Twitch Music Guidelines“ öffnen, Link an Claude |
| help.twitch.tv Shield Mode, AutoMod, Verifizierung, Bit-Badges, Kanalpunkte | nur Snippets | beim Einrichten im Dashboard die angezeigten Vorgaben übernehmen |
| Twitch-Dashboard: Latenz-Modus „Niedrig/Normal“ | keine Primärquelle gefunden | im Dashboard → Einstellungen → Stream nachsehen |
| OBS-KB Stream-Delay, Enhanced Broadcasting, Aufnahmespuren | Seiten existieren nicht (404) | — (Quelltexte gelesen) |
| Epidemic Sound, Pretzel Lizenz für Twitch | 404 bzw. leere Seite | vor Abo Lizenzseite selbst öffnen |
| Ob WASAPI-Loopback EQ APO enthält | keine Primärquelle | Abgriff-Test `audio-kette.md` Abschnitt 4 |
| CoD-Anti-Cheat und OBS Game Capture | nicht recherchiert | im Testlauf prüfen |
| Upload-Bandbreite der Nutzer | wz-Wert aus ChatGPT, ungeprüft | Speedtest am PC |
