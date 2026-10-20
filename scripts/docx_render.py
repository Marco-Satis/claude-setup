#!/usr/bin/env python3
"""DOCX/ODT/PPTX/XLSX visuell pruefbar machen: Office-Datei -> PDF -> PNG-Seiten.

Claude kann selbst erzeugte Office-Dateien sonst nur strukturell pruefen (XML lesen,
Tabellen zaehlen). Layoutfehler - umbrechende Tabellenkoepfe, gemischte Schriftgroessen,
verrutschte Fusszeilen - sind so unsichtbar. Dieses Skript rendert die Seiten als PNG,
die anschliessend mit dem Read-Tool angesehen werden.

Laeuft auf Windows (soffice.com) und Linux (soffice).

Beispiele:
    python docx_render.py bericht.docx
    python docx_render.py bericht.docx --outdir render --dpi 150
    python docx_render.py bericht.docx --pages 1,3 --clip 0,0.85,1,1   # nur Fusszeile
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("docx_render")

# Eigenes LibreOffice-Profil je Automatisierung: sonst haengt der headless-Aufruf
# am Profil-Lock, sobald parallel eine LibreOffice-Oberflaeche geoeffnet ist.
PROFILE_DIR = Path.home() / ".claude" / ".cache" / "lo_profile_claude"

WINDOWS_CANDIDATES = [
    Path(r"C:\Program Files\LibreOffice\program\soffice.com"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.com"),
]


def find_soffice() -> Path:
    """Findet den LibreOffice-Launcher.

    Auf Windows zwingend soffice.com (Konsolen-Launcher): nur der wartet auf das Ende
    der Konvertierung und liefert einen brauchbaren Exit-Code. soffice.exe kehrt sofort
    zurueck, die PDF ist dann noch nicht geschrieben.
    """
    override = os.environ.get("SOFFICE_BIN")
    if override and Path(override).exists():
        return Path(override)

    if sys.platform == "win32":
        for cand in WINDOWS_CANDIDATES:
            if cand.exists():
                return cand
        found = shutil.which("soffice.com") or shutil.which("soffice")
        if found:
            return Path(found)
        raise FileNotFoundError(
            "LibreOffice nicht gefunden. Installation:\n"
            "  winget install --id TheDocumentFoundation.LibreOffice -e\n"
            "Die --id mit -e ist wichtig - eine Namenssuche nach 'Libre' bietet auch "
            "LibreHardwareMonitor an."
        )

    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return Path(found)
    raise FileNotFoundError(
        "LibreOffice nicht gefunden. Installation:  sudo apt install libreoffice-writer"
    )


def to_pdf(src: Path, outdir: Path) -> Path:
    """Konvertiert eine Office-Datei nach PDF und gibt den PDF-Pfad zurueck."""
    soffice = find_soffice()
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    outdir.mkdir(parents=True, exist_ok=True)

    profile_uri = PROFILE_DIR.resolve().as_uri()
    cmd = [
        str(soffice),
        "--headless",
        f"-env:UserInstallation={profile_uri}",
        "--convert-to",
        "pdf",
        "--outdir",
        str(outdir),
        str(src),
    ]
    log.info("LibreOffice: %s -> PDF", src.name)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(
            f"soffice exit={proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        )

    pdf = outdir / (src.stem + ".pdf")
    if not pdf.exists():
        raise RuntimeError(
            f"Kein PDF erzeugt (erwartet: {pdf}).\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    return pdf


def to_pngs(
    pdf: Path,
    outdir: Path,
    dpi: int = 110,
    pages: list[int] | None = None,
    clip: tuple[float, float, float, float] | None = None,
) -> list[Path]:
    """Rendert PDF-Seiten als PNG.

    pymupdf statt pdftoppm/Poppler: keine Systemabhaengigkeit, und es kann Ausschnitte
    rendern (clip), um eine Fusszeile oder einen Tabellenkopf gross zu pruefen.
    """
    try:
        import pymupdf
    except ImportError as exc:
        raise ImportError("pymupdf fehlt. Installation:  pip install pymupdf") from exc

    doc = pymupdf.open(pdf)
    total = len(doc)
    written: list[Path] = []
    for idx, page in enumerate(doc, start=1):
        if pages and idx not in pages:
            continue
        rect = None
        if clip:
            r = page.rect
            x0, y0, x1, y1 = clip
            rect = pymupdf.Rect(
                r.x0 + x0 * r.width,
                r.y0 + y0 * r.height,
                r.x0 + x1 * r.width,
                r.y0 + y1 * r.height,
            )
        pix = page.get_pixmap(dpi=dpi, clip=rect)
        target = outdir / f"{pdf.stem}-seite-{idx:02d}.png"
        pix.save(target)
        written.append(target)
        log.info("  %s  (%dx%d px)", target.name, pix.width, pix.height)
    doc.close()

    if not written:
        raise ValueError(f"Keine Seite gerendert (PDF hat {total} Seiten, --pages={pages}).")
    return written


def parse_clip(value: str) -> tuple[float, float, float, float]:
    parts = [float(p) for p in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("--clip braucht 4 Werte: x0,y0,x1,y1 (0..1)")
    return tuple(parts)  # type: ignore[return-value]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="DOCX/ODT/PPTX/XLSX-Datei")
    ap.add_argument("--outdir", type=Path, default=None, help="Zielordner (Default: <quelle>/render)")
    ap.add_argument("--dpi", type=int, default=110, help="Aufloesung der PNGs (Default 110)")
    ap.add_argument("--pages", default=None, help="Nur diese Seiten, z.B. 1,3,7")
    ap.add_argument("--clip", type=parse_clip, default=None,
                    help="Ausschnitt als Anteile x0,y0,x1,y1 - z.B. 0,0.85,1,1 fuer die Fusszeile")
    args = ap.parse_args()

    src = args.source.resolve()
    if not src.exists():
        log.error("Datei nicht gefunden: %s", src)
        return 1

    outdir = (args.outdir or src.parent / "render").resolve()
    pages = [int(p) for p in args.pages.split(",")] if args.pages else None

    try:
        pdf = to_pdf(src, outdir)
        pngs = to_pngs(pdf, outdir, dpi=args.dpi, pages=pages, clip=args.clip)
    except Exception as exc:
        log.error("%s: %s", type(exc).__name__, exc)
        return 1

    print()
    print("Jetzt mit dem Read-Tool ansehen:")
    for p in pngs:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
