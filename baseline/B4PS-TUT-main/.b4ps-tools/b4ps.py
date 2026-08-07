#!/usr/bin/env python
"""B4PS deck updater.

  python b4ps.py scan                      what screenshots are waiting
  python b4ps.py analyze [--all]           work out what needs changing (writes nothing)
  python b4ps.py apply   [--include 51]    apply confident changes (+ named boxes)
  python b4ps.py correct --slide 10 --box 51
  python b4ps.py tune                      re-derive the confidence bar from corrections
  python b4ps.py status

Analysis never writes to the deck. Application is a separate, deliberate step.
"""

import argparse
import glob
import json
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib import anchors, config, deck as deck_io, plan as planner, ppt_engine  # noqa: E402

NAME_RE = re.compile(r"^slide[_\-\s]*(\d+)(?:[_\-]([a-z0-9]+))?", re.I)


# --------------------------------------------------------------------------
# intake
# --------------------------------------------------------------------------

def parse_name(filename):
    """Slide_10.png / Slide_10_b.png / Slide_10_reference.png.png -> (10, slot)."""
    stem = os.path.basename(filename)
    while True:
        stem, ext = os.path.splitext(stem)
        if not ext:
            break
    m = NAME_RE.match(stem)
    if not m:
        return None
    slot = (m.group(2) or "").lower()
    return {"slide": int(m.group(1)), "slot": slot,
            "is_reference": slot in ("reference", "ref")}


def scan(only_new=True):
    queue, skipped = [], []
    for deck_name, spec in config.DECKS.items():
        folder = spec["screenshots"]
        if not os.path.isdir(folder):
            continue
        deck_mtime = os.path.getmtime(spec["pptx"]) if os.path.exists(spec["pptx"]) else 0
        for path in sorted(glob.glob(os.path.join(folder, "*"))):
            if not os.path.isfile(path):
                continue
            parsed = parse_name(path)
            if not parsed:
                skipped.append((path, "filename does not name a slide"))
                continue
            if parsed["is_reference"]:
                skipped.append((path, "alignment reference, not a replacement"))
                continue
            fresh = os.path.getmtime(path) > deck_mtime
            if only_new and not fresh:
                skipped.append((path, "older than the deck - already applied?"))
                continue
            queue.append({"deck": deck_name, "slide": parsed["slide"],
                          "slot": parsed["slot"], "image": path, "fresh": fresh})
    return queue, skipped


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_scan(args):
    queue, skipped = scan(only_new=not args.all)
    if not queue:
        print("Nothing waiting.")
    for item in queue:
        print("  %-8s slide %-4s %s" % (item["deck"], item["slide"],
                                        os.path.basename(item["image"])))
    for path, why in skipped:
        print("  skipped: %-40s (%s)" % (os.path.basename(path), why))
    return 0


def cmd_analyze(args):
    config.ensure_dirs()
    thresholds = config.load_thresholds()
    queue, _ = scan(only_new=not args.all)
    if args.slides:
        wanted = {int(s) for s in args.slides.split(",")}
        queue = [q for q in queue if q["slide"] in wanted]
    if not queue:
        print("Nothing to analyse.")
        return 0

    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(config.REPORT_DIR, stamp)
    os.makedirs(out_dir, exist_ok=True)

    by_deck = {}
    for item in queue:
        by_deck.setdefault(item["deck"], []).append(item)

    plans = []
    for deck_name, items in by_deck.items():
        index = deck_io.build_index(deck_name)     # slide XML + rels only, cached
        with deck_io.DeckReader(deck_name) as reader:   # nothing unpacked to disk
            for item in items:
                result = planner.analyse_slide(deck_name, item["slide"], item["image"],
                                               index, reader, thresholds)
                if result.get("boxes"):
                    planner.render_preview(result, out_dir)
                plans.append(result)

    with open(os.path.join(out_dir, "plans.json"), "w", encoding="utf-8") as fh:
        json.dump(plans, fh, indent=2)
    _print_summary(plans, out_dir)
    return 0


