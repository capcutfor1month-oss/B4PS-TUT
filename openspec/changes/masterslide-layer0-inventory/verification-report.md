# Verification Report — MasterSlide Layer 0: Deterministic Slide Inventory

## Founder summary

### Where things stand

Independent Codex Audit 5 (of Build 5) **PASSED** the entire publication-validity
design this slice has been iterating on: the publication state machine, the
whole-owned-tree commitment/digest, hard-precondition marker invalidation, same-source
mid-publication safety, normal and incomplete-rollback behavior, the source-integrity
transaction, deterministic output, rotated/flipped group geometry, grouped-title
extraction, connector validity, the empty-slide fingerprint, the staged-write
typed-error boundary, the runtime lock, working-tree scope accounting, GOV-L0-01, and
GOV-L0-02. It found three narrower, purely parser-level gaps specifically in
`is_tree_valid()`: the marker's own `schema_version` field was never actually enforced
on read (a missing, `null`, wrong-typed, or unknown/future value all still validated
`True`); invalid UTF-8 in the marker or the manifest could raise a raw
`UnicodeDecodeError`; and an oversized integer JSON token could raise a raw
`ValueError` (Python's own interpreter-level integer-string conversion limit, not a
`json.JSONDecodeError`). This record (Build 6) is a parser-only repair scoped to
exactly those three gaps in `is_tree_valid()` and the one helper it calls
(`_compute_owned_tree_digest`) — nothing else was touched. Not committed, pushed, or
opened as a PR.

### Why this matters

`is_tree_valid()` exists specifically so a consumer never has to trust a Layer 0 tree
based on "the files are present and look reasonable." That guarantee is only as strong
as the function's own robustness against input it did not itself write — a version
number nobody checks is not really a version number, and a "safe predicate" that can
still be made to raise on adversarial-but-plausible input (truncated/corrupted text,
a huge number) is not actually safe. All three gaps here are exactly that pattern:
each was already caught somewhere else in the design (a mismatched digest would
eventually catch a tampered marker too), but "eventually catch it, after crashing" is
not the same guarantee as "always return a clean `False`."

### What has already happened

`is_tree_valid()` now requires an exact `schema_version` match against a single named
constant (`_MARKER_SCHEMA_VERSION`), and both JSON read sites (`_committed.json` in
`is_tree_valid()`, `manifest.json` in `_compute_owned_tree_digest()`) now catch
`UnicodeDecodeError` around the text read and `ValueError` around the `json.loads`
call, each scoped narrowly to just that operation. 22 new regression tests (125 total,
up from 103), empirically confirming the oversized-integer `ValueError` behavior
against this environment's actual Python interpreter before writing the fix. Full
pre-existing suites re-run and confirmed unaffected. The production inventory
regenerated against the real deck; source hash, `is_tree_valid()`, and the digest value
itself (unchanged from Build 5, confirming this round changed only validation
robustness, not the digest computation) all re-verified.

### What happens next

Independent Codex parser-closure re-audit of this repaired diff. `audit-report.md` is
intentionally not created by this record — Codex owns that stage.

### Founder action or decision

Unchanged from the prior round's correction (not re-litigated here): independent Codex
audit **PASS** is the pre-commit/integration gate for the exact audited tree; founder/
manual usability approval is a separate, later gate for release/phase-closure, and
remains genuinely **PENDING** — this record does not claim it and does not need to
before a Codex-authorized commit/push/PR.

### Recommended option and reason

Commission the Codex parser-closure re-audit. Given Audit 5 already passed the entire
design this round did not touch, a passing result here should complete this slice's
audit history.

## Technical evidence

### Parser fail-closed contract

`is_tree_valid(output_dir)` must return only `True` (complete, valid, schema-supported,
internally consistent publication) or `False` (anything else) — never raise
`UnicodeDecodeError`, `json.JSONDecodeError`/`ValueError`, `AttributeError`, `KeyError`,
or `TypeError` for expected malformed/adversarial input. Verified this round by 22 new
tests covering every category in the task's required parser matrix (marker: missing,
empty, invalid UTF-8, invalid JSON syntax, array, scalar, missing/null/wrong-type/
unsupported `schema_version`, missing/wrong-type/malformed `tree_sha256`, missing/
wrong-type `owned_file_count`, oversized integer, valid; manifest: missing, invalid
UTF-8, invalid JSON, wrong top-level shape, oversized integer, malformed Tier-B
declaration, valid) plus every pre-existing whole-tree mutation test re-run unchanged.

