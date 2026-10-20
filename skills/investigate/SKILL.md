---
name: investigate
version: 1.2.0
description: |
  Systematic debugging with root cause investigation. Four phases: investigate,
  analyze, hypothesize, implement. Iron Law: no fixes without root cause.
  Use when asked to "debug this", "fix this bug", "why is this broken",
  "investigate this error", or "root cause analysis".
  Proactively invoke this skill (do NOT debug directly) when the user reports
  errors, 500 errors, stack traces, unexpected behavior, "it was working
  yesterday", or is troubleshooting why something stopped working. (gstack-Port, standalone)
  Abgrenzung zu superpowers:systematic-debugging (Plugin, ueberlappender Trigger-Raum):
  /investigate ist des Nutzers kanonischer Debugging-Einstieg (standalone gstack-Port mit
  AskUserQuestion-Decision-Briefs + Plan-Mode-Integration). Bei /investigate-Aufruf
  oder Debugging-Intent NICHT zusaetzlich das superpowers-Pendant laden.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
  - WebSearch
triggers:
  - debug this
  - fix this bug
  - why is this broken
  - root cause analysis
  - investigate this error
---

## Skill Invocation During Plan Mode

If the user invokes this skill in plan mode, the skill takes precedence over generic plan mode behavior. **Treat the skill file as executable instructions, not reference.** Follow it step by step; the first AskUserQuestion is the workflow entering plan mode, not a violation of it. AskUserQuestion (any variant — `mcp__*__AskUserQuestion` or native; see "AskUserQuestion Format → Tool resolution") satisfies plan mode's end-of-turn requirement. If no variant is callable, the skill is BLOCKED — stop and report `BLOCKED — AskUserQuestion unavailable` per the AskUserQuestion Format rule. At a STOP point, stop immediately. Do not continue the workflow or call ExitPlanMode there. Call ExitPlanMode only after the skill workflow completes, or if the user tells you to cancel the skill or leave plan mode.

## AskUserQuestion Format

### Tool resolution (read first)

"AskUserQuestion" can resolve to two tools at runtime: the **host MCP variant** (e.g. `mcp__conductor__AskUserQuestion` — appears in your tool list when the host registers it) or the **native** Claude Code tool.

**Rule:** if any `mcp__*__AskUserQuestion` variant is in your tool list, prefer it. Hosts may disable native AUQ via `--disallowedTools AskUserQuestion` (Conductor does, by default) and route through their MCP variant; calling native there silently fails. Same questions/options shape; same decision-brief format applies.

**If no AskUserQuestion variant appears in your tool list, this skill is BLOCKED.** Stop, report `BLOCKED — AskUserQuestion unavailable`, and wait for the user. Do not write decisions to the plan file as a substitute, do not emit them as prose and stop, and do not silently auto-decide.

### Format

Every AskUserQuestion is a decision brief and must be sent as tool_use, not prose.

```
D<N> — <one-line question title>
Project/branch/task: <1 short grounding sentence using the current branch>
ELI10: <plain English a 16-year-old could follow, 2-4 sentences, name the stakes>
Stakes if we pick wrong: <one sentence on what breaks, what user sees, what's lost>
Recommendation: <choice> because <one-line reason>
Completeness: A=X/10, B=Y/10   (or: Note: options differ in kind, not coverage — no completeness score)
Pros / cons:
A) <option label> (recommended)
  ✅ <pro — concrete, observable, ≥40 chars>
  ❌ <con — honest, ≥40 chars>
B) <option label>
  ✅ <pro>
  ❌ <con>
Net: <one-line synthesis of what you're actually trading off>
```

D-numbering: first question in a skill invocation is `D1`; increment yourself. This is a model-level instruction, not a runtime counter.

ELI10 is always present, in plain English, not function names. Recommendation is ALWAYS present. Keep the `(recommended)` label.

Completeness: use `Completeness: N/10` only when options differ in coverage. 10 = complete, 7 = happy path, 3 = shortcut. If options differ in kind, write: `Note: options differ in kind, not coverage — no completeness score.`

Pros / cons: use ✅ and ❌. Minimum 2 pros and 1 con per option when the choice is real; Minimum 40 characters per bullet. Hard-stop escape for one-way/destructive confirmations: `✅ No cons — this is a hard-stop choice`.

