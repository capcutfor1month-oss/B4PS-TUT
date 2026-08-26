# Change Specification — MasterSlide Layer 0: Deterministic Slide Inventory

Written **before** the initial implementation, per this repository's established
convention. Not a numbered Documentation Intelligence slice — a bounded foundation
piece, named directly, matching the `safe-ppt-engine` change's own non-slice-numbered
naming convention. This record has been corrected five times after independent Codex
audits: Audit 1 returned **FAIL** against Build 1 (L0-01 through L0-07, plus
SCOPE-L0-01); Audit 2 confirmed L0-01, L0-02, L0-05, L0-06, L0-07 **CLOSED** against
Build 2 and found L0-03, L0-04, SCOPE-L0-01 **PARTIAL**, plus two new governance
findings GOV-L0-01 and GOV-L0-02; Build 3 closed L0-04, GOV-L0-01, and GOV-L0-02, but
Audit 3 found L0-03 still **PARTIAL**, plus a new typed-error gap and a lock-file
commit-scope question; Build 4 closed the staged-write typing and lock-scope findings
and made a first attempt at L0-03, but Audit 4 reproduced four further concrete
failures against that attempt; Build 5 replaced the manifest-only marker with a
whole-owned-tree digest and a hard-precondition invalidation, and Audit 5 **PASSED**
the entire publication state machine, whole-tree commitment, hard-precondition
invalidation, same-source mid-publication safety, normal and incomplete-rollback
behavior, source-integrity transaction, deterministic output, rotated/flipped
geometry, grouped titles, connector validity, fingerprint, staged-write typed errors,
runtime flock, scope accounting, GOV-L0-01, and GOV-L0-02 — but found three narrower
parser/schema gaps specifically in `is_tree_valid()`: an unenforced marker
`schema_version` (missing/wrong-type/unknown values all still validated `True`), a raw
`UnicodeDecodeError` on invalid UTF-8 in the marker or manifest, and a raw `ValueError`
from Python's own oversized-integer JSON parsing limit. **This record reflects Build
6**, a parser-only repair scoped to exactly those three gaps in `is_tree_valid()` and
the one helper it calls — none of the already-PASSed design elements listed above were
touched or reopened. Not yet re-audited.

## Structural vs. visual authority (GOV-L0-01)

Stated explicitly, since Codex found it missing from both OpenSpec records:

- **PPTX/OOXML is authoritative** for every fact this slice extracts — shape structure,
  groups and hierarchy, connector bindings, geometry (local and slide-resolved), picture
  crops, text/style summaries, and every other Layer 0 fact. All of it comes directly
  from the deck's own XML, read via python-pptx and raw `lxml` element access; nothing
  is inferred from a rendered image.
- **Layer 0 does not establish visual truth.** It has no dependency on OfficeCLI or any
  other renderer — none is imported, invoked, or referenced anywhere in
  `layer0.py`. Rendered output (OfficeCLI, native PowerPoint, or a canonical PDF export)
  is never used by this slice as semantic or stylistic authority for any fact it
  produces. Establishing visual/editorial truth — via canonical PDF or native PowerPoint
  rendering — belongs entirely to a later, separate visual/editorial exploration stage
  this change does not implement and does not depend on.

## Classification

- **Base tier: Standard.** This slice adds a new, read-only reader over the canonical
  MasterSlide `.pptx` and writes new derived artifact files under
  `documentation-artifacts/masterslide/layer0/`. It performs no PPT mutation of any
  kind — no Safe PPT Engine mutation primitive is imported or called anywhere in this
  module. Not Trivial (real extraction/normalization/decomposition/publication logic,
  with adversarial regression coverage). Does not meet the High bar (no auth, payments,
  secrets, tenant isolation, or production migration).
- **Applicable specialized evidence profile: neither applies.** No user-facing UI flow;
  no schema/migration/bulk write beyond regenerable, deterministic derived JSON.
- **Independent-audit requirement**: consistent with every prior slice, an independent
  Codex audit of this local diff is the required next action before any commit/push/PR/
  merge. **Audit 1: FAIL** (L0-01, L0-02, L0-03 blockers; L0-04, L0-05, L0-06,
  SCOPE-L0-01 major; L0-07 minor), fixed as Build 2. **Audit 2: L0-01/L0-02/L0-05/L0-06/
  L0-07 CLOSED; L0-03/L0-04/SCOPE-L0-01 PARTIAL; GOV-L0-01/GOV-L0-02 new MAJOR**, fixed
  as Build 3. **Audit 3: L0-04/GOV-L0-01 confirmed CLOSED; L0-03 still PARTIAL; new
  typed-staged-write-error and lock-commit-scope findings; SCOPE-L0-01/GOV-L0-02
  accounting still imprecise**, fixed as Build 4. **Audit 4: staged-write typing/
  lock-scope/SCOPE-L0-01 confirmed CLOSED; L0-03 reproduced FAIL on four further
  concrete grounds** (silent marker-invalidation failure, a same-source mid-publication
  valid window, a marker that authenticated only the manifest, and a malformed-marker
  `AttributeError`), fixed as Build 5. **Audit 5: PASSED the entire publication state
  machine, whole-tree commitment, hard-precondition invalidation, same-source mid-
  publication safety, rollback (normal and incomplete), source-integrity transaction,
  deterministic output, rotated/flipped geometry, grouped titles, connector validity,
  fingerprint, staged-write typed errors, runtime flock, scope accounting, GOV-L0-01,
  GOV-L0-02; found 3 narrower parser/schema gaps in `is_tree_valid()` itself**
  (unenforced marker `schema_version`, raw `UnicodeDecodeError` on invalid UTF-8, raw
  `ValueError` on an oversized JSON integer), fixed as this record's Build 6. Not yet
  re-audited.

