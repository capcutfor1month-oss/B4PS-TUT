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
    CorruptEvidenceRecordError,
    CorruptProvenanceError,
    EditorialMemoryError,
    FeatureAreaMismatchError,
    InvalidLifecycleTransitionError,
    KeyCollisionError,
    KnowledgeTypeMismatchError,
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
from .store import JSONStore, is_tombstone_entry, slugify, validate_feature_area


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _next_version(states: list, tombstoned_versions: frozenset = frozenset()) -> int:
    """The next version to assign for a new KnowledgeState on this item:
    one higher than every version number that still means something for
    this item's history -

    - every currently-present state's own `version`,
    - every `superseded_by` value any surviving state still points at,
      even if the state that version originally belonged to was later
      removed by purge (EM47-03/finding 2), and
    - every version this item still has a retained purge tombstone for
      (round-3 finding 1) - a tombstoned state is no longer a real
      `KnowledgeState` (so it isn't in `states` here at all), but its
      identity must still never be handed to a new, unrelated state.

    Never just `len(states) + 1` (unsafe once purge can remove entries)
    and never just `max(s.version for s in states) + 1` alone (unsafe
    once a dangling `superseded_by` reference, or a retained tombstone,
    can refer to a version above the highest still-present real one)."""
    used = {s.version for s in states}
    used |= {s.superseded_by for s in states if s.superseded_by is not None}
    used |= set(tombstoned_versions)
    return max(used, default=0) + 1


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
        try:
            return Evidence.from_dict(data)
        except (KeyError, TypeError, ValueError) as exc:
            # EM47-05: valid JSON but not a valid Evidence record - most
            # commonly a Slice 7 purge tombstone stub loaded as if it
            # were still real Evidence. Must surface as a typed
            # Editorial Memory error, not a raw KeyError/TypeError, so
            # get_current's existing CorruptProvenanceError wrapping
            # (EM-01, which only catches EditorialMemoryError) still
            # catches this too.
            raise CorruptEvidenceRecordError(
                f"stored Evidence record {evidence_id!r} is not a valid Evidence "
                f"record (missing/invalid fields - e.g. a purge tombstone stub): {exc}"
            ) from exc

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
        """The single choke point every mutation path (`propose_state`,
        `approve_state`, `invalidate_state`) uses to persist a
        KnowledgeItem. `item.states` only ever holds real states -
        `get_knowledge_item`/`store.load_knowledge_item` filter purge
        tombstones out of it on the way in (see `store.py`) - so writing
        `item.to_dict()` back verbatim would silently drop any tombstone
        currently on disk for this item every time anything else about
        it is saved.

        Round-4 finding 2: a retained tombstone must stay in its exact
        original array position, and the relative order of surviving
        real states must not shift either - prepending tombstones (as an
        earlier round did) or appending them satisfies "not lost" but
        violates "same slot." The merge here instead walks the raw,
        on-disk array position by position: a tombstone entry is carried
        through unchanged at its own index; a real-state entry at a
        version this call already knew about is replaced in place with
        its updated dict (content/status/etc. may have changed);
        anything in `item.states` that wasn't in the raw record at all
        yet (a version `propose_state` just appended) is added at the
        end, in its own append order - exactly where a brand-new state
        belongs, and exactly what this method already did before any
        tombstone existed to preserve."""
        data = item.to_dict()
        existing_raw = self.store.load_knowledge_item_raw(item.id)
        if existing_raw is None:
            self.store.save_knowledge_item(data)
            return

        updated_by_version = {s["version"]: s for s in data["states"]}
        merged = []
        known_versions = set()
        for entry in existing_raw["states"]:
            if is_tombstone_entry(entry, item.id):
                merged.append(entry)
                continue
            known_versions.add(entry["version"])
            merged.append(updated_by_version.get(entry["version"], entry))
        for state_dict in data["states"]:
            if state_dict["version"] not in known_versions:
                merged.append(state_dict)

        data["states"] = merged
        self.store.save_knowledge_item(data)

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
            # Derived from every version number that still means
            # something for this item's history: currently-present
            # states' own versions, any surviving state's `superseded_by`
            # reference to a purged-away version, and any version this
            # item still has a retained purge tombstone for (round-3
            # finding 1 - tombstoned versions live in the raw record, not
            # in the parsed `item.states` this method otherwise works
            # from, so they're read separately here). See `_next_version`
            # for the full reasoning.
            version=_next_version(item.states, self.store.tombstoned_versions(item_id)),
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
        idempotent repeat of an existing one. Its stored `knowledge_type`
        must likewise already be `editorial` (finding 4): a mismatch
        raises typed `KnowledgeTypeMismatchError`, for the same reason -
        product, documentation, and editorial knowledge must never blend
        under one KnowledgeItem just because a natural key collides.

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
            if existing_data["knowledge_type"] != KnowledgeType.EDITORIAL.value:
                raise KnowledgeTypeMismatchError(
                    f"KnowledgeItem {item_id!r} (key {key!r}) already exists "
                    f"with knowledge_type {existing_data['knowledge_type']!r}; "
                    f"refusing to record a maintainer decision (knowledge_type="
                    f"{KnowledgeType.EDITORIAL.value!r}) for it"
                )
            existing_item = KnowledgeItem.from_dict(existing_data)

        relation_was_omitted = relation_to_previous is None
        relation = relation_to_previous
        if relation is None:
            relation = Relation.NEW if existing_item is None or not existing_item.states else Relation.REFINES

        if existing_item is not None:
            duplicate = self._find_matching_evidence_backed_state(
                existing_item, EvidenceType.MAINTAINER_DECISION, content, source_ref, captured_by,
                captured_at, notes, verification_scope, rationale, relation,
                relation_was_omitted=relation_was_omitted,
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

    def _find_matching_evidence_backed_state(
        self,
        item: KnowledgeItem,
        evidence_type: EvidenceType,
        content: str,
        source_ref: str,
        captured_by: str,
        captured_at: Optional[str],
        notes: Optional[str],
        verification_scope: Optional[list],
        rationale: Optional[str],
        relation_to_previous: Relation,
        relation_was_omitted: bool = False,
    ) -> Optional[KnowledgeState]:
        """Exact-repeat detection shared by every single-evidence bootstrap
        path (Slice 2's maintainer decisions, Slice 4's documentation
        ingestion): a state counts as the same submission if its content/
        rationale/relation_to_previous match and every field of the
        Evidence it cites matches - including `evidence_type`, so a
        maintainer decision and a documentation ingestion never dedupe
        against each other even with identical text - checked against
        records already on disk, not a separate dedup index.

        `relation_was_omitted` (EM47-01, revised by finding 1): when the
        caller left `relation_to_previous` unspecified, its default
        (`NEW` for a brand-new item, `REFINES` for a later one) is
        derived from `item.states` *at call time*. Duplicate detection
        must use each candidate's *own stable, persisted identity*, not
        its transient position in `item.states` - an `enumerate()` index
        shifts whenever an earlier state is fully removed by a Slice 7
        purge, so "was this candidate at array index 0" stops meaning
        "was this candidate the item's actual first-ever state" the
        moment anything before it is purged away. `version` is never
        renumbered for a surviving state (EM47-03/finding 2 also
        guarantees a version number, once assigned, is never reassigned
        to a different logical state), so `version == 1` - the version
        every item's true first state is always given - is used instead:
        a stable identity check that survives purges of *other* states,
        including an earlier one. (If the item's own true first state was
        itself purged away, nothing carries `version == 1` anymore, so a
        repeat of exactly that original claim is correctly treated as
        fresh - there is genuinely nothing left to compare it against,
        matching purge's own "no trace" semantics.) An explicitly-
        supplied relation (S2-02) is unaffected: it must still match
        exactly, as before.

        Evidence lookups (finding 3) go through the typed `get_evidence`
        - not a raw `store.load_evidence` + `Evidence.from_dict` call -
        so a tombstoned or otherwise corrupt Evidence record raises
        `EditorialMemoryError` here, never an unguarded `KeyError`. A
        missing or corrupt reference simply can't corroborate a match and
        is skipped, exactly as a missing one already was: one candidate
        state's damaged provenance must not block an unrelated dedup
        check (or, worse, crash the whole ingestion call) for this item."""
        norm_scope = list(verification_scope) if verification_scope else None
        for state in item.states:
            expected_relation = relation_to_previous
            if relation_was_omitted:
                expected_relation = Relation.NEW if state.version == 1 else Relation.REFINES
            if (
                state.content != content
                or state.rationale != rationale
                or state.relation_to_previous != expected_relation
            ):
                continue
            for eid in state.evidence_refs:
                try:
                    evidence = self.get_evidence(eid)
                except EditorialMemoryError:
                    continue
                if (
                    evidence.evidence_type == evidence_type
                    and evidence.source_ref == source_ref
                    and evidence.captured_by == captured_by
                    and evidence.captured_at == captured_at
                    and evidence.notes == notes
                    and evidence.verification_scope == norm_scope
                ):
                    return state
        return None

    # --- Existing-documentation ingestion (Slice 4) ------------------------

    def ingest_existing_documentation(
        self,
        key: str,
        feature_area: str,
        content: str,
        source_ref: str,
        captured_by: str,
        captured_at: Optional[str] = None,
        notes: Optional[str] = None,
        verification_scope: Optional[list] = None,
        rationale: Optional[str] = None,
        relation_to_previous: Optional[Relation] = None,
    ) -> KnowledgeState:
        """Ingest a claim already extracted from existing documentation
        (a deck, a tutorial script, a repo doc - the caller has already
        done any parsing; this method takes the resulting short claim,
        not raw source content) as Evidence plus a proposed
        `documentation`-type KnowledgeState.

        Unlike `record_maintainer_decision`, this NEVER auto-approves:
        existing documentation describes what was *written*, not
        necessarily what's true today (per the approved evidence
        hierarchy - documentation is historical, not self-approving), so
        this is `propose_state()` alone, with no `approve_state()` call.
        The resulting state always lands `proposed`, no matter how
        authoritative the source looks; only an explicit, separate
        `approve_state()` call - the same one every other proposal
        lifecycle path uses - can ever promote it to `current`.

        The existing item's stored `feature_area` must match the
        requested one exactly, mirroring S2-01's protection: a mismatch
        is rejected with typed `FeatureAreaMismatchError` before any
        Evidence or KnowledgeState is created, never silently accepted
        or treated as an idempotent repeat. Its stored `knowledge_type`
        must likewise already be `documentation` (finding 4): a mismatch
        raises typed `KnowledgeTypeMismatchError`, for the same reason -
        product, documentation, and editorial knowledge must never blend
        under one KnowledgeItem just because a natural key collides.

        Idempotent on exact-repeat input, reusing the same evidence-
        backed-state comparison Slice 2 uses (scoped to this call's own
        `evidence_type=existing_documentation`, so it never dedupes
        against a maintainer decision with identical text): resubmitting
        identical content/rationale/relation_to_previous backed by
        identical Evidence fields returns the existing proposed state
        as-is rather than creating a duplicate. A materially different
        resubmission (any field differing, including an explicitly
        different `relation_to_previous`) creates a new proposed state
        through the ordinary Slice 1 lifecycle instead."""
        validate_feature_area(feature_area)

        item_id = slugify(key)
        existing_data = self.store.load_knowledge_item(item_id)
        existing_item = None
        if existing_data is not None and existing_data["key"] == key:
            if existing_data["feature_area"] != feature_area:
                raise FeatureAreaMismatchError(
                    f"KnowledgeItem {item_id!r} (key {key!r}) already exists "
                    f"with feature_area {existing_data['feature_area']!r}; "
                    f"refusing to ingest documentation for it under "
                    f"a different feature_area {feature_area!r}"
                )
            if existing_data["knowledge_type"] != KnowledgeType.DOCUMENTATION.value:
                raise KnowledgeTypeMismatchError(
                    f"KnowledgeItem {item_id!r} (key {key!r}) already exists "
                    f"with knowledge_type {existing_data['knowledge_type']!r}; "
                    f"refusing to ingest documentation (knowledge_type="
                    f"{KnowledgeType.DOCUMENTATION.value!r}) for it"
                )
            existing_item = KnowledgeItem.from_dict(existing_data)

        relation_was_omitted = relation_to_previous is None
        relation = relation_to_previous
        if relation is None:
            relation = Relation.NEW if existing_item is None or not existing_item.states else Relation.REFINES

        if existing_item is not None:
            duplicate = self._find_matching_evidence_backed_state(
                existing_item, EvidenceType.EXISTING_DOCUMENTATION, content, source_ref, captured_by,
                captured_at, notes, verification_scope, rationale, relation,
                relation_was_omitted=relation_was_omitted,
            )
            if duplicate is not None:
                return duplicate

        item = self.get_or_create_knowledge_item(key, KnowledgeType.DOCUMENTATION, feature_area)

        evidence = self.record_evidence(
            evidence_type=EvidenceType.EXISTING_DOCUMENTATION,
            source_ref=source_ref,
            captured_by=captured_by,
            captured_at=captured_at,
            notes=notes,
            verification_scope=verification_scope,
        )

        return self.propose_state(
            item.id,
            content=content,
            evidence_ids=[evidence.id],
            relation_to_previous=relation,
            rationale=rationale,
        )

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
