# Current State

## Repository purpose

Bridge4PS Documentation Engineer product repository.

## Current phase

Repository Hardening Batch 1 completed. Safe PPT Engine Build 1 (mechanical read/inspect/mutate primitives) completed. Documentation Intelligence and semantic/AI capability on top of the engine have not started.

## Active change

None. No OpenSpec change is open.

## Completed

- Research: completed and closed.
- Architecture v0.1: founder-approved and locked.
- Universal Agentic Project Pipeline adopted from `capcutfor1month-oss/project-Pipline` at source commit `e755ece0caf62f8e7df1a6c168727049c362cd4c`.
- Pipeline adoption is complete: `scripts/check_pipeline.py` was repaired to validate this target repository truthfully (the inherited README assertion "This is a development-governance repository" was replaced with a target-repository-accurate assertion), and `python scripts/check_pipeline.py` passes with the result `Bridge4PS target-repository pipeline-adoption checks passed.`
- Canonical baseline imported and verified. The canonical ZIP is the complete immutable raw baseline: `baseline/source-artifacts/B4PS-TUT-main.zip` (SHA-256 `00f5e41f475b8205535481da11f73c4e4f0bd614e0d3b1efff938e921b9eb6ee`, unmodified, 58 files, embedded source commit `85af51a123e237c14f61f5bb43094292db664561`) contains every original file. The GitHub materialization at `baseline/B4PS-TUT-main/` contains 50 of those 58 source files, byte-for-byte identical to the ZIP, plus the baseline's own original `.gitattributes` restored unmodified. Eight unresolved Git LFS pointer entries are intentionally omitted from the extracted tree only, because their referenced binary objects are unavailable and GitHub rejects unresolved LFS references (`GH008`). Their exact source representations remain preserved inside the canonical ZIP. This omission is a repository-publication constraint, not a baseline repair — see the manifest below. `python scripts/check_pipeline.py` still passes.

### Omitted Git LFS pointer entries (GitHub materialization only — present in the canonical ZIP)

| Baseline-relative path | LFS OID | Declared size (bytes) |
|---|---|---|
| `.b4ps-tools/wip/new-filters-sidebar-2026-08-01/slides_171_173.pptx` | `sha256:a11552b742cfebe12b5445a399e04d2115949a2be6860e078632ba813c60372e` | 1946671 |
| `.b4ps-tools/wip/new-filters-sidebar-2026-08-01/staged_desktop.pptx` | `sha256:4dd652abbc81b097d8cf117fce311f5cdd290c4f78907bd92f39958e9db6f536` | 149116945 |
| `B4PS_Pipeline_Guide.pdf` | `sha256:3ad794a07ec8d76af8ebfa0ca17eb56b0e37907b7243c9cd6f79ffc712001f00` | 15909 |
| `Current update/Desktop/MASTER Complete Bridge4PS Desktop-Browser Feature Tutorials.pptx` | `sha256:47c12e3fd04ce950ed27d540e2fddc0ff9ef12250ee7a80fa263a5f862d470f4` | 142506574 |
| `Current update/Mobile/Copy of MASTER Complete Bridge4PS Mobile Feature Tutorials.pptx` | `sha256:85f8d522500af5de19226e3146d0d565927478ccb98225ff40ca9d3c624ad5b9` | 183065770 |
| `Source/Design/Slide Sample.pdf` | `sha256:592008b8f42b06520b61b1490836707bdcb02a2c534382007b573d91b6b7b53d` | 396583 |
| `Source/Desktop/Creating slides/pdf/New Filters and secondary sidebar (1).pdf` | `sha256:86311bd2578e961bb4792fecfd4e8bd401b65e7b1d425300b53f36e8541a767f` | 3503140 |
| `Source/Desktop/Screen recording/Notification_threedots.mp4` | `sha256:38565efb71bef3421cf719e15262d0cf722ccbe1266a6c8bf5c78d36d4d3124a` | 9369549 |

Each entry was present in the source ZIP only as Git LFS pointer text (not a real binary); their actual binary objects were never available to this import. GitHub rejected publishing those unresolved references with `GH008`. Their exact pointer representations remain preserved, unmodified, inside the canonical ZIP.

