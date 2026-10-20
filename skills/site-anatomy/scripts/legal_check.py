#!/usr/bin/env python3
"""Rechts-Check vor einer Website-Analyse: maschinenlesbare TDM-Vorbehalte suchen.

Geprueft wird die Ziel-URL und jede Station einer Weiterleitung (Origin und Pfad):
- robots.txt nach RFC 9309: laengste passende Regel gewinnt, Allow bei Gleichstand, `*` und `$`.
  Ausgewertet fuer das eigene Token `site-anatomy` (ersatzweise `*`), fuer `*` selbst und fuer
  die Gruppen der KI-Crawler (Sperre dort = TDM-Signal). Sperrt robots.txt den Pfad oder ist sie
  unerreichbar (5xx/429/Netzfehler = vollstaendiges Disallow, RFC 9309 2.3.1.4), wird die Seite
  selbst nicht abgerufen. Crawl-delay wird gemeldet.
- /.well-known/tdmrep.json nach W3C TDMRep (CG-FINAL 2024-05-10): erste passende Regel in
  Dateireihenfolge, `*` = beliebig viele Zeichen, `$` am Ende = Musterende. Danach ueberschreiben
  Header `tdm-reservation` und Meta `tdm-reservation` der finalen Antwort den Wert; ein fehlender
  Wert setzt nichts zurueck.
- Header X-Robots-Tag und Meta robots auf noai/noimageai.
Optional `--legal-pages`: bis zu 3 Impressum-/AGB-Seiten derselben Origin nach natuerlichsprachigen
TDM-Hinweisen durchsuchen (Exit-Code bleibt, Fund wird der Nutzer vorgelegt).
Nur lesende GET-Requests, nur stdlib, laeuft unter python3 -I.

Aufruf: legal_check.py <url> [--out <datei.json>] [--legal-pages]
  URL ohne Schema bekommt https://. --out haengt das Ergebnis an eine JSON-Liste an und muss
  unter der Workroot liegen (~/site-anatomy bzw. SITE_ANATOMY_WORKROOT).
Exit-Codes: 0 frei, 2 Vorbehalt ODER unklar (Feld `verdict`), 3 nicht erreichbar oder Eingabe
ungueltig. Exit 0/2/3 kommen nach dem Parsen immer mit JSON auf stdout; Exit 2 ohne JSON ist ein
Aufruffehler (z. B. falscher Skriptpfad), kein Vorbehalt.
"""
import argparse
import datetime as dt
import functools
import http.client
import importlib.util
import json
import os
import re
import socket
import ssl
import string
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) site-anatomy/0.1"
PRODUCT_TOKEN = "site-anatomy"  # eigenes robots-Token (RFC 9309 2.2.1), steckt auch im User-Agent
TIMEOUT = 15  # Sekunden; grosse Firmenseiten antworten selten langsamer
MAX_BYTES = 2_000_000  # nur der Kopf der Seite wird fuer Meta-Tags gebraucht
ROBOTS_MAX_BYTES = 512_000  # RFC 9309 2.5: mindestens 500 KiB auswerten
# KI-Crawler, deren Sperre als maschinenlesbarer TDM-Vorbehalt gilt (Recherche L21, Stand 2026-10)
AI_TOKENS = ("ClaudeBot", "anthropic-ai", "Claude-Web", "GPTBot", "ChatGPT-User", "CCBot", "Google-Extended",
             "Applebot-Extended", "PerplexityBot", "Bytespider", "meta-externalagent", "cohere-ai")
UNRESERVED = frozenset(string.ascii_letters + string.digits + "-._~")  # RFC 3986 2.3
NOAI = re.compile(r"\bno(?:image)?ai\b", re.I)
LEGAL_LINK = re.compile(r"impressum|\bagb\b|nutzungsbedingungen|\bterms\b|rechtliche[\s_-]*hinweise", re.I)
TDM_HINT = re.compile(r"text[\s-]*(?:und|and|&)[\s-]*data[\s-]*mining|\btdm\b|§\s*44\s*b|data[\s-]*mining|"
                      r"ki[\s-]*training|k(?:ü|ue)nstliche[nr]?\s+intelligenz", re.I)
MAX_LEGAL_PAGES = 3  # Impressum, AGB, Nutzungsbedingungen; mehr waere Crawling
LEGAL_GAP = 1.0  # Sekunden Mindestabstand zwischen den Zusatzabrufen
SNIPPET = 200  # Zeichen je Fundstelle; reicht fuer den Satz, kein Volltext


