# Hooks — Verdrahtung

Die `settings.json` ist nicht Teil dieses Repos: sie enthält maschinenspezifische Pfade
und Berechtigungen. Diese Tabelle ersetzt sie als Referenz — sie wird bei jedem Sync aus der
real laufenden Konfiguration erzeugt und zeigt, an welchem Event jeder Hook hängt.

Ein Hook wird eingehängt, indem in `~/.claude/settings.json` unter `hooks.<Event>` ein
Eintrag mit `type: "command"` und dem Aufruf steht. Rückgabe über stdout als JSON;
`{"systemMessage": "..."}` erscheint im nächsten Turn als injizierte Notiz.


## SessionStart

| Hook | Matcher | Timeout | Zweck |
|---|---|---|---|
| `context_bundle_loader.py` | `startup|resume|clear|compact|fork` | 5 | SessionStart-Hook: injiziert einen Index der Projekt-Wissens-Bundles. |
| `backup_health_check.py` | `startup|resume|clear|fork` | 10 | SessionStart Hook: warnt wenn das Memory-DB-Backup veraltet oder fehlgeschlagen ist. |
| `memory_start_probe.py` | `startup|resume|clear|fork` | 10 | SessionStart Hook: merkt sich ob der Memory-Service beim Session-Start erreichbar war. |
| `reap_orphan_graphify.py` | `startup|resume|clear|fork` | 5 | SessionStart-Hook: raeumt verwaiste graphify.serve-MCP-Prozesse weg. |
| `problems_banner.py` | `startup|resume|clear|fork` | 5 | SessionStart Hook: zeigt offene Probleme aus dem Problem-Tracker. |
| `project_scaffold.py` | `startup|resume|clear|fork` | 10 | SessionStart-Hook: richtet fehlende Projektstruktur automatisch ein. |
| `syncthing_project_notice.py` | `startup|resume|clear|fork` | 10 | SessionStart-Hook: Sync-Status-Hinweis fuer Sessions in Syncthing-gesyncten Ordnern. |
| `routine_digest.py` | `startup|resume|clear|fork` | — | routine_digest.py — SessionStart-Hook: Routine-Lage in die Session injizieren. |
| `handoff_inject.py` | `startup|resume|clear|fork` | 10 | SessionStart-Hook: ungelesene Handoffs im Arbeitsverzeichnis melden. |
| `rc-session-resume.py` | `startup|resume|clear|fork` | 10 | SessionStart (resume/startup): aktiv den letzten Stand injizieren, damit eine |

## UserPromptSubmit

| Hook | Matcher | Timeout | Zweck |
|---|---|---|---|
| `context_threshold_warning.py` | `—` | 5 | UserPromptSubmit Hook: aktiv-erzwingt /compact bei steigender Context-Auslastung. |
| `secret_leak_detector.py` | `—` | 5 | UserPromptSubmit Hook: erkennt API-Keys / Tokens / Secrets im User-Prompt. |
| `memory_delta_watch.py` | `—` | 10 | UserPromptSubmit Hook: erkennt Setup-Aenderungen anderer Sessions mid-session. |
| `agent_inbox.py` | `—` | 6 | UserPromptSubmit + PostToolUse Hook: stellt Nachrichten von Codex (und anderen Agents) zu. |
| `ultracode_advisor.py` | `—` | 10 | UserPromptSubmit-Hook: erinnert an ultracode/Multi-Agent-Schwarm wenn ein Task |
| `fastmode_hint.py` | `—` | 10 | UserPromptSubmit-Hook: weist auf Fast Mode (/fast) hin wenn sinnvoll. |

## PreToolUse

