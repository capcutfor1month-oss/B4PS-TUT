# Desktop Deck Update Workflow (screenshot swaps + red marking boxes)

> **There is now a tool for this: `B4PS TUT/.b4ps-tools/` (see its README).**
> `python b4ps.py scan | analyze | apply` automates everything below - including
> the measurement discipline in the "lesson learned" section, which is encoded as
> a two-method agreement rule that refuses to auto-apply when the methods
> disagree. Read the rest of this document to understand *why* the tool works the
> way it does, or when doing something by hand that the tool does not cover.

This document captures the exact method used on 2026-07-30 to replace slide 10's
screenshot and realign its red "marking" boxes, so the same steps don't need to be
rediscovered next time. Applies to both the Desktop and Mobile decks — same slide
anatomy, same pitfalls.

## Deck anatomy (per content slide)

Each feature slide is built from layered shapes on top of one full-bleed screenshot:

- **One background picture** (`<p:pic>`), usually the largest shape, filling most of
  the slide body. `<a:blipFill><a:blip r:embed="rIdN"/><a:stretch><a:fillRect/></a:stretch>`
  — no `<a:srcRect>` cropping, so the image is stretched to exactly fill the picture's
  `<a:xfrm><a:off/><a:ext/>` frame. This means: **as long as the replacement image has
  the same aspect ratio as the frame, a straight file swap causes no distortion.**
- **Red marking/highlight boxes**: separate `<p:sp>` rectangle (or ellipse, for numbered
  step circles) shapes drawn *independently* on top of the picture, each with its own
  `<a:xfrm>` in absolute slide EMU coordinates (not relative to the picture). Line color
  `srgbClr val="FF0000"`. **These do NOT move or scale with the picture** — they're
  hardcoded to point at wherever the *old* screenshot's UI elements happened to be.
- **Numbered step circles**: small ellipses near the instruction text (not on the image),
  usually unaffected by a screenshot swap since they don't overlay the image.

## Why swapping the screenshot breaks the red boxes

The red boxes' positions were hand-placed to match pixel locations of specific UI
elements (a button, a menu item, a sidebar row) in the *original* screenshot. A new
screenshot — even of the same app/screen — will almost never have those UI elements in
the exact same pixel position, because:
- different fake/sample data (different usernames, different number of list items)
  shifts where dynamic content (dropdown menus anchored to a hover target, list rows)
  ends up vertically,
- fixed chrome (top toolbar icons, panel headers, search bars) typically stays in the
  same place — those boxes are usually still fine after a swap,
- row heights can differ slightly between screenshots if the list has a different
  number of items.

