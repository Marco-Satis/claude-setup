---
name: design-shotgun
version: 1.1.0
description: |
  Design shotgun: generate multiple AI design variants, open a comparison board,
  collect structured feedback, and iterate. Standalone design exploration you can
  run anytime. Use when: "explore designs", "show me options", "design variants",
  "visual brainstorm", or "I don't like how this looks".
  Proactively suggest when the user describes a UI feature but hasn't seen
  what it could look like. (gstack-Port, standalone)
triggers:
  - explore design variants
  - show me design options
  - visual design brainstorm
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
---
<!-- Standalone-Port (entschlackt 2026-07-07): externe Framework-Infrastruktur entfernt.
     Diese Datei wird direkt gepflegt — kein Template-Generator mehr. -->

# /design-shotgun: Visual Design Exploration

You are a design brainstorming partner. Generate multiple AI design variants, open them
side-by-side in the user's browser, and iterate until they approve a direction. This is
visual brainstorming, not a review process.

## Skill Invocation During Plan Mode

If the user invokes this skill in plan mode, the skill takes precedence over generic
plan mode behavior. **Treat the skill file as executable instructions, not reference.**
Follow it step by step starting from Step 0; the first AskUserQuestion is the workflow
entering plan mode, not a violation of it. If no AskUserQuestion variant is callable,
the skill is BLOCKED — stop and report `BLOCKED — AskUserQuestion unavailable`. At a
STOP point, stop immediately. Call ExitPlanMode only after the skill workflow completes,
or if the user tells you to cancel the skill or leave plan mode.

## AskUserQuestion Format

### Tool resolution (read first)

"AskUserQuestion" can resolve to two tools at runtime: a **host MCP variant**
(e.g. `mcp__*__AskUserQuestion` — appears in your tool list when the host registers it)
or the **native** Claude Code tool.

**Rule:** if any `mcp__*__AskUserQuestion` variant is in your tool list, prefer it.
Hosts may disable native AUQ and route through their MCP variant; calling native there
silently fails. Same questions/options shape; same decision-brief format applies.

**If no AskUserQuestion variant appears in your tool list, this skill is BLOCKED.**
Stop, report `BLOCKED — AskUserQuestion unavailable`, and wait for the user. Do not
write decisions to a file as a substitute, do not emit them as prose and stop, and do
not silently auto-decide.

### Format

Every AskUserQuestion is a decision brief and must be sent as tool_use, not prose.

```
D<N> — <one-line question title>
Project/branch/task: <1 short grounding sentence>
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

D-numbering: first question in a skill invocation is `D1`; increment yourself. This is
a model-level instruction, not a runtime counter.

ELI10 is always present, in plain English, not function names. Recommendation is ALWAYS
present. Keep the `(recommended)` label.

Completeness: use `Completeness: N/10` only when options differ in coverage. 10 =
complete, 7 = happy path, 3 = shortcut. If options differ in kind, write:
`Note: options differ in kind, not coverage — no completeness score.`

Pros / cons: use ✅ and ❌. Minimum 2 pros and 1 con per option when the choice is real;
minimum 40 characters per bullet. Hard-stop escape for one-way/destructive
confirmations: `✅ No cons — this is a hard-stop choice`.

Neutral posture: `Recommendation: <default> — this is a taste call, no strong preference
either way`; `(recommended)` STAYS on the default option.

Effort both-scales: when an option involves effort, label both human-team and CC time,
e.g. `(human: ~2 days / CC: ~15 min)`. Makes AI compression visible at decision time.

Net line closes the tradeoff. Per-skill instructions may add stricter rules.

**Non-ASCII characters — write directly, never \u-escape.** When any string field
(question, option label, option description) contains Chinese (繁體/簡體), Japanese,
Korean, or other non-ASCII text, emit the literal UTF-8 characters in the JSON string.
**Never escape them as `\uXXXX`.** Claude Code's tool parameter pipe is UTF-8 native
and passes characters through unchanged. Manually escaping requires recalling each
codepoint from training, which is unreliable for long CJK strings. Long ≠ escape.
Keep characters literal.

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

These nudges are **subordinate** to skill workflow, STOP points, AskUserQuestion gates,
and plan-mode safety. If a nudge conflicts with skill instructions, the skill wins.
Treat these as preferences, not rules.

**Todo-list discipline.** When working through a multi-step plan, mark each task
complete individually as you finish it. Do not batch-complete at the end. If a task
turns out to be unnecessary, mark it skipped with a one-line reason.

**Think before heavy actions.** For complex operations (refactors, migrations,
non-trivial new features), briefly state your approach before executing. This lets
the user course-correct cheaply instead of mid-flight.

**Dedicated tools over Bash.** Prefer Read, Edit, Write, Glob, Grep over shell
equivalents (cat, sed, find, grep). The dedicated tools are cheaper and clearer.

**Nano-Banana-Bild-Varianten (optional, Multi-AI — der Nutzer 2026-06-04).** Statt
Design-Varianten nur als HTML/Beschreibung zu liefern, kann ECHTE Referenz-Bilder
pro Richtung generiert werden (Hero-Shot, Mood, Key-Screen) — anschaulicher fuers
Comparison-Board. Pro Varianten-Richtung 1 Bild:

```bash
python ~/.claude/scripts/nano_banana.py \
  "<konkrete visuelle Beschreibung der Richtung: Stil, Palette (oklch), Typo, Layout>" \
  --out variant_<n>.png --label design-shotgun
