# Verification Report — Documentation Intelligence, Slice 1 (Build 1 + Repair Rounds 1–3)

## Founder summary

### Where things stand

Slice 1 (a read-only Editorial Memory delta-comparison layer) was implemented locally. Audit 1 returned **FAIL** (4 code + 3 governance findings), fixed as Repair Round 1. Re-audit 1 returned **FAIL** (3 code findings — DI-S1-01, DI-S1-02, DI-S1-04 — plus 3 governance/test findings — TEST-DI-01, GOV-DI-01, GOV-DI-03), fixed as Repair Round 2. Re-audit 2 confirmed 5 of those 6 closed and found one residual gap in DI-S1-04 (an unrelated-`lib`-occupant path that silently fell back to a private alias instead of failing), fixed as Repair Round 3, recorded in this same change. Not committed, pushed, or opened as a PR — left as working-tree changes per explicit task instruction.

### Why this matters

Repair Round 2's DI-S1-04 fix closed the ordering Codex first reproduced (an existing editorial-memory copy found under another alias) but left a second, narrower ordering open: nothing loaded yet, and `lib` already claimed by something unrelated. Both are the same underlying property — no import ordering may ever leave two different `Relation`/`EditorialMemory`/exception objects live in one process — so closing one path and leaving the other was still an incomplete fix, not a different bug.

### What has already happened

`documentation-intelligence/documentation_intelligence/_editorial_memory_import.py`'s `_load_editorial_memory_lib()` no longer falls back to the private alias when `lib` is unrelated-occupied and no existing copy can be canonicalized — it raises `EditorialMemoryImportConflictError` immediately instead. The now-dead private-alias constant was removed. A new subprocess-isolated regression, `tests/test_import_unrelated_lib_conflict.py`, reproduces the exact Codex condition. 33 Documentation Intelligence tests pass (up from 32); the full combined suite (`editorial-memory` + `documentation-intelligence`, one process, both directory orders) is 376/376.

### What happens next

A further independent Codex closure re-audit of this repaired local diff.

### Founder action or decision

None required by this record itself — no PR exists to merge.

### Recommended option and reason

Commission the next Codex re-audit before any commit/push/PR/merge, matching this repository's established convention.

## Technical evidence

### Change verified

- `compare.py`: `expected_verification_scope` parameter removed. New `_resolve_typed_item`/`_all_recorded_evidence_ids` helpers: type-checks the exact referenced KnowledgeItem unconditionally (independent of `get_current_by_key`), and computes Evidence relevance as membership in the union of `evidence_refs` across *every* state (any status) of the resolved `product_key` item. `relation_candidate` derivation reordered so evidence-sufficiency is checked first, uniformly gating both `NEW` and `CONFIRMS` (previously sufficiency was only explicitly checked in the `CONFIRMS` branch).
- `_editorial_memory_import.py`: new `_canonicalize_under_lib` — registers an alias-discovered module (and its already-imported submodules) under the canonical name `lib`; new `EditorialMemoryImportConflictError`, raised instead of silently proceeding when `lib` is already bound to something genuinely unrelated.
- `tests/test_compare.py`: `TestEvidenceRelevance` rewritten (scope-based tests replaced with item-history-based ones, plus a dedicated DI-S1-01 reproduction); `TestDeterministicRelationReasoning`'s NEW test rewritten to use a persisted-but-unapproved state instead of scope matching, plus a new "no KnowledgeItem at all → NEW never produced" case and a new "CONFIRMS requires relevant Evidence too, not text match alone" case; `TestKnowledgeTypeEnforcement` gains two DI-S1-02 regressions (wrong type + no current state; wrong type + opt-in false); the previously byte-snapshot-missing real-data test fixed.
- `tests/test_import_alias_first.py` (new): DI-S1-04 regression, run via `subprocess` in a fully isolated fresh Python process to make the alias-first ordering unambiguous regardless of this suite's own file-collection order.
- `editorial-memory/` confirmed unmodified: `git status --short editorial-memory/` shows nothing.

### Classification

**Standard** base tier (see `spec.md` → Classification, added Repair Round 2 per GOV-DI-01). Three audit rounds so far: Audit 1 (Repair Round 1) **FAIL**; Re-audit 1 (Repair Round 2) **FAIL**; Re-audit 2 (Repair Round 3, this record) **FAIL**.

### Builder review

Re-audit 1 findings, previously confirmed fixed (unchanged this round): DI-S1-01, DI-S1-02, TEST-DI-01, GOV-DI-01, GOV-DI-03.

