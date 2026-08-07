# Context Management

## Purpose

AI development quality degrades when a working context becomes overloaded, repetitive, contradictory, or detached from repository truth. The orchestration hub manages context automatically; the founder does not manage token budgets or decide when to clear a session.

This pipeline treats context engineering as an operating discipline, not merely as writing larger prompts.

- **Prompt engineering** defines how the current instruction, constraints, examples, and requested output are worded.
- **Context engineering** decides what verified information, tools, memory, history, and schemas the working agent should—and should not—receive for its current step.

Both are required. A well-written prompt cannot compensate for missing, stale, irrelevant, or contradictory context.

## Core rule

```text
The repository stores durable truth.
A focused context performs one bounded stage or implementation slice.
Each model call receives the smallest sufficient high-signal context.
Temporary chat history is never the only source of an approved decision.
```

## Runtime context stack

For every meaningful agent call, the orchestration hub assembles only the relevant parts of this stack:

1. **Instructions** — role, approved objective, constraints, safety boundaries, and permitted actions
2. **Current user input** — the founder's present request or approved task
3. **Retrieved project truth** — only the canonical files, specification sections, code, evidence, and decisions needed now
4. **Tools** — only capabilities relevant to the current stage
5. **Short-term state** — recent progress, changed facts, open blockers, and checks already performed
6. **Long-term project memory** — stable approved facts selected from the repository on demand
7. **Output contract** — the required schema, report shape, evidence, and stopping point

Do not automatically load the complete repository, full chat history, all skills, all research, or every prior report into each call.

## Context-engineering cycle

Use this cycle throughout the pipeline:

### Write

Store durable decisions, specifications, evidence, current state, and unresolved blockers outside the chat context in their canonical repository locations. Temporary scratch notes may support work, but must not silently become project truth.

### Select

Retrieve only the material needed for the current stage and objective. Prefer targeted repository paths, specification sections, relevant code, and a bounded evidence subset over broad context dumps.

### Compress

Convert large histories, logs, research sets, and previous-stage output into loss-aware handoffs. Preserve decisions, provenance, constraints, failures, uncertainty, and acceptance criteria; remove repetition and unrelated detail.

### Isolate

Separate stages or agents when their responsibilities, evidence, or evaluation criteria differ. Researchers, builders, reviewers, auditors, and generation tools should receive stage-specific context so noisy output from one role does not contaminate another.

```text
write durable truth
→ select relevant evidence
→ compress without losing decisions
→ isolate the next responsibility
→ execute one bounded step
→ record the verified result
```

## Per-call context check

Before invoking an agent or generation tool, verify:

- What exact decision or output is required now?
- Which source is authoritative for each required fact?
- What is the smallest evidence set sufficient to do the work?
- Are any included facts unverified, stale, duplicated, or contradictory?
- Which tools are genuinely needed?
- What must be excluded because it belongs to another stage?
- What output contract and stopping boundary apply?
- Where will the verified result be written?

If required context is missing, return a precise blocker or request the missing source. Do not compensate by inventing facts or padding the prompt.

## Common context failures

Watch for:

- **Poisoning** — an invented or incorrect fact enters a handoff and is reused as truth
- **Distraction** — large history or tool output obscures the current task
- **Confusion** — irrelevant context changes the model's direction
- **Clash** — two sources disagree and no authority rule resolves them

When detected, stop progression, identify the authoritative source, correct the durable record when approved, and rebuild the next context from verified material.

## Prompt construction after context selection

Only after context is selected should the orchestration hub write the task prompt. The prompt should state:

```text
Objective
Authoritative inputs
Requirements and acceptance criteria
Relevant tools
Output contract
Permissions and prohibitions
Stopping point
Required return
```

Do not repeat entire canonical documents when precise references or retrieved excerpts are sufficient. Do not remove critical decisions, safety boundaries, provenance, or verification requirements merely to shorten the prompt.

## External generation tools

When the pipeline uses a bounded generation tool such as a design, media, code, or music generator:

1. Build the generation packet upstream from verified project context.
2. Compress it to only the controls that the tool can use.
3. Keep source description, desired transformation, must-preserve traits, and prohibited traits distinct when the tool supports them.
4. Treat the final text entered into the tool as prompt engineering produced by the upstream context-engineering process.
5. Store approved inputs and outputs in the project-specific repository when they become durable evidence.

