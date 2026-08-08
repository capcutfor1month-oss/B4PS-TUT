# Change Specification — Safe PPT Engine (Builds 1–2, Audit Repairs 1–7)

This is the canonical classification record required by `docs/TESTING.md` → "Canonical recording surface" (governing base tier, rationale, applicable specialized evidence profiles, and any explicit independent-audit requirement). It was missing for Builds 1–2 (part of Codex finding F-06); this file closes that gap. See `verification-report.md` for evidence and `audit-report.md` for independent-audit history.

**Process deviation, recorded explicitly rather than presented as normal process:** `docs/TESTING.md` implies classification is recorded as part of specifying a change *before* implementation. This file was actually written *after* Builds 1–2 were already implemented and merged — a retroactive classification, prompted by the first independent Codex audit (finding F-06) rather than produced prospectively. It is recorded here as a deviation from the intended order, not silently presented as though it had happened at the normal time.

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

- Full engine test suite passes (206 tests as of the local Audit Repair 7 changes — see `verification-report.md`; 185 as of the last merged state, Audit Repair 2).
- `python scripts/check_pipeline.py` passes.
- Canonical baseline ZIP `baseline/source-artifacts/B4PS-TUT-main.zip` SHA-256 unchanged.
- Independent Codex audit findings addressed across seven rounds: F-01–F-08 (Audit 1); F-02/F-04/F-05/F-06/R-01/R-02 (Audit 2, re-audit of Repair 1); F-05/F-06/R-01/R-02 (Audit 3, re-audit of Repair 2 — F-02 and F-04 confirmed closed); F-05 (`os.close` gap)/F-06 (governance-wording gap)/R-02 (test-assertion gap) (Audit 4, re-audit of Repair 3's local diff — R-01 confirmed closed); F-05 (fd-closure gap)/F-06 (governance-wording gap)/R-02 (test-assertion gap) (Audit 5, re-audit of Repair 4's local diff); F-05 (Repair 5's `fstat`/retry fix for Audit 5's F-05 was itself an fd-reuse safety defect)/F-06 (governance record overstated Audit 5's scope and Repair 5's safety)/R-02 (regression didn't prove the retried fd was still safely owned) (Audit 6, re-audit of Repair 5's local diff). F-01/F-02/F-03/F-04/F-07/F-08/R-01 have remained closed without regression once fixed. The fixes for Audit 6's findings are local, uncommitted working-tree changes only, per explicit instruction — they have not been pushed, and Audit 7 completed with PASS WITH FINDINGS: F-05 closed; F-06 and R-02 remain and are addressed by current local Repair 7; Audit 8 is next — see `audit-report.md`.

## Explicit non-goals

- No semantic shape targeting, fuzzy matching, screenshot intelligence, or Documentation Intelligence.
- No Editorial Memory.
- No resolution of the 8 historically-unavailable Git LFS production assets.
- No changes to `lib/deck.py`, `lib/plan.py`, `lib/match.py`, `lib/anchors.py`, `lib/layout.py`, `lib/geometry.py` (the existing anchor/matching workflow), and no Architecture v0.1 redesign.

## Classification

- **Base tier: Standard** (per `docs/TESTING.md`). This is a normal internal-tool feature — not authentication, payments, secrets, tenant isolation, or a production migration (which would be High), and not a copy-only/non-behavioral change (which would be Trivial).
- **Rationale:** The engine mutates local `.pptx` files and is explicitly designed to protect an irreplaceable source asset from corruption. Given that safety purpose, verification for this component intentionally exceeds typical Standard-tier depth (adversarial/fault-injection testing, seven completed rounds of independent audit as of this record; Audit 7 was PASS WITH FINDINGS with F-05 closed and F-06/R-02 remaining; Audit 8 is pending) without the change itself carrying High-tier risk factors.
- **Applicable specialized evidence profile: Data-sensitive** (the engine performs bulk file writes — a full `.pptx` package rewrite per mutation). UI-sensitive: not applicable — there is no browser-rendered UI; the CLI is a developer tool, not an end-user surface.
- **Explicit independent-audit requirement:** Yes, beyond the deterministic High/Incident triggers — seven rounds so far: Audit 1 on Builds 1–2 (found F-01–F-08); Audit Repair 1 closed all 8 and was re-audited as Audit 2, against commit `13b3b532528b52a808030840734da9e58d92cfeb` (found F-02/F-04/F-05/F-06/R-01/R-02 remaining; F-01/F-03/F-07/F-08 confirmed closed); Audit Repair 2 closed those 6, was pushed and merged, and was re-audited as Audit 3 against the merged commit `69bb4761921ac7f7b843beb04ab255a2b272865e` (found F-05/F-06/R-01/R-02 remaining; F-01/F-02/F-03/F-04/F-07/F-08 confirmed closed); Audit Repair 3 fixed those 4 **as a local, uncommitted diff** and was re-audited directly against that local diff as Audit 4 — the first round in this history to review a diff before it was committed or pushed (found F-05's `os.close` gap, a governance-wording gap, and an R-02 test-assertion gap remaining; R-01 confirmed closed); Audit Repair 4 fixed those 3 and was re-audited directly as Audit 5 (found Repair 4's F-05 fix incomplete — it removed the leaked temp pathname but never verified the file descriptor itself stayed closed — plus 2 governance-wording gaps); Audit Repair 5 fixed those by having `create_working_copy` probe the fd with `os.fstat` and retry `os.close` once after a reported close failure, and corrected the governance gaps — and was re-audited directly as Audit 6, which found that retry approach itself unsafe (a retried or probed fd may already have been reused by unrelated code after the first close failure, so touching it again risks acting on a descriptor the process no longer owns), plus 2 further governance corrections (this record previously said Audit 5 had "confirmed" Repair 4's F-06/R-02 fixes closed, and described Repair 5's retry strategy as safe — both claims removed, since neither was independently established) — all now fixed; see `audit-report.md`. Audits 4, 5, 6, and 7 together establish that independent audit against a local, uncommitted diff is a normal, exercised part of this workflow, not a blocked state requiring a push first.

## Approval

- Founder: not recorded — no founder sign-off has occurred for this change.
- Date: —
- Status: Not approved (implementation proceeded under the founder's standing task-level authorization for this repair; the formal per-change approval field above is intentionally left truthful rather than fabricated, per `docs/TESTING.md` and the explicit instruction not to invent approvals that did not happen).
