# Change Specification — Presentation Editing Intelligence / Scene-Aware Editing, Slice 1

Written after implementation (process deviation disclosed, matching this repository's own
established disclosure convention for retroactively-written specs, e.g. Safe PPT Engine Audit
Repair 3, Editorial Memory Slices 4–7 Repair 3). This is the first bounded slice of Presentation
Editing Intelligence, authorized after the Founder-Approved Presentation Memory integration
(`presentation-exploration-layers-1-4`, integrated at `main` `d593133ab62780d7c994c56c431a526a030b2b06`).
**This record reflects the post-Repair-5 state.** Audit chronology: Codex Audit 1 → **FAIL**
(PEI-S1-01 through PEI-S1-07) → Repair 1 (builder-implemented) → Codex Re-Audit 1 → **FAIL** again,
on 5 findings Repair 1 had not actually closed (PEI-S1-01, PEI-S1-02, PEI-S1-06, PEI-S1-07) plus
one newly identified (PEI-S1-08) → Repair 2 (builder-implemented) → Codex Re-Audit 2 → **FAIL**
again, narrowly, on 2 findings (PEI-S1-07, PEI-S1-08 — Repair 2's target-growth refusal was too
narrow, activating only for `MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT`) → Repair 3 (builder-implemented) →
Codex final narrow audit → **FAIL** again, narrowly, on the same 2 findings (PEI-S1-08 — Repair 3's
fit estimate selected a single run's font size, which underestimates mixed-format text, reproduced
with an 8pt first run / 40pt edited run; PEI-S1-07 — governance accuracy: conservative-fit claims,
current-tree file accounting, and the auto-size test description all needed correction) → Repair 4
(builder-implemented) → Codex closure audit → **FAIL** again, narrowly, on the same 2 findings
(PEI-S1-08 — Repair 4's own fix checked `isinstance(line_spacing, (int, float))` before checking
`isinstance(line_spacing, Length)`; every python-pptx `Length` subclass is itself an `int`
subclass, so an absolute line-spacing value such as `Pt(12)` was silently misread as a multiplier,
falsely refusing clearly-fitting text; PEI-S1-07 — three remaining factual problems in
`verification-report.md`: an absolute-`Length` line-spacing claim describing behavior the code did
not yet have, a self-contradictory Repair 4 touched-file count, and a false claim that the dead
`max_lines_that_fit()` helper "remains used") → Repair 5 (this record; builder-implemented).
**Status per finding:** PEI-S1-01 through PEI-S1-06 are recorded **CLOSED** (Re-Audit 2, the final
narrow audit, and the closure audit did not reopen any of them). PEI-S1-07 and PEI-S1-08 remain, at
most, "builder repair implemented; independent closure pending" — a builder's own re-run of its own
tests is not independent verification, and this exact finding (PEI-S1-08) is itself the fourth
consecutive round where a builder-reported "FIXED" did not hold up under independent review. See
`verification-report.md` for the full per-finding record across all five repair rounds.

## Purpose

Presentation Memory answered *what* Bridge4PS slides should look like (the founder-approved
default editorial grammar, plus the relationship-aware exception rule). It did not answer *how*
to apply an edit to a real slide without breaking that look — the exact gap founder visual review
of the prior Documentation Intelligence Slice 3 benchmark exposed: `TextFrame.text = new_text`
correctly changed the words but destroyed run/paragraph formatting and left the slide's visual
rhythm broken. This slice builds the smallest capability that closes that gap for one real
benchmark case: correct content edit + formatting preservation + local relationship preservation
+ layout maintenance, on the real Pinned Messages / Message Actions slide.

## Bounded scope

Builds only enough capability for a scene-aware **single-slide text-edit pilot**. Explicitly
**not** built in this slice: full-deck autonomous editing, batch editing, new-slide generation,
arbitrary redesign, broad modernization, every possible relationship type, general LLM slide
regeneration. See "Non-goals" below for the complete list.