## Approved user journey

A caller has: the canonical MasterSlide `.pptx` path. This slice answers exactly one
question: "what deterministic PowerPoint structure exists in this deck, extracted once
and represented compactly enough that a later presentation-editing agent never needs to
re-parse raw OOXML for facts already captured here?" It never decides what a shape
*means*, what the deck's current editorial style is, which era a slide belongs to, or
how a slide should be edited or created — those are explicitly out of scope, deferred to
a later, separate Presentation Exploration stage this change does not implement.

## Functional requirements

- `documentation_intelligence.layer0.generate_layer0_inventory(source_deck_path,
  output_dir) -> dict` — the slice's one production entry point.

- **Source-integrity transaction (L0-01, repaired)**: the source is hashed via
  `_hash_source_or_raise()` — a typed-error-preserving wrapper around the bridge's
  `file_sha256` — **before** it is opened at all. Only then is it opened, once,
  read-only, via the Safe PPT Engine's own typed `load_deck()` (reused unmodified).
  Immediately before anything is written to disk, the source is re-hashed the same way;
  if the two hashes differ, `SourceIntegrityError` (a `DeckSourceError` subclass) is
  raised and **nothing is staged or published**. This specifically closes the case
  where a source replacement happens between the initial hash and `load_deck()` — under
  the previous (hash-after-load) ordering, such a replacement could make the manifest's
  hash describe bytes different from what was actually parsed into memory and extracted,
  with the before/after check never detecting it because both hashes reflected the
  already-replaced file. `TestSourceIntegrityTransaction` reproduces exactly this
  boundary via a monkeypatched `load_deck` that swaps the source file after parsing but
  before returning.

- **Two-tier output**:
  - **Tier A** (`extract_tier_a`) — one compact per-slide summary: counts, a
    shape-type histogram, group depth, connector/picture/freeform/hidden counts
    (including `invalid_connector_count`, new — see L0-06 below), unsupported-structure
    flags, the normalized title/topic key, and the structural fingerprint. Deliberately
    excludes any per-shape list or full text — cheap enough for the complete 170-slide
    deck to be loaded in one context.
  - **Tier B** (`extract_tier_b`) — one full per-shape detail record per slide. Written
    as one JSON file per slide under `tier_b/`, meant for lazy single-slide/small-batch
    retrieval — never bulk-loaded.

- **Connector binding, descendant search (unchanged from Build 1, still locked in
  code)**: `stCxn`/`endCxn` live under `p:nvCxnSpPr/p:cNvCxnSpPr` — a grandchild of
  `cxnSp`, not a direct child. `_connector_facts()` searches descendants (`.//a:stCxn`),
  not direct children.

- **Connector endpoint validity (L0-06, repaired)**: presence of an `stCxn`/`endCxn`
  element is no longer treated as sufficient for `bound=True`. Each endpoint now has an
  explicit `status`: `ABSENT` (no element — an ordinary unbound line, not an anomaly),
  `VALID` (present, with a well-formed non-negative integer `id` and `idx`), or
  `INVALID` (present but malformed — missing/non-numeric/negative `id` or `idx`). The
  connector's aggregate `status` is `INVALID` if *either* endpoint is malformed (even if
  the other is clean — malformed data is surfaced, never silently downgraded to a plain
  absence), else `VALID` if at least one endpoint is a well-formed binding, else
  `ABSENT`. Tier A's `bound_connector_count` counts only `status == "VALID"` connectors
  (unchanged real-deck meaning); a new `invalid_connector_count` tracks malformed ones
  separately, per Layer 0's "surface unsupported/invalid rather than silently drop"
  philosophy. `TestMalformedConnectorBindings` covers missing id, missing idx,
  non-numeric id, negative idx, valid-start-only, valid-end-only, both-valid,
  both-absent, and one-invalid-one-valid (aggregate must be `INVALID`, not `VALID`).

