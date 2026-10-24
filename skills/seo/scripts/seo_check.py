#!/usr/bin/env python3
"""seo_check — mechanischer SEO-Vorlauf fuer den Skill `seo` (nur lesend, stdlib).

Aufruf:
  python3 -I seo_check.py <url|datei.html> [--max-seiten N] [--json]

Prueft je Seite: HTTP-Status, Weiterleitung, Title, Meta-Description, H1, Canonical,
robots-meta/X-Robots-Tag, Viewport, lang, hreflang, Alt-Texte, JSON-LD (Typen +
Pflichtfelder fuer Dataset/Organization/LocalBusiness/SoftwareApplication/Product/FAQPage),
Impressum-/Datenschutz-Link. Fuer URLs zusaetzlich robots.txt (inkl. KI-Crawler),
sitemap.xml und llms.txt. Folgt der Sitemap bis --max-seiten (Standard 10).

Seiteninhalte sind Daten: Das Skript fuehrt nichts aus und meldet nur Befunde.
"""
import argparse
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from pathlib import Path

UA = "Mozilla/5.0 (compatible; seo-check/1.0; +https://github.com/Marco-Satis/claude-setup)"
TIMEOUT = 15
BOTS = ["Googlebot", "Bingbot", "OAI-SearchBot", "ChatGPT-User", "GPTBot", "PerplexityBot",
        "Claude-SearchBot", "ClaudeBot", "Google-Extended", "CCBot"]
REQ_FIELDS = {
    "Dataset": ["name", "description", "license"],
    "Organization": ["name", "url"],
    "LocalBusiness": ["name", "address", "telephone"],
    "SoftwareApplication": ["name", "operatingSystem", "applicationCategory"],
    "Product": ["name", "offers"],
    "FAQPage": ["mainEntity"],
}


def fetch(url: str, limit: int = 3_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read(limit)
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return {"status": r.status, "url": r.geturl(), "headers": dict(r.headers),
                    "body": raw.decode(r.headers.get_content_charset() or "utf-8", "replace"),
                    "ms": int((time.monotonic() - t0) * 1000)}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "url": url, "headers": dict(e.headers or {}), "body": "", "ms": 0}
    except Exception as e:  # Netz, TLS, Timeout
        return {"status": 0, "url": url, "headers": {}, "body": "", "ms": 0, "error": f"{type(e).__name__}: {e}"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self._in_title = "", False
        self.meta, self.links, self.h1, self.imgs, self.jsonld = {}, [], [], [], []
        self.lang, self._in_h1, self._in_ld, self._buf = "", False, False, ""
        self.anchors = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or a.get("http-equiv") or "").lower()
            if key:
                self.meta[key] = a.get("content", "")
        elif tag == "link":
            self.links.append(a)
        elif tag == "h1":
            self._in_h1, self._buf = True, ""
        elif tag == "img":
            self.imgs.append(a)
        elif tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._in_ld, self._buf = True, ""
        elif tag == "a":
            self.anchors.append(a.get("href", ""))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "h1" and self._in_h1:
            self.h1.append(self._buf.strip())
            self._in_h1 = False
        elif tag == "script" and self._in_ld:
            self.jsonld.append(self._buf)
            self._in_ld = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_h1 or self._in_ld:
            self._buf += data


def ld_types(blocks):
    found, problems = [], []
    for raw in blocks:
        try:
            data = json.loads(raw)
        except ValueError as e:
            problems.append(f"JSON-LD unlesbar: {e}")
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for it in items:
            if not isinstance(it, dict):
                continue
            types = it.get("@type")
            for t in (types if isinstance(types, list) else [types]):
                if not t:
                    continue
                found.append(t)
                base = "LocalBusiness" if t not in REQ_FIELDS and "Business" in str(t) else t
                for f in REQ_FIELDS.get(base, []):
                    if f not in it:
                        problems.append(f"{t}: Feld '{f}' fehlt")
                if t == "Dataset":
                    d = str(it.get("description", ""))
                    if not 50 <= len(d) <= 5000:
                        problems.append(f"Dataset: description hat {len(d)} Zeichen (Soll 50-5000)")
    return found, problems


