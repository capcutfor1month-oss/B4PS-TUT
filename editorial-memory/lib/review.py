"""Editorial Memory Slice 5 - review queue / unresolved-review workflow.

The smallest mechanism the existing contract requires: deterministic
retrieval of pending-review knowledge (proposed states, including
unresolved contradictions), with enough item identity attached that a
human reviewer knows *which* KnowledgeItem/version to act on - something
`EditorialMemory.get_pending()`/`get_conflicts()` don't provide on their
own when called across the whole store (they return bare `KnowledgeState`
objects with no back-reference to their parent item).

This module adds no new lifecycle, no new status, and no new mutation.
The human decision itself - approve, reject, or resolve a contradiction -
is made entirely through Slice 1's existing, unchanged lifecycle:

    approve       -> EditorialMemory.approve_state(item_id, version, approved_by)
    reject         -> EditorialMemory.invalidate_state(item_id, version, invalidated_by, reason)
                       (a rejected proposal was never trustworthy as
                       submitted - the same status Slice 1 already uses
                       for that meaning; leaving a proposal un-approved
                       forever is also a valid, silent-by-design "not
                       accepted" outcome and requires no call at all)
    resolve a       -> approve_state (the new state wins, superseding the
    contradiction       old current) or invalidate_state (the old current
                       state stands, the contradicting proposal is
                       rejected) - whichever a human decides is correct

No autonomous approval of any kind happens here or anywhere in this
module - every state this module surfaces stays `proposed` (and, for
review_required items, is exactly the state Slice 1's contradiction
handling already refuses to let overwrite `current`) until a human calls
one of the two methods above directly.
"""

from __future__ import annotations

import dataclasses
from typing import Optional

from .memory import EditorialMemory
from .models import KnowledgeItem, KnowledgeState, KnowledgeType


@dataclasses.dataclass
class PendingReview:
    """One proposed KnowledgeState, with the KnowledgeItem identity a
    reviewer needs to act on it (`approve_state`/`invalidate_state` both
    require the item id and version, not just the state)."""

    id: str
    key: str
    knowledge_type: KnowledgeType
    feature_area: str
    version: int
    content: str
    relation_to_previous: Optional[str]
    review_required: bool
    evidence_refs: list
    created_at: str
    rationale: Optional[str]

    @classmethod
    def _from(cls, item: KnowledgeItem, state: KnowledgeState) -> "PendingReview":
        return cls(
            id=item.id,
            key=item.key,
            knowledge_type=item.knowledge_type,
            feature_area=item.feature_area,
            version=state.version,
            content=state.content,
            relation_to_previous=state.relation_to_previous.value if state.relation_to_previous else None,
            review_required=state.review_required,
            evidence_refs=list(state.evidence_refs),
            created_at=state.created_at,
            rationale=state.rationale,
        )


def _list_pending(memory: EditorialMemory, feature_area: Optional[str], knowledge_type: Optional[KnowledgeType],
                   conflicts_only: bool) -> list:
    items = memory.list_knowledge_items(feature_area=feature_area, knowledge_type=knowledge_type)
    results = []
    for item in items:
        for state in memory.get_pending(item.id):
            if conflicts_only and not state.review_required:
                continue
            results.append(PendingReview._from(item, state))
    return results


def list_pending_review(memory: EditorialMemory, feature_area: Optional[str] = None,
                         knowledge_type: Optional[KnowledgeType] = None) -> list:
    """Every proposed state awaiting a human decision (first-time
    approval and unresolved contradictions alike), optionally narrowed to
    one feature_area and/or knowledge_type. Deterministic order: items in
    `JSONStore`'s sorted id order, states within an item in their
    append-only (oldest -> newest) order - the same ordering
    `EditorialMemory.get_pending` already produces, unmodified. Never
    mutates memory."""
    return _list_pending(memory, feature_area, knowledge_type, conflicts_only=False)


def list_conflicts(memory: EditorialMemory, feature_area: Optional[str] = None,
                    knowledge_type: Optional[KnowledgeType] = None) -> list:
    """The unresolved-contradiction subset of `list_pending_review`: only
    proposed states whose `relation_to_previous` is `contradicts` and
    which have not yet been resolved by approval or invalidation. Same
    determinism and no-mutation guarantees as `list_pending_review`."""
    return _list_pending(memory, feature_area, knowledge_type, conflicts_only=True)
