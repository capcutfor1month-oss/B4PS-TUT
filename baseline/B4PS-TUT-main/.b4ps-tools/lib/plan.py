"""Build the change plan for a slide, render previews, learn from corrections."""

import json
import os
import re
import time
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw

from . import anchors, config, deck as deck_io, geometry, layout, match

AUTO = "AUTO"
REVIEW = "NEEDS_REVIEW"
BLOCKED = "BLOCKED"

# Marking-box moves are measurable, so they may auto-apply. Anything about
# meaning - wording, a control that no longer exists - always comes back to the
# user regardless of how confident the matcher is.
COLOURS = {AUTO: (0, 200, 0), REVIEW: (255, 165, 0), BLOCKED: (255, 0, 0)}


def _jsonable(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def analyse_slide(deck_name, slide_no, new_image, index, reader, thresholds):
    """Compare a new screenshot against a slide and propose concrete changes.

    `reader` is a deck.DeckReader - every part is pulled from the deck's zip on
    demand, nothing is unpacked to disk.
    """
    info = index["slides"].get(str(slide_no))
    if info is None:
        return {"deck": deck_name, "slide": slide_no, "verdict": BLOCKED,
                "problems": ["slide %s not present in deck" % slide_no]}

    plan = {
        "deck": deck_name, "slide": int(slide_no), "xml": info["path"],
        "new_image": new_image, "problems": [], "boxes": [], "untouched_boxes": [],
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    lo, hi = config.DECKS[deck_name]["toc_range"]
    if not (lo <= int(slide_no) <= hi):
        plan["problems"].append(
            "slide %s is outside the deck's Table of Contents range (%d-%d) - "
            "out of scope unless explicitly requested" % (slide_no, lo, hi))

    # ---- which picture is being replaced -------------------------------
    opened = {}   # media name -> PIL Image, kept open only for this analysis
    for pic in info["pictures"]:
        img = reader.open_image(pic["media"])
        if img is not None:
            opened[pic["media"]] = img

    candidates = [{"media": pic["media"], "picture_id": pic["id"],
                  "image": opened.get(pic["media"])}
                 for pic in info["pictures"] if pic["media"] in opened]
    if not candidates:
        plan["verdict"] = BLOCKED
        plan["problems"].append("slide has no replaceable (readable) pictures")
        return plan

    ranked = match.identify_target(new_image, candidates)
    if not ranked:
        plan["verdict"] = BLOCKED
        plan["problems"].append("none of the slide's images could be read")
        return plan

    target = ranked[0]
    runner_up = ranked[1]["score"] if len(ranked) > 1 else -9.0
    picture = next(p for p in info["pictures"] if p["id"] == target["picture_id"])
    old_image = opened[picture["media"]]
    old_size = old_image.size

    with Image.open(new_image) as img:
        new_size = img.size

    frame_ar = picture["frame"]["cx"] / float(picture["frame"]["cy"])
    new_ar = new_size[0] / float(new_size[1])
    drift = abs(new_ar - frame_ar) / frame_ar

    plan["image_swap"] = _jsonable({
        "target_media": picture["media"], "picture_id": picture["id"],
        "similarity": target["similarity"], "margin_over_runner_up": round(target["score"] - runner_up, 4),
        "old_size": list(old_size), "new_size": list(new_size),
        "frame_aspect": round(frame_ar, 4), "new_aspect": round(new_ar, 4),
        "aspect_drift": round(drift, 4),
        "cropped_picture": picture["cropped"],
    })
    if drift > thresholds["max_aspect_drift"]:
        plan["problems"].append(
            "new screenshot's shape differs from the picture frame by %.1f%% - it "
            "would be stretched" % (drift * 100))
    if picture["cropped"]:
        plan["problems"].append(
            "this picture is cropped in the slide; a straight file swap will not "
            "line up")
    if target["score"] - runner_up < 0.05:
        plan["problems"].append(
            "could not confidently tell which of the slide's images to replace")

    # ---- boxes ---------------------------------------------------------
    # Work out which boxes actually sit on the picture being replaced *before*
    # doing any image analysis - most slides in this deck have zero marking
    # boxes at all, and the per-box matching (grayscale conversion, global
    # landmark search) is entirely wasted work when there is nothing to move.
    assignments = geometry.assign_boxes(info["boxes"], info["pictures"])
    on_target = [b for b in info["boxes"]
                 if assignments[b["id"]]["picture_id"] == picture["id"]]
    for box in info["boxes"]:
        if box not in on_target:
            other = assignments[box["id"]]["media"]
            plan["untouched_boxes"].append({
                "box_id": box["id"], "name": box["name"],
                "reason": ("sits on %s, not the picture being replaced" % other
                           if other else "not over any picture (step marker)")})

    if on_target:
        old_gray = match.gray_of(old_image)
        new_gray = match.load_gray(new_image)
        new_rgb = match.load_rgb(new_image)
        exclude = [tuple(int(v) for v in geometry.box_to_pixels(b["frame"], picture["frame"], old_size))
                  for b in on_target]
        shift = match.global_shift(old_gray, new_gray, exclude=exclude)
        for box in on_target:
            plan["boxes"].append(_analyse_box(
                deck_name, slide_no, box, picture, old_size,
                new_image, new_size, old_gray, new_gray, new_rgb, shift, thresholds))

    for img in opened.values():
        img.close()

    # ---- layout: would this leave anything overlapping? ------------------
    # Re-checked here even though the individual box matches already looked
    # right in isolation - "respect alignment, don't overlap UI/images" is a
    # property of the *whole slide*, not any one box on its own.
    hypothetical = [{"id": b["box_id"], "name": b["name"],
                     "frame": b["proposed_emu"]} for b in plan["boxes"]]
    box_picture = {b["box_id"]: picture for b in plan["boxes"]}
    plan["layout_violations"] = layout.check_slide(
        info["pictures"], hypothetical, info.get("text_shapes", []), box_picture)
    if plan["layout_violations"]:
        plan["problems"].append(
            "%d layout issue(s) found - see layout_violations" % len(plan["layout_violations"]))

    verdicts = [b["verdict"] for b in plan["boxes"]]
    if plan["problems"] or BLOCKED in verdicts:
        plan["verdict"] = BLOCKED if BLOCKED in verdicts else REVIEW
    elif REVIEW in verdicts:
        plan["verdict"] = REVIEW
    else:
        plan["verdict"] = AUTO
    return _jsonable(plan)


def suggest_templates(deck_name, index, step_count, limit=5):
    """Rank in-scope slides by how close their marking-box count is to
    `step_count` - a cheap proxy for "how many steps does this slide teach",
    used to pick a duplication template for a new tutorial slide.

    Deliberately a ranked *suggestion*, not an automatic pick - which template
    fits best is a judgment call the user can override.
    """
    lo, hi = config.DECKS[deck_name]["toc_range"]
    candidates = []
    for num_str, info in index["slides"].items():
        num = int(num_str)
        if not (lo <= num <= hi) or not info["pictures"]:
            continue
        assignments = geometry.assign_boxes(info["boxes"], info["pictures"])
        on_picture = sum(1 for a in assignments.values() if a["picture_id"])
        candidates.append((abs(on_picture - step_count), num, on_picture, len(info["pictures"])))
    candidates.sort()
    return [{"slide": num, "boxes_on_picture": on_pic, "picture_count": pics}
           for _, num, on_pic, pics in candidates[:limit]]


def plan_new_slide(deck_name, template_slide_no, feature_title, screenshot_path,
                   index, thresholds, toc=None):
    """Duplicate `template_slide_no` (appended at the end - see
    PPT-UPDATE-WORKFLOW.md on why appending beats inserting mid-deck) and
    realign its marking boxes against `screenshot_path`.

    Immediately after duplication the new slide's content is byte-identical to
    the template's, which means the box-realignment problem is *exactly* the
    routine screenshot-swap problem this tool already solves - so this reuses
    analyse_slide rather than a parallel implementation.

    `toc`: optional {"slide", "shape_id", "after_para_index", "segments"} -
    where to insert the new ToC line. Placement is a content decision, so
    nothing is inferred here; pass None to skip the ToC entry.

    Does not touch the live deck - duplicate_slide writes a separate staged
    file; this only reads it.
    """
    template_info = index["slides"][str(template_slide_no)]
    staged, new_part = deck_io.duplicate_slide(deck_name, template_info["path"])

    with deck_io.DeckReader(deck_name, path=staged) as reader:
        new_info = reader.parse_slide(new_part)
        new_number = len(reader.slide_order())
        ad_hoc_index = {"slides": {str(new_number): new_info}}
        result = analyse_slide(deck_name, new_number, screenshot_path,
                               ad_hoc_index, reader, thresholds)

        if "image_swap" in result:
            target_media = result["image_swap"]["target_media"]
            ext = os.path.splitext(target_media)[1].lstrip(".") or "png"
            result["image_swap"]["new_media_name"] = deck_io.next_media_names(reader, 1, ext)[0]
            target_pic = next(p for p in new_info["pictures"] if p["media"] == target_media)
            result["image_swap"]["target_rid"] = target_pic["rid"]
            result["image_swap"]["rels_part"] = ("%s/_rels/%s.rels"
                % (os.path.dirname(new_part), os.path.basename(new_part)))

        if toc:
            # `staged` is the full deck plus the one new slide, so every
            # pre-existing part (including the ToC slide) is still readable
            # through this same reader.
            toc_info = index["slides"][str(toc["slide"])]
            toc_xml = reader.read_text(toc_info["path"])
            result["toc_plan"] = _plan_toc_insert(
                deck_name, toc["slide"], toc_info["path"], toc["shape_id"],
                toc["after_para_index"], toc["segments"], toc_xml)

    # analyse_slide flags any slide outside the deck's current ToC range as
    # out-of-scope - correct for an *existing* slide, but every brand-new
    # slide starts there by construction (that's what the ToC step above is
    # for), so this one specific, expected message is not a real problem here.
    EXPECTED = "outside the deck's Table of Contents range"
    result["problems"] = [p for p in result["problems"] if EXPECTED not in p]
    if not toc:
        result["problems"].append(
            "no ToC entry planned yet - this slide will stay unreferenced "
            "until one is added")
    box_verdicts = [b["verdict"] for b in result["boxes"]]
    if result["problems"] or BLOCKED in box_verdicts:
        result["verdict"] = BLOCKED if BLOCKED in box_verdicts else REVIEW
    elif result.get("toc_plan") and not result["toc_plan"]["valid"]:
        result["verdict"] = BLOCKED
    elif REVIEW in box_verdicts:
        result["verdict"] = REVIEW
    else:
        result["verdict"] = AUTO

    result["kind"] = "new_slide"
    result["staged_source"] = staged
    result["template_slide"] = template_slide_no
    result["new_slide_number"] = new_number
    result["feature_title"] = feature_title
    return _jsonable(result)


def _plan_toc_insert(deck_name, toc_slide_no, xml_part, shape_id, after_para_index, segments, xml):
    try:
        new_xml = deck_io.insert_paragraph_after(xml, shape_id, after_para_index, segments)
        ET.fromstring(new_xml)
        problem = None
    except Exception as e:
        problem = str(e)
    return {"deck": deck_name, "slide": toc_slide_no, "xml": xml_part,
           "shape_id": shape_id, "after_para_index": after_para_index,
           "segments": segments, "valid": problem is None, "problem": problem}


def _font_size_pt(paragraph, default=12.0):
    for run in paragraph["runs"]:
        m = re.search(r'sz="(\d+)"', run["rpr"])
        if m:
            return int(m.group(1)) / 100.0
    return default


def plan_text_edit(deck_name, slide_no, shape_id, para_index, new_segments, index, reader):
    """Propose a wording change to one paragraph. Never auto-applies - text
    meaning is a human judgment call, the same principle as an unrecognizable
    marking-box target: measurable things (does it fit, is the XML valid) are
    checked here; whether the *wording* is right is always yours to confirm.
    """
    info = index["slides"][str(slide_no)]
    xml = reader.read_text(info["path"])
    old_paragraphs = deck_io.read_paragraphs(xml, shape_id)

    plan = {"kind": "text_edit", "deck": deck_name, "slide": int(slide_no),
           "xml": info["path"], "shape_id": shape_id, "para_index": para_index,
           "problems": [], "verdict": REVIEW}

    if para_index >= len(old_paragraphs):
        plan["problems"].append("shape %s has %d paragraph(s), asked for index %d"
                                % (shape_id, len(old_paragraphs), para_index))
        plan["verdict"] = BLOCKED
        return plan

    old_segments = [(r["text"], r["bold"]) for r in old_paragraphs[para_index]["runs"]]
    plan["old_text"] = "".join(t for t, _ in old_segments)
    plan["new_text"] = "".join(t for t, _ in new_segments)
    plan["old_segments"] = old_segments
    plan["new_segments"] = new_segments

    try:
        new_xml = deck_io.rewrite_paragraph(xml, shape_id, para_index, new_segments)
        ET.fromstring(new_xml)
    except Exception as e:
        plan["problems"].append("xml error: %s" % e)
        plan["verdict"] = BLOCKED
        return plan

    shape_frame = next((t["frame"] for t in info.get("text_shapes", []) if t["id"] == shape_id), None)
    font_pt = _font_size_pt(old_paragraphs[para_index])
    est_width = deck_io.estimate_text_width_emu(plan["new_text"], font_pt)
    plan["estimated_width_in"] = round(est_width / 914400.0, 2)
    if shape_frame:
        plan["box_width_in"] = round(shape_frame["cx"] / 914400.0, 2)
        if est_width > shape_frame["cx"] * 1.05:
            plan["problems"].append(
                "estimated text width (~%.2fin) may exceed the text box (~%.2fin) - "
                "no renderer available on this machine, confirm visually before applying"
                % (plan["estimated_width_in"], plan["box_width_in"]))

    return plan


def _analyse_box(deck_name, slide_no, box, picture, old_size,
                 new_image, new_size, old_gray, new_gray, new_rgb, shift, thresholds):
    old_rect = geometry.box_to_pixels(box["frame"], picture["frame"], old_size)
    entry = {"box_id": box["id"], "name": box["name"],
             "old_rect_px": [round(v, 1) for v in old_rect],
             "current_emu": box["frame"], "evidence": [], "notes": []}

    if box["frame"].get("rot") or box["frame"].get("flip"):
        entry["verdict"] = REVIEW
        entry["confidence"] = 0.0
        entry["notes"].append("box is rotated or flipped - not handled automatically")
        return entry

    # anchor: reuse the remembered element if we have one, else snip it now
    stored = anchors.load(deck_name, slide_no, box["id"])
    if stored is not None:
        patch = stored["patch"]
        inset = stored["inset"]
        entry["evidence"].append("used remembered anchor from %s" % stored["saved"])
        if stored.get("label"):
            entry["was_pointing_at"] = stored["label"]
    else:
        padded = anchors.padded_rect(old_rect, old_size)
        left, top, right, bottom = [int(round(v)) for v in padded]
        patch = old_gray[top:bottom, left:right]
        inset = [old_rect[0] - padded[0], old_rect[1] - padded[1]]
        entry["evidence"].append("anchor snipped from the current screenshot")

    if patch.size == 0 or min(patch.shape) < 8:
        entry["verdict"] = REVIEW
        entry["confidence"] = 0.0
        entry["notes"].append("box is too small to match reliably")
        return entry

    # --- method A: find that element in the new screenshot
    found = match.match_anchor(patch, new_gray)
    if not found:
        entry["verdict"] = REVIEW
        entry["confidence"] = 0.0
        entry["notes"].append("no match found for this element")
        return entry

    scale = found["scale"]
    a_left = found["x"] + inset[0] * scale
    a_top = found["y"] + inset[1] * scale
    a_rect = (a_left, a_top,
              a_left + (old_rect[2] - old_rect[0]) * scale,
              a_top + (old_rect[3] - old_rect[1]) * scale)
    entry["evidence"].append("element match %.3f (scale %.2f)" % (found["score"], scale))

    # --- method B: where the page as a whole moved
    if shift:
        b_rect = (old_rect[0] + shift["dx"], old_rect[1] + shift["dy"],
                  old_rect[2] + shift["dx"], old_rect[3] + shift["dy"])
        disagree = float(np.hypot((a_rect[0] + a_rect[2]) / 2 - (b_rect[0] + b_rect[2]) / 2,
                                  (a_rect[1] + a_rect[3]) / 2 - (b_rect[1] + b_rect[3]) / 2))
        entry["evidence"].append(
            "page shift (%+.0f,%+.0f) from %d landmarks; methods differ by %.0fpx"
            % (shift["dx"], shift["dy"], shift["landmarks"], disagree))
    else:
        disagree = None
        entry["notes"].append("not enough landmarks for an independent cross-check")

    # --- method C: do the edges land on real colour boundaries
    support = match.edge_support(new_rgb, a_rect)
    entry["evidence"].append("edge support %.2f %s" % (support["score"], support["edges"]))

    # --- combine
    confidence = found["score"]
    if found.get("ratio", 0) > 0.92:
        confidence *= 0.60
        entry["notes"].append(
            "several places in the new screenshot look equally like this element")
    if disagree is None:
        confidence *= 0.70
    elif disagree > thresholds["max_method_disagree_px"]:
        confidence *= max(0.30, thresholds["max_method_disagree_px"] / max(disagree, 1e-6))
        entry["notes"].append(
            "the two methods disagree by %.0fpx - the element may have moved "
            "relative to the page, or this may be a different element" % disagree)
    # The edge check exists to catch a *move* that lands on the wrong size - the
    # slide 10 defect. If the element matched near-perfectly and did not move,
    # there is no new geometry to second-guess, so the check is not applied.
    moved = float(np.hypot(a_rect[0] - old_rect[0], a_rect[1] - old_rect[1]))
    if moved < 2.0 and found["score"] >= 0.95:
        entry["evidence"].append("element unchanged and in the same place")
    else:
        confidence *= (0.85 + 0.15 * support["score"])
        if support["score"] < 0.25:
            entry["notes"].append(
                "proposed edges do not sit on a clear boundary - the size may be wrong")

    entry["proposed_rect_px"] = [round(v, 1) for v in a_rect]
    entry["moved_px"] = round(moved, 1)
    if moved < 1.0:
        # Template matches land on whole pixels, so re-deriving coordinates for a
        # box that has not moved would nudge it by a fraction of a pixel for no
        # reason. Leave the original values exactly as they are.
        entry["proposed_emu"] = dict(box["frame"])
        entry["changed"] = False
        entry["evidence"].append("already correctly placed - left untouched")
    else:
        entry["proposed_emu"] = geometry.pixels_to_box(a_rect, picture["frame"], new_size)
        entry["changed"] = True
    entry["match_score"] = round(found["score"], 4)
    entry["ambiguity"] = found.get("ratio")
    entry["method_disagreement_px"] = None if disagree is None else round(disagree, 1)
    entry["edge_support"] = support["score"]
    entry["confidence"] = round(float(confidence), 4)

    if found["score"] < 0.55:
        entry["verdict"] = BLOCKED
        entry["notes"].append(
            "the marked control cannot be found in the new screenshot - it may "
            "have been renamed or removed, which is a content change, not an "
            "alignment fix")
    elif (confidence >= thresholds["auto_apply_confidence"]
          and found["score"] >= thresholds["min_match_score"]
          and disagree is not None
          and disagree <= thresholds["max_method_disagree_px"]):
        entry["verdict"] = AUTO
    else:
        entry["verdict"] = REVIEW
    return entry


# --------------------------------------------------------------------------
# previews
# --------------------------------------------------------------------------

def render_preview(plan, out_dir):
    """Draw the proposed boxes on the new screenshot so they can be eyeballed."""
    os.makedirs(out_dir, exist_ok=True)
    with Image.open(plan["new_image"]) as img:
        canvas = img.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    for box in plan.get("boxes", []):
        rect = box.get("proposed_rect_px") or box.get("old_rect_px")
        if not rect:
            continue
        colour = COLOURS.get(box["verdict"], COLOURS[REVIEW])
        draw.rectangle([rect[0], rect[1], rect[2], rect[3]], outline=colour, width=3)
        draw.text((rect[0] + 4, max(0, rect[1] - 14)),
                  "%s %.2f" % (box["name"], box.get("confidence", 0)), fill=colour)
    path = os.path.join(out_dir, "slide%03d_proposed.png" % plan["slide"])
    canvas.save(path)
    plan["preview"] = path
    return path


# --------------------------------------------------------------------------
# corrections log + threshold tuning
# --------------------------------------------------------------------------

def log_correction(record):
    """Record what was proposed vs. what was right - the raw material for tuning."""
    os.makedirs(config.STATE_DIR, exist_ok=True)
    record = dict(record)
    record.setdefault("logged", time.strftime("%Y-%m-%d %H:%M:%S"))
    with open(config.CORRECTIONS_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(_jsonable(record)) + "\n")


def tune():
    """Raise the auto-apply bar if a confidence band has been wrong too often.

    Deliberately one-directional: the bar goes up on evidence of mistakes, never
    down. It also refuses to move until a band has enough samples, so a couple of
    early corrections cannot swing it.
    """
    thresholds = config.load_thresholds()
    if not os.path.exists(config.CORRECTIONS_LOG):
        return thresholds, "no corrections logged yet - nothing to learn from"

    # One outcome per applied box, latest record wins: `apply` records a hopeful
    # accepted=True, and a later `correct` for the same event supersedes it.
    outcomes = {}
    with open(config.CORRECTIONS_LOG, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("claimed_confidence") is None or "accepted" not in rec:
                continue
            key = (rec.get("deck"), rec.get("slide"), rec.get("box_id"),
                   rec.get("applied_at"))
            outcomes[key] = rec

    bands = {}
    for rec in outcomes.values():
        band = round(float(rec["claimed_confidence"]) * 20) / 20.0   # 0.05 buckets
        stats = bands.setdefault(band, {"n": 0, "wrong": 0})
        stats["n"] += 1
        if not rec["accepted"]:
            stats["wrong"] += 1

    need = thresholds["min_samples_to_tune"]
    limit = thresholds["tune_error_rate"]
    worst = None
    for band, stats in sorted(bands.items()):
        if stats["n"] < need:
            continue
        rate = stats["wrong"] / float(stats["n"])
        if rate > limit:
            worst = max(worst or 0.0, band)

    if worst is None:
        return thresholds, "no confidence band has enough evidence to justify a change"

    new_bar = min(0.99, round(worst + 0.05, 2))
    if new_bar <= thresholds["auto_apply_confidence"]:
        return thresholds, "current bar (%.2f) already covers the observed failures" % \
            thresholds["auto_apply_confidence"]

    old = thresholds["auto_apply_confidence"]
    thresholds["auto_apply_confidence"] = new_bar
    config.save_thresholds(thresholds)
    return thresholds, "raised auto-apply bar %.2f -> %.2f (band %.2f was wrong too often)" % \
        (old, new_bar, worst)