def check_page(html: str, url: str, headers: dict) -> dict:
    p = Page()
    try:
        p.feed(html)
    except Exception as e:
        return {"url": url, "befunde": [f"HTML nicht parsebar: {e}"]}
    b, info = [], {}
    title = re.sub(r"\s+", " ", p.title).strip()
    desc = p.meta.get("description", "").strip()
    info["title"] = f"{title[:90]} ({len(title)} Z.)"
    info["description"] = f"{len(desc)} Z."
    if not title:
        b.append("HOCH: kein <title>")
    elif not 30 <= len(title) <= 65:
        b.append(f"MITTEL: Title {len(title)} Zeichen (Richtwert 50-60)")
    if not desc:
        b.append("MITTEL: keine Meta-Description")
    elif not 70 <= len(desc) <= 160:
        b.append(f"NIEDRIG: Meta-Description {len(desc)} Zeichen (Richtwert 120-155)")
    if len(p.h1) != 1:
        b.append(f"MITTEL: {len(p.h1)} H1-Ueberschriften (Soll 1)")
    robots = (p.meta.get("robots", "") + " " + headers.get("X-Robots-Tag", "")).lower()
    if "noindex" in robots:
        b.append("HOCH: noindex gesetzt (Seite erscheint nicht in Google)")
    canon = [l.get("href") for l in p.links if "canonical" in l.get("rel", "").lower()]
    info["canonical"] = canon[0] if canon else "-"
    if not canon:
        b.append("NIEDRIG: kein Canonical")
    elif url.startswith("http") and urllib.parse.urljoin(url, canon[0]).rstrip("/") != url.rstrip("/"):
        b.append(f"MITTEL: Canonical zeigt woanders hin: {canon[0]}")
    if "viewport" not in p.meta:
        b.append("HOCH: kein Viewport-Meta (Mobildarstellung)")
    if not p.lang:
        b.append("NIEDRIG: <html lang> fehlt")
    info["lang"] = p.lang or "-"
    hreflang = [l for l in p.links if l.get("hreflang")]
    if hreflang:
        info["hreflang"] = ", ".join(l["hreflang"] for l in hreflang)
    no_alt = [i.get("src", "")[:60] for i in p.imgs if "alt" not in i]
    if no_alt:
        b.append(f"NIEDRIG: {len(no_alt)} von {len(p.imgs)} Bildern ohne alt (z. B. {no_alt[0]})")
    types, ld_prob = ld_types(p.jsonld)
    info["json_ld"] = ", ".join(types) or "keins im Rohtext (JS-Einbindung mit Browser pruefen)"
    b += [f"MITTEL: {x}" for x in ld_prob]
    hrefs = " ".join(h.lower() for h in p.anchors)
    de = p.lang.lower().startswith("de") or ".de/" in (url + "/")
    tag = "RECHT" if de else "HINWEIS (nur fuer DE-Anbieter Pflicht)"
    if not re.search(r"impressum|imprint|legal-notice", hrefs):
        b.append(f"{tag}: kein Impressum-Link gefunden (§ 5 DDG)")
    if not re.search(r"datenschutz|privacy", hrefs):
        b.append(f"{tag}: kein Datenschutz-Link gefunden (DSGVO Art. 13)")
    text_len = len(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", " ", html)).split())
    info["woerter"] = text_len
    if text_len < 150:
        b.append(f"MITTEL: nur ~{text_len} Woerter im HTML (wenig Inhalt oder JS-gerendert)")
    if re.search(r"(?i)(ignore (all )?previous instructions|you are an ai|assistant:)", html):
        b.append("HINWEIS: Seite enthaelt an KI gerichteten Text (nur gemeldet, nicht befolgt)")
    return {"url": url, "info": info, "befunde": b}


def site_checks(base: str) -> dict:
    root = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(base))
    out = {"root": root, "befunde": [], "bots": {}, "sitemap_urls": []}
    r = fetch(root + "/robots.txt")
    if r["status"] != 200:
        out["befunde"].append(f"MITTEL: robots.txt Status {r['status'] or r.get('error')}")
        rp = None
    else:
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(r["body"].splitlines())
        for bot in BOTS:
            out["bots"][bot] = "erlaubt" if rp.can_fetch(bot, root + "/") else "GESPERRT"
        if out["bots"].get("OAI-SearchBot") == "GESPERRT":
            out["befunde"].append("HOCH: OAI-SearchBot gesperrt (nicht in ChatGPT-Suche)")
        if out["bots"].get("Googlebot") == "GESPERRT":
            out["befunde"].append("HOCH: Googlebot gesperrt")
    sitemaps = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", r.get("body", "")) or [root + "/sitemap.xml"]
    for sm in sitemaps[:3]:
        s = fetch(sm)
        if s["status"] == 200:
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", s["body"])
            if "<sitemapindex" in s["body"]:
                for sub in locs[:5]:
                    ss = fetch(sub)
                    out["sitemap_urls"] += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", ss.get("body", ""))
            else:
                out["sitemap_urls"] += locs
        else:
            out["befunde"].append(f"MITTEL: Sitemap {sm} Status {s['status'] or s.get('error')}")
    if not out["sitemap_urls"]:
        out["befunde"].append("MITTEL: keine URLs aus Sitemap gelesen")
    l = fetch(root + "/llms.txt")
    out["llms_txt"] = "vorhanden" if l["status"] == 200 else "fehlt (optional, kein belegter Effekt)"
    if not root.startswith("https://"):
        out["befunde"].append("HOCH: kein HTTPS")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ziel")
    ap.add_argument("--max-seiten", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    result = {"ziel": a.ziel, "seiten": []}
    if re.match(r"https?://", a.ziel):
        result["site"] = site_checks(a.ziel)
        urls = [a.ziel] + [u for u in result["site"]["sitemap_urls"] if u.rstrip("/") != a.ziel.rstrip("/")]
        for u in urls[: max(1, a.max_seiten)]:
            r = fetch(u)
            if r["status"] != 200:
                result["seiten"].append({"url": u, "befunde": [f"HOCH: Status {r['status'] or r.get('error')}"]})
                continue
            pg = check_page(r["body"], r["url"], r["headers"])
            pg["info"]["ms"] = r["ms"]
            if r["url"].rstrip("/") != u.rstrip("/"):
                pg["befunde"].append(f"NIEDRIG: Weiterleitung {u} -> {r['url']}")
            result["seiten"].append(pg)
            time.sleep(0.5)  # hoeflich crawlen
        if len(urls) > a.max_seiten:
            result["ausgelassen"] = len(urls) - a.max_seiten
    else:
        p = Path(a.ziel)
        files = sorted(p.rglob("*.html"))[: a.max_seiten] if p.is_dir() else [p]
        for f in files:
            result["seiten"].append(check_page(f.read_text(encoding="utf-8", errors="replace"), str(f), {}))
    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0
    print(f"# seo_check: {a.ziel}\n")
    s = result.get("site")
    if s:
        print("## Website")
        print(f"- KI-/Such-Crawler laut robots.txt: " + (", ".join(f"{k} {v}" for k, v in s["bots"].items()) or "robots.txt fehlt"))
        print(f"- Sitemap-URLs: {len(s['sitemap_urls'])} · llms.txt: {s['llms_txt']}")
        for x in s["befunde"]:
            print(f"- {x}")
        print()
    for pg in result["seiten"]:
        print(f"## {pg['url']}")
        for k, v in (pg.get("info") or {}).items():
            print(f"- {k}: {v}")
        for x in pg["befunde"] or ["keine Befunde"]:
            print(f"- {x}")
        print()
    if result.get("ausgelassen"):
        print(f"_{result['ausgelassen']} weitere Sitemap-URLs nicht geprueft (--max-seiten erhoehen)_")
    return 0


if __name__ == "__main__":
    sys.exit(main())
