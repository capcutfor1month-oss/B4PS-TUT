# Audit Report — Documentation Intelligence, Slice 3 (Controlled PPT Mutation Handoff)

## Chronology

| Step | Description |
|---|---|
| 1 | `spec.md` written **before** implementation, per this repository's established convention. |
| 2 | Build 1 implemented: `mutate.py`, bridge extended (`set_shape_text`, `MutationError`, `ValidationError`), `tests/test_mutate.py`. |
| 3 | Deterministic validation initially passed (focused Slice 3 tests, full DI suite, Safe PPT Engine suite, Editorial Memory suite, combined suites both orders, `check_pipeline.py`, `py_compile`, `git diff --check`, real-deck-copy regression, byte hashes unchanged). |
| 4 | Independent Codex Audit 1 — **FAIL**. |
| 5 | Findings: DI-S3-01, DI-S3-02, GOV-DI3-01 (below). |
| 6 | Repair Round 1 performed locally — fixes DI-S3-01 and DI-S3-02; adds GOV-DI3-01's governance records (this file and `verification-report.md`). |
| 7 | Independent Codex Re-audit 1 — **FAIL/PARTIAL**: DI-S3-01 and GOV-DI3-01 confirmed closed; DI-S3-02 confirmed **PARTIAL** — an output-ownership race Repair Round 1 did not cover. |
| 8 | Repair Round 2 performed locally (this record) — closes the DI-S3-02 ownership race. |
| 9 | Closure re-audit pending — not yet independently re-audited. |

## Audit 1 — FAIL

1. **DI-S3-01 — structurally incomplete post-mutation verification.** The original verification used a single `zip(before_shapes, after_shapes)` per slide, which silently truncates to the shorter sequence — a trailing shape or an entire trailing slide disappearing would never surface as a discrepancy. Slide/shape counts and stable shape correspondence/identity were never explicitly verified before content was compared, and the target shape's resulting text was never explicitly checked against `replacement_text` itself (only implicitly trusted via whatever `inspect_deck()` happened to report at that position).
2. **DI-S3-02 — failed wrapper validation leaves published output behind.** `set_shape_text()` already publishes its output (per its own existing atomic-publish contract) before Slice 3's own additional verification ever runs. If that additional verification then failed, the real, published-but-unverified `.pptx` was left on disk with no cleanup.
3. **GOV-DI3-01 — canonical evidence records missing.** Only `spec.md` existed for Slice 3. No `verification-report.md`, no `audit-report.md`.

## Repair — fixes applied (this record)

1. **DI-S3-01 — fixed.** New `_verify_mutation()` in `mutate.py` explicitly checks, in this order, over the full `before_structure`/`after_structure` returned by `inspect_deck()`:
   - total slide count equality (raises `ValidationError` immediately on mismatch — a disappeared trailing slide can no longer escape detection);
   - per-slide shape count equality (a disappeared trailing shape can no longer escape detection);
   - per-slide shape-id sequence equality — a stable-identity/correspondence check, performed *before* any shape's content is compared;
   - the intended target shape's text compared exactly against `replacement_text` (explicit, not implicit);
   - every non-target shape's text compared exactly against its own pre-mutation value.

   No `zip()` over possibly-unequal-length sequences is used anywhere in the new verification path — every length is checked explicitly first. No fuzzy matching, searching, recovery, or retargeting was added anywhere. Six new regressions in `TestVerifyMutationAdversarial` (`tests/test_mutate.py`) call `_verify_mutation()` directly with adversarially-constructed before/after structures, proving failure for: target text remaining old, a trailing shape disappearing, a trailing slide disappearing, shape-identity/order differing, unrelated text changing, and (positive control) a genuinely correct mutation passing cleanly.

