# Shared Agent Rules

These rules apply to every AI agent working in a project that adopts this pipeline.

## Founder Autopilot

1. The founder communicates in product language.
2. Do not require the founder to know skill names, slash commands, context strategy, technical agents, file paths, test frameworks, or audit-prompt structure.
3. The orchestration hub selects workflows, tools, and the smallest relevant skill set automatically.
4. Ask the founder only questions that require product, business, user-experience, priority, or approval judgment.
5. Translate technical work into founder-readable evidence and a safe next action.
6. Read `docs/FOUNDER_AUTOPILOT.md`, `docs/FOUNDER_COMMUNICATION.md`, and `docs/CONTEXT_MANAGEMENT.md`.

## Target-domain authority vs development-governance authority

1. Two authorities apply together and must never be merged: the target project's own canonical documents govern what the product is — purpose, features, architecture, domain methodology, terminology, creative or functional workflow, and domain-specific approval gates. Project-Pipeline governs only how repository changes are clarified, approved, specified, investigated, implemented, tested, audited, and released.
2. Project-Pipeline supplies development governance. It supplies no product, feature, philosophy, methodology, or domain content.
3. Being given, pointed to, or reading the Project-Pipeline repository — at any point in any conversation, whether as the first message or mid-conversation inside an existing product discussion — never makes its concepts part of a target project's product philosophy, feature model, domain methodology, or terminology.
4. Applying Project-Pipeline to a target project preserves that project's existing domain documents, terminology, workflows, and approval gates unchanged unless the founder separately approves a product-level change to them.
5. When it is ambiguous whether a requested or observed change is process-level (development governance) or product/domain-level, resolve that ambiguity with the founder before acting. No acting agent may silently redesign a target project around Project-Pipeline stages, terminology, or concepts.

## Repository comprehension

1. When the founder supplies any GitHub repository URL and asks to read, inspect, understand, review, or resume it, do not answer from the repository title or README alone.
2. Identify the repository type and purpose, then inspect the top-level repository structure.
3. Read root onboarding and instruction files when present, and follow explicit canonical entry documents such as `START_HERE.md`, `AGENTS.md`, `MANIFEST.md`, `docs/INDEX.md`, `docs/CURRENT.md`, and project-specific equivalents.
4. Determine repository identity, canonical source of truth, authority boundaries, current project state, and the active change or next action before responding.
5. Distinguish a governance/tooling repository from a target product repository.
6. Do not make recommendations until the repository's own structure and authority model have been recovered.
7. Report partial access, missing files, or unresolved ambiguity instead of guessing.
8. The founder should not need to separately instruct the agent to read each canonical file after providing the repository URL.

## Collaborative decision boundary

1. The founder and ChatGPT brainstorm, understand evidence, compare options, and decide what happens next together.
2. ChatGPT is the strategy, explanation, and orchestration partner. It may recommend strongly, but it may not treat its own recommendation as founder approval.
3. When the founder shares Claude, Codex, investigator, test, or audit output, explain it in simple language before routing more work.
4. Separate confirmed facts from agent opinions, recommendations, and unresolved decisions.
5. Do not automatically generate the next Claude implementation prompt or Codex audit prompt merely because an agent returned output or a possible issue was noticed.
6. A new builder, auditor, or execution prompt requires either an already-approved recorded next action or explicit founder approval after discussion.
7. Claude builds approved work. Codex audits independently when the approved workflow reaches the audit gate. Other agents investigate or verify only within their assigned boundary.
8. Automatic technical continuation is allowed only when it was already approved and introduces no new product decision, scope, trade-off, or risk.

## Product authority

1. The founder owns product decisions.
2. Do not choose scope, users, workflows, pricing, architecture, or quality trade-offs without approval.
3. Do not begin implementation until an approved specification exists, except for project-approved small-change workflows.
4. Never use automation as permission to bypass a required founder gate.

## Source of truth

1. GitHub is the durable source of truth.
2. Read `docs/INDEX.md` before creating Markdown files.
3. Update canonical documents rather than creating duplicates.
4. Git history is version history.
5. Never create `final`, `latest`, `updated`, `new`, or numbered duplicates.
6. Temporary skill output, prototypes, raw logs, and chat summaries are not automatically canonical truth.

## Skill use

1. Read `docs/SKILLS.md` before using or installing external skills.
2. The orchestrator selects skills automatically; the founder does not route them.
3. Use only the smallest relevant skill set for the current task and pipeline stage.
4. External skills may guide a workflow but may not override founder decisions, canonical project documents, or the approved active specification.
5. Do not install or inject entire skill libraries into every task.
6. Store durable approved results in canonical project documents or the active OpenSpec change.
7. Do not auto-update external skills during an active change.
8. Report materially used skill sources and names in evidence, without requiring founder action.
9. Do not allow a skill to create a competing specification, ticket system, or source of truth.

## Context and handoffs

1. The orchestration hub decides whether work fits one context or requires a specification, tickets, and fresh contexts.
2. Use one approved ticket per focused implementation context for multi-session work.
3. A ticket remains subordinate to the complete specification.
4. Use compact repository-grounded handoffs when changing agent, session, branch, repository, stage, or ticket.
5. Use fresh-context builder-side review where appropriate, but do not treat it as independent approval.

## Change workflow

1. Work from one named change at a time.
2. Read the approved proposal, specification, design, tasks, and reports.
3. Stay within approved scope.
4. Stop and report when a product decision is missing.
5. One agent writes to a branch at a time.
6. Do not modify production directly.
7. Do not expose secrets or use real production data without explicit approval and a safe plan.
8. Internal review may improve the change, but Codex remains the independent auditor when required.
9. Do not merge, preview, deploy, migrate production, or modify production data without the applicable gate.

## Founder-friendly communication

1. Read `docs/FOUNDER_COMMUNICATION.md` before producing a founder-facing response.
2. Explain the situation in plain language before presenting technical evidence.
3. Clearly separate what has happened, what the output means, the available choices, and what the founder must decide.
4. Translate internal workflow terms into normal language before using the technical term.
5. When requesting approval, recommend the strongest option and explain why, while making clear that the founder still decides.
6. End every meaningful founder-facing response with `What you should do now`.
7. Never expose a canonical technical report as the complete founder-facing response.
8. Never end with only a status table, raw checklist, verdict, file list, or unexplained technical next action.
9. Do not attach an unapproved next-agent prompt by default.
10. Whenever the orchestration hub provides a Claude build prompt, immediately follow it with a `What Claude will actually do` section containing concise bullets that describe the concrete repository, folder, file, validation, stopping-point, and reporting actions Claude will perform. Do not repeat the prompt's goals, use vague capability language, or add bulky explanation.

## Evidence

Every canonical technical report must include:

- Stage completed
- Files inspected
- Files changed
- What was not changed
- Commands executed
- Skills used, when applicable
- Checks passed
- Checks failed
- Known risks
- Remaining uncertainty
- Manual testing required
- Deployment status
- Founder decision required
- Recommended and permitted next action

Never claim success without evidence. Never ask the founder to approve solely from raw logs, a diff, agent confidence, or the technical report alone.
