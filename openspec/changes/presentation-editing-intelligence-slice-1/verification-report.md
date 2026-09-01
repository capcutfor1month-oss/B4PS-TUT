# Verification Report — Presentation Editing Intelligence / Scene-Aware Editing, Slice 1

## Status

**Audit chronology:**

1. Codex Audit 1 → **FAIL** (PEI-S1-01 through PEI-S1-07).
2. Repair 1 (builder-implemented).
3. Codex Re-Audit 1 → **FAIL** — 5 findings not actually closed by Repair 1 (PEI-S1-01, PEI-S1-02,
   PEI-S1-06, PEI-S1-07) plus 1 newly identified (PEI-S1-08).
4. Repair 2 (builder-implemented).
5. Codex Re-Audit 2 → **FAIL**, narrowly — 2 findings (PEI-S1-07, PEI-S1-08): Repair 2's
   target-growth refusal activated only for `MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT`, so a fixed-height
   (`MSO_AUTO_SIZE.NONE`) box could still be published with grossly overflowing content.
6. Repair 3 (builder-implemented).
7. Codex final narrow audit → **FAIL**, narrowly — the same 2 findings (PEI-S1-08: Repair 3's fit
   estimate selected a single run's font size to drive the estimate, which underestimates
   mixed-format text — reproduced with an 8pt first run and a 40pt edited run, where the system
   used 8pt and published a replacement whose fit was never conservatively established; PEI-S1-07:
   governance accuracy — conservative-fit claims, current-tree file accounting, and the auto-size
   test description all required correction).
8. Repair 4 (builder-implemented).
9. Codex closure audit → **FAIL**, narrowly again — the same 2 findings (PEI-S1-08: Repair 4's own
   fix introduced a new, distinct type-handling defect — `_paragraph_conservative_line_height_emu`
   checked `isinstance(line_spacing, (int, float))` *before* checking `isinstance(line_spacing,
   Length)`, and every python-pptx absolute-`Length` line-spacing value (e.g. the `Centipoints`
   returned for `paragraph.line_spacing = Pt(12)`) is itself an `int` subclass, so absolute line
   spacing was silently misread as a multiplier, falsely refusing clearly-fitting text; PEI-S1-07:
   three remaining factual problems in this report — the absolute-`Length` line-spacing claim
   describing behavior the code did not yet have, the Repair 4 touched-file count contradicting
   itself ("exactly four" plus two more), and a false claim that the dead `max_lines_that_fit()`
   helper "remains used").
10. Repair 5 (builder-implemented).
11. Codex governance-only re-audit → **FAIL**, narrowly — 1 finding (PEI-S1-07: this report's
    "Repository status" section described Repair 5 as touching "3 of the 19" scope paths in the
    same paragraph that also described `spec.md` as having received a truthfulness correction that
    round — an internal contradiction, since a fourth touched path was described without being
    counted). **PEI-S1-08 was not reopened — Repair 5's `Length`-before-numeric branch-order fix
    held under this re-audit.**
12. Repair 6 (governance-only; **this record**) — corrects only the Repair 5 touched-file count
    contradiction the re-audit named; no implementation or test change.

**Finding status:**

- **PEI-S1-01: CLOSED.** **PEI-S1-02: CLOSED.** **PEI-S1-03: CLOSED.** **PEI-S1-04: CLOSED.**
  **PEI-S1-05: CLOSED.** **PEI-S1-06: CLOSED.** **PEI-S1-08: CLOSED.** (Re-Audit 2, the final
  narrow audit, the closure audit, and the governance-only re-audit did not reopen any of these
  seven.)
- **PEI-S1-07: builder repair implemented; independent closure pending.** This is the fifth
  consecutive round a governance-record defect has been found under this finding (a distinct,
  narrower defect each time: conservative-fit wording, tree accounting, the auto-size test
  description, the Repair 4 file-count self-contradiction, and now the Repair 5 file-count
  self-contradiction) — recorded as pending, not pre-declared PASS.

This record is local, not committed, pushed, or opened as a PR.

## PEI-S1-08 repair (Repair 4)

