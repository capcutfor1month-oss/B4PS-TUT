# B4PS TUT — auto-loaded project context

Read this first, every session, on every machine. This file is synced via OneDrive so it
follows the project wherever it's opened (Windows or Mac). Full narrative history and
architecture notes live in [HANDOFF.md](HANDOFF.md) — read that too if picking up
mid-task; this file is the fast-start summary plus hard rules.

## What this project is

Two PowerPoint tutorial decks for the Bridge4PS chat app:
- `Current update/Desktop/MASTER Complete Bridge4PS Desktop-Browser Feature Tutorials.pptx`
- `Current update/Mobile/Copy of MASTER Complete Bridge4PS Mobile Feature Tutorials.pptx`

Only slides inside each deck's own Table of Contents are in scope (Desktop 7–149, Mobile
8–164). New feature material comes in via `Source/<Desktop|Mobile>/...` (screenshots, PDFs,
screen recordings) and gets turned into new numbered tutorial slides, appended at the end of
the deck, with a matching new ToC entry.

## Hard rules — do not skip these

1. **Always back up before writing the live deck.** Timestamped copy in that deck's
   `Backups/` folder, 3 kept. Automatic if using `.b4ps-tools`; manual otherwise.
2. **Use `.b4ps-tools/` instead of hand-editing** for screenshot swaps and box realignment
   on existing slides (`cd .b4ps-tools && python b4ps.py scan|analyze|apply`). See its
   `README.md`.
3. **New slides are hand-built, not templated via `new-slide`,** when the new content is
   visually unlike any existing slide (new screens, no prior box to re-match against). See
   "The real slide template" below for the exact shape XML to reuse.
4. **Never apply a new slide or a text edit without showing the user a rendered preview
   first and getting explicit confirmation.** Positions can auto-fix on *existing* slides;
   new content and wording never auto-apply, ever.
5. **Close PowerPoint before writing the live file** — it locks the file; tools check this
   and refuse rather than corrupt it.

## The real slide template (learned 2026-08-01 — do not use slide 10/28 as the template)

