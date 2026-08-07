"""Image matching: identify the target picture, relocate boxes, verify results.

Everything here is deterministic computer vision - no model tokens. The model is
only consulted for the cases this module reports as uncertain.

A box move is only ever trusted when two independent methods agree:
  A) local anchor match - find the specific UI element the box was marking
  B) global transform  - where the page as a whole moved, from scattered landmarks
plus a content check (C) that the proposed edges land on real colour boundaries.
Method A alone is what produced the slide 10 width error; requiring agreement is
the guard against repeating it.
"""

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None
from PIL import Image

READABLE = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff")


def load_gray(path):
    img = Image.open(path).convert("L")
    return np.array(img)


def load_rgb(path):
    return np.array(Image.open(path).convert("RGB"))


def gray_of(img):
    """Same as load_gray, but from an already-open PIL Image (e.g. read
    straight out of the deck's zip - never touches disk)."""
    return np.array(img.convert("L"))


def rgb_of(img):
    return np.array(img.convert("RGB"))


def _norm(arr):
    arr = arr.astype(np.float32)
    return (arr - arr.mean()) / (arr.std() + 1e-6)


# --------------------------------------------------------------------------
# which picture does this screenshot replace?
# --------------------------------------------------------------------------

def identify_target(new_image_path, candidates):
    """Pick which of a slide's pictures the new screenshot is meant to replace.

    Slides here carry up to a dozen images (screenshots, logos, icons), so the
    largest is not reliably the right one. Compare downscaled content instead.

    `candidates` items need a "media" / "picture_id" plus either an "image"
    (already-open PIL Image, read straight from the deck's zip) or a "path".
    """
    with Image.open(new_image_path) as img:
        new_small = np.array(img.convert("L").resize((128, 72)))
        new_ar = img.size[0] / float(img.size[1])

    scored = []
    for cand in candidates:
        img = cand.get("image")
        opened_here = False
        if img is None:
            path = cand.get("path", "")
            if not path.lower().endswith(READABLE):
                continue
            try:
                img = Image.open(path)
                opened_here = True
            except Exception:
                continue
        try:
            old_small = np.array(img.convert("L").resize((128, 72)))
            old_ar = img.size[0] / float(img.size[1]) if img.size[1] else 0.0
        except Exception:
            continue
        finally:
            if opened_here:
                img.close()

        corr = float(np.mean(_norm(new_small) * _norm(old_small)))
        ar_pen = abs(new_ar - old_ar) / max(new_ar, old_ar) if old_ar else 1.0
        scored.append({
            "media": cand["media"], "picture_id": cand["picture_id"],
            "similarity": round(corr, 4), "aspect_drift": round(ar_pen, 4),
            "score": round(corr - 2.0 * ar_pen, 4),
        })
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


# --------------------------------------------------------------------------
# method A - local anchor match
# --------------------------------------------------------------------------