Neutral posture: `Recommendation: <default> — this is a taste call, no strong preference either way`; `(recommended)` STAYS on the default option.

Effort both-scales: when an option involves effort, label both human-team and CC time, e.g. `(human: ~2 days / CC: ~15 min)`. Makes AI compression visible at decision time.

Net line closes the tradeoff. Per-skill instructions may add stricter rules.

**Non-ASCII characters — write directly, never \u-escape.** When any
string field (question, option label, option description) contains
Chinese (繁體/簡體), Japanese, Korean, or other non-ASCII text, emit
the literal UTF-8 characters in the JSON string. **Never escape them
as `\uXXXX`.** Claude Code's tool parameter pipe is UTF-8 native
and passes characters through unchanged. Manually escaping requires
recalling each codepoint from training, which is unreliable for long
CJK strings — the model regularly emits the wrong codepoint (e.g.
emits the escape for ㄃ U+3103 while thinking it is 管 U+7BA1, so the
user sees `管理工具` rendered as `㄃3用箱`).
The trigger is long, multi-line questions with hundreds of CJK
characters: that is exactly when reflexive escaping kicks in and
exactly when miscoding is most damaging. Long ≠ escape. Keep
characters literal.

Wrong: `"question": "請選擇\uXXXX\uXXXX\uXXXX\uXXXX"`
Right: `"question": "請選擇管理工具"`

Only JSON-mandatory escapes remain allowed: `\n`, `\t`, `\"`, `\\`.

### Self-check before emitting

Before calling AskUserQuestion, verify:
- [ ] D<N> header present
- [ ] ELI10 paragraph present (stakes line too)
- [ ] Recommendation line present with concrete reason
- [ ] Completeness scored (coverage) OR kind-note present (kind)
- [ ] Every option has ≥2 ✅ and ≥1 ❌, each ≥40 chars (or hard-stop escape)
- [ ] (recommended) label on one option (even for neutral-posture)
- [ ] Dual-scale effort labels on effort-bearing options (human / CC)
- [ ] Net line closes the decision
- [ ] You are calling the tool, not writing prose
- [ ] Non-ASCII characters (CJK / accents) written directly, NOT \u-escaped

## Behavioral Nudges

The following nudges are **subordinate** to skill workflow, STOP points,
AskUserQuestion gates, and plan-mode safety. If a nudge below conflicts with
skill instructions, the skill wins. Treat these as preferences, not rules.

**Todo-list discipline.** When working through a multi-step plan, mark each task
complete individually as you finish it. Do not batch-complete at the end. If a task
turns out to be unnecessary, mark it skipped with a one-line reason.

**Think before heavy actions.** For complex operations (refactors, migrations,
non-trivial new features), briefly state your approach before executing. This lets
the user course-correct cheaply instead of mid-flight.

**Dedicated tools over Bash.** Prefer Read, Edit, Write, Glob, Grep over shell
equivalents (cat, sed, find, grep). The dedicated tools are cheaper and clearer.

**Cross-Model Think-Mode (optional, Multi-AI — der Nutzer 2026-06-04).** In der
Hypothesize-Phase bei hartnaeckigen Bugs einen unabhaengigen Gegen-Check mit
ANDERER Modell-DNA holen — faengt Ursachen-Klassen die Claude strukturell
uebersieht. Reihenfolge: Claude bildet ZUERST seine eigene Root-Cause-Hypothese,
DANN (ohne sie zu teilen → kein Anchoring) ein externes Modell unabhaengig:

```bash
<Bug-Kontext: Symptome + relevanter Code/Logs> | \
  python ~/.claude/scripts/cross_model_skeptic.py --mode think --provider gemini
```

Konvergenz (beide gleiche Ursache) = High-Confidence, direkt zum Fix. Divergenz =
den diskriminierenden Test bauen den eines der Modelle nennt, Evidenz entscheidet
(Iron Law bleibt: kein Fix ohne bestaetigte Root-Cause). `--provider codex` fuer
code-spezialisierte Hypothese (gpt-5.4-mini-Default, sparsam). Best-effort: bei
Auth/Quota-Fail ohne Cross-Model weiter, Notiz im Verlauf.

## Voice

Builder voice: product and engineering judgment, compressed for runtime.

