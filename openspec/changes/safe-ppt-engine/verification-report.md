# Verification Report — Safe PPT Engine (Builds 1–2, Audit Repairs 1–7)

## Founder summary

### Where things stand

The Safe PPT Engine's mechanical read/inspect/mutate primitives (Build 1: `set_shape_text`; Build 2: `move_shape`, `resize_shape`, `set_shape_geometry`, `replace_picture`) have been through seven rounds of independent Codex audit. The first two rounds' findings (F-01–F-08, then F-02/F-04/F-05/F-06/R-01/R-02) were fixed, pushed, and merged. A third round (Audit 3) found 4 findings remaining against the merged state; those were fixed locally as Audit Repair 3, and Codex re-audited that local diff directly (Audit 4), finding F-05, F-06, and R-02 still had residual gaps (R-01 confirmed closed). Those were fixed as Audit Repair 4, re-audited directly as Audit 5, which found Repair 4's F-05 fix incomplete (it removed the leaked temp *pathname* but never verified the file descriptor itself stayed closed) plus 2 narrower governance-wording gaps. Repair 5 fixed Audit 5's F-05 finding by having `create_working_copy` probe the fd with `os.fstat` and retry `os.close` once after a reported close failure - **and Audit 6 found that fix itself unsafe**: retrying a close, or even just probing with `fstat`, after a failed `close()` risks acting on a file descriptor the process no longer owns, if that fd number has already been reused by unrelated code. **The fixes for Audit 6's findings, recorded in this update, exist only as local, uncommitted working-tree changes** — per explicit instruction, they have not been committed, pushed, or opened as a PR.

### Why this matters

This is safety-critical local-file infrastructure: it exists specifically so a mutation can never corrupt the one copy of a source PPTX. Seven audit rounds have now found real, distinct defects in that guarantee. This round is notable because the defect found was in a *fix*, not an unfixed gap: Repair 5's retry logic was reasoned through and documented as safe, and that reasoning was wrong in a way regular functional testing would not surface, since it only manifests under a genuine fd-reuse race. That is precisely the kind of claim independent audit exists to catch rather than accept on the implementer's own confidence.

### What has already happened

Audit Repairs 1 and 2 were implemented, tested, pushed, and merged (see `docs/DECISIONS.md` PROJ-009, PROJ-010, and `audit-report.md`). Audit Repair 3 fixed Audit 3's findings and was re-audited directly as Audit 4, which found F-05, F-06, R-02 not yet fully closed. Audit Repair 4 fixed those and was re-audited directly as Audit 5, which found F-05's fix incomplete plus 2 narrower governance gaps. Audit Repair 5 fixed Audit 5's F-05 finding with an `os.fstat`-then-retry approach and corrected the governance gaps; that repair was re-audited directly as Audit 6, which found the retry approach itself unsafe, plus 2 further governance corrections needed. Audit 6's findings have now been fixed and tested locally, again left as uncommitted working-tree changes for Codex to audit directly.

### What happens next

Audit 7 has completed with PASS WITH FINDINGS: F-05 is closed, while F-06 and R-02 remain; current local Repair 7 addresses F-06/R-02, and independent Audit 8 is next. Codex does not need these changes pushed or opened as a PR to review them — Audits 4, 5, 6, and 7 already reviewed a local, uncommitted diff directly. If Audit 8 accepts the changes, a maintainer commits, pushes, and opens a PR through the normal workflow (not performed by this instruction) — that PR's own CI run would then be the first actual CI evidence for this and the prior local rounds, which does not exist yet.

### Founder action or decision

None required by this record itself (no PR exists to merge). Separately, truthful founder-preview status (below) remains **pending** across all seven rounds — no human has visually confirmed a Safe-PPT-Engine-generated `.pptx` renders correctly in real PowerPoint. That gate is not affected by this round's fixes and is not marked complete here.

### Recommended option and reason

Have Codex independently re-audit the current local Repair 7 changes (Audit 8). Separately, and lower priority, arrange a founder/human preview of at least one generated output in real PowerPoint before the engine is relied upon for actual Bridge4PS deck edits.

## Technical evidence

### Change verified

