---
name: gate
version: 1.1.0
last-reviewed: 2026-09-30
description: Quality-Gate für abgeschlossene Änderungssätze — deterministische Orakel-Kette (lint/typecheck/test/build) vor jeder LLM-Bewertung, danach Slop-Pass gegen die 15 belegten AI-Fehlermodi, semantischer Review und Deployment-Preflight. Schreibt ein maschinenlesbares `verdict.json` mit work-sha-Caching und läuft eine gegatete Fix-Schleife bis grün oder Budget erschöpft. Erkennung über kostenlose Bridges, Fixes über das starke Modell. NICHT für einzelne Edits (dafür /quick-review) und NICHT in Loop-Sessions.
when_to_use: gate, quality gate, änderungssatz abnehmen, ist das fertig, vor dem merge prüfen, ai-slop prüfen, code guard, gegatete abnahme, deterministische prüfung vor review
argument-hint: 'Optional Pfad/Scope — Default: uncommitted Änderungen (`git diff`). `--quick` überspringt Build+Review, `--force` ignoriert den Cache, `--dual` = Zweifach-Abnahme Claude+Codex nur für kritische Lieferungen.'
allowed-tools: Read Grep Glob Bash Edit Write Task
userInvocable: true
---

# /gate — Abnahme eines Änderungssatzes

Zweck: einen **abgeschlossenen Änderungssatz** gegen harte Kriterien abnehmen, statt ihn für fertig zu erklären. Das Gate hört erst auf, wenn objektive Signale grün sind — nicht, wenn eine Bewertung zufrieden klingt.

**Grundsatz (die eine Regel, die alles trägt):** eine LLM-Bewertung überzeugt sich selbst, ein fehlgeschlagener Test nicht. Deshalb laufen **deterministische Stufen zuerst und blockierend**; die semantischen Stufen kommen erst dran, wenn die deterministischen grün sind. Umgekehrt wäre es teuer und wertlos.

**Abgrenzung:** einzelne Datei oder schneller Diff-Check → `/quick-review`. Ganzes Repo / Quartals-Audit → `/full-audit`. Reine Security-SAST → `/security-audit`. `/gate` ist die Abnahme eines Änderungssatzes und ruft `/review` intern als eine Stufe von mehreren.

## Nicht anwenden

- **In Loop-Sessions (`/loopmode`) nie.** Das Gate frisst genau den Kontext, den die Compact-Stufenregel schützt. Prüfen: existiert `LOOP_RUN.flag` im Projekt oder ist die Session in `state/loopmode_sessions.json` markiert → sofort abbrechen mit Hinweis.
- Nicht auf jeden Edit. Ein Durchlauf kostet real 20–60 Minuten Wanduhr (nicht Tokens). Das ist der ehrliche Preis.

---

## Phase 0 — Scope und Vorprüfung