**Rule of thumb confirmed on slide 10:** static/toolbar-anchored elements (Members panel
icon, "All" filter dropdown, the main context-menu items themselves) stayed aligned.
Elements whose position depends on *where in a list something sits* (which row is
highlighted in a sidebar, which member row's "..." button was clicked) moved and needed
realignment.

## Step-by-step procedure for a screenshot swap

1. **Backup first** — always, before touching the live deck (see [[b4ps-tut-ppt-maintenance]]
   memory for the retention policy: `Backups/` subfolder next to the deck, timestamped,
   keep 3 most recent).
2. **Unpack the pptx**: `python -c "import zipfile; zipfile.ZipFile(r'deck.pptx').extractall(r'unpacked')"`
3. **Find the slide's real XML file**: slide *display order* N does not always equal
   `slideN.xml` — confirm via `ppt/presentation.xml`'s `<p:sldIdLst>` mapped through
   `ppt/_rels/presentation.xml.rels`. (For this deck, slides 1-15 happened to map 1:1,
   but don't assume this holds throughout — always check.)
4. **Find which media file is the background picture**: open `ppt/slides/_rels/slideN.xml.rels`,
   look at the image relationships, and open each referenced file in `ppt/media/` to see
   which one is the actual screenshot (vs. a logo/branding image reused across the deck —
   e.g. `image6.png` here is the Bridge4PS logo used on many slides, not slide-specific).
5. **Check dimensions/aspect ratio** of old vs. new image (PIL `Image.size`). If they're
   close (within ~1%), a straight overwrite of the media file (same filename) is a clean
   swap with no distortion. If very different, the picture's `<a:ext cx/cy>` frame will
   need adjusting too (out of scope so far — hasn't come up yet).
6. **Replace the media file in place** (same filename in `ppt/media/`) — this is simplest
   because the slide XML's relationship/embed reference doesn't need to change at all.
7. **Re-zip**: Windows Git Bash has no `zip` binary here — use Python's `zipfile` module
   to walk the unpacked directory and write a fresh archive (see script pattern below).
8. **Validate**: run the pptx skill's `scripts/office/validate.py new.pptx --original original.pptx`.
   On this machine, validate.py's file reads default to a non-UTF-8 codec and throw
   `'charmap' codec can't decode byte...` on nearly every slide/notes XML — **this is a
   pre-existing environment quirk, not a real error** (confirmed by running validate.py
   against the untouched original and getting the identical failures). Fix: prefix the
   command with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` to force proper decoding, then
   validate normally.
9. **No LibreOffice on this machine** — `scripts/office/soffice.py` (and thus the normal
   pdf/thumbnail visual-QA path) doesn't work here (`soffice` isn't installed, and the
   skill's sandbox shim assumes a Unix socket that doesn't exist on Windows). Visual QA
   has to be done differently — see next section.
10. **Check for the red marking boxes** — if the slide has any (most step-by-step slides
    do), don't assume the swap is done just because the image dropped in cleanly. Follow
    the realignment procedure below *every time* the background screenshot changes.
11. **Close PowerPoint before writing the final file** — the live `.pptx` is held open
    by PowerPoint (`POWERPNT.exe`) whenever someone has it open for review, and the file
    write will fail with "Device or resource busy". Check with:
    `Get-Process | Where-Object { $_.ProcessName -match "POWERPNT" }` (PowerShell) — if
    it returns a process, ask the user to close it before retrying the copy.
12. **Sanity-check the final file** opens correctly and slide count is unchanged
    (`python-pptx` `Presentation(path)` + `len(prs.slides._sldIdLst)`).

## Realigning red marking boxes without LibreOffice (the visual-QA workaround)

Since there's no renderer available, alignment is verified by **compositing the shape
coordinates directly onto the raw screenshot image with PIL**, not by rendering the slide:

1. Find every red-outlined shape in the slide XML: search for `srgbClr val="FF0000"`
   inside `<p:sp>...</p:sp>` blocks, and pull out each shape's `<a:off x y>` /
   `<a:ext cx cy>` (all in slide-absolute EMU).
2. Get the background picture's own `<a:off>`/`<a:ext>` (its frame in EMU) and the
   *pixel* dimensions of the screenshot image file (`PIL.Image.size`).
3. For any point in EMU-space on the picture, convert to pixel coordinates on the image:
   ```
   relative_x = (shape_off_x - picture_off_x) / picture_ext_cx
   pixel_x    = relative_x * image_pixel_width
   ```
   (same for y). This works because the picture uses simple `<a:stretch><a:fillRect/>`
   with no cropping — EMU-relative-to-picture-frame maps linearly to pixel-relative-to-image.
4. Draw each shape's box (PIL `ImageDraw.rectangle`) onto **the OLD (backup) screenshot**
   first, and view it — this tells you what UI element each box was actually pointing at
   (labels/positions in the XML like "Rectangle 47" don't tell you that on their own).
5. Draw the *same* EMU-derived boxes onto the **NEW** screenshot and view it — any box
   that no longer sits on the matching UI element is the one that needs realignment.
6. For each misaligned box: visually (or by scanning pixel rows/cols with numpy for
   sharp color transitions — e.g. list-divider lines, button backgrounds) find the new
   pixel bounding box of the *same conceptual UI element* in the new screenshot, convert
   back to EMU with the inverse of the formula above, and patch the shape's `<a:off>`/
   `<a:ext>` in the slide XML.
7. Re-render the overlay once more with corrected coordinates and re-check visually
   before repacking — cheap to iterate since it's pure image compositing, no PowerPoint/
   LibreOffice round-trip needed.
8. Typically only resize/reposition — most marking boxes on the same feature keep the
   same *width* (they're highlighting a UI element of roughly fixed size, like an icon or
   a single list row), so re-anchoring by center point while keeping original width/height
   is usually correct. Only adjust the size itself if the new screenshot's UI genuinely
   renders that element at a different size (e.g. a row height changed because the app
   redesigned that list).

## Known environment gotchas (this machine specifically)

- Git Bash has no `zip` — always repackage pptx via Python `zipfile`.
- `python3` is not on PATH here — use `python`.
- Bash paths (`/c/Users/...`) do NOT work when passed to `python -c` scripts on Windows —
  always use native Windows paths (`C:\Users\...`) inside Python code, even when the
  surrounding shell command is Bash.
- `validate.py` needs `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` prefixed or it reports
  spurious charmap decode failures on almost every part.
- No LibreOffice installed — `soffice.py`-based PDF/thumbnail conversion doesn't work;
  use the PIL-overlay approach above for visual QA instead.
- The live decks are frequently open in PowerPoint for review — always check
  `Get-Process POWERPNT` (or attempt the copy and watch for "Device or resource busy")
  before the final overwrite, and ask the user to close it if so.

## Scope reminder

Only touch slides that are listed in the deck's own Table of Contents (see
[[b4ps-tut-ppt-maintenance]] memory) — Desktop deck ToC covers slides 7-149; slides
150-170 (including hidden ones) are out of scope unless explicitly requested.

## Lesson learned: my first realignment pass on slide 10 was still wrong

After the first screenshot swap, I realigned the red boxes by eyeballing an overlay
render (compositing the OLD box's EMU coordinates onto both the old and new screenshots
and comparing visually — see procedure above). That caught two badly-misplaced boxes
but got the **sidebar row highlight box's width wrong**: I kept the old box's width
unchanged on the assumption that only *position*, not *size*, needed correcting. The
user caught this — the box was too wide, extending well past where the actual
highlighted list row ends in the new screenshot.

**Root cause:** eyeballing a rendered overlay is good enough to catch *gross*
misalignment (wrong row entirely, box floating over blank space) but not precise enough
to catch a width that's off by ~20%. When the user supplies a reference image showing
the *correct* alignment (e.g. a crop taken from inside PowerPoint with the shape
selected), don't just eyeball-compare it either — **measure it**:

1. If the reference image is a crop/zoom, it is usually at a **different pixel scale**
   than the raw screenshot embedded in the deck (e.g. PowerPoint's edit-canvas zoom
   level differs from the screenshot's native resolution). Never assume 1:1 — solve for
   the scale and offset empirically.
2. Do this by finding 2+ small, highly distinctive landmarks that exist in both images
   (e.g. a uniquely-colored icon — a two-tone logo, not a plain single-color square,
   which is too ambiguous/repetitive) and matching them with `cv2.matchTemplate` across
   a range of candidate scales (`cv2.resize` the template, try e.g. 0.5x-2x in small
   steps, keep the scale with the highest `TM_CCOEFF_NORMED` score).
3. **Cross-validate with at least two landmarks** — a single small-icon template match
   can converge on a plausible-looking but wrong scale (confirmed happening here: one
   single-icon match reported a confidently-wrong scale that a second landmark and a
   full 1D color-signal correlation both contradicted). Prefer a **1D color-signal
   cross-correlation along a whole column of stacked icons** (average color per row in
   the icon column, resample at candidate scales, slide against the same column in the
   other image, keep the lowest-error scale/offset) — this is far more robust than any
   single-icon 2D template match because the alternating color sequence (e.g.
   purple-orange-gold-gold-white icon colors in a row) is much less ambiguous than one
   isolated icon.
4. Once you have a validated scale + offset, transform the reference box's pixel
   coordinates into the target screenshot's pixel space, then **independently sanity
   check against the image content itself** — e.g. here, the corrected box's right edge
   was confirmed by checking that the list row's own highlighted background pixel color
   actually ends at that exact x-coordinate. This kind of independent confirmation (not
   just "does it look plausible") is what catches subtle errors before writing the file.
5. Only after that kind of numeric cross-validation, apply the fix, backup, repackage,
   validate, and write.

**Slide 10 final corrected box (Rectangle 50, the sidebar "Testing9999" row highlight),
for reference if this screenshot ever needs replacing again:** the box must span
exactly the currently-selected/highlighted channel row in the sidebar — full row height
only (not 2 rows, not a fixed size carried over from a previous screenshot), and its
right edge must stop exactly where that row's highlighted background color reverts to
the sidebar's base (unselected) background color, not extend further right into empty
sidebar space. Verify this with the "check where a distinct background color reverts"
technique from step 4 above rather than assuming the old box's width still applies.
