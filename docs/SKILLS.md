# Universal Skills Registry

This document defines the approved external capability libraries used by the universal project pipeline, and Bridge4PS's own project-specific adoption record.

## Purpose

The pipeline controls the project process. Skills add specialist knowledge and repeatable workflows inside that process.

Skills do not replace:

- Founder product authority
- Canonical project documents
- Approved OpenSpec changes
- Deterministic tests and CI
- Independent Codex audit
- Founder release approval

## Founder experience

Skill selection and activation are orchestration responsibilities.

The founder must not be required to:

- Know available skill names
- Install or activate skills manually
- Invoke slash commands
- Choose which capability applies
- Manage context windows
- Create specifications or tickets manually
- Decide which technical agent should use a skill

The orchestration hub may report skills used after a stage for transparency, but no founder action is required.

## Approved skill sources

### Product management

Source: `phuryn/pm-skills`

Approved capability areas include product discovery, strategy, market research, execution, metrics, go-to-market, launch, and AI-assisted shipping.

### Engineering discipline

Source: `mattpocock/skills`

Approved capability areas include requirement clarification, repository-aware grilling, prototypes, specification and ticket creation, TDD, disciplined bug diagnosis, domain modelling, codebase design, architecture improvement, Git guardrails, code review, and compact handoffs.

High-value workflows include `grill-with-docs`, specification and ticketing workflows, `tdd`, `diagnosing-bugs`, `domain-modeling`, `codebase-design`, Git guardrails, review, and `handoff`.

### Marketing and growth

Source: `coreyhaines31/marketingskills`

Approved capability areas include product marketing, customer research, positioning, copywriting, CRO, onboarding, SEO, analytics, experiments, email, SMS, social, image, video, pricing, launch, retention, referral, sales enablement, and revenue operations.

Product-marketing context must be established before downstream marketing skills generate claims or campaigns.

## Installation versus activation

Installation or availability means a capability can be used in the project.

Activation means the orchestration hub selects that capability for the current stage and provides only the instructions required by the working agent.

A project may make approved skills available without loading all of them into every context. "Lazy loading" is internal context management, not a founder task.

Prefer project-level installation for governed projects so capability versions, safety rules, and team behaviour remain reproducible. Global installation may be used for personal experimentation but is not the project source of truth.

## Automatic stage routing

### Discovery and clarification

The orchestrator may use:

- PM discovery and assumption workflows
- Repository-aware clarification such as `grill-with-docs`
- Product vision and value-proposition workflows
- Customer-interview workflows when real interviews are planned

### Runnable uncertainty

Use a prototype only when a named question cannot be answered through discussion or static repository inspection.

A prototype must be isolated, disposable, use no production data, answer one question, and not automatically become production code.

### Specification and planning

The orchestrator may use:

- PRD, roadmap, user-story, test-scenario, pre-mortem, and red-team workflows
- Specification transformation
- Ticket creation only for multi-context work
- Domain modelling when terminology affects behaviour or architecture

Approved durable output must be mapped to the active OpenSpec change.

### Implementation

The orchestrator may route:

- TDD
- Codebase design
- Domain modelling
- Git guardrails
- Pre-commit checks
- Fresh-context internal code review

### Bug fixing and incidents

Route disciplined diagnosis, reproduction, regression-test discipline, TDD for the smallest safe fix, and risk-scaled audit.

### Launch and growth

Activate only after product direction and evidence exist.

## Canonical-output rule

Skills may guide work but may not create a competing source of truth.

```text
OpenSpec spec.md = approved destination and acceptance criteria
OpenSpec tasks.md = implementation slices
repository-report.md = investigation evidence
implementation-report.md = builder evidence
verification-report.md = repeatable verification evidence
ux-report.md = user-flow evidence
audit-report.md = independent verdict
```

Do not maintain duplicate local tickets, GitHub issues, scratch specs, and OpenSpec tasks for the same purpose unless a distinct need is explicitly approved.

## Precedence and conflict rules

When instructions conflict, follow this order:

1. Founder-approved decision
2. Canonical project documents
3. Approved active change specification
4. Project agent rules
5. This universal pipeline
6. External skill instructions
7. General model knowledge

A skill may improve execution but may not silently expand scope, change architecture, invent product facts, or override a project decision.

## Context-bloat rule

For each task, the orchestration hub must:

1. Identify the current stage and risk.
2. Select the smallest relevant capability set.
3. Load only those instructions into the working context.
4. Store durable outcomes in canonical documents.
5. Remove or summarize temporary logs and scratch material.
6. Start a fresh context or handoff when required by `docs/CONTEXT_MANAGEMENT.md`.

## Installation policy

- The three upstream repositories are approved sources.
- Record the exact upstream repository and selected skills before project installation.
- Prefer project-level installation.
- Do not vendor or duplicate entire upstream libraries into every repository.
- Do not auto-update skills during an active change.
- Review upstream changes before upgrading.
- Never allow an installer to overwrite canonical project documents or agent rules.
- Availability does not grant permission to bypass founder approvals, tests, audits, or release gates.

## Project adoption requirement

Each adopted project should contain its own `docs/SKILLS.md` stating:

- Approved upstream sources
- Capabilities installed or available
- Capabilities currently active
- Capabilities deferred or restricted
- Project-specific safety boundaries
- Installation status and version when known

The orchestration hub reads this file and selects capabilities automatically. The founder does not operate it.

---

## Bridge4PS project-specific adoption record

### Installation status

No skill library has been installed into this repository. This bootstrap did not install entire skill libraries, per `BOOTSTRAP_CONTRACT.md`.

### Approved upstream sources (available, not installed)

- `phuryn/pm-skills` — available for future product-discovery and go-to-market work. Not installed.
- `mattpocock/skills` — available for future engineering-discipline work (TDD, diagnosing-bugs, codebase-design, handoff). Not installed.
- `coreyhaines31/marketingskills` — available for future marketing/growth work. Not installed.

### Capabilities currently active

None. Product implementation has not started.

### Capabilities deferred

All three upstream sources are deferred until a specific implementation task needs them. Selection remains the orchestration hub's responsibility per `docs/SKILLS.md` → "Installation versus activation".

### Restricted / out of scope for Bridge4PS

The following are explicitly out of current Bridge4PS scope and must not be pulled in by any skill or agent without separate founder approval:

- Ontology work
- HTML migration
- Browser exploration
- Future semantic versions beyond v0.1
- Freshdesk automation
- AppSheet automation
- Video automation

### Bridge4PS-specific safety boundaries

- No skill may import, unpack, or reconstruct `B4PS-TUT-main.zip` or any other baseline content. Baseline import is a separately approved task.
- No skill may generate application code before an approved specification and founder-approved implementation start.
- No skill may reconstruct or invent the detailed Architecture v0.1 specification; it is not present in this repository.
- No skill may begin Repository Hardening Batch 1 before it is separately approved as the next milestone.