- **Group coordinate space and hierarchy (L0-04)**:
  - `child_ids` on a `grpSp` record lists **immediate children only** (read directly
    from one level of `shape.shapes`), not every recursively flattened descendant.
  - `local_z_order`: each shape's index among its own immediate siblings only,
    independently reset at every parent level (not a global flattened counter).
  - Geometry is honestly labelled: `local_geometry_in` is always the shape's position
    in its *immediate parent's* coordinate space (slide-absolute for a top-level shape,
    the group's own `chOff`/`chExt` child space for a grouped shape). `resolved_geometry_in`
    is the slide-absolute position, computed by applying each ancestor group's affine
    transform (`off`/`ext`/`chOff`/`chExt`, pure OOXML arithmetic, no semantic
    inference) from the immediate parent outward; it is `None` — never invented — the
    moment any ancestor's transform is missing or degenerate (zero child-extent). For a
    top-level shape, `resolved_geometry_in` trivially equals `local_geometry_in`.
  - **Rotated/flipped ancestor groups (Build 3, closes the Audit-2 PARTIAL finding)**:
    Codex confirmed real canonical groups (slide index 32, groups 1255/1259/1263) carry
    `rot="10800000" flipH="1"` on their own `p:grpSpPr/a:xfrm`. `_group_transform()` now
    reads `rot`/`flipH`/`flipV` from that same `xfrm` and returns `None` — the whole
    transform, not an approximation — whenever any of the three is non-default. Since
    `_resolve_geometry_chain()` already treats any `None` entry in the ancestor
    transform stack as unresolvable, this correctly poisons `resolved_geometry_in` for
    every descendant of a rotated/flipped group, without touching `local_geometry_in`,
    `child_ids`, `local_z_order`, or `parent_group_id` at all. Rotation/flip
    *composition* itself remains explicitly out of scope, per instruction — this is a
    safety guard against a false non-null answer, not an attempt to compute the
    rotated/flipped position. Note: a rotated/flipped group's OWN position within ITS
    parent (its own `local_geometry_in`/`resolved_geometry_in` as a shape) is
    unaffected and still resolves normally — per OOXML, `off`/`ext` describe the
    un-rotated/un-flipped bounding box; only resolving *children* through that group's
    rotated/flipped child-coordinate space is unsafe.
  - Tests: `TestGroupCoordinateResolution` (single- and two-level-nested synthetic
    groups, a degenerate zero-`chExt` case, plus Build 3's new rotated/flipH/flipV/
    nested-ancestor-poisoning/`rot="0"`-is-normal cases) and
    `TestGroupRecursion.test_local_z_order_is_per_parent_not_a_global_flattened_counter`
    / `test_child_ids_are_immediate_only_not_flattened_descendants`. Real-deck
    regression: `TestRealDeckValidation.test_real_rotated_flipped_groups_yield_
    unresolved_geometry` dynamically discovers every rotated/flipped group on real
    slide index 32 via raw XML inspection (not hardcoded IDs — the found IDs are
    asserted only as evidence, matching what this session independently confirmed:
    `{1255, 1259, 1263}`) and asserts every one of their children has
    `resolved_geometry_in is None` while `local_geometry_in` remains populated.

- **Title/topic-key extraction, now group-aware (L0-05, repaired)**: `extract_title`'s
  candidate search previously inspected only top-level `slide.shapes`. It now walks the
  full shape tree via `_iter_text_candidates`, resolving each candidate's slide-absolute
  top position through the same group-transform chain used for `resolved_geometry_in`,
  so a real title sitting inside a group is found and correctly classified as
  header-region text. The existing five-tier priority order is unchanged: (1) title
  placeholder; (2) `Desktop:`-convention header-region text; (3) other header-region
  text, topmost first; (4) `Desktop:` convention anywhere; (5) topmost-then-leftmost
  fallback. `TestTitleExtraction.test_grouped_title_beats_top_level_body_fallback`
  places a `Desktop: Grouped Title` inside a group whose raw local child coordinate
  (9,000,000 EMU) is far outside the header zone if treated as absolute — only correct
  transform resolution places it in the header region — and asserts it still wins over a
  distractor top-level body shape. The real Message Actions/Pinned Messages
  counterexample (index 74) and repeated-title occurrence-ordinal behavior are
  unaffected and still pass.

- **Empty-slide fingerprint (L0-07, repaired)**: `compute_fingerprint` previously used
  one guarded (never-zero) `total` value both as the ratio denominator *and* as the
  numerator for `shape_count_norm`, so a genuinely empty slide reported a small nonzero
  `shape_count_norm` instead of `0.0`. Now `raw_count` (the real, unguarded count) feeds
  `shape_count_norm`, and a separate `denom = max(raw_count, 1)` is used only for the
  ratio divisions. `TestFingerprint.test_empty_slide_fingerprint_is_all_zero_...`
  asserts every fingerprint field is exactly `0.0` for an empty slide.

