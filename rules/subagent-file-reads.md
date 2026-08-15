# Subagent-Datei-Reads (Global Rule)

Auto-applied bei Sub-Agent-Dispatch (review, full-audit, security-audit, investigate, alle Reviewer).

## Regel
Sub-Agents lesen Datei-Inhalte **ausschließlich via `Read`-Tool** (bzw. `Grep`/`Glob` für Suche).
**Nie** `Get-Content`, `cat`, `head`, `tail`, `type`, `sed -n '…p'`, `awk '{print}'` via `Bash`/`PowerShell` zum Datei-Lesen.
(`sed -i` als Edit und `sed`/`awk` als Filter in Pipes hinter echten Befehlen bleiben erlaubt; `grep` via Bash ist als Suche geduldet, bevorzugt aber Grep-Tool. Der enforce_read_tool-Hook blockt die Pure-Read-Formen seit 2026-07-21 auch technisch.)

## Begründung
der Nutzer Setup hat eine Read-Deny-/Security-Flag-Regel: Datei-Reads über Shell-Befehle triggern
einen Security-Flag (p-a52a0b0780). Das `Read`-Tool integriert sich in Permission-UI + Datei-State-
Tracking; Shell-`cat` umgeht das. Bash bleibt erlaubt für echte Befehle (Tests, git, Build) — nur
nicht zum reinen Datei-Lesen.

## Für Dispatch-Prompts
Jeder Reviewer-/Audit-Subagent-Prompt enthält die Zeile:
> Datei-Inhalte NUR via Read-Tool lesen (nie Get-Content/cat/head/tail/sed/awk via Bash/PowerShell) — sonst Security-Flag.