def _print_summary(plans, out_dir):
    print("\nreport: %s\n" % out_dir)
    for result in plans:
        print("%s slide %s  ->  %s" % (result["deck"], result["slide"], result["verdict"]))
        swap = result.get("image_swap")
        if swap:
            print("   replaces %s (match %.2f, shape drift %.2f%%)"
                  % (swap["target_media"], swap["similarity"], swap["aspect_drift"] * 100))
        for problem in result.get("problems", []):
            print("   ! %s" % problem)
        for box in result.get("boxes", []):
            print("   [%s] %s  conf %.2f  moves %.0fpx"
                  % (box["verdict"], box["name"], box.get("confidence", 0),
                     box.get("moved_px", 0)))
            for note in box.get("notes", []):
                print("        - %s" % note)
        for box in result.get("untouched_boxes", []):
            print("   [keep] %s (%s)" % (box["name"], box["reason"]))
        if result.get("preview"):
            print("   preview: %s" % result["preview"])
        print("")
    needs = [p for p in plans if p["verdict"] != planner.AUTO]
    if needs:
        print("%d slide(s) need your decision before they can be applied." % len(needs))
    print("Apply the confident ones with:  python b4ps.py apply")


def _same_bytes(media_bytes, new_image_path):
    """Byte-identical check, so an unchanged screenshot never triggers a write."""
    if media_bytes is None or not os.path.exists(new_image_path):
        return False
    with open(new_image_path, "rb") as fh:
        return fh.read() == media_bytes


def _latest_report():
    dirs = sorted(glob.glob(os.path.join(config.REPORT_DIR, "*")), reverse=True)
    return dirs[0] if dirs else None


