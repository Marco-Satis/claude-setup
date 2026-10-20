# Projekt-Achsen E-J — kanonische Quelle (review-Familie)

> **Single-Source-of-Truth** fuer die Projekt-Ebene eines Reviews: Architektur,
> Doku-/Instruktions-Drift, Config/Env/Deploy, Repo-Hygiene, Betrieb, Ziel-Abgleich.
> Genutzt von `/review` (Phase 4.6), `/full-audit`, `/quick-review` (nur Achse H).
> **Aenderung NUR hier** — die Skills referenzieren diese Datei statt zu kopieren
> (dieselbe Trennung wie bei den Severity-Ankern; verhindert Cross-Skill-Drift).
>
> Severity-Anker fuer diese Achsen: **K2p** in [`severity-anchors.md`](severity-anchors.md).
> Gating (welche Achse wann laeuft), Council-Kopplung (K6), Ehrlichkeits-Pflicht und
> Reporting bleiben im aufrufenden Skill — hier steht nur das *Wie* der Achsen.
>
> Ausgelagert 2026-08-02 aus `review/SKILL.md` v4.5.1 (Kern war auf 80 KB gewachsen;
> das eigene v3.3.1-Changelog hatte Bloat als Instruction-Following-Risiko geflaggt).

---

### Schritt 1 — Mechanischer Vorlauf (PFLICHT, vor jeder Modell-Bewertung)

Gelernt aus dem `/gate`-Test 2026-07-29: ein Modell allein erfand einen Befund und uebersah zwei reale, die `grep` in einer Sekunde fand (19 : 1 zugunsten der Mechanik). **Deshalb zuerst messen, dann urteilen.** Das Modell bewertet nur, was die Mechanik geliefert hat, plus die Achsen die echtes Urteil brauchen (E, J).

`<root>` = Projekt-Wurzel. Ergebnisse als Rohdaten in `RAW_TOOL_OUTPUT/projekt_prepass.txt`, Zaehlwerte in den Master.

**`$PRUNE` zuerst setzen — nicht optional.** Beim Verifikationslauf 2026-08-02 (filedrop) fehlte `.venv` im Ausschluss: Achse E meldete daraufhin `idna/uts46data.py` (16.896 LoC) als God-File und pip-Vendor-Kopien als Duplikate — 100 % Rauschen, echte Signale (`app.py` 151 LoC, keine Duplikate) unsichtbar. **Punkt-Verzeichnisse und `site-packages` gehoeren in den Prune, sonst reviewst du fremde Dependencies.**

