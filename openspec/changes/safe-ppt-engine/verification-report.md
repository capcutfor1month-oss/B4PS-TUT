# Verification Report — Safe PPT Engine (Builds 1–2, Audit Repair 1)

## Founder summary

### Where things stand

The Safe PPT Engine's mechanical read/inspect/mutate primitives (Build 1: `set_shape_text`; Build 2: `move_shape`, `resize_shape`, `set_shape_geometry`, `replace_picture`) passed their own implementation test suites when built, but this record was not created at the time — `docs/TESTING.md` requires every change to record its risk classification and canonical verification evidence, and Builds 1 and 2 were marked complete in `docs/CURRENT.md`/`docs/DECISIONS.md` without that recordkeeping. This report supplies it retroactively, truthfully, without changing what was actually built in Builds 1–2.

### Why this matters

An independent Codex audit of Builds 1–2 subsequently found 8 defects (F-01 through F-08), 1 critical and 2 high-severity, in exactly the kind of transaction-safety guarantees this engine exists to provide (source-file aliasing, publish-race conditions, error typing, stale media, and deterministic output). Builds 1 and 2 must **not** be described as having passed independent safety audit — they had not yet been audited when marked complete, and once audited, they failed with the findings below. This repair (Audit Repair 1) addresses all 8 findings in the same commit that adds this record.

### What has already happened

Repair implemented, tested, and merged. See the companion PR and `docs/DECISIONS.md` (PROJ-009) for the technical account of each fix.

### What happens next

An independent Codex re-audit of the repaired engine is the required next step before any further reliance on these transaction-safety guarantees. It is not performed by this report or by Claude.

### Founder action or decision

None required to merge this record. Founder should be aware that re-audit, not another Claude implementation milestone, is the appropriate next action per the audit-repair task's own instruction.

### Recommended option and reason

Proceed to independent re-audit before building further capability (e.g. Editorial Memory, Documentation Intelligence) on top of this engine, since those layers would inherit any residual defect in the mechanical foundation.

## Technical evidence

### Change verified

Safe PPT Engine Build 1 (`set_shape_text`), Build 2 (`move_shape`, `resize_shape`, `set_shape_geometry`, `replace_picture`), and Audit Repair 1 (fixes for Codex findings F-01–F-08) — all in `baseline/B4PS-TUT-main/.b4ps-tools/lib/ppt_engine.py` and `b4ps.py`.

### Classification

- **Base tier:** Standard (per `docs/TESTING.md`) — new engine capability, not authentication/payments/secrets/tenant-isolation/production-migration (which would be High), and not a copy-only/non-behavioural change (which would be Trivial).
- **Rationale:** This is file-handling infrastructure that mutates PowerPoint files and is explicitly designed to protect an irreplaceable source asset. Given that safety purpose, verification for this component intentionally exceeds typical Standard-tier depth — it includes adversarial/fault-injection tests (symlink aliasing, publish races, staged-copy/save/validation/publication failure injection) beyond what a normal Standard-tier feature would require, without this change actually being High tier (no auth, payment, secret, or tenant-isolation surface exists here).
- **Applicable specialized evidence profiles (per `docs/TESTING.md`):** Data-sensitive — the engine performs bulk file writes (a full `.pptx` package rewrite per mutation) and this report documents the data-preservation guarantees (source-hash-unchanged, atomic no-partial-output publication) in lieu of a database migration/rollback plan, since there is no database or migration involved. UI-sensitive: not applicable (no browser-rendered UI).
- **Independent-audit requirement:** An independent Codex audit was performed after Builds 1–2 (unplanned at merge time, but exactly the kind of scrutiny this file-safety-critical component warrants) and found F-01–F-08. Audit Repair 1 (this change) is required to close those findings. A second independent Codex re-audit of the repair is the recorded next action — not yet performed as of this report.

### Environment

Python 3.14, `pytest` 9.1.1, dependencies from `requirements-dev.txt` (`Pillow`, `numpy`, `opencv-python-headless`, `python-pptx`, `pytest`) installed into an isolated virtualenv. macOS (Darwin), local filesystem (case-sensitive APFS volume under `/private/tmp`).

### Commands executed

```bash
python -m py_compile lib/ppt_engine.py b4ps.py
python -m pytest tests/ -v
python scripts/check_pipeline.py   # run from repository root
```

### Checks passed

- `python -m pytest tests/` → all tests passed (Build 1: 37, Build 2: +35 = 72, Audit Repair 1: +48 = 120 total — see the audit-repair PR description for the exact final count).
- All pre-existing Build 1/2 tests pass unmodified except two explicitly justified changes: one error-message wording assertion (F-01 improved the message text) and the CLI JSON-shape assertions in `test_engine_cli.py`/`test_engine_cli_geometry_image.py` (F-08 separates canonical structure from source-path metadata in `engine-inspect --json` output).
- `python scripts/check_pipeline.py` → `Bridge4PS target-repository pipeline-adoption checks passed.`
- Canonical archive `baseline/source-artifacts/B4PS-TUT-main.zip` SHA-256 unchanged throughout Builds 1, 2, and this repair.
- Manual reproduction confirmed each of F-01–F-08 was real against the pre-repair code, and confirmed fixed against the repaired code (symlink-alias rejection, exclusive-create no-overwrite publish, typed `DeckSourceError` before hashing, stale-media removal verified against actual ZIP package contents, exception-safe staging, non-picture rejection before staging with no temp file created, and identical structural inspection for two byte-identical files at different paths).

### Checks failed

None outstanding as of this report. (Historical: the Codex audit that produced F-01–F-08 is the "failure" this report exists to record truthfully — see Founder summary.)

### Failure summary

Not applicable — no unresolved failing check at time of writing. See `docs/DECISIONS.md` (PROJ-009) for the full defect-by-defect repair account.

### Files changed

`lib/ppt_engine.py`, `b4ps.py`, `tests/test_ppt_engine.py` (2 assertion updates), `tests/test_engine_cli.py`, `tests/test_engine_cli_geometry_image.py`, new `tests/test_ppt_engine_audit_repair.py`, `docs/CURRENT.md`, `docs/DECISIONS.md`, this file.

### Remaining uncertainty

- Independent Codex re-audit of this repair has not been performed.
- The 8 historically-unavailable Git LFS production assets (including both production decks) remain unresolved and were not needed by any test here.
- `_publish_atomically`'s `overwrite=False` exclusive-create path has not been exercised against non-POSIX filesystems (e.g. network shares with weak `O_EXCL` guarantees); behavior there is standard-library-dependent and not separately verified in this environment.

### Recommended next action

Independent Codex re-audit of the repaired Safe PPT Engine. Editorial Memory and Documentation Intelligence remain not started and are out of scope until re-audit clears.
