# Independent Audit Report — Browser Verification Pilot, Engineering Slice 1

## Founder summary

### Where things stand

Two audit rounds have occurred against this change so far, both **FAIL**: Audit 1 found 4 findings (fixed as local Repair 1); Closure Audit 2 found 3 further findings against Repair 1's own fix (fixed as local Repair 2, recorded in this same change). The next closure audit is pending — this change has not yet passed an independent audit.

### Why this matters

This change is one half of the Browser Verification Pilot adoption gate. Until a closure audit returns a clean pass, this diff must be treated as implementer-verified only, not independently verified — and the pilot's adoption gate remains uncleared regardless.

### What has already happened

Audit 1: FAIL, 4 findings, fixed as local Repair 1. Closure Audit 2: FAIL, 3 findings against Repair 1's fix, fixed as local Repair 2.

### What happens next

A further closure audit of the local diff (the initial implementation, Repair 1, and Repair 2 together).

### Founder action or decision

None required by this record itself.

### Recommended option and reason

Commission the next closure audit before any commit/push/PR/merge, matching this repository's established convention for every prior Editorial Memory round. Do not treat this change as PASS or complete until a closure audit says so.

## Technical evidence

### Verdict

**FAIL** (Audit 1) → local Repair 1 → **FAIL** (Closure Audit 2) → local Repair 2 → next closure audit pending. This change has not yet received a passing audit verdict.

### Specification reviewed

`openspec/changes/browser-verification-pilot-engineering-slice-1/spec.md` (this change), against `editorial-memory/lib/browser_evidence.py` and `editorial-memory/tests/test_browser_evidence.py`, on top of merged Editorial Memory Slices 1–7 (`main` at `31a5ae1e725c3377f2510dc38c8d85c883286224`).

### Findings and resolutions — Audit 1 (FAIL)

| Finding | Issue | Resolution |
|---|---|---|
| 1. Strict persisted notes parsing | `BrowserObservation.from_notes()` accepted extra/unexpected keys (subset check, not exact match); compared `schema` with `!=` (a boolean `schema` value would have silently passed, since `True == 1` in Python); called `tuple(...)` on `direct_observations`/`inferences`/`unknowns` without checking they were JSON arrays first — a persisted string would have been silently character-split; did not validate `direct_observations` was non-empty, or that `workflow`/`uncertainty` were strings. | Exact key-set equality (`set(payload.keys()) != _REQUIRED_NOTES_KEYS`); `type(schema) is not int or schema != 1` (excludes `bool` by type); new `_require_json_str_list` helper enforces list-type, non-empty (for `direct_observations`), and non-blank-string entries before any `tuple()` call; explicit `isinstance` checks added for `workflow`/`uncertainty`. |
| 2. Strict write boundary | `record_browser_observation`'s helper called `tuple(value)` directly — a bare string was silently character-split, a non-iterable value raised a raw `TypeError`, and a `set`/`frozenset` produced nondeterministic order; `verification_scope` received no validation of its own before reaching the existing `record_evidence`; `evidence_quality` was never type-checked. | New `_require_ordered_str_sequence` helper explicitly rejects `str`/`bytes`, explicitly rejects `set`/`frozenset`, requires `list`/`tuple`, validates every entry — applied to `direct_observations`/`inferences`/`unknowns`/`verification_scope`; `evidence_quality` now checked via `isinstance(evidence_quality, EvidenceQuality)`. |
| 3. Regression coverage | No tests existed for any of the malformed shapes in findings 1–2, and no test proved `captured_at` round-trips. | 41 new tests added (22 → 63 total in `test_browser_evidence.py`): every malformed shape named in findings 1–2 on both boundaries, an explicit `captured_at`-present and `captured_at`-omitted round-trip test, and a deterministic-ordering proof. |
| 4. Canonical governance records | This change had no `openspec/changes/` classification/verification/audit record set, and `docs/CURRENT.md`/`docs/DECISIONS.md` did not reflect this change's existence at all. | `spec.md`, `verification-report.md`, `audit-report.md` added; `docs/DECISIONS.md` gained `PROJ-028`; `docs/CURRENT.md`'s one stale line about a `browser_observation` producer not existing was corrected. |

