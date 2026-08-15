#!/usr/bin/env bash
# RC launcher: resume last session in cwd (--continue) across host restarts.
# Preserves session-id + chat context. Starts a FRESH session ONLY if there is
# genuinely nothing to resume - never on signal-termination or transient failure.
name="$1"
BIN="$HOME/.local/bin/claude"
# Trust-Guard (2026-08-14): CLI >=2.1.232 verlangt Workspace-Trust, sobald das
# Projekt eine .claude/settings.json traegt — headless kann den Dialog niemand
# beantworten (Incident: 453-Restart-Crash-Loop, discord 2,5 h down). Der Guard
# ergaenzt den Eintrag additiv+atomar+geflockt und ist best-effort (Exit immer 0).
# Absoluter Interpreter-Pfad: systemd-user-PATH ist nicht der Login-PATH.
/usr/bin/python3 $HOME/.claude/rc-trust-guard.py "$PWD" || true
# Terminated by systemd (SIGTERM/INT) -> exit quietly, let systemd re-run launcher.
trap "exit 143" TERM INT
for attempt in 1 2 3; do
  start=$(date +%s)
  "$BIN" remote-control --name "$name" --continue --permission-mode auto
  rc=$?
  end=$(date +%s)
  # Ran a while, or was signaled -> normal lifecycle, do NOT fall back to fresh.
  if [ "$rc" -ge 128 ] || [ $((end - start)) -ge 15 ]; then
    exit "$rc"
  fi
  # Fast non-signal failure = transient lock/contention or no-session -> retry.
  sleep 3
done
# Resume kept failing fast after retries -> genuinely no resumable session.
exec "$BIN" remote-control --name "$name" --permission-mode auto
