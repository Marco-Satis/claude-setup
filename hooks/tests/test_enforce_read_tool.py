#!/usr/bin/env python3
"""Regressionstests fuer hooks/enforce_read_tool.py (v2, 14.11.2026).

Aufruf: python3 ~/.claude/hooks/tests/test_enforce_read_tool.py   (Exit 0 = alles gruen)
Jeder Fall laeuft echt per stdin gegen den Hook; Soll True = Exit 2 (geblockt), False = Exit 0.
M<n> = Glied aus der Messung REGEL_EINHALTUNG_2026-11-14.md (145 durchgelaufene Shell-Reads).
"""
import json
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "enforce_read_tool.py")

# Ketten-Varianten aus der Messung (105 Ketten, 21 mit 2>/dev/null, 19 Variablenpfade)
CHAINS = [
    ("cd ~/projects/x && sed -n 1,20p PROGRESS.md", True),
    ('cd "$HOME/projects/Skills_&_Co" && sed -n 1,8p PROGRESS.md', True),
    ("cat f 2>/dev/null", True),
    ("cat .stignore 2>/dev/null || echo fehlt", True),
    ("head f; tail g", True),
    ("echo ---; cat f", True),
    ("ls -la x && cat x", True),
    ("[ -f x ] && cat x || echo missing", True),
    ("if [ -f x ]; then cat x; fi", True),
    ('for f in a.md b.md; do echo "== $f"; head -3 "$f"; done', True),
    ("( cd /tmp && tail -5 out.log )", True),
    ("tail -n 400 ~/.claude/logs/wissen_mcp_audit.jsonl 2>/dev/null", True),
    ("tail -3 /var/log/x.log 2>&1", True),
    ("git status --short; sed -n '30p' $f", True),
    ('cat "$HOME/r/uym_$(date +%F).md"', True),
    ("LC_ALL=C cat f", True),
    ("timeout 5 cat f", True),
    ("awk '{print $1}' f.txt", True),
    ("awk 'NR>=5&&NR<=9' f.txt", True),
    ("cat < f.txt", True),
    ("/usr/bin/cat f", True),
    ("'cat' f", True),
    ("sed 's/a/b/' f", True),
    ("Get-Content f.txt", True),
    ("gc f.txt", True),
]

ALLOW = [
    ("git log --oneline | head", False),
    ("ls | sed -n 1,5p", False),
    ("cat f | grep x", False),
    ("cd x && git log -5 | head -3", False),
    ("cat a b > c", False),
    ("cat f >> g", False),
    ("cat > f <<'EOF'\nhallo\nEOF", False),
    ("cat <<EOF\n$x\nEOF", False),
    ("python3 - <<'EOF'\nimport os\ncat foo\nhead bar\nEOF", False),
    ("x=$(cat f); echo $x", False),
    ('echo "$(cat f)"', False),
    ("diff <(cat a) <(cat b)", False),
    ("tail -f app.log", False),
    ("tail -F app.log", False),
    ("sed -i 's/a/b/' f", False),
    ("sed -n 1p", False),
    ("awk '{s+=$1} END{print s}' nums.txt", False),
    ("awk -F: '$3 > 1000 {print $1}' /etc/passwd", False),
    ("sudo cat /etc/shadow", False),
    ("sudo -n /bin/su - botuser -c 'cat x'", False),
    ("bash -c 'cat f'", False),
    ("grep -n foo f.py", False),
    ("rg foo", False),
    ("type python3", False),
    ('echo "a; cat b"', False),
    ("python3 -c 'print(1); cat = 2'", False),
    ("find . -name '*.py' -exec cat {} \\;", False),
    ("while read l; do echo $l; done < f.txt", False),
    ("cat", False),
    ("head -n 5", False),
    ("cat -", False),
    ("cmd 2>&1 | tail -20", False),
    ("make test |& tail -5", False),
    ("cat f >/dev/null", False),
    ("echo ok", False),
    ("bash run.sh; cat /dev/null", False),
    ("", False),
]

