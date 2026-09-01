"""Bounded local reflow planning.

When an edit changes the target shape's occupied height or width, some
nearby shapes may need to move to avoid overlapping it or leaving an
inconsistent gap. This module does **not** implement "move everything
below the text box" - it walks the shape chain that the relationship
graph (`relationships.py`) actually evidenced as stacked against the
target (a divider `anchored-to`/`depends-on` the target, then whatever
sits immediately after that divider, and so on), and stops the moment the
chain runs out of evidenced neighbors or leaves the local scene. Shapes
outside that evidenced chain are never touched, even if they happen to
be geometrically "below" the target somewhere on the slide.

This planner only ever proposes a vertical shift (`top` changes by the
same signed delta for every dependent) - it never resizes a dependent
shape, and it never touches horizontal position. That is the smallest
mechanism that correctly keeps a chain of stacked shapes non-overlapping
after one shape in the chain grows or shrinks vertically.
"""

from __future__ import annotations

import dataclasses
from typing import Dict, List, Optional

from .relationships import Relationship
from .scene import Geometry, LocalScene, SceneShape

_CHAIN_GAP_TOLERANCE_EMU = 300_000  # ~0.33in: still "the next thing in the stack"


@dataclasses.dataclass(frozen=True)
class ReflowMove:
    shape_id: int
    shape_index: int
    delta_top_emu: int
    new_top_emu: int  # absolute EMU top after the move - the Safe PPT Engine's
                       # own geometry primitives take absolute values, never deltas
    reason: str


@dataclasses.dataclass(frozen=True)
class ReflowPlan:
    moves: List[ReflowMove]
    delta_height_emu: int
    delta_width_emu: int

    @property
    def is_noop(self) -> bool:
        return not self.moves and self.delta_height_emu == 0 and self.delta_width_emu == 0


def plan_reflow(
    scene: LocalScene,
    relationships: List[Relationship],
    target_new_geometry: Geometry,
) -> ReflowPlan:
    """Builds a bounded reflow plan for the target's geometry change.

    Only vertical growth/shrink is handled (the only case this slice's
    formatting-preserving text edits can produce - width never changes
    from a text edit). If the target's width also changed here, no
    horizontal dependents are computed - `delta_width_emu` is reported
    for the caller's own safety checks, but no shape is moved
    horizontally by this planner, since no evidenced horizontal-stacking
    relationship exists in this slice's vocabulary.
    """
    target = scene.target
    delta_height = target_new_geometry.height - target.geometry.height
    delta_width = target_new_geometry.width - target.geometry.width

    if delta_height == 0:
        return ReflowPlan(moves=[], delta_height_emu=delta_height, delta_width_emu=delta_width)

    by_id: Dict[int, SceneShape] = {s.shape_id: s for s in scene.shapes}

    # The chain starts at whichever shape(s) `depends-on` the target
    # directly (evidenced: a divider anchored to the target's bottom
    # edge). From there, each further link is the shape `separates`
    # names as the *other* side of that same divider, if it is also
    # present in the local scene.
    direct_dependents = [
        r.source_shape_id for r in relationships
        if r.relation_type == "depends-on" and r.target_shape_id == target.shape_id
    ]

    moves: List[ReflowMove] = []
    visited = {target.shape_id}
    frontier = list(direct_dependents)
    chain_reason = {sid: "depends-on the edited shape (anchored divider)" for sid in direct_dependents}

    while frontier:
        shape_id = frontier.pop(0)
        if shape_id in visited or shape_id not in by_id:
            continue
        visited.add(shape_id)
        original_top = by_id[shape_id].geometry.top
        moves.append(ReflowMove(
            shape_id=shape_id,
            shape_index=by_id[shape_id].shape_index,
            delta_top_emu=delta_height,
            new_top_emu=original_top + delta_height,
            reason=chain_reason.get(shape_id, "part of the evidenced local stacking chain"),
        ))

        # Continue the chain: whatever this shape `separates` (its other
        # side) is the next link, if it's a genuine forward continuation
        # (positioned below what's already in the chain, within the
        # chain-gap tolerance) and still inside the local scene.
        current_shape = by_id[shape_id]
        for r in relationships:
            if r.relation_type != "separates" or r.source_shape_id != shape_id:
                continue
            next_id = r.target_shape_id
            if next_id in visited or next_id not in by_id:
                continue
            next_shape = by_id[next_id]
            if next_shape.geometry.top < current_shape.geometry.bottom:
                continue  # not a forward (downward) continuation
            gap = next_shape.geometry.top - current_shape.geometry.bottom
            if gap <= _CHAIN_GAP_TOLERANCE_EMU:
                frontier.append(next_id)
                chain_reason[next_id] = (
                    "next shape in the evidenced stacking chain after shape id %d" % shape_id
                )

    moves.sort(key=lambda m: by_id[m.shape_id].geometry.top)
    return ReflowPlan(moves=moves, delta_height_emu=delta_height, delta_width_emu=delta_width)