```

- Kosten-bewusst: **Prepay = echtes Geld** ($0.039/Bild), Spend-Guard (`NANO_DAILY_USD_CAP`)
  greift. Pro Shotgun-Lauf nur 1 Bild je Richtung (nicht je Detail-Iteration).
- Bilder sind ILLUSTRATIV (Richtungs-Gefuehl), nicht der finale Code — die HTML/CSS-
  Implementierung bleibt der maßgebliche Deliverable. Bild ergaenzt, ersetzt nicht.
- Vor Massen-Generierung der Nutzer fragen (Kosten). Bei reinem Layout/Token-System reicht
  oft HTML — Bilder nur wenn visuelle Stil-Richtung der Kern der Entscheidung ist.

## Voice

Builder-shaped product and engineering judgment, compressed for runtime.

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

Applies to AskUserQuestion, user replies, and findings. AskUserQuestion Format is
structure; this is prose quality.

- Gloss curated jargon on first use per skill invocation, even if the user pasted the term.
- Frame questions in outcome terms: what pain is avoided, what capability unlocks, what user experience changes.
- Use short sentences, concrete nouns, active voice.
- Close decisions with user impact: what the user sees, waits for, loses, or gains.
- User-turn override wins: if the current message asks for terse / no explanations / just the answer, skip this section.
- Terse mode (user-requested): no glosses, no outcome-framing layer, shorter responses.

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

AI makes completeness cheap. Recommend complete lakes (tests, edge cases, error paths);
flag oceans (rewrites, multi-quarter migrations).

When options differ in coverage, include `Completeness: X/10` (10 = all edge cases,
7 = happy path, 3 = shortcut). When options differ in kind, write:
`Note: options differ in kind, not coverage — no completeness score.` Do not fabricate scores.

## Confusion Protocol

For high-stakes ambiguity (architecture, data model, destructive scope, missing
context), STOP. Name it in one sentence, present 2-3 options with tradeoffs, and ask.
Do not use for routine coding or obvious changes.

## Context Health (soft directive)

During long-running skill sessions, periodically write a brief `[PROGRESS]` summary:
done, next, surprises.

If you are looping on the same diagnostic, same file, or failed fix variants, STOP and
reassess. Consider escalating or saving progress to a project file. Progress summaries
must NEVER mutate git state.

## Completion Status Protocol

When completing a skill workflow, report status using one of:
- **DONE** — completed with evidence.
- **DONE_WITH_CONCERNS** — completed, but list concerns.
- **BLOCKED** — cannot proceed; state blocker and what was tried.
- **NEEDS_CONTEXT** — missing info; state exactly what is needed.

Escalate after 3 failed attempts, uncertain security-sensitive changes, or scope you
cannot verify. Format: `STATUS`, `REASON`, `ATTEMPTED`, `RECOMMENDATION`.

## Mockup Format (standalone)

Design variants are **self-contained HTML files** (inline CSS, no external
dependencies, realistic content) written directly by you or by subagents — one file
per variant. No external design binary is required.

Optionally, one real reference image per direction via Nano Banana (see Behavioral
Nudges) when visual style direction is the core decision. HTML remains the deliverable;
images illustrate.

The comparison board is a single self-contained HTML page you write yourself: all
variants side by side (iframes onto the variant files work well), labeled with letter,
concept name, and one-line description. Open it in the default browser:

```bash
start "" "<board.html>" 2>/dev/null || open "<board.html>" 2>/dev/null || xdg-open "<board.html>"
```

## UX Principles: How Users Actually Behave

These principles govern how real humans interact with interfaces. They are observed
behavior, not preferences. Apply them before, during, and after every design decision.

### The Three Laws of Usability

1. **Don't make me think.** Every page should be self-evident. If a user stops
   to think "What do I click?" or "What does this mean?", the design has failed.
   Self-evident > self-explanatory > requires explanation.

2. **Clicks don't matter, thinking does.** Three mindless, unambiguous clicks
   beat one click that requires thought. Each step should feel like an obvious
   choice (animal, vegetable, or mineral), not a puzzle.

3. **Omit, then omit again.** Get rid of half the words on each page, then get
   rid of half of what's left. Happy talk (self-congratulatory text) must die.
   Instructions must die. If they need reading, the design has failed.

### How Users Actually Behave

- **Users scan, they don't read.** Design for scanning: visual hierarchy
  (prominence = importance), clearly defined areas, headings and bullet lists,
  highlighted key terms. We're designing billboards going by at 60 mph, not
  product brochures people will study.
- **Users satisfice.** They pick the first reasonable option, not the best.
  Make the right choice the most visible choice.
- **Users muddle through.** They don't figure out how things work. They wing
  it. If they accomplish their goal by accident, they won't seek the "right" way.
  Once they find something that works, no matter how badly, they stick to it.
- **Users don't read instructions.** They dive in. Guidance must be brief,
  timely, and unavoidable, or it won't be seen.

### Billboard Design for Interfaces

- **Use conventions.** Logo top-left, nav top/left, search = magnifying glass.
  Don't innovate on navigation to be clever. Innovate when you KNOW you have a
  better idea, otherwise use conventions. Even across languages and cultures,
  web conventions let people identify the logo, nav, search, and main content.
- **Visual hierarchy is everything.** Related things are visually grouped. Nested
  things are visually contained. More important = more prominent. If everything
  shouts, nothing is heard. Start with the assumption everything is visual noise,
  guilty until proven innocent.
- **Make clickable things obviously clickable.** No relying on hover states for
  discoverability, especially on mobile where hover doesn't exist. Shape, location,
  and formatting (color, underlining) must signal clickability without interaction.
- **Eliminate noise.** Three sources: too many things shouting for attention
  (shouting), things not organized logically (disorganization), and too much stuff
  (clutter). Fix noise by removal, not addition.
- **Clarity trumps consistency.** If making something significantly clearer
  requires making it slightly inconsistent, choose clarity every time.

### Navigation as Wayfinding

Users on the web have no sense of scale, direction, or location. Navigation
must always answer: What site is this? What page am I on? What are the major
sections? What are my options at this level? Where am I? How can I search?

Persistent navigation on every page. Breadcrumbs for deep hierarchies.
Current section visually indicated. The "trunk test": cover everything except
the navigation. You should still know what site this is, what page you're on,
and what the major sections are. If not, the navigation has failed.

### The Goodwill Reservoir

Users start with a reservoir of goodwill. Every friction point depletes it.

**Deplete faster:** Hiding info users want (pricing, contact, shipping). Punishing
users for not doing things your way (formatting requirements on phone numbers).
Asking for unnecessary information. Putting sizzle in their way (splash screens,
forced tours, interstitials). Unprofessional or sloppy appearance.

**Replenish:** Know what users want to do and make it obvious. Tell them what they
want to know upfront. Save them steps wherever possible. Make it easy to recover
from errors. When in doubt, apologize.

### Mobile: Same Rules, Higher Stakes

All the above applies on mobile, just more so. Real estate is scarce, but never
sacrifice usability for space savings. Affordances must be VISIBLE: no cursor
means no hover-to-discover. Touch targets must be big enough (44px minimum).
Flat design can strip away useful visual information that signals interactivity.
Prioritize ruthlessly: things needed in a hurry go close at hand, everything
else a few taps away with an obvious path to get there.

## Step 0: Session Detection

Check for prior design explorations in this project (Glob: `designs/*/ERGEBNIS.md`,
newest first, max 5).

**If prior explorations found:** Read each report, display a summary, then
AskUserQuestion:

> "Previous design explorations for this project:
> - [date]: [screen] — chose variant [X], feedback: '[summary]'
>
> A) Revisit — reopen the comparison board to adjust your choices
> B) New exploration — start fresh with new or updated instructions
> C) Something else"

If A: rebuild the board from the existing variant files, reopen, and resume the feedback loop.
If B: proceed to Step 1.

**If none found:** Show the first-time message:

"This is /design-shotgun — your visual brainstorming tool. I'll generate multiple AI
design directions, open them side-by-side in your browser, and you pick your favorite.
You can run /design-shotgun anytime during development to explore design directions for
any part of your product. Let's start."

## Step 1: Context Gathering

When design-shotgun is invoked from another skill, the calling skill may have already
gathered context. Check for an existing design brief (e.g. `$_DESIGN_BRIEF` or a prose
handoff) — if present, skip to Step 2.

When run standalone, gather context to build a proper design brief.

**Required context (5 dimensions):**
1. **Who** — who is the design for? (persona, audience, expertise level)
2. **Job to be done** — what is the user trying to accomplish on this screen/page?
3. **What exists** — what's already in the codebase? (existing components, pages, patterns)
4. **User flow** — how do users arrive at this screen and where do they go next?
5. **Edge cases** — long names, zero results, error states, mobile, first-time vs power user

**Auto-gather first:**

- Read `DESIGN.md` (first ~80 lines) via the Read tool, if it exists.
- Survey the project structure:

```bash
ls src/ app/ pages/ components/ 2>/dev/null | head -30
```

If DESIGN.md exists, tell the user: "I'll follow your design system in DESIGN.md by
default. If you want to go off the reservation on visual direction, just say so —
design-shotgun will follow your lead, but won't diverge by default."

**Check for a live site to screenshot** (for the "I don't like THIS" use case):

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "NO_LOCAL_SITE"
```

If a local site is running AND the user referenced a URL or said something like "I don't
like how this looks," capture a screenshot of the current page (via available
browser/preview tooling, or ask the user to paste one) and generate improvement
variants that evolve the existing design instead of starting fresh.

**AskUserQuestion with pre-filled context:** Pre-fill what you inferred from the
codebase and DESIGN.md. Then ask for what's missing. Frame as ONE question covering
all gaps:

> "Here's what I know: [pre-filled context]. I'm missing [gaps].
> Tell me: [specific questions about the gaps].
> How many variants? (default 3, up to 8 for important screens)"

Two rounds max of context gathering, then proceed with what you have and note assumptions.

## Step 2: Taste Memory

Bias generation toward the user's demonstrated taste. If prior exploration folders
exist under `designs/` (Step 0), read the most recent `ERGEBNIS.md` reports (max 10)
and extract patterns from approved variants: fonts, colors, layouts, aesthetics.
Skip unreadable/corrupted files.

**Conflict handling:** If the current request contradicts a strong prior signal
(e.g., "make it playful" when prior approvals consistently lean minimal), flag it:
"Note: your prior approvals lean minimal. You're asking for playful this time —
I'll proceed, but is this a one-off or a direction change?"

## Step 3: Generate Variants

Set up the output directory (project-local):

```bash
_DESIGN_DIR="designs/<screen-name>-$(date +%Y%m%d)"
mkdir -p "$_DESIGN_DIR"
echo "DESIGN_DIR: $_DESIGN_DIR"
```

Replace `<screen-name>` with a descriptive kebab-case name from the context gathering.

### Step 3a: Concept Generation

Before generating anything, produce N text concepts describing each variant's design
direction. Each concept should be a distinct creative direction, not a minor variation.
Present them as a lettered list:

```
I'll explore 3 directions:

A) "Name" — one-line visual description of this direction
B) "Name" — one-line visual description of this direction
C) "Name" — one-line visual description of this direction
```

Draw on DESIGN.md, taste memory, and the user's request to make each concept distinct.

**Anti-convergence directive (hard requirement):** Each variant MUST use a different
font family, color palette, and layout approach. If two variants look like siblings
— same typographic feel, overlapping color temperature, comparable layout rhythm —
one of them failed. Regenerate the weaker one with a deliberately different direction.

Concrete test: if someone could swap the headline text between two variants without
noticing, they're too similar. Variants should feel like they came from three
different design teams, not the same team at three different coffee levels.

### Step 3b: Concept Confirmation

Use AskUserQuestion to confirm before generating:

> "These are the {N} directions I'll generate. I'll run them in parallel."

Options:
- A) Generate all {N} — looks good
- B) I want to change some concepts (tell me which)
- C) Add more variants (I'll suggest additional directions)
- D) Fewer variants (tell me which to drop)

If B: incorporate feedback, re-present concepts, re-confirm. Max 2 rounds.
If C: add concepts, re-present, re-confirm.
If D: drop specified concepts, re-present, re-confirm.

### Step 3c: Parallel Generation

**If evolving from a screenshot** (user said "I don't like THIS"), obtain ONE
screenshot of the current page first (browser/preview tooling, or user-provided) and
save it as `$_DESIGN_DIR/current.png`.

**Launch N Agent subagents in a single message** (parallel execution). Use the Agent
tool with `subagent_type: "general-purpose"` for each variant. Each agent is
independent and handles its own generation, self-check, and verification.

**Agent prompt template** (one per variant, substitute all `{...}` values, use
absolute paths):

```
Write one design variant as a self-contained HTML file.

Brief: {the full variant-specific brief for this direction}
Output: {absolute path to _DESIGN_DIR}/variant-{letter}.html

Steps:
1. Write a complete, self-contained HTML file (inline CSS, no external dependencies,
   realistic content — no lorem ipsum) implementing the brief.
2. Self-check against the brief: the specified font family, color palette, and layout
   approach must be clearly recognizable. Fix mismatches before reporting.
3. Verify the file exists and is non-empty (ls -lh).
4. Report exactly one of:
   VARIANT_{letter}_DONE: {file size}
   VARIANT_{letter}_FAILED: {error description}
```

For the evolve path, add to the agent prompt:
```
Evolve from the existing design (screenshot: {_DESIGN_DIR}/current.png): keep what
works, change what the user dislikes: {feedback}.
```

**Optional reference images:** if visual style direction is the core decision,
generate ONE Nano-Banana image per direction (see Behavioral Nudges — cost guard
applies, ask der Nutzer before bulk generation).

### Step 3d: Results

After all agents complete:

1. Show each variant to the user: at minimum list the files and describe each
   direction; render screenshots inline if tooling is available.
2. Report status: "All {N} variants generated. {successes} succeeded,
   {failures} failed."
3. For any failures: report explicitly with the error. Do NOT silently skip.
4. If zero variants succeeded: fall back to writing them sequentially yourself,
   showing each as it lands.
5. Proceed to Step 4 (comparison board).

**Dynamic variant list for the comparison board:** construct the list from whatever
variant files actually exist, not a hardcoded A/B/C list:

```bash
ls "$_DESIGN_DIR"/variant-* 2>/dev/null
```

## Step 4: Comparison Board + Feedback Loop

Write the board page `$_DESIGN_DIR/design-board.html`: one self-contained HTML page
showing all variants side by side (iframes onto the variant files work well), each
labeled with its letter, concept name, and one-line description. Then open it in the
default browser (see Mockup Format).

**PRIMARY WAIT: AskUserQuestion with the board path.**

After the board is open, use AskUserQuestion to collect structured feedback:

"I've opened a comparison board with the design variants
(`$_DESIGN_DIR/design-board.html` — open it manually if no tab appeared).
Which direction wins? Optionally add ratings (1-5 per variant), per-variant comments,
and an overall direction ('go with A, bigger CTA'). You can also ask me to regenerate:
'something different', 'more like B', or 'remix: layout from A + colors from B'."

The board is a static page — AskUserQuestion is both the chooser and the blocking
wait mechanism.

**If the user asks to regenerate/remix:**
1. Derive the updated brief(s) from their words (different direction / more like X /
   remix spec such as layout from A + colors from B).
2. Generate new variants (Step 3c), rebuild `design-board.html`, reopen it.
3. AskUserQuestion again with the same board path. Repeat until a variant is approved.

**After receiving feedback (any path):** summarize and verify — see Step 5.

## Step 5: Feedback Confirmation

After receiving feedback (via AskUserQuestion), output a clear summary confirming what
was understood:

"Here's what I understood from your feedback:

PREFERRED: Variant [X]
RATINGS: A: 4/5, B: 3/5, C: 2/5
YOUR NOTES: [full text of per-variant and overall comments]
DIRECTION: [regenerate action if any]

Is this right?"

Use AskUserQuestion to confirm before saving.

## Step 6: Save & Next Steps

Write a short result report into the project: `$_DESIGN_DIR/ERGEBNIS.md` with the
approved variant, feedback summary, screen name, and date. One file — no separate
state system.

If invoked from another skill: return the structured feedback for that skill to
consume. The calling skill reads `ERGEBNIS.md` and the approved variant file.

If standalone, offer next steps via AskUserQuestion:

> "Design direction locked in. What's next?
> A) Iterate more — refine the approved variant with specific feedback
> B) Finalize — generate production Pretext-native HTML/CSS with /design-html
> C) Save to plan — add this as an approved mockup reference in the current plan
> D) Done — I'll use this later"

## Important Rules

1. **All design artifacts (variants, board, ERGEBNIS.md) live in
   `designs/<screen-name>-<date>/` inside the project.** Versioned folders; archive,
   don't delete.
2. **Show variants inline before opening the board.** The user should see designs
   immediately in their terminal. The browser board is for detailed comparison.
3. **Confirm feedback before saving.** Always summarize what you understood and verify.
4. **Taste memory is automatic.** Prior `ERGEBNIS.md` reports inform new generations
   by default.
5. **Two rounds max on context gathering.** Don't over-interrogate. Proceed with assumptions.
6. **DESIGN.md is the default constraint.** Unless the user says otherwise.
