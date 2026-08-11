# Verification Report — Browser Verification Pilot, Engineering Slice 1 (+ Repair Rounds 1–2)

## Founder summary

### Where things stand

Engineering Slice 1 (a bounded browser observation → Editorial Memory Evidence bridge) was implemented locally. Audit 1 returned **FAIL** with 4 findings, fixed as local Repair Round 1. Closure Audit 2 also returned **FAIL**, with 3 further findings against Repair Round 1's own fix, fixed as local Repair Round 2, recorded in this same change. Not committed, pushed, or opened as a PR — left as working-tree changes per explicit task instruction.

### Why this matters

Browser Verification cannot become a routine Editorial Memory evidence source until it clears the founder-locked pilot adoption gate ([[Browser Verification Pilot Requirement]]), which requires both an AI-understanding pass (three pilot tests already run against the live app) and an engineering pass (this change) — and, for the engineering pass specifically, a passing audit, which has not yet occurred (two rounds so far, both FAIL).

### What has already happened

`editorial-memory/lib/browser_evidence.py` and `editorial-memory/tests/test_browser_evidence.py` were written, then hardened twice: Repair Round 1 against 4 Audit 1 findings, Repair Round 2 against 3 Closure Audit 2 findings. 341 tests pass in the full `editorial-memory` suite.

### What happens next

A further closure audit of this local diff — the initial implementation, Repair Round 1, and Repair Round 2 together.

### Founder action or decision

None required by this record itself — no PR exists to merge. Treat this local diff as implementer-verified, not independently verified, until a closure audit passes.

### Recommended option and reason

Commission the next closure audit of this local diff before any commit/push/PR/merge, matching how every prior Editorial Memory slice/repair in this repository was handled. Do not treat this change as complete or PASS in the meantime.

## Technical evidence

### Change verified

- New module `editorial-memory/lib/browser_evidence.py`: `BrowserObservation` dataclass, `to_notes`/`from_notes` (strict, deterministic JSON encoding/decoding), `record_browser_observation`, `get_browser_observation`.
- Two new typed errors in `errors.py`: `InvalidBrowserObservationError`, `MalformedBrowserObservationError`.
- `__init__.py` exports the three new public names and two new errors.
- **Repair Round 1 changes**: `from_notes` rewritten for exact key-set matching, strict `schema` type check (`type(...) is int`, excluding `bool`), and a new `_require_json_str_list` helper rejecting non-list/empty/non-string-entry values before any coercion; `record_browser_observation` rewritten to use a new `_require_ordered_str_sequence` helper (rejects `str`/`bytes`/`set`/`frozenset`/non-iterable/non-string-entries) for `direct_observations`/`inferences`/`unknowns` *and* `verification_scope`, plus an explicit `isinstance(evidence_quality, EvidenceQuality)` check.
- **Repair Round 2 changes**: `from_notes`'s `json.loads` call now passes a custom `object_pairs_hook` (`_strict_object_pairs_hook`) that rejects any duplicate JSON object key, at any nesting level, instead of Python's default silent last-value-wins behavior; and a custom `parse_int` hook (`_strict_parse_int`) that enforces a fixed, version-independent digit-count bound (`_MAX_JSON_INT_DIGITS = 18`) on every integer literal in the document before `int()` is ever called on it, so an oversized literal (e.g. 5000 digits) can never reach Python's own version-varying int-string-conversion guard and raise a raw `ValueError`. The caught-exception set around `json.loads` was broadened from `(TypeError, json.JSONDecodeError)` to `(TypeError, ValueError)` (a superset, since `JSONDecodeError` is itself a `ValueError` subclass) as defense-in-depth; both new hooks raise `MalformedBrowserObservationError` directly, which `json.loads` propagates unwrapped, so it is never caught and re-wrapped by that clause.
- `models.py`, `store.py`, `memory.py`'s `record_evidence`, `purge.py`, `review.py`, `retrieval.py`: confirmed unmodified across both repair rounds (`git diff --stat` shows only `errors.py`, `__init__.py`, the new `browser_evidence.py`, and the new test file).

### Classification

**Standard** base tier, no specialized profile applicable (see `spec.md` → Classification). Two audit rounds so far, both **FAIL**: Audit 1 found 4 findings (Repair Round 1); Closure Audit 2 found 3 findings (Repair Round 2, this record).

### Builder review

Genuine-regression proof performed inline for both rounds (not via a formal revert-and-rerun cycle, since this is a local-only change with no prior committed baseline to diff against): pre-fix behavior for each strictness bug was independently reproduced by isolated, throwaway Python snippets (not the real module) before its corresponding fix was written.

