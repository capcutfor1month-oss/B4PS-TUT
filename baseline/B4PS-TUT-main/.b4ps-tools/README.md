# B4PS deck updater

Updates the tutorial decks three ways: swaps a slide's screenshot and re-aligns
its red marking boxes, creates a brand-new tutorial slide from a template, or
edits a slide's instruction wording. All three refuse to guess when unsure.

**Analysis never writes to a deck.** Applying is always a separate, deliberate step.

## Setup

```bash
cd ".b4ps-tools"
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

**Known limitation:** as of this checkout, the two production decks
(`Current update/Desktop/*.pptx`, `Current update/Mobile/*.pptx`) are not
present - they were unresolved Git LFS pointers in the imported baseline (see
`docs/CURRENT.md` in the repository root). Commands that need a deck's `.pptx`
fail with a clear `deck source not found` error rather than a crash until
those files are resolved.

## Using it

```bash
cd ".b4ps-tools"
python b4ps.py scan       # what screenshots are waiting
python b4ps.py analyze    # work out what needs changing (writes nothing)
python b4ps.py apply      # apply the confident changes
```

Drop screenshots into `Source/Desktop/Screenshots` or `Source/Mobile/Screenshots`.
The folder decides which deck; the filename decides which slide:

| filename | meaning |
|---|---|
| `Slide_10.png` | replaces the screenshot on slide 10 |
| `Slide_14_b.png` | a slide with more than one screenshot (Chrome *and* Edge panels) |
| `Slide_10_reference.png` | an alignment reference, never applied |

Trailing double extensions (`.png.png`) and case differences are tolerated.

`scan` and `analyze` only pick up screenshots newer than the deck. Add `--all` to
include older ones, or `--slides 10,23` to narrow it down.

### Applying

```bash
python b4ps.py apply                 # everything the tool is confident about
python b4ps.py apply --include 51    # plus box 51, which it wanted you to check
python b4ps.py apply --force         # everything, including flagged items
```

A slide is **deferred** if any of its boxes are still unresolved. This is
deliberate: swapping the screenshot while leaving some of its own boxes pointing
at the old layout would leave the deck visibly wrong. Resolve the box, or pass
`--include`, and the whole slide goes in together.

### When it gets something wrong

```bash
python b4ps.py correct --slide 10 --box 51 --note "too wide"
python b4ps.py tune
```

This is the only way the tool improves. `correct` records that a change it was
confident about was actually wrong; `tune` raises the confidence bar if a band has
been wrong too often. The bar only ever moves **up**, and only once a band has
enough evidence behind it - a couple of early corrections cannot swing it.

## Creating a new tutorial slide

```bash
python b4ps.py suggest-templates --deck Desktop --steps 4      # find a slide to copy
python b4ps.py new-slide --deck Desktop --template 10 \
    --title "Desktop: New Feature" --screenshot new.png \
    --toc-json toc.json                                        # plan only, writes nothing
python b4ps.py apply-new-slide <report> --confirm               # writes it
```

`toc.json` says where the new feature's line goes in the deck's own Table of
Contents - a content decision, so nothing is inferred:
```json
{"slide": 2, "shape_id": "200", "after_para_index": 5,
 "segments": [["New Feature Name ", true], ["\t\t171", false]]}
```
`segments` are `[text, bold]` pairs - matching how ToC lines are actually built
(a bold feature name, a tab, a bold page number).

**Unlike a screenshot update, this never auto-applies, no matter how confident
the plan looks.** Adding a slide is a content decision - a new tutorial now
exists, the ToC changed - on the same footing as a wording edit, not a
measurable realignment. `apply-new-slide` always requires `--confirm`, and it
is a separate command from the routine bulk `apply`, so a new slide can never
be swept up in one.

What happens under the hood:
1. **The template is duplicated** via the pptx skill's own `add_slide.py` -
   that script does the structural bookkeeping a new slide needs (a fresh
   `<p:sldId>`, `[Content_Types].xml` entry, relationship) correctly; this tool
   does not reimplement it. Appended at the end of the deck, never inserted
   mid-deck - inserting would cascade-renumber every slide after it throughout
   the deck's own ToC, a much bigger and riskier job than one clean append.
2. **Box realignment reuses the exact same pipeline as a routine screenshot
   swap.** Immediately after duplication the new slide is byte-identical to
   its template, so realigning its boxes against the new screenshot *is* the
   routine problem this tool already solves - there is no separate,
   less-tested code path for it.
3. **The new slide gets its own copy of the replaced screenshot.** A freshly
   duplicated slide initially *shares* media files with its template (only the
   slide XML is copied, not the images) - swapping that shared file in place
   would silently corrupt the template slide too. So the new slide's picture is
   given a fresh, uniquely-numbered filename before anything is written, and
   only its own relationship is repointed to it.
4. **A layout check runs on the whole slide** before anything is considered
   ready - every box must land inside its picture, and no two boxes (or a box
   and the instruction text) may substantially overlap. Template-derived
   layouts should already satisfy this, but it is checked rather than assumed.

## Editing instruction wording

```bash
python b4ps.py edit-text --deck Desktop --slide 10 --shape 52 --para 0 \
    --segments-json new_text.json                    # plan only, writes nothing
python b4ps.py apply-text-edit <report> --confirm      # writes it
```

`new_text.json` is a list of `[text, bold]` segments, e.g. matching this deck's
own house style of bolding the UI control being referenced:
```json
[["Select ", false], ["Edit", true], (" from the ", false), ["Members", true], (" menu.", false)]
```

Formatting is preserved by reusing the paragraph's *existing* bold/regular run
templates (their real `<a:rPr>` XML - color, font, size), not by re-describing
them - so a bold label stays visually identical to the ones around it.

**Always requires `--confirm`, and is never treated as auto-appliable** even
when everything checks out - wording is a human judgment call, full stop.
What *is* checked automatically:
- the resulting XML is well-formed (a hard **BLOCKED** if not - this class of
  bug bit early development: a naive regex extracting `<a:rPr>` stopped at the
  first `/>` it saw, which was actually a *nested* self-closing `<a:latin/>`
  child, silently truncating the run and leaving the paragraph unbalanced;
  fixed by walking real tag boundaries instead of guessing with regex)
- a rough fit estimate (font size × character count vs. the text box's actual
  width) - conservative and flagged for your own visual confirmation rather
  than silently trusted, since this machine has no LibreOffice to render an
  actual preview against

## Safe PPT Engine (generic, deck-agnostic primitives)

Separate from the anchor/matching workflow above, `lib/ppt_engine.py` provides
mechanical, non-destructive primitives for any explicit `.pptx` path - not
just the two registered decks. It never modifies its input, never falls back
to another file, and always validates a mutation by reopening the saved
output before treating it as done.

```bash
python b4ps.py engine-inspect --input some.pptx --json   # structural inspection, no writes

# All coordinates/dimensions are EMU (914400 = 1 inch), python-pptx's and
# OOXML's own native unit.
python b4ps.py engine-set-text --input some.pptx --output out.pptx \
    --slide 0 --shape 2 --text "New wording"

python b4ps.py engine-move-shape --input some.pptx --output out.pptx \
    --slide 0 --shape 2 --left 914400 --top 914400          # left/top only

python b4ps.py engine-resize-shape --input some.pptx --output out.pptx \
    --slide 0 --shape 2 --width 1828800 --height 914400     # width/height only

python b4ps.py engine-set-geometry --input some.pptx --output out.pptx \
    --slide 0 --shape 2 \
    --left 457200 --top 457200 --width 1828800 --height 914400   # all four, atomically

python b4ps.py engine-replace-image --input some.pptx --output out.pptx \
    --slide 0 --shape 2 --image new.png   # preserves the existing frame; rejects a non-picture target
```

This is the mechanical foundation only - it assigns no meaning to what a
shape represents, and does no fuzzy/semantic shape selection. That is
future Documentation Intelligence work.

## How it decides

For each marking box, three independent checks:

- **A - element match.** Find the thing the box was marking, in the new
  screenshot. Includes an ambiguity test: these UIs are rows of near-identical
  list items, so a strong score means nothing if three other places score almost
  as well.
- **B - page shift.** Where the layout as a whole moved, from scattered landmark
  patches, outliers discarded. Independent of A.
- **C - edge support.** Do the proposed edges sit on real colour boundaries, or
  float in flat colour? Only applied when a box actually moves.

A box is auto-applied only when A is strong, A and B **agree**, and the combined
confidence clears the bar. Otherwise it is flagged.

If the marked control cannot be found at all, the box is **BLOCKED** rather than
moved - a renamed or removed control is a content change, and the slide's wording
may now be wrong. That judgement is not the tool's to make.

Positions auto-fix. Wording never does.

## What it remembers

`state/anchors/` stores a snip of what each box points at, refreshed from the new
screenshot after every successful realignment. The first update to a slide
discovers its elements; later ones just look them up, so repeat updates on the
same slide get cheaper. It also keeps up with the app's UI as it drifts, rather
than going stale.

`state/index_<deck>.json` caches each slide's pictures and boxes, keyed to the
deck's fingerprint - it rebuilds itself automatically when the deck changes
(including when PowerPoint re-saves it).

## Layout

```
.b4ps-tools/
  b4ps.py            command line
  lib/config.py      deck paths, ToC ranges, thresholds
  lib/deck.py        selective reads, XML/text patching, slide duplication,
                     media dedup, surgical write, validate
  lib/geometry.py    EMU <-> pixel maths, box-to-picture assignment
  lib/match.py       the three box-matching checks (deterministic, no model tokens)
  lib/layout.py      overlap/bounds checks - shared by all three capabilities
  lib/anchors.py     the anchor library
  lib/plan.py        change plans (screenshot update, new slide, text edit),
                     previews, corrections log, tuning
  state/             anchors, index caches, thresholds, corrections log
  reports/<stamp>/   plan.json + preview images
```

## Why analyzing and applying are fast

A `.pptx` is a ZIP, and in these decks ~99% of it is `ppt/media/` - already
storing PNG/JPG images that PowerPoint itself does not bother compressing
further. Two things follow from that:

- **Reading is selective.** `analyze` never touches a deck's images except the
  one picture each affected slide is actually replacing - it opens the archive
  and reads only that slide's XML, rels, and target image. A slide with no
  marking boxes on the swapped picture costs about 0.1s; a batch's total cost
  scales with slides actually touched, not deck size.
- **Writing is surgical.** `apply` streams the original archive into a new
  one, copying every untouched entry as raw bytes and substituting only the
  changed slide XML and media. Measured on the Desktop deck: unpacking
  everything to disk and recompressing everything on write took 31.2s; the
  same write via streamed substitution takes 0.5s.

Nothing is unpacked to a working directory any more - there is no disk
extraction step at all, just an open archive read on demand.

**What does not get faster this way:** the box-matching itself (multi-scale
template search + landmark cross-check) is compute, not I/O, and costs roughly
0.1-7 seconds per slide depending on how many marking boxes it has - unaffected
by any of the above. A coarse-to-fine (downsample-then-refine) speed-up for
that was tried and **reverted**: it mismatched several boxes that the plain
full-resolution search gets right, including the exact one that produced the
original slide 10 width error. That is a bad trade at any speed, so the search
stays simple. The one compute optimization that *is* in place - skipping the
matching work entirely for slides with zero boxes on the picture being
replaced - is pure waste elimination with no effect on results.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest tests/
```

Tests use small synthetic fixtures for filesystem/failure-path behavior - they
never fabricate or stand in for the real production decks.

## Notes

- **Close PowerPoint before applying.** It holds an exclusive lock on the live
  file. The tool checks first and stops rather than failing halfway.
- **Backups** go to each deck's `Backups/` folder, timestamped, 3 kept. One backup
  per apply run, not per slide.
- **Scope**: slides outside a deck's own Table of Contents range are flagged as
  out of scope (Desktop 7-149, Mobile 8-164). See `PPT-UPDATE-WORKFLOW.md`.
- **Requires** `opencv-python-headless`, `Pillow`, `numpy` - see `requirements.txt`.
  Validation reuses the pptx skill's `validate.py` if present, forced to UTF-8 -
  without that it reports spurious `charmap` errors on nearly every part of
  these decks.