class Blocked(Exception):
    """Eine Weiterleitung fuehrt auf einen Pfad, den robots.txt sperrt oder nicht klaert."""

    def __init__(self, url, verdict, chain):
        super().__init__(url)
        self.url, self.verdict, self.chain = url, verdict, chain


class _Redirects(urllib.request.HTTPRedirectHandler):
    def __init__(self, guard=None):
        self.chain, self.guard = [], guard

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme.lower() not in ("http", "https"):
            fp.close()
            raise urllib.error.HTTPError(newurl, code, "Weiterleitung auf Nicht-HTTP-Ziel", headers, None)
        if self.guard:
            verdict = self.guard(newurl)
            if verdict:
                fp.close()
                raise Blocked(newurl, verdict, [*self.chain, newurl])
        self.chain.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Resp:
    def __init__(self, resp, body, chain):
        self.status, self.url, self.body, self.chain = resp.status, resp.geturl(), body, chain
        hs = resp.headers
        self.headers = {k.lower(): ", ".join(hs.get_all(k)) for k in set(hs.keys())}
        self.charset = hs.get_content_charset() or "utf-8"

    def text(self):
        try:
            return self.body.decode(self.charset, "replace")
        except LookupError:
            return self.body.decode("utf-8", "replace")


def ascii_url(url):
    """IDNA-Host und prozentkodierter Pfad, damit urllib auch Umlaut-URLs abrufen kann."""
    p = urlsplit(url)
    host = p.hostname or ""
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        pass
    netloc = f"[{host}]" if ":" in host else host
    if p.port:
        netloc += f":{p.port}"
    safe = "/%:@!$&'()*+,;=-._~"
    return urlunsplit((p.scheme, netloc, quote(p.path or "/", safe=safe), quote(p.query, safe=safe + "?"), ""))


def fetch(url, limit=MAX_BYTES, guard=None):
    rd = _Redirects(guard)
    opener = urllib.request.build_opener(rd)
    req = urllib.request.Request(ascii_url(url), headers={"User-Agent": USER_AGENT, "Accept-Language": "de-DE"})
    with opener.open(req, timeout=TIMEOUT) as resp:
        return Resp(resp, resp.read(limit), rd.chain)


NET_ERRORS = (urllib.error.URLError, http.client.HTTPException, OSError, ValueError)


def unreachable(exc):
    """DNS, Verbindung abgelehnt, TLS: der Host ist fuer jeden Abruf weg (Exit 3, nicht 'unklar')."""
    r = getattr(exc, "reason", exc)
    return isinstance(r, (socket.gaierror, ConnectionRefusedError, ssl.SSLError, ssl.CertificateError))


def origin_of(url):
    p = urlsplit(url)
    host = p.hostname or ""
    netloc = f"[{host}]" if ":" in host else host
    return f"{p.scheme.lower()}://{netloc}" + (f":{p.port}" if p.port else "")


def match_target(url):
    """Pfad plus Query, wie RFC 9309 und Googles Auslegung (auf die TDMRep verweist) ihn vergleichen."""
    p = urlsplit(ascii_url(url))
    return _norm(p.path or "/") + (("?" + _norm(p.query)) if p.query else "")


# --- Musterabgleich (RFC 9309 2.2.2/2.2.3, TDMRep 6.1) --------------------------------------
def _norm(s):
    """Prozent-Kodierung vereinheitlichen: unreservierte Zeichen dekodieren, Rest gross kodiert,
    Nicht-ASCII kodiert. %24/%2A werden zu $/* (so schreiben beide Specs woertliche Sonderzeichen)."""
    b, out, i = s.encode("utf-8"), [], 0
    while i < len(b):
        c, h = b[i], b[i + 1:i + 3]
        if c == 0x25 and len(h) == 2 and all(chr(x) in string.hexdigits for x in h):
            v = int(h, 16)
            out.append(chr(v) if chr(v) in UNRESERVED or chr(v) in "$*" else f"%{v:02X}")
            i += 3
            continue
        out.append(f"%{c:02X}" if c >= 0x80 else chr(c))
        i += 1
    return "".join(out)