### Findings and resolutions — Closure Audit 2 (FAIL)

Repair 1's own fix for finding 1 (strict persisted notes parsing) was itself found insufficiently strict against two further malformed-JSON shapes, plus a governance-chronology misstatement in this record's own prior verdict:

| Finding | Issue | Resolution |
|---|---|---|
| 1. Duplicate JSON keys | `BrowserObservation.from_notes()` used plain `json.loads(notes)`, which silently accepts a JSON object containing a duplicate member name and keeps only the last-seen value (Python's default `json` behavior) — e.g. two `"workflow"` keys would silently resolve to the second value, never rejected. | `json.loads` is now called with a custom `object_pairs_hook` (`_strict_object_pairs_hook`) that raises typed `MalformedBrowserObservationError` the instant a duplicate key is seen, at any nesting level, before the payload is ever handed back to the caller. |
| 2. Oversized JSON integer raw `ValueError` | A JSON integer literal with an extreme digit count (e.g. a 5000-digit `schema` value) would reach Python's own int-string-conversion guard *inside* `json.loads` itself, raising a raw `ValueError` — before this module's own `try`/`except` around `json.loads` even had a chance to distinguish it from a genuine parse failure, since that guard's threshold varies by Python version and is process-configurable (including disable-able). | `json.loads` is now also called with a custom `parse_int` hook (`_strict_parse_int`) that checks a fixed, version-independent digit-count bound (`_MAX_JSON_INT_DIGITS = 18`) *before* ever calling `int()` on the literal's text, raising typed `MalformedBrowserObservationError` deterministically regardless of Python version/configuration. Applies to every integer literal in the document, not only `schema`. |
| 3. Governance chronology | This record's own prior verdict misstated Audit 1 as **PASS WITH FINDINGS** rather than **FAIL** — a materially different verdict since "PASS WITH FINDINGS" implies the underlying implementation was basically sound with isolated gaps, while the founder's actual chronology records Audit 1 as a **FAIL** verdict. | This file rewritten throughout to state the verdict chronology accurately: Audit 1 FAIL → Repair 1 → Closure Audit 2 FAIL → Repair 2 → next closure audit pending. `docs/DECISIONS.md` (`PROJ-028`) and `docs/CURRENT.md` corrected to match. `spec.md`/`verification-report.md` reviewed and left as-is where their own wording was already verdict-neutral (they describe findings/fixes, not a PASS/FAIL verdict of their own) — see "Governance chronology" note below. |

### Test-quality findings

None against the 63 tests from Repair 1 — Closure Audit 2's findings were both implementation-strictness gaps in `from_notes`'s JSON-decode boundary itself, not test weaknesses, plus one governance-record accuracy issue. No pre-existing test was weakened by Repair 2; all 11 new tests are additive (63 → 74).

### Regression proof

Each of the 11 new Repair 2 tests targets exactly one malformed shape (duplicate `workflow` key specifically, duplicate keys at other positions, a 5000-digit `schema` integer through both `from_notes()` and `get_browser_observation()`, and combined no-raw-exception proofs) or a valid-input-still-works sanity check. Both underlying bugs were independently confirmed as real before the fix: plain `json.loads` on a payload with a duplicate `"workflow"` key returns a dict with only the last value (`{'workflow': 'b'}` for `{"workflow":"a","workflow":"b"}`); plain `json.loads` on a 5000-digit integer literal raises `ValueError: Exceeds the limit (4300 digits) for integer string conversion` directly from the decoder, confirming both were genuine, reproducible defects, not hypothetical.

## Explicit non-goals for this round

No architecture redesign; no changes to `models.py`/`store.py`/`memory.py`'s `record_evidence`/`purge.py`/`review.py`/`retrieval.py` (all confirmed unmodified by `git diff --stat`); no Browser Verification automation/orchestration framework; no Documentation Intelligence; no change to the underlying `Evidence.notes`-as-JSON encoding choice itself (only its decode-boundary strictness); no declaration that the Browser Verification Pilot adoption gate is cleared, or that this change has PASSed an audit.
