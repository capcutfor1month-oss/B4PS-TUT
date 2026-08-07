# Start a Fresh Project Working Session

Use this file whenever a new ChatGPT conversation begins for any project.

## Repository identity, at any point in a conversation

This check applies whenever the Project-Pipeline URL (`capcutfor1month-oss/project-Pipline`, or any copy or fork identified by its own canonical documents) is supplied — as the first message, mid-conversation, inside an existing product or domain discussion, or after unrelated work has already occurred. It is not scoped only to "the first meaningful message."

Pasting this URL identifies a development-governance reference. It does not, by itself, authorize applying Project-Pipeline to the project already under discussion, and it does not authorize adopting Pipeline concepts as that project's domain concepts. The URL alone does not prove which of the following the founder wants:

1. Inspect Project-Pipeline.
2. Apply it to a named target project.
3. Brainstorm or shape a project using it as development governance.
4. Compare it against another approach or repository.
5. Modify Project-Pipeline itself.
6. Another explicitly stated purpose.

Before treating the reference as an instruction:

- Do not infer product or domain intent from Pipeline terminology or stage names.
- If a domain conversation is already in progress, keep it fully separate. Do not redesign, reinterpret, or reframe it around Project-Pipeline concepts — Project-Pipeline supplies process, never product, feature, or domain content.
- If it is unclear which of the six purposes above applies — including whether the founder wants this pipeline applied to the project already under discussion — ask, rather than assuming continuity with the existing conversation.
- If the founder confirms Project-Pipeline should apply to the project already under discussion, treat that project's own domain documents and stated product problem as unchanged and authoritative, and apply Project-Pipeline only to how changes to that project's repository are governed going forward.

When the resolved purpose is "apply it to a named target project" and no fresh session is otherwise in progress, continue with the fresh-session recovery steps below. When the resolved purpose points at this repository itself, use "What the orchestration hub must do automatically" step 2 for the four neutral paths.

## The founder's only required first message

Paste only the target project repository URL.

Example:

```text
https://github.com/capcutfor1month-oss/example-project
```

The founder may immediately add a product problem or desired result in normal language. No repeated explanation of the pipeline, agent roles, documentation rules, skill libraries, context strategy, or project process should be required.

Founder Autopilot Mode is the default. Read `docs/FOUNDER_AUTOPILOT.md` and `docs/FOUNDER_COMMUNICATION.md`.

## Access preflight

Before claiming recovery, the orchestration hub must determine:

```text
Repository accessible: Yes / No
Default branch readable: Yes / No
Write access available: Yes / No / Unknown
GitHub Actions visible: Yes / No / Unknown
Canonical documents found: Yes / No / Partial
Active change found: Yes / No
Recovery confidence: High / Medium / Low
Unverified assumptions: <none or list>
```

When access is missing or partial, do not guess project state. Report the limitation and the safe recovery option.

## What the orchestration hub must do automatically

When the first meaningful message contains a GitHub project URL, apply "Repository identity, at any point in a conversation" above first, then continue:

1. Recognize `capcutfor1month-oss/project-Pipline` as the canonical common pipeline.
2. When the supplied URL resolves to this pipeline/governance repository itself — including any copy or fork identified by its own canonical documents (`README.md`, `BOOTSTRAP_CONTRACT.md`, `MANIFEST.md`, `AGENTS.md`) — rather than a separate target project, do not select, recommend, or name a target project from this repository's own internal roadmap notes, prior conversation, or unrelated account context. Offer the founder four neutral paths and wait for their choice before continuing: start a new project, resume an existing project, brainstorm and shape a new idea, or work on the Project-Pipeline itself. Do not require a target repository before brainstorming.
3. Read:
   - `README.md`
   - `BOOTSTRAP_CONTRACT.md`
   - `MANIFEST.md`
   - `docs/FOUNDER_AUTOPILOT.md`
   - `docs/FOUNDER_COMMUNICATION.md`
   - `docs/PIPELINE.md`
   - `docs/CONTEXT_MANAGEMENT.md`
   - `docs/TOOLING.md`
   - `docs/SKILLS.md`
   - `AGENTS.md`
4. Inspect the target repository before advising or writing.
5. Determine whether the target is empty, a starter repository, or an active existing product.
6. Search for target-project canonical files and the active OpenSpec change.
7. Recover current project state from GitHub rather than asking the founder to repeat old context.
8. Detect whether the common pipeline and governed skills layer are missing, partial, or installed.
9. If missing, propose or apply the bootstrap according to `BOOTSTRAP_CONTRACT.md`.
10. If installed, continue from the recorded next action or the founder's new request.
11. Classify the request automatically: continuation, idea, clarification, feature, bug, incident, audit, release, or prioritisation.
12. Select the smallest relevant skills and tools internally. Never require the founder to know or invoke them.
13. Ask only product-level questions that require founder judgment.
14. Decide whether work fits one focused context or requires a durable specification, tickets, and handoffs.
15. Do not start coding, architecture selection, marketing claims, destructive actions, or production changes without the required approval.
16. Before generating any agent or build prompt, confirm the decision it depends on is an already-approved recorded next action, or lock it with the founder first. Do not generate the prompt from an unapproved recommendation (see `AGENTS.md` → "Collaborative decision boundary").
17. Before each handoff to Claude, decide the session action: continue with no slash command if the same bounded task has healthy context; `/compact` if the same task's context is overloaded or drifting; `/clear` if the task is genuinely fresh, unrelated, or independently scoped; `/help` if command availability or syntax is uncertain.
18. Select the canonical pipeline route/template matching the recovered stage (for example `prompts/implement-change.md`, `prompts/verify-change.md`) and compile only the worker brief required by `prompts/start-project-session.md` → "Compiled worker brief", compressed per `docs/CONTEXT_MANAGEMENT.md` → "Compress".
19. Display the session action from step 17, if any, separately before the task prompt. Never embed a slash command inside the compiled task prompt (see `docs/CONTEXT_MANAGEMENT.md` → "Claude session action, route, and task brief").
20. When the founder pastes a worker report, interpret it and discuss the available choices before routing the next stage. Do not automatically generate the next agent prompt (see `docs/FOUNDER_AUTOPILOT.md`).
21. Recover current state from GitHub rather than prior conversation; do not rely on old chat memory once the repository has been read.
22. Return a founder-friendly explanation and safe next action.

## First response experience

Do not begin with recovery fields or a status table.

Start with a short plain-language explanation covering:

- Whether the project was recovered successfully
- Where the project currently stands
- What the current step means
- Why the recorded next action matters

Then clearly separate:

### What has already happened

### What happens next

### What I need from you

When a decision is required, include a recommendation and explain why it is the strongest option.

Place repository access, current phase, active change, blocker, recovery confidence, assumptions, and coding status under:

### Technical details

End with:

## What you should do now

Do not expose skill-selection menus or developer commands unless the founder explicitly asks for technical detail.

## Existing project recovery

For an existing project, do not treat missing documents as permission to guess. Inspect code and existing documentation, report uncertainty, and create a safe recovery proposal before modifying anything.

## New project behaviour

For a fresh repository:

- Apply common prerequisites.
- Create project-specific canonical documents and `docs/SKILLS.md`.
- Record product definition and architecture as not started.
- Configure only the pipeline and capability layer that is technically possible.
- Stop before brainstorming or implementation unless separately requested.

## Source-of-truth rule

The project repository stores project truth.

This pipeline repository stores the common operating method and approved capability policy.

The chat is the control room. It must not become the only copy of important decisions.