Safe PPT Engine Build 1, Build 2, Audit Repair 1 (F-01–F-08), Audit Repair 2 (F-02, F-04, F-05, F-06, R-01, R-02), Audit Repair 3 (F-05, F-06, R-01, R-02 from Audit 3), Audit Repair 4 (F-05, F-06, R-02 from Audit 4; R-01 confirmed closed), Audit Repair 5 (F-05, F-06, R-02 from Audit 5 — F-05's fix later found unsafe by Audit 6, see below), Audit Repair 6 (F-05, F-06, R-02 from Audit 6 — Audit 7 confirmed F-05 closed, F-06 and R-02 remaining), and — as local, uncommitted changes only — the fixes for Audit 7's findings (F-06: corrected the stale `docs/DECISIONS.md` chronology heading; R-02: strengthened the fd-reuse regression to assert the reused fd number explicitly, rather than assuming it; no engine-code change, since the strengthened test did not expose a defect) — all in `baseline/B4PS-TUT-main/.b4ps-tools/lib/ppt_engine.py`, `b4ps.py`, and this change's `openspec/changes/safe-ppt-engine/` records.

### Classification

See `spec.md` → "Classification" for the canonical record (base tier, rationale, applicable profiles, audit requirement), per `docs/TESTING.md` → "Canonical recording surface". Summary: **Standard** base tier, **Data-sensitive** profile applies, **UI-sensitive** does not apply, independent Codex audit explicitly required and performed seven times, including four times (Audits 4, 5, 6, 7) directly against a local, uncommitted diff rather than only against pushed/merged commits. **This classification was recorded retroactively** (after Builds 1–2 were already implemented and merged, prompted by finding F-06 in Audit 1) rather than before implementation as `docs/TESTING.md` intends — see `spec.md`'s "Process deviation" note. This is disclosed as a deviation from normal process, not presented as though classification happened at the correct time.

### Builder review

Performed by the implementing session at each stage: manual reproduction of each Codex finding against the pre-fix code before writing a fix; a full diff review for scope creep; and, this round specifically, deliberately reproducing the exact defect Audit 6 flagged (temporarily reinstating the removed `fstat`/retry block and re-running the new regression tests, which fail against it — see "Checks passed" below) to confirm the fix genuinely addresses what was found, not just plausibly related to it; and re-reading every governance-record sentence claiming Audit 5 "confirmed" Repair 4's F-06/R-02 fixes closed, or describing Repair 5's retry strategy as safe, to remove both classes of claim rather than merely add a caveat next to them. This is builder-side review only — it does not substitute for independent Codex audit.

### Environment

Python 3.14, `pytest` 9.1.1, dependencies from `requirements-dev.txt` (`Pillow`, `numpy`, `opencv-python-headless`, `python-pptx`, `pytest`) installed into an isolated virtualenv. macOS (Darwin), local filesystem (case-sensitive APFS volume).

### Commands executed

```bash
python -m py_compile lib/ppt_engine.py b4ps.py tests/*.py
python -m pytest tests/ -v
python -m pytest tests/test_ppt_engine_audit_3.py -k close -v   # targeted fd-reuse/close-error tests
python scripts/check_pipeline.py   # run from repository root
shasum -a 256 baseline/source-artifacts/B4PS-TUT-main.zip
```

### Checks passed

- `python -m pytest tests/` → **206 passed** (Build 1: 37; Build 2: +35 = 72; Audit Repair 1: +48 = 120; Audit Repair 2: +65 = 185; Audit Repair 3: +19 = 204; Audit Repair 4: +1 = 205; Audit Repair 5: +0 (one test strengthened in place) = 205; Audit Repair 6: +1 = 206 — the one test Repair 5 had rewritten is split into two: a same-fd no-retouch regression and an adversarial fd-reuse regression).
- All other pre-existing tests pass **unmodified**. `test_f05_create_working_copy_os_close_failure_typed_and_no_leak` (Repair 5's version, which proved a retry occurred and that `os.fstat` eventually failed - not that the fd being retried was still safely the engine's own) is replaced by `test_f05_create_working_copy_os_close_failure_typed_and_never_retouches_fd` (proves `os.close`/`os.fstat` are never called on the failed fd a second time at all) and `test_f05_create_working_copy_close_failure_does_not_touch_reused_fd` (lets a real, unrelated file genuinely reuse the exact freed fd number after the close failure, and proves the engine never closes or probes it).
- Targeted fd-reuse/close-error tests: `pytest tests/test_ppt_engine_audit_3.py -k close` → **2 passed**.
- `python scripts/check_pipeline.py` → `Bridge4PS target-repository pipeline-adoption checks passed.`
- Canonical archive `baseline/source-artifacts/B4PS-TUT-main.zip` SHA-256 confirmed unchanged (`00f5e41f475b8205535481da11f73c4e4f0bd614e0d3b1efff938e921b9eb6ee`) before and after this round's changes.
- Manual reproduction confirmed Audit 6's finding was real: temporarily reinstating the `fstat`/retry block and re-running both new tests fails them - the no-retouch test fails because a second `close`/`fstat` call is observed, and the fd-reuse test fails the same way while additionally showing the retry sequence would have probed and closed a descriptor now owned by an unrelated file, proving the tests are genuine regressions, not tautologies.

### Checks failed

None outstanding in this repository's own local test suite as of this report. (Historical: all six Codex audits are "failures" this report exists to record truthfully — see `audit-report.md`.)

### Pipeline / CI evidence

- **Local**: `python scripts/check_pipeline.py` passes (see above). This is the only CI-equivalent evidence available for *this round's changes*, because they are local and uncommitted — there is no PR and therefore no GitHub Actions run for them. This is a statement about CI evidence specifically, not about auditability — Codex's own independent review does not require a push (see Audits 4, 5, 6, and 7, which each reviewed exactly this kind of local diff).
- **Actual recorded CI result for the last pushed round (Audit Repair 2, PR #7)**: the GitHub Actions `validate` check (`.github/workflows/pipeline-checks.yml`) **passed** — confirmed via `gh pr checks 7` (`validate  pass`) and again on the merge commit `69bb4761921ac7f7b843beb04ab255a2b272865e` (`gh run list` → `completed success`).

### Founder-preview requirement

Per `docs/TESTING.md`, Standard-tier changes require "founder usability testing" as part of required evidence. **Status: PENDING — genuinely open, not waived, unchanged by this round.** No human has opened a Safe-PPT-Engine-generated `.pptx` in real PowerPoint (or any real presentation viewer) to visually confirm a mutation looks correct; all verification here is programmatic (reopen-and-check-attributes via python-pptx). Recorded truthfully as an open gate, not fabricated as complete.

### Profile-specific gates (Data-sensitive)

| Required evidence | Status | Detail |
|---|---|---|
| Migration test | N/A | No database or schema is involved; the "migration" here is a whole-file rewrite, not a schema migration. No approving authority reviewed this determination — it is a factual scope statement, not an approval, and is not labeled as one. |
| Data-preservation check | Complete | Source-hash-unchanged verified immediately before publication (the one gate, per R-01's fix — no post-publication re-check remains, confirmed closed by Audit 4); adversarial symlink/alias tests (F-01); dedicated tests per mutation family, including source-deletion-at-the-integrity-boundary and, this round, the fd-reuse-safety regression for the `os.close` failure path. |
| Tenancy-isolation check | N/A | This is a single-process local-file library with no multi-tenant concept; there is no tenant boundary to isolate. No approving authority reviewed this determination — it is a factual scope statement, not an approval, and is not labeled as one. |
| Rollback plan | Complete | The engine never writes in place — the original input file is never the write target of any operation (enforced by `_assert_safe_output_path`). "Rollback" for a mutation is simply: the original file was never touched, so no rollback action is needed on the source; for the *generated output*, discarding it is the rollback. |

### Files changed

Local, uncommitted working-tree changes only (see `git status --short` in the required return): `lib/ppt_engine.py`, `tests/test_ppt_engine_audit_3.py`, `docs/CURRENT.md`, `docs/DECISIONS.md`, `openspec/changes/safe-ppt-engine/spec.md`, `openspec/changes/safe-ppt-engine/audit-report.md`, this file.

### Remaining uncertainty

- Audit 7 completed with PASS WITH FINDINGS; F-05 is closed, F-06 and R-02 remain, and current local Repair 7 addresses those findings. It does not require these changes to be pushed first — Audits 4, 5, 6, and 7 already reviewed a local, uncommitted diff directly — and Audit 8 is the next independent re-audit before integration.
- Founder/human preview of generated output in real PowerPoint has not been performed across any round (see above — genuinely pending).
- The 8 historically-unavailable Git LFS production assets remain unresolved and were not needed by any test here.
- The atomic no-overwrite publish path (`os.link`) has not been exercised against non-POSIX or non-hardlink-capable filesystems (e.g. some network shares); behavior there is standard-library-dependent and not separately verified in this environment.
- `create_working_copy` no longer attempts to detect or recover a genuinely-still-open fd after a reported close failure - it accepts that descriptor state is not safely knowable from this code at that point and does not touch the fd again. This is a deliberate accuracy-over-cleverness tradeoff (see F-05 in `docs/DECISIONS.md` PROJ-014), not a claim that the fd is provably closed in every case.

### Recommended next action

Have Codex independently re-audit the current local Repair 7 governance/test changes directly (Audit 8). Do not commit, push, or merge them as part of this task. Editorial Memory and Documentation Intelligence remain not started and are out of scope until the engine clears independent audit.
