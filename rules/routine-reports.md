# Server-Routinen: Report-Pflicht + Session-Check (Global Rule)

> der Nutzer-Entscheid 2026-08-14. Begründung in einem Satz: **der Nutzer sieht die Server-Routinen
> nicht.** Sie laufen per cron/systemd auf netcup, ihre Logs liest niemand, und was sie
> brauchen (fehlender Login, leeres Secret, Rate-Limit) blieb bisher unsichtbar, bis etwas
> kaputtging.

## Pflicht 1 — jede Routine schreibt am Ende eine MD

Gilt für **jede** Routine auf dem Server, bestehende wie künftige. Ziel:
`~/projects/Skills_&_Co/ROUTINE_REPORTS/<name>_<YYYY-MM-DD>.md` (synct zum PC).

Nicht selbst formatieren — Helper nutzen:

```bash
{
  echo "## Was lief"
  echo "- ..."
  echo
  echo "## BRAUCHT"
  echo "- fehlender gh-Login -> Feeds unauthentifiziert"   # oder weglassen
} | ~/.claude/scripts/routine_md.sh <name> OK|WARN|FAIL
```

Der Helper setzt Kopfzeile (Status, Host, Plan) und ergänzt `## BRAUCHT` automatisch mit
„nichts", falls der Abschnitt fehlt — **„braucht nichts" ist damit eine explizite Aussage,
keine Lücke.** `ROUTINE_PLAN` als env setzen, wenn der Plan im Report stehen soll.

Der Helper ist best-effort: schlägt das Schreiben fehl, exitet er 0. Eine Routine darf
**nie** am Reporting scheitern.

## Pflicht 2 — Claude prüft zu Session-Beginn

Bei jedem Session-Start im Skills_&_Co-Projekt läuft der Hook
`~/.claude/hooks/routine_digest.py` → `~/.claude/scripts/routine_audit.py` und hängt das
Ergebnis als Kontext an. Claude hat dann drei Aufgaben, ohne dass der Nutzer fragen muss:

1. **Neue Reports mit der Nutzer besprechen** — insbesondere die `## BRAUCHT`-Zeilen.
2. **Planmäßigkeit prüfen** — überfällige Routinen meldet der Audit.
3. **Überfälliges selbst root-causen und nach Möglichkeit fixen**, danach Bescheid geben.

Als Hook gebaut, nicht als Vorsatz: eine Regel, die nur im Prompt steht, verschwindet nach
zwanzig Turns still (belegt: `gamebot-compact-amnesie`).

## Evidenz-Modell — der Grund, warum „Log ist alt" kein Fehleralarm ist

`routine_audit.py` unterscheidet zwei Sorten. Wer eine Routine hinzufügt, trägt sie mit der
richtigen Art ein:

| Art | Bedeutung | Beleg |
|---|---|---|
| `append` | schreibt bei **jedem** Lauf | Log-mtime; älter als Toleranz = überfällig |
| `event_only` | schreibt **nur bei Ereignis** | Stille = **gesund**. mtime ist hier KEIN Beleg |

Beispiele `event_only`: `pipeline_selfcheck --quiet` (loggt nur Warnungen),
`sweep_watchdog` (loggt nur bei Daemon-Neustart). Am 2026-08-14 sahen beide „3 Tage still"
aus — ein naiver Checker hätte zwei Fehlalarme erzeugt.

Systemd-Timer brauchen keine Heuristik: `LastTriggerUSec` ist der harte Beleg.

## Bestandsroutinen: Wrapper statt Skript-Edit

Die sieben Bestandsroutinen laufen seit 2026-08-14 durch
`~/.claude/scripts/routine_wrap.sh` — eingehängt in der crontab, die Skripte selbst
sind **unangetastet** (teils produktiv und fremd gepflegt in `n8n_stack`):

```
<zeitfelder> routine_wrap.sh <name> "<plan>" [--quiet-ok] -- /bin/bash -c '<original>' >> <log> 2>&1
```

Drei Details, die nicht offensichtlich sind:

- **`/bin/bash -c '…'` ist Pflicht**, sobald der Originalbefehl Shell-Konstrukte enthält
  (`cd … &&`, ENV-Präfixe wie `STACK_ROOT=…`). Der Wrapper führt mit `"$@"` aus und kann
  das sonst nicht auflösen.
- **Die Log-Umleitung bleibt stehen.** Der Wrapper reicht die Ausgabe unverändert durch,
  damit `routine_report.py` und die bestehenden Logs weiter funktionieren.
- **`--quiet-ok` bei häufigen event-only-Routinen** (`sweep_watchdog` alle 5 min,
  `pipeline_selfcheck` alle 30 min): Report nur bei Exit ≠ 0 oder nicht-leerer Ausgabe.
  Ohne das Flag entstünden 288 bzw. 48 Reports pro Tag.

`weekly_tool_scout.sh` schreibt seinen Report selbst (feinere Angaben als der Wrapper
liefern kann) und ist deshalb nicht eingehängt.

## Neue Routine anlegen — Checkliste

1. Report-Block mit `routine_md.sh` ans Ende (Pflicht 1)
2. Eintrag in `CRON_ROUTINES` bzw. `TIMERS` in `routine_audit.py`, mit korrekter
   Evidenz-Art und Toleranz (wöchentlich → 8 Tage, täglich → 30 h)
3. Bei frisch eingerichteten Routinen `"since": "<datum>"` setzen — dann meldet der Audit
   „wartet auf ersten Lauf" statt „überfällig"
4. `--no-session-persistence` nicht vergessen, falls die Routine `claude -p` nutzt
5. `flock` bei allem, was Geld oder Tokens kostet (siehe `hintergrundjobs-doppelstart`)

## Abgrenzung zu `routine_report.py`

`routine_report.py` (systemd, täglich 08:15) ist der **Diff-Melder**: neue Log-Zeilen seit
letztem Lauf → Discord + `ROUTINE_STATUS.md`. `routine_audit.py` ist die
**Planmäßigkeits-Prüfung** + Report-Sammler für Claude. Beide bleiben, sie beantworten
verschiedene Fragen: „was ist passiert" vs. „lief alles und was fehlt".