2. **DI-S3-02 — fixed.** `apply_approved_replacement()` now records whether `output_deck_path` already existed *before* calling `set_shape_text()`. If the post-mutation verification (`_verify_mutation()`, or the `inspect_deck()` reopen it depends on) then raises, and the output path did not pre-exist, the newly-created output is removed (`os.remove()`) before the original verification error propagates. If that removal itself fails, a new `OutputCleanupError` is raised, chained (`raise ... from`) onto the original verification error, so both failure contexts are preserved — the verification failure as `OutputCleanupError.__cause__`, the cleanup failure in `OutputCleanupError`'s own message. The source deck is never touched by any part of this cleanup path (`set_shape_text()`'s own existing contract already guarantees this independently, via its own source-hash-reverification step). A pre-existing output is never removed — guarded explicitly via the existed-before-call check, though this is also structurally unreachable in practice since `overwrite=False` is always hardcoded (`set_shape_text()` itself refuses to publish over a pre-existing path before Slice 3's own verification would ever run). Four new regressions in `TestOutputCleanupOnVerificationFailure` (`tests/test_mutate.py`) prove: a verification failure (simulated via `monkeypatch` on `_verify_mutation`) leaves no final output on disk; the source remains byte-identical; a genuinely pre-existing output at the target path is left completely untouched (the call fails earlier, inside `set_shape_text()` itself, with a typed `SafeDeckError`); and a simulated `os.remove()` failure during cleanup raises `OutputCleanupError` with both the original verification error (`__cause__`) and the cleanup failure (message) preserved.

3. **GOV-DI3-01 — fixed.** This file and `verification-report.md` added, recording the truthful chronology above (spec-before-implementation → Build 1 → initial deterministic validation pass → independent Codex Audit 1 FAIL → these three findings → this repair round → actual post-repair validation). No future PASS or closure pre-recorded.

## Re-audit 1 — FAIL/PARTIAL

Independent Codex re-audit of Repair Round 1's diff confirmed DI-S3-01 and GOV-DI3-01 closed, and found DI-S3-02's own fix still **PARTIAL**:

1. **DI-S3-02 (residual) — output-ownership race.** Repair Round 1's cleanup logic recorded only whether `output_deck_path` *existed* before the call, then removed whatever currently occupied that pathname on a verification failure. Codex reproduced a race this did not cover: (1) `set_shape_text()` publishes the expected output; (2) during Slice 3's own verification, some other process atomically replaces `output_deck_path` with an unrelated artifact; (3) verification fails; (4) cleanup deleted the replacement file — because "did the path exist before" says nothing about whether the file *currently* at that path is still the one this call itself created.

## Repair Round 2 — fix applied (this record)

**DI-S3-02 (residual) — fixed.** `apply_approved_replacement()` now establishes the *identity* of the file it just published — the POSIX `(st_dev, st_ino)` device+inode pair, captured via a new `_file_identity()` helper immediately after `set_shape_text()` returns. Before any cleanup removal, the current occupant of `output_deck_path` is re-stat'd and its identity compared against what was published; `os.remove()` is only called when the identities still match. A rename preserves this identity; a delete-and-recreate (or replace) at the same pathname does not, so a since-replaced file is left completely untouched, and the original verification error still propagates unchanged either way. This is the smallest mechanism the platform offers for "is this still the same file" without a path-based-only cleanup call trusting the pathname alone — it mirrors the same inode-stability property Safe PPT Engine's own `_publish_atomically()` already relies on internally (via `os.link`), so no new architectural concept is introduced. The unavoidable, structurally-minimal gap between the identity re-check and the `os.remove()` call itself is the smallest window any path-based POSIX API can offer — closing it further would require an OS-specific primitive this repository depends on nowhere else, which is out of scope for this bounded repair.

New regression: `test_ownership_race_replacement_artifact_is_never_deleted` (`tests/test_mutate.py`) — simulates an external replacement of `output_deck_path` during verification (via `monkeypatch` on `_verify_mutation`, performing an `os.replace()` onto the output path before raising), and proves: the replacement artifact survives byte-for-byte untouched; the source remains byte-identical; the original `ValidationError` still propagates and is still typed. A companion regression, `test_ownership_still_matches_when_nothing_replaces_the_output`, proves the ownership check is not overly cautious — ordinary cleanup (no replacement) still removes Slice 3's own output exactly as before. The existing `test_cleanup_failure_is_typed_and_explicit_with_both_contexts` regression (no replacement scenario) continues to pass unchanged, confirming existing cleanup-failure behavior is preserved.

## Preserved, unchanged by this repair

Exact `slide_index`/`shape_index` targeting only; optional `shape_id` guard with no guessing/retargeting on mismatch; mutation only through the existing, unmodified `set_shape_text()`; `overwrite=False` hardcoded; canonical source never modified (re-verified: real MasterSlide `.pptx` byte hash `e461613b...ab16834` unchanged before/after this entire repair round's validation); zero Editorial Memory access or write; zero `documentation_intelligence.locate` (Slice 2) involvement; no replacement-wording decision, claim extraction, product-Knowledge use, LLM/fuzzy/semantic matching, or batch mutation; zero Safe PPT Engine source changes.

## Verdict

**This repair is not yet independently re-audited.** A narrow Codex closure audit of DI-S3-02's ownership-race fix is the required next action before Slice 3 is integrated, declared complete, or used to generate any founder-facing test PPT.
