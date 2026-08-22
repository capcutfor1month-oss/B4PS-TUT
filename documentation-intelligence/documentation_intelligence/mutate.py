"""Documentation Intelligence - Slice 3: Controlled PPT Mutation Handoff.

Implements the approved Slice 3 specification
(`openspec/changes/documentation-intelligence-slice-3/spec.md`). Given one
already-approved replacement text and one already-resolved structural
target (`slide_index`, `shape_index`, optionally `shape_id` as a guard -
typically Slice 2's own `LocateResult`), safely produces a new `.pptx` by
reusing the existing, unmodified Safe PPT Engine `set_shape_text()`.
Answers exactly one question: "given this exact approved text and this
exact target, can we safely produce the updated PPT?"

Locked boundaries this module enforces in code, not only documentation:

- Exactly one mutation primitive - `set_shape_text()`, reused unmodified.
  No second text-mutation mechanism exists anywhere in this module.
- No judgment about whether `replacement_text` is correct - it is
  assumed already human-approved before this function is ever called.
- No re-targeting, fuzzy recovery, or Slice 2 involvement of any kind -
  this module never imports `documentation_intelligence.locate`. If the
  target has drifted (out of range, or a `shape_id` mismatch), this
  module fails explicitly rather than guessing.
- No Editorial Memory access - this function takes no `EditorialMemory`
  handle and performs no retrieval or write of any kind.
- `overwrite` is hardcoded `False` - this slice never overwrites an
  existing output path or the source; the first founder test produces a
  separate output `.pptx`.

History (Codex Audit 1 findings DI-S3-01/DI-S3-02, repaired):

DI-S3-01: the original post-mutation verification compared shapes via a
single `zip()` over `(before_shapes, after_shapes)`, which silently
truncates to the shorter sequence - a trailing shape or trailing slide
disappearing entirely would never surface as a discrepancy, and the
target's own resulting text was never explicitly compared against
`replacement_text` (only implicitly trusted via what `inspect_deck()`
happened to report). Fixed: `_verify_mutation()` now explicitly checks,
in order, slide count equality, per-slide shape count equality, per-slide
shape-id sequence equality (a stable identity/correspondence check before
any content is compared), the target's exact text against
`replacement_text`, and every non-target shape's text against its
before-value - each check raising the existing, reused `ValidationError`
on any discrepancy, with no fuzzy matching, searching, recovery, or
retargeting anywhere in this function.

DI-S3-02: `set_shape_text()` already publishes its output (atomically,
per its own existing contract) before this slice's own additional
verification ever runs - so a verification failure previously left a
real, published-but-unverified `.pptx` behind on disk. First fixed
(Repair Round 1) by removing the output on a verification failure
whenever `output_deck_path` had not existed before the call.

Codex Re-audit 1 (DI-S3-02, still PARTIAL) reproduced a race that fix
did not cover: between `set_shape_text()` publishing this call's own
output and this function's cleanup running, some other process could
atomically replace whatever now occupies `output_deck_path` with an
unrelated artifact - "did the path exist before" says nothing about
whether the file *currently* at that path is still the one this call
itself created, so a naive `os.remove(output_deck_path)` could delete
someone else's file.

Fixed here: this function now establishes the *identity* of the file it
just published - `(st_dev, st_ino)`, the standard POSIX device+inode
pair, captured via `os.stat()` immediately after `set_shape_text()`
returns - and, before any cleanup removal, re-stats `output_deck_path`
and compares. Removal proceeds only when the current occupant's identity
still matches what this call published; a rename preserves this
identity, but a delete-and-recreate (or a replace) at the same pathname
does not, so a since-replaced file is left completely untouched. This is
the smallest mechanism the platform actually offers for "is this still
the same file" without redesigning Safe PPT Engine's own atomic-publish
step (which already uses the same inode-stability property internally,
via `os.link`, for its own publication) - it narrows the cleanup race to
the single unavoidable gap between the identity re-check and the
`os.remove()` call itself, which no path-based POSIX API can close
further without an OS-specific mechanism this repository does not
depend on anywhere else.

If the cleanup `os.remove()` call itself fails, a new `OutputCleanupError`
is raised - chained (`raise ... from`) onto the original verification
failure, so both failure contexts are preserved: the verification
failure as this exception's `__cause__`, the cleanup failure in this
exception's own message. The source is never touched by any part of this
cleanup path.
"""

