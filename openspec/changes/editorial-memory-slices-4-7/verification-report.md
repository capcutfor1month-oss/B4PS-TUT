# Verification Report — Editorial Memory Slices 4–7 (Completion Batch + Repair Rounds 1–4)

## Process note (GOV-01)

This record — and `spec.md`/`audit-report.md` alongside it — was authored **retroactively**: Slices 4–7 were implemented, locally tested, and independently audited once (finding EM47-01–05, GOV-01, GOV-02) *before* any classification/spec/verification/audit record existed for this change at all. That absence was itself GOV-01's finding. This is a process deviation from normal order (spec-then-implement, or at minimum spec-alongside-implement) — the same category of deviation this repository's own Safe PPT Engine governance history has flagged for itself in earlier rounds (see `docs/DECISIONS.md`, Safe PPT Engine Audit Repair 3's governance-record correction). It is recorded here explicitly rather than presented as if this document had existed from the start.

## Founder summary

### Where things stand

Editorial Memory Slices 4 (existing-documentation ingestion), 5 (review queue), 6 (knowledge evolution proof), and 7 (invalidation + bounded purge) were implemented locally and sequentially, on top of merged Slices 1–3 (`main` at `98c55f3839c66221ae3b8389b15c627d74b4be03`). Four independent Codex audit rounds have found issues, all now fixed as further local repairs:

- **Round 1 (EM47-01–05, GOV-01, GOV-02):** idempotency, purge input validation, version-collision, purge-visibility, and typed-error findings, plus the two governance findings this document itself exists to close.
- **Round 2 (findings 1–5):** deeper correctness gaps Round 1's own fixes did not fully close — dedup identity stability across purge, version allocation against dangling `superseded_by` references, typed Evidence loading inside dedup specifically (not just `get_current`), cross-`knowledge_type` blending across the two bootstrap paths, and a full redesign of the KnowledgeState purge tombstone to the approved non-claim `{id, purged_at, purged_by, reason}` contract, stored in a new `tombstones/` directory (Round 1's own tombstone approach — redacting content in place while reusing `invalidated_*` fields — was superseded by this, not layered on top of it).
- **Round 3:** Round 2's own `tombstones/` directory was itself found to be an unapproved storage-architecture expansion; the tombstone now overwrites its target's existing array slot in place, inside the same per-item file, with no new directory - which also exposed and fixed a previously-latent bug where saving any other change to an item would have silently dropped its retained tombstones. Round 2's version allocation also didn't account for a retained tombstone's own identity, and purge's removal-then-tombstone sequence was two separate writes rather than one atomic one; both fixed.
- **Round 4 (this document's current state):** Round 3's tombstone *recognition* was too loose - any dict with a `purged_at` key was treated as a tombstone, with no shape or identity check, meaning a real state that somehow acquired that field would be silently hidden rather than flagged. Round 3's `_save_item` fix also merged tombstones back by prepending them, preserving their existence but not their original array position. Both fixed: strict shape/identity validation (raising typed `StorageCorruptionError` on any ambiguous case), and a positional merge that keeps every tombstone in its exact original slot.

**All findings from all four rounds are fixed, as local, uncommitted working-tree changes only** — per explicit instruction, not committed, pushed, or opened as a PR.

### Why this matters

All four rounds share the same underlying pattern: each fixed the *specific* defect found, without independently re-deriving whether the same assumption held everywhere else it was relied on. Round 2's findings 1 and 3 were both cases where `_find_matching_evidence_backed_state` had its own, separate logic Round 1's fixes never reached. Round 3 rejected Round 2's own storage-location choice outright, and implementing the required alternative surfaced a genuinely new defect (`_save_item` dropping tombstones) neither prior round had reason to find. Round 4 goes one level deeper still: it doesn't reject Round 3's mechanism (in-place tombstones are correct and stay), it finds that mechanism's own *recognition logic* (any `purged_at` key = a tombstone) and its *merge logic* (tombstones preserved but not positioned) were each too loose - the same class of "fixed existence, not correctness" gap Round 3 itself closed for `_save_item`, now recurring in that same method's own refinement.

### What has already happened

Slices 4–7 were implemented and locally tested (172 tests). Round 1 audit found EM47-01–05 + GOV-01/GOV-02; fixed (193 tests). Round 2 audit found findings 1–5 + GOV-01/GOV-02; fixed (210 tests). Round 3 audit found 3 further findings + GOV-01/GOV-02; fixed (221 tests). Round 4 audit found 2 further findings + GOV-01/GOV-02; fixed (231 tests). All work left as uncommitted working-tree changes for Codex to audit directly, per explicit instruction.

### What happens next

Codex performs a comprehensive re-audit of the complete Editorial Memory Slices 1–7 system, covering all four repair rounds. Not performed as part of this task.

### Founder action or decision

None required by this record itself (no PR exists to merge). Founder should treat all four rounds' fixes as implementer-verified, not independently verified, until the comprehensive re-audit happens.

### Recommended option and reason

Have Codex re-audit the local working-tree changes described here before they are committed, pushed, or merged, and before Editorial Memory is declared complete/closed or any Slice 8/Documentation Intelligence work begins.

## Technical evidence

### Change verified

- `editorial-memory/lib/memory.py`:
  - `_next_version(states)` (new helper, findings 2/EM47-03): `max` over every state's own `version` **and** every surviving state's `superseded_by` value, so a version number is never reused while anything still points at it, even across a full-removal purge.
  - `_find_matching_evidence_backed_state` (findings 1 & 3): omitted-relation comparison now keyed on `state.version == 1` (a stable, never-renumbered identity) instead of array-enumeration index; Evidence lookups inside the dedup loop now go through the typed `self.get_evidence()`, catching `EditorialMemoryError` and skipping (not crashing on) a tombstoned/corrupt candidate.
  - `record_maintainer_decision`/`ingest_existing_documentation` (finding 4): both now check the existing item's stored `knowledge_type` against the fixed type each path uses (`editorial`/`documentation`), raising new typed `KnowledgeTypeMismatchError` on mismatch, before any dedup check or mutation - mirroring the existing `feature_area`-mismatch check exactly.
- Round 3 changes (this update):
  - `editorial-memory/lib/store.py`: `tombstone_dir`/`_tombstone_path`/`save_knowledge_state_tombstone`/`load_knowledge_state_tombstone` (Round 2's dedicated directory) **removed entirely** (round-3 finding 2). New `TOMBSTONE_MARKER_KEY` constant, `load_knowledge_item_raw` (unfiltered read), `load_knowledge_item` now filters tombstone-shaped entries out of `states`, and new `tombstoned_versions(item_id)` (round-3 finding 1).
  - `editorial-memory/lib/memory.py`: `_next_version` now also folds in `store.tombstoned_versions(item_id)` (round-3 finding 1); `_save_item` now merges retained raw tombstones back into what it writes, fixing a previously-latent bug this round's redesign exposed (a filtered read-modify-write cycle would otherwise silently drop them).
  - `editorial-memory/lib/purge.py`: `purge_knowledge_state` now replaces the target's array slot in place with the tombstone (or removes it, `tombstone=False`) and performs exactly one `save_knowledge_item` call either way (round-3 findings 2 & 3 - the same redesign that fixes the storage location also makes the write atomic, since it's now genuinely one write instead of two).
  - `editorial-memory/tests/test_repair3_tombstone_contract.py`: 11 new adversarial regression tests.
  - 6 tests referencing Round 2's `load_knowledge_state_tombstone` accessor updated to read the raw record directly instead: `test_s7_14`, `test_s7_15`, `test_s7_18`, two `test_finding5_*` tests, one E2E test - a *different, smaller* set than GOV-01's own 7-test count above (that count includes three `test_em47_04_*` tests, none of which called this accessor and so needed no change here). The two sets overlap on 4 tests but are not identical; earlier drafts of this report incorrectly conflated them as "the same seven-test set," corrected here.
- Round 1/2 changes (unchanged by Round 3, retained here for a complete picture): `_find_matching_evidence_backed_state` (findings 1 & 3, dedup identity/typed Evidence loading); `record_maintainer_decision`/`ingest_existing_documentation` (finding 4, `knowledge_type` isolation); `errors.py` new `KnowledgeTypeMismatchError`; `__init__.py` export.
- Round 4 changes (this update):
  - `editorial-memory/lib/store.py`: new `is_tombstone_entry(entry, item_id)` - strict shape validation (`{id, purged_at, purged_by, reason}` exactly) plus `id` identity validation (`"<item_id>#<version>"`), raising `StorageCorruptionError` on any ambiguous `purged_at`-bearing dict. Replaces the old bare `TOMBSTONE_MARKER_KEY in entry` check everywhere entries are classified: `load_knowledge_item`'s filter, `tombstoned_versions`.
  - `editorial-memory/lib/memory.py`: `_save_item` no longer prepends retained tombstones - it walks the existing raw array position by position, carrying each tombstone through unchanged at its own index, replacing known real-state versions in place, and appending only genuinely new versions at the end.
  - `editorial-memory/lib/purge.py`: target-lookup now uses `is_tombstone_entry` (typed, strict) in place of the old bare marker check.
  - `editorial-memory/tests/test_repair4_tombstone_validation.py`: 10 new adversarial regression tests.

### Classification

**Standard** base tier, **Data-sensitive** profile applies (see `spec.md`). Independent Codex audit is confirmed as an explicit, exercised requirement - four rounds have now happened and all four found real defects.

### Builder review

Round 2's five findings were each reproduced against the pre-fix (i.e., Round-1-fixed) code before writing their fixes. Round 3's three findings were confirmed similarly: finding 2 (unapproved directory) was a code-review finding against the approved contract text directly, not a runtime reproduction; finding 1 (tombstone version reuse) and finding 3 (write atomicity) were each proven via the new adversarial tests themselves failing against the pre-fix code - see "Checks passed" below. The `_save_item` tombstone-dropping bug was caught by this round's own new tests failing unexpectedly during development (not anticipated by the audit finding itself), then root-caused and fixed before being included in this report as an additional, self-discovered fix.

### Environment

Python 3.14, `pytest` 9.1.1, isolated per-run virtualenv (`editorial-memory/.venv`, created and removed each verification pass - not committed).

### Commands executed

```bash
python -m py_compile editorial-memory/lib/*.py editorial-memory/tests/*.py
python -m pytest editorial-memory/tests/ -q
python scripts/check_pipeline.py   # run from repository root
git diff --check
```

### Checks passed

- `python -m pytest editorial-memory/tests/` → **231 passed** (221 prior Slice 1–7 + Round 1/2/3 tests + 10 new Round 4 adversarial tests, all passing; zero skipped or xfailed).
- Regression proof (Round 2): finding 1's fix (stable-identity dedup) and finding 2's fix (`superseded_by`-aware version allocation) were each individually reverted in isolation and their corresponding new tests re-run - both reproduced clean failures (finding 1: 2 tests failed with a wrong version number returned; finding 2: 3 tests failed with a reused, dangling version number) - confirming these are genuine regressions the new tests actually exercise, not tautological assertions. Fixes were then restored and the full suite re-confirmed green.
- Regression proof (Round 3): before the `_save_item` fix was applied, three new Round 3 tests failed naturally with `TypeError: argument of type 'NoneType' is not a container` / an assertion mismatch (`assert 1 == 3`), directly demonstrating the tombstone-dropping bug the redesign had introduced - not a synthetic revert-and-check, an organic failure caught mid-implementation. The write-atomicity fault-injection tests (`test_tombstone_write_failure_preserves_original_state` and its two siblings) each monkeypatch a specific write-path failure point (`_atomic_write_json` itself, and `Path.replace` specifically) and confirm the original state's `content`/`version` survive unchanged after the induced failure.
- Regression proof (Round 4): the slot/order-preservation fix was individually reverted in isolation (back to Round 3's prepend-based merge) and its two dedicated slot-preservation tests re-run - both reproduced clean `KeyError: 'version'` failures (the reverted merge no longer keeps real states at their expected positions), confirming a genuine regression before the fix was restored and the full suite re-confirmed green.
- `python -m py_compile` on all `lib/` and `tests/` files → clean.
- `python scripts/check_pipeline.py` → `Bridge4PS target-repository pipeline-adoption checks passed.`
- `git diff --check` → clean, no whitespace errors.

### Checks failed

None outstanding in this repository's own local test suite as of this report.

### Pipeline / CI evidence

**Local only**: no PR exists for this change, so there is no GitHub Actions run for it. `check_pipeline.py` and `git diff --check` are the only CI-equivalent evidence available.

### Founder-preview requirement

**Pending, not N/A (GOV-01 correction).** This batch's earlier version of this record marked founder-preview "Not applicable — no user-facing surface exists," reasoning by analogy to Slices 1–3's pure retrieval/storage API. That reasoning does not transfer cleanly to Slice 7: `purge_evidence`/`purge_knowledge_state` are a genuinely new *operational* capability - not an end-user UI, but a real, irreversible, destructive action a maintainer would eventually invoke against real Bridge4PS Editorial Memory data. No maintainer has exercised either purge function against real data outside this test suite's synthetic fixtures. Marking that "N/A" would overstate readiness the same way this repository's Safe PPT Engine governance history has consistently guarded against for its own founder-preview gate - recording it "truthfully as still pending, not fabricated as complete" (`docs/DECISIONS.md`, PROJ-009) and keeping it "explicitly recorded as pending" across every subsequent repair round (PROJ-011), never quietly marked N/A once a real operational surface existed. Recorded honestly as **Pending** here for the same reason.

### Profile-specific gates (Data-sensitive)

| Required evidence | Status | Detail |
|---|---|---|
| Migration test | N/A | No existing schema/data is migrated. |
| Data-preservation check | Complete | Finding 2's fix is proven by tests that purge a superseded state, confirm the dangling `superseded_by` reference persists, and confirm a subsequent `propose_state` never reuses that version - across both a single run and a fresh reload. Finding 5's fix is proven by asserting a purged state is fully absent from `states` and from every normal query path (`get_current`, `get_history_by_key`, the review queue, `get_invalidated_by_key`), while its tombstone (when written) remains readable directly from the item's own raw record (`JSONStore.load_knowledge_item_raw`, validated via `is_tombstone_entry` - round-4 finding 1) - never blended back into the filtered view ordinary callers see. |
| Tenancy-isolation check | N/A | Single-process local-file library, unchanged. |
| Rollback plan | **No rollback exists for a completed purge, by design (GOV-01 correction).** An earlier version of this record marked this gate "Complete," describing only pre-purge *validation* (non-blank `purged_by`, a validated literal `item_id`) - that is a prevention guarantee against an *invalid* purge call, not a rollback of a *completed, valid* one. There is no rollback of a completed purge: `tombstone=False` leaves no trace at all, and `tombstone=True` preserves only `{id, purged_at, purged_by, reason}` - the original content is gone in both modes, permanently, which is purge's entire intended purpose (design §15.3). The only recovery path for a regretted purge is a backup of the repository taken *outside* Editorial Memory's own storage before the purge ran; this system provides no such backup mechanism itself. This is accurately described as irreversible-by-design, not as a gap to be closed. Round 3 additionally made the *write itself* atomic (finding 3) - a purge either fully completes or the target is fully untouched, no partial state - which is a correctness property of *how* an authorized purge executes, not a rollback mechanism for a purge that already succeeded; the two are not in tension. |

### Files changed

Round 1: `editorial-memory/lib/{memory,store,purge,errors,__init__}.py`, `editorial-memory/tests/test_em47_audit_repair.py` (new), `editorial-memory/tests/test_slice7_invalidation_purge.py` (one test updated).
Round 2: `editorial-memory/lib/{memory,store,purge,errors,__init__}.py` (further changes), `editorial-memory/tests/test_repair2_purge_and_dedup.py` (new, 17 tests), `editorial-memory/tests/test_slice7_invalidation_purge.py` (3 more tests updated), `editorial-memory/tests/test_em47_audit_repair.py` (3 tests updated/renamed), `editorial-memory/tests/test_e2e_slices_4_7.py` (1 test updated).
Round 3: `editorial-memory/lib/{memory,store,purge}.py` (further changes); `editorial-memory/tests/test_repair3_tombstone_contract.py` (new, 11 tests); `test_slice7_invalidation_purge.py`, `test_repair2_purge_and_dedup.py`, `test_e2e_slices_4_7.py` (6 tombstone-accessor references updated - a distinct, smaller set than Round 2's own 7-test count, see "Test-quality findings" in `audit-report.md`).
Round 4 (this update): `editorial-memory/lib/{memory,store,purge}.py` (further changes - no `errors.py`/`__init__.py` change, no new error type needed); `editorial-memory/tests/test_repair4_tombstone_validation.py` (new, 10 tests). No existing tests required updating this round.
Governance (all rounds): `openspec/changes/editorial-memory-slices-4-7/{spec.md, verification-report.md, audit-report.md}`; `docs/CURRENT.md`, `docs/DECISIONS.md`.
All local/uncommitted.

### Remaining uncertainty

- Comprehensive independent Codex re-audit of the complete Slices 1–7 system, covering all four repair rounds, has not occurred - the required next action, out of scope for this task per explicit instruction to stop after local repair.
- Round 2's finding 3 fix (still in effect, unchanged since) chooses to *skip* (not raise) a dedup candidate whose Evidence is tombstoned/corrupt, rather than surfacing a typed error to the caller. This was a deliberate implementer judgment call - a single damaged historical Evidence record for an unrelated past submission should not block an entirely new, unrelated ingestion call for the same item - but it was not independently reviewed, and a founder/Codex reviewer may reasonably prefer the opposite (raise, forcing the caller to address the corruption before proceeding). Flagged, not silently decided; see the "contract ambiguity" note in this round's final report.
- No consumer exists yet (Documentation Intelligence has not started), so end-to-end usage beyond the test suite remains unproven - unchanged from Slice 1–3.
- Concurrency behavior under simultaneous writers remains untested - unchanged limitation from Slice 1.

### Recommended next action

Commission a comprehensive independent Codex audit of the complete Editorial Memory Slices 1–7 system, covering all four repair rounds. Do not commit, push, or merge these changes as part of this task.
