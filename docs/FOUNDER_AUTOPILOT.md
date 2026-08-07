# Founder Autopilot Mode

## Purpose

Founder Autopilot Mode is the default operating experience for projects using this pipeline.

The founder communicates in product language. The orchestration hub automatically handles development workflow selection, skill routing, context management, specifications, implementation handoffs, verification, audits, documentation, and safe next actions.

The pipeline exists so the founder does not need to become a developer or learn agent commands.

## Founder responsibilities

The founder is responsible for:

- Describing the product problem or desired result
- Explaining important user behaviour and business rules
- Choosing priorities and product trade-offs
- Reviewing the real user experience
- Approving specifications, high-risk actions, preview, and production release

The founder is not responsible for:

- Knowing skill names or slash commands
- Selecting or lazy-loading skills
- Managing context windows
- Choosing technical agents
- Writing specifications or tickets manually
- Interpreting raw code, terminal output, or test logs
- Creating technical audit prompts
- Deciding which test framework or repository files to use

## Collaborative strategy and decision rule

ChatGPT is the founder's brainstorming, interpretation, and strategy partner. Its job is to:

- Understand the founder's idea, concern, or goal
- Explain Claude, Codex, investigator, and verification output in simple language
- Separate confirmed facts from agent opinions and recommendations
- Surface useful options, risks, trade-offs, and a strongest recommendation
- Discuss the recommendation with the founder before turning it into the next approved action

The founder and ChatGPT decide the next product move together.

ChatGPT must not silently convert its own observation or recommendation into:

- An approved product decision
- A scope change
- A new implementation instruction for Claude
- A new audit instruction for Codex
- A decision to reopen frozen work
- Progression through an approval gate

When the founder pastes Claude or Codex output, the default response is to explain what it means and discuss the available choices. Do not automatically produce the next agent prompt unless the founder asks for it or approves the recommended next step.

Automatic technical continuation is allowed only when that continuation was already explicitly approved and introduces no new product decision, trade-off, scope, or risk.

Role boundary:

- **Founder + ChatGPT:** brainstorm, understand, compare options, and decide what happens next
- **Claude:** build or change only the approved work
- **Codex:** independently audit when the approved workflow reaches the audit step
- **Other agents and tools:** investigate, verify, or execute only within their assigned approved boundary

## Simplest entry point

In a new ChatGPT session, the founder pastes only the target project repository URL.

Example:

```text
https://github.com/capcutfor1month-oss/example-project
```

The founder may then describe a problem naturally:

```text
The dashboard is confusing. Owners should immediately understand students,
fees, seats, and what needs attention.
```

The founder does not need to paste the universal pipeline URL into every agent. An adopted target repository must contain its project-specific operating files and a reference to this canonical pipeline.

## Orchestration responsibilities

The orchestration hub must automatically:

1. Confirm repository access and recovery confidence.
2. Read the universal pipeline and target-project canonical documents.
3. Recover current project state from GitHub.
4. Classify the founder's request and choose the correct workflow.
5. Determine risk and required approval gates.
6. Select the smallest relevant skills and tools without asking the founder to operate them.
7. Ask only product-level questions that require founder judgment.
8. Record approved decisions in the target repository.
9. Create or update the appropriate OpenSpec change.
10. Decide whether the work fits one focused implementation context or requires tickets and handoffs.
11. Prepare concise instructions for Claude, investigators, verification tools, and Codex only after the relevant next action is approved.
12. Translate technical evidence into a founder-readable decision report.
13. Prevent unsafe or unapproved progression when evidence, discussion, or approvals are missing.
14. Update current state and exact next action before ending the working session.

Skill names may be reported after use for transparency, but the founder must never be required to invoke or route them manually.

## Natural-language workflow routing

| Founder says | Orchestrator routes to |
|---|---|
| "Continue this project" | Recover repository state and resume the recorded approved next action |
| "I have a new idea" | Discovery, clarification, feasibility, and discussion before specification |
| "This part is confusing" | Product clarification, repository inspection, and scoped UX discussion |
| "Build this feature" | Clarification, approved specification, investigation, implementation, and verification |
| "Something is broken" | Incident or bug workflow with reproduction and regression evidence |
| "Check Claude's work" | Explain the evidence first, then perform an independent Codex audit when approved or required |
| "Prepare this for release" | Preview or production release gates and founder approval |
| "What should we build next?" | Recover current evidence, priorities, and blockers; discuss the smallest valuable next change |

The founder may use different wording. The orchestrator must infer the workflow from intent rather than require special commands.

## Automatic skills workflow

The orchestrator may internally use approved skills such as:

```text
grill-with-docs
prototype
to-spec
to-tickets
diagnosing-bugs
tdd
codebase-design
handoff
internal code review
```

The governed default flow for a normal feature is:

```text
Founder problem
→ automatic clarification and repository inspection
→ founder + ChatGPT discuss options and agree on behaviour
→ OpenSpec specification
→ tickets only when multiple focused contexts are needed
→ Claude implements one approved slice
→ fresh-context builder-side review
→ deterministic checks
→ Codex independent audit when required
→ founder manual test
→ preview and production approval gates
```

Builder-side review improves work before handoff but never replaces independent Codex audit or founder approval.

## Founder-facing communication

All responses shown directly to the founder must follow `docs/FOUNDER_COMMUNICATION.md`.

Technical evidence remains mandatory, but it must appear after the plain-language explanation.

A meaningful response must clearly separate:

1. What has already happened
2. What the evidence or agent output means
3. The available choices and recommendation
4. What happens next only after the founder decides or approves

When approval is required, recommend the strongest option and briefly explain why. A recommendation is not approval.

Every meaningful response must end with:

## What you should do now

The founder must not be asked to approve work based only on agent confidence, raw logs, a code diff, a status table, or an unexplained technical verdict.

## Mandatory manual approval gates

The following remain manual even in Founder Autopilot Mode:

- Product behaviour and business rules
- Pricing and major scope decisions
- Major architecture changes
- Destructive data operations
- Production migrations
- Access to real customer or production data
- Preview or production deployment when risk requires approval
- Public launch
- Rollback when business impact is unclear

Autopilot automates development operations. It does not remove collaborative product discussion, founder authority, or safety gates.