def cmd_apply(args):
    report = args.report or _latest_report()
    if not report or not os.path.exists(os.path.join(report, "plans.json")):
        print("No analysis to apply - run analyze first.")
        return 1
    with open(os.path.join(report, "plans.json"), encoding="utf-8") as fh:
        plans = json.load(fh)

    include = {str(b) for b in (args.include or "").split(",") if b.strip()}
    applied_at = time.strftime("%Y-%m-%d %H:%M:%S")
    todo = []

    for result in plans:
        if result.get("problems") and not args.force:
            print("skip %s slide %s: %s" % (result["deck"], result["slide"],
                                            result["problems"][0]))
            continue
        boxes = result.get("boxes", [])
        chosen = [b for b in boxes
                  if b["verdict"] == planner.AUTO or str(b["box_id"]) in include or args.force]
        # Keep the deck self-consistent: never swap a screenshot while leaving
        # some of its own marking boxes pointing at the old layout.
        if len(chosen) != len(boxes):
            pending = [b["name"] for b in boxes if b not in chosen]
            print("defer %s slide %s: %s still unresolved"
                  % (result["deck"], result["slide"], ", ".join(pending)))
            continue
        todo.append((result, chosen))

    if not todo:
        print("Nothing ready to apply.")
        return 0

    # Work out what genuinely needs writing *before* taking any backup, so a run
    # where everything is already current does not burn a backup slot. Reading
    # is selective: only the slide XML and the one media part per slide.
    by_deck = {}
    for result, chosen in todo:
        by_deck.setdefault(result["deck"], []).append((result, chosen))

    work_items = []
    xml_cache = {}     # deck -> {part: current text, patched as boxes are folded in}
    for deck_name, entries in by_deck.items():
        xml_cache[deck_name] = {}
        with deck_io.DeckReader(deck_name) as reader:
            for result, chosen in entries:
                if not result.get("image_swap"):
                    reason = result["problems"][0] if result.get("problems") else "no image identified"
                    print("skip %s slide %s: %s" % (deck_name, result["slide"], reason))
                    continue
                media_bytes = reader.media_bytes(result["image_swap"]["target_media"])
                image_differs = not _same_bytes(media_bytes, result["new_image"])
                moving = [b for b in chosen if b.get("changed")]
                if not image_differs and not moving:
                    print("skip %s slide %s: screenshot and boxes are already current"
                          % (deck_name, result["slide"]))
                    continue
                if moving:
                    xml = xml_cache[deck_name].get(result["xml"]) or reader.read_text(result["xml"])
                    for box in moving:
                        emu = box["proposed_emu"]
                        xml = deck_io.patch_shape_xfrm(xml, box["box_id"],
                                                       emu["x"], emu["y"], emu["cx"], emu["cy"])
                    xml_cache[deck_name][result["xml"]] = xml
                work_items.append((result, chosen, moving, image_differs))

    if not work_items:
        print("\nNothing to write - the deck is already up to date.")
        return 0

    if deck_io.powerpoint_running():
        print("PowerPoint is open and holds the deck locked - close it and re-run.")
        return 1

    changed = {}
    for deck_name, entries in by_deck.items():
        my_items = [w for w in work_items if w[0]["deck"] == deck_name]
        if not my_items:
            continue

        spec = config.DECKS[deck_name]
        print("backup: %s" % deck_io.backup(deck_name))

        changes = {}
        for part, xml in xml_cache[deck_name].items():
            changes[part] = xml.encode("utf-8")
        for result, chosen, moving, image_differs in my_items:
            if image_differs:
                with open(result["new_image"], "rb") as fh:
                    changes["ppt/media/" + result["image_swap"]["target_media"]] = fh.read()
            changed.setdefault(deck_name, []).append((result, chosen))
            print("patched %s slide %s (%s%d box%s moved)"
                  % (deck_name, result["slide"],
                     "screenshot + " if image_differs else "", len(moving),
                     "" if len(moving) == 1 else "es"))

        os.makedirs(config.WORK_DIR, exist_ok=True)
        staged = os.path.join(config.WORK_DIR, "%s_staged.pptx" % deck_name)
        deck_io.write_with_changes(deck_name, staged, changes)
        backups = sorted(glob.glob(os.path.join(spec["backups"], "*.pptx")),
                         key=os.path.getmtime, reverse=True)
        ok, detail = deck_io.validate(staged, backups[0] if backups else None)
        if not ok:
            print("VALIDATION FAILED - deck not written:\n%s" % detail)
            return 1
        if deck_io.powerpoint_running():
            print("PowerPoint reopened mid-run - deck not written. Close it and re-run.")
            return 1
        shutil.copy2(staged, spec["pptx"])
        os.remove(staged)
        print("wrote %s" % spec["pptx"])

        for result, chosen in changed[deck_name]:
            for box in chosen:
                if "proposed_rect_px" not in box:
                    print("no proposed position for %s slide %s box %s, skipping anchor update"
                          % (deck_name, result["slide"], box["box_id"]))
                    continue
                anchors.save(deck_name, result["slide"], box["box_id"],
                             result["new_image"], box["proposed_rect_px"],
                             extra={"label": box.get("was_pointing_at")})
                planner.log_correction({
                    "deck": deck_name, "slide": result["slide"], "box_id": box["box_id"],
                    "applied_at": applied_at, "accepted": True,
                    "claimed_confidence": box.get("confidence"),
                    "match_score": box.get("match_score"),
                    "disagreement_px": box.get("method_disagreement_px"),
                    "rect": box.get("proposed_rect_px"),
                })
        deck_io.build_index(deck_name, force=True)
    if changed:
        print("\nAnchors refreshed. If anything looks wrong, run:"
              "  python b4ps.py correct --slide N --box ID")
    return 0


