# Verify Change

The orchestration hub invokes verification against the exact implementation commit.

## Instructions

- Work from the orchestrator's compiled brief (`docs/PIPELINE.md` → "Context recovery"; `prompts/start-project-session.md`) rather than re-reading the complete approved specification, ticket status, implementation report, or project testing policy directly, except when the brief names one of them, a contradiction or missing authority surfaces, or the task is auditing the Project-Pipeline governance corpus itself. Read `docs/FOUNDER_COMMUNICATION.md` directly for the founder-facing return.
- Confirm repository, branch, commit, and environment tested.
- Run the repeatable checks required by the change risk.
- Verify every acceptance criterion, important failure state, and relevant historical-data behaviour.
- Check authentication, authorization, tenant isolation, migrations, mobile and desktop behaviour when relevant.
- Confirm no silent scope expansion or unrelated regression is evident.
- Do not make product decisions.
- Do not repair production code unless separately assigned.
- Summarize failures instead of pasting large logs.
- Write `verification-report.md`.

## Founder-facing return

Before the technical report, provide a concise explanation following `docs/FOUNDER_COMMUNICATION.md`.

Explain:

- Whether the change works as intended
- Why this proof matters before continuing
- What passed and what remains uncertain
- What happens next
- What the founder needs to test, decide, or approve
- The recommended next action and reason

End with:

## What you should do now

## Technical evidence

```text
Stage completed: Verification
Repository, branch, commit, and environment:
Acceptance criteria verified:
Test data used:
Commands executed:
Checks passed:
Checks failed:
Failure states tested:
Database and historical-data findings:
Authentication and tenant findings:
UI and device findings:
Areas not tested:
Known risks:
Remaining uncertainty:
Founder manual-test steps:
Founder decision required:
Permitted next action:
```
