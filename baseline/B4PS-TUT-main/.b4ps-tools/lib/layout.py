"""Overlap and bounds checking - "respect alignment, don't overlap UI/images".

Used by both new capabilities (new-slide creation, instruction text edits):
neither is safe to auto-apply just because the *individual* placement or
wording looks right - the result also has to not collide with anything else
already on the slide. This is new *rules*, reusing the EMU/pixel math already
proven in geometry.py.

All checks work in EMU (native slide units) so they apply uniformly to boxes,
pictures, and text shapes without a pixel conversion step.
"""

TOLERANCE_EMU = 12700 * 2   # ~2pt - shared borders/anti-aliasing noise, not a real overlap


def to_ltrb(frame):
    return (frame["x"], frame["y"], frame["x"] + frame["cx"], frame["y"] + frame["cy"])


def _intersection(a_frame, b_frame):
    a, b = to_ltrb(a_frame), to_ltrb(b_frame)
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    if right <= left or bottom <= top:
        return 0, (left, top, right, bottom)
    return (right - left) * (bottom - top), (left, top, right, bottom)


def overlap_fraction(a_frame, b_frame):
    """Intersection area as a fraction of the *smaller* shape's area.

    Fraction, not raw area, so a large screenshot and a small marking box are
    judged on the same scale: a box 20% swallowed by something is a problem
    regardless of how big the other shape is.
    """
    area, _ = _intersection(a_frame, b_frame)
    if area <= 0:
        return 0.0
    a_area = a_frame["cx"] * a_frame["cy"]
    b_area = b_frame["cx"] * b_frame["cy"]
    smaller = min(a_area, b_area)
    return area / float(smaller) if smaller else 0.0


def is_within(inner_frame, outer_frame, tolerance=TOLERANCE_EMU):
    """True if `inner` lies inside `outer`, allowing a small tolerance."""
    i, o = to_ltrb(inner_frame), to_ltrb(outer_frame)
    return (i[0] >= o[0] - tolerance and i[1] >= o[1] - tolerance
           and i[2] <= o[2] + tolerance and i[3] <= o[3] + tolerance)


def check_slide(pictures, boxes, text_shapes, box_picture, overlap_limit=0.15):
    """Run every layout rule against one slide's shapes.

    `box_picture`: box_id -> picture dict it has been assigned to (from
    geometry.assign_boxes, resolved to the actual picture object).

    Returns a list of violation dicts: {"rule", "shapes", "detail"}. An empty
    list means the slide is clean; this does not decide auto-apply on its own,
    callers fold it into their own confidence/verdict.
    """
    violations = []

    # 1. every marking box must lie inside the picture it marks
    for box in boxes:
        picture = box_picture.get(box["id"])
        if picture is None:
            continue     # not on any picture - a step-number circle, not our concern
        if not is_within(box["frame"], picture["frame"]):
            violations.append({
                "rule": "out_of_bounds",
                "shapes": [box["name"]],
                "detail": "box extends outside the picture it is meant to mark",
            })

    # 2. no two marking boxes may substantially overlap each other
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            frac = overlap_fraction(a["frame"], b["frame"])
            if frac > overlap_limit:
                violations.append({
                    "rule": "box_overlap",
                    "shapes": [a["name"], b["name"]],
                    "detail": "%.0f%% overlap between two marking boxes" % (frac * 100),
                })

    # 3. a marking box must not sit on top of instruction/title text
    for box in boxes:
        for text in text_shapes:
            frac = overlap_fraction(box["frame"], text["frame"])
            if frac > overlap_limit:
                violations.append({
                    "rule": "box_over_text",
                    "shapes": [box["name"], text.get("name") or "text"],
                    "detail": "%.0f%% overlap between a marking box and text (\"%s\")"
                              % (frac * 100, (text.get("text") or "")[:40]),
                })

    # 4. two pictures on the same slide should not overlap (rare, usually a
    #    real defect for the side-by-side Chrome/Edge-style slides)
    for i, a in enumerate(pictures):
        for b in pictures[i + 1:]:
            frac = overlap_fraction(a["frame"], b["frame"])
            if frac > overlap_limit:
                violations.append({
                    "rule": "picture_overlap",
                    "shapes": [a["name"], b["name"]],
                    "detail": "%.0f%% overlap between two pictures" % (frac * 100),
                })

    return violations
