# Change Specification — Editorial Memory Slice 2 (Maintainer-Decision Bootstrap, Repair 1)

This file is the canonical classification record required by `docs/TESTING.md` → "Canonical recording surface." Slice 1 (`openspec/changes/editorial-memory/`) is closed and unmodified by this change; this slice adds exactly one new capability on top of the existing, unmodified Slice 1 storage/lifecycle layer.

## Approved user journey

A maintainer has already made and approved an editorial decision (in a meeting, a chat thread, their own judgment) outside this system. They record it once, with the reasoning already settled, and it becomes durable current Editorial Memory immediately — with the same Evidence/KnowledgeItem/KnowledgeState separation, provenance, and lifecycle Slice 1 already enforces for every other evidence type. Nothing about how any *other* evidence type is created, proposed, or approved changes.

## Functional requirements

- `EditorialMemory.record_maintainer_decision(...)` records one `Evidence` (`evidence_type=maintainer_decision`) and one `KnowledgeState` (`knowledge_type=editorial`) for the identified `KnowledgeItem`, and returns that state already `current`.
- Internally this is `propose_state()` followed immediately by `approve_state()` — the same two Slice 1 methods every other caller uses, with no new approval mechanism and no direct write of `status=current`.
- `get_or_create_knowledge_item` is reused unmodified: the same natural `key` always resolves to the same `KnowledgeItem`; a slug collision with a different key still raises `KeyCollisionError` (EM-02 protection, untouched).
- `feature_area` is validated with the existing `validate_feature_area()` (EM-03 protection) before anything is written.
- **The requested `feature_area` must match the existing `KnowledgeItem`'s stored `feature_area` exactly (S2-01, added by Audit 1 repair):** before any duplicate-detection or mutation, a mismatch is rejected with typed `FeatureAreaMismatchError` — no Evidence is recorded, no `KnowledgeState` is created, and the mismatched request is never treated as an idempotent repeat.
- Exact-repeat input (identical `content`, `rationale`, `relation_to_previous`, and Evidence fields) is idempotent: the existing `KnowledgeState` is returned, no new records are created. This is a runtime comparison against already-stored records — no new persisted field, no separate dedup index. **`relation_to_previous` is part of this identity (S2-02, added by Audit 1 repair):** the same content/rationale/Evidence fields resubmitted with an explicitly different relation (e.g. `new` then `contradicts`) are NOT an idempotent repeat.
- A materially different decision (any field differing, including relation-only differences) for the same `KnowledgeItem` creates a new `KnowledgeState` through the unmodified Slice 1 lifecycle (proposed → approved, prior current → superseded).
- `relation_to_previous` defaults to `new` for a brand-new `KnowledgeItem` and `refines` for a subsequent decision on an existing one; callers may override it explicitly (e.g. to record a `contradicts` decision). This default is unchanged by the Repair 1 fixes.
- No other evidence type gains this bootstrap privilege — the method accepts no `evidence_type` parameter; `maintainer_decision` is the only value it can ever produce.

## Failure and empty states

All existing Slice 1 typed errors apply unchanged and are triggered through this new entry point exactly as through the old ones: `InvalidFeatureAreaError`, `KeyCollisionError`, `MissingProvenanceError`, `UnknownEvidenceError`, `InvalidLifecycleTransitionError`, `CorruptProvenanceError`, `InvalidEvidenceIdError`, `StorageCorruptionError`. One new error type was added by this repair round: a `feature_area` that differs from an existing `KnowledgeItem`'s stored value → typed `FeatureAreaMismatchError` (S2-01), raised before any record is created.

## Security and privacy requirements

Unchanged from Slice 1: no credentials, no network access, local structured-text persistence only.

## Acceptance criteria

- Full Editorial Memory test suite passes (85 tests — 59 from Slice 1/Repair 1/Repair 2, +17 original Slice 2 tests (2 updated for the S2-01/S2-02 fixes), +9 new adversarial tests for S2-01/S2-02).
- `python scripts/check_pipeline.py` passes; `git diff --check` passes.
- All 9 new adversarial tests confirmed to fail against the pre-repair `record_maintainer_decision`/`_find_matching_maintainer_state` logic specifically (regression proof, not tautology) — 7 fail outright, 2 pass coincidentally since they exercise default-relation behavior unaffected by either fix, reported honestly rather than dropped.
- `propose_state`/`approve_state` are proven, via a call-spy test, to be the actual mechanism used — not bypassed.
- Idempotency and KnowledgeItem-reuse are proven by record-count assertions (`list_evidence()`, `list_knowledge_items()`, `item.states`), not by inference; a mismatched `feature_area` is proven to create zero new records on rejection.
- Safe PPT Engine and Editorial Memory Slice 1's own files (`store.py`, `models.py`) are untouched by this change — `memory.py`, `errors.py` (new `FeatureAreaMismatchError`), `__init__.py` (its export), and the test file were modified.
- No review queue, no document-ingestion path, no new retrieval architecture, and no Documentation Intelligence work were added.

## Explicit non-goals

PPT/script/screenshot/recording ingestion, browser observation producers, a CLI or UI, review queues beyond what Slice 1 already exposes (`get_pending`/`get_conflicts`), any new retrieval architecture, Documentation Intelligence, and any redesign of the three-entity model, lifecycle, or invalidation/purge design (all explicitly out of scope per this slice's own instructions).

## Classification

- **Base tier: Standard**, same reasoning as Slice 1 — new local behavior on existing data-layer code, no external exposure, no production data.
- **Applicable specialized evidence profile: Data-sensitive** (new persisted-data write path). UI-sensitive: not applicable.
- **Explicit independent-audit requirement:** Per the founder's explicit task instruction, an independent Codex audit is required before this slice is considered closed or before any further Editorial Memory work begins. One round so far: Audit 1 on the original local implementation found S2-01 and S2-02 (**FAIL**); both are fixed here as a further local, uncommitted repair (Repair 1) — not committed, pushed, or merged, per explicit instruction, so Codex can audit the repaired tree directly. Audit 2 has not occurred — see `audit-report.md`.