## Relationship-aware founder requirement

Per the founder-approved presentation style
(`documentation-artifacts/masterslide/exploration/founder_approved_presentation_style.md`),
purposeful gray pointers, arrows, connectors, dividers, callouts, and highlights are part of the
approved grammar whenever they explain exceptions, dependencies, source→target relationships,
before/after progression, text-to-screenshot associations, or cross-UI-region relationships — and
must be preserved and intelligently maintained (not stranded, misdirected, or deleted) when
related content moves, resizes, or reflows. This slice implements a bounded subset of the full
scene-relationship vocabulary that checkpoint names as a future direction: `belongs-to`,
`points-to`, `highlights`, `separates`, `anchored-to`, `aligned-with`, `depends-on`. **`moves-with`
is explicitly NOT implemented (Codex PEI-S1-05)** — it requires group-member extraction (re-basing
each member's coordinates through its group's `chOff`/`chExt` transform), which this slice defers
as a materially larger scope; `SceneShape.group_shape_index` is never populated, and no code path
emits a `moves-with` relationship. `ordered-before/after`, `repeated-with`, and `contained-by` are
also not implemented this slice — no benchmark evidence required them yet, and adding unevidenced
relationship types would violate the deterministic-first architecture below.

## Deterministic-first architecture

Every fact this slice's scene model, relationship inference, and safety checks rely on comes
directly from OOXML/python-pptx structure — geometry, shape type, line/fill color, explicit
`<a:stCxn>`/`<a:endCxn>` connector bindings, text. No LLM, no semantic/fuzzy matching, no
image-based inference. Every inferred relationship carries `confidence` (`HIGH`/`MEDIUM`/`LOW`)
and `evidence` (the concrete structural facts that produced it). **Confidence calibration (Codex
PEI-S1-04):** `HIGH` is reserved exclusively for an explicit OOXML structural binding (currently
only a real `<a:stCxn>`/`<a:endCxn>` connector endpoint reference) — geometry/proximity/style
inference, including color, is capped at `MEDIUM`; weak contextual proximity is `LOW`. Ambiguous
geometry is never promoted to certainty, and color is never treated as semantic authority on its
own. A formatting-preserving text edit that cannot be localized to exactly one existing run
returns `unresolved` rather than guessing, including a genuinely ambiguous zero-width insertion at
a shared run boundary whose adjacent runs have unknown or differing formatting (Codex PEI-S1-03 —
see `text_edit.py`'s module docstring for the full algorithm). A safety check that finds a
critical conflict (new overlap — checked against every shape on the target slide, not only the
local reasoning scope, per Codex PEI-S1-06; out-of-bounds; alignment breakage; a relationship that
would become one-sided/stranded) stops the edit before publication rather than silently degrading
the slide. Publication itself is gated a second time, after the fact, by comprehensive
protected-structure verification (Codex PEI-S1-02, `protected_structure.py`) — any unauthorized
difference removes the just-published output and the edit is never reported `"applied"`.

## Safe PPT Engine reuse

**Corrected design decision (Codex PEI-S1-01, FAIL on the original decision below — kept here,
struck through in effect, for an honest record; see the replacement decision immediately after):**
~~this slice does not add any new primitive to `ppt_engine.py` itself; formatting-preserving text
mutation is a new, self-contained primitive implemented in this package rather than by reopening
the Safe PPT Engine's own file.~~ Codex found this reimplemented a second, weaker publication
protocol (a racy `overwrite=False` check). **Corrected:** `set_shape_text_runs_and_geometry` is
now a new primitive added **directly to `ppt_engine.py`** (purely additive — zero existing lines
touched), reusing that file's own private staging/publication machinery
(`_staged_copy`/`_finalize_transaction`/`_publish_atomically`) exactly as every other primitive in
that file does. `presentation-editing-intelligence/presentation_editing_intelligence/
_safe_ppt_engine_import.py` imports this primitive plus `inspect_deck`, `load_deck`,
`file_sha256`, `move_shape`/`resize_shape`/`set_shape_geometry` (kept for reference/reuse where a
caller wants a standalone geometry mutation), and the engine's own typed errors.
`text_mutation.py` is now a thin adapter only — it translates this package's plan objects into the
plain tuples the engine primitive accepts and calls it; it contains no staging, publication,
no-clobber, or cleanup logic of its own. Presentation Editing Intelligence decides *what* to
change (text runs, geometry moves); the Safe PPT Engine remains the only thing that ever writes a
`.pptx`, and remains the sole owner of staging, atomic publication, no-clobber behavior, typed
failures, cleanup, and the source-integrity gate. The Safe PPT Engine's existing primitives,
tests, and audit history are otherwise untouched — this is an addition, not a redesign.

**Second correction (Codex PEI-S1-01, Re-Audit 1, FAIL again):** Repair 1's engine primitive
accepted `geometry_moves` shape-id guards but had no `expected_shape_id` parameter for the *text*
target — that guard still lived in `text_mutation.py`, checked against a separate read-only load
taken *before* calling the engine. Codex reproduced the exact TOCTOU this left open: the source
can be swapped for a different deck (same slide/shape index, different `shape_id`) between that
check and the engine actually staging and mutating the file, and the stale pre-check would not
catch it. **Corrected:** `set_shape_text_runs_and_geometry` now accepts `expected_shape_id`
directly and validates it against the shape resolved on the **staged copy**, inside the same
transaction, immediately before any run edit is applied. `text_mutation.py` performs no identity
check of its own anymore — it passes `expected_shape_id` straight through.

## Native PowerPoint visual authority

OfficeCLI is not used, and is not treated as ground-truth visual evidence, anywhere in this
slice. This sandbox has no automated native Microsoft PowerPoint rendering available, so the
benchmark output is produced and structurally verified (formatting preserved at the OOXML level,
relationships preserved, no unrelated mutation, source unchanged, deterministic safety checks
pass), but **final visual approval is explicitly marked `FOUNDER NATIVE-POWERPOINT REVIEW
REQUIRED`** — this slice's own automated checks are not a substitute for that review and do not
self-approve it.

## Refusal/unresolved behavior

`pilot.apply_scene_aware_edit` returns one of three statuses, never partially applying an edit:

- `"applied"` — the edit was planned, safety-checked, applied, and verified (including
  comprehensive protected-structure verification after publication).
- `"unresolved"` — the requested text change cannot be safely localized to one existing run, a
  `shape_id` guard mismatched (checked on the staged copy, inside the transaction — PEI-S1-01), or
  **fit within the target's EXISTING container cannot be conservatively established (Codex
  PEI-S1-08)** — nothing is written in any of these cases. **The true Slice 1 rule: if fit in the
  existing container cannot be conservatively established, the edit is refused regardless of
  `auto_size` mode** — `MSO_AUTO_SIZE.NONE`, `SHAPE_TO_FIT_TEXT`, and any other or unknown value
  are all treated identically, because Slice 1 never resizes the target container in any code
  path; see "Non-goals". **Fit is established conservatively across every run/paragraph
  participating in the resulting text, not from a single run's formatting (Repair 4):** the
  effective font size used for the estimate is the maximum resolved size across all affected runs
  (falling back to each paragraph's default size only where a run has no explicit size of its
  own), each paragraph's `line_spacing` and `space_before`/`space_after` are added into the
  required-height estimate where deterministically available, and if any run's effective size
  cannot be resolved at either the run or paragraph level the edit is refused
  (`status="unresolved"`) rather than estimated with an unresolved size — "uncertain fit ⇒
  refuse" applies to formatting resolution itself, not only to the geometry comparison. **An
  absolute `line_spacing` (a python-pptx `Length`, e.g. `Pt(12)`) is checked and used directly, in
  EMU, before any generic numeric/multiplier check runs (Repair 5) — every `Length` subclass is
  itself an `int` subclass, so checking the generic numeric case first would silently misread an
  absolute value as a multiplier and produce a grossly inflated, falsely-refusing estimate; a
  plain `float`/`int` that is not a `Length` instance is still treated as a multiplier of the base
  line height.**
