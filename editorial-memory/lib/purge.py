"""Editorial Memory Slice 7 - invalidated-knowledge audit access, and
bounded, human-authorized purge.

Two distinct, narrower operations, kept in one module because they are
the two halves of the same approved slice - not because they share
mechanism:

- **Invalidated-knowledge audit access** (`get_invalidated_by_key`,
  `list_invalidated_by_feature_area`, `list_invalidated_by_knowledge_type`):
  the dedicated query the design's retrieval model always reserved for
  `invalidated` states - deliberately never built in Slice 3/5, since
  Slice 3's default retrieval and Slice 5's review queue are exactly the
  normal paths `invalidated` must stay excluded from. Read-only, no
  mutation, same composition pattern as `retrieval.py`/`review.py`.

- **Bounded hard purge** (`purge_evidence`, `purge_knowledge_state`): the
  narrow, human-authorized exception to "nothing is ever deleted," for
  content that must not remain stored at all - secrets, credentials,
  personal information, maliciously ingested material, a legal deletion
  requirement. This is explicitly *not* part of the normal evolution flow
  (Slice 1/6): it is a direct storage-layer operation, invoked one record
  at a time, never a bulk or pattern-based operation, and never triggered
  by any ingestion/approval/evolution code path - only by a caller who has
  already decided, outside this system, that a specific record must go.
  Both purge functions share one canonical, non-claim tombstone contract:
  `Tombstone = {id, purged_at, purged_by, reason}`. Each writes it to the
  *same canonical record location* the purged record already occupied -
  never a new file, a new directory, or any other storage-architecture
  expansion (round-3 finding 2). Evidence is one-file-per-record, so its
  tombstone overwrites that same file in place (or the file is removed
  with no trace at all, `tombstone=False`). A KnowledgeState has no
  one-file-per-record location of its own - it lives embedded in its
  KnowledgeItem's `states` list, and the approved storage contract never
  defines any other canonical location for it - so its tombstone
  overwrites that same array slot, inside that same per-item file
  (`JSONStore.load_knowledge_item` filters tombstone-shaped entries back
  out of `states` for every ordinary reader, so this is invisible to
  `get_current`/`get_history`/the Slice 5 review queue/`get_invalidated_by_key`
  without any of them needing tombstone-specific logic of their own).
  Both purge functions perform exactly one atomic write each (round-3
  finding 3): removal/redaction and tombstone publication are the *same*
  write, not two separate ones, so a write failure can never leave a
  state removed with no tombstone, or a tombstone written but the
  original record only half-gone - the underlying file either ends up
  fully updated or is left completely untouched, per `_atomic_write_json`'s
  existing temp-file-then-rename discipline.
"""

from __future__ import annotations

import dataclasses
import datetime
from typing import Optional

from .errors import (
    MissingPurgeAuthorizationError,
    UnknownEvidenceError,
    UnknownKnowledgeItemError,
    UnknownStateVersionError,
)
from .memory import EditorialMemory
from .models import KnowledgeItem, KnowledgeType, StateStatus
from .retrieval import _resolve_key
from .store import is_tombstone_entry, validate_evidence_id, validate_knowledge_item_id


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# --- Invalidated-knowledge audit access ---------------------------------

@dataclasses.dataclass
class InvalidatedKnowledge:
    """One `invalidated` KnowledgeState with its KnowledgeItem identity -
    the dedicated audit view. Never returned by `retrieval.py`'s current-
    knowledge lookups or `review.py`'s pending-review queue."""

    id: str
    key: str
    knowledge_type: KnowledgeType
    feature_area: str
    version: int
    content: str
    relation_to_previous: Optional[str]
    evidence_refs: list
    invalidated_by: Optional[str]
    invalidated_at: Optional[str]
    invalidation_reason: Optional[str]
    created_at: str

    @classmethod
    def _from(cls, item: KnowledgeItem, state) -> "InvalidatedKnowledge":
        return cls(
            id=item.id,
            key=item.key,
            knowledge_type=item.knowledge_type,
            feature_area=item.feature_area,
            version=state.version,
            content=state.content,
            relation_to_previous=state.relation_to_previous.value if state.relation_to_previous else None,
            evidence_refs=list(state.evidence_refs),
            invalidated_by=state.invalidated_by,
            invalidated_at=state.invalidated_at,
            invalidation_reason=state.invalidation_reason,
            created_at=state.created_at,
        )


