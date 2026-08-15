# Native Skills & UI-Kommandos — Erkennung statt Abstreiten (Global Rule)

> Anlass 2026-08-14: Auf der Nutzer Frage nach `/goal` behauptete eine Session „existiert auf
> dieser Installation nicht" — geprüft wurden aber nur Skill-Ordner, `~/.claude/commands/`
> und CLI-Flags. Native UI-Kommandos sind von dort aus unsichtbar. Die Behauptung war falsch;
> der Nutzer nutzt `/goal` regelmäßig.

## Kernregel

Die Skill-Liste, die eine Session beim Start sieht, ist **unvollständig**. Sie zeigt eigene
Skills, Plugin-Skills und einen Teil der Builtins — **nicht** die nativen UI-Kommandos der
CLI (`/goal`, `/help`, `/clear`, …). Daraus folgt:

1. **Nie** aus „steht nicht in meiner Liste" auf „existiert nicht" schließen.
2. Nennt der Nutzer einen Slash-Befehl, den die Liste nicht kennt: **erst proben, dann antworten** —
   `Skill`-Tool mit dem Namen aufrufen. Die Fehlermeldung ist die Wahrheit:
   - `"<name> is a UI command, not a skill"` → existiert, ist aber Terminal-Ebene.
   - Skill lädt → existiert und ist auch autonom nutzbar.
   - „no such skill"-artig → erst dann darf „kenne ich nicht" gesagt werden, mit dem
     Zusatz, dass UI-Kommandos neuerer CLI-Versionen trotzdem existieren können
     (Changelog gegenprüfen: `anthropics/claude-code/CHANGELOG.md`).

## Was Sessions selbständig können — und was nicht

| Ebene | Beispiele | Session kann selbst aufrufen? |
|---|---|---|
| Eigene Skills | `/review`, `/cso`, `/lyra`, … | **ja** (Skill-Tool) |
| Builtin-Skills | `/loop`, `/schedule`, `/code-review`, `/dataviz`, `/run` | **ja** (Skill-Tool) |
| Plugin-Skills | `/caveman`, `/council`, `/impeccable` | **ja** (Skill-Tool) |
| **UI-Kommandos** | `/goal`, `/help`, `/clear`, `/config`, `/mcp`, `/fast` | **nein** — laufen im Terminal, bevor die Session sie sieht. der Nutzer bitten, sie selbst zu tippen. |

Empirisch belegt am 2026-08-14: `Skill(skill="goal")` → „goal is a UI command, not a skill.
Ask the user to run /goal themselves — it cannot be invoked via the Skill tool."

## Konsequenz für Autonomie-Fragen

Wenn der Nutzer fragt „können die Sessions X selbständig anwenden": Antwort hängt an der Ebene.
Skills ja — auch headless/RC (seit Trust-Guard 14.08. starten alle Hosts dialogfrei).
UI-Kommandos nein — die kann nur der Nutzer im Terminal auslösen; die Session darf das sagen,
aber nicht mit „gibt es nicht" verwechseln.

## Katalog der nativen Kommandos (Referenz, Quelle: code.claude.com/docs/en/commands, Stand 2026-08-14)

**Sessions sollen diese Kommandos AKTIV EMPFEHLEN, wenn die Situation passt** — der Nutzer kennt
nicht jedes und erwartet den Hinweis („dafür gibt es `/goal`, tipp es ein"). Die wichtigsten
nach Situation:

| Situation | Empfehlen |
|---|---|
| Aufgabe soll laufen, bis eine Bedingung erfüllt ist („bis Tests grün", „bis deployed") | **`/goal <bedingung>`** — Claude arbeitet weiter bis erfüllt; `/goal clear` beendet |
| Langlauf soll Terminal nicht blockieren | **`/background`** (Session löst sich als Hintergrund-Agent) · `/fork [prompt]` (Kopie als Hintergrund-Session) |
| Nebenaufgabe, Hauptkontext nicht verschmutzen | **`/subtask <auftrag>`** (Subagent, meldet zurück) · `/btw <frage>` (Seitenfrage ohne Verlaufseintrag) |
| Kontext wird knapp | `/compact [anweisung]` · `/autocompact <tokens>` (Schwelle setzen — Anschluss an Loopmode-55/70/80-Regel) · `/context` (Anzeige) |
| Alternative ausprobieren ohne Verlauf zu verlieren | `/branch` (Abzweig der Konversation) · `/rewind` (Checkpoint zurück) |
| Qualität/Tempo steuern | `/effort <level>` · `/fast on\|off` · `/model` · `/advisor` (Zweitmodell-Beratung) |
| PR-/Review-Automation | `/autofix-pr` (Web-Session wacht über den PR) · `/code-review [ultra]` · `/security-review` · `/verify` |
| Groß-Refactor über viele Dateien | `/batch <auftrag>` (parallele Orchestrierung) |
| Selbstdiagnose | `/doctor` · `/insights` (HTML-Report über Sessions) · `/usage` · `/status` · `/tasks` |
| Session-Mobilität | `/remote-control` · `/teleport` (Web-Session ins Terminal) · `/desktop` · `/cd <pfad>` · `/add-dir` |

Rest (Verwaltung, selbsterklärend): `/help /clear /resume /export /copy /diff /config /settings
/permissions /hooks /memory /mcp /plugin /reload-plugins /reload-skills /keybindings /login
/logout /model /privacy-settings /release-notes /bug /feedback /init /plan /debug /import
/deep-research /loop /dataviz /claude-api /fewer-permission-prompts /powerup /recap /focus
/color /heapdump /exit /upgrade /passes /mobile /chrome /ide /install-github-app
/install-slack-app /design-sync /design-login /radio /simplify /effort`.

Bundled Skills (`/loop`, `/code-review`, `/deep-research`, `/plan`, `/verify`, `/batch`,
`/debug`, `/effort`, …) kann die Session via Skill-Tool selbst aufrufen; alles andere ist
UI-Ebene → der Nutzer tippen lassen. Dispatch-Kollisionen (`review`, `loop`, …) regelt weiterhin
`rules/skill-dispatch.md` — der Nutzer eigene Skills gewinnen dort, wo die Tabelle es sagt.
