"""Formatting-preserving text replacement planning.

The old Documentation Intelligence Slice 3 mutation path set
`shape.text_frame.text = new_text` directly. That setter destroys every
paragraph and run in the text frame and replaces them with a single new
paragraph/run carrying only default formatting - founder visual review of
the resulting real-deck edit confirmed this: bold/underline distinctions,
multi-run structure, and paragraph breaks were all lost.

The fix used here does not touch `TextFrame.text` at all. python-pptx's
`Run.text` setter only rewrites that run's `<a:t>` text node - it leaves
the run's own `<a:rPr>` (bold/italic/underline/size/color/font name)
completely untouched. So "preserve formatting" reduces to: identify the
*smallest* set of existing runs that must change to turn the old full
text into the new full text, and only ever call `run.text = ...` on
exactly those runs - never on any other run, and never by rebuilding the
paragraph/run tree.

This module is pure Python - it operates on a plain `RunSpan` list, not
on python-pptx objects - so it is unit-testable with synthetic fixtures
with no `.pptx` file involved anywhere. `text_mutation.py` is the thin
layer that reads a real shape into this shape and applies the resulting
plan back onto it.
"""

from __future__ import annotations

import dataclasses
from typing import List, Optional, Sequence


@dataclasses.dataclass(frozen=True)
class RunSpan:
    """One run's identity and current text, as it exists in the source
    shape right now. `paragraph_index`/`run_index` are 0-based positions
    within the text frame; both are required so the plan can be applied
    back to the exact run it was computed against, never by re-locating
    text after the fact.

    `format_signature` (Codex PEI-S1-03): an opaque, comparable tuple of
    this run's formatting (e.g. `(bold, italic, underline, size, color,
    font_name)`) - only ever used to compare two *adjacent* runs at a
    zero-width insertion boundary for equality, never interpreted or
    unpacked by this module. `None` means "formatting unknown to the
    caller" and is treated as never equal to anything (including another
    `None`) - an ambiguous boundary with unknown formatting is refused,
    not guessed past."""

    paragraph_index: int
    run_index: int
    text: str
    format_signature: Optional[tuple] = None


@dataclasses.dataclass(frozen=True)
class RunEdit:
    """One run whose text must change, and to what. Every other run in
    the frame is implicitly unchanged - a `RunEdit` never carries any
    formatting of its own, because none is meant to change."""

    paragraph_index: int
    run_index: int
    new_text: str


@dataclasses.dataclass(frozen=True)
class EditPlan:
    """Result of planning a formatting-preserving replacement.

    `status` is either `"resolved"` (exactly one run must change; safe to
    apply) or `"unresolved"` (the requested change cannot be localized to
    a single existing run without guessing at formatting for newly
    introduced text spanning a run boundary; `reason` explains why, and
    `edits` is always empty in that case)."""

    status: str
    edits: List[RunEdit]
    reason: Optional[str] = None


