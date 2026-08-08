"""Lifecycle proof tests for Editorial Memory Slice 1.

Examples reference plausible Bridge4PS-shaped scenarios (a workflow
button's behavior, a permission rule) for readability. These are
illustrative test fixtures, not claims about real Bridge4PS product
behavior.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from lib import (
    CorruptProvenanceError,
    EditorialMemory,
    EditorialMemoryError,
    EvidenceQuality,
    EvidenceType,
    FeatureAreaMismatchError,
    InvalidEvidenceIdError,
    InvalidFeatureAreaError,
    InvalidLifecycleTransitionError,
    KeyCollisionError,
    KnowledgeType,
    MissingProvenanceError,
    Relation,
    StateStatus,
    StorageCorruptionError,
    UnknownEvidenceError,
    UnknownKnowledgeItemError,
    UnknownStateVersionError,
)
from lib.store import slugify


@pytest.fixture
def memory(tmp_path):
    return EditorialMemory(tmp_path / "store")


def _record_screenshot(memory, notes="button says Filters"):
    return memory.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT,
        source_ref="Source/Desktop/Screenshots/filters_button.png",
        captured_by="maintainer",
        notes=notes,
        evidence_quality=EvidenceQuality.MEDIUM,
    )


def _record_browser_observation(memory, notes="clicked Filters, sidebar opened"):
    return memory.record_evidence(
        evidence_type=EvidenceType.BROWSER_OBSERVATION,
        source_ref="https://app.bridge4ps.example/workspace/filters",
        captured_by="maintainer",
        notes=notes,
        evidence_quality=EvidenceQuality.HIGH,
    )


# --------------------------------------------------------------------------
# Evidence isolation
# --------------------------------------------------------------------------

def test_evidence_is_retrievable_but_not_current_knowledge(memory):
    evidence = _record_screenshot(memory)
    fetched = memory.get_evidence(evidence.id)
    assert fetched.id == evidence.id
    assert fetched.source_ref == evidence.source_ref

    # Recording evidence alone must not create or affect any KnowledgeItem.
    assert memory.list_knowledge_items() == []


def test_unknown_evidence_id_raises_typed_error(memory):
    with pytest.raises(UnknownEvidenceError):
        memory.get_evidence("ev-does-not-exist")


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------

def test_knowledge_state_without_evidence_is_rejected(memory):
    item = memory.get_or_create_knowledge_item(
        "desktop.filters.button-label", KnowledgeType.PRODUCT, "desktop.filters"
    )
    with pytest.raises(MissingProvenanceError):
        memory.propose_state(item.id, content="Filters opens a sidebar.", evidence_ids=[])


def test_knowledge_state_with_valid_evidence_succeeds(memory):
    item = memory.get_or_create_knowledge_item(
        "desktop.filters.button-label", KnowledgeType.PRODUCT, "desktop.filters"
    )
    evidence = _record_screenshot(memory)
    state = memory.propose_state(item.id, content="Filters opens a sidebar.", evidence_ids=[evidence.id])
    assert state.status == StateStatus.PROPOSED
    assert state.evidence_refs == [evidence.id]


def test_knowledge_state_with_unknown_evidence_is_rejected(memory):
    item = memory.get_or_create_knowledge_item(
        "desktop.filters.button-label", KnowledgeType.PRODUCT, "desktop.filters"
    )
    with pytest.raises(UnknownEvidenceError):
        memory.propose_state(item.id, content="x", evidence_ids=["ev-nonexistent"])


def test_provenance_remains_queryable_historically(memory):
    item = memory.get_or_create_knowledge_item(
        "desktop.filters.button-label", KnowledgeType.PRODUCT, "desktop.filters"
    )
    e1 = _record_screenshot(memory)
    state = memory.propose_state(item.id, content="Filters opens a sidebar.", evidence_ids=[e1.id])
    memory.approve_state(item.id, state.version, approved_by="maintainer")

    provenance = memory.get_provenance(item.id, state.version)
    assert [e.id for e in provenance] == [e1.id]


# --------------------------------------------------------------------------
# Approval
# --------------------------------------------------------------------------

def test_proposed_state_does_not_become_current(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    evidence = _record_screenshot(memory)
    memory.propose_state(item.id, content="claim", evidence_ids=[evidence.id])
    assert memory.get_current(item.id) is None


def test_approved_state_becomes_current(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    evidence = _record_screenshot(memory)
    state = memory.propose_state(item.id, content="claim", evidence_ids=[evidence.id])
    memory.approve_state(item.id, state.version, approved_by="maintainer")
    current = memory.get_current(item.id)
    assert current is not None
    assert current.version == state.version
    assert current.status == StateStatus.CURRENT
    assert current.approved_by == "maintainer"


def test_cannot_approve_an_already_current_state_again(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    evidence = _record_screenshot(memory)
    state = memory.propose_state(item.id, content="claim", evidence_ids=[evidence.id])
    memory.approve_state(item.id, state.version, approved_by="maintainer")
    with pytest.raises(InvalidLifecycleTransitionError):
        memory.approve_state(item.id, state.version, approved_by="maintainer")


# --------------------------------------------------------------------------
# Supersession
# --------------------------------------------------------------------------

def test_supersession_preserves_history_and_traceability(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    e1 = _record_screenshot(memory, notes="popover")
    s1 = memory.propose_state(item.id, content="Filters opens a popover.", evidence_ids=[e1.id])
    memory.approve_state(item.id, s1.version, approved_by="maintainer")

    # S2 proposed - must not replace S1 while still proposed.
    e2 = _record_browser_observation(memory, notes="now a sidebar")
    s2 = memory.propose_state(
        item.id, content="Filters opens a sidebar.", evidence_ids=[e2.id],
        relation_to_previous=Relation.SUPERSEDES,
    )
    assert memory.get_current(item.id).version == s1.version

    memory.approve_state(item.id, s2.version, approved_by="maintainer")

    current = memory.get_current(item.id)
    assert current.version == s2.version

    history = memory.get_history(item.id)
    assert [s.version for s in history] == [1, 2]
    old = next(s for s in history if s.version == 1)
    assert old.status == StateStatus.SUPERSEDED
    assert old.superseded_by == 2


# --------------------------------------------------------------------------
# Invalidation vs. supersession
# --------------------------------------------------------------------------

def test_invalidated_state_is_not_returned_as_current_but_history_is_preserved(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.EDITORIAL, "desktop.filters")
    evidence = memory.record_evidence(
        evidence_type=EvidenceType.MAINTAINER_DECISION, source_ref="chat-log-123",
        captured_by="founder",
    )
    state = memory.propose_state(item.id, content="hallucinated claim", evidence_ids=[evidence.id])
    memory.approve_state(item.id, state.version, approved_by="maintainer")
    assert memory.get_current(item.id) is not None

    memory.invalidate_state(item.id, state.version, invalidated_by="maintainer", reason="AI hallucination, never true")

    assert memory.get_current(item.id) is None  # not returned as current
    history = memory.get_history(item.id)
    assert len(history) == 1  # history remains preserved
    assert history[0].status == StateStatus.INVALIDATED
    assert history[0].invalidation_reason == "AI hallucination, never true"


def test_invalidation_is_distinct_from_supersession(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    e1 = _record_screenshot(memory)
    s1 = memory.propose_state(item.id, content="claim", evidence_ids=[e1.id])
    memory.approve_state(item.id, s1.version, approved_by="maintainer")
    memory.invalidate_state(item.id, s1.version, invalidated_by="maintainer", reason="bad ingestion")

    invalidated = memory.get_history(item.id)[0]
    assert invalidated.status == StateStatus.INVALIDATED
    assert invalidated.superseded_by is None  # never had a replacement - that's the point


def test_cannot_invalidate_twice(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    evidence = _record_screenshot(memory)
    state = memory.propose_state(item.id, content="claim", evidence_ids=[evidence.id])
    memory.approve_state(item.id, state.version, approved_by="maintainer")
    memory.invalidate_state(item.id, state.version, invalidated_by="maintainer", reason="r1")
    with pytest.raises(InvalidLifecycleTransitionError):
        memory.invalidate_state(item.id, state.version, invalidated_by="maintainer", reason="r2")


# --------------------------------------------------------------------------
# Contradiction / review-required
# --------------------------------------------------------------------------

def test_contradicting_evidence_is_recorded_and_review_becomes_visible_without_overwriting_current(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    e1 = _record_screenshot(memory)
    s1 = memory.propose_state(item.id, content="Filters opens a sidebar.", evidence_ids=[e1.id])
    memory.approve_state(item.id, s1.version, approved_by="maintainer")

    assert memory.has_pending_conflict(item.id) is False

    # Contradicting, unresolved evidence arrives.
    e_contradicting = _record_browser_observation(memory, notes="Filters opened a modal instead")
    s_conflict = memory.propose_state(
        item.id, content="Filters opens a modal.", evidence_ids=[e_contradicting.id],
        relation_to_previous=Relation.CONTRADICTS,
    )

    # Preserved, visible, but must not silently overwrite current.
    assert s_conflict.review_required is True
    assert memory.has_pending_conflict(item.id) is True
    assert memory.get_current(item.id).version == s1.version
    conflicts = memory.get_conflicts(item.id)
    assert [c.version for c in conflicts] == [s_conflict.version]

    # Resolving the conflict via approval clears the review flag and
    # moves current forward, exactly like any other supersession.
    memory.approve_state(item.id, s_conflict.version, approved_by="maintainer")
    assert memory.has_pending_conflict(item.id) is False
    assert memory.get_current(item.id).version == s_conflict.version


# --------------------------------------------------------------------------
# Evidence quality
# --------------------------------------------------------------------------

def test_evidence_quality_persists_and_is_not_a_truth_score(memory):
    evidence = memory.record_evidence(
        evidence_type=EvidenceType.RECORDING, source_ref="Source/rec.mp4",
        captured_by="maintainer", evidence_quality=EvidenceQuality.LOW,
    )
    fetched = memory.get_evidence(evidence.id)
    assert fetched.evidence_quality == EvidenceQuality.LOW
    # It is metadata about the artifact only - nothing in the model
    # converts it into a numeric confidence score anywhere; there is no
    # such field to find on Evidence, KnowledgeState, or the retrieval
    # results, by construction.
    assert not hasattr(fetched, "confidence_score")
    assert not hasattr(fetched, "score")


# --------------------------------------------------------------------------
# Source diversity (no scoring)
# --------------------------------------------------------------------------

def test_source_diversity_metadata_is_preserved_without_scoring(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    e_browser = _record_browser_observation(memory)
    e_maintainer = memory.record_evidence(
        evidence_type=EvidenceType.MAINTAINER_DECISION, source_ref="review-note",
        captured_by="maintainer",
    )
    e_screenshot = _record_screenshot(memory)
    state = memory.propose_state(
        item.id, content="claim", evidence_ids=[e_browser.id, e_maintainer.id, e_screenshot.id]
    )
    memory.approve_state(item.id, state.version, approved_by="maintainer")

    diverse_summary = memory.get_evidence_type_summary(item.id, state.version)
    assert diverse_summary == {"browser_observation": 1, "maintainer_decision": 1, "screenshot": 1}

    # Contrast: three of the same category is distinguishable from three diverse ones.
    item2 = memory.get_or_create_knowledge_item("k2", KnowledgeType.PRODUCT, "desktop.filters")
    b1 = _record_browser_observation(memory, notes="a")
    b2 = _record_browser_observation(memory, notes="b")
    b3 = _record_browser_observation(memory, notes="c")
    state2 = memory.propose_state(item2.id, content="claim2", evidence_ids=[b1.id, b2.id, b3.id])
    memory.approve_state(item2.id, state2.version, approved_by="maintainer")
    homogeneous_summary = memory.get_evidence_type_summary(item2.id, state2.version)
    assert homogeneous_summary == {"browser_observation": 3}
    assert diverse_summary != homogeneous_summary


# --------------------------------------------------------------------------
# Current retrieval - newest does not automatically win
# --------------------------------------------------------------------------

def test_current_retrieval_ignores_newer_unapproved_state(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    e1 = _record_screenshot(memory)
    s1 = memory.propose_state(item.id, content="claim v1", evidence_ids=[e1.id])
    memory.approve_state(item.id, s1.version, approved_by="maintainer")

    e2 = _record_browser_observation(memory)
    memory.propose_state(item.id, content="claim v2 - newer but unapproved", evidence_ids=[e2.id])

    current = memory.get_current(item.id)
    assert current.version == s1.version
    assert current.content == "claim v1"


def test_current_retrieval_never_returns_raw_evidence(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    evidence = _record_screenshot(memory)
    # No KnowledgeState has ever been proposed or approved for this item.
    assert memory.get_current(item.id) is None


# --------------------------------------------------------------------------
# History
# --------------------------------------------------------------------------

def test_history_returns_all_states_in_correct_sequence(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    e1 = _record_screenshot(memory)
    s1 = memory.propose_state(item.id, content="v1", evidence_ids=[e1.id])
    memory.approve_state(item.id, s1.version, approved_by="maintainer")
    e2 = _record_browser_observation(memory)
    s2 = memory.propose_state(item.id, content="v2", evidence_ids=[e2.id], relation_to_previous=Relation.SUPERSEDES)
    memory.approve_state(item.id, s2.version, approved_by="maintainer")

    history = memory.get_history(item.id)
    assert [s.version for s in history] == [1, 2]
    assert [s.status for s in history] == [StateStatus.SUPERSEDED, StateStatus.CURRENT]


# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------

def test_deterministic_ordering_across_repeated_reads(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    for i in range(5):
        evidence = _record_screenshot(memory, notes=f"note {i}")
        memory.propose_state(item.id, content=f"claim {i}", evidence_ids=[evidence.id])

    first_read = [s.version for s in memory.get_history(item.id)]
    second_read = [s.version for s in memory.get_history(item.id)]
    assert first_read == second_read == [1, 2, 3, 4, 5]


# --------------------------------------------------------------------------
# Persistence (reload from storage)
# --------------------------------------------------------------------------

def test_reload_from_storage_preserves_current_history_and_provenance(tmp_path):
    root = tmp_path / "store"
    memory = EditorialMemory(root)
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    e1 = _record_screenshot(memory)
    s1 = memory.propose_state(item.id, content="v1", evidence_ids=[e1.id])
    memory.approve_state(item.id, s1.version, approved_by="maintainer")
    e2 = _record_browser_observation(memory)
    s2 = memory.propose_state(item.id, content="v2", evidence_ids=[e2.id], relation_to_previous=Relation.SUPERSEDES)
    memory.approve_state(item.id, s2.version, approved_by="maintainer")

    # A fresh EditorialMemory instance pointed at the same root - simulates
    # a new process reloading from disk.
    reloaded = EditorialMemory(root)
    current = reloaded.get_current(item.id)
    assert current is not None
    assert current.version == 2
    assert current.content == "v2"

    history = reloaded.get_history(item.id)
    assert [s.version for s in history] == [1, 2]

    provenance = reloaded.get_provenance(item.id, 2)
    assert [e.id for e in provenance] == [e2.id]


# --------------------------------------------------------------------------
# Invalid references
# --------------------------------------------------------------------------

def test_unknown_knowledge_item_reference_is_rejected(memory):
    with pytest.raises(UnknownKnowledgeItemError):
        memory.get_knowledge_item("does-not-exist")
    evidence = _record_screenshot(memory)
    with pytest.raises(UnknownKnowledgeItemError):
        memory.propose_state("does-not-exist", content="x", evidence_ids=[evidence.id])


def test_unknown_state_version_is_rejected(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    with pytest.raises(UnknownStateVersionError):
        memory.approve_state(item.id, version=99, approved_by="maintainer")


def test_get_or_create_is_idempotent_on_key(memory):
    a = memory.get_or_create_knowledge_item("desktop.filters.button-label", KnowledgeType.PRODUCT, "desktop.filters")
    b = memory.get_or_create_knowledge_item("desktop.filters.button-label", KnowledgeType.PRODUCT, "desktop.filters")
    assert a.id == b.id
    assert len(memory.list_knowledge_items()) == 1


# --------------------------------------------------------------------------
# Rationale
# --------------------------------------------------------------------------

def test_rationale_is_optional_and_preserved_when_supplied(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.EDITORIAL, "desktop.filters")
    evidence = memory.record_evidence(
        evidence_type=EvidenceType.MAINTAINER_DECISION, source_ref="chat-log", captured_by="founder",
    )
    with_rationale = memory.propose_state(
        item.id, content="Keep the warning box on slide 12.", evidence_ids=[evidence.id],
        rationale="Learners repeatedly missed the required click without it.",
    )
    assert with_rationale.rationale == "Learners repeatedly missed the required click without it."

    item2 = memory.get_or_create_knowledge_item("k2", KnowledgeType.PRODUCT, "desktop.filters")
    without_rationale = memory.propose_state(item2.id, content="claim", evidence_ids=[evidence.id])
    assert without_rationale.rationale is None


# --------------------------------------------------------------------------
# Full end-to-end lifecycle scenario (the core Slice 1 proof)
# --------------------------------------------------------------------------

def test_slice_1_end_to_end_lifecycle_scenario(memory):
    """Evidence -> KnowledgeItem -> KnowledgeState -> approval ->
    supersession -> unresolved conflict, in one deterministic run,
    matching the Slice 1 contract step by step."""

    # 1. Evidence E1: initial verified observation.
    e1 = memory.record_evidence(
        evidence_type=EvidenceType.BROWSER_OBSERVATION,
        source_ref="https://app.bridge4ps.example/workspace/filters",
        captured_by="maintainer",
        notes="Filters button opens a popover.",
        evidence_quality=EvidenceQuality.HIGH,
    )

    # 2. KnowledgeItem K created.
    k = memory.get_or_create_knowledge_item(
        "desktop.filters.open-behavior", KnowledgeType.PRODUCT, "desktop.filters"
    )

    # 3. KnowledgeState S1 references E1.
    s1 = memory.propose_state(k.id, content="Filters opens a popover.", evidence_ids=[e1.id])
    assert s1.status == StateStatus.PROPOSED

    # 4. S1 approved.
    memory.approve_state(k.id, s1.version, approved_by="maintainer")

    # 5. Current retrieval returns S1.
    assert memory.get_current(k.id).version == s1.version
    assert memory.get_current(k.id).content == "Filters opens a popover."

    # 6. Evidence E2 arrives with changed behavior.
    e2 = memory.record_evidence(
        evidence_type=EvidenceType.BROWSER_OBSERVATION,
        source_ref="https://app.bridge4ps.example/workspace/filters",
        captured_by="maintainer",
        notes="Filters button now opens a sidebar, not a popover.",
        evidence_quality=EvidenceQuality.HIGH,
    )

    # 7. S2 references E2 but remains unapproved.
    s2 = memory.propose_state(
        k.id, content="Filters opens a sidebar.", evidence_ids=[e2.id],
        relation_to_previous=Relation.SUPERSEDES,
    )
    assert s2.status == StateStatus.PROPOSED

    # 8. Current retrieval still returns S1.
    assert memory.get_current(k.id).version == s1.version

    # 9. S2 is approved and supersedes S1.
    memory.approve_state(k.id, s2.version, approved_by="maintainer")

    # 10. Current retrieval returns S2.
    current = memory.get_current(k.id)
    assert current.version == s2.version
    assert current.content == "Filters opens a sidebar."

    # 11. History returns S1 and S2.
    history = memory.get_history(k.id)
    assert [s.version for s in history] == [1, 2]
    assert history[0].status == StateStatus.SUPERSEDED
    assert history[0].superseded_by == 2
    assert history[1].status == StateStatus.CURRENT

    # 12. Provenance shows E1 and E2 correctly.
    assert [e.id for e in memory.get_provenance(k.id, 1)] == [e1.id]
    assert [e.id for e in memory.get_provenance(k.id, 2)] == [e2.id]

    # 13. Evidence E3 contradicts S2 but is unresolved.
    e3 = memory.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT,
        source_ref="Source/Desktop/Screenshots/filters_modal.png",
        captured_by="maintainer",
        notes="Screenshot appears to show a modal, not a sidebar.",
        evidence_quality=EvidenceQuality.MEDIUM,
    )
    s3 = memory.propose_state(
        k.id, content="Filters opens a modal.", evidence_ids=[e3.id],
        relation_to_previous=Relation.CONTRADICTS,
    )

    # 14. Conflict/review-required becomes visible.
    assert s3.review_required is True
    assert memory.has_pending_conflict(k.id) is True
    assert [c.version for c in memory.get_conflicts(k.id)] == [s3.version]

    # 15. S2 remains current until an approved resolution exists.
    assert memory.get_current(k.id).version == s2.version
    assert memory.get_current(k.id).content == "Filters opens a sidebar."


# --------------------------------------------------------------------------
# EM-01: get_current() must not return a state with missing/corrupt provenance
# --------------------------------------------------------------------------

def test_em01_get_current_rejects_current_state_with_deleted_evidence(memory, tmp_path):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    evidence = _record_screenshot(memory)
    state = memory.propose_state(item.id, content="claim", evidence_ids=[evidence.id])
    memory.approve_state(item.id, state.version, approved_by="maintainer")
    assert memory.get_current(item.id) is not None  # sanity: works before corruption

    # Simulate the evidence artifact being lost after the fact.
    (memory.store.evidence_dir / f"{evidence.id}.json").unlink()

    with pytest.raises(CorruptProvenanceError):
        memory.get_current(item.id)


def test_em01_get_current_rejects_current_state_with_corrupt_evidence_file(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    evidence = _record_screenshot(memory)
    state = memory.propose_state(item.id, content="claim", evidence_ids=[evidence.id])
    memory.approve_state(item.id, state.version, approved_by="maintainer")

    (memory.store.evidence_dir / f"{evidence.id}.json").write_text("{not valid json")

    with pytest.raises(CorruptProvenanceError) as excinfo:
        memory.get_current(item.id)
    # The specific evidence problem remains discoverable via chaining.
    assert isinstance(excinfo.value.__cause__, StorageCorruptionError)


def test_em01_get_current_still_returns_a_healthy_state_untouched(memory):
    # Regression guard: the provenance re-check must not reject a
    # perfectly healthy current state.
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    evidence = _record_screenshot(memory)
    state = memory.propose_state(item.id, content="claim", evidence_ids=[evidence.id])
    memory.approve_state(item.id, state.version, approved_by="maintainer")
    current = memory.get_current(item.id)
    assert current is not None
    assert current.version == state.version


def test_em01_only_current_states_evidence_is_checked_not_history(memory):
    # A superseded state's own evidence being lost must not block
    # get_current() from returning the newer, healthy current state.
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    e1 = _record_screenshot(memory)
    s1 = memory.propose_state(item.id, content="v1", evidence_ids=[e1.id])
    memory.approve_state(item.id, s1.version, approved_by="maintainer")
    e2 = _record_browser_observation(memory)
    s2 = memory.propose_state(item.id, content="v2", evidence_ids=[e2.id], relation_to_previous=Relation.SUPERSEDES)
    memory.approve_state(item.id, s2.version, approved_by="maintainer")

    (memory.store.evidence_dir / f"{e1.id}.json").unlink()  # e1 backed the now-superseded s1

    current = memory.get_current(item.id)
    assert current is not None
    assert current.version == s2.version


# --------------------------------------------------------------------------
# EM-02: natural-key slug collisions must not silently merge identity
# --------------------------------------------------------------------------

def test_em02_dot_and_hyphen_keys_collide_and_are_rejected(memory):
    a = memory.get_or_create_knowledge_item("a.b", KnowledgeType.PRODUCT, "desktop.filters")
    with pytest.raises(KeyCollisionError):
        memory.get_or_create_knowledge_item("a-b", KnowledgeType.PRODUCT, "desktop.filters")
    # The original item must be entirely unaffected by the rejected call.
    assert memory.get_knowledge_item(a.id).key == "a.b"


def test_em02_collision_detected_regardless_of_which_key_was_created_first(memory):
    memory.get_or_create_knowledge_item("a-b", KnowledgeType.PRODUCT, "desktop.filters")
    with pytest.raises(KeyCollisionError):
        memory.get_or_create_knowledge_item("a.b", KnowledgeType.PRODUCT, "desktop.filters")


def test_em02_same_key_reused_remains_idempotent_not_a_collision(memory):
    # Re-confirms existing idempotency still works: this must NOT raise.
    a = memory.get_or_create_knowledge_item("desktop.filters.button-label", KnowledgeType.PRODUCT, "desktop.filters")
    b = memory.get_or_create_knowledge_item("desktop.filters.button-label", KnowledgeType.PRODUCT, "desktop.filters")
    assert a.id == b.id


def test_em02_identity_stays_deterministic_and_stable_across_reload(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    created = m1.get_or_create_knowledge_item("desktop.filters.open-behavior", KnowledgeType.PRODUCT, "desktop.filters")

    m2 = EditorialMemory(root)
    found = m2.get_or_create_knowledge_item("desktop.filters.open-behavior", KnowledgeType.PRODUCT, "desktop.filters")
    assert found.id == created.id

    # A different natural key that normalizes to the same slug ("." -> "-")
    # must be detected as a collision even after a fresh reload, not
    # just within the same process that created the original item.
    with pytest.raises(KeyCollisionError):
        m2.get_or_create_knowledge_item("desktop-filters-open-behavior", KnowledgeType.PRODUCT, "desktop.filters")


# --------------------------------------------------------------------------
# EM-03: feature_area path traversal/escape must be rejected
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "malicious_feature_area",
    [
        "../../../etc",
        "..",
        "desktop/../../etc",
        "/etc/passwd",
        "desktop\\..\\..\\etc",
        "desktop.filters/../../evil",
        "",
        "desktop..filters",
        ".hidden",
        "desktop.",
    ],
)
def test_em03_path_traversal_feature_areas_are_rejected(memory, malicious_feature_area):
    with pytest.raises(InvalidFeatureAreaError):
        memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, malicious_feature_area)


def test_em03_rejected_feature_area_never_touches_disk_outside_root(tmp_path):
    root = tmp_path / "store"
    memory = EditorialMemory(root)
    with pytest.raises(InvalidFeatureAreaError):
        memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "../../escaped")
    # Nothing was written anywhere outside (or even inside, for this
    # rejected call) the configured root.
    outside_marker = tmp_path.parent / "escaped"
    assert not outside_marker.exists()
    assert list(root.rglob("*.json")) == []


def test_em03_legitimate_multi_segment_feature_areas_still_work(memory):
    # Regression guard: the fix must not break the documented convention.
    for fa in ["desktop.filters", "mobile.members", "desktop.new-filters-sidebar"]:
        item = memory.get_or_create_knowledge_item(f"k-{fa}", KnowledgeType.PRODUCT, fa)
        assert item.feature_area == fa


# --------------------------------------------------------------------------
# Corrupt JSON is normalized into a typed storage-corruption error
# --------------------------------------------------------------------------

def test_corrupt_knowledge_item_json_raises_typed_error_not_raw_json_error(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    path = memory.store.knowledge_dir / "desktop.filters" / f"{item.id}.json"
    path.write_text("{this is not json at all")

    with pytest.raises(StorageCorruptionError):
        memory.get_knowledge_item(item.id)


def test_corrupt_evidence_json_raises_typed_error_not_raw_json_error(memory):
    evidence = _record_screenshot(memory)
    path = memory.store.evidence_dir / f"{evidence.id}.json"
    path.write_text("not json { at all")

    with pytest.raises(StorageCorruptionError):
        memory.get_evidence(evidence.id)


def test_truncated_json_file_raises_typed_error(memory):
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    path = memory.store.knowledge_dir / "desktop.filters" / f"{item.id}.json"
    original = path.read_text()
    path.write_text(original[: len(original) // 2])  # truncate mid-record

    with pytest.raises(StorageCorruptionError):
        memory.get_knowledge_item(item.id)


# --------------------------------------------------------------------------
# EM-04: evidence_id must not escape the configured memory root
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "malicious_evidence_id",
    [
        "../../escape",
        "/etc/passwd",
        "desktop/../../etc",
        "desktop\\..\\..\\etc",
        "..",
        "a/b",
    ],
)
def test_em04_path_traversal_evidence_ids_are_rejected(memory, malicious_evidence_id):
    with pytest.raises(InvalidEvidenceIdError):
        memory.get_evidence(malicious_evidence_id)


def test_em04_rejected_evidence_id_never_touches_disk_outside_root(tmp_path):
    root = tmp_path / "store"
    memory = EditorialMemory(root)
    with pytest.raises(InvalidEvidenceIdError):
        memory.get_evidence("../../escaped")
    outside_marker = tmp_path.parent / "escaped"
    assert not outside_marker.exists()


def test_em04_valid_generated_evidence_id_still_works(memory):
    evidence = _record_screenshot(memory)
    # A real record_evidence()-generated id ("ev-" + hex) must be
    # unaffected by the EM-04 validation.
    fetched = memory.get_evidence(evidence.id)
    assert fetched.id == evidence.id


def test_em04_persisted_malicious_provenance_reference_is_rejected_via_get_current(memory):
    evidence = _record_screenshot(memory)
    item = memory.get_or_create_knowledge_item("k", KnowledgeType.PRODUCT, "desktop.filters")
    memory.propose_state(item.id, content="s", evidence_ids=[evidence.id])
    memory.approve_state(item.id, version=1, approved_by="maintainer")

    # Tamper with the persisted KnowledgeItem record directly, as if a
    # hand-edited or otherwise corrupted file smuggled in a traversal
    # payload as an evidence_refs entry.
    path = memory.store.knowledge_dir / "desktop.filters" / f"{item.id}.json"
    raw = path.read_text().replace(evidence.id, "../../escaped")
    path.write_text(raw)

    with pytest.raises(CorruptProvenanceError) as excinfo:
        memory.get_current(item.id)
    assert isinstance(excinfo.value.__cause__, InvalidEvidenceIdError)


def test_em04_evidence_id_validation_survives_reload(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    evidence = _record_screenshot(m1)

    m2 = EditorialMemory(root)  # simulate a fresh process reload
    assert m2.get_evidence(evidence.id).id == evidence.id
    with pytest.raises(InvalidEvidenceIdError):
        m2.get_evidence("../../escape")


# ==========================================================================
# Slice 2: maintainer-decision bootstrap
# ==========================================================================

def _decision_kwargs(**overrides):
    kwargs = dict(
        key="desktop.filters.button-label",
        feature_area="desktop.filters",
        content="The Filters button is labeled 'Filters', not 'Filter'.",
        source_ref="maintainer-meeting-2026-08-08",
        captured_by="founder",
        captured_at="2026-08-08T10:00:00+00:00",
        notes="Confirmed in product review",
        verification_scope=["desktop"],
        rationale="Matches the shipped UI copy.",
    )
    kwargs.update(overrides)
    return kwargs


def test_s2_01_valid_decision_creates_one_evidence_and_one_current_state(memory):
    memory.record_maintainer_decision(**_decision_kwargs())
    assert len(memory.list_evidence()) == 1
    item_id = slugify("desktop.filters.button-label")
    current = memory.get_current(item_id)
    assert current is not None
    assert current.status == StateStatus.CURRENT


def test_s2_02_state_references_the_created_evidence(memory):
    state = memory.record_maintainer_decision(**_decision_kwargs())
    evidence = memory.list_evidence()[0]
    assert state.evidence_refs == [evidence.id]
    assert evidence.evidence_type == EvidenceType.MAINTAINER_DECISION


def test_s2_03_approved_by_and_approved_at_exist_for_current_knowledge(memory):
    state = memory.record_maintainer_decision(**_decision_kwargs(captured_by="founder"))
    assert state.approved_by == "founder"
    assert state.approved_at is not None


def test_s2_03b_approved_by_can_differ_from_captured_by(memory):
    state = memory.record_maintainer_decision(
        **_decision_kwargs(captured_by="assistant", approved_by="founder")
    )
    assert state.approved_by == "founder"
    evidence = memory.list_evidence()[0]
    assert evidence.captured_by == "assistant"


def test_s2_04_rationale_survives_when_supplied(memory):
    state = memory.record_maintainer_decision(**_decision_kwargs(rationale="Because X."))
    assert state.rationale == "Because X."


def test_s2_05_verification_scope_survives_when_supplied(memory):
    memory.record_maintainer_decision(**_decision_kwargs(verification_scope=["desktop", "mobile"]))
    evidence = memory.list_evidence()[0]
    assert evidence.verification_scope == ["desktop", "mobile"]


def test_s2_06_invalid_feature_area_is_rejected(memory):
    with pytest.raises(InvalidFeatureAreaError):
        memory.record_maintainer_decision(**_decision_kwargs(feature_area="../../escape"))
    assert memory.list_evidence() == []


def test_s2_07_conflicting_creation_does_not_silently_overwrite_memory(memory):
    memory.record_maintainer_decision(**_decision_kwargs(feature_area="desktop.filters"))
    # A second call under the same key but a different feature_area must
    # be rejected outright (S2-01), not silently move/overwrite the
    # existing KnowledgeItem's feature_area.
    with pytest.raises(FeatureAreaMismatchError):
        memory.record_maintainer_decision(
            **_decision_kwargs(feature_area="desktop.other", content="A materially different claim.")
        )
    item_id = slugify("desktop.filters.button-label")
    item = memory.get_knowledge_item(item_id)
    assert item.feature_area == "desktop.filters"
    assert len(item.states) == 1


def test_s2_08_bootstrap_is_the_only_path_for_this_privilege(memory):
    # The API accepts no evidence_type argument at all - a caller cannot
    # ask the bootstrap path to mint non-maintainer-decision Evidence.
    import inspect
    params = inspect.signature(memory.record_maintainer_decision).parameters
    assert "evidence_type" not in params
    memory.record_maintainer_decision(**_decision_kwargs())
    evidence = memory.list_evidence()[0]
    assert evidence.evidence_type == EvidenceType.MAINTAINER_DECISION


def test_s2_09_created_records_round_trip_through_slice1_loading(memory):
    state = memory.record_maintainer_decision(**_decision_kwargs())
    item_id = slugify("desktop.filters.button-label")
    reloaded_item = memory.get_knowledge_item(item_id)
    reloaded_state = next(s for s in reloaded_item.states if s.version == state.version)
    assert reloaded_state.content == state.content
    assert reloaded_state.status == StateStatus.CURRENT
    provenance = memory.get_provenance(item_id, state.version)
    assert len(provenance) == 1
    assert provenance[0].evidence_type == EvidenceType.MAINTAINER_DECISION


def test_s2_10_bootstrap_reuses_existing_approval_logic(memory, monkeypatch):
    propose_calls = []
    approve_calls = []
    original_propose = memory.propose_state
    original_approve = memory.approve_state

    def spy_propose(*args, **kwargs):
        propose_calls.append((args, kwargs))
        return original_propose(*args, **kwargs)

    def spy_approve(*args, **kwargs):
        approve_calls.append((args, kwargs))
        return original_approve(*args, **kwargs)

    monkeypatch.setattr(memory, "propose_state", spy_propose)
    monkeypatch.setattr(memory, "approve_state", spy_approve)

    memory.record_maintainer_decision(**_decision_kwargs())

    assert len(propose_calls) == 1
    assert len(approve_calls) == 1
    # approve_state is invoked on the exact version propose_state created,
    # i.e. the bootstrap never writes status=current by any other route.
    assert approve_calls[0][1]["version"] == 1
    assert approve_calls[0][1]["approved_by"] == "founder"


def test_s2_10b_approving_an_already_current_state_still_uses_normal_lifecycle_rules(memory):
    # Proves the bootstrap did not bypass InvalidLifecycleTransitionError:
    # trying to approve the same version again through the ordinary API
    # still fails exactly as it would for any other state.
    state = memory.record_maintainer_decision(**_decision_kwargs())
    item_id = slugify("desktop.filters.button-label")
    with pytest.raises(InvalidLifecycleTransitionError):
        memory.approve_state(item_id, version=state.version, approved_by="founder")


def test_s2_11_exact_repeat_maintainer_decision_is_idempotent(memory):
    # Explicit, matching relation_to_previous on both calls: the default
    # relation legitimately differs between "first state on a brand-new
    # item" (NEW) and "another decision on an existing item" (REFINES),
    # so an exact repeat of the *default* is not exercised here (see
    # test_s2_15/test_s2_17 for that default behavior) - this proves
    # idempotency for the same fields including the same explicit relation.
    kwargs = _decision_kwargs(relation_to_previous=Relation.NEW)
    first = memory.record_maintainer_decision(**kwargs)
    second = memory.record_maintainer_decision(**kwargs)
    assert first.version == second.version
    assert first.content == second.content


def test_s2_12_repeated_exact_input_does_not_duplicate_records(memory):
    kwargs = _decision_kwargs(relation_to_previous=Relation.NEW)
    memory.record_maintainer_decision(**kwargs)
    memory.record_maintainer_decision(**kwargs)
    memory.record_maintainer_decision(**kwargs)
    assert len(memory.list_evidence()) == 1
    item_id = slugify("desktop.filters.button-label")
    item = memory.get_knowledge_item(item_id)
    assert len(item.states) == 1
    assert len(memory.list_knowledge_items()) == 1


def test_s2_13_materially_different_decision_creates_new_state_via_lifecycle(memory):
    first = memory.record_maintainer_decision(**_decision_kwargs())
    second = memory.record_maintainer_decision(
        **_decision_kwargs(content="Updated: the button now reads 'Filter' (singular).")
    )
    assert second.version == first.version + 1
    assert second.status == StateStatus.CURRENT

    item_id = slugify("desktop.filters.button-label")
    item = memory.get_knowledge_item(item_id)
    first_reloaded = next(s for s in item.states if s.version == first.version)
    assert first_reloaded.status == StateStatus.SUPERSEDED
    assert first_reloaded.superseded_by == second.version
    assert len(memory.list_evidence()) == 2


def test_s2_14_same_logical_knowledge_item_is_reused_not_duplicated(memory):
    memory.record_maintainer_decision(**_decision_kwargs())
    memory.record_maintainer_decision(
        **_decision_kwargs(content="A second, materially different decision about the same item.")
    )
    assert len(memory.list_knowledge_items()) == 1


def test_s2_15_default_relation_is_new_for_first_state_and_refines_for_later_ones(memory):
    first = memory.record_maintainer_decision(**_decision_kwargs())
    assert first.relation_to_previous == Relation.NEW
    second = memory.record_maintainer_decision(
        **_decision_kwargs(content="A materially different second decision.")
    )
    assert second.relation_to_previous == Relation.REFINES


# --------------------------------------------------------------------------
# S2-01: feature_area mismatch on an existing KnowledgeItem is rejected
# --------------------------------------------------------------------------

def test_s2_16_mismatched_feature_area_and_different_content_is_rejected(memory):
    memory.record_maintainer_decision(**_decision_kwargs(feature_area="desktop.filters"))
    with pytest.raises(FeatureAreaMismatchError):
        memory.record_maintainer_decision(
            **_decision_kwargs(feature_area="desktop.other", content="A totally different claim.")
        )
    assert len(memory.list_evidence()) == 1
    item_id = slugify("desktop.filters.button-label")
    item = memory.get_knowledge_item(item_id)
    assert len(item.states) == 1
    assert item.feature_area == "desktop.filters"


def test_s2_17_mismatched_feature_area_with_otherwise_exact_repeat_is_rejected(memory):
    # Same content/source_ref/captured_by/etc. as the original - only
    # feature_area differs. Must still be rejected, not treated as an
    # idempotent replay of the original decision.
    memory.record_maintainer_decision(**_decision_kwargs(feature_area="desktop.filters"))
    with pytest.raises(FeatureAreaMismatchError):
        memory.record_maintainer_decision(**_decision_kwargs(feature_area="desktop.other"))
    assert len(memory.list_evidence()) == 1
    item_id = slugify("desktop.filters.button-label")
    item = memory.get_knowledge_item(item_id)
    assert len(item.states) == 1


def test_s2_18_reload_then_mismatch_is_still_rejected(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    m1.record_maintainer_decision(**_decision_kwargs(feature_area="desktop.filters"))

    m2 = EditorialMemory(root)  # simulate a fresh process reload
    with pytest.raises(FeatureAreaMismatchError):
        m2.record_maintainer_decision(
            **_decision_kwargs(feature_area="desktop.other", content="Different after reload.")
        )
    item_id = slugify("desktop.filters.button-label")
    item = m2.get_knowledge_item(item_id)
    assert item.feature_area == "desktop.filters"
    assert len(item.states) == 1
    assert len(m2.list_evidence()) == 1


def test_s2_19_mismatch_rejection_creates_no_new_records_at_all(memory):
    memory.record_maintainer_decision(**_decision_kwargs(feature_area="desktop.filters"))
    evidence_count_before = len(memory.list_evidence())
    item_count_before = len(memory.list_knowledge_items())
    states_before = len(memory.get_knowledge_item(slugify("desktop.filters.button-label")).states)

    with pytest.raises(FeatureAreaMismatchError):
        memory.record_maintainer_decision(
            **_decision_kwargs(feature_area="mobile.filters", content="Yet another different claim.")
        )

    assert len(memory.list_evidence()) == evidence_count_before
    assert len(memory.list_knowledge_items()) == item_count_before
    item = memory.get_knowledge_item(slugify("desktop.filters.button-label"))
    assert len(item.states) == states_before


# --------------------------------------------------------------------------
# S2-02: relation_to_previous is part of exact-repeat identity
# --------------------------------------------------------------------------

def test_s2_20_same_fields_but_different_explicit_relation_creates_new_state(memory):
    first = memory.record_maintainer_decision(**_decision_kwargs(relation_to_previous=Relation.NEW))
    second = memory.record_maintainer_decision(
        **_decision_kwargs(relation_to_previous=Relation.CONTRADICTS)
    )
    assert second.version == first.version + 1
    assert second.relation_to_previous == Relation.CONTRADICTS
    assert len(memory.list_evidence()) == 2

    item_id = slugify("desktop.filters.button-label")
    item = memory.get_knowledge_item(item_id)
    first_reloaded = next(s for s in item.states if s.version == first.version)
    assert first_reloaded.status == StateStatus.SUPERSEDED
    assert first_reloaded.superseded_by == second.version


def test_s2_21_same_fields_and_same_explicit_relation_remains_idempotent(memory):
    kwargs = _decision_kwargs(relation_to_previous=Relation.REFINES)
    first = memory.record_maintainer_decision(**kwargs)
    second = memory.record_maintainer_decision(**kwargs)
    assert first.version == second.version
    assert len(memory.list_evidence()) == 1


def test_s2_22_refines_repeat_after_contradicts_is_a_new_state_not_idempotent(memory):
    memory.record_maintainer_decision(**_decision_kwargs(relation_to_previous=Relation.NEW))
    contradicting = memory.record_maintainer_decision(
        **_decision_kwargs(relation_to_previous=Relation.CONTRADICTS)
    )
    # Same fields again, but with REFINES this time - still not idempotent
    # with either prior state, since neither prior state used REFINES.
    third = memory.record_maintainer_decision(
        **_decision_kwargs(relation_to_previous=Relation.REFINES)
    )
    assert third.version == contradicting.version + 1
    assert len(memory.list_evidence()) == 3


def test_s2_23_default_relation_behavior_still_works(memory):
    first = memory.record_maintainer_decision(**_decision_kwargs())
    assert first.relation_to_previous == Relation.NEW
    second = memory.record_maintainer_decision(
        **_decision_kwargs(content="A materially different second decision.")
    )
    assert second.relation_to_previous == Relation.REFINES


def test_s2_24_history_and_supersession_remain_correct_across_relation_changes(memory):
    s1 = memory.record_maintainer_decision(**_decision_kwargs(relation_to_previous=Relation.NEW))
    s2 = memory.record_maintainer_decision(
        **_decision_kwargs(relation_to_previous=Relation.CONTRADICTS)
    )
    item_id = slugify("desktop.filters.button-label")
    history = memory.get_history(item_id)
    assert [s.version for s in history] == [1, 2]
    assert history[0].status == StateStatus.SUPERSEDED
    assert history[0].superseded_by == s2.version
    assert history[1].status == StateStatus.CURRENT
    current = memory.get_current(item_id)
    assert current.version == s2.version
    assert current.relation_to_previous == Relation.CONTRADICTS
