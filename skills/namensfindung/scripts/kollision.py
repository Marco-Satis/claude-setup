#!/usr/bin/env python3
"""Kollisionspruefung fuer Namenskandidaten (stdlib, nur lesend).

Prueft je Name: PyPI, npm, GitHub-Repos, App Store (iTunes-Suche) und Domains per RDAP.
Markenregister, Google Play und die Google-Suche haben keine freie API: Fuer sie gibt das
Skript die fertigen Such-URLs aus, die Pruefung dort macht der Agent (WebFetch/Playwright).

Aufruf:
    python3 -I ~/.claude/skills/namensfindung/scripts/kollision.py Name1 Name2 ... [--tlds com,de,io] [--json]

Statuswerte: FREI, BELEGT, TREFFER (Suche fand Aehnliches), UNKLAR (Abruf gescheitert, Grund steht dabei).
Exit-Code immer 0: Das Skript meldet, es entscheidet nicht.
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "namensfindung-kollision/1.0 (stdlib urllib)"
TIMEOUT = 15  # Sekunden je Abruf; RDAP-Server antworten sonst teils erst nach 20+ s gar nicht

# RDAP-Basis-URLs. .com/.net/.org/.dev/.app stehen im IANA-Bootstrap (data.iana.org/rdap/dns.json),
# .de und .io fehlen dort (geprueft 2026-11-16) und wurden direkt gegen Bekannt/Unsinn getestet.
RDAP = {
    "com": "https://rdap.verisign.com/com/v1/domain/",
    "net": "https://rdap.verisign.com/net/v1/domain/",
    "org": "https://rdap.publicinterestregistry.org/rdap/domain/",
    "dev": "https://pubapi.registry.google/rdap/domain/",
    "app": "https://pubapi.registry.google/rdap/domain/",
    "de": "https://rdap.denic.de/domain/",
    "io": "https://rdap.identitydigital.services/rdap/domain/",
    "tv": "https://rdap.nic.tv/domain/",
}
# Ohne RDAP: per whois, "NOT FOUND" = frei (.gg geprueft 2026-11-16 gegen google.gg)
WHOIS_FREI = {"gg": "NOT FOUND"}


def http_status(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:  # Netzwerk, Timeout, TLS
        return None, str(e).encode()


def by_status(code, err=b""):
    if code == 200:
        return "BELEGT", ""
    if code == 404:
        return "FREI", ""
    return "UNKLAR", f"HTTP {code}" if code else err.decode(errors="replace")[:80]


def slug(name):
    return re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", ""))


def check_pypi(name):
    n = re.sub(r"[-_.]+", "-", name).lower()  # PEP 503
    code, err = http_status(f"https://pypi.org/pypi/{urllib.parse.quote(n)}/json")
    st, why = by_status(code, err)
    if st == "FREI":
        why = "Name frei; PyPIs Aehnlichkeitssperre ('too similar') ist nicht oeffentlich pruefbar"
    return st, why


def check_npm(name):
    code, err = http_status(f"https://registry.npmjs.org/{urllib.parse.quote(slug(name))}")
    return by_status(code, err)


def check_domain(name, tld):
    base = RDAP.get(tld)
    if not base and tld in WHOIS_FREI:
        try:
            out = subprocess.run(["whois", f"{slug(name)}.{tld}"], capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT).stdout
        except Exception as e:
            return "UNKLAR", f"whois fehlgeschlagen: {e}"[:80]
        return ("FREI", "") if WHOIS_FREI[tld] in out else ("BELEGT", "")
    if not base:
        return "UNKLAR", f"kein RDAP-Server fuer .{tld} hinterlegt; whois {slug(name)}.{tld}"
    code, err = http_status(base + f"{slug(name)}.{tld}")
    return by_status(code, err)


def check_github(name):
    q = f"{name} in:name"
    try:
        out = subprocess.run(
            ["gh", "api", "-X", "GET", "search/repositories", "-f", f"q={q}",
             "-f", "per_page=5", "-f", "sort=stars"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT + 5)
        if out.returncode != 0:
            raise RuntimeError(out.stderr.strip()[:80])
        data = json.loads(out.stdout)
    except Exception:
        code, body = http_status("https://api.github.com/search/repositories?"
                                 + urllib.parse.urlencode({"q": q, "per_page": 5, "sort": "stars"}))
        if code != 200:
            return "UNKLAR", f"GitHub-Suche HTTP {code} (ohne gh-Login 10 Anfragen/min)"
        data = json.loads(body)
    total = data.get("total_count", 0)
    exact = [i for i in data.get("items", []) if i["name"].lower() == name.lower()]
    top = ", ".join(f"{i['full_name']} ({i['stargazers_count']}*)" for i in data.get("items", [])[:3])
    ucode, _ = http_status(f"https://api.github.com/users/{urllib.parse.quote(slug(name))}")
    if ucode == 200:
        return "BELEGT", f"GitHub-Konto/Org github.com/{slug(name)} existiert; {total} Repos; {top}"
    if exact:
        return "BELEGT", f"{total} Repos, exakt: {exact[0]['full_name']} ({exact[0]['stargazers_count']}*); {top}"
    return ("TREFFER" if total else "FREI"), f"{total} Repos im Namen; {top}" if total else ""


def check_appstore(name):
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": name, "entity": "software", "country": "de", "limit": 5})
    code, body = http_status(url)
    if code != 200:
        return "UNKLAR", f"HTTP {code}"
    res = json.loads(body).get("results", [])
    names = [r.get("trackName", "") for r in res]
    hit = [n for n in names if name.lower() in n.lower()]
    if hit:
        return "BELEGT", "; ".join(hit[:3])
    return ("TREFFER" if names else "FREI"), ("Suche liefert: " + "; ".join(names[:3])) if names else ""


def manual_urls(name):
    q = urllib.parse.quote(name)
    return {
        "DPMAregister (nur identisch, keine Aehnlichkeit)": "https://register.dpma.de/DPMAregister/marke/uebersicht",
        # Ergebnis-URL lief am 2026-11-24 im Browser (Namens-Agent MB227). F5-Bot-Sperre bei API-POSTs, Serien
        # und kaltem Direktaufruf ("Problem detected", Setup PC 24.11.): erst die Startseite laden, je Name eine
        # Abfrage mit >= 5 s Abstand; bei Sperre nicht wiederholen, Kandidat unter "ohne Zugriff".
        "TMview (EUIPO, DE+EU+national, unscharfe Suche; erst Startseite laden)":
            "https://www.tmdn.org/tmview/#/tmview/results?page=1&pageSize=100&criteria=C&basicSearch=" + q,
        "EUIPO eSearch plus (EU-Marken)": "https://euipo.europa.eu/eSearch/",
        # Aehnlichkeitssuche (similarname/results) lief am 2026-11-24 mit ~5 s Abstand ohne Sperre
        "WIPO Global Brand Database (Aehnlichkeitssuche ueber die Maske, ~5 s Abstand)":
            "https://branddb.wipo.int/en/quicksearch",
        "Google Play": f"https://play.google.com/store/search?q={q}&c=apps",
        "Google (Branche)": f"https://www.google.com/search?q=%22{q}%22+software+OR+app",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("namen", nargs="+")
    ap.add_argument("--tlds", default="com,de,io")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    # Windows: Pipe-Ausgabe ist sonst cp1252, Namen/Apps mit Sonderzeichen brachen ab (p-88636b22db, 24.11.2026)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    tlds =[t.strip(".").strip() for t in a.tlds.split(",") if t.strip()]
    report = {}
    for name in a.namen:
        r = {"PyPI": check_pypi(name), "npm": check_npm(name), "GitHub": check_github(name),
             "AppStore-DE": check_appstore(name)}
        for t in tlds:
            r[f"{slug(name)}.{t}"] = check_domain(name, t)
            time.sleep(0.3)  # RDAP-Server drosseln Serienabfragen; 0,3 s reicht bei <= 10 Namen
        report[name] = {"automatisch": {k: {"status": v[0], "info": v[1]} for k, v in r.items()},
                        "von_hand": manual_urls(name)}
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    for name, r in report.items():
        print(f"\n## {name}")
        for k, v in r["automatisch"].items():
            print(f"  {k:<22} {v['status']:<8} {v['info']}")
    print("\nVon Hand pruefen (keine freie API; <name> einsetzen):")
    for k, v in manual_urls("<name>").items():
        print(f"  - {k}: {v}")
    print("\nUebersicht (frei/geprueft, belegt-Stellen):")
    for name, r in report.items():
        st = [v["status"] for v in r["automatisch"].values()]
        bel = [k for k, v in r["automatisch"].items() if v["status"] == "BELEGT"]
        print(f"  {name:<20} {st.count('FREI')}/{len(st)} frei · belegt: {', '.join(bel) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
