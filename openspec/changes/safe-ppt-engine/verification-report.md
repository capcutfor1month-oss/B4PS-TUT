# Verification Report — Safe PPT Engine (Builds 1–2, Audit Repairs 1–2)

## Founder summary

### Where things stand

The Safe PPT Engine's mechanical read/inspect/mutate primitives (Build 1: `set_shape_text`; Build 2: `move_shape`, `resize_shape`, `set_shape_geometry`, `replace_picture`) have been through two rounds of independent Codex audit and two matching repair rounds. Every finding from both audits (F-01–F-08, then F-02/F-04/F-05/F-06/R-01/R-02) is fixed and tested by Claude's own suite. **A third independent Codex re-audit, of this repair (Audit Repair 2), has not yet been performed** — see `audit-report.md` for the full audit history and `spec.md` for the change classification this file's evidence is scoped against.

### Why this matters

This is safety-critical local-file infrastructure: it exists specifically so a mutation can never corrupt the one copy of a source PPTX. Two audit rounds already found real defects in exactly that guarantee (source aliasing, publication races, incomplete relationship cleanup). Trusting the engine's current state as "safe" should rest on independent verification, not the implementer's own tests alone — which is why a third audit round is the recorded next action, not optional.

### What has already happened

Repair implemented and tested; see `docs/DECISIONS.md` (PROJ-009, PROJ-010) for the technical account of each fix, and `audit-report.md` for the audit-verdict history.

### What happens next

An independent Codex re-audit of Audit Repair 2. Not performed as part of this record.

### Founder action or decision

None required to merge this record. Separately, truthful founder-preview status (below) shows that the Standard-tier "founder usability testing" evidence layer required by `docs/TESTING.md` has not been performed for this engine — no human has visually confirmed a Safe-PPT-Engine-generated `.pptx` renders correctly in real PowerPoint. That is a genuinely open gate, not fabricated as complete here.

### Recommended option and reason

