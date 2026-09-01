"""Deterministic relationship inference over a `LocalScene`.

Implements the bounded relationship vocabulary this slice supports:
`belongs-to`, `points-to`, `highlights`, `separates`, `anchored-to`,
`aligned-with`, `depends-on`. Every inferred relationship carries its
source/target shape ids, a `confidence` (`HIGH`/`MEDIUM`/`LOW`), and
`evidence` - the concrete geometric/structural facts that produced it.

Codex finding PEI-S1-04 (FAIL, repaired): confidence calibration is now
strictly enforced - `HIGH` is reserved for an explicit OOXML structural
binding (currently: a real `<a:stCxn>`/`<a:endCxn>` connector endpoint
reference). Every other relationship - including `separates`/
`anchored-to`/`depends-on` (geometry-only adjacency) and `highlights`
(color + geometry overlap - color is never treated as semantic authority
on its own) - is capped at `MEDIUM`. Weak, proximity-only evidence
(`aligned-with`, the geometry-proxy fallback for `points-to`/`belongs-to`)
remains `MEDIUM` or `LOW` as before. See `_MAX_CONFIDENCE_WITHOUT_STRUCTURAL_BINDING`.

Codex finding PEI-S1-05 (FAIL, repaired): `moves-with` and group-based
inference are **not implemented** in this slice. `scene.py`'s
`SceneShape.group_shape_index` is not populated by scene extraction (see
that module's own docstring) - claiming a `moves-with` relationship based
on it would be an unreachable, untruthful capability claim. Group-member
extraction (which requires re-basing each member's coordinates through
its group's `chOff`/`chExt` transform) is deferred to a future slice, per
the smaller-safe-option instruction; nothing in this module or its
callers claims group support.

This module never asserts a relationship it cannot point to concrete
evidence for. A shape with no qualifying evidence simply gets no
relationship - it is not forced into the nearest available category.
"""

from __future__ import annotations

import dataclasses
from typing import List, Optional

from .scene import LocalScene, SceneShape

# Tolerances are deliberately named constants, not magic numbers scattered
# through the logic - and are generic thresholds, not tuned to any one
# slide's specific shape ids.
_ADJACENCY_GAP_EMU = 150_000          # ~0.16in: "immediately below/above"
_ALIGNMENT_TOLERANCE_EMU = 40_000      # ~0.04in: "same edge, allowing for rounding"
_ENDPOINT_PROXIMITY_EMU = 250_000      # ~0.27in: "this endpoint is at that shape"

_SATURATED_COLORS = {"FF0000"}  # red - the founder-approved highlight/attention color


@dataclasses.dataclass(frozen=True)
class Relationship:
    source_shape_id: int
    target_shape_id: int
    relation_type: str
    confidence: str  # "HIGH" | "MEDIUM" | "LOW"
    evidence: str


def infer_relationships(scene: LocalScene) -> List[Relationship]:
    relationships: List[Relationship] = []
    target = scene.target
    context = scene.context
    all_shapes = scene.shapes  # target + context - relationships often involve the target itself

    relationships.extend(_infer_separates_and_anchored_to(target, context))
    relationships.extend(_infer_highlights(all_shapes))
    relationships.extend(_infer_points_to(all_shapes))
    relationships.extend(_infer_aligned_with(target, context))
    relationships.extend(_infer_belongs_to(all_shapes))
    relationships.extend(_derive_depends_on(relationships))
    # `moves-with` / group-based inference: deferred, see PEI-S1-05 in
    # this module's docstring - not implemented in this slice.
    return relationships


def _horizontally_overlaps(a: SceneShape, b: SceneShape) -> bool:
    return a.geometry.horizontal_overlap(b.geometry)


def _is_divider(shape: SceneShape) -> bool:
    """A plain horizontal/vertical separator line, structurally
    distinct from a pointer/callout connector - its meaning is fully
    captured by `separates`/`anchored-to`/`depends-on`, so it is
    deliberately excluded from `points-to`/`belongs-to` inference to
    avoid a redundant or category-confused claim (a divider does not
    "belong to" one side over the other, and does not "point at"
    anything)."""
    return shape.is_line_shape and shape.geometry.height <= _ADJACENCY_GAP_EMU and shape.geometry.width > 0