The Re-audit 2 residual finding was reproduced before its fix:

- **DI-S1-04 (residual)**: reproduced by preloading an unrelated `types.ModuleType("lib")` into `sys.modules["lib"]` in a clean subprocess, with no editorial-memory copy loaded anywhere else, then importing the DI bridge. Under Repair Round 2's code this succeeded silently, loading editorial-memory under `_documentation_intelligence_editorial_memory_lib` and leaving the unrelated `lib` binding in place — a live divergent-identity state. Under Repair Round 3's code the same sequence raises `EditorialMemoryImportConflictError` before any load happens, and the bridge module never appears in `sys.modules`. The new test (`test_import_unrelated_lib_conflict.py`) fails against the pre-fix code and passes against the fix; it also asserts no module ends up loaded under the old private-alias name.

### Environment

Local `python3` (system interpreter). Run against the working tree.

### Commands executed

```
cd documentation-intelligence && python3 -m pytest tests/test_import_unrelated_lib_conflict.py -q
cd documentation-intelligence && python3 -m pytest tests/ -q
cd documentation-intelligence && python3 -m pytest tests/test_import_unrelated_lib_conflict.py tests/test_import_alias_first.py tests/test_import_order.py tests/test_compare.py -q   # reversed order
python3 -m pytest editorial-memory/tests -q
python3 -m pytest editorial-memory/tests documentation-intelligence/tests -q          # combined session
python3 -m pytest documentation-intelligence/tests editorial-memory/tests -q          # combined session, reversed dir order
python3 scripts/check_pipeline.py
python3 -m py_compile documentation-intelligence/documentation_intelligence/*.py documentation-intelligence/tests/*.py
git diff --check
```

### Checks passed

- New regression `test_import_unrelated_lib_conflict.py` → 1/1 passed.
- `documentation-intelligence/tests/` alone → 33/33 passed (up from 32).
- Reversed file collection order → 33/33 passed, unchanged.
- `editorial-memory/tests` alone → 343/343 passed, unchanged.
- Combined `editorial-memory/tests` + `documentation-intelligence/tests`, both directory orders → 376/376 passed both ways.
- `python scripts/check_pipeline.py` → "Bridge4PS target-repository pipeline-adoption checks passed."
- `py_compile` → clean.
- `git diff --check` → exit 0.
- Real-store byte-level immutability: sha256 of every file under `documentation-artifacts/bridge-ui-evidence/store` identical before and after the full validation run (40 files, hash `ad0b6a31...5f3432c5`, unchanged from the pre-round-3 baseline).

### Checks failed

None (against the repaired code). Re-audit 2 returned FAIL against the pre-Repair-Round-3 code — see `audit-report.md` → Verdict.

### Pipeline / CI evidence

No CI run exists for this change — it has not been pushed. The local `check_pipeline.py` pass is the only pipeline evidence available at this stage.

### Founder-preview requirement

Not applicable — no user-facing surface exists in this slice.

### Profile-specific gates

Not applicable — see `spec.md` → Classification (neither UI-sensitive nor Data-sensitive applies).

### Files changed (Repair Round 3, in addition to Repair Rounds 1–2's files)

- `documentation-intelligence/documentation_intelligence/_editorial_memory_import.py` (unrelated-`lib` fallback removed; raises `EditorialMemoryImportConflictError` instead; dead private-alias constant removed)
- `documentation-intelligence/tests/test_import_unrelated_lib_conflict.py` (new)
- `openspec/changes/documentation-intelligence-slice-1/{spec.md, verification-report.md, audit-report.md}` (this record)

`editorial-memory/` remains completely untouched. `compare.py`, `test_compare.py`, `test_import_alias_first.py`, `docs/DECISIONS.md`, and `docs/INDEX.md` are unchanged this round.

### Remaining uncertainty

`REFINES`/`CONTRADICTS`/`SUPERSEDES` remain, by founder-accepted design, unreachable outcomes in this slice. The `_canonicalize_under_lib` "claim the global name `lib`" strategy remains a deliberate, documented trade-off rather than a fully side-effect-free solution — every non-canonicalizable case (alias-found-but-conflicting, or unrelated-occupant-with-nothing-to-canonicalize) now fails explicitly via `EditorialMemoryImportConflictError` rather than silently proceeding under any alias, per the founder's own Option A/B framing.

### Recommended next action

A further independent Codex closure re-audit of this repaired local diff. Do not commit, push, or merge, and do not treat this change as PASS or complete, until that audit occurs.