MEASURED = [
    ('tail -3 /opt/fritzbox-monitor/cron.log 2>&1', True),  # M0
    ('tail -5 /opt/fritzbox-monitor/cron.log', True),  # M1
    ('tail -n 3 /opt/fritzbox-monitor/docs/docsis_stats.csv 2>&1', True),  # M2
    ('head -c 300 cron.log', True),  # M3
    ('sed -n 476,510p scripts/pipeline_autoupdate.py', True),  # M4
    ('sed -n 585,625p scripts/pipeline_autoupdate.py', True),  # M5
    ('sed -n 545,583p scripts/pipeline_autoupdate.py', True),  # M6
    ('sed -n 1,20p PROGRESS.md', True),  # M7
    ('sed -n 1,8p PROGRESS.md', True),  # M8
    ('tail -3 logs/autoupdate.log', True),  # M9
    ('sed -n 527,540p scripts/pipeline_autoupdate.py', True),  # M10
    ('sed -n 43p CLAUDE.md', True),  # M11
    ("sed -n '309,320p' DrsImportService.cs", True),  # M12
    ('head -3 PROGRESS_weapon_db.md', True),  # M13
    ('head -c 600 "robots_$h.txt" 2>/dev/null', True),  # M14
    ('head -5 cod_db_repo/LICENSE 2>/dev/null', True),  # M15
    ('cat /etc/systemd/system/recon-bot.service.d/satisfactory-rw.conf 2>/dev/null', True),  # M16
    ('sed -n 418,426p mail.py', True),  # M17
    ('sed -n 215,220p assistant.py', True),  # M18
    ('tail -3 PROGRESS.md', True),  # M19
    ("sed -n '734p' SKILL.md", True),  # M20
    ("sed -n '784,792p' ~/.claude/skills/lyra/SKILL.md", True),  # M21
    ('tail -1 /tmp/claude-1001/-home-marco-projects-Skills---Co/d7b69fbc-26f6-59b5-8292-162def4b17ef/scratchpad/konsistenz_lauf.txt', True),  # M22
    ("sed -n '43p' ~/n8n_stack/CLAUDE.md", True),  # M23
    ("sed -n '20,26p' ~/.claude/rules/design-qualitaet.md", True),  # M24
    ("sed -n '30p' $f", True),  # M25
    ('tail -n 400 ~/.claude/logs/wissen_mcp_audit.jsonl 2>/dev/null', True),  # M26
    ('tail -n 3 ~/.claude/logs/wissen_mcp_audit.jsonl', True),  # M27
    ('tail -1 ~/.claude/logs/rc-health.log', True),  # M28
    ('head -30 audit_cron.txt', True),  # M29
    ('cat calls', True),  # M30
    ('sed -n 556p cso/SKILL.md', True),  # M31
    ('cat ~/.local/share/trading-bot/d-probe-replay/replay.log', True),  # M32
    ('cat .stignore 2>/dev/null', True),  # M33
    ('sed -n 26p tests/test_crisis.py', True),  # M34
    ("sudo head -10 /etc/nftables.conf'", False),  # M35
    ('sudo cat /home/$u/.local/state/uym-setup/applied-commit', False),  # M36
    ('sed -n 1,40p ~/.claude/scripts/routine_md.sh', True),  # M37
    ('cat "$HOME/projects/Skills_&_Co/ROUTINE_REPORTS/uym_server_report_$(date +%F).md"', True),  # M38
    ('sed -n 105,123p AVV-Entwurf_Agentur-Marco_v1.md', True),  # M39
    ('cat /etc/apt/apt.conf.d/20auto-upgrades', True),  # M40
    ('sed -n 16,26p FEEDBACK/inbox.md', True),  # M41
    ('sed -n 1,200p tagesstruktur/SKILL.md', True),  # M42
    ('cat "$WD/ergebnis/measure_errors.json"', True),  # M43
    ('sed -n 1,60p WHATSAPP_2026-11-07_entwurf.md', True),  # M44
    ('cat $S/claudeops.new', True),  # M45
    ('sed -n 25,90p feedback_pull.py', True),  # M46
    ('cat /etc/debian_version', True),  # M47
    ('sed -n 55,62p AVV-Entwurf_Agentur-Marco_v1.md', True),  # M48
    ('cat "$HOME/projects/Skills_&_Co/ROUTINE_REPORTS/uym_server_report_2026-11-14.md"', True),  # M49
    ("sed -n '255,275p' bots/operator_bot.py", True),  # M50
    ('tail -5 /tmp/claude_g4_out.txt', True),  # M51
    ("sed -n '245,270p' cogs/shutdown_cog.py", True),  # M52
    ('cat /tmp/claude-1001/nachtlauf_g3-monitoring/final.txt', True),  # M53
    ('tail -5 /tmp/claude_g1_out.txt', True),  # M54
    ("sed -n '1,25p' tests/$f.py", True),  # M55
    ('tail -4 $f', True),  # M56
    ("sed -n '425,440p' cogs/scheduler_cog.py", True),  # M57
    ('cat /home/botuser/Discord_Bots/venv/pyvenv.cfg 2>&1', True),  # M58
    ('cat .gitignore', True),  # M59
    ('cat utils/permissions.py', True),  # M60
    ('tail -3 /tmp/nl_g6_out.txt', True),  # M61
    ("sed -n '79,100p' cogs/temp_voice_cog.py", True),  # M62
    ('cat /tmp/claude-1001/-home-marco-projects-Discord-Bots/62cbf0dc-dc3d-5d75-84f4-f3e926efd3d0/tasks/bj7jwh63m.output 2>/dev/null', True),  # M63
    ('cat /tmp/claude-1001/-home-marco-projects-Discord-Bots/62cbf0dc-dc3d-5d75-84f4-f3e926efd3d0/tasks/btjkq57hf.output', True),  # M64
    ('sed -n 100,112p cogs/notify_cog.py', True),  # M65
    ("sed -n '76,95p' utils/config.py", True),  # M66
    ("sed -n '255,270p' web/routes/config_route.py", True),  # M67
    ("sed -n '270,290p' web/templates/config.html", True),  # M68
    ("sed -n '468p' cogs/pipeline_control_cog.py", True),  # M69
    ("sed -n '208,232p' web/routes/dashboard.py", True),  # M70
    ('cat /tmp/claude-1001/-home-marco-projects-Discord-Bots/62cbf0dc-dc3d-5d75-84f4-f3e926efd3d0/tasks/b3x1rtw37.output', True),  # M71
    ("sed -n '175,220p' web/routes/webhook_route.py", True),  # M72
    ("sed -n '250,275p' web/routes/config_route.py", True),  # M73
    ("sed -n '110,120p' web/navigation.py", True),  # M74
    ("sed -n '268,282p' cogs/notify_cog.py", True),  # M75
    ("sed -n '37,49p' docs/UMBAU_PLAN_2026-10-19.md", True),  # M76
    ("sed -n '120,132p' $HOME/projects/Discord_Bots/CHANGELOG.md", True),  # M77
    ('cat VERSION 2>/dev/null', True),  # M78
    ("sed -n '344,382p' cogs/satisfactory_cog.py", True),  # M79
    ("sed -n '855,885p' web/routes/server_detail_route.py", True),  # M80
    ("sed -n '320,336p' modules/monitoring/port_monitor.py", True),  # M81
    ('cat /tmp/claude-1001/nachtlauf_g7-web/baseline2.txt 2>/dev/null', True),  # M82
    ("sed -n '1,40p' web/routes/marshal_bot_route.py", True),  # M83
    ('cat /tmp/claude-1001/nachtlauf_g7-web/final.txt', True),  # M84
    ('sed -n 470,490p cogs/satisfactory_cog.py', True),  # M85
    ("sed -n '112p' CLAUDE.md", True),  # M86
    ("sed -n '15p' docs/OFFEN.md", True),  # M87
    ("sed -n '220,240p' bots/operator_bot.py", True),  # M88
    ('sed -n 3355,3385p bots/recon_bot.py', True),  # M89
    ('cat tests/_umgebung.py 2>/dev/null', True),  # M90
    ("sed -n '80,95p' bots/recon_bot.py", True),  # M91
    ("sed -n '25,60p' utils/async_tasks.py", True),  # M92
    ("sed -n '1,12p' bots/operator_bot.py", True),  # M93
    ('cat /tmp/claude-1001/nachtlauf_g9-kern/suite_ergebnis.txt 2>/dev/null', True),  # M94
    ('cat /usr/games/steamcmd 2>/dev/null', True),  # M95
    ('tail -3 /var/log/discordbots-deploy.log 2>&1', True),  # M96
    ('head -30 tests/test_migration_v12.py', True),  # M97
    ('head -60 tests/test_csrf_middleware.py', True),  # M98
    ('cat VERSION', True),  # M99
    ('cat /tmp/claude-1001/nachtlauf_g10-doku/geaendert.txt', True),  # M100
    ('sed -n 525,545p bots/recon_bot.py', True),  # M101
    ("tail -3 /tmp/ti_g12.out'", False),  # M102
    ('cat .claude/launch.json 2>/dev/null', True),  # M103
    ("sed -n '20,45p' ~/.claude/plugins/cache/impeccable/impeccable/3.9.1/skills/impeccable/reference/brand.md 2>/dev/null", True),  # M104
    ('cat old_errors.txt', True),  # M105
    ('tail -c 400 fx_pruefen.log', True),  # M106
    ('cat catch.log', True),  # M107
    ('head -c 150 detkill.log', True),  # M108
    ('tail -n 2 $SP/t/fx_final.log', True),  # M109
    ("sed -n '1990,2040p' chrome_verlauf_01.txt", True),  # M110
    ('cat ~/.claude/secrets/cron_token.env', True),  # M111
    ('tail -12 ~/.claude/logs/projekt_kompass.log', True),  # M112
    ('tail -3 ~/.claude/logs/rc-health.log 2>/dev/null', True),  # M113
    ('sed -n 255,285p cogs/moderation_cog.py', True),  # M114
    ('cat ~/wissen/_schema/schema.json', True),  # M115
    ('tail -4 $S/t_wz.txt $S/t_m.txt $S/t_codex.txt', True),  # M116
    ('cat err.txt', True),  # M117
    ('head -9 t3b.txt', True),  # M118
    ('head -c 30 rc-health.log', True),  # M119
    ('tail -5 ~/.claude/logs/wissen_pflege.log 2>/dev/null', True),  # M120
    ("sed -n '84,96p' permission-modes.md", True),  # M121
    ('cat $S/mail.log', True),  # M122
    ('cat $HOME/n8n_stack/.gitignore 2>/dev/null', True),  # M123
    ('tail -30 classified.txt', True),  # M124
    ('tail -12 classified.txt', True),  # M125
    ("sed -n '2054p' $D/hooks.md", True),  # M126
    ('head -12 ~/.claude/agents/untrusted-reader.md', True),  # M127
    ("sed -n '400,470p' README.md", True),  # M128
    ("sed -n '50,72p' $HOME/.claude/rc-autoupdate.sh", True),  # M129
    ('cat $D/srv/requests.log', True),  # M130
    ('cat $D/srv/requests.log', True),  # M131
    ('cat $D/srv/requests.log', True),  # M132
    ('tail -1 $D/T1_T8.log', True),  # M133
    ('cat $D/T7.log', True),  # M134
    ('cat "$Z/zuordnung.txt"', True),  # M135
    ('tail -40 "$SP/b1/out6.log" 2>/dev/null', True),  # M136
    ('cat /proc/self/cgroup', True),  # M137
    ('sed -n 1,25p test_codex_adapter.py', True),  # M138
    ('tail -2 $T/S.md', True),  # M139
    ('cat ~/.claude/logs/agent_os_montag.log', True),  # M140
    ('tail -1 ~/.claude/logs/wissen_mcp_audit.jsonl', True),  # M141
    ('sed -n 10,14p wz.py', True),  # M142
    ('cat golden_z_v1.jsonl.sha256', True),  # M143
    ('head -30 test_codex_adapter.py', True),  # M144

]


def run(cmd, payload=None):
    raw = payload if payload is not None else json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    p = subprocess.run([sys.executable, HOOK], input=raw, capture_output=True, text=True, timeout=10)
    return p.returncode


def main():
    fails = 0
    total = 0
    for group, cases in (("CHAINS", CHAINS), ("ALLOW", ALLOW), ("MEASURED", MEASURED)):
        for cmd, soll in cases:
            total += 1
            rc = run(cmd)
            ist = rc == 2
            if rc not in (0, 2) or ist != soll:
                fails += 1
                print(f"FAIL [{group}] soll={'block' if soll else 'allow'} rc={rc}: {cmd!r}")
    # Robustheit: leeres/kaputtes JSON, anderes Tool
    for raw in ("", "{kaputt", "[]", "null", json.dumps({"tool_name": "Read", "tool_input": {"file_path": "x"}})):
        total += 1
        if run(None, raw) != 0:
            fails += 1
            print(f"FAIL [ROBUST] rc!=0 fuer {raw!r}")
    print(f"enforce_read_tool: {total - fails}/{total} ok")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
