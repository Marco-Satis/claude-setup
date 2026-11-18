#!/usr/bin/env python3
"""Handle-Verfuegbarkeit fuer Gamertag-Kandidaten (stdlib, nur lesend, keine Logins).

Automatisch (oeffentliche Profilseite bzw. API, ohne Konto):
  Kick (API), YouTube @Handle (Profilseite), X (Profilseite, nur Hinweis), Steam-Custom-URL,
  GitHub-Konto, Domains .com/.de/.tv/.gg (ueber namensfindung/scripts/kollision.py).
Nur von Hand (Login, App oder Bot-Schutz noetig): Twitch, TikTok, Instagram, Discord,
  Activision-ID, BattleTag, Epic, PSN, Xbox -> das Skript gibt Pruefweg und URL aus.

Aufruf:
    python3 -I ~/.claude/skills/gamertag/scripts/handles.py Name1 Name2 ... [--tlds com,de,tv,gg] [--json]

Status: FREI, BELEGT, UNKLAR (Grund dabei), HINWEIS (Signal ohne Gewaehr). Exit-Code immer 0.
Hinweis: Eine freie Profilseite heisst nicht, dass die Plattform den Namen vergibt (gesperrte,
reservierte oder in Wartefrist befindliche Namen sehen von aussen wie frei aus).
"""
import argparse
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) gamertag-check/1.0"
TIMEOUT = 15  # Sekunden je Abruf


def get(url, follow=True):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read(400_000)
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return None, str(e).encode()


def by_code(code, err=b""):
    if code == 200:
        return "BELEGT", ""
    if code == 404:
        return "FREI", ""
    return "UNKLAR", f"HTTP {code}" if code else err.decode(errors="replace")[:80]


def handle(name):
    return re.sub(r"[^a-z0-9_]", "", name.lower())


def kick(n):
    return by_code(*get(f"https://kick.com/api/v2/channels/{n}"))


def youtube(n):
    # Getestet 2026-11-16: belegtes Handle 200, freies 404 (nach Consent-Redirect)
    return by_code(*get(f"https://www.youtube.com/@{n}"))


def x_com(n):
    code, err = get(f"https://x.com/{n}")
    st, why = by_code(code, err)
    if st in ("FREI", "BELEGT"):
        return "HINWEIS", f"Profilseite {'existiert' if st == 'BELEGT' else 'fehlt'}; gesperrte Konten blockieren den Namen trotzdem"
    return st, why


def steam(n):
    code, body = get(f"https://steamcommunity.com/id/{n}")
    if code != 200:
        return "UNKLAR", f"HTTP {code}"
    # Steam liefert immer 200; freie Custom-URL zeigt diese Fehlermeldung
    return ("FREI", "Custom-URL frei (Anzeigename ist auf Steam nicht eindeutig)") \
        if b"could not be found" in body else ("BELEGT", "Custom-URL vergeben")


def github(n):
    return by_code(*get(f"https://api.github.com/users/{n}"))


MANUELL = {
    "Twitch": "twitch.tv/<name> zeigt immer eine Seite; Pruefung im Browser (Profil vorhanden?) "
              "oder bei Kontoanlage/Umbenennung; Helix-API braucht eigene Twitch-App (Client-ID+Token)",
    "TikTok": "Bot-Schutz; in der App unter Profil bearbeiten > Benutzername (zeigt verfuegbar/vergeben)",
    "Instagram": "Login-Wand; in der App unter Profil bearbeiten > Benutzername",
    "Discord": "nur im Client: Einstellungen > Mein Account > Benutzername (zeigt verfuegbar)",
    "Activision-ID": "nicht eindeutig: gleiche Namen bekommen eine Ziffernfolge (#1234567); pruefen = Websuche nach bekannten Spielern/Streamern",
    "BattleTag": "nicht eindeutig: Ziffern-Code wird angehaengt; pruefen = Websuche",
    "Epic": "eindeutig; Pruefung nur beim Aendern im Konto (epicgames.com > Konto > Anzeigename)",
    "PSN": "eindeutig; Online-ID-Aenderung unter playstation.com > Konto > Profil (zeigt Verfuegbarkeit)",
    "Xbox": "Gamertag mit Ziffern-Suffix bei Doppelung; Pruefung beim Aendern auf xbox.com",
}


def domains(name, tlds):
    path = os.path.expanduser("~/.claude/skills/namensfindung/scripts/kollision.py")
    try:
        spec = importlib.util.spec_from_file_location("kollision", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        return {f".{t}": ("UNKLAR", f"namensfindung/kollision.py nicht ladbar: {e}"[:80]) for t in tlds}
    res = {}
    for t in tlds:
        res[f"{mod.slug(name)}.{t}"] = mod.check_domain(name, t)
        time.sleep(0.3)  # RDAP-Drosselung
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("namen", nargs="+")
    ap.add_argument("--tlds", default="com,de,tv,gg")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    tlds = [t.strip(". ") for t in a.tlds.split(",") if t.strip()]
    out = {}
    for name in a.namen:
        n = handle(name)
        r = {"Kick": kick(n), "YouTube @": youtube(n), "X": x_com(n), "Steam-URL": steam(n), "GitHub": github(n)}
        r.update(domains(name, tlds))
        out[name] = {"handle": n, "automatisch": {k: {"status": s, "info": i} for k, (s, i) in r.items()},
                     "von_hand": MANUELL}
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    for name, r in out.items():
        print(f"\n## {name}  (Handle-Form: {r['handle']})")
        for k, v in r["automatisch"].items():
            print(f"  {k:<20} {v['status']:<8} {v['info']}")
    print("\nVon Hand (gilt fuer alle Namen):")
    for k, v in MANUELL.items():
        print(f"  - {k}: {v}")
    print("\nUebersicht (Pflicht-Kanaele YouTube/Kick, dann Rest):")
    for name, r in out.items():
        a = r["automatisch"]
        bel = [k for k, v in a.items() if v["status"] == "BELEGT"]
        frei = sum(v["status"] == "FREI" for v in a.values())
        print(f"  {name:<18} YouTube {a['YouTube @']['status']:<7} Kick {a['Kick']['status']:<7} "
              f"{frei}/{len(a)} frei · belegt: {', '.join(bel) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