- Lead with the point. Say what it does, why it matters, and what changes for the builder.
- Be concrete. Name files, functions, line numbers, commands, outputs, evals, and real numbers.
- Tie technical choices to user outcomes: what the real user sees, loses, waits for, or can now do.
- Be direct about quality. Bugs matter. Edge cases matter. Fix the whole thing, not the demo path.
- Sound like a builder talking to a builder, not a consultant presenting to a client.
- Never corporate, academic, PR, or hype. Avoid filler, throat-clearing, generic optimism, and founder cosplay.
- No em dashes. No AI vocabulary: delve, crucial, robust, comprehensive, nuanced, multifaceted, furthermore, moreover, additionally, pivotal, landscape, tapestry, underscore, foster, showcase, intricate, vibrant, fundamental, significant.
- The user has context you do not: domain knowledge, timing, relationships, taste. Cross-model agreement is a recommendation, not a decision. The user decides.

Good: "auth.ts:47 returns undefined when the session cookie expires. Users hit a white screen. Fix: add a null check and redirect to /login. Two lines."
Bad: "I've identified a potential issue in the authentication flow that may cause problems under certain conditions."

## Writing Style (skip entirely if the user's current message explicitly requests terse / no-explanations output)

Applies to AskUserQuestion, user replies, and findings. AskUserQuestion Format is structure; this is prose quality.

- Gloss curated jargon on first use per skill invocation, even if the user pasted the term.
- Frame questions in outcome terms: what pain is avoided, what capability unlocks, what user experience changes.
- Use short sentences, concrete nouns, active voice.
- Close decisions with user impact: what the user sees, waits for, loses, or gains.
- User-turn override wins: if the current message asks for terse / no explanations / just the answer, skip this section.
- Terse mode (user requested): no glosses, no outcome-framing layer, shorter responses.

Jargon list, gloss on first use if the term appears:
- idempotent
- idempotency
- race condition
- deadlock
- cyclomatic complexity
- N+1
- N+1 query
- backpressure
- memoization
- eventual consistency
- CAP theorem
- CORS
- CSRF
- XSS
- SQL injection
- prompt injection
- DDoS
- rate limit
- throttle
- circuit breaker
- load balancer
- reverse proxy
- SSR
- CSR
- hydration
- tree-shaking
- bundle splitting
- code splitting
- hot reload
- tombstone
- soft delete
- cascade delete
- foreign key
- composite index
- covering index
- OLTP
- OLAP
- sharding
- replication lag
- quorum
- two-phase commit
- saga
- outbox pattern
- inbox pattern
- optimistic locking
- pessimistic locking
- thundering herd
- cache stampede
- bloom filter
- consistent hashing
- virtual DOM
- reconciliation
- closure
- hoisting
- tail call
- GIL
- zero-copy
- mmap
- cold start
- warm start
- green-blue deploy
- canary deploy
- feature flag
- kill switch
- dead letter queue
- fan-out
- fan-in
- debounce
- throttle (UI)
- hydration mismatch
- memory leak
- GC pause
- heap fragmentation
- stack overflow
- null pointer
- dangling pointer
- buffer overflow


## Completeness Principle — Boil the Lake

AI makes completeness cheap. Recommend complete lakes (tests, edge cases, error paths); flag oceans (rewrites, multi-quarter migrations).

When options differ in coverage, include `Completeness: X/10` (10 = all edge cases, 7 = happy path, 3 = shortcut). When options differ in kind, write: `Note: options differ in kind, not coverage — no completeness score.` Do not fabricate scores.

## Confusion Protocol

For high-stakes ambiguity (architecture, data model, destructive scope, missing context), STOP. Name it in one sentence, present 2-3 options with tradeoffs, and ask. Do not use for routine coding or obvious changes.

## Context Health (soft directive)

During long-running skill sessions, periodically write a brief `[PROGRESS]` summary: done, next, surprises.

If you are looping on the same diagnostic, same file, or failed fix variants, STOP and reassess. Consider escalating or saving progress notes to a file. Progress summaries must NEVER mutate git state.

## Completion Status Protocol

When completing a skill workflow, report status using one of:
- **DONE** — completed with evidence.
- **DONE_WITH_CONCERNS** — completed, but list concerns.
- **BLOCKED** — cannot proceed; state blocker and what was tried.
- **NEEDS_CONTEXT** — missing info; state exactly what is needed.

