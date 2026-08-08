# Independent Audit Report — Editorial Memory

This file records the history of independent Codex audits of Editorial Memory, as required by `docs/PIPELINE.md` ("independent audit findings → `audit-report.md`"). **This document is a truthful record of past audit results, not an audit performed by Claude.** Claude cannot self-certify closure of an independent audit finding — only Codex's own re-audit can.

## Founder summary

### Where things stand

Editorial Memory Slice 1 has been merged and independently audited twice by Codex. Audit 1 found three real defects: `get_current()` could return a state whose Evidence provenance was missing or corrupt (EM-01); natural-key slugging could silently collide two distinct subjects into one `KnowledgeItem` (EM-02); and `feature_area` was not validated as a safe path segment, allowing path traversal/escape outside the configured memory root (EM-03). Those, plus a related JSON-corruption-normalization gap, were fixed locally as Repair 1. Audit 2 re-audited that local diff and returned **PASS WITH FINDINGS**: EM-01, EM-02, and EM-03 are confirmed closed, but a new, narrower finding — EM-04, the analogous unvalidated-path pattern in `evidence_id` handling — was raised. EM-04 has now been fixed **locally only** as Repair 2 — not committed, pushed, or opened as a PR, per explicit instruction, so Codex can audit the repaired tree directly before anything is integrated.

### Why this matters

Editorial Memory's core guarantee (evidence never auto-promotes into approved knowledge, history is never silently destroyed) is exactly the kind of claim that should not rest on the implementer's own tests alone. Audit 1 finding three real defects on the very first independent pass, and Audit 2 finding a fourth on the very next one — including two (EM-03, EM-04) that are genuine security-adjacent boundary violations, not just lifecycle-logic gaps — confirms that independent audit here is doing real work, the same way it did across all seven rounds of the Safe PPT Engine's own history.

### What has already happened

Slice 1 was implemented, tested, merged, and independently audited (Audit 1), which found EM-01/EM-02/EM-03; those were fixed as Repair 1. Repair 1 was independently re-audited (Audit 2), which confirmed EM-01/EM-02/EM-03 closed and raised EM-04; EM-04 has now been fixed as Repair 2, as local, uncommitted working-tree changes (see `verification-report.md`).

### What happens next

Codex re-audits this local diff (Audit 3). Not performed as part of this task — this task explicitly stops after local repair, without committing, pushing, or opening a PR.

### Founder action or decision

None required by this record itself. Founder should treat this round's fixes as implementer-verified, not independently verified, until Audit 3 happens.

### Recommended option and reason

Commission an independent Codex re-audit of this local diff (Audit 3) before it is committed, pushed, or merged, and before Slice 2 begins.

## Technical evidence

### Verdict

| Round | Scope audited | Verdict |
|---|---|---|
| Audit 1 | Editorial Memory Slice 1 (implementation commit `f2643a7bf42d9af5e8556986fa982e94997d88de`, PR #9, merged to `main` as `93e87239ea9b55185f374f1a3aa2a390be03c24f`) | **FAIL** — 3 findings (EM-01, EM-02, EM-03), plus a related JSON-corruption-normalization gap noted in the same pass |
| Audit 2 | Local, uncommitted Repair 1 diff (fixes for EM-01, EM-02, EM-03, and the JSON-corruption gap) | **PASS WITH FINDINGS** — EM-01/EM-02/EM-03 confirmed closed; 1 new finding (EM-04, unvalidated `evidence_id` path handling) |
| Audit 3 | Local, uncommitted Repair 2 diff (fix for EM-04) | **NOT YET PERFORMED** |

### Specification reviewed

`openspec/changes/editorial-memory/spec.md` and `docs/EDITORIAL_MEMORY_IMPLEMENTATION_AUDIT.md` — both committed as part of the merged Slice 1 change.

### Diff and files reviewed

Audit 1: `editorial-memory/lib/{memory,store,models,errors}.py` and `editorial-memory/tests/test_editorial_memory.py` as merged (`93e87239ea9b55185f374f1a3aa2a390be03c24f`). Audit 2: the local, uncommitted Repair 1 diff described in `verification-report.md` (same files, plus `docs/CURRENT.md`, `docs/DECISIONS.md`, and the `openspec/changes/editorial-memory/*.md` records). Audit 3: not yet performed; would review the local, uncommitted Repair 2 diff (`editorial-memory/lib/{errors,store}.py`, `editorial-memory/lib/__init__.py`, `editorial-memory/tests/test_editorial_memory.py`, and this round's governance-doc updates).

### Security and privacy findings

Audit 1: EM-03 (path traversal / escape via an unvalidated `feature_area` value used directly as a filesystem path component) is the one finding in that round with genuine security relevance — a caller-supplied string could otherwise cause reads or writes outside the configured memory root. Fixed by validating `feature_area` against a safe `<platform>.<feature>` pattern before it is ever used as a path segment, plus a defense-in-depth containment check that resolves the final path and confirms it stays inside the configured knowledge directory even if a symlink were somehow present.

Audit 2: EM-04 — the same class of finding, in the sibling `evidence_id` path-construction code (`store._evidence_path()`), which Repair 1 had already flagged in its own verification report as a known, narrower, not-yet-fixed limitation. A caller-supplied `evidence_id`, or one read back out of a persisted (and potentially tampered) `KnowledgeState.evidence_refs` entry, could otherwise cause reads outside the configured memory root. Fixed the same way as EM-03: a safe-token allowlist (`store.validate_evidence_id`) plus the same defense-in-depth resolved-path containment check, applied in `_evidence_path()` so every evidence read/write goes through it.

### Regression findings

Audit 2: all 49 tests from the post-Repair-1 suite (26 original Slice 1 tests + 23 Audit-1-driven adversarial tests) continue to pass unmodified after the EM-04 fix. No regression introduced.

### Test-quality findings

Audit 1's findings drove 23 new adversarial tests covering exactly the residual cases found: a deleted/corrupted evidence file behind a `current` state (EM-01), colliding natural keys in both creation orders and across a simulated process reload (EM-02), a parametrized set of path-traversal `feature_area` values plus a check that a rejected call never touches disk outside the root (EM-03), and corrupt/truncated JSON for both `Evidence` and `KnowledgeItem` records. Two of the EM-01 tests were confirmed to fail against the pre-fix `get_current()` logic (not merely against missing symbols), establishing they are genuine regressions.

Audit 2's EM-04 finding drove 10 new adversarial tests: a 6-value parametrized path-traversal/escape matrix for `evidence_id`, a check that a rejected call touches no file outside the root, a regression guard proving a real generated evidence id still works, a test proving a persisted malicious `evidence_refs` entry is caught via `get_current` (chaining `InvalidEvidenceIdError` under `CorruptProvenanceError`), and a reload test. All 9 negative-path tests were confirmed to fail against the pre-fix `_evidence_path()` specifically before being accepted.

### Remaining uncertainty

Whether this second repair fully satisfies an independent auditor is, by definition, not something this record can establish — that is what Audit 3 exists to determine. It has not been commissioned as part of this task.

### Recommended next action

Commission an independent Codex audit of the local, uncommitted Repair 2 diff (Audit 3) before it is committed, pushed, or merged, and before Editorial Memory Slice 2 begins.