### Schema-version behavior

`_MARKER_SCHEMA_VERSION = "1.0.0"` is the single named constant (already existed,
already written into every marker by `_write_commit_marker`) — the gap was purely that
nothing on the read side compared against it. `is_tree_valid()` now includes
`if marker.get("schema_version") != _MARKER_SCHEMA_VERSION: return False` immediately
after confirming the marker is a JSON object, before any digest work. Verified:
missing field, `null`, an integer, an empty string, and an unrelated/future version
string (`"999.0.0"`) all return `False`; the exact current constant validates normally
(re-confirmed against a real freshly-published marker).

### UTF-8 failure behavior

Both `_committed.json` (in `is_tree_valid()`) and `manifest.json` (in
`_compute_owned_tree_digest()`) now read via a `try`/`except (OSError,
UnicodeDecodeError)` block scoped to exactly the `.read_text(encoding="utf-8")` call,
separate from the subsequent JSON-parsing `try`/`except ValueError` block. Verified:
a marker file containing raw invalid UTF-8 bytes (`\xff\xfe...`) and a manifest file
with the same — both return `False`, no exception escapes either the `is_tree_valid()`
call or, transitively, the `_compute_owned_tree_digest()` call it makes.

### Oversized-number behavior

Empirically confirmed first, in this session's own venv, that `json.loads` on a
5,000-digit integer literal raises `ValueError: Exceeds the limit (4300 digits) for
integer string conversion...` — not `json.JSONDecodeError` — under this environment's
actual Python 3.14 interpreter (the limit and its default value are CPython's own,
unmodified; this repair does not touch `sys.set_int_max_str_digits` or disable any
interpreter safety limit). Both `json.loads` call sites (marker, manifest) now catch
bare `ValueError`, which also transitively covers `json.JSONDecodeError` (itself a
`ValueError` subclass) without needing two separate except clauses. Verified: a
5,000-digit integer embedded in `owned_file_count` (marker) and in `slide_count`
(manifest) both return `False` from `is_tree_valid()`, no exception escapes.

### Commands executed

```
cd documentation-intelligence && python -m pytest tests/test_layer0.py -q
cd documentation-intelligence && python -m pytest tests -q
python -m pytest baseline/B4PS-TUT-main/.b4ps-tools/tests -q
python -m pytest editorial-memory/tests -q
python -m pytest editorial-memory/tests documentation-intelligence/tests -q          # combined
python -m pytest documentation-intelligence/tests editorial-memory/tests -q          # combined, reversed dir order
python3 -m py_compile documentation-intelligence/documentation_intelligence/*.py documentation-intelligence/tests/*.py
python3 scripts/check_pipeline.py
git diff --check
python -m documentation_intelligence.layer0 <real deck path> documentation-artifacts/masterslide/layer0
python -c "from documentation_intelligence.layer0 import is_tree_valid; print(is_tree_valid('documentation-artifacts/masterslide/layer0'))"
git status --short -uall
```

### Tests and exact counts

- Focused Layer 0 tests (`test_layer0.py`): **125/125 passed** (up from 103; +22 new,
  all in `TestParserFailClosed`).
- Full Documentation Intelligence suite: **216/216 passed**.
- Safe PPT Engine's own suite: **206/206 passed** (unaffected — not touched).
- `editorial-memory/tests` alone: **343/343 passed** (unaffected — not touched).
- Combined `editorial-memory` + `documentation-intelligence`, both directory orders:
  **559/559 passed both ways**.
- `python3 -m py_compile`: clean. `check_pipeline.py`: passed. `git diff --check`:
  clean (exit 0).
- No test failures at any point this round — every new test passed on its first
  implementation.

### Existing publication regression sanity