- `"unsafe"` — the edit is resolvable but a deterministic safety check found a critical conflict
  (including a swept-path collision — PEI-S1-06), or post-publication protected-structure
  verification found an unauthorized difference, in which case the just-published output is
  removed (or, if that removal itself fails, both the verification failure and the cleanup
  failure are reported explicitly — PEI-S1-02) — nothing is left in a falsely-"applied" state.

## Benchmark acceptance criteria

Real benchmark: canonical source deck, slide index 74, shape index 12, shape id 2428 (the same
Pinned Messages/Message Actions target Documentation Intelligence Slice 3 used and founder visual
review found formatting-degraded). Engineering acceptance for this benchmark:

- replacement text applied to exactly the correct target run(s);
- every other run/paragraph's formatting (bold "Pin:" label, the bold+underlined "for all
  members" emphasis run, font/size/color) byte-identical to before;
- local relationships correctly identified before the edit is planned (at minimum: the gray
  divider `separates`/`anchored-to`/`depends-on` this shape; the red highlight box `highlights`
  the screenshot it overlaps);
- a bounded reflow plan is computed (empty, in this specific benchmark, since the estimated
  wrapped-line count does not increase — see `verification-report.md` for the exact estimate);
- fit within the existing target container is conservatively established for this benchmark (the
  conservative, mixed-format-aware required-height estimate is within the container's existing
  capacity, floored by the fact that the original text already renders in it today), so the
  PEI-S1-08 refusal path is never exercised by it (that refusal is proven separately, by synthetic
  regressions covering `MSO_AUTO_SIZE.NONE`, `SHAPE_TO_FIT_TEXT`, `TEXT_TO_FIT_SHAPE`, mixed-format
  runs, unresolvable font sizes, and paragraph spacing/line-spacing);
