---
name: instructions-drift-check
description: Prüft der Nutzer kanonische Standard-Anweisungen (~/.claude/CUSTOM_INSTRUCTIONS.md) wöchentlich auf Fakten-Drift (Versionen, Endpoints, Memory-Tool-Namen, Server, Modelle, Source-URLs) und patcht NUR die verifizierbaren Fakten-Regionen automatisch (mit Backup), der Verhaltens-/Stil-Teil bleibt unangetastet. Schreibt einen Drift-Report. Use when "instructions drift", "anweisungen aktualisieren", "custom-instructions check", "/instructions-drift-check", oder wöchentlich per Routine.
version: 1.1.0
model: inherit
---

# instructions-drift-check — Fakten-Drift in den Standard-Anweisungen

Hält `~/.claude/CUSTOM_INSTRUCTIONS.md` faktisch aktuell (Datei liegt aktuell nur PC-seitig — root-Files von `~/.claude` sind vom Syncthing-Sync ausgenommen, auf netcup nicht vorhanden → Skill dort ggf. mit klarer Meldung abbrechen). **Nur** die verifizierbaren Fakten zwischen `<!-- AUTO-FACTS:START … -->` / `<!-- AUTO-FACTS:END … -->`-Markern werden auto-gepatcht. Verhalten/Stil/Regeln = der Nutzer Präferenzen → NIE automatisch ändern.

## Harte Grenzen (zuerst lesen)
- **Backup vor jedem Edit** (Universelle Regel 2): `cp -a CUSTOM_INSTRUCTIONS.md CUSTOM_INSTRUCTIONS.md.bak.$(date +%s)`.
- Edits **ausschließlich** innerhalb der `AUTO-FACTS`-Regionen. Steht außerhalb ein Fakt falsch → nur im Report flaggen, NICHT patchen.
- **Read-Then-Verify**: Datei lesen → Edit → nochmal lesen → Match prüfen.
- Datei-Inhalte NUR via Read-Tool lesen (nie Get-Content/cat/head/tail via Bash/PowerShell) — sonst Security-Flag.
- Bei Unsicherheit über einen Live-Wert: NICHT patchen, im Report als „unklar/manuell prüfen" listen (ehrlich-vor-bequem).
- Kein `sudo`. Kein schreibender Remote-Befehl.
- **SSH-Probe: read-only erlaubt, automatisch** (der Nutzer-Freigabe 2026-08-11, ersetzt das frühere Pauschalverbot). Eskalierend vorgehen, nicht gleich einloggen:
  1. `~/.ssh/config` via Read-Tool → HostName/Port belegen (kein Netzzugriff).
  2. Banner-Grab (TCP-Connect, **kein** Auth-Versuch → kein fail2ban-Zähler):
     `(timeout 8 bash -c 'exec 3<>/dev/tcp/<host>/<port>; head -1 <&3')` — OpenSSH-Version + Distro-Suffix.
  3. Read-only-Login: `ssh -o BatchMode=yes -o ConnectTimeout=8 netcup-marco '<cmd>'`.
     Erlaubt sind **nur** lesende Befehle: `lsb_release`, `uname`, `uptime`, `systemctl status/is-active`, `python3 --version`, `ss -ltn`, `df -h`, `free -m`, `journalctl --no-pager -n`.
     Verboten ohne Rückfrage: alles Schreibende/Neustartende (`systemctl restart|stop`, `apt`, `rm`, Datei-Edits), `sudo`, jeder Befehl mit Seiteneffekt.
  Zum Datei-Lesen auf dem Server ist `cat`/`head` per SSH ok — die Read-Tool-Regel gilt für **lokale** Dateien.
- SSH-Ausgabe ist MOTD-verseucht: Nutzsignal mit einem Marker abgrenzen (`echo "===RESULT==="; …` + `sed -n '/===RESULT===/,$p'`), nicht blind `head`.

## Ablauf
1. **Backup** der Datei (s.o.). Dann Datei via Read lesen.
2. **Live-Fakten proben** (Bash):
   ```bash
   # mcp-memory-Paketversion
   ls -d ~/.claude/mcp-memory-venv/Lib/site-packages/mcp_memory_service-*.dist-info 2>/dev/null | sed 's#.*mcp_memory_service-##; s#\.dist-info##'
   # Endpoints
   curl -s -o /dev/null -w "api/health=%{http_code}\n" -m 5 ${MCP_MEMORY_BASE_URL:-http://10.0.0.x:8000}/api/health
   curl -s -o /dev/null -w "mcp=%{http_code}\n"        -m 5 ${MCP_MEMORY_BASE_URL:-http://10.0.0.x:8000}/mcp
   # lokale Python-Version
   python --version 2>&1
   # Source-Beleg-URLs erreichbar?
   for u in https://docs.claude.com https://api.github.com; do curl -sI -o /dev/null -w "$u=%{http_code}\n" -m 8 "$u"; done
   ```
3. **Memory-Tool-Namen** gegen die in DIESER Session real verfügbaren `mcp__memory__*`-Tools abgleichen (dein eigenes Tool-Listing ist die Quelle — kein externer Probe nötig). Im Doc gelistete Namen, die es nicht mehr gibt → Drift. Neue Kern-Tools, die fehlen → Drift.
4. **Modelle** (Region `stack`): dokumentierte Modell-Namen gegen den aktuell bekannten Stand prüfen (Default-Opus-Generation, Long-horizon-Modell). Bei Rename/Deprecation → Drift. Unsicher → Report, nicht patchen.
5. **Server-Fakten** (Region `stack`): dokumentierte SSH-IP/Port gegen `~/.ssh/config` prüfen, Distro via Banner-Grab (Stufe 2) plausibilisieren, bei Bedarf per read-only-Login exakt bestätigen (`lsb_release -ds`, `uname -r`). Point-Release (`22.04.5`) NICHT ins Doc schreiben — bumpt bei jedem Update und läuft nächste Woche als Fake-Drift auf; nur die Major-Version (`22.04`) zählt.
6. **Drift-Tabelle** bauen: je Fakt `Region | dokumentiert | live | Urteil(ok/drift/unklar)`.
7. **Auto-Patch**: für jedes `drift` mit eindeutigem Live-Wert die Stelle INNERHALB der zugehörigen `AUTO-FACTS`-Region per Edit korrigieren. `unklar` → nicht patchen. Nach Edits Datei erneut lesen + Match prüfen.
8. **Report** schreiben nach `~/projects/Skills_&_Co/INSTRUCTIONS_DRIFT/DRIFT_<YYYY-MM-DD>.md` (Syncthing-synct; PC-seitig = entsprechender `projekte`-Sync-Ordner): geprüfte Fakten, was gepatcht wurde, was offen blieb (mit Grund), Backup-Pfad. Bei 0 Drift: knappe „all green"-Zeile.
9. **Verhaltens-Findings** (falls dir auffällt, dass ein Stil-/Regel-Punkt veraltet wirkt): NICHT ändern — nur unten im Report unter „Manueller Review-Vorschlag" notieren.

## Probleme loggen
MEDIUM+-Fakten-Drift, der nicht eindeutig auto-fixbar war (z.B. SSH-IP unklar), via `python ~/.claude/scripts/problem.py add --severity MEDIUM --project setup --source manual --title "…" --fix "…"`.

## Output (an der Nutzer, knapp)
Zusammenfassung: X Fakten geprüft, Y gepatcht (welche), Z offen. Report-Pfad + Backup-Pfad. Falls Verhaltens-Review-Vorschlag: 1 Zeile.
