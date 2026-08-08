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
    CorruptProvenanceError,
    EditorialMemoryError,
    FeatureAreaMismatchError,
    InvalidLifecycleTransitionError,
    KeyCollisionError,
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
from .store import JSONStore, slugify, validate_feature_area


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
        knowledge_type/feature_area are not overwritten by this call).

        `slugify` is lossy (e.g. "a.b" and "a-b" both normalize to
        "a-b"). If an item already exists at this slug under a
        *different* natural key, that is a slug collision between two
        distinct subjects, not the same subject being re-found - raise
        rather than silently merging their identity and history (EM-02)."""
        item_id = slugify(key)
        existing = self.store.load_knowledge_item(item_id)
        if existing is not None:
            if existing["key"] != key:
                raise KeyCollisionError(
                    f"key {key!r} collides with existing key {existing['key']!r} "
                    f"(both normalize to id {item_id!r}); refusing to merge them "
                    "into one KnowledgeItem"
                )
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
        contradictory state, or a superseded/invalidated state.

        Also never returns a state whose cited Evidence is missing or
        corrupt (EM-01): a current state's provenance is re-checked on
        every call, and a broken reference raises typed
        `CorruptProvenanceError` rather than handing back a "current"
        claim nobody can actually verify."""
        item = self.get_knowledge_item(item_id)
        current = next((s for s in item.states if s.status == StateStatus.CURRENT), None)
        if current is None:
            return None
        for eid in current.evidence_refs:
            try:
                self.get_evidence(eid)
            except EditorialMemoryError as exc:
                raise CorruptProvenanceError(
                    f"current state version {current.version} of {item_id!r} cites "
                    f"evidence {eid!r}, which is missing or corrupt"
                ) from exc
        return current

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

    # --- Maintainer-decision bootstrap (Slice 2) --------------------------

    def record_maintainer_decision(
        self,
        key: str,
        feature_area: str,
        content: str,
        source_ref: str,
        captured_by: str,
        approved_by: Optional[str] = None,
        captured_at: Optional[str] = None,
        notes: Optional[str] = None,
        verification_scope: Optional[list] = None,
        rationale: Optional[str] = None,
        relation_to_previous: Optional[Relation] = None,
    ) -> KnowledgeState:
        """Bootstrap path for an already-approved maintainer editorial
        decision. This is the only evidence type with this privilege: a
        maintainer has already supplied their approved reasoning, so this
        performs propose_state + approve_state as one explicit workflow -
        reusing both unchanged (never writing status=current directly,
        never adding a second approval mechanism).

        The existing item's stored `feature_area` must match the
        requested one exactly (S2-01): a mismatch is rejected with typed
        `FeatureAreaMismatchError` *before* any duplicate-detection or
        mutation happens, so a mismatched request never creates Evidence,
        never creates a KnowledgeState, and is never treated as an
        idempotent repeat of an existing one.

        Idempotent on exact-repeat input: if a state already exists on
        this KnowledgeItem with identical content/rationale/relation_to_
        previous, backed by Evidence with identical source_ref/
        captured_by/captured_at/notes/verification_scope, that existing
        state is returned as-is rather than creating duplicate Evidence/
        KnowledgeItem/KnowledgeState records (no new persisted field is
        needed for this - the comparison is against records already
        stored). `relation_to_previous` is part of that identity (S2-02):
        the same fields resubmitted with an explicitly different relation
        (e.g. NEW vs. CONTRADICTS) are NOT an idempotent repeat and create
        a new KnowledgeState through the ordinary Slice 1 lifecycle - as
        does any other materially different decision (any field
        differing) for the same KnowledgeItem."""
        validate_feature_area(feature_area)
        approved_by = approved_by or captured_by

        item_id = slugify(key)
        existing_data = self.store.load_knowledge_item(item_id)
        existing_item = None
        if existing_data is not None and existing_data["key"] == key:
            if existing_data["feature_area"] != feature_area:
                raise FeatureAreaMismatchError(
                    f"KnowledgeItem {item_id!r} (key {key!r}) already exists "
                    f"with feature_area {existing_data['feature_area']!r}; "
                    f"refusing to record a maintainer decision for it under "
                    f"a different feature_area {feature_area!r}"
                )
            existing_item = KnowledgeItem.from_dict(existing_data)

        relation = relation_to_previous
        if relation is None:
            relation = Relation.NEW if existing_item is None or not existing_item.states else Relation.REFINES

        if existing_item is not None:
            duplicate = self._find_matching_maintainer_state(
                existing_item, content, source_ref, captured_by,
                captured_at, notes, verification_scope, rationale, relation,
            )
            if duplicate is not None:
                return duplicate

        item = self.get_or_create_knowledge_item(key, KnowledgeType.EDITORIAL, feature_area)

        evidence = self.record_evidence(
            evidence_type=EvidenceType.MAINTAINER_DECISION,
            source_ref=source_ref,
            captured_by=captured_by,
            captured_at=captured_at,
            notes=notes,
            verification_scope=verification_scope,
        )

        proposed = self.propose_state(
            item.id,
            content=content,
            evidence_ids=[evidence.id],
            relation_to_previous=relation,
            rationale=rationale,
        )
        return self.approve_state(item.id, version=proposed.version, approved_by=approved_by)

    def _find_matching_maintainer_state(
        self,
        item: KnowledgeItem,
        content: str,
        source_ref: str,
        captured_by: str,
        captured_at: Optional[str],
        notes: Optional[str],
        verification_scope: Optional[list],
        rationale: Optional[str],
        relation_to_previous: Relation,
    ) -> Optional[KnowledgeState]:
        """Exact-repeat detection for the bootstrap path: a state counts
        as the same maintainer decision if its content/rationale/
        relation_to_previous match and every field of the Evidence it
        cites matches, checked against records already on disk - not a
        separate dedup index."""
        norm_scope = list(verification_scope) if verification_scope else None
        for state in item.states:
            if (
                state.content != content
                or state.rationale != rationale
                or state.relation_to_previous != relation_to_previous
            ):
                continue
            for eid in state.evidence_refs:
                data = self.store.load_evidence(eid)
                if data is None:
                    continue
                evidence = Evidence.from_dict(data)
                if (
                    evidence.evidence_type == EvidenceType.MAINTAINER_DECISION
                    and evidence.source_ref == source_ref
                    and evidence.captured_by == captured_by
                    and evidence.captured_at == captured_at
                    and evidence.notes == notes
                    and evidence.verification_scope == norm_scope
                ):
                    return state
        return None

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