- Repository Hardening Batch 1 completed on the imported baseline tooling at `baseline/B4PS-TUT-main/.b4ps-tools/`. Hardened categories: reproducibility (removed a hardcoded personal absolute path from `scripts/capture_and_rename.sh`; added `requirements.txt`/`requirements-dev.txt` for previously-undeclared `Pillow`/`numpy`/`opencv-python-headless` dependencies), failure behavior (missing/empty/corrupt deck `.pptx` sources now raise a clear `MissingDeckSourceError` with an actionable message instead of crashing with a raw traceback, wired into `DeckReader`, `backup()`, and the CLI's top-level error handling), and operator usability (`.b4ps-tools/README.md` gained a Setup section, a Running-tests section, and an explicit note that the 2 production decks are currently unavailable in this checkout). 16 new automated tests were added under `.b4ps-tools/tests/` (`pytest`), all passing, covering the fixed failure paths (not just happy paths) using small synthetic fixtures — no production PPTX content was fabricated. `python scripts/check_pipeline.py` still passes; the canonical ZIP was not touched. See `docs/DECISIONS.md` for the full record and `docs/TESTING.md` for what remains deliberately unhardened.
- Safe PPT Engine Build 1 completed: `baseline/B4PS-TUT-main/.b4ps-tools/lib/ppt_engine.py`, built on `python-pptx` (added to `requirements.txt`), provides deck-agnostic, non-destructive primitives — `load_deck` (typed `DeckSourceError` on missing/empty/corrupt input, never falls back to another file), `inspect_deck` (deterministic structural JSON: slide count, dimensions, per-shape id/name/type/position/text/image-presence/z-order — no semantic interpretation), `create_working_copy` (mutation always stages on a private temp copy, never the original or the final output path directly), and `set_shape_text` (the one controlled mutation primitive built this pass: sets one explicitly-targeted shape's text, validated by reopening the saved output and reconfirming slide count and the new text, before being placed at the caller's output path). Exposed via two new CLI commands, `engine-inspect` and `engine-set-text`, operating on any explicit `--input` path. 21 new tests (37 total in the suite), all passing, using only synthetic fixtures built with `python-pptx`/`Pillow` — the 8 unavailable Git LFS assets were not touched, fabricated, or worked around. `python scripts/check_pipeline.py` still passes. This is the mechanical engine only: no semantic red-box detection, fuzzy shape matching, or documentation-intelligence work exists yet. See `docs/DECISIONS.md` (PROJ-007) for the full record.

## Registered skill sources

- `phuryn/pm-skills`
- `mattpocock/skills`
- `coreyhaines31/marketingskills`

See `docs/SKILLS.md` for Bridge4PS-specific availability and safety boundaries.

## Not included / not started

- Detailed Architecture v0.1 specification (not yet migrated into GitHub — do not reconstruct or invent it)
- Resolved binary content for the 8 omitted Git LFS pointer entries listed above (pointer text preserved in the canonical ZIP; actual binaries not present anywhere in this repository) — untouched by both Batch 1 and Safe PPT Engine Build 1
- Semantic/AI capability on top of the engine: red-box identification, fuzzy shape matching, screenshot intelligence, automatic screenshot replacement
- Editorial Memory, Documentation Intelligence, Human Review
- Ontology work, HTML migration, browser exploration, future semantic versions, Freshdesk automation, AppSheet automation, video automation
- Additional Safe PPT Engine mutation primitives beyond `set_shape_text` (move/resize shape, image replacement) — not built this pass; `set_shape_text` established the pattern, further primitives are a follow-up build
- Hardening of `lib/plan.py`, `lib/match.py`, `lib/anchors.py`, `lib/layout.py`, `lib/geometry.py` beyond what Batch 1 touched (no defects requiring a fix were found in scope during Batch 1's inspection, but they were not exhaustively re-audited line by line, and Safe PPT Engine Build 1 does not use or replace them)

## Current blocker

None for Repository Hardening Batch 1 or Safe PPT Engine Build 1. The 8 Git LFS pointer entries remain an unresolved baseline availability limitation (unchanged by either): their actual binary content is not present anywhere recovered, and was not fabricated. Neither batch needed the real decks — Safe PPT Engine Build 1 was validated entirely against synthetic fixtures.

## Exact next action

Next engine capability (additional mutation primitives) or Documentation Intelligence work has not started and requires separate founder approval before starting.
