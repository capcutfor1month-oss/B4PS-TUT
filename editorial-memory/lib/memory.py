"""EditorialMemory - the small, clean programmatic interface to the
Evidence / KnowledgeItem / KnowledgeState lifecycle.

Lifecycle rules are centralized here, not scattered through storage code
or any future CLI. This is the one place that enforces:

    Evidence never promotes itself into Knowledge. Every KnowledgeState
    must have provenance referencing Evidence.

and every other lifecycle rule: approval controls current-state
selection, supersession preserves history, invalidation differs from
supersession, and an unresolved contradiction is visible but does not
silently replace current truth.
"""

from __future__ import annotations

import datetime
import uuid
from pathlib import Path
from typing import Optional

from .errors import (
    InvalidLifecycleTransitionError,
    MissingProvenanceError,
    UnknownEvidenceError,
    UnknownKnowledgeItemError,
    UnknownStateVersionError,
)
from .models import (
    Evidence,
    EvidenceQuality,
    EvidenceType,
    KnowledgeItem,
    KnowledgeState,
    KnowledgeType,
    Relation,
    StateStatus,
)
from .store import JSONStore, slugify


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class EditorialMemory:
    """Stateless-between-calls facade over `JSONStore`. Every method
    reads current state from disk and, for mutations, writes a complete
    updated record back - there is no separate in-memory model that can
    drift from what is actually persisted."""

    def __init__(self, root: Path):
        self.store = JSONStore(root)

    # --- Evidence -------------------------------------------------------

    def record_evidence(
        self,
        evidence_type: EvidenceType,
        source_ref: str,
        captured_by: str,
        captured_at: Optional[str] = None,
        notes: Optional[str] = None,
        verification_scope: Optional[list] = None,
        evidence_quality: Optional[EvidenceQuality] = None,
    ) -> Evidence:
        """Record an artifact/observation/source. This alone never
        creates or changes any KnowledgeState - Evidence is not current
        knowledge by itself."""
        evidence = Evidence(
            id="ev-" + uuid.uuid4().hex[:12],
            evidence_type=evidence_type,
            source_ref=source_ref,
            captured_by=captured_by,
            captured_at=captured_at,
            recorded_at=_now(),
            notes=notes,
            verification_scope=list(verification_scope) if verification_scope else None,
            evidence_quality=evidence_quality,
        )
        self.store.save_evidence(evidence.to_dict())
        return evidence

    def get_evidence(self, evidence_id: str) -> Evidence:
        data = self.store.load_evidence(evidence_id)
        if data is None:
            raise UnknownEvidenceError(f"no Evidence record with id {evidence_id!r}")
        return Evidence.from_dict(data)

    def list_evidence(self) -> list:
        return [self.get_evidence(eid) for eid in self.store.list_evidence_ids()]

    # --- KnowledgeItem ---------------------------------------------------

    def get_or_create_knowledge_item(
        self, key: str, knowledge_type: KnowledgeType, feature_area: str
    ) -> KnowledgeItem:
        """Idempotent by `key`: the same natural key always resolves to
        the same durable KnowledgeItem id, so recording more evidence
        about the same subject never creates a duplicate item. If the
        item already exists, it is returned as-is (existing
        knowledge_type/feature_area are not overwritten by this call)."""
        item_id = slugify(key)
        existing = self.store.load_knowledge_item(item_id)
        if existing is not None:
            return KnowledgeItem.from_dict(existing)
        item = KnowledgeItem(
            id=item_id, key=key, knowledge_type=knowledge_type, feature_area=feature_area, states=[]
        )
        self.store.save_knowledge_item(item.to_dict())
        return item

    def get_knowledge_item(self, item_id: str) -> KnowledgeItem:
        data = self.store.load_knowledge_item(item_id)
        if data is None:
            raise UnknownKnowledgeItemError(f"no KnowledgeItem with id {item_id!r}")
        return KnowledgeItem.from_dict(data)

    def list_knowledge_items(
        self, feature_area: Optional[str] = None, knowledge_type: Optional[KnowledgeType] = None
    ) -> list:
        items = [self.get_knowledge_item(iid) for iid in self.store.list_knowledge_item_ids()]
        if feature_area is not None:
            items = [i for i in items if i.feature_area == feature_area]
        if knowledge_type is not None:
            items = [i for i in items if i.knowledge_type == knowledge_type]
        return items

    def _save_item(self, item: KnowledgeItem) -> None:
        self.store.save_knowledge_item(item.to_dict())

    def _find_state(self, item: KnowledgeItem, version: int) -> KnowledgeState:
        for state in item.states:
            if state.version == version:
                return state
        raise UnknownStateVersionError(
            f"KnowledgeItem {item.id!r} has no state with version {version}"
        )

    # --- KnowledgeState lifecycle ----------------------------------------

    def propose_state(
        self,
        item_id: str,
        content: str,
        evidence_ids: list,
        relation_to_previous: Relation = Relation.NEW,
        rationale: Optional[str] = None,
    ) -> KnowledgeState:
        """Propose a new versioned claim about a KnowledgeItem. Always
        lands at status=proposed - it does not become current knowledge
        by being proposed, no matter how strong its evidence looks."""
        item = self.get_knowledge_item(item_id)

        if not evidence_ids:
            raise MissingProvenanceError(
                "a KnowledgeState must reference at least one Evidence record"
            )
        for eid in evidence_ids:
            self.get_evidence(eid)  # raises UnknownEvidenceError if any reference is invalid

        state = KnowledgeState(
            version=len(item.states) + 1,
            content=content,
            status=StateStatus.PROPOSED,
            relation_to_previous=relation_to_previous,
            evidence_refs=list(evidence_ids),
            created_at=_now(),
            rationale=rationale,
        )
        item.states.append(state)
        self._save_item(item)
        return state

    def approve_state(self, item_id: str, version: int, approved_by: str) -> KnowledgeState:
        """The only way a state becomes current. If another state was
        already current for this item, it becomes superseded (never
        deleted) and points at the version that replaced it."""
        item = self.get_knowledge_item(item_id)
        state = self._find_state(item, version)

        if state.status != StateStatus.PROPOSED:
            raise InvalidLifecycleTransitionError(
                f"cannot approve state version {version} of {item_id!r}: "
                f"status is {state.status.value}, not proposed"
            )

        previous_current = next((s for s in item.states if s.status == StateStatus.CURRENT), None)
        if previous_current is not None:
            previous_current.status = StateStatus.SUPERSEDED
            previous_current.superseded_by = version

        state.status = StateStatus.CURRENT
        state.approved_by = approved_by
        state.approved_at = _now()
        self._save_item(item)
        return state

    def invalidate_state(
        self, item_id: str, version: int, invalidated_by: str, reason: Optional[str] = None
    ) -> KnowledgeState:
        """Mark a state as never having been trustworthy - distinct from
        supersession. Does not require a replacement to exist: after
        this call the item may have no current state at all, which is a
        valid outcome, not an error."""
        item = self.get_knowledge_item(item_id)
        state = self._find_state(item, version)

        if state.status == StateStatus.INVALIDATED:
            raise InvalidLifecycleTransitionError(
                f"state version {version} of {item_id!r} is already invalidated"
            )

        state.status = StateStatus.INVALIDATED
        state.invalidated_by = invalidated_by
        state.invalidated_at = _now()
        state.invalidation_reason = reason
        self._save_item(item)
        return state

    # --- Retrieval --------------------------------------------------------

    def get_current(self, item_id: str) -> Optional[KnowledgeState]:
        """The latest approved/verified knowledge for this item, or
        None if nothing has ever been approved. Never returns a raw
        evidence artifact, an unapproved proposal, an unresolved
        contradictory state, or a superseded/invalidated state."""
        item = self.get_knowledge_item(item_id)
        return next((s for s in item.states if s.status == StateStatus.CURRENT), None)

    def get_history(self, item_id: str) -> list:
        """Every state this item has ever had, oldest to newest,
        including superseded and invalidated ones with their lifecycle
        fields intact - enough to explain what was previously believed,
        when, from which evidence, and what replaced or invalidated it.
        Nothing is ever removed from this list."""
        item = self.get_knowledge_item(item_id)
        return list(item.states)

    def get_provenance(self, item_id: str, version: int) -> list:
        """The Evidence records backing one specific state."""
        item = self.get_knowledge_item(item_id)
        state = self._find_state(item, version)
        return [self.get_evidence(eid) for eid in state.evidence_refs]

    def get_pending(self, item_id: Optional[str] = None) -> list:
        """The review queue: every proposed state (including ones
        awaiting first approval and ones flagged as an unresolved
        contradiction), across one item or the whole store."""
        items = [self.get_knowledge_item(item_id)] if item_id is not None else self.list_knowledge_items()
        return [s for item in items for s in item.states if s.status == StateStatus.PROPOSED]

    def has_pending_conflict(self, item_id: str) -> bool:
        """True if this item currently has any unresolved contradiction
        - i.e. current retrieval or any related status query can expose
        'review/conflict currently exists' without fabricating a
        resolution."""
        return any(s.review_required for s in self.get_knowledge_item(item_id).states)

    def get_conflicts(self, item_id: Optional[str] = None) -> list:
        """The unresolved-contradiction subset of `get_pending`."""
        return [s for s in self.get_pending(item_id) if s.review_required]

    def get_evidence_type_summary(self, item_id: str, version: int) -> dict:
        """Source-diversity metadata for one state: a count per
        evidence_type among its cited evidence. No scoring, no ranking -
        just enough for a future reader to tell 'browser + maintainer +
        screenshot' apart from 'browser + browser + browser'."""
        summary: dict = {}
        for evidence in self.get_provenance(item_id, version):
            key = evidence.evidence_type.value
            summary[key] = summary.get(key, 0) + 1
        return summary