Early in this project slide 10 and slide 28 were used as style references for new slides.
That was **wrong** — the user pointed to `Source/Design/Slide Sample.pdf` (rendered from the
deck's actual **slide 148**, "Configure Channel Export Permissions") and `Source/Design/Template.png`
as the authoritative reference. Slide 148 is the correct template to copy shape XML from.
Key differences from the old (wrong) approach:

- **Title**: Arial Narrow, size **25pt** (`sz="2500"`), two runs — `"Desktop: "` **not bold**,
  the feature name **bold**. (Slide 148 itself uses 24pt; the user explicitly asked for 25pt
  for new slides — follow the user's stated size, not slide 148's literal size.)
- **Instruction/caption text**: Calibri, size **11pt** (`sz="1100"`). Bold the specific UI
  term being clicked, plain the connecting words, same run-splitting pattern as slide 148's
  captions.
- **Picture border**: plain single outline, `<a:ln><a:solidFill><a:schemeClr val="tx1"><a:lumMod val="50000"/><a:lumOff val="50000"/></a:schemeClr></a:solidFill></a:ln>` —
  **no** drop shadow, no `7F7F7F` grey line (that was the old, wrong slide-10-derived style).
- **Step badge** (red-outlined white circle with bold number): ellipse, 220133×220133 EMU,
  `<a:ln w="19050">` red `FF0000`, white `schemeClr lt1` fill — this part *was* already right
  (confirmed present on slide 10 too, it's a deck-wide convention).
- **Red marking box**: `<a:ln w="12700"><a:solidFill><a:srgbClr val="FF0000"/></a:solidFill></a:ln>`,
  `noFill`, plain rect — unchanged, deck-wide convention.
- **Layout preference (2026-08-01, from user feedback with a real example, slide 12
  "Join-Search Public Channels")**: prefer **one big shared screenshot per distinct app
  screen**, with numbered steps as a text row across the top and callout boxes drawn
  directly on that shared image — not a grid of many small separate screenshots. Only use
  a separate picture per step when the steps are genuinely different app screens/states
  (e.g. a menu opening vs. the resulting toggled view). When two steps land on the *same*
  screenshot, they must share one `<p:pic>` with two separate callout boxes, never two
  copies of the same image.

## Current work in progress (as of 2026-08-01, end of this session)

Building **3 new Desktop slides** for the "New Filters and Secondary Sidebar" feature
(source: `Source/Desktop/Creating slides/pdf/New Filters and secondary sidebar (1).pdf`,
plus two real screenshots the user dropped directly in
`Source/Desktop/Screenshots/Screenshot 2026-07-31 173810.png` and `173847.png`, plus a
screen recording `Source/Desktop/Screen recording/Notification_threedots.mp4` not yet
reviewed/used).

Status: **staged, not applied to the live deck.** Everything lives in
`.b4ps-tools/wip/new-filters-sidebar-2026-08-01/`:
- `staged_desktop.pptx` — full staged copy of the Desktop deck (173 slides: the original
  170 + 3 new ones at 171–173), built entirely outside the live file.
- `preview_slide_171_v3.png`, `172_v3.png`, `173_v3.png` — composited previews (no
  LibreOffice on the Windows machine this was built on, so these are hand-rendered with PIL
  reading the actual XML — legit substitute for a real PowerPoint render, keep doing this on
  any machine that also lacks PowerPoint/LibreOffice for previewing).
- `real_unread.png`, `real_menu.png`, `real_prefs.png` — the cropped real screenshots
  actually embedded in slides 171/172 (real app screenshots, not the PDF's demo/test data).
- `new_slides_report.md` — shape-by-shape coordinates and rationale from the first build
  pass (predates the slide-148 template correction and the layout consolidation below —
  useful for *how the numbers were derived*, not for the final positions).

**Slide contents (as last shown to the user, awaiting final go-ahead):**
- **171 — "Desktop: New Filters and Secondary Sidebar"**: 4 steps/screenshots — enable via
  Feature Preview; before/after sidebar; filter by workspace; new Unread toggle. 2×2 grid
  (4 genuinely different screens, can't consolidate further).
- **172 — "Desktop: Filters & Secondary Sidebar — Display Menu and Notifications"**: 4
  steps, 3 pictures in a single row (display menu; a shared screenshot for "open options
  menu" + "turn off notifications" with two boxes; the real Notification Preferences panel).
  This is the one that got restructured today to match the single-big-screenshot convention.
- **173 — "Desktop: Drafts in Sidebar"**: 2 steps/screenshots — enable toggle; resulting
  Drafts group in sidebar.

**Not done yet:**
1. Any further layout tweaks the user wants on 171/173 (they were told 172 changed, 171/173
   didn't — no objection registered yet).
2. Table of Contents entries for all 3 slides (not drafted at all yet — need ToC shape/slide
   location for the Desktop deck's own ToC, same pattern as the `new-slide` ToC-JSON format
   in `.b4ps-tools/README.md`).
3. Backup + apply to the live deck — **do not do this without a fresh explicit confirmation**,
   the last preview round (172 v3) had not yet been approved when this session ended.
4. The `Notification_threedots.mp4` screen recording has not been reviewed — worth checking
   before finalizing slide 172 in case it shows something the static screenshots don't.

## Mac machine notes (added 2026-08-01, setting up this project on Mac for the first time)

- **Always run `b4ps.py` through the project venv, never the system `python3`:**
  `.b4ps-tools/.venv/bin/python b4ps.py ...`. The Mac's system Python is 3.9.6, which is
  too old for the pptx skill's own scripts (`add_slide.py`, `office/validate.py` — they use
  `match` statements and `str | None` unions, both 3.10+ syntax). The venv uses Homebrew's
  Python 3.14 and has `opencv-python-headless`, `Pillow`, `numpy`, `defusedxml`, `python-pptx`
  installed. `add_slide.py`/`validate.py` are invoked by `deck.py` via `sys.executable`, i.e.
  whatever interpreter ran `b4ps.py` — so using the wrong Python silently breaks `new-slide`
  (`add_slide.py` crashes) and makes `apply`'s validation step fail (`validate.py` crashes),
  blocking writes that used to work fine on Windows.
- **`_find_pptx_script` in `lib/deck.py`** originally only searched `%APPDATA%` (Windows-only)
  for the pptx skill's scripts. Fixed to also search
  `~/Library/Application Support/Claude/local-agent-mode-sessions/...` on macOS.
- **`powerpoint_running()` in `lib/deck.py`** used to just return `False` unconditionally on
  non-Windows (no lock protection at all on Mac). Fixed to check for the Office `~$<filename>`
  sibling lock file, which both Windows and Mac PowerPoint create — cross-platform instead of
  `tasklist`-only.
- A stale `~$MASTER Complete...pptx` lock file (leftover from the Windows session, not real
  content) was found and removed from `Current update/Desktop/` — it would have permanently
  tripped the fixed lock check above.
- **The "PowerPoint (By Anthropic)" Claude Desktop extension is installed and partially
  fixed** (retested 2026-08-01, on a throwaway copy of the deck, never the live file):
  `export_pdf` now genuinely works — exports a real, correct multi-page PDF (verified
  page 148 pixel-matches the live slide). `get_slide_content` is still broken with the
  same AppleScript syntax error as before (`if shp has text frame then` — `-2741 syntax
  error: Expected "then", etc. but found property`). Also note: this MCP is only
  reachable from Claude Desktop's **Code** surface if the extension's tools happen to be
  exposed there — they were not visible in a Code session until re-checked via ToolSearch
  after the user re-enabled/fixed it in Desktop's Extensions settings; no restart was
  needed once that was done. `.b4ps-tools` still doesn't depend on it (it edits XML
  directly), but `export_pdf` is now viable for generating a real-slide preview/render
  step if wanted — `get_slide_content` is not.

## Rendering real slide previews (added 2026-08-02)

LibreOffice + poppler are installed on this Mac (`brew install --cask libreoffice`,
`brew install poppler`) specifically so slide previews don't depend on PowerPoint
AppleScript automation (which has been unreliable all session — `save slide as PNG`
kept throwing parameter errors). To render any slide as a real image:

```bash
soffice --headless --convert-to pdf --outdir <out_dir> "deck.pptx"
pdftoppm -jpeg -r 150 -f <slide_no> -l <slide_no> "<out_dir>/deck.pdf" slide
```

Full ~150MB Desktop deck converts in a few seconds. Verified against slide 148 —
screenshots, marking boxes, and text all render correctly; minor font-substitution
differences (e.g. bold weight) vs. real PowerPoint are cosmetic only, not real defects.
This is also the pipeline the `pptx` skill's own visual-QA section documents — no need
to reinvent it per-session, just check `soffice`/`pdftoppm` are on PATH first.

## B4PS Screenshot capture tool (added 2026-08-02)

A dedicated hotkey (**Cmd+Shift+6**) captures a screen region and saves it directly into
`Source/Desktop/Screenshots/` — no manual renaming from macOS's default
`Screenshot 2026-...png` naming needed. Built specifically so new screenshots land ready
for `.b4ps-tools`' `scan`/`analyze`/`apply` flow without a rename step.

- **What it is**: `/Applications/B4PS Screenshot.app` — a tiny compiled AppleScript app
  (`osacompile`) that calls `.b4ps-tools/scripts/capture_and_rename.sh`. That script runs
  `screencapture -i` (same engine as Cmd+Shift+4), then prompts for a slide number via an
  AppleScript dialog, then moves the file into `Source/Desktop/Screenshots/` with the
  correct `Slide_N.png` / `Slide_N_b.png` name. Always targets the **Desktop** deck — this
  hotkey captures the Mac's own screen, so it's inherently Desktop-app screenshots, not
  Mobile (which come from a phone/simulator).
- **Root cause of the "not saving / no rename prompt / lands on Desktop" bug (found and
  fixed 2026-08-05): two competing Services registrations were both trying to claim
  Cmd+Shift+6.** An old, already-abandoned Automator `~/Library/Services/B4PS
  Screenshot.workflow` (leftover from before this tool switched to Shortcuts.app) still had
  Cmd+Shift+6 registered via the Services-menu mechanism (`key_equivalent = "@$6"` in
  `~/Library/Preferences/pbs.plist`). The *current* Shortcuts.app Quick Action's own key
  equivalent had independently gotten corrupted/lost (showed as a broken
  modifiers-only combo with no actual key). Net effect: pressing Cmd+Shift+6 hit neither
  handler correctly and macOS's plain default screenshot fired instead — which explains the
  no-dialog, saved-to-Desktop symptom perfectly (that's just standard `Cmd+Shift+3/4`
  behavior, unrelated to this tool). **Fixed by**: deleting the old `.workflow` (moved to
  `~/.Trash`), removing its stale entry from `pbs.plist` via
  `PlistBuddy -c "Delete :NSServicesStatus:<key>"` + `killall cfprefsd` to flush, then
  re-recording Cmd+Shift+6 on the *current* Shortcuts.app Quick Action's "Run with:" field.
  **Diagnostic technique worth reusing**: `defaults read pbs NSServicesStatus` lists every
  Services-menu shortcut and its exact key equivalent — check this first any time a
  Quick-Action hotkey seems to silently do the wrong thing, before assuming it's the
  script's fault.
- **The hotkey is bound via Shortcuts.app**, not System Settings' Services pane directly
  (Services-menu keyboard shortcuts bound through System Settings itself turned out to be
  unreliable on modern macOS — bound but never actually fired). The working path: open the
  "Open App" shortcut in Shortcuts.app → info (`i`) button → "Use as Quick Action" gets
  checked automatically → click the "Run with:" field → press the combo directly (not
  through a separate "Add Keyboard Shortcut" dialog — that field itself is the recorder).
  This registers a real system-wide Quick Action shortcut that works with Shortcuts.app
  closed and survives restarts (it's a saved preference, not a running process — no
  LaunchAgent/background daemon needed). If a capture ever again seems to silently no-op or
  produce OS-default behavior, check `defaults read pbs NSServicesStatus` for the actual
  registered key equivalent before assuming the script broke.
- If rebuilding/re-signing the app bundle ever becomes necessary again, expect Screen
  Recording permission to need re-granting (see next bullet) **and** the Quick Action's key
  equivalent to need re-checking/re-recording afterward — both are tied to the app's exact
  identity/signature and can silently drop on rebuild.
- **Screen Recording permission is tied to the app's exact code signature.** If the app is
  ever rebuilt or re-signed (`codesign`), macOS silently revokes its Screen Recording grant
  even if the Privacy & Security toggle still *looks* on — captures then fail with
  `"could not create image from rect"`. Fix: System Settings → Privacy & Security → Screen
  & System Audio Recording → toggle "B4PS Screenshot" off then on again. Avoid rebuilding
  the app unless actually necessary, to avoid re-tripping this.
- The app lives in `/Applications/` (not `~/Applications/`) with an explicit
  `CFBundleIdentifier` (`com.b4ps.screenshot-app`) — both were required for it to even
  appear in Shortcuts.app's "Open App" picker; `osacompile`'s default output has neither.

## Persistent memory note

This machine's Claude Code also has local memory files (not synced, Windows-only) at
`~/.claude/projects/.../memory/`: `b4ps-deck-updater-tool.md`, `b4ps_tut_ppt_maintenance.md`,
`powerpoint-mcp-setup.md`. Everything load-bearing from them has been folded into this file
and HANDOFF.md so a fresh machine (e.g. Mac) doesn't need them — but if continuing on the
*same* machine, that memory still applies too and may have more granular detail.
