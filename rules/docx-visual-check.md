# Office-Dokumente vor der Übergabe selbst ansehen (Global Rule)

> Erarbeitet 2026-08-25 in der NTE-Session (PC), auf netcup verifiziert am selben Tag.
> Auto-applied bei jeder Arbeit an `.docx`, `.odt`, `.pptx`, `.xlsx` — Erstellen, Umbauen,
> Formatieren.

## Kernregel

**Wer ein Office-Dokument baut, prüft es vor der Übergabe optisch selbst.** Nicht die
XML-Struktur zählen, sondern die gerenderte Seite ansehen.

Das ist kein Stil-Anspruch, sondern deckt eine Fehlerklasse ab, die strukturell unsichtbar
ist. Beim ersten selbst gerenderten Blick fielen sofort drei Layoutfehler auf, die jede
XML-Prüfung passiert hätten: zwei umbrechende Tabellenköpfe („Slots" wurde zu „Slot/s",
„Rang" zu „Ran/g") und eine Fußzeile mit gemischten Schriftgrößen. Tabellen zählen und
Felder kontrollieren beantwortet die Frage „ist es drin", nie die Frage „sitzt es".

## Der Weg

Ein Aufruf, auf beiden Maschinen identisch:

```bash
python ~/.claude/scripts/docx_render.py bericht.docx
```

Das Skript konvertiert per LibreOffice nach PDF, rendert die Seiten mit `pymupdf` als PNG
und gibt die Pfade aus. **Danach die PNGs mit dem Read-Tool ansehen** — erst dann ist die
Prüfung erfolgt.

Nützliche Schalter:

| Schalter | Zweck |
|---|---|
| `--pages 1,3` | nur bestimmte Seiten (spart Zeit bei langen Dokumenten) |
| `--dpi 150` | höhere Auflösung für Detailfragen |
| `--clip 0,0.85,1,1` | Ausschnitt als Anteile `x0,y0,x1,y1` — hier: nur die Fußzeile, groß |

Der Ausschnitt ist der Weg, um einen einzelnen Tabellenkopf oder eine Fußzeile genau zu
prüfen, statt eine 110-dpi-Vollseite zu deuten.

## Voraussetzungen je Maschine

Installierte Pakete syncen nicht — jede Maschine braucht sie einzeln.

| | PC (Windows) | netcup (Linux) |
|---|---|---|
| LibreOffice | 26.2.5.2, `C:\Program Files\LibreOffice\program\soffice.com` | 7.3.7.2, `/usr/bin/soffice` |
| pymupdf | installiert | 1.28.0 |
| Stand | verifiziert 2026-08-25 | verifiziert 2026-08-25 (End-to-End) |

Nachinstallieren:

```bash
winget install --id TheDocumentFoundation.LibreOffice -e   # Windows
sudo apt install libreoffice-writer                        # Linux
pip install pymupdf                                        # beide
```

⚠ Die `--id` mit `-e` ist auf Windows wichtig. Eine Namenssuche nach „Libre" bietet mehrere
Treffer an; beim ersten Versuch landete versehentlich **LibreHardwareMonitor** auf dem
Rechner.

## Fünf Fallstricke

1. **Auf Windows `soffice.com`, nicht `soffice.exe`.** Nur der Konsolen-Launcher wartet auf
   das Ende der Konvertierung und liefert einen brauchbaren Exit-Code. `soffice.exe` kehrt
   sofort zurück — die PDF ist dann noch nicht geschrieben.
2. **`-env:UserInstallation=...` ist Pflicht.** Ohne eigenes Profil hängt der headless-Aufruf
   am Profil-Lock, sobald parallel eine LibreOffice-Oberfläche offen ist. Das Skript setzt
   dafür `~/.claude/.cache/lo_profile_claude`.
3. **Das `docx`-npm-Paket ist NICHT vorinstalliert**, obwohl die Skill-Doku „docx is
   preinstalled" behauptet. `npm install docx` war nötig. Die Doku-Zeile stimmt hier nicht.
4. **`scripts/office/soffice.py` aus dem docx-Skill ist Unix-only.** Unter Windows bricht es
   mit `AttributeError: module 'socket' has no attribute 'AF_UNIX'` ab. Auf netcup läuft es.
   `docx_render.py` deckt beide Seiten ab und ist deshalb der Standardweg.
5. **`pdftoppm` (Poppler) fehlt auf dem PC.** `pymupdf` ersetzt es vollständig, ohne
   Systemabhängigkeit, und kann zusätzlich Ausschnitte rendern.

Ein sechster, beim netcup-Test aufgetaucht: **HTML → DOCX braucht einen expliziten
Filternamen** (`--convert-to 'docx:MS Word 2007 XML'`), sonst schlägt die Konvertierung
still fehl. Der eigentliche Weg DOCX → PDF ist davon nicht betroffen.

## Zwei Erkenntnisse für docx-js

- **Seitenzahl-Feldwerte erben die Schriftgröße vom `TextRun` nicht.**
  `new TextRun({ children: [PageNumber.CURRENT], size: 17 })` ergibt gemischte Größen.
  Lösung: eigene `paragraphStyles`-Formatvorlage mit `run: { size }` anlegen und den Absatz
  per `style:` daran hängen.
- **Schmale Tabellenspalten brauchen kleinere Zellränder**, sonst brechen kurze Köpfe wie
  „Rang" um. Bewährt: `< 800 DXA → 60`, `< 1100 → 90`, sonst `130`.

## Abgrenzung

| Situation | Werkzeug |
|---|---|
| Selbst gebautes Office-Dokument optisch prüfen (diese Regel) | `docx_render.py` + Read-Tool |
| Fremdes PDF lesen/ausfüllen/zusammenführen | `PDF_Tools`-MCP bzw. `anthropic-skills:pdf` |
| Markdown → PDF für der Nutzer | bestehender md2html/Chrome-headless-Weg |
