# Trigger-Eval site-anatomy — 2026-10-20

Werkzeug: `~/.claude/scripts/skill_trigger_eval.sh` (run_eval.py aus skill-creator), seriell (`--num-workers 1`).

| Lauf | Description | Soll-Treffer (9) | Held-out (4) | Beinahe-Treffer (10, sollen NICHT) |
|---|---|---|---|---|
| 1–3 | v0.2.0 bzw. erste Schärfung, **parallel** (10 Worker) | 1/9 bzw. 0/9 | – / 0/4 | 10/10 |
| 4 | erste Schärfung, seriell, 1 Lauf je Anfrage | 8/9 | 3/4 | 9/10 (otto.de-technisch löste aus) |
| 5 | zweite Schärfung (leanrea-Grenze in der Description), 3 Läufe je Anfrage | – | notion.so 2/3 | otto.de 3/3 (weiter falsch) |
| 6 | + Abgrenzungssatz in leanrea/ui-critique/design-html, 3 Läufe | linear.app 0/3 (s. u.) | – | otto.de 0/3, filedrop-Security 0/3 |

**Parallel-Artefakt:** Bei 10 Workern liegen 10 gleich beschriebene Test-Commands im selben Ordner;
Claude wählt die ID eines anderen Laufs → als Fehlschlag gezählt. Wrapper seit 20.10. seriell per Default.

**linear.app („…und übertrag das auf meine Farben")** gilt als Grenze des Werkzeugs, nicht der Description:
Claude sucht zuerst per Bash im Projekt nach „meinen Farben" und ruft den Skill danach auf. run_eval.py zählt
nur den ERSTEN Tool-Aufruf. Einzelprobe ohne Partial-Stream: erster Aufruf = Skill site-anatomy.

Stand nach Lauf 6: alle Beinahe-Treffer bestanden; Soll-Treffer 8/9 + Held-out 4/4 (Lauf 4/5).
