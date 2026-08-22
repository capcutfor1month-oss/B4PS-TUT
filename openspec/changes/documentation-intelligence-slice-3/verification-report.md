# Verification Report — Documentation Intelligence, Slice 3 (Controlled PPT Mutation Handoff)

## Founder summary

### Where things stand

Slice 3 (a controlled, read-mostly PPT mutation handoff — one already-approved text, one already-resolved target, one reused Safe PPT Engine mutation call) was specified before implementation, then implemented locally. Deterministic validation initially passed. Independent Codex Audit 1 returned **FAIL** — DI-S3-01 (incomplete post-mutation verification), DI-S3-02 (a failed wrapper verification left a published-but-unverified output file on disk), GOV-DI3-01 (missing governance records) — fixed as Repair Round 1. Independent Codex Re-audit 1 then confirmed DI-S3-01 and GOV-DI3-01 closed but found DI-S3-02 itself **PARTIAL**: the cleanup fix removed whatever currently occupied the output pathname, without confirming it was still the exact file this call had published — an output-ownership race. This record documents Repair Round 2, closing that residual finding. Not committed, pushed, or opened as a PR.

### Why this matters

The residual DI-S3-02 finding is the same class of problem the whole repair effort keeps closing: a check that looks complete but has a gap under adversarial conditions is worse than no check at all. "Does the output path exist" and "did it exist before this call" both say nothing about whether the file *currently* there is still the artifact this call itself produced — a cleanup routine that trusts a pathname alone can delete someone else's file the moment two things race for the same path, which is exactly the kind of silent, hard-to-notice failure this slice exists to prevent, not commit.

### What has already happened

Repair Round 1 closed DI-S3-01 (structurally complete `_verify_mutation()`) and GOV-DI3-01 (governance records) — both reconfirmed closed by Re-audit 1, unaffected by this round. This round (Repair Round 2) closes DI-S3-02's residual ownership race: `apply_approved_replacement()` now captures the POSIX device+inode identity of the file `set_shape_text()` just published, and only removes the current occupant of `output_deck_path` on a verification failure when its identity still matches — a since-replaced file is left completely untouched. Two new regressions added (the ownership-race adversarial case, and a positive-control case proving ordinary cleanup still works).

### What happens next

A narrow, targeted independent Codex closure audit of this round's DI-S3-02 fix.

### Founder action or decision

None required by this record itself.

### Recommended option and reason

Commission the narrow Codex closure audit before any commit/push/PR/merge, matching this repository's established convention. Do not generate or publish the founder-facing final test PPT until this slice passes that audit and is integrated.

## Technical evidence

### Change verified

- `documentation_intelligence/mutate.py`: new `_file_identity(path)` — returns the POSIX `(st_dev, st_ino)` pair for `path`, or `None` if it cannot be stat'd. `apply_approved_replacement()` now captures `published_identity = _file_identity(output_deck_path)` immediately after `set_shape_text()` returns (a real file now exists there); on a subsequent verification failure, it re-stats the current occupant of `output_deck_path` and only calls `os.remove()` when the current identity still equals `published_identity`. The `output_existed_before_call` boolean tracking from Repair Round 1 is superseded by this identity check, which subsumes its guarantee (a genuinely pre-existing output is structurally unreachable anyway, since `overwrite=False` means `set_shape_text()` itself refuses to publish over one before this logic would ever run).

### Classification

**Standard** base tier (see `spec.md` → Classification, unchanged this round). Audit 1: **FAIL**, fixed as Repair Round 1. Re-audit 1: **FAIL/PARTIAL** on DI-S3-02's ownership race. This round (Repair Round 2) has not yet been re-audited.

### Builder review

- **DI-S3-02 (residual, ownership race)**: reproduced by monkeypatching `mutate.py`'s own `_verify_mutation` to, as a side effect, atomically replace `output_deck_path` with an unrelated artifact (via `os.replace()`) before raising `ValidationError` — simulating exactly the race Codex reported. Pre-fix, cleanup would have deleted this replacement file purely because the pathname was occupied and the boolean "existed before" check said it was fine to remove. Post-fix, the identity captured right after `set_shape_text()` published no longer matches the replacement file's own identity, so cleanup correctly declines to remove it — the replacement survives byte-for-byte, the source remains untouched, and the original `ValidationError` still propagates. A companion positive-control test (no replacement) confirms the identity check does not become overly cautious: ordinary cleanup still removes Slice 3's own output exactly as Repair Round 1 established. The existing cleanup-failure regression (`test_cleanup_failure_is_typed_and_explicit_with_both_contexts`) continues to pass unmodified, confirming that behavior is preserved.

### Environment