from __future__ import annotations

import dataclasses
import os
from typing import Optional

from ._safe_ppt_engine_import import MutationError, ValidationError, inspect_deck, set_shape_text

__all__ = [
    "MutationResult",
    "ShapeIdMismatchError",
    "OutputCleanupError",
    "apply_approved_replacement",
]


class ShapeIdMismatchError(MutationError):
    """Raised when a caller-supplied `shape_id` guard does not match the
    shape actually found at `(slide_index, shape_index)` in the source
    deck. This is the explicit "do not guess or retarget" failure path -
    the deck's structure has drifted since the target was resolved, and
    this module refuses to silently proceed against the wrong shape."""


class OutputCleanupError(MutationError):
    """Raised only when Slice 3's own post-mutation verification failed
    AND the subsequent removal of the newly-created (now-unverified)
    output could not be completed. The original verification failure is
    preserved as this exception's `__cause__`; the cleanup failure itself
    is in this exception's own message. The source deck, and any output
    path that already existed before this call, are never touched by the
    cleanup attempt this error reports on."""


@dataclasses.dataclass
class MutationResult:
    """The full Slice 3 output for a successful, verified mutation.
    Getting a `MutationResult` back *is* the success signal - every
    precondition or verification failure raises a typed error instead
    (see the module docstring); this dataclass is never constructed on a
    failure path."""

    status: str  # always "applied" - see class docstring
    output_path: str
    slide_index: int
    shape_index: int
    shape_id: int
    previous_text: Optional[str]
    new_text: str

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "output_path": self.output_path,
            "slide_index": self.slide_index,
            "shape_index": self.shape_index,
            "shape_id": self.shape_id,
            "previous_text": self.previous_text,
            "new_text": self.new_text,
        }


def _file_identity(path: str):
    """The POSIX `(st_dev, st_ino)` pair identifying the actual file
    currently at `path` - survives a rename, but not a delete-and-
    recreate (or replace) at the same pathname. Returns `None` if `path`
    cannot be stat'd (already gone). Used only to confirm, immediately
    before a cleanup removal, that the file this call is about to delete
    is still the exact artifact it itself published - never to identify
    or compare content."""
    try:
        stat_result = os.stat(path)
    except OSError:
        return None
    return (stat_result.st_dev, stat_result.st_ino)


def _resolve_shape_info(structure: dict, slide_index: int, shape_index: int) -> dict:
    """Mirrors the Safe PPT Engine's own `_resolve_shape()` bounds
    checking and error wording exactly, over `inspect_deck()`'s already-
    computed structure - so an out-of-range target raises the same typed
    `MutationError`, with the same message shape, regardless of whether
    the engine's own preflight or this slice's own guard check is what
    happens to catch it first."""
    slides = structure["slides"]
    if not 0 <= slide_index < len(slides):
        raise MutationError(
            "slide_index %d out of range (deck has %d slide(s))"
            % (slide_index, len(slides))
        )
    shapes = slides[slide_index]["shapes"]
    if not 0 <= shape_index < len(shapes):
        raise MutationError(
            "shape_index %d out of range (slide %d has %d shape(s))"
            % (shape_index, slide_index, len(shapes))
        )
    return shapes[shape_index]


