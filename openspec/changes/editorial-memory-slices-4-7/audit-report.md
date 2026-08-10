# Independent Audit Report — Editorial Memory Slices 4–7

This file records the history of independent Codex audits of Editorial Memory Slices 4–7, as required by `docs/PIPELINE.md`. **This document is a truthful record of past audit results, not an audit performed by Claude.** Claude cannot self-certify closure of an independent audit finding — only Codex's own audit can.

## Founder summary

### Where things stand

Editorial Memory Slices 4–7 (the completion batch) have been independently audited four times by Codex. Round 1 found 5 code findings (EM47-01 through EM47-05) and 2 governance findings (GOV-01, GOV-02); all 7 were fixed. Round 2, auditing that repaired tree, found 5 further code findings (numbered 1–5, deeper gaps Round 1's own fixes did not fully close) plus GOV-01/GOV-02 again; all fixed. Round 3, auditing that repaired tree, found the Round 2 tombstone-storage approach itself to be an unapproved storage-architecture expansion, plus 2 further code findings (version allocation, write atomicity) and GOV-01/GOV-02 a third time; all fixed. Round 4, auditing that repaired tree, found tombstone recognition was not strictly validated and tombstone array position/order was not preserved across later saves, plus GOV-01/GOV-02 a fourth time; all fixed. **All findings from all four rounds are fixed locally only** — not committed, pushed, or opened as a PR, per explicit instruction, so Codex can audit the repaired tree directly.

### Why this matters

Round 1's EM47-04/EM47-05 were direct instances of the failure mode this entire system exists to prevent — content that should no longer be trusted remaining silently retrievable as truth, and a storage-layer failure surfacing as an untyped crash instead of a typed, catchable error. Round 2 found that Round 1's own fixes for closely related mechanisms (dedup identity, version allocation, Evidence loading inside dedup specifically) had each fixed one call site while leaving a structurally similar one unfixed. Round 3 rejected Round 2's *chosen mechanism* (a new tombstone directory) outright as exceeding the approved contract, and implementing the required alternative surfaced a genuinely new defect (`_save_item` silently dropping tombstones on any subsequent save). Round 4 finds that Round 3's own in-place-tombstone mechanism, while structurally correct, still recognized a tombstone too loosely (any `purged_at`-bearing dict, no shape/identity check) - which is exactly the same "silently hide current truth" failure mode Round 1's EM47-04 originally represented, now recurring one layer deeper, in the *recognition* logic rather than the storage location. Round 4's second finding (position/order) is the same pattern again: Round 3's `_save_item` fix correctly preserved tombstones' *existence*, but not their *position*, because "not lost" and "not moved" are different guarantees that happened to be conflated.

### What has already happened

Slices 4–7 were implemented and locally tested (172 tests; see `docs/DECISIONS.md` PROJ-023). Round 1 audit found EM47-01–05 + GOV-01/GOV-02; fixed (193 tests; PROJ-024). Round 2 audit found findings 1–5 + GOV-01/GOV-02 again; fixed (210 tests; PROJ-025). Round 3 audit found 3 further findings + GOV-01/GOV-02 a third time; fixed (221 tests; PROJ-026). Round 4 audit found 2 further findings + GOV-01/GOV-02 a fourth time; fixed (231 tests, this update). All left as uncommitted working-tree changes for Codex to re-audit directly.

### What happens next

Codex performs a comprehensive re-audit of the complete Editorial Memory Slices 1–7 system, covering all four repair rounds. Not performed as part of this task.

### Founder action or decision

None required by this record itself (no PR exists to merge). Founder should treat all four rounds' fixes as implementer-verified, not independently verified, until the comprehensive re-audit happens.

### Recommended option and reason

Have Codex re-audit the local working-tree changes described here before they are committed, pushed, or merged, and before Editorial Memory is declared complete/closed.

## Technical evidence

### Verdict

| Round | Scope audited | Verdict |
|---|---|---|
| Round 1 | Local, uncommitted Slices 4–7 diff as originally implemented (`editorial-memory/lib/{memory,store,review,purge}.py`, five new test files) | **FAIL/FINDINGS** — 5 code findings (EM47-01–05), 2 governance findings (GOV-01, GOV-02) |
| Round 2 | Local, uncommitted Round 1 repair diff | **FAIL/FINDINGS** — 5 code findings (1–5), 2 governance findings (GOV-01, GOV-02) |
| Round 3 | Local, uncommitted Round 2 repair diff | **FAIL/FINDINGS** — 3 code findings (tombstone version reuse, unapproved storage expansion, write atomicity), 2 governance findings (GOV-01, GOV-02) |
| Round 4 | Local, uncommitted Round 3 repair diff | **FAIL/FINDINGS** — 2 code findings (tombstone validation strictness, array slot/order preservation), 2 governance findings (GOV-01, GOV-02) |
| Comprehensive re-audit | Local, uncommitted Round 4 repair diff (this update) | **NOT YET PERFORMED** |

### Specification reviewed

`openspec/changes/editorial-memory-slices-4-7/spec.md` (this change's own classification record, added as part of Round 1's GOV-01, extended in Round 2's, Round 3's, and Round 4's GOV-01).

### Findings and resolutions — Round 1

| Finding | Summary | Resolution |
|---|---|---|
| EM47-01 | Omitted-relation exact-repeat detection (Slice 2 + 4) recomputed its default relation at call time, breaking idempotency for a repeat submitted after the item already had a state. | `_find_matching_evidence_backed_state` now compares each candidate against the default relation that would have applied when *that* state was created, not a single default computed once per call. **Superseded by Round 2 finding 1** (see below) - the fix's own identity signal (array index) was itself unstable. |
| EM47-02 | `purge_knowledge_state`'s `item_id` reached a glob-based (`Path.glob()`) lookup unvalidated. | New `store.validate_knowledge_item_id()` rejects any non-literal token (including glob metacharacters) before purge touches disk. Confirmed still correct by Round 2. |
| EM47-03 | `propose_state`'s version (`len(states)+1`) could collide with a remaining version after a Slice 7 full-removal purge shrank the states list. | Version is now `max(existing versions, default=0) + 1`. **Superseded by Round 2 finding 2** (see below) - didn't account for dangling `superseded_by` references. |
| EM47-04 | A tombstoned `KnowledgeState` that was `current` remained retrievable as current truth; `purged_by` was not validated as non-blank; purge attribution/reason were not persisted. | Tombstone mode forced `status=invalidated`, reusing `invalidated_by`/`invalidated_at`/`invalidation_reason`. **Superseded by Round 2 finding 5** (see below) - didn't match the approved tombstone contract shape and left a state-shaped-but-not-a-state entry in `states`. |
| EM47-05 | A tombstoned (or otherwise structurally incomplete) Evidence record raised a raw `KeyError` from `Evidence.from_dict`, not a typed error. | `EditorialMemory.get_evidence()` now wraps `KeyError`/`TypeError`/`ValueError` into new typed `CorruptEvidenceRecordError`, chained via `__cause__`. **Extended by Round 2 finding 3** (see below) - the dedup helper had its own, separate call site this fix didn't reach. |
| GOV-01 | No classification/spec/verification/audit records existed for Slices 4–7. | This directory added. |
| GOV-02 | `docs/CURRENT.md` claimed the KnowledgeState-tombstone attribution limitation was "accepted," without any recorded approving authority. | Claim corrected. |

### Findings and resolutions — Round 2

| Finding | Summary | Resolution |
|---|---|---|
| 1 | EM47-01's fix used `enumerate(item.states)` array index for the omitted-relation default, which shifts once an earlier state is fully removed by purge - breaking dedup for a surviving later state. | Compared using `state.version == 1` instead - stable, never renumbered for a surviving entry, immune to purges of *other* states. |
| 2 | EM47-03's fix only considered currently-present states' own versions, not a surviving state's `superseded_by` reference to a version later fully removed by purge - risking silent reuse of that dangling number. | New `_next_version()` folds every surviving `superseded_by` value into the same `max()` computation. |
| 3 | `_find_matching_evidence_backed_state`'s own Evidence lookup called `Evidence.from_dict` directly, bypassing EM47-05's `get_evidence()` fix - a tombstoned/corrupt candidate's Evidence during dedup still raised a raw `KeyError`. | Dedup loop now calls `self.get_evidence()`, catching `EditorialMemoryError` and skipping the candidate rather than crashing. |
| 4 | Neither `record_maintainer_decision` nor `ingest_existing_documentation` checked the existing item's `knowledge_type` before reusing it - the two bootstrap paths could silently blend `editorial`/`documentation`/`product` knowledge under one shared key. | Both paths now check `knowledge_type` before any dedup/mutation, raising new typed `KnowledgeTypeMismatchError` on mismatch - mirrors the existing `feature_area` check exactly. |
| 5 | EM47-04's tombstone (redact in place, force `status=invalidated`, reuse `invalidated_*` fields) didn't match the approved `{id, purged_at, purged_by, reason}` non-claim contract, and left a state-shaped-but-not-a-state entry inside `states`. | `purge_knowledge_state` now always fully removes the target from `states`; tombstone mode (default) writes the canonical `Tombstone` shape to a new dedicated location, never inside `states`. **Superseded by Round 3's "unapproved storage expansion" finding** (see below) - the new dedicated location was itself the problem. |
| GOV-01 | This directory's records had not been updated to reflect Round 1's own findings' resolutions once Round 2 began, and lacked the retrospective-authorship/process-deviation disclosure, an honest rollback statement (previously described purge-input validation as if it were purge rollback), and correctly Pending (not N/A) founder-preview status for the new purge capability. | This document, `spec.md`, and `verification-report.md` updated throughout. |
| GOV-02 | `docs/CURRENT.md`'s top-level active-Editorial-Memory-change pointer still named Slice 1, not the Slices 4–7 completion batch actually in progress. | Corrected. |

### Findings and resolutions — Round 3

| Finding | Summary | Resolution |
|---|---|---|
| Tombstone version reuse | `_next_version()` (Round 2) accounted for `superseded_by` references but not for a version whose tombstone still exists after the state itself was removed from `states` - that version could be silently reassigned to a new, unrelated state. | `_next_version()` also folds in `JSONStore.tombstoned_versions(item_id)`, read from the raw persisted record. |
| Unapproved storage-architecture expansion | Round 2's `tombstones/` top-level directory was itself an expansion the approved contract never authorized - it defines no location for a KnowledgeState tombstone other than the per-item file a real state already lives in. | `tombstones/` directory removed entirely. A tombstone now overwrites its target's existing array slot in place, inside the same `knowledge/<feature_area>/<item_id>.json` file; `JSONStore.load_knowledge_item` filters tombstone-shaped entries (a `purged_at` key, never present on a real `KnowledgeState`) back out of `states` for every ordinary reader. Fixing this exposed a second, previously-latent defect: `EditorialMemory._save_item` wrote `item.to_dict()` verbatim, silently dropping any tombstone on disk the next time anything else about that item was saved (since `item.states` is always the filtered view) - `_save_item` now merges retained raw tombstones back into what it writes. |
| Purge write not atomic | Round 2's `purge_knowledge_state` performed state removal and tombstone publication as two separate `save_*` calls - a failure of the second after the first succeeded would leave a state permanently gone with no tombstone. | Moot as a side effect of the storage-location fix above: the target's array slot is now replaced/removed and the entire item record written in one `save_knowledge_item` call, making both purge modes atomic by construction via the existing temp-file-then-rename discipline. |
| GOV-01 (again) | `spec.md`/`verification-report.md`/`audit-report.md` said "five pre-existing tests updated" while enumerating seven test names. | Corrected to "seven" in both files; Round 2's process-deviation/founder-preview/rollback corrections reconfirmed accurate and untouched. |
| GOV-02 (again) | `docs/CURRENT.md` wording could read as if Slices 4–7 had not yet been audited at all, rather than audited three times with re-audit/integration still pending. | Corrected. |

### Findings and resolutions — Round 4

| Finding | Summary | Resolution |
|---|---|---|
| Tombstone validation not strict | Round 3's tombstone recognition treated any dict containing `purged_at` as a tombstone, with no shape or identity check - a real `KnowledgeState` with a stray `purged_at` field (corruption/bug/tampering) would have been silently filtered out of `states`, hiding current/history truth without any error. | New `store.is_tombstone_entry(entry, item_id)` requires the entry's keys to match `{id, purged_at, purged_by, reason}` *exactly* and `id` to parse as `"<item_id>#<version>"`. Any `purged_at`-bearing dict that doesn't match raises typed `StorageCorruptionError` - never silently resolved either way, never a raw `KeyError`/`IndexError`. |
| Tombstone slot/order not preserved | Round 3's `_save_item` fix merged retained tombstones back by prepending them ahead of real states - preserving existence but not original array position, and not preserving real states' relative order either. | `_save_item` now walks the existing raw array position by position: tombstones carried through unchanged at their own index; known real-state versions replaced in place; only genuinely new versions appended at the end. |
| GOV-01 (again) | Two stale spots in Round 3's own governance wording: "both rounds" (never updated when Round 3 itself was added), and a reference to the just-removed `load_knowledge_state_tombstone` accessor in a Data-preservation gate row. A separate arithmetic error was also found: Round 3's report conflated Round 2's 7-test tombstone-contract set with Round 3's own, smaller 6-test accessor-removal set as if they were identical. | All corrected; the two test sets are now described separately with their actual, distinct membership and counts. |
| GOV-02 (again) | `docs/CURRENT.md` still described only 3 completed audit/repair rounds. | Updated to state 4 rounds completed, with comprehensive re-audit (covering all four) and integration as the remaining pending steps. |

### Test-quality findings

Round 1: none against the original test suite's quality - the 5 findings were implementation gaps, not test weaknesses. One test (`test_s7_09`) had, by coincidence, encoded EM47-05's bug as expected behavior; corrected, not weakened.

Round 2: seven pre-existing tests (`test_s7_14`, `test_s7_15`, `test_s7_18`, `test_em47_04_purging_current_state_removes_it_from_current_retrieval`, `test_em47_04_attribution_and_reason_preserved_via_canonical_tombstone` (renamed), `test_em47_04_purge_of_already_invalidated_state_is_still_authorization_checked`, `test_adversarial_purge_tombstone_is_never_silent`) asserted Round 1's now-superseded tombstone behavior; each updated with explicit justification tied to finding 5, not weakened - the behavior they asserted no longer occurs once finding 5 is fixed, so the old assertions could not remain true regardless.

Round 3: 6 tests (`test_s7_14`, `test_s7_15`, `test_s7_18`, two `test_finding5_*` tests, one E2E test) referenced Round 2's now-removed `load_knowledge_state_tombstone` accessor; updated to read the raw persisted record directly instead - a mechanical update tied to the storage-location change, not a behavioral weakening. This is a distinct, smaller set than the 7 tests Round 2's own GOV-01 fix touched (that count also included three `test_em47_04_*` tests, unaffected here).

Round 4: none against the test suite's quality - both findings were implementation gaps in the Round 3 mechanism itself, not test weaknesses.

### Regression proof

Round 1: each of the 21 new tests in `test_em47_audit_repair.py` targets exactly one finding. Round 2: each of the 17 new tests in `test_repair2_purge_and_dedup.py` targets exactly one finding; findings 1 and 2's fixes were each individually reverted in isolation and their tests re-run, reproducing clean failures (2 and 3 tests respectively) before the fixes were restored - confirmed as genuine regressions, not tautological assertions (see `verification-report.md` → "Checks passed" for the exact reproduction). Round 3: each of the 11 new tests in `test_repair3_tombstone_contract.py` targets exactly one finding; the `_save_item` tombstone-dropping defect was caught organically - three new tests failed against the code as first written (before that specific fix), not via a deliberate revert - and the two write-atomicity fault-injection tests each induce a distinct failure point (`_atomic_write_json` itself, and `Path.replace` specifically) to prove the original state survives either way. Round 4: each of the 10 new tests in `test_repair4_tombstone_validation.py` targets exactly one finding; the slot/order-preservation fix was individually reverted in isolation (back to Round 3's prepend approach) and its two dedicated tests re-run, reproducing clean `KeyError` failures before the fix was restored - confirmed as a genuine regression.

## Explicit non-goals for all four repair rounds

No architecture redesign; no changes to Slice 5/6 behavior, EM-01–EM-04, Slice 2 bootstrap, or Slice 3 retrieval (all confirmed unaffected by the full suite passing unmodified); no Browser Verification; no Documentation Intelligence; no Slice 8; no new top-level storage directory (Round 3 specifically removes the one Round 2 added; Round 4 confirms it stays removed).
