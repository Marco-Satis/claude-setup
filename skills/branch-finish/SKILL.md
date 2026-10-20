---
name: branch-finish
version: 1.0.0
last-reviewed: 2026-07-21
description: Strukturierter Abschluss eines Feature-Branches — Test-Gate zuerst, dann exaktes Optionen-Menü (lokal mergen / PR nur falls Remote existiert / behalten / verwerfen) mit Verifikation + Cleanup. Solo-Dev-orientiert (kein PR-Zwang), Syncthing-bewusst (git läuft pro Seite, .git wird nicht gesynct). (geerntet aus superpowers:finishing-a-development-branch v6.1.1, 2026-07-21)
when_to_use: branch fertig, feature-branch abschließen, branch mergen oder löschen, branch aufräumen, implementation fertig was nun mit dem branch, branch finish, merge zurück auf main
argument-hint: 'Optional: Branch-Name — Default: aktueller Branch'
allowed-tools: Bash Read
userInvocable: true
---

# Branch-Finish — Feature-Branch strukturiert abschließen

Zweck: Wenn die Arbeit auf einem Feature-Branch fertig ist, nicht offen fragen „was nun?", sondern Test-Gate → exakte Optionen → gewählte Option ausführen → verifizieren → aufräumen.

## Phase 0 — Pre-Flight

1. **Git-Repo-Check:** `git rev-parse --git-dir` — kein Repo → Abort.
2. **Branch bestimmen:** Argument oder `git branch --show-current`. Auf `main`/`master`? → nichts abzuschließen, Exit.
3. **Uncommitted Changes?** `git status --porcelain` — wenn ja: erst committen (oder der Nutzer fragen: committen/stashen/abbrechen).
4. **Syncthing-Kontext merken:** Liegt das Repo unter `~/projects` (bidirektional gesynct PC↔netcup, `.git` excluded)? → Hinweis für Phase 4 vormerken.

## Phase 1 — Test-Gate (Pflicht, geerntet aus superpowers:finishing-a-development-branch v6.1.1)

Projekt-Testsuite laufen lassen (meist `pytest`; sonst was das Projekt vorgibt).

