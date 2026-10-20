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

## Abgrenzung

- Gamebots: [gamebot-reuse-first](gamebot-reuse-first.md) konkretisiert Stufe 4 für `_botcore/` und geht dort vor.
- Gilt nicht für Wegwerf-Tests, Attrappen und einmalige Diagnose-Snippets.
- Eine nachweislich bessere Alternative bleibt erlaubt: als 1-Zeiler-Tradeoff flaggen, der Nutzer entscheidet.