```bash
PRUNE="-path */.git -o -path */.venv -o -path */venv -o -path */node_modules \
       -o -path */site-packages -o -path */__pycache__"

# H — Hygiene (laeuft IMMER, auch im THEMA-Modus)
find <root> \( $PRUNE \) -prune -o -name '*.sync-conflict-*' -print      # Konflikt-Kopien im Quellbaum
find <root> \( $PRUNE \) -prune -o \( -name '*.bak.*' -o -name '*.orig' \) -print
find <root> \( $PRUNE \) -prune -o -type f -size +5M -print              # grosse Binaries
git -C <root> ls-files | grep -E '(__pycache__|\.pyc$|/venv/|node_modules|\.env$|\.key$|\.pem$)'
# Secret-Backups: untracked UND nicht ignoriert = ein `git add .` vom Leak entfernt (K2p CRITICAL)
find <root> \( $PRUNE \) -prune -o \( -name '.env*' -o -name '*secret*' -o -name '*.key' \) \
     -not -name '*.example' -not -name '*.sample' -not -name '*.template' -print \
  | while read -r f; do git -C <root> check-ignore -q "$f" || echo "NICHT IGNORIERT: $f"; done
# .env.example/.sample/.template MUESSEN untracked-und-nicht-ignoriert sein (das ist ihr Zweck)
# — ohne diesen Ausschluss meldet der Check sie als Secret-Leak. Verifiziert 2026-08-02.

# E — Architektur
find <root> \( $PRUNE \) -prune -o -name '*.py' -print0 | xargs -0 md5sum \
  | sort | uniq -w32 -d                                                  # byte-identische Duplikate
find <root> \( $PRUNE \) -prune -o -name '*.py' -print0 | xargs -0 wc -l | sort -rn | head -10

# G — Config/Env
grep -rhoE "(os\.environ(\.get)?[\[\(][[:space:]]*['\"]|getenv\([[:space:]]*['\"])[A-Z_]+" \
     <root> --include='*.py' | grep -oE '[A-Z_]{3,}' | sort -u          # im Code gelesene ENV-Vars
# gegen .env / .env.example / systemd-Unit / settings.json abgleichen (Differenz beidseitig!)
#
# ACHTUNG, verifiziert 2026-08-02: die Klammer-Klasse [\[\(] ist der springende Punkt.
# Eine Fassung ohne sie ("\[?['\"]") matcht os.environ["X"], aber NIE os.environ.get("X")
# — nach .get folgt "(", kein Quote. Im Test fand die kaputte Fassung 4 von 13 Variablen;
# die 9 unsichtbaren waeren als "deklariert aber nirgends gelesen" (LOW) gemeldet worden.
# Ein Vorlauf-Fehler erzeugt hier also FALSCHE FINDINGS, nicht nur fehlende.
#
# Liest das Projekt ENV ueber einen Helper (des Nutzers Standard laut rules/secret-handling.md:
# `from utils.config import get_env`), findet dieser grep NICHTS. Dann zusaetzlich nach dem
# Helper-Namen greppen und dessen Aufrufe auswerten — vorher pruefen, ob es ihn gibt:
#   grep -rn "def get_env\|BaseSettings\|pydantic_settings" <root> --include='*.py'

# I — Betrieb
grep -rn "except Exception" <root> --include='*.py' | grep -v test       # Kandidaten fuer stille Fehler
systemctl --user list-timers --all 2>/dev/null; crontab -l 2>/dev/null   # laufende Automation vs. Repo-Stand
```

Kein Git-Repo → `git ls-files`/`check-ignore`-Zeilen entfallen (Notiz), Rest laeuft unveraendert.

**Plausibilitaets-Gate vor der Bewertung:** liegt der groesste „God-File" im Bereich Zehntausend Zeilen oder heissen Duplikate nach Paketnamen, ist der Prune kaputt — Befehle korrigieren, **nicht** die Ergebnisse melden. Fremde Dependencies zu reviewen ist kein Finding, sondern ein Messfehler.

### Schritt 2 — Delegieren statt neu bauen (Reuse-first)

Fuer drei Achsen existieren gepflegte Spezial-Skills. Diese **aufrufen**, nicht nachbauen; ihr Ergebnis als Findings uebernehmen (Severity nach K2p neu kalibrieren — fremde Skala nicht blind uebernehmen):

| Achse | Delegieren an | Wann |
|---|---|---|
| F Doku-Drift | `code-doc-sync` | Projekt hat README/CODE_DOKUMENTATION/COWORK |
| F Instruktions-Drift | `instructions-drift-check` | Scope beruehrt `~/.claude` (CLAUDE.md, rules/, Skills) |
| G Env-Vollstaendigkeit | `python-env-audit` | Python-Projekt mit `.env` |
| G Deploy-Reife | `deploy-preflight` | vor Release/Deploy ODER Scope beruehrt Service-/Unit-Dateien |
| Dep-Supply-Chain | `deps-check` / `dependency-auditor` | laeuft bereits als Phase-2-Slot 3 — hier NICHT doppeln |

Skill fehlt/failt → Achse manuell nach den Kriterien unten, Notiz „delegiert an X fehlgeschlagen: <grund>". **Nie beides** — kein Doppel-Reporting derselben Sache.

### Achse E — Architektur & Struktur

Aus dem Vorlauf + Lesen: **Divergierte Duplikate** (dieselbe Verantwortung an 2 Orten, Inhalte auseinander — der teuerste Befund dieser Achse, weil Fixes nur eine Seite treffen; byte-identisch ist harmloser als divergiert). **God-Files** (>1000 LoC mit mehreren unabhaengigen Verantwortlichkeiten — reine Laenge allein ist kein Finding). **Zirkulaere/Layering-verletzende Imports** (Low-Level importiert Feature-Modul). **Copy-Paste-Block ≥30 Zeilen in 3+ Files.** **Modulgrenzen:** gibt es einen Ort an dem eine neue Funktion offensichtlich hingehoert, oder muss man raten?