@functools.lru_cache(maxsize=4096)
def _compile(pattern):
    """`*` = beliebig viele Zeichen, `$` nur als letztes Zeichen = Musterende, sonst Praefix-Treffer."""
    if not pattern.startswith(("/", "*")):
        pattern = "/" + pattern  # beide Specs verlangen fuehrenden Slash; fehlt er, ist er gemeint
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    rx = ".*".join(re.escape(_norm(part)) for part in body.split("*"))
    return re.compile(rx + (r"\Z" if anchored else ""), re.S)


def pattern_matches(pattern, target):
    return _compile(pattern).match(target) is not None


# --- robots.txt ----------------------------------------------------------------------------
def parse_robots(text):
    """Gruppen nach RFC 9309 2.1: aufeinanderfolgende user-agent-Zeilen bilden eine Gruppe."""
    groups, cur, in_rules = [], None, False
    for raw in text.lstrip("﻿").splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, val = (x.strip() for x in line.split(":", 1))
        key = key.lower()
        if key in ("user-agent", "useragent"):
            if cur is None or in_rules:
                cur = {"agents": [], "rules": [], "crawl_delay": None}
                groups.append(cur)
                in_rules = False
            m = re.match(r"\*|[A-Za-z_-]+", val)  # Produkt-Token: nur Buchstaben, _ und - (RFC 9309 2.2.1)
            if m:
                cur["agents"].append(m.group(0).lower())
        elif key in ("allow", "disallow") and cur is not None:
            in_rules = True
            if val:  # leeres Disallow/Allow ist keine Regel
                cur["rules"].append((key == "allow", val))
        elif key == "crawl-delay" and cur is not None:
            try:
                d = float(val)
            except ValueError:
                continue
            if d >= 0:
                cur["crawl_delay"] = max(cur["crawl_delay"] or 0, d)
    return groups


def groups_named(groups, token):
    t = token.lower()
    return [g for g in groups if t in g["agents"]]


def groups_for(groups, token):
    """Eigene Gruppen des Tokens, sonst die *-Gruppe; mehrere Treffer werden vereinigt (RFC 9309 2.2.1)."""
    return groups_named(groups, token) or groups_named(groups, "*")


def robots_allowed(groups, target):
    """Laengste passende Regel (Oktette) gewinnt, Allow bei Gleichstand; kein Treffer = erlaubt."""
    best = None
    for g in groups:
        for allow, pat in g["rules"]:
            if pattern_matches(pat, target):
                key = (len(pat.encode("utf-8")), allow)
                if best is None or key > best[0]:
                    best = (key, allow, pat)
    if best is None:
        return True, None
    return best[1], {"regel": "allow" if best[1] else "disallow", "muster": best[2]}


