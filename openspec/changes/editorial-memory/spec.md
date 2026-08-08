# Change Specification — Editorial Memory Slice 1

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

## Security and privacy requirements

- No credentials, secrets, or production data are involved; this is local structured-text persistence only, written under a caller-chosen directory.
- No network access, no external service, no hosted database.

## Acceptance criteria

- Full Editorial Memory test suite passes (26 tests as of Slice 1 — see `verification-report.md`).
- `python scripts/check_pipeline.py` passes.
- The core invariant — evidence never auto-promotes into current knowledge, every `KnowledgeState` has provenance — is enforced in code (`MissingProvenanceError`, `UnknownEvidenceError`) and proven by dedicated tests, not documentation alone.
- The full Slice 1 lifecycle scenario (evidence → item → state → approval → current retrieval → new unapproved evidence → supersession → contradiction/review) passes as one deterministic end-to-end test.
- Safe PPT Engine (`baseline/B4PS-TUT-main/.b4ps-tools/`) is untouched.
- Architecture v0.1 is unchanged; no ontology, vector database, graph database, or hosted service was introduced.

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
- **Explicit independent-audit requirement:** Not a deterministic High/Incident trigger. Per the founder's explicit task instruction for this slice, an independent Codex audit is nonetheless the required next action before any further Editorial Memory work (Slice 2) begins — recorded here as an explicit requirement beyond the deterministic tier triggers, not inferred.
