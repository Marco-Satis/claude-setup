# Anti-KI-Checkliste für sichtbare Ergebnisse (G247)

> Vorlage, gelesen nach einem Lauf von `node ~/.claude/scripts/visual_sheet.mjs` (nur netcup). Verbindlich bleibt
> `~/.claude/rules/design-qualitaet.md`. Bewegung bewertet zusätzlich `~/.claude/scripts/visual_sheet_checkliste.md`
> (M1–M12); hier steht Bewegung nur als A12/A13. Der blinde Zweitblick steht in `~/.claude/templates/design_zweitblick.md`.
> Stilquellen: impeccable und frontend-design. Zeilenangaben Stand 13.11.2026 (impeccable 3.9.1), nur als Quelle, sie
> verrutschen bei Plugin-Updates.

## Wertung

Jeder Punkt kommt ins Prüfprotokoll mit genau einem Wert:

- **ok**
- **Befund**: Bildpfad und Stelle, z. B. `A5 Befund: <outdir>/1280_light/full_01.png, Mitte: drei gleiche Karten`
- **n.a.**: nur mit einem Zitat aus dem Brief, das genau dieses Merkmal verlangt (frontend-design :45: „the brief's
  own words always win“)

**Hart (H):** ein Befund genügt zum Durchfallen. **Weich (W):** durchgefallen ist, wer drei weiche Befunde zugleich hat.

Prüfwege:
- **Bild:** Read auf die PNG, bei 390 und 1280 px; Details am Einzelbild in voller Auflösung.
- **Flag:** `visual_sheet.mjs --audit` bzw. `--motion` (beide in `--pruefen`).
- **Detektor:** der impeccable-Hook (meldet sich nach jedem Edit) oder `detect.mjs --json` (Exit 0 = sauber,
  Exit 2 = Funde).

Fixes wählen statt verbieten: Ein Fix ersetzt ein Merkmal durch eine begründete Entscheidung aus Inhalt, Brief oder
Vorbild, nicht durch das nächste Standardmuster.

## Die 15 Punkte

### A1 · Baukasten-Palette (H)
- **Frage:** Passt die Palette zu jeder beliebigen Seite der Kategorie?
- **Im Bild:** Grund großflächig Creme oder Sand (etwa `#F4F1EA`), Akzent Terrakotta nahe `#D97757`; oder getöntes
  Fast-Schwarz (`#0B0B0B`, `#111`) mit einem einzigen Neon-Akzent, der Buttons, Links und Leuchthöfe zugleich färbt.
- **Fix:** Palette aus Inhalt, Marke oder Vorbild ableiten: 4–6 benannte Werte mit Rolle (Grund, Fläche, Text, Akzent,
  Signal) im Zwei-Durchgänge-Plan. Akzent nur für Primäraktion und Status.
- **Prüfung:** Flag (berechnete Hintergrundfarbe im Band OKLCH L 0,84–0,97, C < 0,06, Ton 40–100), Bild.
  **Quelle:** frontend-design :39-40, :43; impeccable SKILL.md :72

### A2 · Reflex-Schrift (H)
- **Frage:** Ist die Schrift eine Gewohnheitswahl ohne Begründung im Brief?
- **Im Bild:** Inter, Space Grotesk, Geist, Outfit, Satoshi oder eine andere Schrift der impeccable-Ablehnungsliste;
  mehr als zwei Schriftfamilien; Fließtextzeilen über 80 Zeichen (bei 1280 px über die halbe Breite).
- **Fix:** Schrift nach Rolle wählen (Lesetext, Auszeichnung, Daten) und im Plan begründen, höchstens zwei Familien,
  Zeilenlänge mit `max-width` in `ch` auf 60–75 Zeichen begrenzen.
- **Prüfung:** Detektor `overused-font`, berechnete `font-family`, Bild.
  **Quelle:** impeccable reference/brand.md :28-40; frontend-design :19-23

### A3 · Template-Grammatik (H)
- **Frage:** Tragen Ordnungszeichen Information, oder sind sie Dekor?
- **Im Bild:** kleine gesperrte Versalienzeile (Eyebrow) über mehreren Überschriften; `01/02/03` ohne echte
  Reihenfolge; Metazeilen „A · B · C“; Überschriften „WORT — Fragment“; „→“ an Links und Buttons; ein einzelnes Wort
  der Headline farbig oder kursiv.
- **Fix:** Eyebrows streichen oder nur dort lassen, wo sie navigieren; Nummern nur bei echter Abfolge; Headline als
  ganzer Satz ohne Hervorhebungswort; Pfeile nur für „weiter“ in Abläufen.
- **Prüfung:** Flag (Eyebrow-Zähler), Bild.
  **Quelle:** frontend-design :25-30, :43; impeccable SKILL.md :90-91

### A4 · Hero nach Rezept (H)
- **Frage:** Folgt der Einstieg einem Standardrezept statt dem Inhalt?
- **Im Bild:** große Zahl mit kleinem Label, Stat-Reihe und Verlaufsakzent; oder Text links und Bild rechts mit zwei
  Buttons, obwohl das Bild nichts zeigt, was der Text braucht. Bei 390 px rutscht das Bild nur unter den Text.