Commission the independent Codex re-audit before building further capability on this engine. Separately, and lower priority, arrange a founder/human preview of at least one generated output in real PowerPoint before this engine is relied upon for actual Bridge4PS deck edits (not required before merging this repair, which is bounded engine-correctness work, but required before the engine's output is trusted end-to-end).

## Technical evidence

### Change verified

Safe PPT Engine Build 1 (`set_shape_text`), Build 2 (`move_shape`, `resize_shape`, `set_shape_geometry`, `replace_picture`), Audit Repair 1 (F-01–F-08), and Audit Repair 2 (F-02, F-04, F-05, F-06, R-01, R-02) — all in `baseline/B4PS-TUT-main/.b4ps-tools/lib/ppt_engine.py` and `b4ps.py`.

### Classification

See `spec.md` → "Classification" for the canonical record (base tier, rationale, applicable profiles, audit requirement), per `docs/TESTING.md` → "Canonical recording surface", which specifies classification belongs in the change's `spec.md`. Summary: **Standard** base tier, **Data-sensitive** profile applies, **UI-sensitive** does not apply, independent Codex audit explicitly required and performed twice (see `audit-report.md`).

### Builder review

Performed by the implementing session at each stage: manual reproduction of each Codex finding against the pre-repair code before writing a fix; a full diff review of each PR for scope creep before commit; and, for Audit Repair 2 specifically, a deliberate check that the fix for R-02 test-quality findings actually strengthens the *mechanism* proof (call-order and call-count assertions, not only end-state filesystem checks). This is builder-side review only — it is not, and does not substitute for, the independent Codex audit `docs/TESTING.md` requires as the higher-order gate for this component.

### Environment

Python 3.14, `pytest` 9.1.1, dependencies from `requirements-dev.txt` (`Pillow`, `numpy`, `opencv-python-headless`, `python-pptx`, `pytest`) installed into an isolated virtualenv. macOS (Darwin), local filesystem (case-sensitive APFS volume).

### Commands executed

```bash
python -m py_compile lib/ppt_engine.py b4ps.py
python -m pytest tests/ -v
python scripts/check_pipeline.py   # run from repository root
```

### Checks passed

- `python -m pytest tests/` → **185 passed** (Build 1: 37; Build 2: +35 = 72; Audit Repair 1: +48 = 120; Audit Repair 2: +65 = 185).
- All pre-existing tests pass unmodified except explicitly justified changes: two Audit Repair 1 wording/JSON-shape updates (documented in the prior version of this report and in `docs/DECISIONS.md` PROJ-009), and two Audit Repair 1 test-body updates in this round (`test_f05_staging_copy_failure_leaves_no_temp_file`, `test_f05_save_failure_cleans_up_staged_file_and_leaves_source_untouched` — both now assert the more specific `TransactionIOError` that F-05's stronger typing introduces, in place of the broader `DeckSourceError`/raw `OSError` they previously accepted).
- `python scripts/check_pipeline.py` → `Bridge4PS target-repository pipeline-adoption checks passed.`
- Canonical archive `baseline/source-artifacts/B4PS-TUT-main.zip` SHA-256 unchanged throughout Builds 1, 2, and both repairs.
- Manual reproduction confirmed each of F-02, F-04, F-05, R-01, R-02 was real against the pre-Repair-2 code and fixed against the repaired code; F-01/F-03/F-07/F-08 confirmed still closed (regression tests included).
- A genuine (unmocked) filesystem failure was also found and fixed during this round: `_publish_atomically`'s own `tempfile.mkstemp` call was not wrapped in typed-error handling, so a permission-denied output directory produced a raw traceback at the CLI. Found by a real (not mocked) read-only-directory test, fixed, and now covered by that same test.

### Checks failed

None outstanding in this repository's own test suite as of this report. (Historical: both Codex audits are the "failures" this report exists to record truthfully — see `audit-report.md`.)

### Pipeline / CI evidence

`python scripts/check_pipeline.py` passes locally (see above); the companion PR's GitHub Actions `validate` check (`.github/workflows/pipeline-checks.yml`, running the same script) is the CI-equivalent gate and is expected to pass identically. This report is updated with the actual CI result once the PR is inspected, per the repair task's own workflow.

### Founder-preview requirement

Per `docs/TESTING.md`, Standard-tier changes require "founder usability testing" as part of required evidence. **Status: PENDING — genuinely open, not waived.** No human has opened a Safe-PPT-Engine-generated `.pptx` in real PowerPoint (or any real presentation viewer) to visually confirm the mutation looks correct; all verification here is programmatic (reopen-and-check-attributes via python-pptx). This is recorded truthfully as an open gate rather than marked complete, per the explicit instruction not to fabricate approvals or completions that did not happen.

### Profile-specific gates (Data-sensitive)

| Required evidence | Status | Detail |
|---|---|---|
| Migration test | N/A (approved) | No database or schema is involved; the "migration" here is a whole-file rewrite, not a schema migration. |
| Data-preservation check | Complete | Source-hash-unchanged verified before and after every mutation (defense-in-depth check after, primary gate before publish per R-01); adversarial symlink/alias tests (F-01); dedicated tests per mutation family. |
| Tenancy-isolation check | N/A (approved) | This is a single-process local-file library with no multi-tenant concept; there is no tenant boundary to isolate. |
| Rollback plan | Complete | The engine never writes in place — the original input file is never the write target of any operation (enforced by `_assert_safe_output_path`). "Rollback" for a mutation is simply: the original file was never touched, so no rollback action is needed on the source; for the *generated output*, discarding it (or not merging the PR that would ship it) is the rollback. |

### Files changed

`lib/ppt_engine.py`, `b4ps.py`, `tests/test_ppt_engine.py` (2 F-01-era assertions, unchanged this round), `tests/test_engine_cli.py`, `tests/test_engine_cli_geometry_image.py`, `tests/test_ppt_engine_audit_repair.py` (2 assertion updates this round), new `tests/test_ppt_engine_audit_repair_2.py`, `docs/CURRENT.md`, `docs/DECISIONS.md`, `openspec/changes/safe-ppt-engine/spec.md` (new), `openspec/changes/safe-ppt-engine/audit-report.md` (new), this file.

### Remaining uncertainty

- Independent Codex re-audit of Audit Repair 2 has not been performed.
- Founder/human preview of generated output in real PowerPoint has not been performed (see above — genuinely pending, not a fabricated pass).
- The 8 historically-unavailable Git LFS production assets (including both production decks) remain unresolved and were not needed by any test here.
- The atomic no-overwrite publish path (`os.link`) has not been exercised against non-POSIX or non-hardlink-capable filesystems (e.g. some network shares); behavior there is standard-library-dependent and not separately verified in this environment.

### Recommended next action

Independent Codex re-audit of Audit Repair 2. Editorial Memory and Documentation Intelligence remain not started and are out of scope until re-audit clears.
