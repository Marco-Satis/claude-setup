# Reuse-Leiter vor neuem Code (Global Rule)

> der Nutzer-Entscheid 2026-09-30, TikTok-Auswertung A1 #6 (Idee „vier Pflichtfragen" bzw. Ponytail,
> bewusst als Rule statt als Tool übernommen). Lücke: `/gate` und `/review` greifen erst im
> Review, nicht beim Schreiben.

## Kernregel

Bevor neuer Code, ein Helper, Skript, Hook oder eine Abhängigkeit entsteht, der Reihe nach
fragen. Ein Nein bei 1 oder 2 heißt: nicht bauen. Auch wenn 3 reicht, wird 4 geprüft:

1. **Ist es nötig?** Welches konkrete Problem löst es? Ohne Antwort: nicht bauen.
2. **Ist es heute nötig?** Kein Vorbau für hypothetische Fälle.
3. **Reicht die stdlib oder eine vorhandene Abhängigkeit?** Keine neue Library für wenige Zeilen.
4. **Gibt es ein natives Feature?** CLI-Builtin, Framework-Funktion, vorhandener Skill oder
   Script. Bei Setup-Arbeit gehören dazu `~/.claude/scripts/`, `~/.claude/hooks/` und die
   Skill-Liste (unvollständig, siehe [native-skills-erkennung](native-skills-erkennung.md)).
5. Erst dann das **Minimum** bauen.

## Bestand zuerst, auch vor der Antwort (der Nutzer 2026-11-16, 21:32)

„Das gilt allgemein wieder projektübergreifend: immer erst den Bestand checken, was da ist, bevor man antwortet, um
erstmal zu wissen, was überhaupt da ist und was für Möglichkeiten es gibt.“ Anlass: Auf „Memories werden nicht aktiv
geschrieben“ baute die Zentrale einen neuen Stop-Hook, bevor sie die vier vorhandenen Memory-Hooks und die live
geschaltete Merkliste (Phase M) gesichtet hatte; der Nutzer musste nachfragen.
1. Vor jeder Antwort, Bewertung oder Lösung zu einem Thema erst den Bestand erheben: verdrahtete Hooks
   (`settings.json`), Skripte, Skills, Rules, Routinen, Flags, `wz find`, laufende Dienste und Projektdateien.
2. Die Antwort nennt zuerst, was es schon gibt und was davon fehlt oder nicht greift; erst danach kommt ein Vorschlag.
3. Gilt für alle Sessions und Projekte, auch unter Zeitdruck und für scheinbar kleine Fragen.

## Abgrenzung

- Gamebots: [gamebot-reuse-first](gamebot-reuse-first.md) konkretisiert Stufe 4 für `_botcore/` und geht dort vor.
- Gilt nicht für Wegwerf-Tests, Attrappen und einmalige Diagnose-Snippets.
- Eine nachweislich bessere Alternative bleibt erlaubt: als 1-Zeiler-Tradeoff flaggen, der Nutzer entscheidet.