- **Fix:** Einstieg aus der Hauptaufgabe der Seite ableiten (Werkzeug: direkt das Werkzeug; Editorial: Text; Handel:
  Produkt). Für 390 px eine eigene Reihenfolge festlegen statt die Desktopfassung zu stapeln.
- **Prüfung:** Bild bei 390 und 1280.
  **Quelle:** impeccable SKILL.md :88; frontend-design :17; design-html SKILL.md :580

### A5 · Kartenbaukasten (H)
- **Frage:** Besteht der Inhalt aus austauschbaren Karten?
- **Im Bild:** gleich große Karten aus Icon, Titel und Text in Reihe; ein Radius auf allem; überall derselbe weiche
  Schatten (`rgba(0,0,0,.1)`); Verlaufsflächen als Deko. Im Graustufen-Bogen sehen alle Flächen gleich aus.
- **Fix:** nach Gewicht ordnen (ein großes Element, mehrere kleine; Liste oder Tabelle für Vergleichbares); Radius und
  Schatten nach Ebene stufen; Deko-Verläufe streichen.
- **Prüfung:** Bild, Graustufen-Bogen.
  **Quelle:** impeccable SKILL.md :89; frontend-design :42

### A6 · Effekte ohne Funktion (H)
- **Frage:** Gibt es Effekte, die nichts tragen?
- **Im Bild:** farbiger Seitenstreifen an Karten oder Hinweisen (`border-left/right` > 1 px); Verlaufstext; milchige
  Glasflächen über Unschärfe; Körnung (Grain); Mesh-Verläufe oder farbige Leuchthöfe als Füller.
- **Fix:** streichen. Hierarchie über Größe, Gewicht, Abstand und Fläche lösen; Status als Symbol oder Text plus
  Farbe statt Streifen.
- **Prüfung:** Detektor (`side-tab`, `gradient-text`), Bild.
  **Quelle:** impeccable SKILL.md :85-87

### A7 · Platzhalter statt Inhalt (H)
- **Frage:** Steht irgendwo Füllmaterial statt Inhalt?
- **Im Bild:** Lorem ipsum; picsum- oder Zufallsbilder; example.com; „John Doe“; runde Fantasiezahlen (99,99 %,
  „10x“); Links ohne Ziel (`href="#"`); leere Bildflächen; Linien-Icons aus Lucide oder Heroicons als einzige
  Bildsprache.
- **Fix:** Dummy-Daten, die nach dem Fach aussehen (unrunde Werte, echte Einheiten, erfundene Namen ohne reale
  Person); Bildfläche weglassen statt Platzhalter; Icons nur als Bedienzeichen, eigene Bildsprache aus dem Inhalt
  (Diagramm, Ausschnitt, Illustration).
- **Prüfung:** Flag (picsum, example.com, Lorem, `href="#"`, Icon-Klassen), Bild.
  **Quelle:** impeccable reference/craft.md :85; Juror-Urteil 1, Nr. 5

### A8 · Floskeltext (W)
- **Frage:** Klingt der Text nach Werbeprosa ohne Aussage?
- **Im Bild:** „Elevate“, „seamless“, „unlock“, „empower“, „next-level“ und deutsche Gegenstücke („nahtlos“, „auf
  das nächste Level“); Buttons „Submit“, „Learn more“, „Mehr erfahren“; dieselbe Handlung heißt im Ablauf mal so,
  mal anders.
- **Fix:** sagen, was passiert (Verb und Objekt: „Bericht exportieren“); eine Bezeichnung je Handlung durchziehen;
  bei ganzen Seiten `design:ux-copy`.
- **Prüfung:** Flag (Wortliste), Lesen.
  **Quelle:** frontend-design :63-71

### A9 · Satzfehler (W)
- **Frage:** Ist der Satz typografisch sauber?
- **Im Bild:** gerade Anführungszeichen statt „…“; `...` statt `…`; Bindestrich statt Gedankenstrich; ein einzelnes
  Wort in der letzten Headline-Zeile; unausgeglichen umbrochene Überschriften; Tabellenziffern im Fließtext.
- **Fix:** typografische Zeichen setzen; `text-wrap: balance` für Überschriften, `text-wrap: pretty` für Absätze;
  `font-variant-numeric: tabular-nums` nur in Tabellen und Zahlenspalten.
- **Prüfung:** Flag (`...`, gerade Anführungszeichen), Bild.
  **Quelle:** frontend-design :21 (Bringhurst); Juror-Urteil 1, Nr. 5

### A10 · Keine Hierarchie (W)
- **Frage:** Gibt es eine klare Rangfolge?
- **Im Bild:** alles gleich laut; überall gleiche Abstände; Radius und Schatten nicht nach Ebene gestuft; mehr als
  ein „mutiges“ Element, die um den Blick konkurrieren.
- **Fix:** Skala mit deutlichen Sprüngen (Größe, Gewicht, Abstand); Abstand zwischen Gruppen größer als innerhalb;
  ein einziger mutiger Moment. Im Graustufen-Bogen fällt der Blick zuerst auf Hauptinhalt und Primäraktion.
