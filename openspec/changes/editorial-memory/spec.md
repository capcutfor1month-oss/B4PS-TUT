# Change Specification — Editorial Memory Slice 1 (Repair 2)

This is the canonical classification record required by `docs/TESTING.md` → "Canonical recording surface" (governing base tier, rationale, applicable specialized evidence profiles, and any explicit independent-audit requirement). See `docs/EDITORIAL_MEMORY_IMPLEMENTATION_AUDIT.md` for the accepted design this implements (three-entity model, six founder-approved amendments) and `verification-report.md` for evidence.

## Approved user journey

A maintainer records an observation about Bridge4PS (a screenshot, a browser check, a documentation excerpt, their own editorial judgment) as `Evidence`. They identify or create a durable `KnowledgeItem` for the subject that evidence is about, and propose a `KnowledgeState` referencing that evidence. Nothing changes what Documentation Intelligence (later) will retrieve as current truth until a maintainer explicitly approves that state. When Bridge4PS changes, new evidence can confirm, refine, contradict, or supersede what's on record — the old approved state is never deleted, only ever superseded (if it was real, valid history) or invalidated (if it turns out it was never trustworthy). An unresolved contradiction is visible as a pending review, not silently either accepted or discarded.

## Functional requirements

- Record an `Evidence` artifact with type, source reference, capture context, optional verification scope, and optional evidence quality (`high`/`medium`/`low`) — never itself current knowledge.
- Create or find a durable `KnowledgeItem` by a stable natural key, idempotently.
- Propose a versioned `KnowledgeState` for a `KnowledgeItem`, always requiring at least one `Evidence` reference.
- Approve a proposed state, making it `current` and moving any previous current state to `superseded` (never deleted).
- Invalidate a state (distinct from supersession) for knowledge that was never trustworthy, with no requirement that a replacement exist.
- Represent an unresolved contradiction (`relation_to_previous = contradicts` on a still-`proposed` state) without it silently becoming or replacing current truth.
- Retrieve current approved knowledge, full history, provenance for a specific state, the review/pending queue, and the unresolved-conflict subset of that queue.
- Preserve source-diversity metadata (evidence type counts per state) without any scoring or ranking.

## Failure and empty states