Local `python3` (system interpreter) for non-`pptx`-dependent checks; a throwaway local venv (installs `python-pptx`/`Pillow`/`numpy`/`opencv-python-headless`/`pytest`, since the system interpreter is externally-managed and lacks them) for every test that touches `.pptx` files, deleted after use — nothing added to the repository.

One incidental finding during this round's validation, unrelated to the code changes: the Safe PPT Engine's own test suite includes several assertions that the *entire shared system temp directory* (`tempfile.gettempdir()`) contains no leftover `b4ps_engine_*`/`.b4ps_publish_*` files — a single such file left over from unrelated prior activity in this same machine session caused 14 of those tests to fail on the first run this round. Removing that one stray file (not created by any Slice 3 code or test in this round — confirmed by re-running Slice 3's own suite immediately afterward with the temp directory verified clean both before and after) restored a clean 206/206 pass. Recorded here for transparency; no Safe PPT Engine source was touched, and this is a pre-existing environmental-isolation characteristic of that suite's own tests, not a defect introduced by this repair.

### Commands executed

```
cd documentation-intelligence && python -m pytest tests/ -q
cd documentation-intelligence && python -m pytest tests/test_mutate.py tests/test_ppt_engine_import_order.py tests/test_locate.py tests/test_import_unrelated_lib_conflict.py tests/test_import_alias_first.py tests/test_import_order.py tests/test_compare.py -q   # reversed order
cd baseline/B4PS-TUT-main/.b4ps-tools && python -m pytest tests/ -q
python -m pytest editorial-memory/tests -q
python -m pytest editorial-memory/tests documentation-intelligence/tests -q          # combined session
python -m pytest documentation-intelligence/tests editorial-memory/tests -q          # combined session, reversed dir order
python3 scripts/check_pipeline.py
python3 -m py_compile documentation-intelligence/documentation_intelligence/*.py documentation-intelligence/tests/*.py
git diff --check
```

### Checks passed

- Focused Slice 3 tests (`test_mutate.py`, including the 2 new Repair Round 2 regressions): 33/33 passed.
- Full Documentation Intelligence suite (Slices 1–3): 91/91 passed.
- Safe PPT Engine's own suite: 206/206 passed.
- `editorial-memory/tests` alone: 343/343 passed.
- Combined `editorial-memory` + `documentation-intelligence`, both directory orders: 434/434 passed both ways.
- `python scripts/check_pipeline.py` → "Bridge4PS target-repository pipeline-adoption checks passed."
- `py_compile` → clean.
- `git diff --check` → exit 0.
- Real-deck-copy mutation regression (`TestRealPinnedMessagesFixtureCopy`, target `slide_index=74`/`shape_index=12`/`shape_id=2428`): passed in isolation, shared temp directory verified clean before and after.
- Byte-level immutability, before/after the full run: Editorial Memory store hash `ad0b6a31...5f3432c5` (40 files) unchanged; real MasterSlide `.pptx` hash `e461613b...ab16834` unchanged.

### Checks failed

None (against the repaired code). Audit 1 returned FAIL, and Re-audit 1 returned FAIL/PARTIAL on DI-S3-02, against the respective pre-repair states — see `audit-report.md` → Verdict.

### Pipeline / CI evidence

No CI run exists for this change — it has not been pushed. The local `check_pipeline.py` pass is the only pipeline evidence available at this stage.

### Founder-preview requirement

Not applicable to this record — no founder-facing test PPT has been generated or published; that remains explicitly deferred until after independent Codex re-audit and integration.

### Profile-specific gates

Not applicable — see `spec.md` → Classification.

### Files changed (Repair Round 2, this record)

- `documentation-intelligence/documentation_intelligence/mutate.py` (new `_file_identity()`; cleanup gated on identity match, not path-existed-before)
- `documentation-intelligence/tests/test_mutate.py` (2 new regressions: ownership-race case, positive-control case)
- `openspec/changes/documentation-intelligence-slice-3/{verification-report.md, audit-report.md}` (this round's chronology)

`editorial-memory/`, `baseline/B4PS-TUT-main/.b4ps-tools/` (Safe PPT Engine source itself), `documentation_intelligence/_safe_ppt_engine_import.py`, and `documentation_intelligence/locate.py` remain completely untouched this round.

### Remaining uncertainty

The cleanup identity re-check and the `os.remove()` call itself remain two separate steps — the smallest gap any path-based POSIX API can offer without an OS-specific primitive this repository depends on nowhere else. Carries forward Slice 2's own accepted, Codex-confirmed bounded import-ordering limitation (unaffected by this round). The actual founder-facing test PPT has still not been generated — explicitly deferred until after independent Codex closure audit and integration.

### Recommended next action

A narrow, targeted independent Codex closure audit of this round's DI-S3-02 ownership-race fix. Do not commit, push, or merge, and do not generate any founder-facing test PPT, until that audit occurs.