- **Prüfung:** Bild, Graustufen-Bogen.
  **Quelle:** frontend-design :57-59

### A11 · Markentest fällt durch (H)
- **Frage:** Könnte die Seite mit abgedecktem Logo und abgedeckter Navigation jedem Anbieter der Kategorie gehören?
- **Im Bild:** ohne Kopfzeile bleibt nichts Eigenes; Thema und Palette sind aus der Kategorie allein erratbar
  (1. Ordnung, etwa Finanzen blau) oder aus „Kategorie minus Klischee“ (2. Ordnung, das erwartbare Gegenteil).
- **Fix:** ein eigenes, aus dem Inhalt gewonnenes Merkmal setzen (Bildsprache, Raster, Datendarstellung, Schriftrolle
  oder Bewegungs-Signatur); ein dominantes Vorbild aus dem Fach statt eines Mittelwerts. Maßstab: gleichwertig,
  nicht verwechselbar.
- **Prüfung:** Bild, Zweitblick.
  **Quelle:** impeccable SKILL.md :94-101

### A12 · Bewegungs-Reflex (H)
- **Frage:** Ist die Bewegung ein Standardpaket?
- **Im Bild (Bögen):** jede Sektion blendet gleich ein und steigt hoch; jede Karte hebt sich bei Hover; Elemente
  wachsen aus dem Nichts (`scale(0)`); Eintritte starten langsam (ease-in); Überschwingen oder Federn; mindestens 70 %
  der Animationen mit gleichem Paar aus Dauer und Kurve; `transition: all`.
- **Fix:** Dauer und Kurve nach Rolle (M10); Eintritt mit ease-out aus Deckkraft und kleiner Verschiebung oder
  `scale(0.95)`; Hover nur an klickbaren Elementen; `transition` mit konkreten Properties; ein Eintrittsmoment statt
  Einblendung je Sektion.
- **Prüfung:** Flags `--motion`.
  **Quelle:** frontend-design :32; impeccable reference/animate.md :9, :183-190; SKILL.md :55-59

### A13 · Bewegung ohne Zweck (W, über 5 s ohne Pause H)
- **Frage:** Hat jede Dauerbewegung eine Bedeutung für den Status?
- **Im Bild (Echtzeitbogen):** pulsierende Punkte, Schimmerstreifen, Partikel, Text-Scramble oder Laufband, auch
  im Ruhezustand. Hart, wenn es länger als 5 s neben Inhalt läuft und sich nicht pausieren oder stoppen lässt.
- **Fix:** streichen oder an einen Status koppeln (Puls nur während „läuft“) und danach stoppen; über 5 s nur mit
  Pause- oder Stopp-Schalter und Reduced-Motion-Variante.
- **Prüfung:** Flag `endless-loop` (steht bei jeder Schleife über 5 s, Pause-Kandidaten nur in der Evidenz), Bogen;
  ein Pause-Schalter zählt erst, wenn seine Wirkung im Bogen belegt ist.
  **Quelle:** impeccable animate.md :187; WCAG 2.2 SC 2.2.2

### A14 · Qualitätsboden fehlt (H)
- **Frage:** Hält die Seite die Grundqualität?
- **Im Bild:** horizontales Scrollen oder abgeschnittene Elemente bei 390 px; leere Flächen im `--nojs`-Lauf oder vor
  dem Reveal; kein sichtbarer Tastaturfokus; Reduced-Motion-Lauf bewegt sich wie der Normallauf; blasser Text unter AA.
- **Fix:** fließende Breiten (`min()`, `clamp()`, Umbruch) statt fester Maße; Inhalt im HTML sichtbar, Reveal nur als
  Zugabe; `:focus-visible` mit mindestens 3:1; `@media (prefers-reduced-motion: reduce)`; Kontrast 4,5:1 für Text,
  3:1 für Bedienelemente.
- **Prüfung:** Läufe bei 390 px, `--nojs`, `--reduced-motion`; axe.
  **Quelle:** frontend-design :59; impeccable SKILL.md :58-60, :92; WCAG 2.2 SC 1.4.3, 1.4.11, 2.4.7

### A15 · Gleich wie die letzten eigenen Arbeiten (W)
- **Frage:** Stimmen Schrift, Palette und Bewegungs-Signatur mit einem der letzten 3 Logbuch-Einträge überein?
- **Im Bild:** Vergleich mit den Einträgen aus `wz find design logbuch`.
- **Fix:** mindestens eine der drei Achsen bewusst anders wählen und im Plan begründen.
- **Prüfung:** `wz find design logbuch`. Ist das Logbuch noch leer: „ok, Logbuch leer“.
  **Quelle:** frontend-design :59 („Human creatives have memory“)

## Pflege

Vierteljährlich aus den Indizien des Zweitblicks (Kennung „neu“) und den Begründungen der Tester nachziehen. Ein
Merkmal, das zweimal neu auftaucht, ersetzt den schwächsten Punkt. Die Liste bleibt bei höchstens 15 Punkten; Punkte
werden ersetzt, nicht angehängt. Häufungsregel „eins hart oder drei weich“ aus G247 E1.
