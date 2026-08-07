# Pipeline Adoption and Versioning

## Adoption

A target repository is pipeline-ready when:

- Canonical documents exist without duplicates
- Agent roles and boundaries are recorded
- Current state is truthful
- Pipeline validation passes
- No product work began without approval

## Versioning

Git history is the pipeline version history.

Do not create files named:

- `pipeline-final.md`
- `pipeline-latest.md`
- `pipeline-v2.md`

## Updating adopted projects

Future pipeline improvements must not be pushed blindly into every project. Inspect each target repository and apply only compatible changes through a reviewed update.

## Post-release validation (Stage 16)

This section is this repository's software-specific mechanics for DEC-016 ("Bounded validation after lock"). It applies to Stage 16, "Production evidence," in `docs/PIPELINE.md`, and does not generalize that stage beyond software.

After release, Stage 16 evidence (Sentry, PostHog, logs, smoke tests) is checked against the change's acceptance criteria.

- If evidence matches the approved change, the change is complete.
- If evidence shows a failure, repair follows the existing change workflow in `AGENTS.md`: Claude fixes within the originally approved scope, not a redefinition of it.
- Repair depth and required audit rigor scale with the risk classification policy defined in `docs/TESTING.md`; the change's own base tier and specialized profiles are recorded in its `spec.md` (or the approved lightweight approval record), not in `docs/TESTING.md` itself. This governs depth and rigor only — it does not set how many repair attempts are allowed.
- The maximum number of bounded repair attempts for this validation target is stated explicitly in the change's `spec.md` (or the approved lightweight approval record for a small-safe change) and tracked there together with `docs/CURRENT.md`'s existing `Active change` and `Exact next action` fields, so the count recovers across sessions. Changing an approved bound requires an explicit approved update to that same record.
- Each repair produces another instance of `verification-report.md` against the same change lineage — not a new report file.
- `docs/CURRENT.md` records the current repair attempt and the failing evidence under the existing `Active change` and `Exact next action` fields — no new field is added.
- A successful repair returns to the same Stage 16 production verification, not a new validation target, with fresh verification evidence.
- Independent Codex audit on a repair follows the recorded risk policy: mandatory when the base tier is High, required for Incident work when operationally possible, and otherwise required only when the approved change, the founder, or a documented risk reclassification requires it. Builder-side review never substitutes for it where it is required.
- If repair would require changing the locked scope or acceptance criteria, exhausts the approved attempt bound, or leaves risk unresolved, escalate to the existing Production-incident route (`docs/PIPELINE.md`) and the manual rollback and production-migration gates already required by DEC-012. Do not repeat repair attempts past this point and do not roll back automatically.

Verification and independent audit stages do not perform this repair themselves (`prompts/verify-change.md`, `prompts/audit-change.md`); repair returns to Claude's implementation stage, then back through fresh verification, with independent audit added only when the risk policy above requires it, before the change is considered complete again.