Bei aktivem Graphify (6.5B): dessen God-Nodes/Cluster als Beleg heranziehen statt zweiter Analyse.

> **Reuse-first-Kopplung:** in den Gamebot-Projekten gilt zusaetzlich die Regel `~/.claude/rules/gamebot-reuse-first.md` — `_botcore/` ist die kanonische Basis, bekannte Abweichung ist `CellSurvivor/bots/core.py`. Diese bekannte Abweichung ist **kein neues Finding** (dokumentierter der Nutzer-Entscheid), aber ihre **Divergenz** (was ist inzwischen auseinandergelaufen) ist eine.

### Achse F — Doku- & Instruktions-Drift

Zuerst delegieren (Tabelle oben), dann die Luecke: **Sagt die Doku etwas, das der Code nicht tut?** Drei Klassen, absteigende Schwere — (1) aktiv falsch (jemand handelt danach und liegt daneben) = HIGH, (2) verwaist (nennt Datei/Flag die weg ist) = MEDIUM, (3) veraltet (Zeilenzahl, Version) = LOW.

Pflicht-Abgleich wenn im Scope: `README` · `CLAUDE.md` (Projekt **und** global) · `PROGRESS.md` · `rules/*.md` · Docstrings geaenderter oeffentlicher Symbole · `SKILL.md`-Frontmatter vs. tatsaechliches Verhalten. **Regel-Dateien sind Code-aequivalent** — eine falsche Rule steuert kuenftige Sessions und ist deshalb kein Kosmetik-Befund.

### Achse G — Config, Env & Deployment

Aus dem ENV-Vorlauf **beide Richtungen** pruefen: im Code gelesen aber nirgends gesetzt (Dienst startet nicht oder laeuft still degraded = HIGH) · gesetzt aber nirgends gelesen (LOW, Verwirrungs-Muell). Dazu: `.env.example` vollstaendig? Secrets ausschliesslich in der vorgesehenen Ablage (Regel `~/.claude/rules/secret-handling.md`) — **Wert niemals in den Report, nur Pfad + Pattern-Typ.** Ports/Pfade/Hosts gegen bestehende Belegung (bei der Nutzer: `tailscale-serve`-Portmap, nginx :443 — keine Kollision, keine Zufallsports). systemd-/Timer-/Cron-Unit: existiert der referenzierte Pfad und Interpreter wirklich?

### Achse H — Repo-/Datei-Hygiene (mechanisch, laeuft immer)

Direkt aus dem Vorlauf, kaum Urteil noetig: **Konflikt-Kopien im aktiven Quellbaum** (bei des Nutzers Syncthing-Setup real und wiederkehrend — 37 Stueck im Bot-Baum, gefunden 2026-07-29; importierbar neben dem Original = HIGH). Getrackte Secrets (CRITICAL) / Build-Artefakte (LOW). `.gitignore`-Luecken. `.bak`-Halde. Grosse Binaries. **Tote Einstiegspunkte:** Script/Hook den nichts referenziert — `grep -rl "<basename>"` gegen Repo, Hooks zusaetzlich gegen `settings.json`; laeuft er noch per Cron/Timer, ist er nicht tot sondern unsichtbar (MEDIUM).

### Achse I — Betrieb & Beobachtbarkeit

Die Frage ist nicht „ist der Code richtig" sondern **„merkt jemand, wenn es kaputtgeht?"**. Pro Dienst/Hook/Timer im Scope: Faellt er aus — gibt es Log, Notify, Watchdog? (nichts davon = HIGH). Ist der Restart-/Recovery-Pfad je ausgefuehrt worden oder nur dokumentiert? Backup ohne verifizierten Restore = MEDIUM. **Idempotenz:** was passiert beim Doppel-Lauf eines Cron/Timers — beschaedigt er State? Log-Rotation vorhanden? Discord-Notify: geht er ueber den kanonischen Kanal (`rules/discord-notify-channel.md`) und ist der auf **dieser** Maschine ueberhaupt verdrahtet — ein stiller No-op ist ein Betriebs-Finding, kein Code-Fehler.

