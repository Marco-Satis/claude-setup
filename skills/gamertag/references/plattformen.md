# Plattformen: Namensregeln, Änderungsfristen, Prüfweg (Stand 2026-11-16)

**Belegstand:** belegt = offizielle Hilfeseite der Plattform gelesen (meist über Suchauszug, weil die Seiten per Skript schlecht abrufbar sind) · sekundär = nur Ratgeberseiten · offen = nicht gefunden.
Regeln ändern sich. Vor einer echten Umbenennung die verlinkte Hilfeseite erneut lesen.

## Regeln und Fristen

| Plattform | Länge / Zeichen | Ändern | Kosten | Eindeutig? | Quelle | Stand |
|---|---|---|---|---|---|---|
| Twitch Username | mind. 4 Zeichen (belegt); bis 25, nur Buchstaben, Ziffern, Unterstrich (sekundär) | alle 60 Tage, nicht live und nicht bei laufendem VOD-Upload; verifizierte E-Mail nötig | frei | ja; alter Name mind. 180 Tage gesperrt, bei Partnern nie wieder frei; Emote-Präfix ändert sich nicht automatisch | help.twitch.tv/s/article/username-rename-and-recycling-policies | belegt (Längen-Obergrenze sekundär) |
| Twitch Emote-Präfix | Länge in der Hilfe nicht gefunden | Partner alle 60 Tage; übrige Monetarisierte einmalig nach Umbenennung | frei | — | help.twitch.tv/s/article/subscriber-emote-guide | belegt (Länge offen) |
| YouTube @Handle | 3–30 Zeichen, Buchstaben, Ziffern, `_ - .` und Mittelpunkt (nicht am Anfang/Ende); nicht wie URL oder Telefonnummer | 2× in 14 Tagen; altes Handle 14 Tage reserviert; Handle gelöschter Kanäle 60 Tage gesperrt (Community-Guide) | frei | ja, Groß-/Kleinschreibung egal | support.google.com/youtube/answer/11585688, …/15920820 | belegt |
| Kick | Länge offen | Kanal- und Anzeigename je alle 60 Tage; 2FA Pflicht | frei | ja | help.kick.com/en/articles/7120563 | belegt (Länge offen) |
| TikTok | Buchstaben, Ziffern, `_` und `.` (Punkt nicht am Ende); Länge offen | alle 30 Tage; aufgegebener Name kurz gesperrt | frei | ja | support.tiktok.com/en/getting-started/setting-up-your-profile/changing-your-username | belegt (Länge offen) |
| X | höchstens 15 Zeichen, Buchstaben, Ziffern, `_` | jederzeit | frei | ja; inaktive Namen werden nicht freigegeben | help.x.com/en/managing-your-account/x-username-rules | belegt |
| Instagram | Länge offen | Rückkehr zum alten Namen „in den meisten Fällen“ möglich | frei | ja | help.instagram.com/876876079327341 | teilweise offen |
| Discord | 2–32, nur a–z, 0–9, `_` und `.` (nicht `..`), klein; nicht „discord“, `@ # :` | 2× pro Woche | frei | ja | support.discord.com/hc/en-us/articles/12620128861463, docs.discord.com/developers/resources/user | belegt |
| Activision-ID | 2–16 Zeichen, keine Sonderzeichen (Anmeldeseite) | Umbenennung braucht Token: 1 neues alle 6 Monate, höchstens 2 gleichzeitig; Filter-Verstoß → „anon…“ | Kauf von Tokens nicht belegt | nein, Ziffernfolge hängt an | support.activision.com/articles/name-changes-in-call-of-duty | belegt (Länge sekundär) |
| BattleTag | 3–12 Zeichen, Akzente erlaubt, kein Leerzeichen/Symbol, nicht mit Ziffer beginnen | 1× frei | danach kostenpflichtig im Battle.net-Shop (Preis regional, ca. 10 USD sekundär) | nein, Ziffern-Code fest | support.blizzard.com Artikel 26963 (Naming Policy), 10367 (Changing) | belegt (Preis sekundär) |
| Epic | 3–16 Zeichen; keine Bezüge zu Epic-Mitarbeitern, -Produkten oder -Figuren, keine persönlichen Daten | alle 14 Tage, Support hebt Sperre nicht auf | frei | ja | epicgames.com/help … a000084763 (Regeln), a18323090 (Ändern) | belegt |
| PSN Online-ID | offen | beliebig oft | 1. Änderung frei, danach kostenpflichtig (2019: 9,99 USD, mit PS Plus 4,99; aktueller Preis im Konto); Zurück zur alten ID frei | ja | playstation.com/en-us/support/account/change-online-id | belegt (Preis von 2019) |
| Xbox Gamertag | offen | auf Web, Konsole, Windows | offen (Hilfeseite per Skript nicht lesbar) | Ziffern-Suffix bei Doppelung (sekundär) | support.xbox.com/en-US/help/account-profile/profile/change-xbox-live-gamertag | offen |
| Steam | Anzeigename frei wählbar, nicht eindeutig; Custom-URL eindeutig | jederzeit | frei | nur Custom-URL | — | Praxis, Skript-getestet |