1. **Loop-Guard** (siehe oben) — bei Treffer abbrechen.
2. **Git-Repo:** `git rev-parse --git-dir` — vorhanden → Diff-Modus. Nicht vorhanden → **Pfad-Modus** (siehe Punkt 3), kein Abbruch.
3. **Scope bestimmen:** Argument = Pfad → dieser Pfad. Kein Argument → Vereinigung von `git diff --cached --name-only`, `git diff --name-only` und untracked, nicht ignoriert; NUL-getrennt verarbeiten.
   **Rauschen vorher abziehen** (sonst nimmt das Gate Backups ab — im ersten Testlauf 2026-07-29 genau so passiert):
   ```bash
   git status --porcelain | grep -vE '\.bak(\.|$)|sync-conflict|/__pycache__/|\.pyc$|^\?\? \.(venv|superpowers|claude/gate)/'
   ```
   Nach dem Filter leer → **„nichts abzunehmen", Ende.** Ein Scope aus reinen `.bak`-Dateien ist kein Änderungssatz.

   **`sync-conflict` gehört zwingend in den Filter — und zusätzlich gemeldet.** Im Dry-Run lagen **37 Konfliktdateien vom 25.07. im aktiven Bot-Quellbaum**, darunter sechs `.py` neben ihren Originalen (`web/app.sync-conflict-….py`, `bots/recon_bot.sync-conflict-….py`, …). Syntaktisch gültig, importierbar, ältere Fassung — `web/app.sync-conflict-….py` fehlte der Channel-Router. Jede Konfliktkopie im Scope ist ein **eigener HIGH-Befund** („Konfliktkopie im Quellbaum"), nicht bloß Filterrauschen: sie wird nicht abgenommen, aber gemeldet.

   **Ohne Git-Repo** (des Nutzers gesyncte Projekt-Spiegel haben kein `.git` — Syncthing schließt es aus): kein Abbruch, sondern Pfad-Modus. Scope = das übergebene Verzeichnis, work-sha = sha256 über die sortierten Dateiinhalte des Scope, Diff-basierte Eingrenzung entfällt. Ein Gate, das an genau den Projekten scheitert, die synchronisiert werden, ist nutzlos.
4. **work-sha berechnen** — Index und Arbeitsbaum getrennt erfassen. Der Fingerabdruck ist vorerst nur Diagnose; er bindet Prüfmodus, externe Prüfkonfiguration und Toolchain nicht vollständig. Ausgabe ausschließen. Bei fehlendem HEAD: kein Cache, Diagnose als nicht unterstützt kennzeichnen.
   ```bash
   set -euo pipefail
   { git rev-parse --verify HEAD
     git diff --no-ext-diff --no-textconv --cached --binary -- . ':(exclude).claude/gate/**'
     git diff --no-ext-diff --no-textconv --binary -- . ':(exclude).claude/gate/**'
     git status --porcelain --untracked-files=all -- . ':(exclude).claude/gate/**'
     while IFS= read -r -d '' file; do
       printf '%s\0' "$file"
       sha256sum -- "$file"
     done < <(git ls-files -o --exclude-standard -z -- . ':(exclude).claude/gate/**' | LC_ALL=C sort -z)
   } | sha256sum | cut -c1-16
   ```
   Fingerabdruckfehler blockieren die Diagnose; daraus niemals PASS ableiten.
5. **Cache vorerst deaktiviert:** Kein gespeichertes PASS wiederverwenden, auch nicht bei gleicher workSha. Jeden angeforderten Modus und Scope frisch prüfen. `--force` ist damit redundant. Alte Verdict-Dateien sind historische Berichte. Cache erst nach separatem Vertrag für Scope, Modus, Stufen, Konfigurations- und Toolchain-Versionen wieder aktivieren.
6. **Toolchain auflösen** (einmal, Ergebnis in `.claude/gate/config.json` merken).
   **`command -v` allein reicht nicht** — Projekt-Tools liegen meist im venv, nicht auf `PATH`
   (Testlauf 2026-07-29: `pytest` fehlte auf `PATH`, lag aber in `.venv/bin/` und lief über
   `python3 -m pytest`). Auflösungs-Reihenfolge je Tool, erster Treffer gewinnt:
   1. `./.venv/bin/<tool>` bzw. `./venv/bin/<tool>` · `./node_modules/.bin/<tool>`
   2. `python3 -m <tool> --version` (bzw. `npx --no-install <tool>`)
   3. `command -v <tool>`

   Python → `ruff`/`mypy`/`pytest` · Node → `eslint`/`tsc`/`vitest|jest` · Shell → `shellcheck`.

   **Nicht auflösbar ist nicht gleich „übersprungen":**
   | Lage | Folge |
   |---|---|
   | Tool nicht auflösbar, im Projekt auch nicht deklariert | Stufe `SKIPPED`, kein Blocker |
   | Tool in `requirements.txt`/`pyproject.toml`/`package.json` deklariert, aber nicht auflösbar | **`SETUP`-Fehler, blockierend** — die Umgebung ist kaputt, nicht der Code |
   | `tests/` existiert, aber kein Test-Runner auflösbar | **`SETUP`-Fehler, blockierend** |

   Ein Gate, das mangels Werkzeug alles überspringt und trotzdem grün meldet, ist schlimmer als kein Gate. `SETUP` erscheint im Verdikt als `failingGate`, nicht als `PASS`.

## Phase 1 — Deterministisches Orakel (blockierend)

Reihenfolge **schnell → langsam, Abbruch beim ersten Fehler**. Keine LLM-Bewertung in dieser Phase.

| # | Stufe | Quelle | Cap |
|---|---|---|---|
| 1 | lint | `ruff check` / `eslint` / `shellcheck` | 120 s |
| 2 | typecheck | `mypy` / `tsc --noEmit` | 180 s |
| 3 | test | `pytest -q` / `vitest run` — auf den Scope eingegrenzt, wo das Kommando es kann | 300 s |
| 4 | build | projektabhängig; nur wenn definiert | 600 s |

Fehlschlag → **sofort Phase 5** (Fix-Schleife) mit `failingGate` und den letzten ~40 Zeilen Ausgabe als `evidence`. Nicht weiterprüfen: ein roter Test macht jede Stilkritik gegenstandslos.

**Rückgabewert vor jeder Pipe abgreifen.** `pytest … | tail` liefert den Status von `tail`, nicht von pytest — im Testlauf 2026-07-29 meldete das `rc=0` bei tatsächlichem `rc=2`. Immer:
```bash
out=$(timeout 300 <cmd> 2>&1); rc=$?
```
Ein Gate, das den Exit-Code der falschen Prozessstufe liest, meldet grün auf rot.

Timeout (rc 124) zählt als Fehlschlag mit `TIMEOUT after Ns` vor der Evidenz.

## Phase 2 — Slop-Pass (billig)

Erst wenn Phase 1 grün ist. Referenz: `~/.claude/skills/_shared/ai-failure-modes.md` — 15 belegte LLM-Fehlermodi, jeder mit Regel.

Ausführung **über eine kostenlose Bridge**, nicht über das teure Modell:
- `gemini-bridge` bei größeren Diffs (großes Fenster),
- `local-bridge` bei kleinen Diffs oder wenn Gemini nicht verfügbar ist.

**Exakter Aufruf** (der Prompt steht positionell nach `--`, es gibt **kein** `--prompt`-Flag; `--mode` kommt aus der festen Liste `offload|triage|second-opinion|fallback|other`):
```bash
python3 ~/.claude/scripts/ollama_call.py --mode triage --model qwen2.5:7b --label gate-slop -- "<prompt>"
python3 ~/.claude/scripts/gemini_call.py --mode triage --label gate-slop -- "<prompt>"
```
Auf netcup verfügbar: Ollama mit `qwen2.5:7b` und `qwen2.5:3b`, `gemini` auf `PATH`. Antwortet die Bridge nicht, wird die Stufe `SKIPPED` — **nicht** ersatzweise vom teuren Modell gemacht, sonst ist der Kostenvorteil weg.

Prompt an die Bridge: Diff + die Fehlermodus-Liste, Auftrag = **nur belegte Treffer melden**, je mit Modus-Nummer, Datei:Zeile und einem Satz Begründung. Keine Stil-Meinungen, keine Neuformulierungen.

### 2a — Mechanischer Vorlauf (zuerst, ohne Modell)

Der größere Teil der Fehlermodi ist per `grep`/AST belegbar. **Testlauf 2026-07-29 an echtem Legacy-Code:** `qwen2.5:7b` meldete eine frei erfundene Fundstelle (ein `discord.Embed(...)`-Konstruktor als „Catch-all-Exception") und übersah dabei zwei echte `except Exception:` — eines davon mit `pass`, eines, das den Fehler als Erfolgsmeldung ausgibt. `grep` fand beide in einer Sekunde. Ein 7B-Modell ist kein verlässlicher Detektor.

```bash
grep -nE 'except\s*(Exception|BaseException)?\s*:' <scope>     # #1  danach: pass / return None / Erfolgsmeldung?
grep -nEi 'mock|dummy|fake|stub|placeholder' <scope>           # #12 im Produktivpfad
grep -nE 'TODO|FIXME|NotImplementedError' <scope>              # #11
```
Importe (#6) gegen die tatsächlich installierten Pakete prüfen — `pip list` / `package.json`, nicht gegen Erinnerung.

**Zwei Filter, ohne die der Vorlauf unbrauchbar wird** (Dry-Run an 203 Dateien aktivem Bot-Code, 2026-07-29):

- **Dokumentierte Unterdrückung ist kein Befund.** Beide gefundenen `except: pass` trugen `# noqa: BLE001 — CancelledError o.ae. erwartet`. Wer eine bewusste, begründete Ausnahme als Fund meldet, erzieht zum Wegklicken aller Funde. Zeilen mit `# noqa`, `# type: ignore` oder einem erklärenden Kommentar in derselben oder der Vorzeile: überspringen.
- **`return None` nur im `except`-Kontext.** Als freies Muster lieferte es **451 Treffer in 203 Dateien** — mehr Rauschen als alle anderen Detektoren zusammen. Relevant ist es ausschließlich innerhalb eines `except`-Blocks (Fehler wird zu einem gültig aussehenden Rückgabewert). Per AST prüfen, nicht per `grep`.

Grundregel für jeden Detektor: liefert er über den ganzen Scope mehr als ~5 % der Zeilen, ist er falsch geschnitten und wird nicht gemeldet, sondern korrigiert.

### 2b — Modell-Pass (nur der Rest)

An die Bridge geht **nur**, was mechanisch nicht entscheidbar ist: **#13 plausibel-aber-falsch**, **#3 verfrühte Abstraktion**, **#10 Inkonsistenz zum Umfeld**. Die Treffer aus 2a werden mitgegeben, damit sie nicht doppelt gemeldet werden.

**Modell-Treffer ohne Zeilenbeleg werden verworfen.** Prüfen, ob die genannte Zeile das behauptete Muster überhaupt enthält — sonst ist es eine Halluzination, und eine erfundene Fundstelle kostet mehr Zeit als sie spart.

Treffer aus 2a und 2b sind **Befunde, keine Blocker** — sie gehen in Phase 3 als Vorlage ein.

## Phase 3 — Semantischer Review

`/review` auf den Scope. Dessen Befunde plus die Slop-Treffer aus Phase 2 zusammenführen, nach Severity sortieren, Duplikate zusammenfassen.

**Blockierend ist ab `HIGH`.** `MEDIUM` und darunter werden protokolliert und nur dann gefixt, wenn sie im Scope liegen und billig sind.

Bei `--quick` entfällt diese Phase.

## Phase 3b — Dual-Abnahme `--dual` (nur kritische Lieferungen)

Idee aus ECC (`skills/santa-method/SKILL.md` + `commands/santa-loop.md`, MIT, gelesen 2026-09-30, nichts installiert): zwei unabhängige Prüfer mit **demselben PASS/FAIL-Raster**, grün nur wenn **beide** PASS geben. Ein einzelner Prüfer teilt die blinden Flecken des Modells, das den Code geschrieben hat. Was nur einer der beiden findet, ist trotzdem ein echter Befund.

**Nur mit `--dual`, nur für kritische Lieferungen:** Deploy der Discord-Bots, Änderungen an `_botcore/` (wirkt auf alle drei Bots), an `~/.claude/hooks/` oder an Security-, Auth- oder Secret-Code. Kostet grob das 2–3-Fache einer Review-Runde plus Codex-Kontingent (Plus, knapp). Mit `--quick` nicht kombinierbar. Ohne `--dual` taucht die Stufe im Verdikt nicht auf.

**Wann:** nach Phase 3, sobald Phase 1 grün ist und Phase 3 keinen offenen Blocker mehr meldet.

**Eingabe, für beide identisch und sonst nichts:** Auftrag wörtlich (des Nutzers Anweisung bzw. Plan-/Task-Text), Diff des Scope (`{ git diff --no-ext-diff --no-textconv --cached --binary; git diff --no-ext-diff --no-textconv --binary; } > .claude/gate/dual_input.diff`; im Pfad-Modus die Dateiliste), das Raster unten. **Nicht** mitgeben: Befunde aus Phase 2/3, das Urteil des anderen Prüfers, den Session-Verlauf, sonst ankern beide auf denselben Stellen. Secret-Dateien (`.env*`, `secrets/`) vorher aus der Eingabe nehmen.

**Raster** (jedes Kriterium PASS oder FAIL; FAIL nur mit `datei:zeile`, Auslöser und der Begründung, warum kein vorhandener Schutz es abfängt):

| # | Kriterium | PASS, wenn |
|---|---|---|
| R1 | Korrektheit | kein Pfad liefert mit einer konkreten Eingabe ein falsches Ergebnis |
| R2 | Sicherheit | keine Secrets im Code, keine Injection, keine Aufweitung von Rechten, Auth oder Sandbox |
| R3 | Fehlerbehandlung | kein stilles Verschlucken, kein Fehler als Erfolgsmeldung (Fehlermodus #1) |
| R4 | Vollständigkeit | jede Anforderung aus dem Auftrag ist umgesetzt |
| R5 | Regressionsfreiheit | bestehende Aufrufer und bestehendes Verhalten bleiben intakt |
| R6 | Konsistenz | keine Widersprüche zwischen Code, Doku und Konfiguration |

**Beide Prüfer in derselben Nachricht starten** (parallel, keiner sieht den anderen):
- **Prüfer A, Claude:** frischer Subagent (Task-Tool, `general-purpose`), Auftrag „Nur prüfen, nichts ändern. Deine Aufgabe ist, Probleme zu finden, nicht freizugeben." Antwort als JSON nach `dual_verdict.schema.json` in diesem Ordner.
- **Prüfer B, Codex:** über den vorhandenen Wrapper, read-only, mit Projektzugriff und demselben Schema:
  ```bash
  python3 ~/.claude/scripts/codex_call.py --mode second-opinion --sandbox read-only \
    --repo <projekt-root> --schema "$HOME/.claude/skills/gate/dual_verdict.schema.json" \
    --timeout 1800 --label gate-dual -- "<Auftrag + Raster + 'nur prüfen, nichts ändern'>" \
    < .claude/gate/dual_input.diff
  ```
  `--timeout 1800` ist Pflicht: `second-opinion` hat im Wrapper nur 300 s (gedacht für kurze Zweitmeinungen), der Dual-Prüfer liest mit `--repo` und hohem Effort aber agentisch wie ein Review (dort 1800 s). Ein Timeout wäre sonst regelmäßig `INCOMPLETE`.

**Urteil:** beide `PASS` → `stages.dual = "PASS"`. Mindestens ein `FAIL` → `critical_issues` beider zusammenführen und deduplizieren. Jede Stelle wie in Phase 2b gegen den Code prüfen: existiert sie nicht, wird der Punkt verworfen und im WORKLOG vermerkt. Der Rest geht als blockierender Befund in Phase 5. Nach dem Fix wie immer ab Phase 1 neu; die nächste Dual-Runde läuft mit **frischen** Prüfern ohne Wissen aus der Vorrunde.

**Deckel:** höchstens 3 Dual-Runden. Danach Status `blocked`, `BLOCKER.md` mit den offenen Punkten beider Prüfer, der Nutzer entscheidet.

**Codex fällt aus** (Exit 3 Login fehlt, 4 Kontingent, sonst Fehler): ein Ausfall ist keine Zustimmung. `stages.dual = "INCOMPLETE"`, Gate nicht grün, Grund im Verdikt. Kein stiller Ersatz durch einen zweiten Claude-Prüfer. Will der Nutzer das, steht im Verdikt „gleiche Modellfamilie".

**Übereinstimmung messen:** im Verdikt `"dual": {"rounds": N, "claude": "PASS|FAIL", "codex": "PASS|FAIL|ERROR", "agreement": {"both": n, "claudeOnly": n, "codexOnly": n}}`. Bleibt die Übereinstimmung dauerhaft niedrig, ist das Raster zu vage; an einem der Prüfer liegt es selten.

## Phase 4 — Deployment-Preflight

`/deploy-preflight` — Tests, Importierbarkeit, `.env`-Abgleich, `pip check`, Debug-Relikte (`print`, `breakpoint`, `pdb`, `TODO`/`FIXME` im Produktivpfad). Go/No-Go.

No-Go ist blockierend. Bei `--quick` entfällt diese Phase.

## Phase 5 — Fix-Schleife (gegatet)

Nur hier wird geschrieben, und nur mit dem starken Modell.

1. **Ein** Befund pro Runde, höchste Severity zuerst.
2. Fix anwenden.
3. **Ab Phase 1 neu** — ein Fix, der eine andere Stufe rot macht, ist kein Fix.
4. Jede Runde nach `.claude/gate/WORKLOG.md` anhängen (append-only): Runde, Befund, Änderung, Ergebnis der Neuprüfung.

**Budget:** `maxIterations: 10`, `maxRepeatedFailures: 3`.
Stuck-Erkennung über die Signatur `failingGate:sha256(evidence)[:16]` — dreimal dieselbe Signatur heißt, der Ansatz trägt nicht: abbrechen mit Status `blocked`, `BLOCKER.md` schreiben, an der Nutzer eskalieren. **Nicht** weiter probieren.

## Phase 6 — Verdikt

`.claude/gate/verdict.json` schreiben (überschreiben, nicht anhängen):

```json
{
  "tool": "gate", "generatedAt": "<iso>", "workSha": "<16 hex>",
  "pass": true, "failingGate": null,
  "stages": {"lint":"PASS","typecheck":"PASS","test":"PASS",
             "slop":"3 findings","review":"PASS","preflight":"GO"},
  "iterations": 2,
  "findings": [{"severity":"HIGH","file":"x.py:41","mode":12,"summary":"…","fixed":true}],
  "evidence": null
}
```

Ausgabe an der Nutzer **kurz**: Status, welche Stufen liefen, wie viele Runden, was gefixt wurde, was offen blieb und warum. Kein Dump der Roh-Ausgaben — die stehen im WORKLOG.

## Modell-Zuordnung

| Aufgabe | Wer | Warum |
|---|---|---|
| Phase 1 komplett | kein Modell | deterministisch, das ist der Punkt |
| Phase 2 Slop-Pass | `gemini-bridge` / `local-bridge` | kostenlos, Erkennung braucht kein Frontier-Modell |
| Phase 3 Review | `/review` (Standard-Dispatch) | eingespielte Pipeline |
| Phase 5 Fixes | starkes Modell (Opus) | hier zählt Korrektheit |
| Cross-Check bei Uneinigkeit | `codex-bridge` | andere Modell-DNA, läuft über das Plus-Abo |
| Phase 3b `--dual` | frischer Claude-Subagent + Codex über `codex_call.py` (read-only) | gleiches Raster, zwei Modellfamilien |

## Constraints

- **Nie einen Befund als erledigt melden, ohne die Stufe neu laufen zu lassen.** Behauptete Fixes sind der häufigste Selbstbetrug in dieser Art Schleife.
- **Kein Whitewashing:** grün wird nur geschrieben, wenn jede blockierende Stufe grün gelaufen ist. Übersprungene Stufen (`--quick`) stehen als `SKIPPED` im Verdikt, nie als `PASS`.
- Backup vor Edit an gepflegten Dateien: `cp -a <file> <file>.bak.pre-gate.$(date +%s)` (Windows: `[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()`).
- Keine Scope-Ausweitung. Was außerhalb des Änderungssatzes liegt, wird gemeldet, nicht gefixt.
- `.claude/gate/` gehört in `.gitignore`.

## Beispiele

```
/gate                      # uncommitted Änderungen abnehmen
/gate src/bots/            # nur diesen Pfad
/gate --quick              # nur Orakel + Slop-Pass, ohne Review/Preflight
/gate --force              # Cache ignorieren, alles neu
/gate --dual src/_botcore/ # kritische Lieferung: zusätzlich Claude + Codex, beide müssen PASS geben
```

## Roadmap (bewusst noch nicht gebaut)

- **Stop-Hook-Durchsetzung** (Muster aus `ncoevoet/claude-loop`): Turn-Ende blocken, solange das Verdikt rot ist. Erst wenn die Kette in der Praxis stabil läuft — ein Stop-Hook greift in *jeden* Turn.
- **`LOGIC.md`-Ledger** — fachliche Zusicherungen mit Beweis-Kommando, Baseline vor der Änderung, Nachprüfung danach (Business-Logik-Drift). Das ist der Teil, den kein fremdes Werkzeug abdeckt.

## Versionen

- 1.0.0 (2026-07-29): Erstfassung. Orakel-Kette + work-sha-Caching + Stuck-Signatur nach dem Muster von `ncoevoet/claude-loop` (MIT); Slop-Pass gegen `_shared/ai-failure-modes.md` aus `amElnagdy/guard-skills` (MIT). Stop-Hook und LOGIC-Ledger bewusst ausgeklammert.
- 1.1.0 (2026-09-30): Phase 3b `--dual` (Santa-Method aus ECC, MIT, nur die Idee übernommen): Claude-Subagent und Codex prüfen mit demselben Raster R1–R6, grün nur bei zweimal PASS, höchstens 3 Runden, Codex-Ausfall = `INCOMPLETE`. Schema `dual_verdict.schema.json`. Quelle: TikTok-Auswertung A2 #6 (a).
