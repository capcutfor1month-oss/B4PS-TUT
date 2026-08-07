# Handoff — B4PS Tutorial Deck Maintenance

Written 2026-07-31, before compacting the session that built this. Updated
2026-08-01 with an in-progress WIP status (see bottom) ahead of moving this
project to a different machine (Mac). **[CLAUDE.md](CLAUDE.md) is now the
first thing to read** — it's auto-loaded every session and has the fast-start
summary plus the corrected slide-template rules; this file is the deeper
narrative. Deeper detail also lives in persistent memory (pointers at the
bottom, Windows-machine-local only) and in `.b4ps-tools/README.md`.

## What this project is

Two actively-maintained PowerPoint tutorial decks for a workplace-chat app
called Bridge4PS:
- `Current update/Desktop/MASTER Complete Bridge4PS Desktop-Browser Feature Tutorials.pptx` (170 slides)
- `Current update/Mobile/Copy of MASTER Complete Bridge4PS Mobile Feature Tutorials.pptx` (171 slides)

Each in-scope slide is a numbered how-to: a full-bleed screenshot, red
"marking boxes" pointing at specific UI elements, numbered step circles, and
instruction text. **Only slides listed in each deck's own Table of Contents
are in scope** — Desktop ToC covers slides 7–149, Mobile covers 8–164.
Anything past that (including hidden slides) is out of scope unless the user
explicitly asks otherwise.

`Source/<Desktop|Mobile>/Screenshots/` is where the user drops new
screenshots when something in the app UI changed. `Source/<Desktop|Mobile>/Screen recording/`
is for video sources (use the **watch** skill to pull frames from these —
empty as of this writing).

## The tool: `.b4ps-tools/`

**This is the primary way to update these decks now — do not hand-edit unless
the tool genuinely doesn't cover the situation.** Full docs in
`.b4ps-tools/README.md`; this section is the essential summary.

```bash
cd ".b4ps-tools"
python b4ps.py scan                          # what's waiting
python b4ps.py analyze                       # plan (writes nothing)
python b4ps.py apply                         # write confident changes
```

### Three capabilities

1. **Screenshot swap + box realignment** (the original, most-used flow).
   Drop `Slide_<N>.png` into a deck's Screenshots folder, then
   `analyze` → `apply`. A box only auto-applies when two independent
   measurement methods agree and confidence clears a bar; otherwise it's
   flagged in the report for you to resolve (`apply --include <box_id>`) or
   `--force`.

2. **New tutorial slide**: `new-slide` → `apply-new-slide --confirm`.
   Duplicates a template slide (matched by step count via
   `suggest-templates`), appends it at the deck's end, swaps in the new
   screenshot, and realigns every box by reusing the exact same pipeline as
   capability #1. **Always requires `--confirm`, never auto-applies** — unlike
   a box move, adding a slide is a content decision. ToC placement is supplied
   explicitly via a small JSON file, never inferred.

3. **Instruction text edit**: `edit-text` → `apply-text-edit --confirm`.
   Rewrites one paragraph's wording from a `[[text, bold], ...]` segment list,
   reusing the paragraph's own existing formatting XML so a bold UI label
   stays visually identical. Includes a rough fit-check (flagged, not
   trusted — no LibreOffice on this machine to render a real check). **Also
   always requires `--confirm`, never auto-applies** — wording is a human
   judgment call, period.

### Why it's built this way (don't undo these without reading why)

- **I/O is selective and surgical, not unpack-everything.** These decks are
  ~99% already-compressed images that PowerPoint itself doesn't re-deflate.
  `deck.py` reads only the slide XML + target image a touched slide actually
  needs, straight from the `.pptx` zip — no disk extraction. Writing streams
  the original archive into a new one, substituting only changed parts as raw
  bytes. Measured: old unpack-all+repack-all ≈31s → ≈0.5s.
- **A coarse-to-fine speed-up for the box-matching itself was tried and
  reverted.** It mismatched several boxes — including the exact one behind
  the original slide-10 mistake — that the plain full-resolution search gets
  right. Getting this wrong is a worse trade than being slow, at any speed.
  Don't re-attempt this without a very good reason and thorough regression
  testing against known-good slides first.
- **Positions auto-fix. Wording never does.** This is the load-bearing
  principle across all three capabilities. A control that can't be found is
  BLOCKED, not force-moved — a renamed/removed control means the slide's text
  may now be wrong, which is not the tool's call to make.
- **`layout.py`** checks every box lands inside its picture and nothing
  overlaps anything else, folded into all three plan types.
- **The anchor library** (`state/anchors/`) remembers what each box visually
  points at, refreshed after every successful realignment — so a slide gets
  cheaper to update every time it's touched, rather than costing the same
  each time.
- **Learning loop**: `correct --slide N --box ID` then `tune` raises the
  auto-apply confidence bar if a band has been wrong too often. One-directional
  (only ever goes up) and requires enough logged evidence before it moves.

### A real bug that got caught, not shipped