def get_invalidated_by_key(memory: EditorialMemory, key: str) -> Optional[list]:
    """Every `invalidated` state for the KnowledgeItem at this key. None
    if the key is unknown; an empty list is a valid result for an item
    with no invalidated states. Never mutates memory."""
    item = _resolve_key(memory, key)
    if item is None:
        return None
    return [InvalidatedKnowledge._from(item, s) for s in item.states if s.status == StateStatus.INVALIDATED]


def _list_invalidated(memory: EditorialMemory, feature_area: Optional[str],
                       knowledge_type: Optional[KnowledgeType]) -> list:
    items = memory.list_knowledge_items(feature_area=feature_area, knowledge_type=knowledge_type)
    return [
        InvalidatedKnowledge._from(item, state)
        for item in items
        for state in item.states
        if state.status == StateStatus.INVALIDATED
    ]


def list_invalidated_by_feature_area(memory: EditorialMemory, feature_area: str) -> list:
    """Every `invalidated` state across all KnowledgeItems in one
    feature_area. Deterministic order, same as `retrieval.py`/`review.py`.
    Never mutates memory."""
    return _list_invalidated(memory, feature_area=feature_area, knowledge_type=None)


def list_invalidated_by_knowledge_type(memory: EditorialMemory, knowledge_type: KnowledgeType) -> list:
    """Every `invalidated` state across all KnowledgeItems of one
    knowledge_type. Same determinism/no-mutation guarantees as
    `list_invalidated_by_feature_area`."""
    return _list_invalidated(memory, feature_area=None, knowledge_type=knowledge_type)


# --- Bounded, human-authorized purge (design §15.3) ----------------------

def _require_purge_authorization(purged_by: str) -> None:
    """Shared precondition for both purge operations (EM47-04): purge
    must always be an explicit, attributed human action - `purged_by`
    missing, `None`, or blank/whitespace-only is rejected before either
    operation touches disk."""
    if not isinstance(purged_by, str) or not purged_by.strip():
        raise MissingPurgeAuthorizationError(
            "purge requires a non-blank purged_by - purge must always be "
            "an explicit, attributed human action, never anonymous"
        )


@dataclasses.dataclass
class Tombstone:
    """The stub left in place of purged content: enough to show that
    something was here and why it's gone, without preserving the unsafe
    content itself. `reason` may be omitted/generalized by the caller
    when the reason text itself would be unsafe to retain."""

    id: str
    purged_at: str
    purged_by: str
    reason: Optional[str] = None


def purge_evidence(
    memory: EditorialMemory, evidence_id: str, purged_by: str,
    reason: Optional[str] = None, tombstone: bool = True,
) -> Optional[Tombstone]:
    """Bounded, human-authorized purge of one Evidence record. Evidence
    is stored one-file-per-record, so this maps directly onto the
    approved purge model: `tombstone=True` (default) overwrites the file
    with a small `Tombstone` stub; `tombstone=False` deletes the file
    with no trace at all, for the rarer case where even the tombstone's
    own metadata would itself be unsafe to retain - always available, per
    the approved contract, since a design that *required* a tombstone
    would itself be a data-safety bug.

    Raises `UnknownEvidenceError` if no such record exists - purge always
    targets one specific, already-identified record; there is no
    bulk/pattern form. Not called by any ingestion, approval, or
    evolution code path in this module or any other - only a caller who
    has already decided, outside this system, that this exact record must
    go.

    Note: if a `current` KnowledgeState still cites this evidence id,
    `EditorialMemory.get_current` will subsequently raise
    `CorruptProvenanceError` for that state (Slice 1's EM-01 protection,
    unchanged) - loudly, not silently. Purge does not check for or block
    this; the human authorizing a purge is expected to already understand
    that consequence for the specific record they are removing.

    Raises `MissingPurgeAuthorizationError` (EM47-04) if `purged_by` is
    missing, `None`, or blank/whitespace-only."""
    validate_evidence_id(evidence_id)
    _require_purge_authorization(purged_by)
    if memory.store.load_evidence(evidence_id) is None:
        raise UnknownEvidenceError(f"no Evidence record with id {evidence_id!r} to purge")

    if not tombstone:
        memory.store.delete_evidence(evidence_id)
        return None

    stub = Tombstone(id=evidence_id, purged_at=_now(), purged_by=purged_by, reason=reason)
    memory.store.save_evidence(dataclasses.asdict(stub))
    return stub