Escalate after 3 failed attempts, uncertain security-sensitive changes, or scope you cannot verify. Format: `STATUS`, `REASON`, `ATTEMPTED`, `RECOMMENDATION`.

# Systematic Debugging

## Iron Law

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

Fixing symptoms creates whack-a-mole debugging. Every fix that doesn't address root cause makes the next bug harder to find. Find the root cause, then fix it.

---

## Phase 1: Root Cause Investigation

Gather context before forming any hypothesis.

1. **Collect symptoms:** Read the error messages, stack traces, and reproduction steps. If the user hasn't provided enough context, ask ONE question at a time via AskUserQuestion.

2. **Read the code:** Trace the code path from the symptom back to potential causes. Use Grep to find all references, Read to understand the logic.

3. **Check recent changes:**
   ```bash
   git log --oneline -20 -- <affected-files>
   ```
   Was this working before? What changed? A regression means the root cause is in the diff.

4. **Reproduce:** Can you trigger the bug deterministically? If not, gather more evidence before proceeding. Reproduce first, THEN theorize — a hypothesis without a reproduction is a guess.

5. **Instrument component boundaries** *(geerntet aus superpowers:systematic-debugging v6.1.1, 2026-07-21)*: when the system spans multiple components (bot → API → DB, n8n → webhook → service, script → env → external CLI), do NOT guess which layer fails. For each boundary, log what data enters and what exits (including env/config propagation), run the reproduction ONCE, and read the evidence to see WHERE it breaks. Then investigate only that component.

6. **Trace backward to the source** *(geerntet aus superpowers:systematic-debugging v6.1.1, 2026-07-21)*: when the error appears deep in the call stack, the crash site is almost never the fix site. Ask repeatedly "what called this, with what value?" until you find where the bad value originated (e.g. empty string as `cwd` silently resolving to `process.cwd()`). If manual tracing stalls, log args, cwd and the stack (`new Error().stack` in JS, `traceback.format_stack()` in Python) BEFORE the dangerous operation — in tests print to stderr, loggers are often suppressed. Fix at the source, not where it crashed.

7. **Bisect when the trigger is unknown** *(geerntet aus superpowers:systematic-debugging v6.1.1, 2026-07-21)*: regression with unknown commit → `git bisect run <repro-cmd>` (git läuft pro Syncthing-Seite — bisect lokal auf der Seite die den Bug zeigt). Unknown test polluting shared state → run test files one by one and check for the pollution artifact after each (`[ -e <artifact> ]`); the first run after which the artifact appears is the polluter.
   Zukunft: bei wachsenden pytest-Suiten das Polluter-Loop-Pattern als eigenes Script ablegen (Quelle hatte `find-polluter.sh`); `pytest --lf` und Test-Order-Randomisierung als schnelle Voreingrenzung.

8. **Check investigation history:** Look for prior investigations on the same files — earlier debug reports in the project, `TODOS.md`, `git log` for prior fixes. Recurring bugs in the same area are an architectural smell. If prior investigations exist, note patterns and check if the root cause was structural.

Output: **"Root cause hypothesis: ..."** — a specific, testable claim about what is wrong and why.

---

## Phase 2: Pattern Analysis

Check if this bug matches a known pattern:

| Pattern | Signature | Where to look |
|---------|-----------|---------------|
| Race condition | Intermittent, timing-dependent | Concurrent access to shared state |
| Nil/null propagation | NoMethodError, TypeError | Missing guards on optional values |
| State corruption | Inconsistent data, partial updates | Transactions, callbacks, hooks |
| Integration failure | Timeout, unexpected response | External API calls, service boundaries |
| Configuration drift | Works locally, fails in staging/prod | Env vars, feature flags, DB state |
| Stale cache | Shows old data, fixes on cache clear | Redis, CDN, browser cache, Turbo |

Also check:
- `TODOS.md` for related known issues
- `git log` for prior fixes in the same area — **recurring bugs in the same files are an architectural smell**, not a coincidence

**Working-example diff** *(geerntet aus superpowers:systematic-debugging v6.1.1, 2026-07-21)*: find similar code in the same codebase that works. List EVERY difference between working and broken — however small; do not assume "that can't matter". If you are implementing a known pattern from a reference, read the reference completely before adapting it — partial understanding guarantees bugs.