While building text-edit support, a naive regex extracting `<a:rPr>` run
properties stopped at the first `/>` it found — which was actually a *nested*
self-closing `<a:latin/>` font child, not the real closing tag. It silently
truncated every formatted run, producing invalid unbalanced XML. Caught by a
round-trip regression test across 149 real paragraphs on 11 real slides
*before* it ever touched a live deck. Fixed in `deck.py:_extract_element` by
walking actual tag boundaries instead of guessing with regex. If you're
touching text-run XML again, this is the class of bug to watch for.

### Known machine gotchas (still true)

- No `zip` binary in Git Bash — the tool never shells out to one anyway
  (pure Python `zipfile`), but keep this in mind for any manual work.
- `python3` isn't on PATH here — use `python`.
- Bash-style paths (`/c/Users/...`) don't work inside `python -c` scripts on
  Windows — always use native `C:\Users\...` paths in Python code even from a
  Bash shell.
- `validate.py` (from the pptx skill) needs `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`
  or it reports spurious `charmap` decode failures on almost every part —
  `deck.py`'s `validate()` already sets this internally, so this only matters
  if you ever call the pptx skill's validator directly.
- No LibreOffice installed — no rendered slide preview is possible. Visual QA
  is done by compositing shape coordinates onto the raw screenshot with PIL
  instead (see `PPT-UPDATE-WORKFLOW.md` for the technique), or by rough
  estimate + human visual confirmation for text fit.
- PowerPoint frequently has the live deck open (for review) — both `apply`
  paths check `Get-Process POWERPNT`-equivalent and refuse to write if it's
  running, rather than corrupt an open file.

## Backup policy

Every apply-style write backs up the live deck first, to a `Backups/`
subfolder next to it, timestamped, rolling window of **3 kept**. This is
automatic in the tool; if ever hand-editing, do this manually first — no
exceptions.

## What's tested vs. not

All three capabilities have been tested end-to-end against **disposable
copies** of the Desktop deck (never the live file during testing) via the
real CLI code paths — not just library-level calls. Confirmed: correct
verdicts on known-good and known-bad (stress test) inputs, PowerPoint-lock
refusal, no-op detection (a run with nothing to do doesn't burn a backup
slot), full `validate.py` pass, byte-level confirmation that a duplicated
slide's template is untouched after giving the new slide its own screenshot,
and a 149-paragraph text-formatting round-trip sweep.

**Not yet exercised**: a real multi-slide bulk batch through the actual CLI
(individual pieces are proven; the batching itself — several slides in one
`analyze`/`apply` run — hasn't been run end-to-end with real screenshots
beyond the single-slide case). Also not yet used in anger: the Mobile deck
(everything so far has been built/tested against Desktop; the tool is
deck-agnostic by design but Mobile hasn't been touched).

## Where the actual content knowledge lives

- `Current update/Desktop/DECK-KNOWLEDGE.md` and `Current update/Mobile/DECK-KNOWLEDGE.md` —
  full slide-by-slide indexes (feature → slide number, Pro-only flags, stale/
  flagged slides) built by background agents reading the decks' extracted text.
- `Current update/Desktop/PPT-UPDATE-WORKFLOW.md` — the original manual
  workflow this tool automates, plus the "lesson learned" write-up from the
  first (hand-fixed) slide-10 alignment mistake. Worth reading once for the
  *why*, even though the tool now handles the *how*.

## Persistent memory (auto-loaded in future sessions)

- `b4ps-deck-updater-tool` — the tool itself, this session's build log in
  memory form.
- `b4ps_tut_ppt_maintenance` — deck scope rules, backup policy, points to the
  tool as the preferred method.
- `powerpoint-mcp-setup` — a separately-installed PowerPoint MCP server
  (`supercurses/powerpoint`) exists too, for building presentations from
  scratch; not what this tool is for, don't confuse the two.

## If the next session needs to keep building

Natural next steps, none started: a real multi-slide bulk run with actual
screenshots; trying the tool against the Mobile deck; possibly extending
`suggest-templates` or the ToC-insert flow based on real usage friction.
Nothing here is urgent — the tool is functional and validated for its core
purpose as of this handoff.

## WIP as of 2026-08-01 (mid-task — read [CLAUDE.md](CLAUDE.md) first)

A follow-on session (still 2026-08-01) started building 3 brand-new Desktop
slides for the "New Filters and Secondary Sidebar" feature preview, using
`new-slide`'s *concept* but not its CLI path — these are hand-built XML since
there's no prior box to re-match against on entirely new screens. Full status,
exact file locations, and the corrected slide-template rules (slide 148, not
slide 10/28 — that was an early mistake in this sub-task, caught by the user)
are in [CLAUDE.md](CLAUDE.md)'s "Current work in progress" section — kept
there instead of duplicated here because CLAUDE.md is auto-loaded and this
file isn't. Short version: 3 slides are staged in
`.b4ps-tools/wip/new-filters-sidebar-2026-08-01/staged_desktop.pptx`, previewed
and mostly approved by the user, **not yet applied to the live deck**, ToC
entries not yet drafted. Pick up there.
