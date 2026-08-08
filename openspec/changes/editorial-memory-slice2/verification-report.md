# Verification Report — Editorial Memory Slice 2 (Maintainer-Decision Bootstrap, Repair 1)

## Founder summary

### Where things stand

Editorial Memory Slice 2 — the maintainer-decision bootstrap path — was implemented and locally tested, then independently audited by Codex (Audit 1), which returned **FAIL**: a `feature_area` mismatch on an existing `KnowledgeItem` could be silently accepted (S2-01), and idempotency detection ignored `relation_to_previous`, wrongly treating a decision resubmitted with an explicitly different relation as an exact repeat (S2-02). **Both are now fixed, recorded in this update, as local, uncommitted working-tree changes only** — per explicit instruction, not committed, pushed, or opened as a PR. `main` (`19946ebc2d80e0d494e451e03750fa1b6f77dddb`) still reflects only Slice 1 through Repair 2 (Audit 3 PASS, integrated via PR #10); Slice 2 does not exist there yet.

### Why this matters

Slice 2 does not touch Slice 1's core guarantee at all — it adds one new caller of the same unmodified `propose_state`/`approve_state` methods. Audit 1's findings are exactly the kind of gap worth independently checking for a bootstrap path like this: S2-01 is the feature_area analogue of Slice 1's own EM-02 (silent identity drift instead of an explicit rejection), and S2-02 is a correctness gap in the idempotency contract itself — accepting a maintainer's explicit `CONTRADICTS` relation as if it were a no-op repeat would silently discard the one signal (a recorded disagreement with prior knowledge) this bootstrap exists to preserve.

### What has already happened

Slice 2 was implemented and locally tested. Codex performed Audit 1 and found S2-01 and S2-02. Both have now been fixed and tested locally, left as uncommitted working-tree changes for Codex to audit directly, per explicit instruction.

### What happens next

Codex reviews these local working-tree changes (Audit 2). Not performed as part of this task — this task explicitly stops after local repair, without committing, pushing, or opening a PR.

### Founder action or decision

None required by this record itself (no PR exists to merge). Founder should treat this round's fixes as implementer-verified, not independently verified, until Audit 2 happens.

### Recommended option and reason

Have Codex audit the local working-tree changes described here (Audit 2) before they are committed, pushed, or merged, and before Slice 3 begins.

## Technical evidence

### Change verified

`EditorialMemory.record_maintainer_decision()` and its private helper `_find_matching_maintainer_state()` in `editorial-memory/lib/memory.py`, as originally implemented, and — as local, uncommitted changes only — the fixes for Audit 1's findings:

- **S2-01**: before any duplicate-detection or mutation, the existing `KnowledgeItem`'s stored `feature_area` (if any) is now compared against the requested one. A mismatch raises typed `FeatureAreaMismatchError` (new, in `errors.py`) immediately — no Evidence is recorded, no `KnowledgeState` is created, and the mismatched request is never treated as an idempotent repeat of an existing decision.
- **S2-02**: `relation_to_previous` (the effective value, after the existing default-computation logic — `NEW` for a brand-new item, `REFINES` otherwise, unless the caller passes one explicitly) is now part of the exact-repeat identity comparison in `_find_matching_maintainer_state()`. The same content/rationale/Evidence fields resubmitted with an explicitly different relation (e.g. `NEW` then `CONTRADICTS`) no longer match as a duplicate and instead create a new `KnowledgeState` through the ordinary `propose_state`/`approve_state` lifecycle, correctly superseding the prior current state.

17 pre-existing Slice 2 tests plus 9 new adversarial tests (`editorial-memory/tests/test_editorial_memory.py`; 85 total in the suite, all 59 Slice 1/Repair 1/Repair 2 tests passing unmodified). Two pre-existing Slice 2 tests were updated with explicit justification (not weakened — see "Test-quality findings" in `audit-report.md`): `test_s2_07` now asserts the mismatch case raises `FeatureAreaMismatchError` instead of asserting the old silent-keep behavior; `test_s2_11`/`test_s2_12` now pass an explicit, matching `relation_to_previous` on repeated calls, since the pre-existing default-relation logic legitimately differs between "first state on a brand-new item" and "another decision on an existing item" — a real interaction, not something either fix introduced. No other file besides `memory.py`, `errors.py`, and `__init__.py` (the new error type's export) was modified — Slice 1's `store.py`, `models.py`, and all governance docs for Slice 1/Repair 1/Repair 2 are untouched.

### Classification

**Standard** base tier, **Data-sensitive** profile applies (see `spec.md`). Independent Codex audit is confirmed as an explicit, exercised requirement — Audit 1 already happened and found real defects.

### Builder review

Manual reproduction of each Audit 1 finding against the pre-repair code before writing a fix: confirmed a second call under the same key with a different `feature_area` was silently accepted, either creating a second state or (for otherwise-identical input) returning the original state as if the mismatched request were valid (S2-01); confirmed a decision resubmitted with the same content/rationale/Evidence fields but an explicitly different `relation_to_previous` (e.g. `NEW` then `CONTRADICTS`) was returned as the same, unchanged state rather than creating a new one (S2-02). Each new test was then confirmed to fail against the pre-fix logic specifically (not merely against missing symbols) before being accepted as a genuine regression — see "Checks passed" below.

Unchanged from the original implementation: confirmed the bootstrap performs exactly `propose_state()` then `approve_state()` via a call-count spy (`test_s2_10_bootstrap_reuses_existing_approval_logic`), and confirmed a state produced this way is still subject to ordinary lifecycle rules — re-approving it through the plain API still raises `InvalidLifecycleTransitionError` (`test_s2_10b_...`), proving no separate/parallel approval path exists.

### Environment

Python 3.14, `pytest` 9.1.1, same isolated virtualenv used for the Repair 1/Repair 2 rounds.

### Commands executed

```bash
python -m py_compile editorial-memory/lib/*.py editorial-memory/tests/*.py
python -m pytest editorial-memory/tests/ -q
python scripts/check_pipeline.py   # run from repository root
git diff --check
```

### Checks passed

- `python -m pytest editorial-memory/tests/` → **85 passed** (59 Slice 1/Repair 1/Repair 2, unmodified, + 17 original Slice 2 tests (2 updated in place with explicit justification) + 9 new S2-01/S2-02 adversarial tests).
- Regression proof: reverted `record_maintainer_decision`/`_find_matching_maintainer_state` to their pre-repair form (new `FeatureAreaMismatchError` type still available but unused) and re-ran the 9 new tests — 7 failed as expected (the S2-01 mismatch tests, the S2-02 differing-relation test, the three-call REFINES-after-CONTRADICTS test, and the history/supersession test), while 2 passed coincidentally, since they exercise still-correct default-relation behavior that neither fix touches; confirms the 7 exercise real logic, not just new symbols existing, and the other 2 are honestly reported as unaffected-by-this-round rather than dropped.
- `python -m py_compile` on all `lib/` and `tests/` files → clean.
- `python scripts/check_pipeline.py` → `Bridge4PS target-repository pipeline-adoption checks passed.`
- `git diff --check` → clean, no whitespace errors.
- `git diff --stat -- baseline/` → empty (Safe PPT Engine untouched).
- Manual disk inspection confirmed S2-01's rejection path creates zero new Evidence/KnowledgeItem/KnowledgeState records (`test_s2_19_mismatch_rejection_creates_no_new_records_at_all`).

### Checks failed

None outstanding in this repository's own local test suite as of this report. (Historical: Audit 1's **FAIL** is a result this report exists to record truthfully — see `audit-report.md`.)

### Pipeline / CI evidence

**Local only**: no PR exists for this change, so there is no GitHub Actions run for it. `check_pipeline.py` and `git diff --check` are the only CI-equivalent evidence available.

### Founder-preview requirement

Not applicable — no user-facing surface exists (same as Slice 1).

### Profile-specific gates (Data-sensitive)

| Required evidence | Status | Detail |
|---|---|---|
| Migration test | N/A | No existing schema/data is migrated. |
| Data-preservation check | Complete | Idempotency tests prove exact-repeat input (including matching `relation_to_previous`, per the S2-02 fix) never creates duplicate Evidence/KnowledgeItem/KnowledgeState; materially-different-decision tests (including differing-relation-only cases) prove prior current state is correctly superseded, not overwritten or lost. S2-01's fix specifically strengthens this: a `feature_area` mismatch is now actively rejected before any write, rather than silently accepted. |
| Tenancy-isolation check | N/A | Single-process local-file library, unchanged. |
| Rollback plan | Complete | Same atomic per-file writes as Slice 1; a rejected `record_maintainer_decision` call (invalid `feature_area`, or now a `feature_area` mismatch against an existing item) creates zero records, verified directly. |

### Files changed

`editorial-memory/lib/memory.py`, `editorial-memory/lib/errors.py` (new `FeatureAreaMismatchError`), `editorial-memory/lib/__init__.py` (export), `editorial-memory/tests/test_editorial_memory.py` (all modified, local/uncommitted); `openspec/changes/editorial-memory-slice2/{spec.md, verification-report.md, audit-report.md}` (modified/new, local/uncommitted); `docs/CURRENT.md`, `docs/DECISIONS.md` (modified, local/uncommitted).

### Remaining uncertainty

- Independent Codex re-audit of this round's fixes (Audit 2) has not occurred — the required next action, out of scope for this task per explicit instruction to stop after local repair.
- The default `relation_to_previous` (`refines` for any decision on an existing item) remains an implementer judgment call, unchanged by this repair and not independently reviewed.
- No consumer exists yet (Documentation Intelligence has not started), so end-to-end usage beyond the test suite remains unproven — unchanged from Slice 1.
- Concurrency behavior under simultaneous writers remains untested — unchanged limitation from Slice 1.

### Recommended next action

Commission an independent Codex re-audit of these local working-tree changes (Audit 2). Do not commit, push, or merge them as part of this task. Do not begin Editorial Memory Slice 3 until Audit 2 clears.
