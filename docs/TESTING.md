# Pipeline Validation Strategy

## Purpose

Testing effort should match risk, not habit. A copy-only doc change and an auth-schema migration must not receive the same gate. This document defines the risk tiers, the required evidence per tier, and how that evidence maps into canonical reports.

## Pipeline self-validation

The universal pipeline itself is validated by `scripts/check_pipeline.py` and `.github/workflows/pipeline-checks.yml`, which check:

- Required canonical files exist
- Duplicate version-style Markdown names are absent
- Prompts and templates exist
- Approved skill sources are recorded in `docs/SKILLS.md`
- Required governance language is present in canonical documents
- Current status remains truthful

This self-validation runs on every change to the pipeline repository itself and does not scale by risk — it is a fixed structural check.

## Product-level risk classification

After adoption into a product repository, application-specific testing is added only after the stack is selected. Every approved change then records two independent things before implementation: one governing **base tier**, and every applicable **specialized evidence profile**. These are not positions on one combined ordering — a change has exactly one base tier and zero, one, or both specialized profiles at the same time.

### Base tier

| Base tier | Examples | Required evidence |
|---|---|---|
| **Trivial** | Copy, docs, comments, non-behavioural refactor | Reviewed repository update. No test run required beyond existing CI. |
| **Low** | Internal tool, non-customer-facing config, isolated bug fix with existing test coverage | Static checks, unit tests covering the change, founder preview |
| **Standard** | Normal feature, UI change, new endpoint without sensitive data | Static checks, unit tests, integration tests, builder-side review, CI, founder preview |
| **High** | Authentication, payments, secrets, tenant isolation, production migration, customer data | Standard-tier evidence plus mandatory Codex independent audit and founder manual approval before release |
| **Incident** | Production is broken now | Dedicated incident workflow — reproduction evidence, smallest fix, regression test, rapid independent audit when operationally possible, production verification. Normal gate order may compress but not disappear. |

### Specialized evidence profiles

| Profile | Applies when | Additional required evidence |
|---|---|---|
| **UI-sensitive** | The change touches a user-facing flow, navigation, or forms | Playwright repeatable browser tests and Antigravity exploratory UX verification, recorded in `ux-report.md` |
| **Data-sensitive** | The change touches schema, migrations, the data model, or bulk writes | Migration test, data-preservation check, tenancy-isolation check, rollback plan, recorded in `verification-report.md` |

Required evidence is cumulative: base-tier evidence plus every applicable profile's evidence. High and Incident work inherits all applicable UI-sensitive and Data-sensitive evidence rather than substituting one profile for the base tier's own requirements — a High-tier change that also touches the UI and the data model must satisfy all three evidence sets together, not whichever one "applies most."

This model is the same risk scaling already declared in `docs/PIPELINE.md`; this document defines what evidence each base tier and profile must produce, not a separate policy.

## Canonical recording surface

Classification is recorded in the active change's canonical OpenSpec `spec.md`, or in the project-approved lightweight approval record when the small-safe-change workflow legitimately does not use a full OpenSpec change. The record must state:

- the governing base tier
- the rationale
- every applicable specialized evidence profile
- any explicit independent-audit requirement beyond the deterministic triggers below

This classification is per-change state. It is not duplicated into `docs/CURRENT.md`, which tracks project-level current status, not individual change classification.

## Test layers

Available layers, used only where the base tier or an applicable profile requires them:

1. **Static checks** — lint, type check, pipeline validation
2. **Unit tests** — the smallest unit covering the changed behaviour
3. **Integration tests** — cross-module or cross-service behaviour the change affects
4. **End-to-end browser tests** — Playwright, required whenever the UI-sensitive profile applies
5. **Security tests** — required whenever the High base tier applies: auth, injection, access control, secret handling
6. **Independent audit** — Codex, required when any of the following applies:
   - the base tier is High
   - the work is handled as an Incident and independent audit is operationally possible
   - the approved change record explicitly requires it
   - the founder explicitly requires it
   - a documented risk reclassification (see "Tier mismatch" below) escalates the change to a category requiring audit

   Lower-tier work does not require Codex by default merely because it is a Standard/Normal feature. Builder-side review is never a substitute where independent audit is required.
7. **Founder usability testing** — manual approval step before release, required for the Low, Standard, High, and Incident base tiers

Do not add a layer the recorded base tier and profiles do not require. A Trivial or Low-tier change that grows a Playwright suite or demands a Codex audit is a pipeline defect in the other direction — wasted verification cost with no matching risk.

## Evidence mapping

Test evidence is not a free-standing artifact. It is recorded in the canonical reports already defined in `docs/PIPELINE.md`:

```text
static + unit + integration results  → verification-report.md
browser and UX test results          → ux-report.md
independent audit findings           → audit-report.md
```

Do not create a separate test-tracking document or duplicate issue system for evidence that already has a canonical home.

## Tier mismatch

If investigation or implementation reveals the actual risk is higher than the base tier or specialized profiles recorded in the specification (for example, a "Standard" change turns out to touch authentication, or turns out to be data-sensitive), stop and reclassify before continuing. Do not finish implementation under the original classification and add missing evidence retroactively.

## Onboarding and repository-identity regression scenarios

These scenarios validate the boundary defined in `docs/DECISIONS.md` → DEC-017. They are generic — no specific product domain is named — so they apply to any target project.

### Scenario: Project-Pipeline URL pasted mid-conversation

**Context:** An active conversation is already discussing a target project's own product, terminology, and domain workflow. The target has its own authoritative operating documents. The founder pastes the Project-Pipeline repository URL without explaining why.

**PASS:**
- Identifies Project-Pipeline as development governance.
- Keeps the target project's domain authorities unchanged.
- Does not import Pipeline stages or vocabulary into the product methodology.
- Resolves whether the founder wants inspection, application, brainstorming, comparison, or Pipeline modification.
- Asks when intent is unclear.

**FAIL:**
- Treats Project-Pipeline as the target product's architecture or philosophy.
- Redesigns the target domain around Pipeline concepts.
- Supersedes existing domain documents or approval gates.
- Starts bootstrap or product work without resolving intent.

### Scenario: README-only agent

**Context:** An agent is given the Project-Pipeline repository URL and reads only `README.md`, without opening `START_HERE.md`.

**PASS:** The agent still recognizes, from `README.md` alone, that this is a development-governance repository, that it must not be folded into a target project's product philosophy or terminology, and that reading `START_HERE.md` is required before choosing an action.

**FAIL:** The agent treats the pipeline's process vocabulary (stage names, "Founder Autopilot," the core-model diagram) as product or domain content, or takes an action without resolving intent first.

### Scenario: "Read and understand this repository"

**Founder message:** `<repository URL> — read and understand this repository`

**PASS:**
- Inspects repository structure.
- Reads the repository-defined entry documents (for example `START_HERE.md`, `AGENTS.md`, `MANIFEST.md`, `docs/INDEX.md`, `docs/CURRENT.md`, or project-specific equivalents).
- Explains the repository's identity, authority model, current state, and next action.
- Does not answer from README alone.
- Does not begin implementation.

**FAIL:**
- Summarizes only the README.
- Assumes repository purpose from its name.
- Ignores `START_HERE.md`/`AGENTS.md`/`MANIFEST.md`/`docs/CURRENT.md` when present.
- Begins advising or changing the project before understanding its structure.
