# Öffentliches Setup-Repo aktuell halten (Global Rule)

> der Nutzer-Auftrag 2026-10-20: „Aktualisiere unser Repo, und zukünftig immer, wenn wir am Setup arbeiten."
> Repo: `~/projects/claude-setup` → GitHub `Marco-Satis/claude-setup` (**öffentlich**).

## Wann

Am Ende jeder Arbeitseinheit, die Skills, Agents, Hooks, Rules, Templates oder die kuratierten
Betriebs-Skripte unter `~/.claude` geändert hat — also immer dann, wenn auch eine `setup-change`-Memory
fällig ist. Zuständig ist die **Skills/Hooks/Agents/Prompts-Session auf netcup**. Andere Sessions
melden Setup-Änderungen dorthin (Session-Disziplin) und pushen nicht selbst.

## Wie

```bash
python3 -I ~/.claude/scripts/setup_repo_sync.py          # kopieren, bereinigen, prüfen
git -C ~/projects/claude-setup status --short            # Änderungen ansehen
```

- **Exit 0 (0 Befunde):** README-Zählungen prüfen, dann `git add -A`, Commit (deutsch, was + warum),
  `git push`. Pre-Commit-Hooks (detect-secrets) nie mit `--no-verify` umgehen.
- **Exit 2 (Befunde):** nichts committen. Befund beheben (Ersetzung in
  `~/.claude/secrets/setup_repo_sanitize.json` ergänzen, Datei auf die Denylist im Skript setzen oder
  die Quelle bereinigen), erneut laufen lassen. Unklarer Fall → der Nutzer fragen.
- Neue Skills mit Personendaten (wie `bewerbung`) gehören auf die `DENY`-Liste in `setup_repo_sync.py`.
- Größere Neuaufnahmen (neuer Skill, neue Agent-Gruppe): vor dem Push den Diff einmal unabhängig
  gegenlesen lassen (Secrets/Infra, Personendaten, Lizenzen fremder Teile).

## Grenzen

- Die Ersetzungsliste enthält private Originalwerte und liegt deshalb nur in `~/.claude/secrets/`
  (netcup, 600, synct nicht). Sie kommt nie ins Repo.
- `settings.json`, `secrets/`, Logs, Reports, Projekte und Laufzeitdaten sind nie Teil des Repos.
- Schlägt der Push am Classifier fehl: der Nutzer den fertigen Befehl nennen, nicht umgehen.