def match_anchor(patch, target_gray, scales=None):
    """Locate `patch` inside `target_gray`, searching a range of scales.

    Returns best position, score, and a ratio test against the runner-up. These
    UIs are highly repetitive (rows of near-identical list items), so a strong
    score alone is not enough - an ambiguous best/second-best gap means the match
    cannot be trusted.

    A coarse-to-fine (downsample-then-refine) version of this was tried for
    speed and reverted: it mismatched several boxes on slide 10 that this exact
    full-resolution search gets right (including the one that produced the
    original slide-10 width error, which this version correctly leaves alone).
    Getting this wrong is worse than being slow, so it stays simple.
    """
    if cv2 is None:
        raise RuntimeError("opencv is required (pip install opencv-python-headless)")
    scales = scales if scales is not None else np.arange(0.90, 1.101, 0.01)
    best = None
    for scale in scales:
        w = int(round(patch.shape[1] * scale))
        h = int(round(patch.shape[0] * scale))
        if w < 8 or h < 8 or w >= target_gray.shape[1] or h >= target_gray.shape[0]:
            continue
        interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
        resized = cv2.resize(patch, (w, h), interpolation=interp)
        result = cv2.matchTemplate(target_gray, resized, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(result)
        if best is None or score > best["score"]:
            second = _runner_up(result, loc, (w, h))
            best = {"score": float(score), "scale": float(scale),
                    "x": int(loc[0]), "y": int(loc[1]), "w": w, "h": h,
                    "second": float(second)}
    if best:
        best["ratio"] = round(best["second"] / best["score"], 4) if best["score"] > 0 else 1.0
    return best


def _runner_up(result, peak, size):
    """Best score outside a window around the peak - measures ambiguity."""
    masked = result.copy()
    x, y = peak
    w, h = size
    x0, y0 = max(0, x - w // 2), max(0, y - h // 2)
    masked[y0:y + h // 2, x0:x + w // 2] = -1.0
    return float(masked.max()) if masked.size else -1.0


# --------------------------------------------------------------------------
# method B - global transform from scattered landmarks
# --------------------------------------------------------------------------

def global_shift(old_gray, new_gray, exclude=None, samples=12, patch=96):
    """Median displacement of scattered landmark patches - how the page moved.

    Outliers (regions whose content genuinely changed) are rejected by taking the
    median, so this reflects layout movement rather than content edits.
    """
    height, width = old_gray.shape
    exclude = exclude or []
    rng = np.random.RandomState(7)
    shifts, scores = [], []
    tries = 0
    while len(shifts) < samples and tries < samples * 6:
        tries += 1
        px = int(rng.randint(0, max(1, width - patch)))
        py = int(rng.randint(0, max(1, height - patch)))
        if any(_overlaps((px, py, px + patch, py + patch), rect) for rect in exclude):
            continue
        tile = old_gray[py:py + patch, px:px + patch]
        if tile.std() < 12:          # featureless area - nothing to match on
            continue
        result = cv2.matchTemplate(new_gray, tile, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(result)
        if score < 0.75:
            continue
        shifts.append((loc[0] - px, loc[1] - py))
        scores.append(float(score))
    if len(shifts) < 3:
        return None
    arr = np.array(shifts, dtype=np.float32)
    return {
        "dx": float(np.median(arr[:, 0])),
        "dy": float(np.median(arr[:, 1])),
        "spread": float(np.median(np.abs(arr - np.median(arr, axis=0)))),
        "landmarks": len(shifts),
        "mean_score": round(float(np.mean(scores)), 4),
    }


def _overlaps(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


# --------------------------------------------------------------------------
# method C - do the proposed edges sit on real colour boundaries?
# --------------------------------------------------------------------------

def edge_support(rgb, rect, reach=4):
    """Score how strongly each edge of `rect` coincides with a colour change.

    A box edge floating in flat colour scores near zero - which is exactly the
    defect that made the first slide 10 fix too wide.
    """
    left, top, right, bottom = [int(round(v)) for v in rect]
    height, width = rgb.shape[:2]
    left, right = max(0, left), min(width - 1, right)
    top, bottom = max(0, top), min(height - 1, bottom)
    if right - left < 4 or bottom - top < 4:
        return {"score": 0.0, "edges": {}}

    def contrast(vals_a, vals_b):
        if vals_a.size == 0 or vals_b.size == 0:
            return 0.0
        diff = np.abs(vals_a.mean(axis=0).astype(float) - vals_b.mean(axis=0).astype(float))
        return float(np.mean(diff))

    edges = {
        "left": contrast(rgb[top:bottom, max(0, left - reach):left].reshape(-1, 3),
                         rgb[top:bottom, left:left + reach].reshape(-1, 3)),
        "right": contrast(rgb[top:bottom, max(0, right - reach):right].reshape(-1, 3),
                          rgb[top:bottom, right:right + reach].reshape(-1, 3)),
        "top": contrast(rgb[max(0, top - reach):top, left:right].reshape(-1, 3),
                        rgb[top:top + reach, left:right].reshape(-1, 3)),
        "bottom": contrast(rgb[max(0, bottom - reach):bottom, left:right].reshape(-1, 3),
                           rgb[bottom:bottom + reach, left:right].reshape(-1, 3)),
    }
    values = np.array(list(edges.values()), dtype=float)
    # normalise: ~25 levels of mean channel difference is a solid UI boundary
    score = float(np.clip(values.mean() / 25.0, 0.0, 1.0))
    return {"score": round(score, 4),
            "edges": {k: round(v, 2) for k, v in edges.items()}}