class Checker:
    """Holt robots.txt und tdmrep.json je Origin genau einmal."""

    def __init__(self):
        self._robots, self._tdmrep = {}, {}

    def robots(self, origin):
        if origin in self._robots:
            return self._robots[origin]
        url = origin + "/robots.txt"
        e = {"url": url, "groups": [], "state": "ok", "status": None, "note": None}
        try:
            r = fetch(url, ROBOTS_MAX_BYTES)
            e["status"] = r.status
            e["groups"] = parse_robots(r.body.decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            e["status"] = exc.code
            if exc.code == 429 or exc.code >= 500:
                e["state"], e["note"] = "unclear", "unerreichbar = vollstaendiges Disallow (RFC 9309 2.3.1.4)"
            elif 400 <= exc.code < 500:
                e["note"] = "nicht verfuegbar = keine Einschraenkung (RFC 9309 2.3.1.3)"
            else:
                e["state"], e["note"] = "unclear", f"Weiterleitung nicht aufloesbar: {exc}"
        except NET_ERRORS as exc:
            e["state"] = "unreachable" if unreachable(exc) else "unclear"
            e["note"] = f"Netzfehler: {exc}"
        self._robots[origin] = e
        return e

    def robots_verdict(self, url):
        """None = Abruf erlaubt, sonst 'vorbehalt' | 'unklar' | 'unerreichbar'."""
        e = self.robots(origin_of(url))
        if e["state"] == "unreachable":
            return "unerreichbar"
        if e["state"] == "unclear":
            return "unklar"
        t = match_target(url)
        ok_us, _ = robots_allowed(groups_for(e["groups"], PRODUCT_TOKEN), t)
        ok_star, _ = robots_allowed(groups_named(e["groups"], "*"), t)
        return None if ok_us and ok_star else "vorbehalt"

    def robots_findings(self, url):
        e, t = self.robots(origin_of(url)), match_target(url)
        f = {"check": "robots.txt", "url": e["url"], "pfad": t, "status": e["status"]}
        if e["note"]:
            f["note"] = e["note"]
        out, reserved, unclear = [f], False, e["state"] != "ok"
        if e["state"] == "ok":
            ok_us, hit_us = robots_allowed(groups_for(e["groups"], PRODUCT_TOKEN), t)
            ok_star, hit_star = robots_allowed(groups_named(e["groups"], "*"), t)
            f.update({f"allowed_for_{PRODUCT_TOKEN}": ok_us, "allowed_for_*": ok_star,
                      "treffer": hit_us if not ok_us else hit_star})
            reserved = not (ok_us and ok_star)
            blocked = []
            for tok in AI_TOKENS:
                named = groups_named(e["groups"], tok)
                if named and not robots_allowed(named, t)[0]:
                    blocked.append(tok)
            if blocked:
                out.append({"check": "robots.txt KI-Crawler", "pfad": t, "disallowed": blocked,
                            "note": "Sperre gegen KI-Crawler = maschinenlesbares TDM-Signal, als Vorbehalt behandelt"})
                reserved = True
        return out, reserved, unclear

    def crawl_delay(self, origin):
        e = self.robots(origin)
        ds = [g["crawl_delay"] for g in groups_for(e["groups"], PRODUCT_TOKEN) if g["crawl_delay"] is not None]
        return max(ds) if ds else None

    def tdmrep(self, origin):
        """Liefert (entries | None, finding, unclear)."""
        if origin in self._tdmrep:
            return self._tdmrep[origin]
        url = origin + "/.well-known/tdmrep.json"
        f, entries, unclear = {"check": "tdmrep.json", "url": url}, None, False
        try:
            r = fetch(url)
            f["status"] = r.status
            raw = r.body.lstrip(b"\xef\xbb\xbf \t\r\n")
            if not raw or raw.startswith(b"<"):
                # leere Antwort oder HTML-Fehlerseite mit 200 (SPA-Fallback): Datei existiert nicht
                f["note"] = "leer oder HTML statt JSON = Protokoll nicht umgesetzt"
            else:
                data = json.loads(raw.decode("utf-8", "replace"))
                if isinstance(data, list):
                    entries = data
                else:
                    f["note"], unclear = "kein JSON-Array, Datei ungueltig", True
        except urllib.error.HTTPError as exc:
            f.update({"status": exc.code, "note": "nicht abrufbar = Protokoll nicht umgesetzt (TDMRep 6.1)"})
        except json.JSONDecodeError as exc:
            f["note"], unclear = f"kaputtes JSON: {exc}", True
        except NET_ERRORS as exc:
            f["note"], unclear = f"Netzfehler: {exc}", True
        self._tdmrep[origin] = (entries, f, unclear)
        return self._tdmrep[origin]


def tdm_value(v):
    """TDMRep: nur 0 und 1 sind gueltig, alles andere gilt als unset (None)."""
    if isinstance(v, bool):
        return None
    if v in (0, 1, "0", "1"):
        return int(v)
    return None


def tdmrep_match(entries, target):
    """Erste passende Regel in Dateireihenfolge (TDMRep: 'The most specific match is the first in sequence')."""
    for e in entries or []:
        if isinstance(e, dict) and "location" in e and pattern_matches(str(e["location"]), target):
            return tdm_value(e.get("tdm-reservation")), e
    return None, None


class PageParser(HTMLParser):
    """Meta-Tags, Links und sichtbarer Text einer HTML-Seite."""

    def __init__(self):
        super().__init__()
        self.metas, self.links, self.text = [], [], []
        self._skip, self._a = 0, None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta" and a.get("name"):
            self.metas.append((a["name"].strip().lower(), a.get("content", "").strip()))
        elif tag in ("script", "style", "noscript"):
            self._skip += 1
        elif tag == "a" and a.get("href"):
            self._a = [a["href"], ""]
            self.links.append(self._a)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
        elif tag == "a":
            self._a = None

    def handle_data(self, data):
        if self._skip:
            return
        self.text.append(data)
        if self._a is not None:
            self._a[1] += data


def parse_page(resp):
    p = PageParser()
    p.feed(resp.text())
    p.close()
    return p


def legal_hints(ck, page, final_url, delay):
    """Impressum/AGB derselben Origin nach TDM-Formulierungen durchsuchen (nur Hinweis, kein Exit-Code)."""
    origin, seen, hints, checked = origin_of(final_url), set(), [], []
    for href, label in page.links:
        u = urljoin(final_url, href.strip()).split("#", 1)[0]
        if u in seen or origin_of(u) != origin or not LEGAL_LINK.search(f"{label} {href}"):
            continue
        seen.add(u)
        if len(checked) >= MAX_LEGAL_PAGES:
            break
        if ck.robots_verdict(u):
            checked.append({"url": u, "uebersprungen": "robots.txt"})
            continue
        time.sleep(delay)
        try:
            text = " ".join(" ".join(parse_page(fetch(u)).text).split())
        except NET_ERRORS as exc:
            checked.append({"url": u, "fehler": str(exc)})
            continue
        checked.append({"url": u})
        for m in TDM_HINT.finditer(text):
            a = max(0, m.start() - (SNIPPET - len(m.group(0))) // 2)
            hints.append({"url": u, "treffer": m.group(0), "ausschnitt": text[a:a + SNIPPET]})
            break  # eine Fundstelle je Seite reicht zum Vorlegen
    return {"check": "Impressum/AGB", "seiten": checked, "hinweise": hints,
            "note": "natuerlichsprachiger Hinweis aendert den Exit-Code nicht; der Nutzer vorlegen"}


def _workdir_module():
    # Expliziter Pfad statt import: unter python3 -I steht der Skriptordner nicht in sys.path
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "workdir.py")
    spec = importlib.util.spec_from_file_location("site_anatomy_workdir", path)
    mod = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True  # kein __pycache__ im Skill-Ordner, der per Syncthing auf den PC geht
    spec.loader.exec_module(mod)
    return mod


def write_out(path, result):
    """Ergebnis an die JSON-Liste in path anhaengen (atomar ersetzen, Kaputtes beiseitelegen)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    data = []
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                old = json.load(fh)
            data = old if isinstance(old, list) else [old]
        except (OSError, ValueError):
            os.replace(path, f"{path}.kaputt.{int(time.time())}")
    data.append(result)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse endet sonst mit 2 = "Vorbehalt"; ein Aufruffehler ist "ungueltig" = 3
        self.print_usage(sys.stderr)
        print(f"legal_check.py: {message}", file=sys.stderr)
        sys.exit(3)


def main(argv=None):
    ap = _Parser(prog="legal_check.py", description="TDM-Vorbehalte einer URL pruefen")
    ap.add_argument("url")
    ap.add_argument("--out", help="JSON-Liste, an die das Ergebnis angehaengt wird (unter der Workroot)")
    ap.add_argument("--legal-pages", action="store_true", help="Impressum/AGB nach TDM-Hinweisen durchsuchen")
    args = ap.parse_args(argv)

    url = args.url.strip()
    if url.startswith("//"):
        url = "https:" + url
    elif "://" not in url:
        url = "https://" + url
    res = {"url": url, "final_url": None, "redirects": [], "reachable": False, "page_fetched": False,
           "status": None, "reserved": False, "unclear": False, "verdict": None, "crawl_delay": None,
           "tdm_reservation": None, "findings": [],
           "checked_at": dt.datetime.now().astimezone().isoformat(timespec="seconds")}

    if args.out:
        wd = _workdir_module()
        if not wd.under_workroot(args.out):
            print(f"--out muss unter {wd.workroot()} liegen: {args.out}", file=sys.stderr)
            return 3

    def finish(code, verdict=None):
        res["verdict"] = verdict or {0: "frei", 2: "vorbehalt" if res["reserved"] else "unklar",
                                     3: "nicht erreichbar"}[code]
        print(json.dumps(res, ensure_ascii=False, indent=1))
        if args.out:
            write_out(args.out, res)
        return code

    try:
        p = urlsplit(url)
        valid = p.scheme.lower() in ("http", "https") and bool(p.hostname)
        p.port  # wirft ValueError bei ungueltigem Port
    except ValueError as exc:
        valid, res["error"] = False, str(exc)
    if not valid:
        res.setdefault("error", "keine gueltige http(s)-URL")
        return finish(3, "ungueltig")

    ck = Checker()
    # 1. robots.txt vor dem ersten Seitenabruf (RFC 9309): gesperrt oder unklar -> Seite nicht abrufen
    first = ck.robots_verdict(url)
    stop_at = url if first else None
    if first == "unerreichbar":
        res["error"] = ck.robots(origin_of(url))["note"]
        return finish(3)
    resp = None
    if not first:
        try:
            resp = fetch(url, guard=ck.robots_verdict)
        except Blocked as b:
            res["redirects"] = b.chain
            if b.verdict == "unerreichbar":
                res.update(final_url=b.url, error=ck.robots(origin_of(b.url))["note"])
                return finish(3)
            stop_at = b.url
        except urllib.error.HTTPError as exc:
            res.update(final_url=exc.geturl() or url, status=exc.code, error=f"HTTP {exc.code}")
            return finish(3)
        except NET_ERRORS as exc:
            res["error"] = str(exc)
            return finish(3)

    res["reachable"] = True
    if resp is None:
        # Abbruch vor dem Abruf: nur robots-Befund fuer die gesperrte Station
        res["final_url"] = stop_at
        fs, reserved, unclear = ck.robots_findings(stop_at)
        res["findings"].extend(fs)
        res.update(reserved=reserved, unclear=unclear, crawl_delay=ck.crawl_delay(origin_of(stop_at)))
        res["findings"].append({"check": "Seite", "note": "nicht abgerufen, robots.txt sperrt oder ist unklar"})
        return finish(2)

    res.update(final_url=resp.url, redirects=resp.chain, status=resp.status, page_fetched=True)
    stations = list(dict.fromkeys([url, *resp.chain, resp.url]))
    reserved = unclear = False
    delays = []
    file_vals = {}
    for s in stations:
        fs, r, u = ck.robots_findings(s)
        res["findings"].extend(fs)
        reserved |= r
        unclear |= u
        o = origin_of(s)
        delays.append(ck.crawl_delay(o))
        entries, f, u = ck.tdmrep(o)
        val, entry = tdmrep_match(entries, match_target(s))
        file_vals[s] = val
        res["findings"].append({**f, "pfad": match_target(s), "reservation": val, "entry": entry})
        unclear |= u
        reserved |= val == 1 and s != resp.url  # Zwischenstationen: Dateiwert gilt fuer sich
    delays = [d for d in delays if d is not None]
    res["crawl_delay"] = (int(max(delays)) if max(delays).is_integer() else max(delays)) if delays else None

    # TDMRep-Reihenfolge fuer die finale Seite: Datei -> Header -> Meta, spaetere Quelle gewinnt
    tdm = {"value": file_vals.get(resp.url), "source": "tdmrep.json" if file_vals.get(resp.url) is not None else None,
           "policy": None}
    hv, hp = resp.headers.get("tdm-reservation"), resp.headers.get("tdm-policy")
    res["findings"].append({"check": "header tdm-reservation", "value": hv, "policy": hp})
    if tdm_value((hv or "").strip()) is not None:
        tdm.update(value=tdm_value(hv.strip()), source="header", policy=hp)
    xrt = resp.headers.get("x-robots-tag")
    if xrt is not None:
        hit = bool(NOAI.search(xrt))
        res["findings"].append({"check": "header x-robots-tag", "value": xrt, "noai": hit})
        reserved |= hit
    page = parse_page(resp)
    meta_names = {"robots", "googlebot", PRODUCT_TOKEN} | {t.lower() for t in AI_TOKENS}
    for name, content in page.metas:
        if name == "tdm-reservation":
            res["findings"].append({"check": "meta tdm-reservation", "value": content})
            if tdm_value(content) is not None:
                tdm.update(value=tdm_value(content), source="meta")
        elif name == "tdm-policy":
            tdm["policy"] = content
        elif name in meta_names and NOAI.search(content):
            res["findings"].append({"check": f"meta {name}", "value": content, "note": "noai-Signal, als Vorbehalt behandelt"})
            reserved = True
    res["tdm_reservation"] = tdm
    reserved |= tdm["value"] == 1

    if args.legal_pages:
        delay = max(LEGAL_GAP, float(res["crawl_delay"] or 0))
        res["findings"].append(legal_hints(ck, page, resp.url, delay))

    res.update(reserved=reserved, unclear=unclear)
    return finish(2 if reserved or unclear else 0)


if __name__ == "__main__":
    sys.exit(main())
