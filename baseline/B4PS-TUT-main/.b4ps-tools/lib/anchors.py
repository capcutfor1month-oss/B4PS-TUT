"""The anchor library - what each marking box actually points at.

A box in the XML is only a rectangle; nothing records that it marks "the Members
button". Each time a slide is worked on, the patch of screenshot underneath every
box is saved here. On the next screenshot change that element can be found
directly instead of being rediscovered, so repeat updates get cheaper.

Anchors are refreshed from the new screenshot after a successful realignment, so
the library tracks the app as its UI drifts instead of going stale.
"""

import json
import os
import time

import numpy as np
from PIL import Image

from . import config

PAD_RATIO = 0.25       # context around the element, as a fraction of box size
PAD_MIN = 8            # ...but never less than this many pixels


def _dir(deck, slide_no):
    return os.path.join(config.ANCHOR_DIR, deck, "slide%03d" % int(slide_no))


def _stem(deck, slide_no, box_id):
    return os.path.join(_dir(deck, slide_no), "box%s" % box_id)


def padded_rect(rect, img_size):
    """Expand a box rect with context, clamped to the image."""
    left, top, right, bottom = rect
    pad_x = max(PAD_MIN, (right - left) * PAD_RATIO)
    pad_y = max(PAD_MIN, (bottom - top) * PAD_RATIO)
    width, height = img_size
    return (max(0.0, left - pad_x), max(0.0, top - pad_y),
            min(float(width), right + pad_x), min(float(height), bottom + pad_y))


def save(deck, slide_no, box_id, image_path, rect, extra=None):
    """Snip what the box sits on and remember it."""
    os.makedirs(_dir(deck, slide_no), exist_ok=True)
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        padded = padded_rect(rect, img.size)
        patch = img.crop(tuple(int(round(v)) for v in padded))
        stem = _stem(deck, slide_no, box_id)
        patch.save(stem + ".png")
        meta = {
            "deck": deck, "slide": int(slide_no), "box_id": str(box_id),
            "saved": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source_image": os.path.basename(image_path),
            "image_size": list(img.size),
            "box_rect": [round(v, 2) for v in rect],
            "patch_rect": [round(v, 2) for v in padded],
            # offset of the true box within the stored patch
            "inset": [round(rect[0] - padded[0], 2), round(rect[1] - padded[1], 2)],
        }
    if extra:
        meta.update(extra)
    with open(stem + ".json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    return meta


def load(deck, slide_no, box_id):
    stem = _stem(deck, slide_no, box_id)
    if not (os.path.exists(stem + ".png") and os.path.exists(stem + ".json")):
        return None
    with open(stem + ".json", encoding="utf-8") as fh:
        meta = json.load(fh)
    meta["patch"] = np.array(Image.open(stem + ".png").convert("L"))
    return meta


def label(deck, slide_no, box_id, text):
    """Attach a human/model description, e.g. 'members panel icon'."""
    stem = _stem(deck, slide_no, box_id)
    path = stem + ".json"
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        meta = json.load(fh)
    meta["label"] = text
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    return meta