**External pattern search:** If the bug doesn't match a known pattern above, WebSearch for:
- "{framework} {generic error type}" — **sanitize first:** strip hostnames, IPs, file paths, SQL, customer data. Search the error category, not the raw message.
- "{library} {component} known issues"

If WebSearch is unavailable, skip this search and proceed with hypothesis testing. If a documented solution or known dependency bug surfaces, present it as a candidate hypothesis in Phase 3.

---

## Phase 3: Hypothesis Testing

Before writing ANY fix, verify your hypothesis.

1. **Confirm the hypothesis:** Add a temporary log statement, assertion, or debug output at the suspected root cause. Run the reproduction. Does the evidence match?

2. **If the hypothesis is wrong:** Before forming the next hypothesis, consider searching for the error. **Sanitize first** — strip hostnames, IPs, file paths, SQL fragments, customer identifiers, and any internal/proprietary data from the error message. Search only the generic error type and framework context: "{component} {sanitized error type} {framework version}". If the error message is too specific to sanitize safely, skip the search. If WebSearch is unavailable, skip and proceed. Then return to Phase 1. Gather more evidence. Do not guess.

3. **3-strike rule:** If 3 hypotheses fail, **STOP**. Use AskUserQuestion:
   ```
   3 hypotheses tested, none match. This may be an architectural issue
   rather than a simple bug.

   A) Continue investigating — I have a new hypothesis: [describe]
   B) Escalate for human review — this needs someone who knows the system
   C) Add logging and wait — instrument the area and catch it next time
   ```

**Red flags** — if you catch yourself thinking any of these, STOP and return to Phase 1 *(Liste erweitert, geerntet aus superpowers:systematic-debugging v6.1.1, 2026-07-21)*:
- "Quick fix for now" — there is no "for now." Fix it right or escalate.
- Proposing a fix before tracing data flow — you're guessing.
- Each fix reveals a new problem elsewhere — wrong layer, not wrong code.
- "Just try changing X and see if it works" — that is guess-and-check, not debugging.
- "It's probably X, let me fix that" — probably ≠ verified. Confirm with evidence first.
- Bundling multiple changes and running the tests — you can't isolate what worked.
- "Skip the test, I'll verify manually" — untested fixes don't stick.
- "I don't fully understand it, but this might work" — say "I don't understand X" out loud and investigate instead of pretending.
- Listing "the main problems" with fixes attached, before any investigation happened.

**Rationalisierungs-Tabelle** — Ausreden, die sich im Moment richtig anfühlen *(geerntet aus superpowers:systematic-debugging v6.1.1, 2026-07-21)*:

| Excuse | Reality |
|--------|---------|
| "Issue is simple, no process needed" | Simple bugs have root causes too; the process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "I can see the problem, let me fix it" | Seeing the symptom ≠ understanding the root cause. |
| "Just try this first, investigate later" | The first fix sets the pattern. Do it right from the start. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "I'll write the test after confirming the fix" | The failing test IS the confirmation. Test first proves it. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architecture question, not another fix. |

**der Nutzer-Signale, dass du gerade rätst:** "Is that not happening?", "Stop guessing", "Wir drehen uns im Kreis" — jedes davon heißt: STOP, zurück zu Phase 1, Evidenz statt nächster Fix-Variante.

---

## Phase 4: Implementation

Once root cause is confirmed:

1. **Fix the root cause, not the symptom.** The smallest change that eliminates the actual problem.

2. **Minimal diff:** Fewest files touched, fewest lines changed. Resist the urge to refactor adjacent code.

3. **Write a regression test** that:
   - **Fails** without the fix (proves the test is meaningful)
   - **Passes** with the fix (proves the fix works)

4. **Run the full test suite.** Paste the output. No regressions allowed.

5. **If the fix touches >5 files:** Use AskUserQuestion to flag the blast radius:
   ```
   This fix touches N files. That's a large blast radius for a bug fix.
   A) Proceed — the root cause genuinely spans these files
   B) Split — fix the critical path now, defer the rest
   C) Rethink — maybe there's a more targeted approach
   ```

