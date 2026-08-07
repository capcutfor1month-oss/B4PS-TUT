"""Coordinate maths between slide EMU space and screenshot pixel space.

Marking boxes are positioned in absolute slide coordinates - they do not move or
scale with the picture underneath. The pictures in these decks use
<a:stretch><a:fillRect/> with no <a:srcRect> crop, so a point on the picture maps
linearly between its EMU frame and the image's pixel grid.
"""


def box_to_pixels(box_frame, pic_frame, img_size):
    """Slide-EMU rect -> pixel rect (left, top, right, bottom) on the image."""
    width, height = img_size
    sx = width / float(pic_frame["cx"])
    sy = height / float(pic_frame["cy"])
    left = (box_frame["x"] - pic_frame["x"]) * sx
    top = (box_frame["y"] - pic_frame["y"]) * sy
    return (left, top, left + box_frame["cx"] * sx, top + box_frame["cy"] * sy)


def pixels_to_box(px_rect, pic_frame, img_size):
    """Pixel rect -> slide-EMU frame dict, inverse of box_to_pixels."""
    width, height = img_size
    left, top, right, bottom = px_rect
    sx = pic_frame["cx"] / float(width)
    sy = pic_frame["cy"] / float(height)
    return {
        "x": int(round(pic_frame["x"] + left * sx)),
        "y": int(round(pic_frame["y"] + top * sy)),
        "cx": int(round((right - left) * sx)),
        "cy": int(round((bottom - top) * sy)),
    }


def _intersection_area(a, b):
    left = max(a["x"], b["x"])
    top = max(a["y"], b["y"])
    right = min(a["x"] + a["cx"], b["x"] + b["cx"])
    bottom = min(a["y"] + a["cy"], b["y"] + b["cy"])
    if right <= left or bottom <= top:
        return 0
    return (right - left) * (bottom - top)


def assign_boxes(boxes, pictures):
    """Map each marking box to the picture it overlays.

    A slide can carry several screenshots (e.g. Chrome and Edge panels on the
    same slide). Replacing one must leave the other's boxes untouched, so a box
    is only ever realigned against the picture it actually sits on.
    """
    assignments = {}
    for box in boxes:
        best, best_area = None, 0
        for pic in pictures:
            area = _intersection_area(box["frame"], pic["frame"])
            if area > best_area:
                best, best_area = pic, area
        box_area = box["frame"]["cx"] * box["frame"]["cy"]
        coverage = (best_area / float(box_area)) if box_area else 0.0
        assignments[box["id"]] = {
            "picture_id": best["id"] if best else None,
            "media": best["media"] if best else None,
            "coverage": round(coverage, 4),
        }
    return assignments