def purge_knowledge_state(
    memory: EditorialMemory, item_id: str, version: int, purged_by: str,
    reason: Optional[str] = None, tombstone: bool = True,
) -> Optional[Tombstone]:
    """Bounded, human-authorized purge of one KnowledgeState (round-3
    findings 1-3, revising the two-directory/two-write approach of the
    prior repair round). Unlike Evidence, a KnowledgeState is not stored
    one-file-per-record - it is embedded in its KnowledgeItem's `states`
    list. The approved storage contract defines no other canonical
    location for a KnowledgeState, so "the same location" a purge
    overwrites (finding 2) is that same array slot, inside that same
    per-item file - never a new directory or file.

    `tombstone=True` (default) replaces the target entry, *in place, at
    its existing array index*, with the approved non-claim tombstone
    contract - `{id, purged_at, purged_by, reason}`, `id` composed as
    `"<item_id>#<version>"`. `JSONStore.load_knowledge_item` filters any
    tombstone-shaped entry back out of `states` before any ordinary
    caller sees it (`get_current`, `get_history`, the Slice 5 review
    queue, `get_invalidated_by_key` are all unaffected, unmodified, and
    never need to know a tombstone exists), so a tombstoned state is
    exactly as invisible to normal retrieval as full removal was in the
    prior round - the difference is only in what's left for a raw,
    deliberate re-read of the item's own file to find (which
    `JSONStore.tombstoned_versions` and `load_knowledge_item_raw`
    expose). `tombstone=False` removes the entry with no trace at all,
    for the rarer case where even the tombstone's own metadata would be
    unsafe to retain.

    Both modes write the target KnowledgeItem's file exactly once
    (finding 3): the in-memory `states` list is fully updated - entry
    replaced or removed - *before* any disk write happens, then
    `JSONStore.save_knowledge_item` performs one atomic temp-file-then-
    rename publish. If that write fails for any reason, the original
    file on disk was never touched (the failure happens either before
    the rename, in which case the temp file is simply incomplete/absent
    and the real file is untouched, or during the rename itself, which
    on this filesystem's semantics either fully succeeds or leaves the
    original in place) - the original state is preserved exactly as it
    was, not partially purged. The caller sees the write's exception
    propagate; no partial-purge state is ever left readable.

    A version that already has a retained tombstone cannot be purged
    again: `states` no longer contains a real `KnowledgeState` at that
    version (it was replaced), so the lookup below finds nothing and
    raises `UnknownStateVersionError` exactly as it would for a version
    that never existed - re-purging an already-tombstoned identity is
    therefore always rejected, not silently accepted or double-purged.

    This bypasses `EditorialMemory`'s normal mutation methods entirely,
    per the approved contract (purge operates underneath the lifecycle
    layer, on the storage layer directly) - it is a direct
    `JSONStore`-level read/rewrite, not a `propose_state`/`approve_state`/
    `invalidate_state` call.

    Raises `InvalidKnowledgeItemIdError` (EM47-02) if `item_id` is not a
    safe, literal generated-id token. Raises `MissingPurgeAuthorizationError`
    (EM47-04) if `purged_by` is missing, `None`, or blank/whitespace-only.
    Raises `UnknownKnowledgeItemError`/`UnknownStateVersionError` if the
    target does not exist (or no longer exists as a real state, e.g. it
    was already purged)."""
    validate_knowledge_item_id(item_id)
    _require_purge_authorization(purged_by)

    data = memory.store.load_knowledge_item_raw(item_id)
    if data is None:
        raise UnknownKnowledgeItemError(f"no KnowledgeItem with id {item_id!r} to purge a state from")

    states = data["states"]
    index = next(
        (i for i, s in enumerate(states) if not is_tombstone_entry(s, item_id) and s.get("version") == version),
        None,
    )
    if index is None:
        raise UnknownStateVersionError(f"KnowledgeItem {item_id!r} has no state with version {version} to purge")

    stub = None
    if tombstone:
        stub = Tombstone(id=f"{item_id}#{version}", purged_at=_now(), purged_by=purged_by, reason=reason)
        states[index] = dataclasses.asdict(stub)
    else:
        del states[index]

    memory.store.save_knowledge_item(data)  # single atomic write - finding 3
    return stub
