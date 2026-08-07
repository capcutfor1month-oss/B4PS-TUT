# Bridge4PS Decision Log

Durable decisions for the Bridge4PS Documentation Engineer repository. This log records this project's own decisions. It is separate from the Project-Pipeline decision log (`capcutfor1month-oss/project-Pipline` → `docs/DECISIONS.md`), which governs the pipeline itself.

## PROJ-001 — Pipeline adoption

**Decision:** Bridge4PS adopts the Universal Agentic Project Pipeline from `capcutfor1month-oss/project-Pipline` at source commit `e755ece0caf62f8e7df1a6c168727049c362cd4c` to govern repository-development workflow only.

**Reason:** Give this repository a repeatable, founder-friendly process for clarifying, specifying, implementing, testing, auditing, and releasing changes without adopting any pipeline concept as Bridge4PS product or domain content.

**Status:** Active

---

## PROJ-002 — Inherited pipeline decision: DEC-014 — Collaborative founder decision rule

**Decision (inherited from Project-Pipeline):** ChatGPT is the founder's brainstorming, explanation, and strategy partner. The founder and ChatGPT discuss evidence, options, risks, and recommendations before deciding the next product move. Claude implements approved work, and Codex audits independently when the approved workflow reaches the audit step. When the founder shares agent output, the default response is explanation and discussion — not automatic generation of another agent prompt.

**Applies to Bridge4PS as:** every agent working in this repository follows this rule unchanged.

**Status:** Active

---

## PROJ-003 — Inherited pipeline decision: DEC-017 — Target-domain / development-governance separation

**Decision (inherited from Project-Pipeline):** Two authorities apply together and must never be merged. Bridge4PS's own canonical documents (`docs/PRODUCT.md`, `docs/ARCHITECTURE.md`) govern what the product is. Project-Pipeline governs only how repository changes are clarified, approved, specified, investigated, implemented, tested, audited, and released. Being given, pointed to, or reading the Project-Pipeline repository never authorizes adopting its concepts as Bridge4PS domain content.

**Applies to Bridge4PS as:** the binding authority-boundary rule recorded in `docs/INDEX.md`.

**Status:** Active

---

## PROJ-004 — Baseline import deferred

**Decision:** The canonical raw baseline `B4PS-TUT-main.zip` is designated as the source of the Bridge4PS implementation but is not imported during pipeline bootstrap.

**Reason:** Bootstrap scope is limited to adopting the pipeline. Importing and verifying the baseline is a separately approved task, recorded as the exact next action in `docs/CURRENT.md`.

**Status:** Superseded by PROJ-005.

---

## PROJ-005 — Baseline imported; canonical ZIP is fidelity authority, GitHub materialization is a 50/58 publication view

**Decision:** `B4PS-TUT-main.zip` (SHA-256 `00f5e41f475b8205535481da11f73c4e4f0bd614e0d3b1efff938e921b9eb6ee`, 58 files, embedded source commit `85af51a123e237c14f61f5bb43094292db664561`) was imported and is the founder-approved final publication model: the unmodified archive is committed at `baseline/source-artifacts/B4PS-TUT-main.zip` as the authority for exact raw-baseline fidelity. Its extraction is committed at `baseline/B4PS-TUT-main/` with its original `.gitattributes` unmodified, containing 50 of the 58 source files byte-for-byte. The remaining 8 files are pre-existing Git LFS pointer-text files whose real binaries were never available; GitHub's server-side Git LFS enforcement (`GH008`) rejects any push referencing those objects regardless of `.gitattributes` content (confirmed by two prior failed attempts, one editing `.gitattributes` and one additionally squashing history — both still rejected). The founder approved omitting those 8 paths from the extracted GitHub tree only, while keeping their exact pointer representations preserved inside the canonical ZIP. The full omission manifest (path, LFS OID, declared size) is recorded in `docs/CURRENT.md`.

**Reason:** The canonical ZIP alone cannot be the only published artifact without also giving GitHub a materialized, browsable tree; but GitHub's LFS enforcement makes publishing pointer-text files impossible without either fabricating binaries (forbidden) or altering their content (forbidden, would destroy evidence they originated as LFS pointers). Splitting the two artifacts — ZIP as immutable fidelity authority, extracted tree as a 50/58 publication view with a documented, non-fabricated gap — satisfies "preserve raw-baseline defects and limitations as baseline evidence" without either fabricating content or leaving the import unpublishable.

