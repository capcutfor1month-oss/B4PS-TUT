# Change Specification — Safe PPT Engine (Builds 1–2, Audit Repairs 1–2)

This is the canonical classification record required by `docs/TESTING.md` → "Canonical recording surface" (governing base tier, rationale, applicable specialized evidence profiles, and any explicit independent-audit requirement). It was missing for Builds 1–2 (part of Codex finding F-06); this file closes that gap. See `verification-report.md` for evidence and `audit-report.md` for independent-audit history.

## Approved user journey

An engineer (human or AI agent) working on Bridge4PS tutorial decks needs to inspect, and make small, explicit, verifiable changes to, a `.pptx` file — without any risk to the original file. They call `inspect_deck`/`describe_deck` to see structure, then one of `set_shape_text`, `move_shape`, `resize_shape`, `set_shape_geometry`, or `replace_picture` with an explicit target and a distinct output path, and get back either a validated output file or a clear, typed failure — never a corrupted source, a partial output, or an opaque crash.

## Functional requirements

- Deterministic structural inspection of any `.pptx`, independent of its filesystem path.
- Five controlled mutation primitives, each targeting one explicit `(slide_index, shape_index)`: text, position, size, atomic geometry, and picture replacement (with stale-relationship cleanup that respects shapes, backgrounds, and any other slide element sharing an image).
- A CLI surface (`b4ps.py engine-*`) exposing all of the above for manual verification.

## Failure and empty states

- Missing / empty / corrupt / non-PPTX-but-valid-ZIP input → typed `DeckSourceError`, no output written, no traceback at the CLI.
- Output path aliasing the input (directly, via symlink, or via any other filesystem alias) → typed `OutputPathError`, no publish attempted.
- Output path already exists and `overwrite=False` → typed `OutputPathError`, published atomically-or-not-at-all (no partial file, no clobber).
- Invalid target (bad slide/shape index, non-picture target for image replacement, non-text-frame shape for text mutation), invalid geometry values → typed `MutationError`, raised before any working copy is staged.
- Source file changes between hashing and publication → typed `SafeDeckError`, publication refused entirely (checked *before* the publish step, not only after).
- Any filesystem/library I/O failure during staging, save, or publication → typed `TransactionIOError`, no raw `OSError`/traceback surfaces at the CLI.

## Security and privacy requirements

- The engine only ever reads paths explicitly supplied by its caller; it never falls back to another file.
- Replacing a picture removes the old, now-unused image relationship (and therefore its media part) from the saved package where safe to do so, so a replaced screenshot does not linger as unused (and potentially sensitive) media in the output — without breaking a relationship still shared by another shape or the slide background.
- No credentials, secrets, or production data are involved; this is local file manipulation only.

## Acceptance criteria

- Full engine test suite passes (185 tests as of Audit Repair 2 — see `verification-report.md`).
- `python scripts/check_pipeline.py` passes.
- Canonical baseline ZIP `baseline/source-artifacts/B4PS-TUT-main.zip` SHA-256 unchanged.
- Independent Codex audit findings F-01–F-08 (first audit) and F-02/F-04/F-05/F-06/R-01/R-02 (re-audit) are addressed; F-01/F-03/F-07/F-08 remain closed without regression. A further independent Codex re-audit of this repair has not yet occurred — see `audit-report.md`.

## Explicit non-goals

- No semantic shape targeting, fuzzy matching, screenshot intelligence, or Documentation Intelligence.
- No Editorial Memory.
- No resolution of the 8 historically-unavailable Git LFS production assets.
- No changes to `lib/deck.py`, `lib/plan.py`, `lib/match.py`, `lib/anchors.py`, `lib/layout.py`, `lib/geometry.py` (the existing anchor/matching workflow), and no Architecture v0.1 redesign.

## Classification

- **Base tier: Standard** (per `docs/TESTING.md`). This is a normal internal-tool feature — not authentication, payments, secrets, tenant isolation, or a production migration (which would be High), and not a copy-only/non-behavioral change (which would be Trivial).
- **Rationale:** The engine mutates local `.pptx` files and is explicitly designed to protect an irreplaceable source asset from corruption. Given that safety purpose, verification for this component intentionally exceeds typical Standard-tier depth (adversarial/fault-injection testing, two rounds of independent audit) without the change itself carrying High-tier risk factors.
- **Applicable specialized evidence profile: Data-sensitive** (the engine performs bulk file writes — a full `.pptx` package rewrite per mutation). UI-sensitive: not applicable — there is no browser-rendered UI; the CLI is a developer tool, not an end-user surface.
- **Explicit independent-audit requirement:** Yes, beyond the deterministic High/Incident triggers — an independent Codex audit was performed on Builds 1–2 (found F-01–F-08), Audit Repair 1 closed all 8 and was itself re-audited (found F-02/F-04/F-05/F-06/R-01/R-02 remaining; F-01/F-03/F-07/F-08 confirmed closed), and this change (Audit Repair 2) is required to close the remainder. **A further independent Codex re-audit of this repair is still required and has not yet been performed** — see `audit-report.md`.

## Approval

- Founder: not recorded — no founder sign-off has occurred for this change.
- Date: —
- Status: Not approved (implementation proceeded under the founder's standing task-level authorization for this repair; the formal per-change approval field above is intentionally left truthful rather than fabricated, per `docs/TESTING.md` and the explicit instruction not to invent approvals that did not happen).
