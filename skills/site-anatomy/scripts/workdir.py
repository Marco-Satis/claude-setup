#!/usr/bin/env python3
"""Arbeitsordner von site-anatomy anlegen, pruefen und fremde Kopien fristgerecht loeschen.

Layout eines Arbeitsordners (WD) unter der Workroot (~/site-anatomy, nicht gesynct):
  <domain>_<YYYY-MM-DD>[_n]/LOESCHDATUM   eine Zeile ISO-Datum
                           /meta.json     url, angelegt, loeschdatum
                           /kopien/       fremde Werke, werden zum Loeschdatum geloescht
                           /ergebnis/     eigene Auswertung, bleibt

Aufrufe:
  workdir.py init <url> [--days 30]   legt WD an, gibt den Pfad als einzige stdout-Zeile aus
  workdir.py sweep [--dry-run]        loescht kopien/ aller WD mit LOESCHDATUM < heute, JSON-Bericht
  workdir.py check <WD>               Exit 0 gueltiger WD, Exit 3 sonst

Exit-Codes: 0 ok, 1 sweep mit Fehlern, 3 ungueltige Eingabe/kein gueltiger WD.
Fremde Kopien werden nach 44b Abs. 2 UrhG geloescht, nicht archiviert (Ausnahme zur
Archiv-Regel). Nur stdlib; laeuft auch unter python3 -I.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
from urllib.parse import urlsplit

DEFAULT_DAYS = 30   # Frist aus der Recherche: Kopien nur so lange, wie die Analyse sie braucht
MAX_DAYS = 365      # laenger ist keine Analyse mehr, sondern Archiv; Verlaengern bewusst neu anlegen
MAX_SUFFIX = 99     # mehr als 99 Laeufe derselben Domain an einem Tag waere ein Fehler im Aufrufer


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse beendet sonst mit 2; das ist hier kein Sonderfall, sondern ungueltige Eingabe
        self.print_usage(sys.stderr)
        print(f"workdir.py: {message}", file=sys.stderr)
        sys.exit(3)


def workroot():
    """Workroot: SITE_ANATOMY_WORKROOT (Tests) oder ~/site-anatomy. Immer als realpath."""
    root = os.environ.get("SITE_ANATOMY_WORKROOT") or os.path.join(os.path.expanduser("~"), "site-anatomy")
    return os.path.realpath(root)


def under_workroot(path):
    """True, wenn der realpath von path echt unterhalb der Workroot liegt (Datei darf noch fehlen)."""
    root, real = workroot(), os.path.realpath(path)
    return real != root and os.path.commonpath([root, real]) == root


def read_loeschdatum(wd):
    with open(os.path.join(wd, "LOESCHDATUM"), encoding="utf-8") as fh:
        return dt.date.fromisoformat(fh.readline().strip())


def check_wd(wd):
    """Gibt den realpath zurueck, wenn wd ein gueltiger Arbeitsordner ist, sonst None."""
    real = os.path.realpath(wd)
    if not under_workroot(real) or not os.path.isdir(real):
        return None
    try:
        read_loeschdatum(real)
    except (OSError, ValueError):
        return None
    return real


def domain_of(url):
    if "://" not in url:
        url = "https://" + url.lstrip("/")
    host = (urlsplit(url).hostname or "").lower()
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        pass
    host = re.sub(r"[^a-z0-9.-]+", "-", host).strip(".-")
    return host or None


def cmd_init(args):
    if not 1 <= args.days <= MAX_DAYS:
        print(f"--days muss zwischen 1 und {MAX_DAYS} liegen", file=sys.stderr)
        return 3
    domain = domain_of(args.url)
    if not domain:
        print(f"keine Domain in URL: {args.url!r}", file=sys.stderr)
        return 3
    root = workroot()
    os.makedirs(root, mode=0o700, exist_ok=True)
    today = dt.date.today()
    stem = f"{domain}_{today.isoformat()}"
    for n in range(1, MAX_SUFFIX + 1):
        wd = os.path.join(root, stem if n == 1 else f"{stem}_{n}")
        try:
            os.mkdir(wd, 0o700)  # atomar: zwei parallele Aufrufe bekommen nie denselben Ordner
            break
        except FileExistsError:
            continue
    else:
        print(f"mehr als {MAX_SUFFIX} Arbeitsordner fuer {stem}", file=sys.stderr)
        return 3
    loesch = today + dt.timedelta(days=args.days)
    for sub in ("kopien", "ergebnis"):
        os.mkdir(os.path.join(wd, sub), 0o700)
    with open(os.path.join(wd, "LOESCHDATUM"), "w", encoding="utf-8") as fh:
        fh.write(loesch.isoformat() + "\n")
    meta = {"url": args.url, "domain": domain, "angelegt": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "loeschdatum": loesch.isoformat()}
    with open(os.path.join(wd, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print(wd)
    return 0


def cmd_sweep(args):
    root, today = workroot(), dt.date.today()
    report = {"workroot": root, "heute": today.isoformat(), "dry_run": args.dry_run,
              "geloescht": [], "faellig": [], "behalten": [], "ohne_kopien": [], "fehler": []}
    if not os.path.isdir(root):
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 0
    for name in sorted(os.listdir(root)):
        wd = os.path.join(root, name)
        if os.path.islink(wd) or not os.path.isdir(wd):
            continue  # Symlinks nie verfolgen, lose Dateien sind keine Arbeitsordner
        try:
            loesch = read_loeschdatum(wd)
        except FileNotFoundError:
            continue  # kein Arbeitsordner von workdir.py
        except (OSError, ValueError) as exc:
            report["fehler"].append({"wd": wd, "grund": f"LOESCHDATUM unlesbar: {exc}"})
            continue
        entry = {"wd": wd, "loeschdatum": loesch.isoformat()}
        if loesch >= today:
            report["behalten"].append(entry)
            continue
        target = os.path.join(wd, "kopien")
        if not os.path.lexists(target):
            report["ohne_kopien"].append(entry)
            continue
        real = os.path.realpath(target)
        if os.path.islink(target) or not os.path.isdir(target) or not under_workroot(real) \
                or os.path.dirname(real) != os.path.realpath(wd):
            report["fehler"].append({**entry, "grund": "kopien/ ist Symlink, kein Ordner oder liegt ausserhalb"})
            continue
        if args.dry_run:
            report["faellig"].append(entry)
            continue
        try:
            shutil.rmtree(real)
        except OSError as exc:
            report["fehler"].append({**entry, "grund": f"rmtree: {exc}"})
            continue
        stamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        report["geloescht"].append({**entry, "am": stamp})
        try:  # Nachweis im WD; scheitert das, ist die Loeschung trotzdem erfolgt
            meta_path = os.path.join(wd, "meta.json")
            with open(meta_path, encoding="utf-8") as fh:
                meta = json.load(fh)
            meta["kopien_geloescht"] = stamp
            with open(meta_path, "w", encoding="utf-8") as fh:
                json.dump(meta, fh, ensure_ascii=False, indent=1)
        except (OSError, ValueError):
            pass
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 1 if report["fehler"] else 0


def cmd_check(args):
    real = check_wd(args.wd)
    if real is None:
        print(f"kein gueltiger Arbeitsordner unter {workroot()}: {args.wd}", file=sys.stderr)
        return 3
    print(real)
    return 0


def main(argv=None):
    p = _Parser(prog="workdir.py", description="Arbeitsordner von site-anatomy verwalten")
    sub = p.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("init")
    pi.add_argument("url")
    pi.add_argument("--days", type=int, default=DEFAULT_DAYS)
    ps = sub.add_parser("sweep")
    ps.add_argument("--dry-run", action="store_true")
    pc = sub.add_parser("check")
    pc.add_argument("wd")
    args = p.parse_args(argv)  # Unterparser erben _Parser (parser_class = type(p)), enden also auch mit 3
    return {"init": cmd_init, "sweep": cmd_sweep, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