**Status:** Active. This decision does not authorize Repository Hardening Batch 1, resolving the 8 missing binaries, or any other baseline content change.

---

## PROJ-006 — Repository Hardening Batch 1 completed

**Decision:** Repository Hardening Batch 1 was implemented directly on the imported baseline tooling at `baseline/B4PS-TUT-main/.b4ps-tools/`, scoped to reproducibility, path/filesystem safety, failure behavior, configuration/state, tests, and operator usability — not to Safe PPT Engine feature work. Concrete fixes: (1) removed a hardcoded personal absolute path (`/Users/aamir/Documents/B4PS TUT`) from `scripts/capture_and_rename.sh`, replaced with a run-time-resolved project root and a `TMPDIR`-honoring temp file path; (2) added `requirements.txt` and `requirements-dev.txt` declaring the previously-undeclared `Pillow`/`numpy`/`opencv-python-headless`/`pytest` dependencies (already named in prose in the tool's own README but not machine-installable); (3) added `config.MissingDeckSourceError` and `config.require_pptx()`, wired into `DeckReader.__init__`, `deck.backup()`, and the CLI's top-level dispatch in `b4ps.py`, so a missing, empty, or corrupt deck `.pptx` now fails with one clear, actionable message and exit code 1 instead of a raw `FileNotFoundError`/`BadZipFile` traceback; (4) added 16 automated tests under `.b4ps-tools/tests/` (`pytest`) covering the fixed failure paths with small synthetic fixtures, plus static regression checks against the hardcoded-path defect and a CLI smoke test proving the tool runs clean from a fresh checkout; (5) added a Setup section, a Running-tests section, and a truthful known-limitation note to `.b4ps-tools/README.md`.

**Reason:** This repository's own baseline import (PROJ-005) made the missing-deck-source failure path immediately, concretely reproducible — running any deck-touching command in this checkout hits exactly the defect fixed in (3). Hardening this foundation before Safe PPT Engine work begins prevents that engine from being built against tooling that crashes opaquely on the exact condition this repository is currently in, and removes a machine-specific path that would silently break for any contributor other than the original author.

**What was deliberately not done:** the 8 missing LFS binaries were not obtained, fabricated, or otherwise resolved (out of scope, unchanged limitation); `lib/plan.py`, `lib/match.py`, `lib/anchors.py`, `lib/layout.py`, `lib/geometry.py` were inspected for the same defect classes but not found to need a fix in this pass, and were not otherwise modified; no Safe PPT Engine feature, semantic-annotation, or workflow-intelligence work was started; the canonical ZIP `baseline/source-artifacts/B4PS-TUT-main.zip` was not touched.

**Status:** Active.

---

## PROJ-007 — Safe PPT Engine Build 1

**Decision:** Built the first Safe PPT Engine layer at `baseline/B4PS-TUT-main/.b4ps-tools/lib/ppt_engine.py`, using `python-pptx` (added to `requirements.txt`) rather than extending the baseline's existing hand-rolled XML-surgery approach in `lib/deck.py` — the two serve different purposes (`deck.py` is a purpose-built, high-performance surgical writer scoped to the two known production decks and their known shape conventions; the engine needs to safely load and describe *any* explicit `.pptx` path generically, which `python-pptx` already does safely and correctly). The engine provides: `load_deck` (typed, never-fallback loading), `inspect_deck` (deterministic structural JSON with no semantic interpretation), `create_working_copy` (mutation always staged off both the original and the final output path), and `set_shape_text` (the one controlled mutation primitive built this pass — explicit `(slide_index, shape_index)` targeting only, validated by reopening the saved result before it is placed at the caller's output path). Exposed via `engine-inspect` and `engine-set-text` CLI commands. Verified with 21 new tests (37 total) against synthetic fixtures built programmatically with `python-pptx`/`Pillow` — the 8 unavailable Git LFS assets were not touched.

**Reason:** The approved build order requires a safe, deterministic mechanical foundation (read/inspect/copy/mutate/save/validate/preserve) before any Documentation Intelligence or semantic capability can be layered on top. Establishing the pattern with one real, tested mutation primitive (text update) proves the safety invariants — source never modified, output path never collides, invalid input fails before mutation, output is reopened and content-verified after save — without yet committing to which richer primitives (move/resize/image-replace) Documentation Intelligence will actually need.

