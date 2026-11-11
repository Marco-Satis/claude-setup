# Setup-Konsistenz über alle Projekte (Global Rule)

> der Nutzer-Entscheid 2026-11-11: „Ich will eine durchgehende Konsistenz meines Setups in allen Projekten.“
> Anlass: Nach der Umstellung auf ein Gedächtnis (27.10.) verwiesen Projekt-CLAUDE.md weiter auf
> Datei-Memories und auf mcp als „semantische Memory mit allen Sessions“.

## Kernregel

1. **Gemeinsames gehört nicht in Projekt-CLAUDE.md.** Regeln, die für alle Projekte gelten, stehen in
   `~/.claude/rules/` (synct PC↔netcup) bzw. in der globalen `CLAUDE.md` der Maschine. Eine
   Projekt-CLAUDE.md enthält nur Projektspezifisches und verweist sonst auf `wz find` oder die Rule.
2. **Überholt eine Setup-Änderung eine Aussage, wird sie überall nachgezogen**, im selben Arbeitsgang:
   - Muster für die alte Aussage in `~/.claude/scripts/claude_md_drift_muster.json` ergänzen (`id`, `seit`,
     `regex`, `ersatz`).
   - `python3 ~/.claude/scripts/claude_md_konsistenz.py` auf netcup laufen lassen und jeden Fund fixen
     (Backup `.bak.pre-konsistenz.<ts>`, minimale Änderung).
   - PC: Auftrag an die PC-Skills-Session (`SendMessage` an „Skills/Hooks/Agents/Prompts“), dort dasselbe
     Skript laufen zu lassen, die Funde zu fixen und die PC-globale `CLAUDE.md` abzugleichen (synct nicht).
   - Globale `CLAUDE.md`: Die netcup-Fassung ist schlank, die PC-Fassung voll. Abschnitte, die auf beiden
     gelten (Memory-Konvention, Universelle Regeln), werden inhaltlich gleich gehalten.
3. Zuständig ist die Skills/Hooks/Agents/Prompts-Session. des Nutzers Freigabe vom 11.11. deckt
   Konsistenz-Edits an fremden Projekt-CLAUDE.md ab, **nicht** inhaltliche Änderungen am Projekt.
   Vor dem Edit die Änderungszeit prüfen: wurde die Datei in den letzten 30 min geändert, arbeitet dort
   eine Session; dann der Session melden statt editieren (Session-Disziplin).

## Kontrolle

- Wöchentlich Mo 07:20 läuft `claude_md_konsistenz.py --report` (Routine `claude_md_konsistenz`).
  Funde stehen unter BRAUCHT im Report.
- Ausgenommen sind Archive, Backups, Fremd-Repos (`ref/`, Plugins, Worktrees) und `uym-setup/deploy/`
  (beschreibt die eigene Memory-Instanz der UYM-Nutzer, nicht des Nutzers Setup).