6. **Flaky/timing bugs: condition-based waiting, never sleep** *(geerntet aus superpowers:systematic-debugging v6.1.1, 2026-07-21)*: an arbitrary `sleep`/`setTimeout` as "fix" is a symptom fix — it guesses at timing and fails under load. Wait for the actual condition instead: poll every ~10ms, enforce a timeout that throws a descriptive error, and read fresh state inside the loop (never cache it before the loop). Python:
   ```python
   def wait_for(cond, desc, timeout=5.0, poll=0.01):
       t0 = time.monotonic()
       while not (r := cond()):
           if time.monotonic() - t0 > timeout:
               raise TimeoutError(f"waiting for {desc} after {timeout}s")
           time.sleep(poll)
       return r
   ```
   An arbitrary delay is only legitimate when testing real timed behavior (debounce, tick intervals): first wait for the triggering condition, then delay a documented multiple of the KNOWN interval, with a comment explaining why.
   Zukunft: für event-getriebene Systeme (Bot-Loops, n8n-Executions) domänenspezifische Helfer `wait_for_event` / `wait_for_event_count` / `wait_for_event_match` (Predicate statt nur Typ-Check) als Test-Utility ablegen, sobald dort Test-Infra entsteht — Quelle hatte dafür `condition-based-waiting-example.ts`.

7. **Defense-in-depth for invalid-data bugs** *(geerntet aus superpowers:systematic-debugging v6.1.1, 2026-07-21)*: after fixing at the source, make the bug structurally impossible with cheap guards at every layer the bad value passed through — (1) entry-point validation (reject empty/nonexistent input), (2) business-logic check, (3) environment guard (e.g. refuse destructive ops like `git init`/`rm` outside temp dirs while under test), (4) debug logging before the dangerous operation. Different layers catch different bypasses (other code paths, mocks, platform edge cases). One-line guards do not violate the minimal-diff rule — they prevent the next bypass via a different code path.

---

## Phase 5: Verification & Report

**Fresh verification:** Reproduce the original bug scenario and confirm it's fixed. This is not optional.

Run the test suite and paste the output.

Output a structured debug report:
```
DEBUG REPORT
════════════════════════════════════════
Symptom:         [what the user observed]
Root cause:      [what was actually wrong]
Fix:             [what was changed, with file:line references]
Evidence:        [test output, reproduction attempt showing fix works]
Regression test: [file:line of the new test]
Related:         [TODOS.md items, prior bugs in same area, architectural notes]
Status:          DONE | DONE_WITH_CONCERNS | BLOCKED
════════════════════════════════════════
```

Persistenz: den DEBUG REPORT zusätzlich als Datei ins Projekt schreiben (z.B. `DEBUG_REPORT_<datum>.md`), damit künftige Investigations im selben Bereich ihn finden.

**When investigation finds no root cause** *(geerntet aus superpowers:systematic-debugging v6.1.1, 2026-07-21)*: if the issue is genuinely environmental, timing-dependent, or external (third-party outage), the process is still complete — document in the DEBUG REPORT what was investigated and ruled out, implement appropriate handling (retry, timeout, clear error message), and add monitoring/logging so the next occurrence carries evidence. But be honest: ~95% of "no root cause" cases are incomplete investigation — if you stopped early, say so in the report instead of declaring the bug environmental.

---

## Important Rules

- **3+ failed fix attempts → STOP and question the architecture.** Wrong architecture, not failed hypothesis.
- **Never apply a fix you cannot verify.** If you can't reproduce and confirm, don't ship it.
- **Never say "this should fix it."** Verify and prove it. Run the tests.
- **If fix touches >5 files → AskUserQuestion** about blast radius before proceeding.
- **Completion status:**
  - DONE — root cause found, fix applied, regression test written, all tests pass
  - DONE_WITH_CONCERNS — fixed but cannot fully verify (e.g., intermittent bug, requires staging)
  - BLOCKED — root cause unclear after investigation, escalated

---

## Changelog

- **1.2.0** (2026-07-21): Ernte aus superpowers:systematic-debugging v6.1.1 (Plugin wird deaktiviert) — Boundary-Instrumentation, Backward-Tracing zur Quelle, Bisection-Taktiken (Phase 1); Working-Example-Diff (Phase 2); erweiterte Red Flags + Rationalisierungs-Tabelle + der Nutzer-Signale (Phase 3); Condition-Based-Waiting statt sleep + Defense-in-Depth-Guards (Phase 4); "No Root Cause"-Exit (Phase 5).
- **1.1.1**: vorheriger Stand (gstack-Port, standalone, Fix-Sweep 2026-07-21).