**What was deliberately not done:** no semantic shape identification, fuzzy matching, screenshot intelligence, or Documentation Intelligence; no additional mutation primitives beyond `set_shape_text`; no changes to `lib/deck.py`, `lib/plan.py`, `lib/match.py`, `lib/anchors.py`, `lib/layout.py`, or `lib/geometry.py` (existing anchor/matching workflow is untouched and independent of the new engine layer); the 8 missing LFS binaries were not obtained or fabricated; the canonical ZIP was not touched.

**Status:** Active.

---

## PROJ-008 — Safe PPT Engine Build 2: visual mutation primitives

**Decision:** Added four visual mutation primitives to `lib/ppt_engine.py`: `move_shape` (left/top, EMU only), `resize_shape` (width/height, EMU only), `set_shape_geometry` (left+top+width+height as one atomic operation, for future red-box relocation), and `replace_picture`. All coordinates/dimensions are EMU — python-pptx's and OOXML's own native integer unit; no other unit is accepted, and callers are responsible for converting from inches/points/pixels if needed. `move_shape` and `resize_shape` are each verified not to touch the other's attributes (a shared regression test proves resize does not move the shape, matching PowerPoint's own semantics — no repositioning side effect was observed or needed handling). `set_shape_geometry` validates all four values *before* any working copy is staged, so an invalid value cannot leave a partially-applied geometry anywhere, in memory or on disk.

`replace_picture` rejects a non-picture target shape and a missing/empty/unreadable replacement image before staging anything. Its default (and only, for this build) behavior preserves the existing shape's left/top/width/height frame exactly, regardless of the replacement image's own pixel dimensions or aspect ratio — chosen as the safest deterministic behavior, since it requires no cropping/scaling decision and matches how PowerPoint's own `blipFill` model already renders an image into a fixed frame. Implementation touches OOXML directly in exactly one place — repointing the picture's `p:blipFill/a:blip/@r:embed` relationship to a newly-added image part via python-pptx's own `SlidePart.get_or_add_image_part()` plus the `CT_Blip.rEmbed` attribute descriptor (both existing, documented python-pptx internals, not raw string/XML surgery) — isolated entirely inside `replace_picture`; no other code touches OOXML for image handling. Any existing crop data (`a:srcRect`) is preserved by construction, since it is never touched.

Build 1's final-publish step (a bare `shutil.copy2(staged, output_path)`) was not fully atomic — an interruption mid-copy could leave a partially-written file at `output_path`. Hardened this pass with `_publish_atomically()` (copy to a same-directory temp file, then `os.replace()`, which is atomic on the same filesystem) and retrofitted it onto `set_shape_text` as well as all four new primitives, per the explicit instruction to harden Build 1's atomicity within this build if it did not already guarantee it.

**Reason:** These are the specific geometry/image operations future red-box relocation and screenshot-swap work will call. Building them as small, independently-tested, deterministic primitives — reusing Build 1's staged-copy/validate/publish pattern rather than inventing a parallel one — keeps the mechanical foundation trustworthy before any semantic targeting is layered on top of it.

**What was deliberately not done:** no semantic shape identification, fuzzy matching, screenshot intelligence, automatic affected-slide detection, Editorial Memory, or Documentation Intelligence; no rotation/flip or other geometry attributes beyond left/top/width/height; no shape creation/deletion; no automatic aspect-ratio cropping or aesthetic image adjustment; no changes to `lib/deck.py`, `lib/plan.py`, `lib/match.py`, `lib/anchors.py`, `lib/layout.py`, or `lib/geometry.py`; the 8 missing LFS binaries (including both production decks) were not obtained, fabricated, or needed by any test; the canonical ZIP was not touched.

**Status:** Active.

---

## PROJ-009 — Safe PPT Engine Audit Repair 1 (Codex findings F-01–F-08)

**Decision:** An independent Codex audit of Safe PPT Engine Builds 1–2 found 8 defects. All 8 are fixed in `lib/ppt_engine.py`/`b4ps.py`, per-finding:

