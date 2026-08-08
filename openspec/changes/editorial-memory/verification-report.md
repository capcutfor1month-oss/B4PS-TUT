# Verification Report — Editorial Memory (Slice 1, Repair 2)

## Founder summary

### Where things stand

Editorial Memory Slice 1 was implemented, tested, and merged to `main` (`93e87239ea9b55185f374f1a3aa2a390be03c24f`, PR #9). Independent Codex audit round 1 (Audit 1) found three real defects — EM-01, EM-02, EM-03 — plus a related JSON-corruption-normalization gap, all fixed locally as Repair 1. Independent Codex audit round 2 (Audit 2) then re-audited Repair 1's local diff and returned **PASS WITH FINDINGS**: EM-01/EM-02/EM-03 confirmed closed, and one new, narrower finding — EM-04, the same class of unvalidated-path defect in `evidence_id` handling — raised. **The fix for EM-04, recorded in this update, exists only as a local, uncommitted working-tree change** — per explicit instruction, it has not been committed, pushed, or opened as a PR, so `main` still reflects the original merged Slice 1 state.

### Why this matters

Editorial Memory exists to hold claims about Bridge4PS without ever letting the mere existence of an artifact be mistaken for approved current truth. EM-04 is the same category of gap as EM-03: an unvalidated caller-controlled (or persisted) string used directly as a filesystem path component is a genuine security-adjacent boundary violation, not just a lifecycle-logic gap — and it was already flagged, by name, as a known limitation in Repair 1's own verification report, so its confirmation by Audit 2 is exactly the kind of check independent audit exists to force.

### What has already happened

Slice 1 was implemented and merged. Audit 1 found EM-01/EM-02/EM-03, fixed as Repair 1. Audit 2 re-audited Repair 1, confirmed those three closed, and raised EM-04. EM-04 has now been fixed and tested locally, left as uncommitted working-tree changes for Codex to audit directly, per explicit instruction.

### What happens next

Codex reviews these local working-tree changes (Audit 3). Not performed as part of this task — this task explicitly stops after local repair, without committing, pushing, or opening a PR.

### Founder action or decision

None required by this record itself (no PR exists to merge). Founder should treat this round's fix as implementer-verified, not independently verified, until Audit 3 happens.

### Recommended option and reason

Have Codex audit the local working-tree changes described here (Audit 3) before they are committed, pushed, or merged, and before Slice 2 begins.

## Technical evidence

### Change verified

Editorial Memory Slice 1 as merged (`93e87239ea9b55185f374f1a3aa2a390be03c24f`), Repair 1's fixes for EM-01/EM-02/EM-03 (confirmed closed by Audit 2, unchanged in this round), and — as a further local, uncommitted change only — the fix for Audit 2's EM-04 finding:

- **EM-01** (Repair 1, confirmed closed by Audit 2): `get_current()` now re-checks that every piece of Evidence a current state cites still resolves (exists and parses) on every call, raising typed `CorruptProvenanceError` — chaining the underlying error via `__cause__` — instead of returning a state whose provenance can no longer actually be verified.
- **EM-02** (Repair 1, confirmed closed by Audit 2): `get_or_create_knowledge_item` now compares the stored natural key against the requested one whenever an existing item is found at the same slug; a mismatch (e.g. `"a.b"` vs `"a-b"`, both normalizing to `"a-b"`) raises typed `KeyCollisionError` instead of silently treating two distinct subjects as the same `KnowledgeItem`.
- **EM-03** (Repair 1, confirmed closed by Audit 2): `feature_area` is now validated against a safe `<platform>.<feature>` pattern (lowercase alphanumerics/hyphens, dot-separated segments only — no `/`, `\`, `..`, empty segments, or leading/trailing dots) before it is ever used as a path component, raising typed `InvalidFeatureAreaError` on rejection. A second, defense-in-depth check resolves the final knowledge-item path and confirms it still lands inside the configured `knowledge/` directory.
- **JSON-corruption normalization** (Repair 1, unchanged): `load_evidence`/`load_knowledge_item` now catch `json.JSONDecodeError` and re-raise as typed `StorageCorruptionError`.
- **EM-04** (new, Repair 2): `evidence_id` is now validated the same way `feature_area` was for EM-03 — `store.validate_evidence_id()` allowlists a plain lowercase-alphanumerics/hyphens token (matching exactly what `record_evidence()` generates), applied in `_evidence_path()` before any filesystem access, raising typed `InvalidEvidenceIdError` on rejection, plus the same defense-in-depth resolved-path containment check. Because `get_current()`'s EM-01 check already wraps each evidence lookup in a generic `except EditorialMemoryError`, a persisted-but-tampered `evidence_refs` entry surfaces as `CorruptProvenanceError` chaining `InvalidEvidenceIdError`, with no change needed to `memory.py`.

Also corrected in Repair 1 (unchanged this round): `docs/CURRENT.md` wording that claimed Safe PPT Engine Audit Repair 7 remained uncommitted/unintegrated, when Git history (`40f3a1083bf8556830abf9552fb186f629412c5c`, merged as `be6df7fdfe8f6ab4cad24f4c3c3a7408945cb715`, PR #8) shows it was already integrated.

### Classification

Unchanged from Slice 1: **Standard** base tier, **Data-sensitive** profile applies, **UI-sensitive** does not apply (see `spec.md`). Independent Codex audit is confirmed as an explicit, exercised requirement — Audit 1 found real defects; Audit 2 confirmed their closure and found a further one.

### Builder review

Repair 1 (unchanged): manual reproduction of each Audit 1 finding against the pre-repair code before writing a fix — confirmed `get_current()` returned a state with a deleted/corrupted evidence reference with no error (EM-01); confirmed `"a.b"` and `"a-b"` silently resolved to the same `KnowledgeItem` (EM-02); confirmed a `feature_area` of `"../../../etc"` wrote outside the configured store root (EM-03); confirmed a corrupted JSON file raised a raw `json.JSONDecodeError` rather than a typed error.

Repair 2 (new): manual reproduction of EM-04 against the pre-repair `_evidence_path()` — confirmed `get_evidence("../../escape")` and similar traversal values were passed straight into a path join with no validation, and that a persisted `evidence_refs` entry tampered to a traversal value was likewise never checked. Each new test was then confirmed to fail against the pre-fix logic specifically (not merely against missing symbols) before being accepted as a genuine regression — see "Checks passed" below.

### Environment

Python 3.14, `pytest` 9.1.1, installed into an isolated virtualenv from `editorial-memory/requirements-dev.txt` (pytest only — no new runtime dependency).

### Commands executed

```bash
python -m py_compile editorial-memory/lib/*.py editorial-memory/tests/*.py
python -m pytest editorial-memory/tests/ -v
python scripts/check_pipeline.py   # run from repository root
git diff --check
```

### Checks passed

- `python -m pytest editorial-memory/tests/` → **59 passed** (26 pre-existing Slice 1 tests + 23 Repair-1 adversarial tests, all unmodified, + 10 new Repair-2/EM-04 adversarial tests: a 6-value parametrized path-traversal matrix, a no-disk-escape check, a valid-generated-id regression guard, a persisted-malicious-provenance-reference test via `get_current`, and a reload test).
- Manual regression check: reverted `_evidence_path()` to its pre-fix form (unvalidated path join, new error types still available/unused) and re-ran the EM-04 tests — 9 of the 10 new tests failed as expected (the traversal matrix, the no-disk-escape check, the persisted-malicious-reference test, and the reload-rejection test all failed to raise `InvalidEvidenceIdError`/`CorruptProvenanceError`), while only the valid-generated-id regression guard still passed; confirms the tests exercise real logic, not just new symbols existing.
- Full pre-fix-vs-post-fix check (Repair 1, unchanged): running the Repair-1 test additions against the original (pre-Repair-1) `lib/` files fails at import time (the new exception types don't exist yet).
- `python -m py_compile` on all `lib/` and `tests/` files → clean.
- `python scripts/check_pipeline.py` → `Bridge4PS target-repository pipeline-adoption checks passed.`
- `git diff --check` → clean, no whitespace errors.
- Manual disk inspection confirmed EM-03's and EM-04's rejection paths never create any file or directory outside (or even inside, for the rejected call) the configured root.

### Checks failed

None outstanding in this repository's own local test suite as of this report. (Historical: Audit 1's **FAIL** and Audit 2's EM-04 finding are results this report exists to record truthfully — see `audit-report.md`.)

### Pipeline / CI evidence

**Local only**: `python scripts/check_pipeline.py` and `git diff --check` both pass (see above). This is the only CI-equivalent evidence available for this round's changes, because they are local and uncommitted — there is no PR and therefore no GitHub Actions run for them.

### Founder-preview requirement

Unchanged from Slice 1: not applicable in the usual sense — no user-facing surface exists yet.

### Profile-specific gates (Data-sensitive)

| Required evidence | Status | Detail |
|---|---|---|
| Migration test | N/A | Unchanged from Slice 1 — no existing schema/data is migrated. Not an approval, a factual scope statement. |
| Data-preservation check | Complete | EM-01's fix specifically strengthens this: a current state's provenance is now actively re-verified, not merely assumed intact, on every retrieval. |
| Tenancy-isolation check | N/A | Unchanged from Slice 1 — single-process local-file library, no multi-tenant concept. Not an approval, a factual scope statement. |
| Rollback plan | Complete | Unchanged from Slice 1 (atomic per-file writes); EM-03's containment check additionally ensures a rejected write can never land outside the configured root to begin with, so there is nothing to roll back for a rejected call. |

### Files changed

`editorial-memory/lib/errors.py`, `editorial-memory/lib/store.py`, `editorial-memory/lib/__init__.py`, `editorial-memory/tests/test_editorial_memory.py` (modified this round, local/uncommitted, on top of Repair 1's already-modified `editorial-memory/lib/memory.py`, unchanged this round); `docs/CURRENT.md`, `docs/DECISIONS.md` (modified, local/uncommitted); `openspec/changes/editorial-memory/{spec.md, verification-report.md, audit-report.md}` (modified, local/uncommitted).

### Remaining uncertainty

- Independent Codex re-audit of this round's fix (Audit 3) has not occurred — the required next action, out of scope for this task per explicit instruction to stop after local repair.
- No consumer exists yet (Documentation Intelligence has not started), so end-to-end usage beyond the test suite remains unproven.
- Concurrency behavior under simultaneous writers remains untested — unchanged limitation from Slice 1.

### Recommended next action

Commission an independent Codex re-audit of these local working-tree changes (Audit 3). Do not commit, push, or merge them as part of this task. Do not begin Editorial Memory Slice 2 until Audit 3 clears.
