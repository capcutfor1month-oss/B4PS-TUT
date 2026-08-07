# Independent Audit Report — Safe PPT Engine

This file records the history of independent Codex audits of the Safe PPT Engine, as required by `docs/PIPELINE.md` ("independent audit findings → `audit-report.md`") and Codex finding F-06. **This document is a truthful record of past audit results, not an audit performed by Claude.** Claude cannot self-certify closure of an independent audit finding — only Codex's own re-audit can.

## Founder summary

### Where things stand

The Safe PPT Engine has been independently audited by Codex twice. Both times, real defects were found. Two repair rounds (Audit Repair 1 and Audit Repair 2) have addressed every finding from both audits, verified by Claude's own test suite — but **neither repair has itself been independently re-audited yet**. The engine's safety claims should be treated as implementer-verified, not independently verified, until that happens.

### Why this matters

This engine exists specifically to prevent PPTX source-file corruption and data loss. Its safety guarantees are exactly the kind of claim that should not rest on self-attestation alone — that is why independent audit was sought in the first place, and why a third round (re-auditing Audit Repair 2) is the necessary next step, not optional.

### What has already happened

Two audit rounds, two repair rounds — see the technical evidence below for the finding-by-finding history.

### What happens next

An independent Codex re-audit of Audit Repair 2. Not performed as part of this change.

### Founder action or decision

None required to merge Audit Repair 2 itself (it is bounded implementation work responding to already-approved audit findings). Founder should be aware that final trust in the engine's safety guarantees is contingent on the pending third-round re-audit, not yet complete.

### Recommended option and reason

Commission the independent Codex re-audit of Audit Repair 2 before building any further capability (Editorial Memory, Documentation Intelligence) on top of this engine.

## Technical evidence

### Verdict

**History across three rounds (see below for detail):**

| Round | Scope audited | Verdict |
|---|---|---|
| Audit 1 | Safe PPT Engine Builds 1–2 | **FAIL** — 8 findings (F-01–F-08: 1 critical, 2 high, 3 medium, 2 low) |
| Audit 2 (re-audit) | Audit Repair 1 | **FAIL** — 6 findings remaining (F-02, F-04, F-05, F-06, R-01, R-02); F-01, F-03, F-07, F-08 confirmed CLOSED |
| Audit 3 (re-audit) | Audit Repair 2 (this change) | **NOT YET PERFORMED** |

### Specification reviewed

`openspec/changes/safe-ppt-engine/spec.md` (created as part of Audit Repair 2, in response to F-06 — did not exist at the time of either prior audit).

### Diff and files reviewed

Audit 1: `lib/ppt_engine.py`, `b4ps.py` as of Safe PPT Engine Build 2 (commit `a475d238f0c36f634d1ca9e23a9f4e2dae8441d5`). Audit 2: the same files as repaired by Audit Repair 1 (commit `13b3b532528b52a808030840734da9e58d92cfeb`). Audit 3: not yet performed; would review this change's commit once merged.

### Skills declared by prior stages

None — this repository has not activated any external skill library (`phuryn/pm-skills`, `mattpocock/skills`, `coreyhaines31/marketingskills`) for this work; see `docs/SKILLS.md`.

### Evidence reviewed

Audits 1 and 2 were performed externally (Codex); their internal working evidence is not reproduced here. This record reflects only the founder-communicated finding IDs, severities, and pass/fail verdicts, which is what this repository can truthfully attest to.

### Skill-governance findings

Not applicable — no external skill was used in scope for either repair.

### Blockers

Independent re-audit of Audit Repair 2 has not been scheduled or performed. This is the single blocker to closing the engine's audit history.

### Non-blocking improvements

None recorded beyond what is already tracked as deferred functionality in `docs/CURRENT.md` (additional mutation primitives, semantic targeting, etc. — all explicitly out of scope for the engine's current mechanical-primitives milestone).

### Security and privacy findings

Audit 1: F-01 (critical) source aliasing could allow the mutation source to be overwritten; F-04 (medium) stale/sensitive media could remain in a saved package after replacement. Both were the closest thing to security-relevant findings in this component (local file-integrity and data-remnant concerns, not network/auth/secrets, which do not apply here). Audit 2: F-04 was found insufficiently fixed (relationship-cleanup scope was too narrow, risking either leaving stale media behind or, in the background-sharing case, breaking a still-used relationship). Both are addressed in Audit Repair 1 and Audit Repair 2 respectively — see `verification-report.md` for the fix-by-fix account. Independent confirmation of the Audit Repair 2 fix is exactly what the pending Audit 3 would provide.

### Regression findings

Audit 2 confirmed F-01, F-03, F-07, and F-08 (from Audit 1) were correctly closed by Audit Repair 1, with no regression. Audit Repair 2's own test suite includes explicit regression guards for all four (`tests/test_ppt_engine_audit_repair_2.py::test_regression_*`), run on every test invocation.

### Test-quality findings

Audit 2's R-02 finding stated the Audit Repair 1 test suite proved end-state outcomes (e.g., "no leftover temp file") without proving the actual mechanism (e.g., that a non-picture target results in *zero* calls to the staging function, not merely a cleaned-up one). Audit Repair 2 addresses this with mechanism-level tests (call-count spies, call-order assertions, instrumented publish functions) — see `verification-report.md`.

### Remaining uncertainty

Whether Audit Repair 2 fully satisfies an independent auditor is, by definition, not something this record can establish — that is what Audit 3 exists to determine.

### Recommended next action

Commission an independent Codex re-audit of Audit Repair 2 (Audit 3). Do not begin Editorial Memory or Documentation Intelligence before that re-audit clears.