- deterministic safety checks (including swept-path collision, PEI-S1-06) report zero critical
  issues;
- no shape anywhere else in the 170-slide deck changes at all;
- the canonical source `.pptx` is byte-identical before and after (SHA-256 verified);
- a new output `.pptx` is produced — the canonical source is never overwritten.

Visual acceptance (separate, not self-approved by this slice): founder review of the benchmark
output in native Microsoft PowerPoint.

## Non-goals

Full-deck autonomous editing; batch editing across multiple shapes/slides in one call; new-slide
generation; arbitrary redesign or broad modernization of existing slides; the complete
scene-relationship vocabulary (`ordered-before/after`, `repeated-with`, `contained-by` — deferred,
unevidenced this slice); general LLM-driven slide regeneration or semantic understanding; a
full-deck cascading reflow (reflow is bounded to the shapes the relationship graph evidences as
depending on the target, within the local scene only); resizing/repositioning of pictures or
freeform shapes as part of the reflow plan (this slice's reflow only ever shifts a dependent
shape's `top`); **target-container resizing — if fit in the existing target container cannot be
conservatively established, the edit is refused regardless of `auto_size` mode** (Codex
PEI-S1-08), returning `"unresolved"` before any mutation or publication, rather than relying on a
particular `auto_size` value, PowerPoint's own autofit behavior, or attempting a general or
partial resize; **native PowerPoint-perfect text measurement** — the fit estimate remains an
explicitly approximate, conservative heuristic (maximum resolved font size across affected runs,
average glyph width, average line height, paragraph spacing where deterministically available),
never a layout-engine-accurate measurement, and refuses whenever that conservative estimate cannot
be safely resolved rather than attempting to become more precise; claiming production readiness
from one benchmark result — this slice is a pilot, not a general-purpose editing system, and its
own automated checks are not a substitute for founder native-PowerPoint visual review.
