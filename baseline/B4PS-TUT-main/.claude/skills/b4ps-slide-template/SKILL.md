---
name: b4ps-slide-template
description: Measured shape-XML spec for Bridge4PS tutorial slides (title, caption, step badge, marking box, screenshot border, layout). Use whenever building a new tutorial slide by hand or checking whether an existing/edited slide matches deck convention.
---

# B4PS tutorial slide template — measured spec

This documents the real formatting convention used by the in-scope tutorial
slides (Desktop ToC: 7–149, Mobile ToC: 8–164) in:
- `Current update/Desktop/MASTER Complete Bridge4PS Desktop-Browser Feature Tutorials.pptx`
- `Current update/Mobile/Copy of MASTER Complete Bridge4PS Mobile Feature Tutorials.pptx`

Every value below is **measured** — pulled from the live deck's XML via
`python-pptx`, across multiple slides, not taken from a single example or
from a prose description. Full sample list and method: [PROVENANCE.md](PROVENANCE.md).
A claim tagged **UNVERIFIED** came from the Claude PowerPoint add-in's own
self-reported study of the deck and has not been measured yet — don't treat
it as fact until it's checked against a real slide's XML the same way
everything else here was.

**This is a spec, not a generator.** `.b4ps-tools/b4ps.py` is still the
primary tool for existing-slide screenshot swaps, box realignment, and its
own `new-slide`/`edit-text` flows (see `HANDOFF.md`). This Skill exists for
the case CLAUDE.md already calls out: new slides hand-built because the
content is visually unlike any existing slide, with no prior box to
re-match against — the shape XML has to be built from this spec directly,
or used to sanity-check output from any other tool (including the add-in)
before it touches the live deck.

## Title

- Shape: TextBox, centered.
- Font: **Arial Narrow, 25pt** (`sz="2500"`).
- Two runs: `"Desktop: "` (or `"Mobile: "`) **not bold**, then the feature
  name **bold**.
- 25pt is measured on 6/6 sampled older slides (10, 28, 60, 90, 100, 120)
  and is the size the user asked for going forward. Several late-deck
  slides (140, 145, 148, 149) have smaller hand-set sizes (20/23/24/21pt) —
  measured, but as inconsistent outliers, not the convention. Don't copy a
  title size off any single slide without checking it against this entry
  first.

## Caption row

- Font: **Calibri, 11pt** (`sz="1100"`) — the current standard, matching
  the deck's most recently added slides (140, 145, 148, 149).
- Fixed, **not** length-dependent: a measured 41-character caption and a
  measured 332-character caption on the same slide (148) are both 11pt.
  Older eras of the deck used different fixed sizes (13pt, then 12pt) as it
  evolved over time — that's the actual source of the size variation, not
  sentence length.
- Bold wraps only the specific UI term/button name being referenced; plain
  weight for connecting words. Same run-splitting pattern as the title.
- **UNVERIFIED**: captions sometimes embed a small cropped icon image
  inline to show the actual button glyph (e.g. "Click the **Directory
  (icon)** icon"). Check for an inline `<p:pic>`/drawing anchored inside a
  text run before relying on this.

## Step badge

- Shape: **OVAL** (ellipse), 220133 × 220133 EMU (= 17.33pt × 17.33pt).
- Line: red `FF0000`, **1.5pt** (`w="19050"`).
- Fill: white (`schemeClr lt1`).
- Contains the bold step number.
- Measured consistent (oval + 1.5pt red line) across all 7 sampled slides
  (12, 60, 100, 120, 140, 148, 149) — no exceptions found.

## Marking box

- Shape: plain **RECTANGLE**, no fill.
- Line: red `FF0000`, **1.0pt** (`w="12700"`).
- Sized exactly to the UI element it's circling — no fixed box size.
- Measured consistent on 6/7 sampled slides; slide 100 had two boxes at
  0.75pt instead of 1.0pt (an older, pre-convention outlier — don't copy
  it).

## Screenshot picture border

- Single hairline: `<a:ln><a:solidFill><a:schemeClr val="tx1">
  <a:lumMod val="50000"/><a:lumOff val="50000"/></a:schemeClr>
  </a:solidFill></a:ln>`
- **Never** a hardcoded grey (`srgbClr val="7F7F7F"` or similar), and
  **never** a drop shadow — that was the old, wrong style mistakenly
  copied from slide 10/28 early in this project. Measured verbatim on
  slide 12 and slide 148's main screenshot.
- Not every picture on a slide has this border — small inset zoom crops
  (see Layout below) may have none (measured: slide 149's first picture
  has no `<a:ln>` at all). A missing border on an inset crop is not an
  error.

## Layout logic

- One big shared screenshot per distinct app screen, with numbered steps
  as a text row and callout boxes drawn directly on that shared image —
  not a grid of many small separate screenshots.
- Only use a separate picture per step when the steps are genuinely
  different app screens/states (menu opening vs. resulting toggled view).
- When two steps land on the *same* screenshot, they share **one**
  `<p:pic>` with two separate marking boxes — never two copies of the same
  image. Measured live on slide 12.
- **UNVERIFIED**: small inset crops (~10–70pt) layered on top of the main
  screenshot for zoomed-in icon detail are a legitimate convention, not an
  error to flag. Plausible — slide 149 does have an extra small borderless
  picture, consistent with this — but not conclusively established as
  deliberate vs. incidental.
