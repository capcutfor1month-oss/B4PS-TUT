# Pipeline Update Recommendations

## Approved direction

The universal pipeline should operate as an AI software-development department controlled by a product-focused founder.

The founder provides:

- Product problems
- Desired solutions and user experience
- Business rules and priorities
- Feedback and final approvals

The pipeline automatically provides:

- Repository recovery
- Product clarification
- Skill and tool routing
- Specifications and implementation slices
- Claude handoffs
- Automated testing and evidence
- Builder-side review
- Codex independent audit
- Founder manual-test instructions
- Preview, production, and documentation gates

The founder must not need to learn skill names, developer commands, context-window management, technical agent selection, or audit-prompt construction.

## Findings incorporated from workflow research

### Governed skills flow

Approved external skills should work inside the pipeline rather than replace it.

```text
Founder idea
→ automatic repository-aware clarification
→ prototype only for a named runnable uncertainty
→ OpenSpec specification
→ tickets only for multi-context work
→ one approved implementation slice
→ fresh-context builder-side review
→ deterministic checks
→ Codex independent audit when required
→ founder test and approval
```

Useful engineering workflows include `grill-with-docs`, prototype, specification, ticketing, implementation, diagnosis, TDD, codebase design, handoff, and code review. The orchestration hub selects them automatically.

### Installation versus activation

Approved developer capabilities may be installed or available at project level. Activation remains stage-based and automatic so irrelevant instructions do not overload the working context.

"Lazy loading" is an orchestration responsibility, not a founder task.

### Canonical output mapping

Do not create duplicate specifications or issue systems.

```text
OpenSpec spec.md = approved destination and acceptance criteria
OpenSpec tasks.md = ordered implementation slices
implementation-report.md = builder evidence
verification-report.md = repeatable verification evidence
ux-report.md = user-flow evidence
audit-report.md = independent Codex verdict
```

### Review separation

Builder-side fresh-context review is valuable and should happen before handoff. It cannot replace Codex because the implementer must not issue its own independent release verdict.

## Immediate repository updates

1. Add Founder Autopilot as the default user experience.
2. Make skill routing invisible to the founder.
3. Add automatic natural-language workflow classification.
4. Add governed context-management and one-ticket-per-focused-context rules.
5. Require founder-readable stage reports.
6. Preserve explicit manual gates for product, data, architecture, and production decisions.
7. Strengthen reusable prompts so each agent receives a bounded task and mandatory return contract.
8. Extend pipeline validation to require the new canonical documents and key policy language.

## Next operational upgrades

After this governance update:

1. ~~Complete risk-based `docs/TESTING.md`.~~ Done — see `docs/TESTING.md` for base risk tiers, cumulative specialized evidence profiles, the canonical recording surface, and deterministic independent-audit triggers.
2. Complete preview, production, rollback, and verification gates in `docs/RELEASE.md`.
3. Add bootstrap automation and idempotency tests.
4. Add incident and hotfix workflow.
5. Add formal pipeline versioning and adoption compatibility reports.
6. Pilot the complete workflow on a target project the founder supplies.

## Target-project pilot

### Round 1 — Adoption and recovery only

- Start from the founder-supplied target project repository URL
- Recover repository state and confidence
- Detect missing or conflicting pipeline files
- Apply compatible prerequisites on a setup branch
- Preserve current product code
- Validate and report
- Stop before product implementation

### Round 2 — One controlled real change

```text
product problem
→ automatic clarification
→ approved OpenSpec change
→ investigation
→ Claude implementation
→ builder-side review
→ GitHub Actions
→ browser and UX verification where relevant
→ Codex audit
→ founder manual test
→ preview
→ production approval
→ production verification
```

Every point where the founder must manage technical workflow, an agent guesses, evidence is missing, or unsafe progression occurs should be treated as a pipeline defect.

## Deferred complexity

Do not add yet:

- More mandatory agents
- More external skill libraries
- Fully autonomous production deployment
- Automatic production migrations
- Parallel builders by default
- A custom multi-agent SDK
- Mandatory Task Master or BMAD
- Multiple competing issue trackers

The next phase is operational proof, not capability expansion.