**Round 1**: `tuple("visual")` silently character-splits into `('v','i','s','u','a','l')`; `tuple(12345)` raises a raw, untyped `TypeError`; `True != 1` evaluates `False` in Python (so a pre-fix `!=`-based schema check would have silently accepted a boolean `schema`); a subset-based key check silently ignores an extra, unapproved key.

**Round 2**: `json.loads('{"workflow":"a","workflow":"b"}')` returns `{'workflow': 'b'}` — the duplicate key is silently resolved to the last value, not rejected; `json.loads('{"schema":' + '9'*5000 + '}')` raises a raw `ValueError: Exceeds the limit (4300 digits) for integer string conversion...` directly from the decoder, before any of this module's own code runs.

All findings from both rounds are exactly the classes of defect their corresponding new tests now cover and would fail without the fix.

### Environment

Local `python3 -m venv .venv` inside `editorial-memory/`, `pip install pytest`, run against the working tree. Removed after verification (never committed).

### Commands executed

```
cd editorial-memory && python3 -m venv .venv && .venv/bin/pip install -q pytest
.venv/bin/python -m pytest tests/test_browser_evidence.py -v
.venv/bin/python -m pytest tests/ -q
cd .. && python3 scripts/check_pipeline.py
python3 -m py_compile editorial-memory/lib/*.py editorial-memory/tests/*.py
git diff --check
rm -rf editorial-memory/.venv
```

### Checks passed

- `pytest tests/test_browser_evidence.py -v` → 74/74 passed (22 from the initial implementation, 41 from Repair Round 1, 11 from Repair Round 2).
- `pytest tests/` (full suite) → 341/341 passed, zero pre-existing tests modified across either round.
- `python scripts/check_pipeline.py` → "Bridge4PS target-repository pipeline-adoption checks passed."
- `py_compile` on all `editorial-memory/lib/*.py` and `editorial-memory/tests/*.py` → clean.
- `git diff --check` → exit 0 (no whitespace errors).
- `git status`/`git diff --stat` → diff limited to `editorial-memory/lib/browser_evidence.py` (new), `editorial-memory/lib/errors.py`, `editorial-memory/lib/__init__.py`, `editorial-memory/tests/test_browser_evidence.py` (new), plus this change's three governance files, `docs/CURRENT.md`, and `docs/DECISIONS.md`.

### Checks failed

None (against the fixed code). The audit itself returned FAIL twice, against the pre-fix code each time — see `audit-report.md` → Verdict.

### Pipeline / CI evidence

No CI run exists for this change — it has not been pushed. `python scripts/check_pipeline.py`'s local pass is the only pipeline evidence available at this stage, consistent with how every prior local-only Editorial Memory round in this repository was verified before its own eventual commit.

### Founder-preview requirement

Not applicable — no user-facing surface exists in this change; it is a pure data-layer bridge with no UI of its own.

### Profile-specific gates

Not applicable — Classification (`spec.md`) determined no Data-sensitive or UI-sensitive profile applies to this change (no destructive-write path, no UI).

### Files changed

- `editorial-memory/lib/browser_evidence.py` (new, modified again in Repair Round 2)
- `editorial-memory/lib/errors.py` (2 new error classes, Repair Round 1 only)
- `editorial-memory/lib/__init__.py` (exports, Repair Round 1 only)
- `editorial-memory/tests/test_browser_evidence.py` (new, 74 tests total)
- `openspec/changes/browser-verification-pilot-engineering-slice-1/{spec.md, verification-report.md, audit-report.md}` (this change's own governance record set, updated again in Repair Round 2)
- `docs/DECISIONS.md` (`PROJ-028`, updated again in Repair Round 2)
- `docs/CURRENT.md` (one corrected line — see `spec.md` → Repair Round 1 finding 4; no other line touched by either round)

### Remaining uncertainty

An independent closure audit of this local diff (both repair rounds combined) has not yet occurred. Whether the encoding choice (deterministic sorted-key JSON inside `Evidence.notes`, rather than a new `Evidence` field) is the right long-term shape remains an implementer judgment call, flagged in the original implementation's own report and not independently reviewed by either repair round — both rounds only strengthen validation strictness and governance accuracy around that existing encoding choice; neither revisits the choice itself.

### Recommended next action

A further independent closure audit of this local diff (the initial implementation, Repair Round 1, and Repair Round 2 together), per this repository's established convention. Do not commit, push, or merge, and do not treat this change as PASS or complete, until that audit occurs.