**Final narrow audit finding:** `pilot.py`'s fit estimate resolved a single font size (via a
now-removed `_dominant_font_size_pt()` helper) and used it for the whole shape's estimate. Codex's
reproduction: a shape whose first run is 8pt and whose edited run is 40pt — the system's estimate
used 8pt, understating the required space, and published the replacement without ever
conservatively establishing that it fit.

**Repair 4:** fit estimation now inspects every run participating in the resulting text and takes
the conservative (largest), never the first-seen, effective size — and refuses outright, before
any mutation, whenever that size cannot be resolved.

- `safety.resolve_conservative_font_size_pt(text_frame)` walks every paragraph and every run in
  the target shape's text frame. For each run, the effective size is the run's own explicit
  `font.size` if set, else the enclosing paragraph's `font.size`. The moment any run's size cannot
  be resolved at either level, the function returns `None` immediately — no partial estimate, no
  first-available-size fallback. Otherwise it returns the **maximum** of all resolved sizes across
  the whole text frame. `pilot.py` calls this once per edit; if it returns `None`, the pilot
  returns `status="unresolved"` with an explicit reason before touching geometry, reflow, or
  mutation at all.
- `safety.estimate_required_height_emu(paragraphs, paragraph_texts, geometry, font_size_pt,
  margin_left_emu, margin_right_emu)` replaces the pure line-count heuristic as the fit
  comparison. For each paragraph it estimates wrapped line count from average glyph width at the
  conservative font size, converts to a line-height in EMU via
  `_paragraph_conservative_line_height_emu` (which honors `paragraph.line_spacing` — a multiplier
  or an absolute `Length`, defaulting to the base line height only when unset), and adds
  `_paragraph_spacing_emu` (`space_before` + `space_after`, where deterministically available, 0
  otherwise) on top. The sum across all paragraphs is the conservative required height.
- `pilot.py` computes `required_height_before` and `required_height_after` this way, compares
  against `safely_available_height = max(usable_height_emu, required_height_before)` — the same
  empirical-floor pattern used in Repair 3, now expressed in EMU of height instead of line count —
  and refuses (`status="unresolved"`) whenever `required_height_after > safely_available_height`.