- **F-01 (critical, source aliasing):** `_assert_safe_output_path` now compares `os.path.realpath` of both paths (resolves symlinks even when the output's final path component does not yet exist) and, when both paths currently exist, additionally checks `os.path.samefile` (catches hardlinks/bind-mount aliasing realpath alone can miss). Applies uniformly to `set_shape_text`, `move_shape`, `resize_shape`, `set_shape_geometry`, and `replace_picture` (all route through this one function). The pre-existing before/after source-hash check is kept as defense-in-depth, not the primary protection.
- **F-02 (high, no-overwrite publication race):** `_publish_atomically` now branches on `overwrite`. `overwrite=False` opens the destination itself with `os.O_CREAT | os.O_EXCL`, which atomically fails if anything exists there at that instant — no separate exists-check followed by a write. `overwrite=True` keeps the prior same-directory-temp-file + `os.replace` atomic-rename approach.
- **F-03 (high, raw filesystem errors leak):** every mutation primitive now calls `load_deck(input_path)` (the typed validation boundary) before `file_sha256`/staging, via a shared `_validate_and_hash_source` helper. A missing input now raises `DeckSourceError`, never a bare `FileNotFoundError`. Verified at both the engine API and CLI boundary (all 5 mutation CLI commands exit 1 with a clean `error:` message, no traceback, for missing/empty/corrupt input).
- **F-04 (medium, stale media left in package):** `replace_picture` captures the old relationship id before repointing the blip, then calls `_drop_relationship_if_unreferenced`, which scans the slide's shape tree for any remaining `a:blip` still using that id and only then drops the relationship. python-pptx's own package writer serializes only parts still reachable via some relationship, so an unreferenced image part is automatically absent from the next save with no separate manual part-deletion step. Verified against actual ZIP package contents (not just API-level state): single-picture replacement removes the old media file; two pictures on one slide sharing the same image (python-pptx assigns them the same relationship id automatically) — replacing one leaves the other's image completely intact.
- **F-05 (medium, staging/failure cleanup gaps):** `create_working_copy` now wraps `shutil.copy2` in try/except, removing the allocated temp path and raising `DeckSourceError` on any copy failure. Failure injection tests cover all four transaction points (staging copy, save, validation, publication) and confirm: source untouched, no partial/incorrect final destination, no leaked `b4ps_engine_*`/`.b4ps_publish_*` temp file, typed error where applicable.
- **F-06 (medium, missing verification records):** this decision entry plus `openspec/changes/safe-ppt-engine/verification-report.md`, recording Builds 1–2 and this repair's classification, rationale, applicable profiles, commands, results, limitations, and — critically — that Builds 1–2 were marked complete *before* independent audit and *failed* that audit; re-audit of this repair is still required and has not happened.
- **F-07 (low, non-picture target validated after staging):** `replace_picture` now calls `_preflight_resolve_shape` (a throwaway `load_deck` against the original input) and checks `shape_type` before `create_working_copy` is ever called, so an invalid target creates no temp file. The same preflight-resolve pattern was applied uniformly to `set_shape_text` and the shared geometry-mutation path too, as a direct, minimal implementation of the cross-cutting contract's stated order ("validate source + target + path safety" before "stage privately") rather than a change scoped to F-07 alone.
- **F-08 (low, canonical inspection includes absolute path):** `inspect_deck`'s return value no longer includes a `path` key, so two byte-identical `.pptx` files at different filesystem paths now produce an equal result. A new `describe_deck(path)` wraps it as `{"source_path": ..., "structure": inspect_deck(path)}` for callers that want provenance; `engine-inspect`'s CLI/JSON output now uses `describe_deck`, so its JSON shape changed from a flat dict to this nested form (documented, deliberate, and covered by updated CLI tests).

48 new adversarial/fault-injection tests added (`tests/test_ppt_engine_audit_repair.py`), 120 total in the suite. Two pre-existing tests were updated, each with an explicit reason: one `OutputPathError` message-wording assertion (F-01 improved the message text) and the CLI JSON-shape assertions in `test_engine_cli.py`/`test_engine_cli_geometry_image.py` (F-08's `structure`/`source_path` split). No test was weakened; all 72 pre-existing behavioral assertions still hold.

**Reason:** These are safety-critical defects in the exact guarantees the Safe PPT Engine exists to provide before any semantic/AI layer is built on top of it. Fixing them now, with adversarial regression coverage proving each fix, keeps the mechanical foundation trustworthy rather than deferring known gaps into Documentation Intelligence work that would inherit them.

**What was deliberately not done:** no redesign of Architecture v0.1; no product-scope expansion; no Editorial Memory or Documentation Intelligence work; no attempt to obtain or fabricate the 8 missing production LFS binaries; no refactor of `lib/deck.py`, `lib/plan.py`, `lib/match.py`, `lib/anchors.py`, `lib/layout.py`, or `lib/geometry.py` (unrelated baseline modules, untouched); the canonical ZIP was not touched. Independent Codex re-audit of this repair was **not** performed as part of this decision — that is the explicitly required next action, not something Claude can self-certify.

**Status:** Active. Re-audit pending.