def _infer_separates_and_anchored_to(target: SceneShape, context: List[SceneShape]) -> List[Relationship]:
    """A divider (`is_line_shape`, zero/near-zero height, horizontal)
    sitting in the small gap immediately below one text-bearing shape and
    immediately above another is evidenced as `separates` for both, and
    `anchored-to` the shape immediately above it (the one whose bottom
    edge it tracks) - this is what makes it move correctly if that shape
    grows."""
    out: List[Relationship] = []
    all_shapes = [target] + context
    dividers = [s for s in context if s.is_line_shape and s.geometry.height <= _ADJACENCY_GAP_EMU]

    for divider in dividers:
        above = None
        below = None
        for s in all_shapes:
            if s.shape_id == divider.shape_id:
                continue
            if not _horizontally_overlaps(divider, s):
                continue
            gap_below_s = divider.geometry.top - s.geometry.bottom
            gap_above_s = s.geometry.top - divider.geometry.bottom
            if 0 <= gap_below_s <= _ADJACENCY_GAP_EMU:
                if above is None or s.geometry.bottom > above.geometry.bottom:
                    above = s
            if 0 <= gap_above_s <= _ADJACENCY_GAP_EMU:
                if below is None or s.geometry.top < below.geometry.top:
                    below = s

        # Codex PEI-S1-04: geometry-only adjacency, however tight the gap,
        # is never HIGH - HIGH is reserved for an explicit OOXML
        # structural binding, which a plain divider line does not have.
        if above is not None:
            out.append(Relationship(
                source_shape_id=divider.shape_id, target_shape_id=above.shape_id,
                relation_type="separates", confidence="MEDIUM",
                evidence="divider sits %d EMU below shape's bottom edge, horizontally overlapping "
                          "(geometry-only adjacency, no explicit structural binding)"
                          % (divider.geometry.top - above.geometry.bottom),
            ))
            out.append(Relationship(
                source_shape_id=divider.shape_id, target_shape_id=above.shape_id,
                relation_type="anchored-to", confidence="MEDIUM",
                evidence="divider's position tracks this shape's bottom edge (%d EMU gap; "
                          "geometry-only adjacency, no explicit structural binding)"
                          % (divider.geometry.top - above.geometry.bottom),
            ))
        if below is not None:
            out.append(Relationship(
                source_shape_id=divider.shape_id, target_shape_id=below.shape_id,
                relation_type="separates", confidence="MEDIUM",
                evidence="divider sits %d EMU above shape's top edge, horizontally overlapping "
                          "(geometry-only adjacency, no explicit structural binding)"
                          % (below.geometry.top - divider.geometry.bottom),
            ))
    return out


def _infer_highlights(context: List[SceneShape]) -> List[Relationship]:
    """A small, unfilled, saturated-color (red, by founder-approved
    convention) auto-shape overlapping a picture is evidenced as
    `highlights` that picture - the founder-approved "red rectangle
    outline on the exact actionable UI target" grammar element."""
    out: List[Relationship] = []
    pictures = [s for s in context if s.shape_type.startswith("PICTURE")]
    candidates = [
        s for s in context
        if not s.is_line_shape
        and s.line_color_rgb in _SATURATED_COLORS
        and not s.text
    ]
    for cand in candidates:
        for pic in pictures:
            if cand.geometry.intersects(pic.geometry, margin=0):
                # PEI-S1-04: color is never semantic authority on its own -
                # this is color + geometry inference, not a structural
                # binding, so it is capped at MEDIUM like every other
                # inferred (non-structurally-bound) relationship.
                out.append(Relationship(
                    source_shape_id=cand.shape_id, target_shape_id=pic.shape_id,
                    relation_type="highlights", confidence="MEDIUM",
                    evidence="unfilled red-outlined shape overlaps this picture's bounding box "
                              "(color + geometry inference, not a structural binding)",
                ))
    return out


def _endpoint_positions(shape: SceneShape):
    """The two extreme points of a line/freeform/connector shape's own
    bounding box - a deterministic proxy for "where it starts and ends"
    when no explicit `<a:stCxn>`/`<a:endCxn>` binding exists. Not a claim
    about the actual drawn path, only its bounding extremes."""
    g = shape.geometry
    return (g.left, g.top), (g.right, g.bottom)


def _point_near_shape(point, shape: SceneShape, margin: int) -> bool:
    x, y = point
    g = shape.geometry
    return (g.left - margin) <= x <= (g.right + margin) and (g.top - margin) <= y <= (g.bottom + margin)