- The refusal check still never inspects `auto_size` anywhere (Repair 3's fix), and still never
  attempts native PowerPoint-perfect measurement — it is an explicitly approximate,
  average-glyph-width/average-line-height heuristic, now made conservative across mixed formatting
  and paragraph spacing rather than more precise.
- The old single-run `_dominant_font_size_pt()` helper was deleted (dead code once
  `resolve_conservative_font_size_pt` replaced its only call site). `estimate_line_count` (width
  wrap estimate) is retained and still called from `pilot.py` for the softer line-count reporting
  already covered by existing tests; it is not the fit-refusal gate any more —
  `estimate_required_height_emu` is. **Correction (Repair 5, PEI-S1-07):** the previous version of
  this report also claimed `max_lines_that_fit` (Repair 3's height-capacity line-count estimate)
  "remains used" alongside `estimate_line_count`. That claim was false — `max_lines_that_fit` has
  had zero callers, in either `pilot.py` or any test file, since Repair 4 replaced the line-count
  fit gate with `estimate_required_height_emu`. It is confirmed-dead/legacy code, superseded but
  not deleted this round (deleting it is outside this round's narrow PEI-S1-08/07 scope); see
  "Governance correction" below.

## PEI-S1-08 repair (Repair 5)

**Closure audit finding:** Repair 4's own new `_paragraph_conservative_line_height_emu` checked
`isinstance(line_spacing, (int, float))` (the multiplier branch) *before* checking whether
`line_spacing` was an absolute `Length`. Every python-pptx `Length` subclass — including
`Centipoints`, the type `paragraph.line_spacing` actually returns for an absolute value such as
`Pt(12)` — is itself an `int` subclass (`Length.__mro__` is `(Length, int, object)`). The
multiplier branch's `isinstance` check therefore matched absolute values too, and matched them
*first*, so an absolute line spacing of, say, 152,400 EMU (`Pt(12)`) was multiplied against the
base line height instead of used directly — producing an estimate on the order of 10 billion EMU
and refusing text regardless of how obviously it fit.

**Repair 5:** `_paragraph_conservative_line_height_emu` now checks `isinstance(line_spacing,
Length)` **first**, before the generic numeric check, and returns that value directly (floored at
1 EMU) as the absolute per-line height. Only when `line_spacing` is not a `Length` does it fall
through to the plain-`float`/`int` multiplier branch. A bare `int`/`float` that is not a `Length`
instance (e.g. a literal `2.0` multiplier assigned by a caller) still reaches the multiplier
branch correctly, since it is not an instance of `pptx.util.Length`. Verified directly against
python-pptx's real type hierarchy (`pptx.util.Length.__mro__ == (Length, int, object)`;
`type(paragraph.line_spacing).__mro__` after `paragraph.line_spacing = Pt(12)` is `(Centipoints,
Length, int, object)`) before writing the branch order, per the instruction to inspect the actual
type hierarchy rather than guess it.

This is an isolated fix inside `_paragraph_conservative_line_height_emu` only — no other function
in `safety.py` or `pilot.py` was touched, no conservative-fit behavior was weakened (a genuinely
unresolvable format still refuses; a genuinely overflowing fit still refuses; the empirical floor
is unchanged), and no target-container resizing was introduced.

**Why the `required_height_before` floor is still necessary, not a loophole (same principle as
Repair 3, re-applied to height):** the pure heuristic is stricter than the real benchmark slide's
actual, already-published capacity — a purely heuristic height estimate for the real "Pin:"
paragraph structure came in under what the container demonstrably already renders correctly today.
Without the floor, Repair 4's first draft caused the real benchmark to regress to
`"unresolved"` — a real regression, caught and fixed during this round's own test development,
before being reported, exactly as the equivalent Repair 3 regression was. The floor only raises
the bar to what the container demonstrably already holds; it cannot rescue a genuine overflow,
since Codex's 8pt/40pt reproduction (and the paragraph-spacing adversarial case below) both
increase the required height well past any such floor.

## Conservative formatting calculation

Effective font size: **maximum** resolved size across every run in the target text frame, with
paragraph-level `font.size` used only as the per-run fallback when a run has no explicit size of
its own — never the first run, never an average, never a size chosen by which run "looks primary."
If any run's size cannot be resolved at either level (no run-level size and no paragraph-level
default), the whole edit is refused (`status="unresolved"`) rather than estimated with a partial
or assumed size.

Line spacing: `paragraph.line_spacing` is honored where python-pptx exposes it as either a numeric
multiplier (scales the base line height) or an absolute `Length` (used directly, floored at 1
EMU); an unset `line_spacing` (PowerPoint's own default single-spacing) falls back to the base
line height computed from the conservative font size — this is not treated as "unknown," since
single-spacing is the real, deterministic default, not an ambiguous case. **The `Length` check
runs before the numeric-multiplier check (Repair 5, PEI-S1-08)** — every python-pptx `Length`
subclass is also an `int` subclass, so an absolute value would otherwise be caught by the
numeric-multiplier check first and misread as a multiplier; see "PEI-S1-08 repair (Repair 5)"
above. This description reflects the behavior as implemented and test-proven this round, not
merely as intended.

Paragraph spacing: `paragraph.space_before` and `paragraph.space_after`, where set, are added
directly (in EMU) to that paragraph's contribution to the required height; unset spacing
contributes 0, again because PowerPoint's own default is genuinely zero additional spacing, not an
unresolved value.

## Mixed-font adversarial result

`test_mixed_font_8pt_first_run_40pt_edited_run_refuses_on_long_replacement` reproduces Codex's
exact case: an 8pt first run, a 40pt edited run, and a replacement long enough that the correct
(40pt-driven) conservative estimate requires more height than the container has, while the
incorrect (8pt-driven) estimate would have wrongly allowed it. Result: `status="unresolved"`, no
output file written, `mutation_result is None` — the edit is refused before any mutation attempt,
never merely flagged as a warning after publishing.

`test_mixed_fonts_where_conservative_calculation_proves_fit_is_allowed` proves the fix is not
merely "refuse whenever fonts are mixed": a mixed-format shape where even the conservative
(largest-size) calculation still fits comfortably is allowed to apply normally
(`status="applied"`).

`test_unresolvable_edited_run_font_size_refuses` covers the case where the edited run has no
explicit size and its paragraph also has no default size set — `resolve_conservative_font_size_pt`
correctly returns `None`, and the pilot refuses (`status="unresolved"`) rather than guessing.

## Absolute line-spacing result

`test_absolute_line_spacing_that_clearly_fits_is_allowed_not_treated_as_multiplier`: `Pt(12)`
(~152,400 EMU) absolute line spacing on a single short line that obviously fits a 300,000 EMU box.
Under the pre-Repair-5 bug this was multiplied against the base line height (~182,880 EMU),
producing an estimate of ~27.87 billion EMU and a false refusal regardless of the box size.
Result: `status="applied"`.

`test_absolute_line_spacing_that_genuinely_overflows_is_refused`: `Pt(30)` (~381,000 EMU/line)
absolute line spacing; the single-line `before` state comfortably fits (so the empirical floor
does not rescue the case), and the edit grows the text to 2 wrapped lines, which at the real
absolute per-line height genuinely exceeds the container. Result: `status="unresolved"`, no output
written.

## Multiplier line-spacing result

`test_numeric_multiplier_line_spacing_still_behaves_as_a_multiplier`: a plain `float` `line_spacing
= 2.0` (not a `Length` instance) on a single-line `before` state that fits; the edit grows the text
to 2 wrapped lines, and 2 lines at *double* the base line height genuinely overflows the container.
If the multiplier had been misclassified as an absolute EMU value instead (`int(2.0) == 2` EMU per
line), the estimate would collapse to nearly nothing and the edit would incorrectly apply — the
refusal is only possible because the multiplier is still genuinely being applied. Result:
`status="unresolved"`, no output written — confirming the `Length`-first branch reorder did not
regress the ordinary-multiplier path.

`test_space_before_still_contributes_to_required_height_after_the_line_spacing_fix`: a regression
guard mirroring the existing `space_after` adversarial case with `space_before` instead, proving
`_paragraph_spacing_emu` (a separate, untouched function) still contributes correctly after the
`_paragraph_conservative_line_height_emu` branch reorder. Result: `status="unresolved"`.

## Paragraph-spacing behavior

`test_paragraph_spacing_that_materially_increases_required_height_causes_refusal` demonstrates
line-spacing/paragraph-spacing accounting specifically: a container sized so that 2 wrapped lines
alone would fit, but 2 wrapped lines plus a moderate `space_after` would not, while the
single-line, same-spacing "before" state already fits (so the `required_height_before` floor
cannot rescue the case). This required one redesign during this round: the first draft used
before/after text of equal line count, which made `required_height_before` exactly equal
`required_height_after`, silently neutralizing the spacing effect via the floor itself. Fixed by
making the edit itself grow the paragraph from 1 line to 2, isolating the spacing contribution as
the deciding factor. Result: `status="unresolved"`, confirming paragraph spacing is genuinely
incorporated into the estimate, not merely accepted as a parameter that is never load-bearing.

## Governance correction

**This round (Repair 5)** corrects the three specific factual problems the closure audit reported
in this file:

1. **Absolute-`Length` line-spacing claim.** Repair 4's version of this report already described
   `_paragraph_conservative_line_height_emu` as honoring "a numeric multiplier ... or an absolute
   `Length`," but the code at that time did not actually implement that distinction correctly — the
   `Length` case was silently shadowed by the numeric-multiplier check running first (see "PEI-S1-08
   repair (Repair 5)" above). The claim is corrected to describe the behavior only now that Repair
   5's code and the new focused tests (absolute-fits, absolute-overflows, multiplier-still-works)
   actually prove it — the "Conservative formatting calculation" section above now states the
   `Length`-first branch order explicitly, rather than describing intended behavior the
   implementation had not yet delivered.
2. **Repair 4 touched-file count corrected.** The prior version of this report said Repair 4
   "touched exactly 4 of the 19 [paths]" for source/test files and then separately said `spec.md`
   and this file were "also updated ... bringing the total to 6" — an internally contradictory
   framing (a round cannot touch "exactly four" files and then six). The truthful, non-contradictory
   statement: **Repair 4 touched 6 of the 19 scope paths in total** — `safety.py`, `pilot.py`,
   `test_pei_s1_repairs.py`, `test_pilot.py`, `spec.md`, and this file. See "Repository status"
   below for Repair 5's own count, stated the same non-contradictory way.
3. **`max_lines_that_fit()` usage claim corrected.** The prior version of this report claimed
   `max_lines_that_fit` "remains used ... for the softer line-count reporting already covered by
   existing tests," alongside `estimate_line_count`. `grep` across every file in
   `presentation-editing-intelligence/presentation_editing_intelligence/*.py` and
   `presentation-editing-intelligence/tests/*.py` for `max_lines_that_fit` turns up exactly one
   match: its own `def` in `safety.py`. It has no caller in `pilot.py` and no direct test. The
   claim that it "remains used" was false and is corrected above to state plainly that it is
   dead/legacy code — retained from Repair 3, superseded by `estimate_required_height_emu` as of
   Repair 4, and not deleted this round because deleting it is outside this round's narrow
   PEI-S1-08/PEI-S1-07 scope (not because it has any current caller).

Preserved unchanged from prior rounds, per the standing PEI-S1-07 instruction:

- **Full audit chronology** (see "Status" above) — no round removed or reframed as
  resolved-without-independent-confirmation.
- **As of Repair 5 (historical — see "Status" above for the current, superseding finding state):**
  PEI-S1-01 through PEI-S1-06 CLOSED; PEI-S1-07 and PEI-S1-08 both "builder repair implemented;
  independent closure pending." Neither was pre-recorded as PASS at that time.
  **Current authoritative finding state (unchanged since the Codex governance-only re-audit — see
  "Status" above): PEI-S1-01 through PEI-S1-06 and PEI-S1-08 are CLOSED; PEI-S1-07 alone remains
  "builder repair implemented; independent closure pending."** PEI-S1-08 is not pending and is not
  awaiting independent closure; only PEI-S1-07 is.
- **`70 = 51 unrelated + 19 PEI Slice 1`** canonical tree accounting (see "Repository status" below
  for the current entry count, which includes one additional audit-generated artifact not part of
  this scope).
- Founder native-PowerPoint review still pending, not self-approved.
- No production-readiness claim.

## Tests

Added to `presentation-editing-intelligence/tests/test_pei_s1_repairs.py` (new section,
"PEI-S1-08 (final repair): conservative mixed-format fit estimation"):

1. `test_mixed_font_8pt_first_run_40pt_edited_run_refuses_on_long_replacement` — Codex's exact
   reproduction → `status="unresolved"`, no output written.
2. `test_mixed_fonts_where_conservative_calculation_proves_fit_is_allowed` — mixed fonts where the
   conservative (max-size) calculation still fits → `status="applied"`.
3. `test_unresolvable_edited_run_font_size_refuses` — edited run and its paragraph both lack an
   explicit size → `status="unresolved"`.
4. `test_paragraph_spacing_that_materially_increases_required_height_causes_refusal` — spacing
   alone is the deciding factor (see "Paragraph-spacing behavior" above) → `status="unresolved"`.
5. `test_real_benchmark_slide_still_applies_with_conservative_formatting` — the real benchmark,
   re-run under the new conservative formatting resolution → `status="applied"` (skipped if the
   real deck is absent from the working tree).

Also corrected this round (governance/test-accuracy fixes, not new behavior coverage):
`test_unknown_or_unset_autosize_still_refuses_conservatively_on_overflow` renamed to
`test_third_autosize_value_still_refuses_conservatively_on_overflow` and now uses
`MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE` explicitly; the third case in
`test_replacement_that_clearly_fits_existing_container_is_allowed` fixed identically.

Test fixtures fixed (Repair 4): `_build_simple_deck` in both `test_pilot.py` and
`test_pei_s1_repairs.py` previously left one or both runs without an explicit `font.size`; under
the new strict conservative resolution this correctly produced `"unresolved"` for unrelated
pre-existing tests. Fixed by giving both runs an explicit `Pt(12)` size in both copies of the
helper — matching real-world content (confirmed against the real benchmark shape, which always has
explicit run-level sizing), not working around the new check.

**New this round (Repair 5)**, added to `test_pei_s1_repairs.py`:

6. `test_absolute_line_spacing_that_clearly_fits_is_allowed_not_treated_as_multiplier` — Codex's
   type-handling reproduction category → `status="applied"`.
7. `test_absolute_line_spacing_that_genuinely_overflows_is_refused` — absolute spacing that
   genuinely doesn't fit → `status="unresolved"`, no output written.
8. `test_numeric_multiplier_line_spacing_still_behaves_as_a_multiplier` — plain-float multiplier
   still applied correctly after the branch reorder → `status="unresolved"`.
9. `test_space_before_still_contributes_to_required_height_after_the_line_spacing_fix` —
   `space_before` regression guard, independent of the `space_after` case already covered →
   `status="unresolved"`.

**Full suite: 58/58 passed** in `presentation-editing-intelligence/tests/` (54 after Repair 4, net
+4 this round: the 4 new line-spacing/space-before tests above).

## Real benchmark

Same target — slide index 74, shape index 12, shape id 2428 — same `expected_old_text`/`new_text`
(`"Pin:\nMessages bookmarked for all members of the channel to view in the Pinned Messages
list."` + `" (approved test update)"`).

- `status="applied"` under the conservative, mixed-format-aware, paragraph-spacing-aware height
  estimate (Repair 4) with the corrected `Length`-vs-multiplier branch order (Repair 5) — no false
  refusal. The conservative font size resolves cleanly (every run in the shape has an explicit
  size); the pure heuristic required-height estimate alone is stricter than the container's real,
  already-published 4-line capacity, so the `required_height_before` floor (this container already
  holds the original 4-line content today) raises the safely-available height to cover the
  replacement, exactly the same empirical-floor pattern as Repair 3, now computed in EMU of height
  rather than line count. This benchmark slide's real paragraphs do not themselves set an explicit
  `line_spacing`, so the Repair 5 fix does not change this particular result — it is re-run and
  re-confirmed this round purely as a regression check, not because the line-spacing type bug was
  ever expected to affect it.
- Exact replacement: full target text equals `expected_old_text + " (approved test update)"`.
- Run formatting preserved: bold `"Pin:"` and bold+underlined `"for all members"` byte-identical;
  only the trailing run's text changed, still `Calibri`.
- `protected_structure_ok == True` — comprehensive deck-wide verification passed, no unrelated
  mutation anywhere in the 170-slide deck.
- Output reopens correctly in python-pptx; text and formatting confirmed directly by read-back.
- Source integrity: canonical `.pptx` SHA-256 identical before and after.
- Shape geometry unchanged: `(left, top, width, height) == (5308964, 866941, 3474844, 646290)`.
- Zero reflow, zero safety issues (including the swept-path check).

**This automated result is not a visual approval.** Final status remains:

**`FOUNDER NATIVE-POWERPOINT REVIEW REQUIRED`**

## Repository status

**Complete current Presentation Editing Intelligence Slice 1 scope (19 paths, unchanged file set
since Repair 2):**

1. `baseline/B4PS-TUT-main/.b4ps-tools/lib/ppt_engine.py` (modified — additive
   `set_shape_text_runs_and_geometry` primitive only; zero pre-existing lines removed)
2. `baseline/B4PS-TUT-main/.b4ps-tools/tests/test_ppt_engine_text_runs_and_geometry.py`
3. `presentation-editing-intelligence/presentation_editing_intelligence/__init__.py`
4. `presentation-editing-intelligence/presentation_editing_intelligence/_safe_ppt_engine_import.py`
5. `presentation-editing-intelligence/presentation_editing_intelligence/pilot.py`
6. `presentation-editing-intelligence/presentation_editing_intelligence/protected_structure.py`
7. `presentation-editing-intelligence/presentation_editing_intelligence/reflow.py`
8. `presentation-editing-intelligence/presentation_editing_intelligence/relationships.py`
9. `presentation-editing-intelligence/presentation_editing_intelligence/safety.py`
10. `presentation-editing-intelligence/presentation_editing_intelligence/scene.py`
11. `presentation-editing-intelligence/presentation_editing_intelligence/text_edit.py`
12. `presentation-editing-intelligence/presentation_editing_intelligence/text_mutation.py`
13. `presentation-editing-intelligence/tests/test_pei_s1_repairs.py`
14. `presentation-editing-intelligence/tests/test_pilot.py`
15. `presentation-editing-intelligence/tests/test_reflow_and_safety.py`
16. `presentation-editing-intelligence/tests/test_scene_and_relationships.py`
17. `presentation-editing-intelligence/tests/test_text_edit.py`
18. `openspec/changes/presentation-editing-intelligence-slice-1/spec.md`
19. `openspec/changes/presentation-editing-intelligence-slice-1/verification-report.md` (this file)

**Canonical PEI Slice 1 scope accounting: `70 = 51 unrelated + 19 PEI Slice 1`.** The 51 unrelated
entries are pre-existing, untouched by any PEI repair round. The 19 are the exact scope list above.
**Current `git status --short -uall` reports 71 entries** — the canonical 70 plus one untracked,
audit-generated pytest bytecode artifact,
`presentation-editing-intelligence/tests/__pycache__/test_pei_s1_repairs.cpython-314-pytest-9.1.1.pyc`,
produced by running the test suite during this and the prior repair round's verification. This
artifact is not one of the 19 PEI Slice 1 implementation/test paths and must never be counted as a
twentieth — it is build/test output, not source.

**Repair 4 touched 6 of the 19 above (corrected count, see "Governance correction" above):**
`safety.py`, `pilot.py`, `test_pei_s1_repairs.py`, `test_pilot.py`, `spec.md`, and this file.

**Repair 5 touched 4 of the 19 above (corrected count — the prior version of this section said "3
of the 19" in the same paragraph that also described `spec.md` as receiving a fourth, uncounted
change; this was the exact contradiction the governance-only re-audit named):**

1. `presentation-editing-intelligence/presentation_editing_intelligence/safety.py` (isolated fix
   inside `_paragraph_conservative_line_height_emu` only — the `Length`-before-numeric branch
   reorder; no other function changed)
2. `presentation-editing-intelligence/tests/test_pei_s1_repairs.py` (4 new focused regression
   tests)
3. `openspec/changes/presentation-editing-intelligence-slice-1/verification-report.md` (this file
   — the Repair 5 governance corrections)
4. `openspec/changes/presentation-editing-intelligence-slice-1/spec.md` (one truthfulness
   correction to the same absolute-`Length` line-spacing wording)

**Repair 6 (this round, governance-only) touched 1 of the 19 above:** this file only — the
touched-file-count correction directly above. No other section, chronology entry, or finding
status besides the PEI-S1-07 count fix and the PEI-S1-08 status update was changed this round; no
implementation file and no test file were touched. PEI-S1-01 through PEI-S1-06 were **not reopened
or modified** across Repair 5 or Repair 6 — confirmed by `git diff` touching no line in
`relationships.py`, `scene.py`, `text_edit.py`, `protected_structure.py`,
`_safe_ppt_engine_import.py`, `reflow.py`, `__init__.py`, `ppt_engine.py`, `pilot.py`, or
`test_ppt_engine_text_runs_and_geometry.py`. No target-container resizing was added; no reflow
redesign was made; founder visual review has not begun.

**Files inspected this round:** `safety.py` (re-read in full before editing, plus the specific
`_paragraph_conservative_line_height_emu` function); `pilot.py` (re-read to confirm no caller needed
changes); `test_pei_s1_repairs.py` (re-read in full); the real python-pptx type hierarchy for
`Length`/`Centipoints`/`Emu` and `line_spacing` (inspected directly in a Python session — `isinstance`
and `__mro__` checks — before writing the branch order, per the instruction not to guess it); the
real MasterSlide deck's slide 74 shape 12 (re-measured/re-confirmed no explicit `line_spacing` is
set on its paragraphs).

**Skills used:** none — direct file reads/edits and ad hoc Python/pytest verification, matching
every prior round's disclosure.

**Test results (declared dependency environment: `numpy`, `opencv-python-headless`, `Pillow`,
`defusedxml`, `python-pptx`, `pytest` all installed; Safe PPT Engine suite re-run with `TMPDIR`
pointed at a freshly created, isolated temp directory):**

- `presentation-editing-intelligence/tests/`: **58/58 passed**.
- `baseline/B4PS-TUT-main/.b4ps-tools/tests/` (Safe PPT Engine, full suite, isolated `TMPDIR`,
  declared dependencies): **218/218 passed** (unchanged — Repair 5 touched no Safe PPT Engine
  file).
- `documentation-intelligence/tests/`: **216/216 passed** (unchanged).
- `editorial-memory/tests/`: **343/343 passed** (unchanged).
- `python3 -m py_compile` on every changed `.py` file: clean.
- `python3 scripts/check_pipeline.py` → `Bridge4PS target-repository pipeline-adoption checks
  passed.`
- `git diff --check` → clean.
- Layer 0 `is_tree_valid('documentation-artifacts/masterslide/layer0')` → `True`.
- Canonical MasterSlide SHA-256, re-verified after this round: unchanged from every prior round
  (`e461613baae2874eaeede3268fff1aee081c33a04a6bcbb0c7769b94bab16834`).
- Repository state confirmed: `HEAD` unchanged at `d593133ab62780d7c994c56c431a526a030b2b06`;
  nothing staged; nothing committed; nothing pushed; nothing merged. Canonical scope remains `70 =
  51 unrelated + 19 PEI Slice 1` (unchanged file set); **current `git status --short -uall` reports
  71 entries** — the canonical 70 plus one untracked, audit-generated pytest bytecode artifact,
  `presentation-editing-intelligence/tests/__pycache__/test_pei_s1_repairs.cpython-314-pytest-9.1.1.pyc`,
  which is not one of the 19 PEI Slice 1 paths and is not counted as a twentieth.

## Current scope

Unchanged: a bounded, single-slide, scene-aware text-edit pilot. Repair 5 did not add target
resizing (explicitly instructed not to), did not redesign reflow, did not revisit PEI-S1-01 through
PEI-S1-06, and did not begin founder review — it corrected the absolute-line-spacing type-handling
defect Codex's closure audit found in Repair 4's own PEI-S1-08 fix, and corrected the three
specific factual problems in this report's PEI-S1-07 governance record.

## One-benchmark limitation

Unchanged: validated against exactly one real benchmark case. Engineering success here is not a
claim of general production readiness.

## Remaining bounded limitations

- Slice 1 explicitly refuses edits requiring more space than the existing target container can be
  conservatively shown to hold, or whose effective formatting cannot be conservatively resolved
  (PEI-S1-08) — a deliberate, tested, honestly-reported scope boundary, not a silent gap. No
  resizing is implemented or planned within Slice 1.
- The `required_height_before` floor means an edit that keeps the estimated required height at or
  below what the container *already* holds today is always allowed, even where the abstract
  heuristic alone would be stricter — this is a deliberate calibration against known-real content,
  not an exploitable loophole (see "Why the `required_height_before` floor is still necessary"
  above); a genuine overflow (Codex's 8pt/40pt case, or the paragraph-spacing adversarial case)
  clears the floor by construction.
- The height/fit estimate remains an explicitly approximate average-glyph-width and
  average-line-height heuristic, now conservative across mixed run formatting and paragraph
  spacing, but still not real font metrics or a layout engine — Slice 1 deliberately does not
  attempt native PowerPoint-perfect measurement.
- Reflow still never cascades beyond the local reasoning scene; group-member extraction remains
  deferred (PEI-S1-05, unchanged).

## Next gate

Independent Codex closure re-audit of this narrow, governance-only repair (**PEI-S1-07 only** —
PEI-S1-01 through PEI-S1-06 and PEI-S1-08 are not expected to be re-examined, having already been
recorded CLOSED). Separately, unconditionally: `FOUNDER NATIVE-POWERPOINT REVIEW REQUIRED` on the
already-verified benchmark output — not self-approved by this record, and founder visual review
does not begin until Codex confirms closure.