- **Deterministic, reproducible canonical output (L0-02, repaired)**: the manifest no
  longer contains a generation timestamp (removed entirely, not moved to a side file —
  simplest compliant fix; nothing downstream depended on it). The caller-supplied
  `source_deck_path` string (which varied between absolute and relative spellings) is
  no longer embedded verbatim; `manifest["source_identifier"]` is instead computed by
  `_normalize_source_identifier()` — the source's resolved real path, expressed
  relative to the repository root when it lives inside the repo (the canonical deck
  always does), else the resolved absolute path — which is identical regardless of how
  the caller spelled the path. `TestDeterminism` proves, both on synthetic fixtures and
  the real deck (see `verification-report.md`), that two full-tree generations from
  identical source bytes into separate output directories are byte-for-byte identical
  (manifest, Tier A, structural analysis, and every Tier B file), and that relative vs.
  absolute spelling of the same source path produces an identical manifest.

- **Staged, validated, atomic, owned-tree publication with an explicit
  publication-validity marker (L0-03)**: `generate_layer0_inventory` never writes
  directly into `output_dir`. It builds the complete new tree into a private sibling
  staging directory (`_write_staged_tree`), validates that staged tree as a whole
  (`_validate_staged_tree` — every owned file present and valid JSON, the staged Tier B
  file set matching the manifest's own `tier_b_paths`, Tier A's record count matching
  the manifest's `slide_count`) **before touching `output_dir` at all**, and only then
  publishes it (`_publish_owned_tree`), all under an exclusive single-writer lock (see
  below). Layer 0 owns exactly three named top-level files (`manifest.json`,
  `tier_a_summary.json`, `structural_analysis.json`), the entire `tier_b/`
  subdirectory, the commit-validity marker (`_committed.json`, see below), and one lock
  file (`.{output_dir.name}.lock`, next to `output_dir`, not inside it — see "Lock file
  is runtime-only" further below) — nothing else under or near `output_dir` is ever
  read, moved, or removed.

  **Typed error boundary — staging (Build 4, closes the Audit-3 "raw `OSError` on a
  staged-write failure" finding)**: `_write_staged_tree()`'s entire body (directory
  creation, every JSON write — Tier A, every individual Tier B file, structural
  analysis, manifest) is now wrapped in one boundary; any `OSError` is normalized to a
  typed `PublicationStagingError`, chained via `from`. The staging-directory creation
  call in `generate_layer0_inventory` itself raises the same typed error. Staging
  failures occur entirely within the private staging directory — `output_dir` (any
  previously published tree) is never touched by a staging failure, and staging cleanup
  (removing the now-useless partial staging directory) still runs via the existing
  `finally` block regardless.

  **Typed error boundary — publication**: `output_dir` existing as a non-directory is
  rejected up front (before the source is even hashed) with a typed `PublicationError`,
  never a raw `FileExistsError`. `_mkdir_or_raise()` wraps every directory-creation call
  and converts `FileExistsError`/`OSError` into `PublicationError`. Lock-acquisition
  failure raises `PublicationLockError`. Commit and cleanup failures raise
  `PublicationError`; a commit failure whose rollback also fails raises
  `PublicationRollbackError` — never a bare `OSError` in any of these cases.

  **Publication-validity invariant, final design (Build 5, closes L0-03 for real —
  Build 4's manifest-only marker was itself found unsound by Audit 4 on four separate
  grounds; see below)**:

  > No canonical Layer 0 tree may ever be considered valid unless the ENTIRE owned
  > artifact set belongs to one complete successful publication. Before mutating any
  > canonical owned artifact, the current publication must first be successfully
  > invalidated. If invalidation fails, abort before moving/replacing ANY canonical
  > artifact, leave the previous valid tree untouched, and raise a typed error. A stale
  > validity marker must never survive into a publication transition.

  **Publication state machine** (the acceptance criterion for this design):

  | State | Trigger | `is_tree_valid()` |
  |---|---|---|
  | Existing valid tree | marker present, whole-tree digest matches | `True` |
  | Publication begins | marker successfully invalidated (removed) — a HARD precondition, before any owned artifact is touched | `False` |
  | Publication in progress | canonical artifacts may temporarily move/change | `False` |
  | Publication succeeds | complete owned tree installed, whole-tree digest computed, marker written as the literal final step | `True` |
  | Commit failure + full rollback succeeds | previous owned tree completely restored, its digest recomputed, marker restored | `True` |
  | Commit failure + rollback incomplete | recovery backups retained; marker NOT recreated | `False` (typed `PublicationRollbackError`) |

  **What Audit 4 found wrong with Build 4's attempt, and how each is closed:**

  1. *Failed marker invalidation could leave a mixed tree valid* — Build 4 invalidated
     the marker only as a best-effort step inside the rollback path, after a failure was
     already detected; if that invalidation itself silently failed (the old
     implementation swallowed the `OSError`), a stale marker could survive a
     subsequently mixed tree. **Closed**: `_invalidate_commit_marker_or_raise()` is now a
     HARD PRECONDITION, called as the very first action of `_publish_owned_tree()` —
     strictly before the prepare phase (moving any owned item aside) even begins. If the
     marker exists and cannot be removed, this raises `PublicationError` immediately;
     zero canonical artifacts have been touched, so there is nothing to roll back and the
     previous tree remains byte-identical and still valid.
  2. *Same-source regeneration had a mid-publication valid window* — because
     invalidation now always happens first, unconditionally, regardless of whether the
     new content will end up byte-identical to the old, there is no code path left in
     which the marker is present while any owned artifact is being replaced.
  3. *The marker authenticated only the manifest* — Build 4's marker was
     `{"manifest_sha256": ...}`; mutating `tier_a_summary.json` alone left `is_tree_valid()`
     returning `True`. **Closed**: `_compute_owned_tree_digest()` now computes one
     SHA-256 over the sorted list of `(relative_path, file_sha256)` pairs for **every**
     owned artifact — `manifest.json`, `tier_a_summary.json`, `structural_analysis.json`,
     and every `tier_b/slide_*.json` file the manifest itself declares via
     `tier_b_paths`. The marker is `{"schema_version", "tree_sha256", "owned_file_count"}`.
     The declared (manifest) and actual (on-disk glob) Tier B file sets must match
     exactly — a missing expected file and an unexpected stray extra file are equally
     disqualifying, so a stale extra Tier B file cannot silently ride along as "owned."
     Digest computation is order-independent (paths sorted explicitly) and never raises —
     any missing/unreadable/mismatched owned file makes it return "not computable"
     (`None, None`), which callers always treat as "does not match."
  4. *Malformed marker shape leaked `AttributeError`* — a bare JSON array (`[]`) passed
     Build 4's `marker.get(...)` call, since lists don't have `.get`. **Closed**:
     `is_tree_valid()` now explicitly checks `isinstance(marker, dict)` before ever
     calling `.get`, and separately checks `isinstance(...)` on each recorded field
     before comparing — fails closed (`False`, never a raised exception) for every
     malformed input: missing marker, invalid JSON, wrong JSON shape, missing/wrong-typed
     fields, a malformed digest, a stale marker literally copied from a different
     published tree, or any owned-file mismatch.

  **Rollback-failure safety (unchanged in mechanism from Build 3, only the marker
  re-establishment step now uses the whole-tree digest instead of the old manifest-only
  hash)**: existing owned items are first moved aside (atomic `os.replace`, not yet
  deleted), then staged replacements are moved into place; if any commit-phase step
  fails, each moved-aside item is restored **independently** (one item's restore failing
  does not abort restoring the rest). Every backup name involved in a rollback failure is
  retained, never deleted, and named explicitly in the `PublicationRollbackError`
  message. Subsequent generation behavior is defined and tested: once affected backups
  are manually restored to their canonical names, a normal regeneration succeeds and
  `is_tree_valid()` becomes `True` again (merely restoring file-level content by hand,
  without running a fresh `generate_layer0_inventory()`, deliberately does **not** by
  itself re-validate the marker).

  Only after every new item AND the marker are successfully in place (ordinary success
  path) are the now-stale "moved aside" originals removed as one unit — this is what
  makes a shorter regeneration's stale extra Tier B files (e.g. a `slide_0170.json` from
  a longer previous deck) disappear automatically, without any per-file staleness
  diffing.

  **Consumer contract**: no code in this module (or anywhere else in the repository)
  currently reads a published Layer 0 tree and treats it as valid without going through
  `is_tree_valid()` — no such consumer exists yet. Documented explicitly for whoever
  builds the first one: **future consumers MUST call `is_tree_valid(output_dir)` before
  trusting the canonical Layer 0 tree** — reading `manifest.json`/`tier_a_summary.json`/
  Tier B files directly, without this check, bypasses the entire publication-validity
  guarantee this section exists to provide.

  **Parser fail-closed boundary (Build 6, closes three narrower parser/schema gaps
  Codex found in `is_tree_valid()` itself, after the state-machine/digest design above
  had already passed audit)**: `is_tree_valid()` is a *safe predicate*, not a
  validating parser — it must return `False`, never raise, for expected malformed
  input, and it must not silently accept a marker it does not actually recognize.
  Three gaps closed, all narrowly scoped to `is_tree_valid()` and the one helper it
  calls (`_compute_owned_tree_digest`, which reads `manifest.json`) — nothing else in
  the module was touched:
  1. **Marker schema version is now mandatory and exact.** The marker's
     `schema_version` field was present in the output (`_MARKER_SCHEMA_VERSION`,
     currently `"1.0.0"`) but never checked on read — a missing, `null`, wrong-typed,
     or unknown/future `schema_version` still validated as `True`. `is_tree_valid()`
     now requires `marker.get("schema_version") == _MARKER_SCHEMA_VERSION` exactly (a
     single named constant, not a duplicated magic string) before proceeding to any
     digest comparison.
  2. **Invalid UTF-8 fails closed.** Reading `_committed.json` or `manifest.json` as
     text can raise `UnicodeDecodeError` (not an `OSError` subclass) on invalid UTF-8
     bytes; both read sites now catch `(OSError, UnicodeDecodeError)` around the read
     itself, separately from JSON parsing.
  3. **Oversized JSON integers fail closed.** Python's interpreter-level integer-
     string conversion limit (`sys.set_int_max_str_digits`, unmodified, not disabled)
     makes `json.loads` raise a plain `ValueError` — not `json.JSONDecodeError` — for
     an oversized integer literal (confirmed empirically this round: a 5,000-digit
     integer literal raises `ValueError: Exceeds the limit (4300 digits)...`). Both
     `json.loads` call sites now catch `ValueError` (which also subsumes
     `json.JSONDecodeError`, itself a `ValueError` subclass), scoped to only the parse
     call, not the surrounding logic.

  Nothing about the digest computation, the hard-precondition invalidation, the
  rollback design, the lock, or the source-integrity transaction changed this round —
  only these three narrow read/parse boundaries inside `is_tree_valid()` and
  `_compute_owned_tree_digest()`.

  **Single-writer publication lock (unchanged from Build 3, still correct — see "Lock
  file is runtime-only" for its commit-scope status, which IS new this round)**:
  `_acquire_publish_lock()` holds an exclusive, non-blocking `fcntl.flock` on
  `output_dir.parent / f".{output_dir.name}.lock"` for the entire staging+validate+
  publish sequence. A second concurrent generation targeting the same `output_dir`
  fails fast with `PublicationLockError` rather than waiting or interleaving. The lock
  file itself is never deleted; only the flock is released, in a `finally`, after every
  generation attempt. No classic stale-PID-file problem (kernel-managed, auto-released
  on process exit/crash); explicitly **POSIX-only**, **no distributed/network-filesystem
  safety** claimed.

  **Bounded limitation, unchanged and explicitly not overclaimed**: this design is
  crash-safe for the class of failure actually reproducible in-process (an exception
  during a write/replace call — exactly what every fault-injection regression below
  tests, including Audit 3's own described double-fault). It is not full ACID/journaled
  filesystem transactionality; a genuine OS-level crash or power loss occurring at an
  even finer granularity than any single `os.replace`/file-write call is outside what
  this bounded repair adds or guarantees beyond "the previous content is never deleted,
  only possibly left under a backup name, and the marker mechanism ensures the tree
  never falsely reads as valid in the meantime."

  Tests: `TestAtomicPublication` (ordinary mid-publish failure with clean rollback; the
  Audit-3-shaped mixed-tree fault injection, now additionally asserting `is_tree_valid()`
  reports `False` throughout; a shortened-deck regeneration removing stale owned Tier B
  files; unrelated files inside *and* adjacent to `output_dir` surviving untouched; a
  normal regeneration over an existing valid tree; a staging-validation failure never
  touching `output_dir`; an `output_dir`-as-a-file probe; and the double-failure fault
  injection with `is_tree_valid()` assertions — `False` after the failure, `True` after
  full manual recovery + a real regeneration). **`TestPublicationValidityMarker`
  (Build 5, new, 17 tests)**: `test_marker_invalidation_failure_aborts_before_any_
  mutation` (Audit 4 finding #1 — a marker-unlink failure aborts with zero canonical
  mutation, no `.prev-*` backups created at all, previous tree stays valid);
  `test_no_valid_window_exists_during_publication_transitions` (Audit 4 finding #2 — a
  same-source regeneration probed via `is_tree_valid()` after every single `os.replace`
  call during the whole publish, asserting every intermediate snapshot is `False`);
  `test_healthy_tree_validates_true`; a full fail-closed matrix — marker missing,
  invalid JSON, wrong shape (`[]`, reproducing Audit 4 finding #4's exact
  `AttributeError` case), missing required field, wrong field types, wrong digest, a
  marker copied verbatim from a *different* published tree (byte-for-byte valid JSON
  with the right shape, just the wrong tree's content); and a full owned-artifact
  mutation matrix — manifest, Tier A, structural analysis, one Tier B file mutated, one
  Tier B file missing, one stray extra Tier B file (Audit 4 finding #3 — each
  independently makes `is_tree_valid()` `False`, proving the digest binds to the whole
  tree, not just the manifest); plus a determinism check that two independent
  generations from the same source produce byte-identical markers.
  `TestStagedWriteTypedErrors` (unchanged from Build 4, still passing: a Tier B file
  write failure, a manifest write failure, a staging-directory creation failure, and a
  staged-write failure proven to leave a prior published tree completely untouched —
  `is_tree_valid()` still `True` afterward — all raising `PublicationStagingError` with
  the original `OSError` chained as `__cause__`). `TestSingleWriterLock` (unchanged: a
  manually pre-acquired flock causing an immediate `PublicationLockError`; the lock file
  surviving across successful generations; a real two-*process*
  `multiprocessing.Process` regression proving a concurrent writer fails fast rather
  than interleaving).

## Non-goals (locked boundary, per founder/task instruction)

No editorial-era, editor-identity, or current-editorial-style determination; no
Presentation Memory (founder-approved or otherwise); no specialist/range agent launch;
no visual/scene interpretation; no slide editing, reflow, or formatting preservation; no
new-slide generation; no PDF analysis (a separate, later channel); no embeddings or LLM
calls anywhere in this module; no redesign of Architecture v0.1; no batch mutation of
any kind (this module performs zero mutation); no commit/push/merge. Repairing this
audit did not expand scope beyond the listed findings — no rotation composition across
group transforms, no per-shape staleness diffing, no new deck-wide statistics beyond
`invalid_connector_count` (a direct consequence of the L0-06 fix, not scope creep), no
distributed/network-filesystem locking (the single-writer lock is explicitly local/
POSIX-only, per instruction), and no crash/power-loss-level transactional durability
beyond the documented, bounded rollback-failure behavior above.

## Failure and empty states

`DeckSourceError` (reused, unmodified) — a missing/empty/corrupt `source_deck_path`.
`SourceIntegrityError` (`DeckSourceError` subclass) — the source's bytes changed
between the pre-extraction and pre-publication hash; nothing is staged or published.
`StagingValidationError` — the staged tree failed its own internal consistency check;
`output_dir` was never touched. `PublicationStagingError` (new, Build 4) — writing the
staged tree itself failed for a filesystem reason (staging-directory creation, any of
the JSON writes); entirely within the private staging directory, `output_dir` never
touched. `PublicationError` — `output_dir` exists as a non-directory; a
directory-creation failure; publication into `output_dir` failed after a full rollback
(previous tree restored, commit-validity marker re-established — `is_tree_valid()` →
`True`); or publication succeeded but best-effort cleanup of the now-stale previous
artifacts failed (the new tree is live, correct, and validly marked in this case — only
the old, now-unreferenced copy could not be removed). `PublicationRollbackError`
(`PublicationError` subclass) — publication failed AND rollback could not fully restore
the previous tree; the previous content is retained, never deleted, under an
explicitly-named `.prev-<token>` backup, and the commit-validity marker is left
deliberately absent (`is_tree_valid()` → `False`) so the canonical tree can never read
as valid in this state. `PublicationLockError` (`PublicationError` subclass) — another
Layer 0 generation currently holds the publish lock for this `output_dir`. All other
per-shape extraction failures (an individual picture's image facts failing to resolve,
for example) are still caught locally and degrade to `None` fields rather than aborting
the whole-deck extraction.

## Source immutability

The canonical MasterSlide source (`documentation-artifacts/masterslide/old/MASTER
Complete Bridge4PS Desktop-Browser Feature Tutorials.pptx`, SHA-256
`e461613baae2874eaeede3268fff1aee081c33a04a6bcbb0c7769b94bab16834`) is opened read-only
exactly once per call, via `load_deck()`, after being hashed first (see the
source-integrity transaction above); this module contains no write path to that file or
any file under `documentation-artifacts/masterslide/old/`. Verified unchanged before and
after the test suite run, the production inventory regeneration, and the required
full-tree determinism comparisons — see `verification-report.md`.

## Persistence — what belongs to Layer 0 and what does not

`documentation-artifacts/masterslide/layer0/` — the Layer-0-owned tree: `manifest.json`,
`tier_a_summary.json`, `structural_analysis.json`, `tier_b/`, and (Build 4, new) the
commit-validity marker `_committed.json`. Not created by this change, deliberately: any
`specialist_findings/` directory, any founder-approved Presentation Memory file, or any
placeholder/empty directory reserving space for either.

**Lock file is runtime-only (Build 4, new)**: `documentation-artifacts/
masterslide/.layer0.lock` — zero-byte, created automatically by
`_acquire_publish_lock()` the first time a generation runs, not durable project
knowledge or configuration, not required to exist before generation. Per Codex's
explicit lock-file commit verdict, it is **excluded from the intended commit path
set** (see "Working-tree scope" below) and is now covered by an exact-path
`.gitignore` rule (`documentation-artifacts/masterslide/.layer0.lock` — the smallest
rule that covers exactly this file, not a wildcard, so no other evidence/artifact file
in this directory is broadly ignored). The flock implementation itself is unchanged —
this is a commit-scope/documentation correction only, not a redesign.

## Working-tree scope (SCOPE-L0-01, corrected again — Build 2's and Build 3's counts
## were each in turn found imprecise by the next audit)

`git status --short -uall` was re-run in full for this record (not sampled, not
estimated, not carried over from a prior round's number) after removing only transient
`__pycache__`/`.pyc` files under `documentation-intelligence/` (already covered in an
earlier round; none remained to remove this round) and after adding the `.gitignore`
rule for `.layer0.lock` described above. The resulting count is **231
untracked/modified entries**, exactly accounted for in three categories:

1. **This change's own intended commit paths — 6 non-generated + 174 generated = 180
   entries:**

   ```
   documentation-intelligence/documentation_intelligence/_safe_ppt_engine_import.py   (modified)
   .gitignore                                                                          (modified - see "Lock file is runtime-only")
   documentation-intelligence/documentation_intelligence/layer0.py                    (new)
   documentation-intelligence/tests/test_layer0.py                                    (new)
   documentation-artifacts/masterslide/layer0/manifest.json                           (new, generated)
   documentation-artifacts/masterslide/layer0/tier_a_summary.json                     (new, generated)
   documentation-artifacts/masterslide/layer0/structural_analysis.json                (new, generated)
   documentation-artifacts/masterslide/layer0/_committed.json                         (new, generated - Build 4 commit-validity marker)
   documentation-artifacts/masterslide/layer0/tier_b/slide_0000.json … slide_0169.json (new, generated, 170 files)
   openspec/changes/masterslide-layer0-inventory/spec.md                              (this record)
   openspec/changes/masterslide-layer0-inventory/verification-report.md              (this record)
   ```

   (2 modified + 4 new non-generated = 6; 3 top-level generated + 1 marker + 170 Tier B
   = 174; 6 + 174 = 180.)

2. **Runtime-only, explicitly excluded from the intended commit set — 1 entry:**
   `documentation-artifacts/masterslide/.layer0.lock` (now `.gitignore`d, so it no
   longer appears in `git status` output at all — listed here for completeness, not
   because it still shows up).

3. **Pre-existing, unrelated untracked material this change did not create and does
   not touch — 51 entries** (unchanged from every prior round):
   - `Expert resources/*.mp4` (4 video files).
   - `documentation-artifacts/README.md`, `documentation-artifacts/masterslide/old/*`
     (the canonical deck itself and its `.gitkeep`), `documentation-artifacts/
     masterslide/updated/*` (`Masterslides.pdf` and its `.gitkeep`) — 5 entries.
   - `documentation-artifacts/bridge-ui-evidence/` (42 files) — output from unrelated
     prior work in this working tree.

   (4 + 5 + 42 = 51.)

**Arithmetic**: 180 (category 1) + 51 (category 3) = 231, the exact `git status --short
-uall` count for this run. Category 2 (the lock file) contributes 0 to this count
because it is gitignored, not because it doesn't exist — it genuinely does, on disk, as
a real runtime artifact; it simply isn't a `git status` candidate at all now.

No untracked/pre-existing material outside category 1 has been or should be deleted,
modified, or staged by this change. This section states a truthful, actually-computed
count for this specific run, not an estimate carried over from a prior round — a future
run may find a different exact number if unrelated working-tree content changes, and
should re-run `git status --short -uall` rather than trust this document's number
stale.

## Status

**Build 1: implemented; Codex Audit 1: FAIL (L0-01, L0-02, L0-03 blockers; L0-04,
L0-05, L0-06, SCOPE-L0-01 major; L0-07 minor). Build 2: repaired all eight findings;
Codex Audit 2: L0-01/L0-02/L0-05/L0-06/L0-07 CLOSED; L0-03/L0-04/SCOPE-L0-01 PARTIAL;
GOV-L0-01/GOV-L0-02 new MAJOR. Build 3: repaired L0-04/GOV-L0-01/GOV-L0-02, partially
repaired L0-03/SCOPE-L0-01; Codex Audit 3: L0-04/GOV-L0-01 confirmed CLOSED; L0-03
still PARTIAL; new typed-staged-write-error and lock-commit-scope findings;
SCOPE-L0-01/GOV-L0-02 accounting still imprecise. Build 4: closed staged-write typing
and lock-commit-scope; a first attempt at L0-03 via a manifest-only marker; Codex
Audit 4: staged-write typing/lock-scope/SCOPE-L0-01 confirmed CLOSED, but L0-03
reproduced FAIL on four further concrete grounds (silent marker-invalidation failure,
a same-source mid-publication valid window, a marker authenticating only the
manifest, a malformed-marker `AttributeError`). Build 5 (this record): replaces the
marker with a whole-owned-tree digest, makes invalidation a hard precondition before
any canonical mutation, and makes `is_tree_valid()` fail closed for every malformed
input. Also corrects the verification report's governance-gate wording: independent
Codex audit **PASS** is the pre-commit/integration gate for this exact audited tree;
founder/manual approval is a distinct, later pre-release/phase-closure gate and
remains PENDING, not a precondition for commit/push/PR itself. Codex **Audit 5:
PASSED** the publication state machine, whole-tree commitment, hard-precondition
invalidation, same-source mid-publication safety, rollback, source-integrity
transaction, deterministic output, rotated/flipped geometry, grouped titles,
connector validity, fingerprint, staged-write typed errors, runtime flock, scope
accounting, GOV-L0-01, GOV-L0-02 — found 3 narrower parser/schema gaps specifically in
`is_tree_valid()` (unenforced marker `schema_version`, raw `UnicodeDecodeError` on
invalid UTF-8, raw `ValueError` on an oversized JSON integer). **Build 6 (this
record)**: closes exactly those three gaps — enforces an exact `schema_version` match
against a single named constant, catches `UnicodeDecodeError` around both the marker
and manifest text reads, and catches `ValueError` around both `json.loads` calls — see
`verification-report.md` for full evidence. Not yet independently re-audited.** Not
committed, pushed, or opened as a PR — local working-tree changes only, per explicit
task instruction.