- **Tests rot:** Failures zeigen, **STOP** — keine Optionen anbieten, kein „mergen wir trotzdem". Erst fixen (ggf. `/investigate`).
- **Tests grün / keine Tests vorhanden:** weiter (bei „keine Tests" das explizit im Output sagen, nicht verschweigen).

## Phase 2 — Kontext ermitteln

- **Base-Branch:** `git merge-base HEAD main` (fallback `master`); unsicher → der Nutzer fragen („Branch ging von main ab — korrekt?").
- **Remote?** `git remote -v` — bei der Nutzer meist keins/kein GitHub-Remote → PR-Option dann gar nicht anbieten.
- **Arbeit zeigen:** `git log --oneline <base>..HEAD` — die Commits, um die es geht.

## Phase 3 — Optionen-Menü (exakt, keine offene Frage)

Ohne Remote genau 3, mit Remote genau 4 Optionen — ohne Erklär-Prosa:

```
Branch <name> ist fertig (Tests grün, N Commits). Was tun?

1. Lokal in <base> mergen (Solo-Dev-Default)
2. Push + Pull Request        [nur anbieten wenn Remote existiert]
3. Branch behalten (der Nutzer kümmert sich später)
4. Arbeit verwerfen
```

## Phase 4 — Ausführung

**Option 1 — Lokal mergen:**
```bash
git checkout <base>            # git pull nur falls Remote existiert
git merge <feature-branch>
<tests auf dem Merge-Resultat>
git branch -d <feature-branch>  # -d, nicht -D: schlägt fehl wenn nicht gemergt = eingebaute Verifikation
```
Reihenfolge ist Pflicht: erst Merge + Tests verifizieren, **dann** Branch löschen.

**Syncthing-Hinweis (gesynctes Repo):** Der gemergte Working-Tree synct zur anderen Seite, `.git` nicht — drüben erscheinen die Änderungen als lokale Modifikationen gegenüber der dortigen History. der Nutzer kurz sagen: auf der anderen Seite den Stand als Commit übernehmen (oder dortiges git bewusst ignorieren) und während des Merges nicht zeitgleich beidseitig im selben Ordner arbeiten (`.sync-conflict`-Gefahr).

**Option 2 — Push + PR** (nur mit Remote): `git push -u origin <feature-branch>`, PR via `gh pr create`. Branch **nicht** löschen — wird für PR-Iteration gebraucht.

**Option 3 — Behalten:** Nichts löschen. Report: „Branch <name> bleibt, Stand <sha>."

**Option 4 — Verwerfen:** Erst zeigen was wegfällt (Commit-Liste aus Phase 2), dann **getippte Bestätigung** verlangen: der Nutzer muss wörtlich `verwerfen` antworten — kein „ja" akzeptieren. Danach:
```bash
git checkout <base>
git branch -D <feature-branch>
```

## Phase 5 — Verifikation

- Option 1: `git log --oneline -3` zeigt Merge auf `<base>`, Tests grün, `git branch --list <name>` leer.
- Option 2: `gh pr view` bzw. Push-Output zeigt Branch upstream.
- Option 4: Branch weg, `<base>` unverändert (`git status` clean).

## Quick-Reference

| Option | Merge | Push | Branch bleibt | Branch gelöscht |
|---|---|---|---|---|
| 1. Lokal mergen | ja | – | – | ja (`-d`) |
| 2. PR | – | ja | ja | – |
| 3. Behalten | – | – | ja | – |
| 4. Verwerfen | – | – | – | ja (`-D`, nach Confirmation) |

## Red Flags

- **Nie** mit roten Tests mergen oder Optionen anbieten.
- **Nie** force-push ohne expliziten Auftrag von der Nutzer.
- **Nie** löschen ohne vorher die Commit-Liste gezeigt zu haben; Option 4 nur mit getipptem `verwerfen`.
- `-D` ausschließlich in Option 4 — sonst immer `-d` (Merge-Beweis).
- Offene Frage („was soll ich jetzt tun?") statt Menü = Anti-Pattern.

## Zukunft: Worktree-Abschluss (geerntet aus superpowers:finishing-a-development-branch v6.1.1)

Sobald der Nutzer mit Git-Worktrees bzw. nativen EnterWorktree/ExitWorktree-Tools arbeitet, gilt zusätzlich: Worktree-Erkennung via `git rev-parse --git-dir` vs. `--git-common-dir` (ungleich = Worktree). Cleanup-Regeln: nur selbst angelegte Worktrees (Pfad unter `.worktrees/`) entfernen — harness-verwaltete via ExitWorktree verlassen, nie manuell löschen; `git worktree remove` nie von innerhalb des Worktrees (erst `cd` zum Main-Repo-Root); Reihenfolge Merge verifizieren → `git worktree remove` → `git branch -d` → `git worktree prune`; bei Optionen PR/Behalten den Worktree stehen lassen.

Sonderfall **Detached HEAD** (kein Branch ausgecheckt, z.B. nach Worktree-Session): Merge-Option entfällt — genau 3 Optionen anbieten: (1) als neuen Branch pushen (`git checkout -b <name>` + push, PR falls Remote), (2) lokal als Branch sichern (`git checkout -b <name>`), (3) verwerfen (Typed-Confirmation). Kein Cleanup bei extern verwalteten Checkouts.

## Beispiel-Triggers

- `/branch-finish` — aktuellen Branch abschließen
- `/branch-finish feature/sse-retry` — benannten Branch abschließen
- „Der Branch ist fertig, wie mach ich weiter?"

## Changelog

- **v1.0.0** (2026-07-21): Neuanlage — geerntet aus superpowers:finishing-a-development-branch v6.1.1 (Test-Gate, exaktes Optionen-Menü, Merge-vor-Delete-Reihenfolge, `-d`-als-Verifikation, Typed-Discard-Confirmation, Worktree-Cleanup als Zukunfts-Absatz), adaptiert an des Nutzers Realität: Solo-Dev, meist kein Remote/PR, Syncthing-Sync mit git pro Seite.
