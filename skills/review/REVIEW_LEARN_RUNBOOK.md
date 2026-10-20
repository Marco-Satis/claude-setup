# review-weekly-learn — Runbook (Stufe 3 der Selbstlern-Schleife)

> Wird von der Scheduled-Task `review-weekly-learn` ausgeführt (wöchentlich, beim
> nächsten App-Start nach Fälligkeit). Self-contained — der Task-Agent folgt diesem
> Runbook ohne weiteren Kontext.

## Zweck

Konsolidiert den verifizierten Outcome-Ledger des `/review`-Skills zu
Verbesserungs-Vorschlägen. **Auto-Apply nur auf die gelernte Daten-Schicht;
Kern-SKILL.md-Änderungen gehen als Idee an des Nutzers Problem-Tracker** — nie
automatisch editiert (Drift- + Bloat-Schutz für den frisch verschlankten Kern).

## Schritte

### 1. Ledger konsolidieren

```bash
python ~/.claude/scripts/review_learn.py consolidate
```

Das (a) baut `review_learned.json` frisch (= Auto-Apply auf die gelernte Schicht,
die Phase 0 beim nächsten Review liest) und (b) schreibt
`~/.claude/skills/review/review_proposals.json` mit `core_skill_proposals`.

Bei `total_outcomes: 0` → noch keine Lern-Daten → Runbook hier beenden, kurze
Notiz „Ledger leer, nichts zu konsolidieren". Kein Task-Fehler.

### 2. Vorschläge sichten

`review_proposals.json` → Liste `core_skill_proposals`, je Eintrag:
- `kind`: `add-reviewer-check` | `add-severity-anchor` | `flag-hotspot`
- `target`: wo im Skill (Phase / KANON K2) bzw. „Projekt-Hinweis"
- `evidence`: die Beleg-Zahl (z.B. „3/4 FP", „2x übersehen", „3 Reviews")
- `proposal`: konkreter Text-Vorschlag

### 3. Pro Vorschlag handeln

| kind | Aktion |
|---|---|
| `add-reviewer-check` | **Idee** in den Problem-Tracker (der Nutzer baut den Check in Phase 2/5.6 ein). Hoher Wert — schließt eine bewiesene Blind-Spot-Lücke. |
| `add-severity-anchor` | **Idee** in den Tracker (K2-Anker um stabiles FP-Muster ergänzen → weniger Lärm). |
| `flag-hotspot` | **Idee** in den Tracker als Refactor-Kandidat für die genannte Datei (kein Skill-Edit). |

Idee loggen (zentral, type=idea):

```bash
python ~/.claude/scripts/problem.py add --type idea --severity LOW \
  --project claude-setup --source review-learn \
  --location "skills/review/SKILL.md" \
  --title "<kind>: <pattern/file> (<evidence>)" \
  --fix "<proposal-Text>"
```

ID ist content-stabil → wöchentliches Re-Loggen dupliziert nicht, aktualisiert.

### 4. KEINE Kern-Edits

Den `SKILL.md`-Kern NICHT automatisch ändern. Die gelernte Schicht
(`review_learned.json`) wirkt bereits über Phase-0-Recall ohne Kern-Edit — das ist
das „selbstständig besser werden" ohne Drift-Risiko. Kern-Regeln bleiben des Nutzers
Entscheidung.

### 5. Kurz-Report

Eine knappe Notiz: wie viele Outcomes im Ledger, wie viele Vorschläge erzeugt,
wie viele als Idee geloggt. Bei ≥1 `add-reviewer-check` (Blind-Spot) das
hervorheben — das ist der wertvollste Lern-Output.

## Guardrails (warum das sicher ist)

- `consolidate` liest nur den **verifizierten** Ledger (Provenance-Gate in
  `review_learn.py` ließ rohe Findings gar nicht erst rein).
- Auto-Apply ausschließlich auf Daten (`review_learned.json`), nie auf Kern-Text.
- Stufe-3-Schwellen sind strenger als Recall (`PROPOSE_*`) → nur belastbare
  Muster werden überhaupt Vorschlag.
- Alles, was den Kern berührt, ist ein Tracker-Idea, kein Edit.
