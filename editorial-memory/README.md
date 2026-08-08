# Editorial Memory — Slice 1

**Editorial Memory is a knowledge system, not a truth system.** It stores
claims, evidence, provenance, approvals, lifecycle state, and history.
Current truth is determined by approval and lifecycle rules, not by the
mere existence of an evidence artifact.

This is the minimal Slice 1 implementation: the smallest real system that
proves the founder's lifecycle requirement end-to-end (see
[`docs/EDITORIAL_MEMORY_IMPLEMENTATION_AUDIT.md`](../docs/EDITORIAL_MEMORY_IMPLEMENTATION_AUDIT.md)
for the accepted design and amendments this implements). It is not a
broad knowledge platform, not Documentation Intelligence, and does not
touch the Safe PPT Engine.

## Three entities

- **`Evidence`** — an artifact or observation (a browser check, a
  screenshot, a maintainer statement, existing documentation, a
  recording). Recording evidence never, by itself, changes what any
  `KnowledgeItem` currently says is true.
- **`KnowledgeItem`** — the durable subject being remembered (e.g. "how
  the Filters button behaves"). Identified by a stable `key` you choose;
  `get_or_create_knowledge_item` is idempotent on that key.
- **`KnowledgeState`** — one versioned claim about a `KnowledgeItem`.
  Every state must cite at least one `Evidence` id — a state with no
  evidence is rejected outright (`MissingProvenanceError`).

## The core invariant

> Evidence never promotes itself into Knowledge. Every `KnowledgeState`
> must have provenance referencing Evidence.

A screenshot existing in the system does not mean its contents are
current product truth. A browser observation existing in the system does
not mean its interpretation is automatically approved knowledge. The
only way a state becomes `current` is `approve_state(...)` — an explicit,
named human decision.

## Lifecycle

```
propose_state(...)              -> status = proposed
approve_state(...)              -> status = current
                                    (previous current, if any, -> superseded)
invalidate_state(...)           -> status = invalidated
```

Nothing is ever deleted from a `KnowledgeItem`'s history. `get_history`
returns every state it has ever had, in order, with enough on each one
(who approved it, when, what replaced or invalidated it) to explain what
was previously believed.

**Supersession vs. invalidation** — these answer different questions and
are never collapsed into one concept:

| | Was the claim ever true? | Outcome |
|---|---|---|
| Superseded | Yes — correct when approved, product then changed | Stays in history, `status = superseded`, points at what replaced it |
| Invalidated | No — never trustworthy (bad ingestion, hallucination, wrong attribution) | Stays in history, `status = invalidated`, excluded from `get_current` |

**Unresolved conflicts** — when new evidence contradicts the current
state, propose it with `relation_to_previous=Relation.CONTRADICTS`. That
state's `review_required` property is `True` until someone approves (or
otherwise resolves) it. The existing current state is *not* touched —
`get_current` keeps returning it — until an explicit approval replaces
it. `has_pending_conflict(item_id)` and `get_conflicts(...)` expose that
a review is outstanding without ever fabricating a resolution.

## Retrieval

- `get_current(item_id)` — the latest approved state, or `None` if
  nothing has ever been approved. Never a raw evidence artifact, an
  unapproved proposal, an unresolved contradiction, or a superseded/
  invalidated state.
- `get_history(item_id)` — every state, in order, lifecycle fields
  intact.
- `get_provenance(item_id, version)` — the `Evidence` records backing
  one specific state.
- `get_pending(item_id=None)` — the review queue (all proposed states).
- `get_conflicts(item_id=None)` — the unresolved-contradiction subset of
  the review queue.
- `get_evidence_type_summary(item_id, version)` — a plain count per
  evidence type cited by a state (e.g. `{"browser_observation": 1,
  "screenshot": 2}`), so a future reader can tell a diverse-source claim
  apart from a single-source one. **No scoring or ranking** — this is
  informational metadata only, by design.

## Evidence quality

`evidence_quality` (`high` / `medium` / `low`) describes the reliability
of the *artifact itself* — a blurry screenshot vs. a clean one — not
confidence that a claim built from it is true. It is a fixed three-value
field, not a numeric score, and nothing in this codebase converts it
into one.

## Feature-area naming

`feature_area` follows a `<platform>.<feature>` convention (e.g.
`desktop.filters`, `mobile.members`) adopted from the first record
onward. It is organizational/retrieval metadata only — a plain string,
not a taxonomy or registry to validate against.

## Editorial rationale

`rationale` is an optional field on `propose_state(...)`, for preserving
the human "why" behind a claim (e.g. why an annotation exists, why a
warning was kept) so it can be reused rather than rediscovered. Not
required for routine facts.

## Persistence

Plain JSON files, one per `Evidence` record and one per `KnowledgeItem`
(embedding its full state history), written atomically (temp file +
rename) under a directory you choose:

```
<root>/
  evidence/<evidence-id>.json
  knowledge/<feature-area>/<item-id>.json
```

This was the smallest sufficient choice for Slice 1: it needs no new
dependency (stdlib `json` only), it's human-readable and git-diffable
like the rest of this repository, and `EditorialMemory` reads fresh from
disk on every call rather than caching — so "reload from storage gives
identical results" holds by construction, not by a separately-maintained
guarantee. No database, vector store, graph store, or embeddings were
introduced.

## Known limitations (Slice 1 scope)

- **No CLI.** This is a Python API only. A CLI can be added later,
  alongside whatever actually needs to call it (Documentation
  Intelligence or an ingestion script) — building one speculatively now
  would be scope this slice doesn't need.
- **No `browser_observation` producer.** `EvidenceType.BROWSER_OBSERVATION`
  exists as a recordable evidence type; nothing automates capturing one.
  Live Bridge4PS access exists only on the maintainer's machine today.
- **No explicit "reject a proposal" operation.** A proposed state that
  nobody approves simply stays `proposed` (visible via `get_pending`)
  indefinitely. There is no separate "dismissed" status — Slice 1's
  contract didn't require one, and adding it speculatively would be
  scope creep.
- **Purge is deferred entirely.** The already-approved design allows a
  bounded, human-authorized hard-purge exception (for secrets/PII/legal
  deletion) as a direct file-level operation outside this API. Slice 1
  implements no purge operation at all — normal supersession/
  invalidation is the only lifecycle mechanism here. If Slice 1's own
  persisted files ever need it, delete/replace the specific JSON file by
  hand; no code change is required to do that safely, since nothing in
  this module assumes a file it wrote will always still exist.
- **No source-trust numeric tier.** The evidence-priority hierarchy
  (maintainer decision > browser verification > existing documentation >
  screenshot / recording) is not encoded as a stored numeric field
  anywhere — deliberately, to avoid the appearance of automatic scoring.
  `evidence_type` on each `Evidence` record is sufficient for a human (or
  a future reasoning layer) to apply that hierarchy when needed.
- **No concurrency control.** Writes are atomic per-file, but two
  concurrent callers approving the same `KnowledgeItem` at once could
  race. Acceptable at Slice 1 scale (small maintainer team, infrequent
  updates) — not solved here.
- **Not consumed by anything yet.** Documentation Intelligence, which
  would call this API, has not started.

## Explicitly not built here

Ontology, semantic IDs beyond ordinary persistence identity, graph
semantics, vector search, embeddings, external hosted database,
Documentation Intelligence, AI reasoning over memory, browser automation,
UI, or any automatic promotion of evidence into approved truth.