def _verify_mutation(before_structure: dict, after_structure: dict,
                      slide_index: int, shape_index: int, replacement_text: str) -> None:
    """Structurally complete post-mutation verification (Codex DI-S3-01).
    Never uses a bare `zip()` over possibly-unequal-length sequences -
    every count is checked explicitly first, so a removed trailing slide
    or shape can never silently escape detection. Raises `ValidationError`
    (reused, unmodified) on the first discrepancy found; never attempts
    to search, recover, or retarget."""
    before_slides = before_structure["slides"]
    after_slides = after_structure["slides"]

    if len(before_slides) != len(after_slides):
        raise ValidationError(
            "slide count changed: expected %d, got %d"
            % (len(before_slides), len(after_slides))
        )

    for s_idx in range(len(before_slides)):
        before_shapes = before_slides[s_idx]["shapes"]
        after_shapes = after_slides[s_idx]["shapes"]

        if len(before_shapes) != len(after_shapes):
            raise ValidationError(
                "shape count changed on slide %d: expected %d, got %d"
                % (s_idx, len(before_shapes), len(after_shapes))
            )

        # Stable shape correspondence/identity, verified before any
        # content is compared - `shape_id` is the OOXML-stable
        # identifier `inspect_deck()` already reports per shape.
        before_ids = [shape["shape_id"] for shape in before_shapes]
        after_ids = [shape["shape_id"] for shape in after_shapes]
        if before_ids != after_ids:
            raise ValidationError(
                "shape identity/order changed on slide %d: expected "
                "shape_id sequence %r, got %r" % (s_idx, before_ids, after_ids)
            )

        for sh_idx in range(len(before_shapes)):
            is_target = (s_idx, sh_idx) == (slide_index, shape_index)
            after_text = after_shapes[sh_idx].get("text")
            if is_target:
                if after_text != replacement_text:
                    raise ValidationError(
                        "target shape at slide %d shape %d does not contain "
                        "the exact replacement text after mutation"
                        % (s_idx, sh_idx)
                    )
            else:
                before_text = before_shapes[sh_idx].get("text")
                if before_text != after_text:
                    raise ValidationError(
                        "unrelated shape text changed outside the intended "
                        "target at slide %d shape %d" % (s_idx, sh_idx)
                    )


def apply_approved_replacement(
    source_deck_path: str,
    output_deck_path: str,
    slide_index: int,
    shape_index: int,
    replacement_text: str,
    shape_id: Optional[int] = None,
) -> MutationResult:
    """Slice 3's one entry point.

    Verifies the target still matches what the caller expects (raising
    the Safe PPT Engine's own typed `MutationError`/`DeckSourceError` for
    a missing deck or out-of-range target, and this module's own
    `ShapeIdMismatchError` for a `shape_id` guard mismatch), applies
    exactly one `set_shape_text()` call, reopens and structurally
    verifies the result (see `_verify_mutation()`), and returns a
    deterministic `MutationResult`. Never writes to `source_deck_path`'s
    deck; never overwrites `output_deck_path` if it already exists.

    If `set_shape_text()` itself fails, nothing is published and this
    function raises its typed error unmodified - unchanged from before.
    If `set_shape_text()` succeeds (a real file now exists at
    `output_deck_path`) but this function's own additional verification
    then fails, the file currently at `output_deck_path` is removed
    before the verification error propagates - but only if it is still,
    by POSIX device+inode identity, the exact file this call itself
    published (Codex DI-S3-02, including the Re-audit 1 ownership-race
    finding). If something else has since replaced it, it is left
    completely untouched. See `OutputCleanupError` if the removal itself
    fails.
    """
    before_structure = inspect_deck(source_deck_path)
    target_before = _resolve_shape_info(before_structure, slide_index, shape_index)

    if shape_id is not None and target_before["shape_id"] != shape_id:
        raise ShapeIdMismatchError(
            "shape_id guard mismatch at slide %d shape %d: expected %r, found %r"
            % (slide_index, shape_index, shape_id, target_before["shape_id"])
        )

    previous_text = target_before.get("text")

    set_shape_text(
        source_deck_path,
        output_deck_path,
        slide_index,
        shape_index,
        replacement_text,
        overwrite=False,
    )

    published_identity = _file_identity(output_deck_path)

    try:
        after_structure = inspect_deck(output_deck_path)
        _verify_mutation(before_structure, after_structure, slide_index, shape_index, replacement_text)
    except Exception as verification_error:
        current_identity = _file_identity(output_deck_path)
        if current_identity is not None and current_identity == published_identity:
            try:
                os.remove(output_deck_path)
            except OSError as cleanup_error:
                raise OutputCleanupError(
                    "post-mutation verification failed (%s) and cleanup of "
                    "the newly-created output %r also failed (%s)"
                    % (verification_error, output_deck_path, cleanup_error)
                ) from verification_error
        raise

    target_after = after_structure["slides"][slide_index]["shapes"][shape_index]

    return MutationResult(
        status="applied",
        output_path=output_deck_path,
        slide_index=slide_index,
        shape_index=shape_index,
        shape_id=target_after["shape_id"],
        previous_text=previous_text,
        new_text=target_after["text"],
    )