- A `KnowledgeState` proposed with no evidence references → typed `MissingProvenanceError`, no state created.
- A `KnowledgeState` proposed referencing an unknown `Evidence` id → typed `UnknownEvidenceError`, no state created.
- Approving, invalidating, or reading a nonexistent `KnowledgeItem` → typed `UnknownKnowledgeItemError`.
- Approving or invalidating a nonexistent state version → typed `UnknownStateVersionError`.
- Approving a state that is not `proposed` (already current/superseded/invalidated) → typed `InvalidLifecycleTransitionError`, no change.
- Invalidating an already-invalidated state → typed `InvalidLifecycleTransitionError`, no change.
- A `KnowledgeItem` with no approved state ever → `get_current` returns `None`, not an error and not a guess.
- A current state whose cited `Evidence` is missing or corrupt → typed `CorruptProvenanceError` (added by Audit 1 repair, EM-01) — `get_current` never hands back a "current" claim whose provenance can no longer actually be verified.
- A natural key that normalizes (via slugification) to the same id as an existing, different key → typed `KeyCollisionError` (added by Audit 1 repair, EM-02) — two distinct subjects are never silently merged into one `KnowledgeItem`.
- A `feature_area` that is not a safe `<platform>.<feature>` path segment (contains `/`, `\`, `..`, is empty, etc.) → typed `InvalidFeatureAreaError` (added by Audit 1 repair, EM-03), before anything is written to or read from disk.
- A persisted record file that exists but cannot be parsed as valid JSON → typed `StorageCorruptionError` (added by Audit 1 repair) rather than a raw `json.JSONDecodeError`.
- An `evidence_id` (caller-supplied or read back out of a persisted `evidence_refs` entry) that is not a safe generated-id token (contains `/`, `\`, `..`, is absolute, etc.) → typed `InvalidEvidenceIdError` (added by Audit 2 repair, EM-04), before anything is read from disk. A persisted, tampered reference reached via `get_current` still surfaces as `CorruptProvenanceError` (EM-01's existing check), chaining `InvalidEvidenceIdError`.

## Security and privacy requirements

- No credentials, secrets, or production data are involved; this is local structured-text persistence only, written under a caller-chosen directory.
- No network access, no external service, no hosted database.

## Acceptance criteria

- Full Editorial Memory test suite passes (59 tests as of this repair — 26 from Slice 1, +23 adversarial tests for EM-01/EM-02/EM-03 and JSON-corruption normalization from Repair 1, +10 adversarial tests for EM-04 from Repair 2 — see `verification-report.md`).
- `python scripts/check_pipeline.py` passes.
- `git diff --check` passes (no whitespace errors).
- The core invariant — evidence never auto-promotes into current knowledge, every `KnowledgeState` has provenance — is enforced in code (`MissingProvenanceError`, `UnknownEvidenceError`) and proven by dedicated tests, not documentation alone.
- The full Slice 1 lifecycle scenario (evidence → item → state → approval → current retrieval → new unapproved evidence → supersession → contradiction/review) passes as one deterministic end-to-end test.
- `get_current()` never returns a state with missing/corrupt Evidence provenance (EM-01); natural-key slug collisions are detected and rejected, not silently merged (EM-02); `feature_area` cannot escape the configured memory root (EM-03); `evidence_id` cannot escape the configured memory root, whether caller-supplied or read back from a persisted `evidence_refs` entry (EM-04) — each proven by adversarial tests confirmed to fail against the pre-repair code specifically, not merely against missing symbols.
- Safe PPT Engine (`baseline/B4PS-TUT-main/.b4ps-tools/`) is untouched by this repair, exactly as it was untouched by Slice 1 and Repair 1.
- Architecture v0.1 is unchanged; no ontology, vector database, graph database, or hosted service was introduced.
- No Editorial Memory Slice 2 work was started as part of this repair.

## Explicit non-goals

- Documentation Intelligence, AI reasoning over memory, or any automatic promotion of evidence into approved truth.
- Affected-slide detection, semantic red-box targeting, or any Safe PPT Engine coupling.
- Browser automation or a live `browser_observation` producer (the evidence type and its approval-gated promotion path are defined; nothing produces one automatically).
- A CLI, a UI, or any consumer of this API — nothing calls it yet.
- Purge/hard-deletion tooling — deferred per the already-approved design; normal supersession/invalidation is the only lifecycle mechanism this slice implements.
- Vector search, embeddings, a graph database, or a generalized Bridge4PS Product Knowledge platform.

## Classification

- **Base tier: Standard** (per `docs/TESTING.md`). A normal internal data-layer feature — not authentication, payments, secrets, tenant isolation, or a production migration (High), and not a copy-only/non-behavioral change (Trivial).
- **Rationale:** This is new local-file persistence and lifecycle logic with no external exposure, no production data, and no user-facing surface yet (nothing consumes it). It follows the same base-tier reasoning already applied to the Safe PPT Engine, without that engine's PPTX-corruption-risk rationale for exceeding Standard-tier depth — Editorial Memory Slice 1 does not mutate any existing production asset.
- **Applicable specialized evidence profile: Data-sensitive** (the change introduces new persisted structured data and a lifecycle/versioning model over it). UI-sensitive: not applicable — no browser-rendered UI, Python API only.
- **Explicit independent-audit requirement:** Not a deterministic High/Incident trigger. Per the founder's explicit task instruction, an independent Codex audit is nonetheless the required next action before any further Editorial Memory work (Slice 2) begins — recorded here as an explicit requirement beyond the deterministic tier triggers, not inferred. Two rounds so far: Audit 1 on merged Slice 1 (`93e87239ea9b55185f374f1a3aa2a390be03c24f`) found EM-01/EM-02/EM-03 (**FAIL**), fixed locally as Repair 1; Audit 2 on Repair 1's local diff returned **PASS WITH FINDINGS** — EM-01/EM-02/EM-03 confirmed closed, one new finding EM-04 raised, fixed locally here as Repair 2 — not committed, pushed, or merged, per explicit instruction, so Codex can audit the repaired tree directly. Audit 3 has not occurred — see `audit-report.md`.
