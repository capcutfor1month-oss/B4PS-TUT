# Start a Project Session from a GitHub URL

Input: one target GitHub repository URL, optionally followed by a product problem or desired result in normal language.

Canonical common pipeline:

`https://github.com/capcutfor1month-oss/project-Pipline`

This prompt has two responsibilities: the orchestrator recovers canonical state, then compiles a bounded brief for whichever downstream worker executes the task. See `docs/PIPELINE.md`'s "Context recovery" section for the underlying rule — the worker does not repeat orchestrator recovery.

## 1. Orchestrator recovery

1. Perform the repository-access preflight before claiming recovery.
2. Inspect the target repository before responding.
3. Cross-check, where applicable to the task at hand:
   - `docs/CURRENT.md` → Current phase
   - Active change
   - Exact next action
   - the active OpenSpec `spec.md`, or the approved lightweight approval record when a full OpenSpec change is not used
   - target repository branch and commit
   - base risk tier
   - applicable UI-sensitive and Data-sensitive profiles
   - any explicit independent-audit requirement
   - required approval gates
   - the validation target, when the task is a repair or a post-lock validation
   - the approved repair-attempt bound and current attempt, when applicable
   - failing evidence, when applicable
   - incident classification and any incident-specific restrictions
   - unresolved blockers
4. Do not rely on `Current phase` alone — it names a stage in one field; it does not carry scope, risk, gates, or validation-target detail by itself.
5. If these sources disagree, are stale, or are incomplete, do not guess and do not silently select a workflow. Report the contradiction and stop.
6. Detect whether the common pipeline and project capability layer are missing, partial, or installed.
7. Classify the founder's request automatically and select the smallest relevant internal workflow, using only the pipeline's existing canonical routes and stages (for example `Implementation`, `Validation after lock`, `Production incident` — see `docs/PIPELINE.md`'s "Automatic request routing" table). Do not invent new named states or aliases for these.
8. Do not ask the founder to repeat the common workflow, select skills, invoke commands, manage context, or construct technical prompts.
9. Ask only product-level questions requiring founder judgment.
10. Do not rely on old chat memory when GitHub contains newer project truth.
11. Do not code, select architecture, perform destructive actions, or make product decisions without the required approval.

## 2. Compiled worker brief

Once recovery is complete, compile the bounded brief handed to the downstream worker (Claude, Codex, an investigator, or any other bounded execution session). This is the only context the worker receives by default.

Required contract — every applicable field is non-droppable:

```text
Identity and target
  Target repository
  Branch
  Target/base commit
  Active change ID or lightweight approval record
  Active implementation ticket, where a ticket exists
  Exact objective
  Exact current stage or request route
  Exact next action

Locked authority
  Approved scope
  Acceptance criteria
  Validation target, where applicable
  Founder decisions
  Unresolved decisions requiring escalation
  Authoritative project files the worker may rely on
  Authoritative-input provenance: where each material instruction or input came from (approved project files, evidence, user-provided input, or other authoritative source) — enough to trace it, without dumping full governance history

Risk and gates
  Base risk tier
  Applicable UI-sensitive / Data-sensitive profiles
  Required tests and evidence
  Whether independent Codex audit is required
  Founder approval gates
  Rollback, migration, data-access, or incident restrictions

Validation-after-lock context, when applicable
  Locked target
  Real-world failing evidence
  Expected result
  Actual result
  Approved repair bound
  Current attempt
  Requirement to return to the same validation
  No new scope
  Stop / escalation conditions

Worker permissions
  Permitted files and actions
  Prohibited files and actions
  Whether modification is allowed
  Whether staging, commit, push, merge, deployment, or rollback is allowed
  Whether the worker is implementing, verifying, auditing, or only reporting

Execution state so far
  Checks already run, their results, and the commit/worktree state they ran against — never implied as passed if they were not actually run
  Known blockers, failed checks, or evidence recovered by the orchestrator, forwarded rather than silently omitted
  Unresolved ambiguity or uncertainty
  Whether any of the above requires stopping or escalation

Required return
  Required evidence
  Required report or output
  Stopping point
  Exact handoff back to orchestrator
```

### Context that should normally be omitted

Do not forward the following into a worker brief unless the task directly requires it:

- Decision-log identifiers (for example DEC numbers)
- Project-Pipeline commit hashes
- Governance-history narration
- The full universal pipeline documents, read verbatim
- Unrelated stages or routes
- Irrelevant tooling policies
- Repository-ownership explanations

**Target-project branch and commit are the one exception that always stays in the brief** — they are execution evidence the worker needs to operate correctly, not governance-history noise.

### Existing canonical selectors

When the brief names the current stage or route, use only the pipeline's existing canonical terms — for example `Implementation`, `Validation after lock`, `Production incident`. Do not define new aliases or a new controlled vocabulary for `Current phase` or any other field.

### When a worker may read beyond the brief

Only when:

- the brief explicitly names an additional source to read;
- the worker discovers a contradiction or missing authority during the task and recovery is required — in which case it stops and returns to the orchestrator rather than reading the corpus itself and continuing;
- the task itself is evolving or auditing the Project-Pipeline governance corpus, rather than executing against an adopted project.

## Required founder-facing response

Follow `docs/FOUNDER_COMMUNICATION.md`.

Do not begin with recovery fields.

First explain in plain language:

- Whether recovery succeeded
- Where the project stands
- What the current step means
- Why it matters

Then separate:

### What has already happened

### What happens next

### What I need from you

When a choice or approval is needed, recommend the strongest option and explain why.

Place repository access, pipeline status, current phase, active change, blocker, recovery confidence, assumptions, and coding status under:

## Technical details

End with:

## What you should do now

Do not expose a skill menu unless the founder explicitly asks for technical detail.