def plan_single_run_replacement(
    runs: Sequence[RunSpan], expected_old_text: str, new_text: str
) -> EditPlan:
    """Plans a formatting-preserving edit for one shape's text frame.

    `runs` must be every run in the frame, in document order (paragraph
    order, then run order within each paragraph) - the same order
    `TextFrame.text` itself concatenates them in (paragraph breaks as
    `"\\n"`, run texts within a paragraph directly concatenated with no
    separator, matching python-pptx's own reconstruction).

    `expected_old_text` is the caller's belief about the frame's current
    full text (typically an already-approved edit's recorded "before"
    value). If it does not match what `runs` actually reconstructs to,
    this returns `unresolved` rather than proceeding against stale
    assumptions about the frame's content - the caller's edit was
    approved against a specific "before" state, and that state has
    apparently changed.

    The plan is resolved only when the character-level diff between old
    and new text is confined entirely within one existing run's span (an
    append, a prepend, or a same-position substitution wholly inside one
    run). If the changed span crosses a run or paragraph boundary, or
    would require inventing formatting for genuinely new structure (e.g.
    a whole new paragraph), this returns `unresolved` - it never guesses.
    """
    reconstructed = _reconstruct(runs)
    if reconstructed != expected_old_text:
        return EditPlan(
            status="unresolved",
            edits=[],
            reason=(
                "expected_old_text does not match the shape's actual current "
                "text - the shape has changed since this edit was approved"
            ),
        )

    if new_text == expected_old_text:
        return EditPlan(status="unresolved", edits=[], reason="no textual change requested")

    if not runs:
        return EditPlan(status="unresolved", edits=[], reason="text frame has no runs to edit")

    prefix_len = _common_prefix_len(expected_old_text, new_text)
    suffix_len = _common_suffix_len(expected_old_text, new_text, prefix_len)

    old_change_start = prefix_len
    old_change_end = len(expected_old_text) - suffix_len
    new_change_start = prefix_len
    new_change_end = len(new_text) - suffix_len

    # A run "contains" the changed range [old_change_start, old_change_end)
    # when the range fits entirely within its own [run_start, run_end]
    # closed span. Runs are contiguous and non-overlapping, so for a
    # non-empty range at most one run can ever qualify. For a zero-width
    # range (a pure insertion) exactly two adjacent runs can both qualify
    # only when the insertion point sits precisely on the shared boundary
    # between them. An insertion at the very start of the whole frame
    # naturally matches only the first run (no earlier run exists to
    # share that boundary); an insertion at the very end naturally
    # matches only the last run, for the same reason - no special-casing
    # needed for either of those two cases.
    run_spans = _run_char_spans(runs)  # [(run_start, run_end), ...] over the "\n"-joined text
    candidates: List[int] = []
    for i, (run_start, run_end) in enumerate(run_spans):
        if run_start <= old_change_start and old_change_end <= run_end:
            candidates.append(i)

    if not candidates:
        return EditPlan(
            status="unresolved",
            edits=[],
            reason=(
                "the changed text span crosses more than one existing run's "
                "boundary; a formatting-preserving edit requires the change "
                "to be confined to exactly one existing run"
            ),
        )

    if len(candidates) > 1:
        # Codex PEI-S1-03: a genuinely ambiguous zero-width insertion at a
        # shared run boundary is never arbitrarily assigned to the
        # earlier (or later) run. It resolves only when every candidate
        # run's formatting signature is known and identical - in that
        # case which run's `.text` gets extended is visually
        # indistinguishable, so the choice is safe, not a guess. Any
        # unknown or differing signature refuses rather than picks a side.
        signatures = [runs[i].format_signature for i in candidates]
        if any(sig is None for sig in signatures) or len(set(signatures)) != 1:
            return EditPlan(
                status="unresolved",
                edits=[],
                reason=(
                    "the insertion point sits on the boundary between %d adjacent runs "
                    "with unknown or differing formatting - a formatting-preserving edit "
                    "cannot determine which run's formatting the new text should inherit"
                    % len(candidates)
                ),
            )

    run_pos = candidates[0]
    target_run = runs[run_pos]
    run_start = run_spans[run_pos][0]
    local_start = old_change_start - run_start
    local_end = old_change_end - run_start
    new_run_text = target_run.text[:local_start] + new_text[new_change_start:new_change_end] + target_run.text[local_end:]

    if "\n" in new_run_text:
        # A real new paragraph break requires an actual new <a:p> element
        # with its own (inherited-or-guessed) formatting - a single run's
        # <a:t> text node cannot represent one. Refuse rather than embed
        # a literal newline character that would not render as intended.
        return EditPlan(
            status="unresolved",
            edits=[],
            reason=(
                "the requested change would introduce a new paragraph break "
                "inside a single run's text, which cannot be represented "
                "without fabricating new paragraph structure"
            ),
        )

    return EditPlan(
        status="resolved",
        edits=[
            RunEdit(
                paragraph_index=target_run.paragraph_index,
                run_index=target_run.run_index,
                new_text=new_run_text,
            )
        ],
    )


def _run_char_spans(runs: Sequence[RunSpan]) -> List[tuple]:
    """Each run's `(start, end)` character offsets within the same
    `"\\n"`-joined flat text `_reconstruct()` produces - a paragraph
    break consumes one character position between the previous
    paragraph's last run and this paragraph's first run, exactly as
    `TextFrame.text`'s own `"\\n"` join does."""
    spans: List[tuple] = []
    offset = 0
    current_paragraph = runs[0].paragraph_index if runs else 0
    for run in runs:
        if run.paragraph_index != current_paragraph:
            offset += 1  # the "\n" between paragraphs
            current_paragraph = run.paragraph_index
        start = offset
        end = offset + len(run.text)
        spans.append((start, end))
        offset = end
    return spans


def _reconstruct(runs: Sequence[RunSpan]) -> str:
    if not runs:
        return ""
    parts: List[str] = []
    current_paragraph = runs[0].paragraph_index
    for run in runs:
        if run.paragraph_index != current_paragraph:
            parts.append("\n")
            current_paragraph = run.paragraph_index
        parts.append(run.text)
    return "".join(parts)


def _common_prefix_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _common_suffix_len(a: str, b: str, prefix_len: int) -> int:
    """Common suffix length, capped so the suffix can never overlap the
    already-computed prefix (standard minimal-diff convention: prefix and
    suffix partition each string without overlapping)."""
    cap = min(len(a), len(b)) - prefix_len
    i = 0
    while i < cap and a[len(a) - 1 - i] == b[len(b) - 1 - i]:
        i += 1
    return i