## Automatisch prüfbar (Skript `handles.py`, getestet 2026-11-16 mit belegtem und Unsinnsnamen)

| Plattform | Weg | Aussagekraft |
|---|---|---|
| Kick | `https://kick.com/api/v2/channels/<name>` 200/404 | gut |
| YouTube | `https://www.youtube.com/@<name>` 200/404 nach Consent-Weiterleitung | gut; reservierte Handles (14-Tage-Frist) wirken frei |
| X | `https://x.com/<name>` 200/404 | nur Hinweis; gesperrte und inaktive Konten blockieren trotzdem |
| Steam | `https://steamcommunity.com/id/<name>`, Text „could not be found“ = frei | gut, nur für die Custom-URL |
| GitHub | `https://api.github.com/users/<name>` | gut |
| Domains .com/.de/.tv/.gg/.io | RDAP bzw. whois über `namensfindung/scripts/kollision.py` | gut |

## Nur von Hand

| Plattform | Grund | Weg |
|---|---|---|
| Twitch | Kanalseite liefert für jeden Namen eine Seite (JS), headless ohne verwertbares Ergebnis; inoffizielle Schnittstellen mit fremder Client-ID nicht verwenden; offizielle Helix-API braucht eigene Twitch-App | der Nutzer: Umbenennen-Dialog unter Einstellungen > Profil zeigt Verfügbarkeit |
| TikTok, Instagram | Bot-Schutz, Login-Wand | App: Profil bearbeiten > Benutzername |
| Discord | nur im Client | Einstellungen > Mein Account > Benutzername |
| Epic, PSN, Xbox | nur im Konto beim Ändern | jeweiliger Umbenennen-Dialog |
| Activision, BattleTag | nicht eindeutig, deshalb kein „belegt“ | Websuche nach bekannten Spielern/Streamern mit gleichem Namen (Verwechslung, nicht Verfügbarkeit) |

## Ohne Zugriff geblieben

| Quelle | Grund | Was der Nutzer tun kann |
|---|---|---|
| Twitch-Längenobergrenze und Zeichenregel (offizieller Wortlaut) | Hilfeseiten laden per Skript nur „CSS Error“ | im Umbenennen-Dialog sehen |
| Twitch-Emote-Präfix-Länge | in der Hilfe nicht gefunden | im Emote-Bereich des Creator-Dashboards sehen |
| Xbox-Gamertag-Kosten | Hilfeseite per Skript leer | support.xbox.com im Browser |
| Instagram-, TikTok-, Kick-Längen | nicht in den Suchauszügen | im jeweiligen Dialog sehen |
| Twitch-Verfügbarkeit automatisch | Abfrage über inoffizielle Twitch-Schnittstelle wurde vom Sicherheitsfilter abgelehnt (zu Recht: fremde Client-ID) | Verfügbarkeit selbst im Dialog prüfen oder eigene Twitch-App für die Helix-API anlegen |