def _infer_points_to(context: List[SceneShape]) -> List[Relationship]:
    """A connector/freeform/line whose two ends each lie near a distinct
    other shape is evidenced as `points-to` from the shape at its start
    end toward the shape at its end end. Explicit `<a:stCxn>`/`<a:endCxn>`
    bindings (when present) are `HIGH` confidence; a bounding-box-extreme
    proxy match is `MEDIUM`."""
    out: List[Relationship] = []
    # An explicit stCxn/endCxn binding is definitive structural evidence
    # regardless of the shape's own visual look, so it is never excluded
    # by the divider heuristic - only the geometry-proxy fallback path
    # (below) treats a plain divider as ineligible.
    pointerlike = [
        s for s in context
        if (s.is_line_shape or s.is_freeform) and (s.connector_endpoints is not None or not _is_divider(s))
    ]
    id_to_shape = {s.shape_id: s for s in context}

    for pointer in pointerlike:
        if pointer.connector_endpoints is not None:
            ep = pointer.connector_endpoints
            if ep.start_shape_id is not None and ep.end_shape_id is not None:
                if ep.start_shape_id in id_to_shape and ep.end_shape_id in id_to_shape:
                    out.append(Relationship(
                        source_shape_id=ep.start_shape_id, target_shape_id=ep.end_shape_id,
                        relation_type="points-to", confidence="HIGH",
                        evidence="explicit OOXML stCxn/endCxn connector binding",
                    ))
                    continue

        start, end = _endpoint_positions(pointer)
        start_owner = None
        end_owner = None
        for s in context:
            if s.shape_id == pointer.shape_id:
                continue
            if _point_near_shape(start, s, _ENDPOINT_PROXIMITY_EMU) and start_owner is None:
                start_owner = s
            if _point_near_shape(end, s, _ENDPOINT_PROXIMITY_EMU) and end_owner is None:
                end_owner = s
        if start_owner is not None and end_owner is not None and start_owner.shape_id != end_owner.shape_id:
            out.append(Relationship(
                source_shape_id=start_owner.shape_id, target_shape_id=end_owner.shape_id,
                relation_type="points-to", confidence="MEDIUM",
                evidence="connector/freeform bounding-box endpoints each lie within %d EMU of "
                          "a distinct shape (no explicit connector binding present)" % _ENDPOINT_PROXIMITY_EMU,
            ))
    return out


def _infer_aligned_with(target: SceneShape, context: List[SceneShape]) -> List[Relationship]:
    out: List[Relationship] = []
    for s in context:
        if s.shape_id == target.shape_id or s.text is None:
            continue
        if abs(s.geometry.left - target.geometry.left) <= _ALIGNMENT_TOLERANCE_EMU:
            out.append(Relationship(
                source_shape_id=target.shape_id, target_shape_id=s.shape_id,
                relation_type="aligned-with", confidence="MEDIUM",
                evidence="left edges match within %d EMU" % _ALIGNMENT_TOLERANCE_EMU,
            ))
    return out


def _infer_belongs_to(context: List[SceneShape]) -> List[Relationship]:
    """A `points-to` source that is itself a pointer/highlight (not a
    text block) is evidenced as `belongs-to` the nearest text block whose
    bounding box it starts adjacent to - captures "this pointer belongs
    to that note" separately from what it points at."""
    out: List[Relationship] = []
    text_shapes = [s for s in context if s.text]
    pointerlike = [s for s in context if (s.is_line_shape or s.is_freeform) and not _is_divider(s)]
    for pointer in pointerlike:
        start, _ = _endpoint_positions(pointer)
        nearest = None
        nearest_dist = None
        for t in text_shapes:
            if _point_near_shape(start, t, _ENDPOINT_PROXIMITY_EMU):
                cx = (t.geometry.left + t.geometry.right) / 2
                cy = (t.geometry.top + t.geometry.bottom) / 2
                dist = (cx - start[0]) ** 2 + (cy - start[1]) ** 2
                if nearest_dist is None or dist < nearest_dist:
                    nearest, nearest_dist = t, dist
        if nearest is not None:
            out.append(Relationship(
                source_shape_id=pointer.shape_id, target_shape_id=nearest.shape_id,
                relation_type="belongs-to", confidence="MEDIUM",
                evidence="pointer's start point lies within %d EMU of this text block's bounding box"
                          % _ENDPOINT_PROXIMITY_EMU,
            ))
    return out


def _derive_depends_on(existing: List[Relationship]) -> List[Relationship]:
    """`depends-on` is the reflow-facing restatement of `anchored-to`:
    the anchored shape depends on the shape it is anchored to, since that
    shape's geometry change is what must propagate. Derived, not
    independently evidenced - carries the same evidence as its source
    `anchored-to` fact."""
    out: List[Relationship] = []
    for rel in existing:
        if rel.relation_type == "anchored-to":
            out.append(Relationship(
                source_shape_id=rel.source_shape_id, target_shape_id=rel.target_shape_id,
                relation_type="depends-on", confidence=rel.confidence,
                evidence="derived from anchored-to: " + rel.evidence,
            ))
    return out