Do not dump full project history, complete research corpora, or unrelated agent reasoning into a generation field.

## Same-context work

Continue in the same focused context when:

- The task is small and clearly specified
- Relevant repository state is already understood
- No major product or architecture decision is unresolved
- The work can reasonably finish as one implementation slice
- The agent continues to remember constraints and acceptance criteria accurately

Small work may follow:

```text
clarify briefly → implement → verify → report
```

## Durable specification and fresh context

Create or update the active OpenSpec change and start a fresh focused context when:

- Investigation consumed substantial context
- The work requires more than one implementation slice
- A different agent, tool, repository, branch, or pipeline stage will continue the work
- The agent repeats questions already answered
- Requirements are forgotten or contradicted
- Scope starts expanding without approval
- The agent struggles to locate prior decisions
- Raw logs, temporary summaries, or unrelated files dominate the session

Do not rely on a universal token-number threshold. Use behavioural evidence and task complexity.

## Specification and ticket roles

```text
spec.md = the approved destination, behaviours, boundaries, and acceptance criteria
tasks.md = the ordered implementation slices used to reach the destination
```

Create tickets only when the approved work needs multiple focused implementation contexts. Do not create a competing local issue tracker when OpenSpec already serves the purpose.

## One-ticket execution rule

For multi-session work:

```text
one approved ticket
→ one focused implementation context
→ tests and internal review
→ implementation evidence
→ update task status
→ clear context before the next ticket when needed
```

Every ticket remains subordinate to the complete approved specification. Completing a ticket does not prove the complete change is finished.

## Handoffs

A handoff is required when changing:

- Agent
- Session
- Repository
- Branch
- Pipeline stage
- Implementation ticket

A compact handoff should reference repository documents rather than copy the entire conversation.

```text
Objective
Approved specification and ticket
Current branch and commit
Authoritative inputs and provenance
Files or areas in scope
Checks already run
Known failures or uncertainty
Required return and stopping point
```

## Claude session action, route, and task brief

A handoff to Claude has three distinct parts. Decide each separately; never merge them into one block.

1. **Claude session action** — whether to continue the existing session unchanged, or issue a slash command first:
   - Same bounded task, context still healthy → continue with no slash command.
   - Same task, context overloaded or drifting → `/compact`.
   - Genuinely fresh, unrelated, or independently scoped task → `/clear`.
   - Command availability or syntax uncertain → `/help`.
2. **Canonical pipeline route/template** — the canonical prompt selected for the current stage (for example `prompts/implement-change.md`, `prompts/verify-change.md`, `prompts/audit-change.md`, `prompts/investigate-change.md`), matched against the stage or route already determined during recovery (`docs/PIPELINE.md` → "Automatic request routing").
3. **Compiled task brief** — the worker brief itself (see "Handoffs" above and `prompts/start-project-session.md` → "Compiled worker brief"), carried by the canonical route into the session.

Do not invent a new command name, alias, or shortcut for an existing session action or stage.

Display the Claude session action, if any, separately, before the task prompt. Never embed a slash command inside the compiled task prompt.

## Fresh-context review

The implementer should use a fresh reviewer context or subagent to check:

- Complete specification adherence
- Code quality and unnecessary complexity
- Test completeness
- Unrelated changes
- Missed acceptance criteria

This internal review is builder-side quality control. It cannot issue the independent release verdict. Codex remains the independent auditor when required by risk.

## Temporary material

Temporary summaries, exploratory notes, raw logs, and prototype output must not silently become canonical truth.

- Approved durable outcomes go into canonical project documents or the active OpenSpec change.
- Raw logs should be summarized and linked or stored outside the main context when retention is necessary.
- Disposable prototypes answer one named question and are not automatically production code.

## Founder experience

The founder must never be told to:

- Calculate context usage
- Choose what to retrieve or exclude
- Choose when to clear the context
- Decide whether to create tickets
- Invoke a handoff skill
- Reconstruct a specification from old chat messages
- Convert project truth into a tool-specific prompt manually

The orchestration hub makes these decisions and explains only the product-relevant result and next approval gate.