def cmd_correct(args):
    """Tell the tool a change it made was wrong - this is what it learns from."""
    if not os.path.exists(config.CORRECTIONS_LOG):
        print("Nothing has been applied yet.")
        return 1
    target = None
    with open(config.CORRECTIONS_LOG, encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if (str(rec.get("slide")) == str(args.slide)
                    and str(rec.get("box_id")) == str(args.box)
                    and rec.get("accepted") is True):
                target = rec
    if not target:
        print("No applied change found for slide %s box %s." % (args.slide, args.box))
        return 1
    planner.log_correction({
        "deck": target["deck"], "slide": target["slide"], "box_id": target["box_id"],
        "applied_at": target["applied_at"], "accepted": False,
        "claimed_confidence": target.get("claimed_confidence"),
        "match_score": target.get("match_score"),
        "note": args.note or "",
    })
    print("Logged. Run 'python b4ps.py tune' to fold this into the confidence bar.")
    return 0


def cmd_tune(args):
    thresholds, message = planner.tune()
    print(message)
    print("auto-apply bar is now %.2f" % thresholds["auto_apply_confidence"])
    return 0


def cmd_status(args):
    thresholds = config.load_thresholds()
    print("thresholds:")
    for key, value in sorted(thresholds.items()):
        print("   %-26s %s" % (key, value))
    count = len(glob.glob(os.path.join(config.ANCHOR_DIR, "*", "*", "*.json")))
    print("remembered anchors: %d" % count)
    if os.path.exists(config.CORRECTIONS_LOG):
        with open(config.CORRECTIONS_LOG, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
        wrong = sum(1 for r in rows if r.get("accepted") is False)
        print("logged outcomes: %d (%d corrected)" % (len(rows), wrong))
    else:
        print("logged outcomes: 0")
    return 0


# --------------------------------------------------------------------------
# new-slide creation
# --------------------------------------------------------------------------
#
# Unlike a screenshot update, this is never auto-applied regardless of how
# confident the plan looks: adding a slide is a content decision (a new
# tutorial exists now, the ToC changes) on the same footing as a wording edit,
# not a measurable realignment. `new-slide` only ever writes a report;
# `apply-new-slide` requires an explicit --confirm and is a separate command
# from the routine bulk `apply`, so it can never be swept up in one.

def cmd_suggest_templates(args):
    idx = deck_io.build_index(args.deck)
    for s in planner.suggest_templates(args.deck, idx, args.steps, limit=args.limit):
        print("  slide %-4d  %d box(es) on picture, %d picture(s)"
              % (s["slide"], s["boxes_on_picture"], s["picture_count"]))
    return 0


def cmd_new_slide(args):
    config.ensure_dirs()
    idx = deck_io.build_index(args.deck)
    th = config.load_thresholds()

    toc = None
    if args.toc_json:
        with open(args.toc_json, encoding="utf-8") as fh:
            toc = json.load(fh)
        toc["segments"] = [tuple(s) for s in toc["segments"]]

    result = planner.plan_new_slide(args.deck, args.template, args.title,
                                    args.screenshot, idx, th, toc=toc)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(config.REPORT_DIR, "newslide_" + stamp)
    os.makedirs(out_dir, exist_ok=True)
    if result.get("boxes"):
        planner.render_preview(result, out_dir)
    report_path = os.path.join(out_dir, "plan.json")
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    print("New slide %s (from template slide %s) -> %s\n"
          % (result["new_slide_number"], args.template, result["verdict"]))
    swap = result.get("image_swap")
    if swap:
        print("screenshot: replaces %s (match %.2f), saved as new file %s"
              % (swap["target_media"], swap["similarity"], swap["new_media_name"]))
    for box in result.get("boxes", []):
        print("  [%s] %s  conf %.2f" % (box["verdict"], box["name"], box.get("confidence", 0)))
    if result.get("layout_violations"):
        print("layout issues:")
        for v in result["layout_violations"]:
            print("   ! %s: %s" % (v["rule"], v["detail"]))
    if result.get("toc_plan"):
        tp = result["toc_plan"]
        print("\nToC insert on slide %s, shape %s, after paragraph %d:"
              % (tp["slide"], tp["shape_id"], tp["after_para_index"]))
        print("   %r" % "".join(t for t, _ in tp["segments"]))
        if not tp["valid"]:
            print("   ! INVALID:", tp["problem"])
    for problem in result.get("problems", []):
        print("! %s" % problem)
    if result.get("preview"):
        print("\npreview:", result["preview"])
    print("\nreport:", report_path)
    print("Nothing has been written. Review this, then:")
    print("  python b4ps.py apply-new-slide %s --confirm" % report_path)
    return 0


def cmd_apply_new_slide(args):
    with open(args.report, encoding="utf-8") as fh:
        result = json.load(fh)
    if not args.confirm:
        print("This adds a new slide (%s) and changes the ToC - pass --confirm "
              "after you've reviewed the report and preview." % result["new_slide_number"])
        return 1
    if result["problems"]:
        print("Not applying - unresolved problem(s):")
        for p in result["problems"]:
            print("   !", p)
        return 1
    if result.get("layout_violations"):
        print("Not applying - layout issues found:")
        for v in result["layout_violations"]:
            print("   !", v["detail"])
        return 1

    deck_name = result["deck"]
    staged = result["staged_source"]
    if not os.path.exists(staged):
        print("Staged file from duplicate_slide is gone (%s) - rerun new-slide." % staged)
        return 1
    if deck_io.powerpoint_running():
        print("PowerPoint is open and holds the deck locked - close it and re-run.")
        return 1

    changes, additions = {}, {}
    with deck_io.DeckReader(deck_name, path=staged) as reader:
        slide_xml = reader.read_text(result["xml"])
        for box in result.get("boxes", []):
            if box.get("changed"):
                e = box["proposed_emu"]
                slide_xml = deck_io.patch_shape_xfrm(slide_xml, box["box_id"],
                                                     e["x"], e["y"], e["cx"], e["cy"])
        changes[result["xml"]] = slide_xml.encode("utf-8")

        swap = result.get("image_swap")
        if swap:
            rels_xml = reader.read_text(swap["rels_part"])
            rels_xml = deck_io.repoint_picture_rel(rels_xml, swap["target_rid"], swap["new_media_name"])
            changes[swap["rels_part"]] = rels_xml.encode("utf-8")
            with open(result["new_image"], "rb") as fh:
                additions["ppt/media/" + swap["new_media_name"]] = fh.read()

        toc_plan = result.get("toc_plan")
        if toc_plan:
            toc_xml = reader.read_text(toc_plan["xml"])
            toc_xml = deck_io.insert_paragraph_after(
                toc_xml, toc_plan["shape_id"], toc_plan["after_para_index"], toc_plan["segments"])
            changes[toc_plan["xml"]] = toc_xml.encode("utf-8")

    spec = config.DECKS[deck_name]
    print("backup:", deck_io.backup(deck_name))
    final = os.path.join(config.WORK_DIR, "%s_newslide_final.pptx" % deck_name)
    deck_io.write_with_changes(deck_name, final, changes, additions=additions, source_path=staged)

    backups = sorted(glob.glob(os.path.join(spec["backups"], "*.pptx")),
                     key=os.path.getmtime, reverse=True)
    ok, detail = deck_io.validate(final, backups[0] if backups else None)
    if not ok:
        print("VALIDATION FAILED - deck not written:\n%s" % detail)
        return 1
    if deck_io.powerpoint_running():
        print("PowerPoint reopened mid-run - deck not written. Close it and re-run.")
        return 1
    shutil.copy2(final, spec["pptx"])
    os.remove(final)
    print("wrote %s (now %d slides)" % (spec["pptx"], result["new_slide_number"]))

    for box in result.get("boxes", []):
        if box.get("changed"):
            anchors.save(deck_name, result["new_slide_number"], box["box_id"],
                        result["new_image"], box["proposed_rect_px"],
                        extra={"label": box.get("was_pointing_at")})
    deck_io.build_index(deck_name, force=True)
    print("Anchors seeded for the new slide; index refreshed.")
    return 0


# --------------------------------------------------------------------------
# instruction text edits
# --------------------------------------------------------------------------
#
# Always REVIEW, never AUTO, regardless of confidence - wording is a judgment
# call. `edit-text` only writes a report; `apply-text-edit` requires --confirm.

def cmd_edit_text(args):
    config.ensure_dirs()
    idx = deck_io.build_index(args.deck)
    with open(args.segments_json, encoding="utf-8") as fh:
        new_segments = [tuple(s) for s in json.load(fh)]

    with deck_io.DeckReader(args.deck) as reader:
        result = planner.plan_text_edit(args.deck, args.slide, args.shape, args.para,
                                        new_segments, idx, reader)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(config.REPORT_DIR, "textedit_" + stamp)
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, "plan.json")
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    print("slide %s shape %s paragraph %s -> %s\n" % (args.slide, args.shape, args.para, result["verdict"]))
    if "old_text" in result:
        print("  old: %r" % result["old_text"])
        print("  new: %r" % result["new_text"])
    if "estimated_width_in" in result:
        print("  estimated width: ~%.2fin (box: ~%.2fin)"
              % (result["estimated_width_in"], result.get("box_width_in", -1)))
    for problem in result.get("problems", []):
        print("! %s" % problem)
    print("\nreport:", report_path)
    print("Nothing has been written. Review this, then:")
    print("  python b4ps.py apply-text-edit %s --confirm" % report_path)
    return 0


def cmd_apply_text_edit(args):
    with open(args.report, encoding="utf-8") as fh:
        result = json.load(fh)
    if not args.confirm:
        print("This changes wording on slide %s - pass --confirm after reviewing "
              "old/new text in the report." % result["slide"])
        return 1
    if result["verdict"] == "BLOCKED":
        print("Not applying - blocked:")
        for p in result["problems"]:
            print("   !", p)
        return 1

    deck_name = result["deck"]
    if deck_io.powerpoint_running():
        print("PowerPoint is open and holds the deck locked - close it and re-run.")
        return 1

    with deck_io.DeckReader(deck_name) as reader:
        xml = reader.read_text(result["xml"])
    new_xml = deck_io.rewrite_paragraph(
        xml, result["shape_id"], result["para_index"],
        [tuple(s) for s in result["new_segments"]])
    changes = {result["xml"]: new_xml.encode("utf-8")}

    spec = config.DECKS[deck_name]
    print("backup:", deck_io.backup(deck_name))
    final = os.path.join(config.WORK_DIR, "%s_textedit_final.pptx" % deck_name)
    deck_io.write_with_changes(deck_name, final, changes)

    backups = sorted(glob.glob(os.path.join(spec["backups"], "*.pptx")),
                     key=os.path.getmtime, reverse=True)
    ok, detail = deck_io.validate(final, backups[0] if backups else None)
    if not ok:
        print("VALIDATION FAILED - deck not written:\n%s" % detail)
        return 1
    if deck_io.powerpoint_running():
        print("PowerPoint reopened mid-run - deck not written. Close it and re-run.")
        return 1
    shutil.copy2(final, spec["pptx"])
    os.remove(final)
    print("wrote %s" % spec["pptx"])
    deck_io.build_index(deck_name, force=True)
    return 0


# --------------------------------------------------------------------------
# Safe PPT Engine (mechanical primitives: inspect / controlled mutation)
# --------------------------------------------------------------------------
#
# These operate on any explicit --input path, not the DECKS registry above -
# this is the generic, deck-agnostic engine layer, not the anchor/matching
# workflow. No semantic interpretation of shape meaning happens here.

def cmd_engine_inspect(args):
    try:
        result = ppt_engine.inspect_deck(args.input)
    except ppt_engine.SafeDeckError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("%s\n  slides: %d  (%d x %d EMU)"
              % (result["path"], result["slide_count"],
                 result["slide_width"], result["slide_height"]))
        for s in result["slides"]:
            print("  slide %d: %d shape(s)" % (s["slide_index"], s["shape_count"]))
            for sh in s["shapes"]:
                text = (" text=%r" % sh["text"]) if sh["text"] else ""
                print("    [%d] %s (%s)%s" % (sh["shape_index"], sh["name"],
                                              sh["shape_type"], text))
    return 0


def cmd_engine_set_text(args):
    try:
        out = ppt_engine.set_shape_text(args.input, args.output, args.slide,
                                        args.shape, args.text,
                                        overwrite=args.overwrite)
    except ppt_engine.SafeDeckError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("wrote %s (source untouched)" % out)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("scan"); p.add_argument("--all", action="store_true"); p.set_defaults(fn=cmd_scan)
    p = sub.add_parser("analyze")
    p.add_argument("--all", action="store_true", help="include screenshots older than the deck")
    p.add_argument("--slides", help="comma-separated slide numbers")
    p.set_defaults(fn=cmd_analyze)
    p = sub.add_parser("apply")
    p.add_argument("--report", help="report folder (default: most recent)")
    p.add_argument("--include", help="also apply these box ids, comma-separated")
    p.add_argument("--force", action="store_true", help="apply everything, including flagged items")
    p.set_defaults(fn=cmd_apply)
    p = sub.add_parser("correct")
    p.add_argument("--slide", required=True); p.add_argument("--box", required=True)
    p.add_argument("--note"); p.set_defaults(fn=cmd_correct)
    p = sub.add_parser("tune"); p.set_defaults(fn=cmd_tune)
    p = sub.add_parser("status"); p.set_defaults(fn=cmd_status)

    p = sub.add_parser("suggest-templates",
                       help="rank slides by step count to pick a new-slide template")
    p.add_argument("--deck", required=True)
    p.add_argument("--steps", type=int, required=True)
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(fn=cmd_suggest_templates)

    p = sub.add_parser("new-slide", help="plan a new tutorial slide (writes nothing)")
    p.add_argument("--deck", required=True)
    p.add_argument("--template", type=int, required=True, help="slide number to duplicate")
    p.add_argument("--title", required=True)
    p.add_argument("--screenshot", required=True)
    p.add_argument("--toc-json", help="path to a JSON file: "
                   '{"slide", "shape_id", "after_para_index", "segments": [[text,bold],...]}')
    p.set_defaults(fn=cmd_new_slide)

    p = sub.add_parser("apply-new-slide", help="write a reviewed new-slide plan")
    p.add_argument("report")
    p.add_argument("--confirm", action="store_true")
    p.set_defaults(fn=cmd_apply_new_slide)

    p = sub.add_parser("edit-text", help="plan an instruction-wording change (writes nothing)")
    p.add_argument("--deck", required=True)
    p.add_argument("--slide", type=int, required=True)
    p.add_argument("--shape", required=True)
    p.add_argument("--para", type=int, default=0)
    p.add_argument("--segments-json", required=True,
                   help="path to a JSON file: [[text, bold], ...]")
    p.set_defaults(fn=cmd_edit_text)

    p = sub.add_parser("apply-text-edit", help="write a reviewed text-edit plan")
    p.add_argument("report")
    p.add_argument("--confirm", action="store_true")
    p.set_defaults(fn=cmd_apply_text_edit)

    p = sub.add_parser("engine-inspect",
                       help="Safe PPT Engine: structural inspection of any .pptx")
    p.add_argument("--input", required=True)
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(fn=cmd_engine_inspect)

    p = sub.add_parser("engine-set-text",
                       help="Safe PPT Engine: controlled mutation, set one shape's text")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--slide", type=int, required=True)
    p.add_argument("--shape", type=int, required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(fn=cmd_engine_set_text)

    args = parser.parse_args()
    try:
        return args.fn(args)
    except config.MissingDeckSourceError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