| Hook | Matcher | Timeout | Zweck |
|---|---|---|---|
| `destructive_command_blocker.py` | `Bash` | 5 | PreToolUse-Hook (Bash): blockt destruktive Kommandos via exit 2. |
| `grep_complexity_guard.py` | `Bash` | 5 | grep_complexity_guard.py — blockt das grep-Muster, das den Server lahmgelegt hat. |
| `important_edit_reminder.py` | `Edit|Write` | 5 | PreToolUse Hook (Edit/Write): Backup-Reminder bei wichtigen Files. |
| `secret_write_guard.py` | `Write|Edit|MultiEdit|Bash` | 5 | PreToolUse Hook: blockt Secrets die CLAUDE in Dateien/Commands schreiben will. |
| `git_push_reminder.py` | `Bash` | 5 | PreToolUse Hook (Bash): Reminder bei git push wegen Token-Push-Verbot. |
| `enforce_read_tool.py` | `Bash` | 5 | PreToolUse-Hook (Bash): blockt REINE Datei-Reads via Shell und erzwingt das Read-Tool. |

## PostToolUse

| Hook | Matcher | Timeout | Zweck |
|---|---|---|---|
| `review_reminder.py` | `Edit|Write` | 10 | PostToolUse Hook (Edit/Write): Review-Reminder bei sicherheits-/integritäts- |
| `agent_inbox.py` | `—` | 6 | UserPromptSubmit + PostToolUse Hook: stellt Nachrichten von Codex (und anderen Agents) zu. |

## PostToolUseFailure

| Hook | Matcher | Timeout | Zweck |
|---|---|---|---|
| `toolfailure_memory_logger.py` | `—` | 8 | PostToolUseFailure Hook: Tool-Fehler loggen, Memory-Write-Fails aktiv flaggen. |
| `stuck_detector.py` | `*` | — | PostToolUseFailure Hook: Festgefahren-Erkennung -> Pflicht-Websuche. |

## Stop

| Hook | Matcher | Timeout | Zweck |
|---|---|---|---|
| `session_logger.py` | `—` | 10 | Stop Hook: loggt Session-Statistiken + persistiert Tier-1-Session-Memory. |
| `context_canary.py` | `—` | — | Stop-Hook: Context-Canary — erkennt stillen Instruktions-Drift vor der ersten Halluzination. |

## StopFailure

| Hook | Matcher | Timeout | Zweck |
|---|---|---|---|
| `stopfailure_logger.py` | `—` | 8 | StopFailure Hook: API-Fehler am Turn-Ende loggen (rate_limit, overloaded, auth). |

## SubagentStop

| Hook | Matcher | Timeout | Zweck |
|---|---|---|---|
| `subagent_tracer.py` | `—` | 10 | SubagentStop-Hook: tracet jeden Sub-Agent-Run in eine JSONL. |

## PreCompact

| Hook | Matcher | Timeout | Zweck |
|---|---|---|---|
| `precompact_backup.py` | `—` | 15 | PreCompact Hook: Backup juengstes STATUS + Review-Master + Backlog vor Compact. |
| `precompact_memory.py` | `—` | 12 | PreCompact Hook: erzwingt einen Session-Checkpoint-Memory-Write vor JEDEM /compact. |

## SessionEnd

| Hook | Matcher | Timeout | Zweck |
|---|---|---|---|
| `session_end.py` | `—` | 12 | SessionEnd-Hook: finaler Session-Rollup-Memory beim echten Session-Ende. |

## Notification

| Hook | Matcher | Timeout | Zweck |
|---|---|---|---|
| `discord_notify.py` | `^(?!agent_needs_input$)` | — | Notification Hook: Claude-Benachrichtigungen in den kanonischen Discord-Kanal. |
| `bg_needs_input_notify.py` | `agent_needs_input` | 30 | Notification-Hook: Discord-Meldung, wenn eine Hintergrund-Session auf Eingabe wartet. |

## Nicht in dieser Tabelle

Diese Hooks der laufenden Konfiguration fehlen bewusst (installationsgebunden oder persönlich): `knapp_de.py`.

Die Dateien unter `hooks/tests/` sind Smoke-Tests der Hooks selbst und werden nicht eingehängt.