All 103 pre-existing `test_layer0.py` tests re-run unchanged and still passing,
including every publication-state-machine test from the prior round
(`TestPublicationValidityMarker`'s full 17-test suite: hard-precondition invalidation,
same-source mid-publication probing, the full owned-artifact mutation matrix, cross-
tree marker copying, digest determinism), `TestAtomicPublication` (ordinary and
double-fault rollback), `TestStagedWriteTypedErrors`, `TestSingleWriterLock` (including
the real two-process regression), and every closed-finding regression from earlier
rounds (source integrity, deterministic output, rotated/flipped geometry, grouped
titles, connector validity, empty-slide fingerprint). None of these needed any change
this round — they simply continue to pass against the parser-hardened
`is_tree_valid()`.

### Real-deck validation

170/170 slides, 0 unsupported structures, max group depth 4, slide 32's rotated/
flipped groups still correctly unresolved, slide 74/78 connector facts unchanged —
identical to every prior round. `is_tree_valid()` on the freshly regenerated
production tree: **True**. The marker's `tree_sha256` value
(`c8cc519b50f4db6c2fd165d9d8548d9df333ad4902dbe223c048b3827fdb15fc`) is byte-identical
to the value recorded in Build 5's own regeneration — direct confirmation that this
round changed only validation robustness, not the digest computation or the extracted
content itself.

### Source hash

`e461613baae2874eaeede3268fff1aee081c33a04a6bcbb0c7769b94bab16834` — confirmed
unchanged before and after the production regeneration this round.

### Files changed

- `documentation-intelligence/documentation_intelligence/layer0.py` (repaired: exact
  `schema_version` enforcement, `UnicodeDecodeError` handling on both JSON read sites,
  `ValueError` handling on both `json.loads` calls — all inside `is_tree_valid()` and
  `_compute_owned_tree_digest()` only)
- `documentation-intelligence/tests/test_layer0.py` (extended: 22 new tests in
  `TestParserFailClosed`)
- `documentation-artifacts/masterslide/layer0/manifest.json` (regenerated, content
  unchanged in substance)
- `documentation-artifacts/masterslide/layer0/tier_a_summary.json` (regenerated)
- `documentation-artifacts/masterslide/layer0/tier_b/slide_0000.json` … `slide_0169.json`
  (regenerated, 170 files)
- `documentation-artifacts/masterslide/layer0/structural_analysis.json` (regenerated)
- `documentation-artifacts/masterslide/layer0/_committed.json` (regenerated — same
  `tree_sha256`/`owned_file_count` as Build 5, confirming no behavioral drift in the
  digest itself)

No other file was touched this round. `documentation-intelligence/documentation_
intelligence/_safe_ppt_engine_import.py`, `.gitignore`, `mutate.py`, `locate.py`,
`compare.py`, `editorial-memory/`, and `baseline/B4PS-TUT-main/.b4ps-tools/` are
unchanged (and every prior round). The canonical source `.pptx` was opened read-only
and is unmodified (hash re-verified — see above).

### Governance update

`spec.md`'s L0-03 section gained one new subsection ("Parser fail-closed boundary")
documenting the three gaps and their fixes, plus updated audit-history lines recording
Audit 5's PASS and Build 6's scope. This report itself is a fresh Build-6 revision.
Founder-gate wording is unchanged from the prior round's correction (Codex PASS gates
commit/integration; founder approval is separate and PENDING) — not re-litigated here,
per instruction not to alter already-correct wording.

### Working-tree scope

Unchanged from the prior round's accounting: this round modified only already-tracked
paths (`layer0.py`, `test_layer0.py`, the two OpenSpec records) plus regenerated
already-accounted-for content (the `layer0/` tree's file set and count are identical to
before — only file *contents* were regenerated, none added or removed). `git status
--short -uall`: **231** entries, same three-category breakdown documented in `spec.md`.

### Residual bounded limitations

Unchanged from the prior round, carried forward without modification: `_acquire_
publish_lock` remains POSIX-only/local-only; the design is crash-safe for in-process
exceptions, not filesystem-level crash/power-loss; `_get_rotation` remains local-only
by design; no real malformed connectors/unsupported structures/marker-invalidation
failures exist in the current canonical deck (synthetic-fixture coverage only); no
consumer of `is_tree_valid()` exists yet in the repository; this repair has not yet
been independently re-audited; founder/manual approval remains genuinely PENDING.

### Recommended next action

Independent Codex parser-closure re-audit of this repaired diff, scoped to confirming
the three `is_tree_valid()` gaps are closed without any regression to the already-
PASSed design elements from Audit 5.
