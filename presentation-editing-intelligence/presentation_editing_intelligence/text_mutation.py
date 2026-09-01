"""The mechanical execution layer for a scene-aware edit.

Codex finding PEI-S1-01 (FAIL): the previous version of this module
reimplemented its own staging/publication transaction, including an
`overwrite=False` check that raced a plain `os.path.exists()` test
against the actual publish - a competing writer could create the
destination between the check and this module's own `os.replace()` call,
which (unlike the audited engine's `os.link`-based no-clobber path) would
silently replace it regardless of the `overwrite` policy.

Fixed by deleting that second transaction protocol entirely. This module
now does exactly one thing: translate this package's own plan objects
(`RunEdit`, `ReflowMove`) into the plain tuples
`ppt_engine.set_shape_text_runs_and_geometry` accepts, call it, and
translate its result back. All staging, publication, no-clobber
enforcement, typed failures, cleanup, and the source-integrity gate are
the Safe PPT Engine's own responsibility, unchanged and unweakened -
Presentation Editing Intelligence decides *what* to change; the engine
remains the only thing that ever writes a `.pptx`.

Codex re-audit finding PEI-S1-01 (FAIL again): Repair 1 still checked
`expected_shape_id` in this module, before calling the engine - a TOCTOU
race (the source could be swapped between that check and the engine
actually staging/mutating it). Fixed: this module no longer performs any
identity check of its own; `expected_shape_id` is passed straight through
to the engine primitive, which validates it against the staged copy,
inside the transaction, immediately before mutation. See
`ppt_engine.set_shape_text_runs_and_geometry`'s own docstring.
"""

from __future__ import annotations

import dataclasses
from typing import List, Optional

from ._safe_ppt_engine_import import (
    MutationError,
    OutputPathError,
    SafeDeckError,
    ValidationError,
    set_shape_text_runs_and_geometry as _engine_apply,
)
from .reflow import ReflowMove
from .text_edit import RunEdit

# Re-exported so callers of this module never need to import the engine
# bridge directly - these are the engine's own typed errors, unmodified.
__all__ = [
    "MutationResult",
    "MutationError",
    "OutputPathError",
    "SafeDeckError",
    "ValidationError",
    "apply_scene_aware_text_edit",
]


@dataclasses.dataclass
class MutationResult:
    output_path: str
    slide_index: int
    shape_index: int
    applied_run_edits: List[RunEdit]
    applied_reflow_moves: List[ReflowMove]


def apply_scene_aware_text_edit(
    source_deck_path: str,
    output_deck_path: str,
    slide_index: int,
    shape_index: int,
    run_edits: List[RunEdit],
    reflow_moves: Optional[List[ReflowMove]] = None,
    expected_shape_id: Optional[int] = None,
    overwrite: bool = False,
) -> MutationResult:
    """Applies one formatting-preserving run edit plus its (possibly
    empty) reflow plan as a single atomic output, entirely through the
    Safe PPT Engine's own audited transaction boundary.

    `expected_shape_id`, if given, is passed straight through to the
    engine primitive's own `expected_shape_id` guard (Codex finding
    PEI-S1-01, re-audit) - it is validated there against the shape
    actually resolved on the **staged copy**, inside the same
    transaction, immediately before any mutation. This function
    deliberately performs **no** pre-transaction identity check of its
    own: a check against a separate read-only load taken before the
    engine call has a TOCTOU window (the source file could be swapped
    between that check and the engine actually staging/mutating it) that
    a caller-side guard cannot close - only validating on the staged copy
    itself, inside the one transaction that mutates it, closes it.
    """
    reflow_moves = reflow_moves or []

    engine_run_edits = [(e.paragraph_index, e.run_index, e.new_text) for e in run_edits]
    engine_geometry_moves = [
        (m.shape_index, m.shape_id, m.new_top_emu) for m in reflow_moves
    ]

    _engine_apply(
        source_deck_path,
        output_deck_path,
        slide_index,
        shape_index,
        run_edits=engine_run_edits,
        geometry_moves=engine_geometry_moves,
        overwrite=overwrite,
        expected_shape_id=expected_shape_id,
    )

    return MutationResult(
        output_path=output_deck_path,
        slide_index=slide_index,
        shape_index=shape_index,
        applied_run_edits=list(run_edits),
        applied_reflow_moves=list(reflow_moves),
    )
