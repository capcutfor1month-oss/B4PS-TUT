"""Editorial Memory Slice 3 - retrieval functions.

Read-only lookups over Slice 1/2's existing storage and lifecycle rules.
Nothing here mutates memory, adds a schema, or introduces search/ranking -
it composes `EditorialMemory.get_current` / `get_history` /
`list_knowledge_items` (all unchanged) into the three lookups Documentation
Intelligence needs: by KnowledgeItem key, by feature_area, and by
knowledge_type. Default retrieval always goes through
`EditorialMemory.get_current`, so every lifecycle rule it already enforces
(approval-gated `current`, corrupt-provenance detection, contradictions
never promoted) applies here unchanged - this module adds no new rules.
"""

from __future__ import annotations

import dataclasses
from typing import Optional

from .memory import EditorialMemory
from .models import KnowledgeItem, KnowledgeState, KnowledgeType, StateStatus
from .store import slugify


@dataclasses.dataclass
class CurrentKnowledge:
    """One KnowledgeItem's current approved state, with the durable
    identity/lifecycle/provenance fields a consumer needs - without
    duplicating raw Evidence content (`evidence_refs` are ids; fetch via
    `EditorialMemory.get_provenance` only if the evidence itself is
    needed)."""

    id: str
    key: str
    knowledge_type: KnowledgeType
    feature_area: str
    version: int
    content: str
    status: str
    relation_to_previous: Optional[str]
    evidence_refs: list
    approved_by: Optional[str]
    approved_at: Optional[str]
    created_at: str
    rationale: Optional[str]

    @classmethod
    def _from(cls, item: KnowledgeItem, state: KnowledgeState) -> "CurrentKnowledge":
        return cls(
            id=item.id,
            key=item.key,
            knowledge_type=item.knowledge_type,
            feature_area=item.feature_area,
            version=state.version,
            content=state.content,
            status=state.status.value,
            relation_to_previous=state.relation_to_previous.value if state.relation_to_previous else None,
            evidence_refs=list(state.evidence_refs),
            approved_by=state.approved_by,
            approved_at=state.approved_at,
            created_at=state.created_at,
            rationale=state.rationale,
        )


def _resolve_key(memory: EditorialMemory, key: str) -> Optional[KnowledgeItem]:
    """Read-only key -> KnowledgeItem lookup. No side effects (unlike
    `get_or_create_knowledge_item`): an unknown key, or a key that
    collides at the slug level with a *different* stored key, both
    resolve to "no such item" rather than raising or creating anything."""
    item_id = slugify(key)
    data = memory.store.load_knowledge_item(item_id)
    if data is None:
        return None
    item = KnowledgeItem.from_dict(data)
    return item if item.key == key else None


def get_current_by_key(memory: EditorialMemory, key: str) -> Optional[CurrentKnowledge]:
    """The current approved knowledge for one KnowledgeItem, looked up by
    its natural key. Returns None if the key is unknown, or if the item
    exists but has never had a state approved (proposed-only, or its only
    states are superseded/contradicted/invalidated) - a superseded state
    or an unresolved proposal is never substituted for a missing current
    one."""
    item = _resolve_key(memory, key)
    if item is None:
        return None
    state = memory.get_current(item.id)
    return CurrentKnowledge._from(item, state) if state is not None else None


def _list_current(memory: EditorialMemory, feature_area: Optional[str], knowledge_type: Optional[KnowledgeType]) -> list:
    items = memory.list_knowledge_items(feature_area=feature_area, knowledge_type=knowledge_type)
    results = []
    for item in items:
        state = memory.get_current(item.id)
        if state is not None:
            results.append(CurrentKnowledge._from(item, state))
    return results


def list_current_by_feature_area(memory: EditorialMemory, feature_area: str) -> list:
    """Current knowledge for every KnowledgeItem in one feature_area,
    across all knowledge_types. Deterministic order (by item id, matching
    `JSONStore.list_knowledge_item_ids`'s sorted listing); items with no
    current state are simply absent, not returned as null entries."""
    return _list_current(memory, feature_area=feature_area, knowledge_type=None)


def list_current_by_knowledge_type(memory: EditorialMemory, knowledge_type: KnowledgeType) -> list:
    """Current knowledge for every KnowledgeItem of one knowledge_type,
    across all feature_areas. Same determinism/exclusion behavior as
    `list_current_by_feature_area`."""
    return _list_current(memory, feature_area=None, knowledge_type=knowledge_type)


def get_history_by_key(memory: EditorialMemory, key: str) -> Optional[list]:
    """The ordered lifecycle history for the KnowledgeItem at this key,
    excluding `invalidated` states: per the canonical retrieval contract,
    invalidated knowledge is excluded from every normal retrieval path
    (`get_current`, feature_area/knowledge_type listing, and history) and
    surfaces only through a dedicated invalidated-state query - not part
    of this slice. `current`, `superseded`, and `proposed`/`contradicted`
    states are all still returned, ordered exactly as
    `EditorialMemory.get_history` (unchanged) orders them - only the
    exclusion filter is applied here, nothing is reordered or
    reconstructed. None if the key is unknown; an empty list is a valid
    result for an item with no non-invalidated states. Never mutates
    memory."""
    item = _resolve_key(memory, key)
    if item is None:
        return None
    return [s for s in memory.get_history(item.id) if s.status != StateStatus.INVALIDATED]