### Achse J — Ziel-/Anforderungs-Abgleich

Der Abgleich, den kein Linter macht: **tut das Projekt, was es zu tun behauptet?** Quelle in dieser Reihenfolge: Plan/Spec der Session · `PROGRESS.md` · `CLAUDE.md` „Stack/Workflow" · README-Feature-Liste.

1. Dokumentiertes Kern-Feature ohne Code = HIGH (die Doku verspricht etwas Nicht-Existentes).
2. Code ohne Aufrufer (YAGNI-Leiche) = LOW, MEDIUM wenn er laufend Ressourcen verbraucht. **Vor „ausbauen" immer erst greppen ob es genutzt wird** — sonst Entfernen vorschlagen.
3. Implementierung weicht vom Plan ab: entweder als **begruendete Verbesserung** markieren oder als Finding. **Liegt das Problem im PLAN statt im Code, genau das sagen** (deckt sich mit dem Plan-Abgleich in Phase 2).

---

## Verifikations-Status des Vorlaufs

Am **2026-08-02 komplett gegen ein echtes Projekt gefahren** (`~/projects/filedrop`:
FastAPI, Git-Repo, systemd-Unit, `.env`, 603 LoC) — **alle sechs Achsen inklusive Urteil**,
nicht nur der Vorlauf. Voller Bericht: `~/.claude/reports/review/PHASE46_VOLLBETRIEB_filedrop_2026-08-02.md`.

Achsen-Ergebnis: E/G/J sauber · F 1×LOW (kein README) · H 1×CRITICAL (`.env.bak` weder
getrackt noch ignoriert — gefixt und committet) · I 2×MEDIUM (Auth-Fehlschlaege ohne
Logging; Crash-Loop ohne Notify). **Kein einziger Council-Trigger feuerte** — C3 blieb
korrekt stumm, weil uvicorn nach journald loggt und die Bedingung „ohne Log UND Notify UND
Watchdog" damit nicht erfuellt ist. Ein sauberes Projekt loest keinen Council-Call aus.
Offen bleibt nur der Modell-Pass (Slot 7) in einer frischen Session.

Vorher: **drei Defekte im Rezept selbst**, alle gefixt und nachgemessen —

| # | Defekt | Auswirkung | Status |
|---|---|---|---|
| 1 | `.venv` fehlte im `$PRUNE` | Achse E meldete pip-Vendor-Dateien als God-Files/Duplikate; echte Signale unsichtbar | gefixt, nachgemessen (`app.py` 151 LoC, 0 Duplikate) |
| 2 | ENV-Regex ohne `[\[\(]` | `os.environ.get("X")` matchte **nie** — 4 von 13 Variablen gefunden, die 9 fehlenden waeren als „deklariert, nirgends gelesen" gemeldet worden | gefixt, nachgemessen (13/13, Differenz beidseitig leer) |
| 3 | `.env.example` im Secret-Check | Template wurde als „nicht ignoriertes Secret" gemeldet (CRITICAL-Fehlalarm) | gefixt via `-not -name '*.example|*.sample|*.template'` |

**Die Lehre, die ueber diese drei hinausgeht:** ein Fehler im mechanischen Vorlauf erzeugt
nicht nur *fehlende*, sondern **falsche Findings** — und weil der Vorlauf als „gemessen"
gilt, bekommen sie mehr Vertrauen als eine Modell-Vermutung. Deshalb gilt das
Plausibilitaets-Gate fuer jede Achse, nicht nur fuer E: **Zaehlwerte gegenlesen, bevor
daraus ein Befund wird.** Bei Achse G heisst das konkret: fuehrt der Abgleich zu vielen
„verwaisten" Variablen, ist zuerst der Lese-Grep verdaechtig, nicht das Projekt.

Echter Befund aus demselben Lauf (kein Rezept-Fehler): `filedrop/.env.bak.pre-tsauth.*`
ist untracked **und** nicht ignoriert — `.gitignore` deckt `.env` ab, aber nicht `.env.*`.
Ein `git add .` vom Leak entfernt (K2p: CRITICAL).

