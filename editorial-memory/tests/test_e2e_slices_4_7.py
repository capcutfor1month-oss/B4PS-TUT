"""End-to-end and cross-slice adversarial tests for the Editorial Memory
completion batch (Slices 4-7), on top of unmodified Slices 1-3.

`test_e2e_full_lifecycle_walkthrough` drives the complete chain the
founder clarification describes in one run: existing documentation
Evidence -> proposed Knowledge -> review -> approval/current -> new
Evidence -> refinement/contradiction -> review -> supersession/update ->
invalidation -> retrieval of the correct current state -> history/
provenance preserved -> reload -> same result.

The remaining tests are adversarial cases that specifically combine two
or more slices (duplicate ingestion mid-lifecycle, conflicting evidence,
invalid transitions, corrupt/missing evidence, malformed JSON, identity/
path-traversal protections, stale/superseded/invalidated retrieval,
repeated-processing idempotency, purge authorization boundaries, and
no-silent-overwrite) - each already has exhaustive single-slice coverage
in its own test file; these prove the same guarantees hold when slices
are used together, not in isolation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from lib import (
    CorruptProvenanceError,
    EditorialMemory,
    EvidenceType,
    FeatureAreaMismatchError,
    InvalidFeatureAreaError,
    InvalidLifecycleTransitionError,
    KnowledgeType,
    Relation,
    StateStatus,
    StorageCorruptionError,
    UnknownStateVersionError,
)
from lib.purge import get_invalidated_by_key, purge_evidence, purge_knowledge_state
from lib.retrieval import get_current_by_key, get_history_by_key
from lib.review import list_conflicts, list_pending_review


@pytest.fixture
def memory(tmp_path):
    return EditorialMemory(tmp_path / "store")


def _screenshot(memory, ref):
    return memory.record_evidence(evidence_type=EvidenceType.SCREENSHOT, source_ref=ref, captured_by="maintainer")


def _raw_state_entry(memory, item_id, version):
    raw = memory.store.load_knowledge_item_raw(item_id)
    for entry in raw["states"]:
        if "purged_at" in entry and entry.get("id") == f"{item_id}#{version}":
            return entry
        if "purged_at" not in entry and entry.get("version") == version:
            return entry
    return None


# ============================================================================
# End-to-end lifecycle walkthrough
# ============================================================================

def test_e2e_full_lifecycle_walkthrough(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    key = "desktop.filters.new-toggle"
    feature_area = "desktop.filters"

    # 1. existing documentation Evidence -> proposed Knowledge (Slice 4)
    v1 = m1.ingest_existing_documentation(
        key=key, feature_area=feature_area,
        content="The New Filters toggle appears under Feature Preview settings.",
        source_ref="Current update/Desktop/MASTER Complete Bridge4PS Desktop-Browser Feature Tutorials.pptx#slide171",
        captured_by="ingestion-script",
        rationale="extracted verbatim from the deck caption",
    )
    assert v1.status == StateStatus.PROPOSED
    item_id = m1.get_or_create_knowledge_item(key, KnowledgeType.DOCUMENTATION, feature_area).id

    # 2. review (Slice 5) - visible in the pending queue, not yet current
    pending = list_pending_review(m1, feature_area=feature_area)
    assert [p.version for p in pending] == [1]
    assert get_current_by_key(m1, key) is None

    # 3. approval/current - a human resolves the review item via existing lifecycle
    m1.approve_state(item_id, v1.version, approved_by="maintainer")
    current = get_current_by_key(m1, key)
    assert current.version == 1
    assert current.content == "The New Filters toggle appears under Feature Preview settings."
    assert list_pending_review(m1, feature_area=feature_area) == []

    # 4. new Evidence -> refinement (Slice 6), still requires review/approval
    v2 = m1.propose_state(
        item_id, "The New Filters toggle appears under Feature Preview settings, scoped per workspace.",
        [_screenshot(m1, "Source/Desktop/Screenshots/toggle_detail.png").id],
        relation_to_previous=Relation.REFINES,
    )
    assert get_current_by_key(m1, key).version == 1  # unchanged until approved
    m1.approve_state(item_id, v2.version, approved_by="maintainer")
    assert get_current_by_key(m1, key).version == 2

    # 5. new Evidence -> contradiction (Slice 6), flagged for review, never auto-promoted
    v3 = m1.propose_state(
        item_id, "The New Filters toggle appears under Settings > General, not Feature Preview.",
        [_screenshot(m1, "Source/Desktop/Screenshots/toggle_conflict.png").id],
        relation_to_previous=Relation.CONTRADICTS,
    )
    assert v3.review_required is True
    assert len(list_conflicts(m1, feature_area=feature_area)) == 1
    assert get_current_by_key(m1, key).version == 2  # still untouched

    # 6. review resolves the contradiction as a rejection (Slice 5) - it was a stale reading
    m1.invalidate_state(item_id, v3.version, invalidated_by="maintainer", reason="checked against a stale build")
    assert list_conflicts(m1, feature_area=feature_area) == []
    assert get_current_by_key(m1, key).version == 2  # unchanged - the contradiction was rejected, not applied

    # 7. supersession/update - a genuine product change arrives afterward
    v4 = m1.propose_state(
        item_id, "The New Filters toggle moved to Settings > General in the 2026-08 release.",
        [_screenshot(m1, "Source/Desktop/Screenshots/toggle_moved.png").id],
        relation_to_previous=Relation.SUPERSEDES,
    )
    m1.approve_state(item_id, v4.version, approved_by="maintainer")
    assert get_current_by_key(m1, key).version == 4

    # 8. invalidation where appropriate - v1 turns out to have been extracted from a
    # corrupted OCR pass and was never trustworthy, distinct from v2 simply being superseded
    m1.invalidate_state(item_id, v1.version, invalidated_by="maintainer", reason="corrupted OCR extraction")

    # 9. retrieval of the correct current state
    current = get_current_by_key(m1, key)
    assert current.version == 4
    assert current.content == "The New Filters toggle moved to Settings > General in the 2026-08 release."

    # 10. history/provenance preserved: v1 and v3 (invalidated) excluded from history,
    # v2 (superseded) and v4 (current) remain, both fully provenanced
    history = get_history_by_key(m1, key)
    assert [s.version for s in history] == [2, 4]
    assert [s.status for s in history] == [StateStatus.SUPERSEDED, StateStatus.CURRENT]
    for state in history:
        assert len(state.evidence_refs) == 1

    invalidated = get_invalidated_by_key(m1, key)
    assert {s.version for s in invalidated} == {1, 3}

    # 11. reload -> same result
    m2 = EditorialMemory(root)
    assert get_current_by_key(m2, key) == get_current_by_key(m1, key)
    assert get_history_by_key(m2, key) == get_history_by_key(m1, key)
    assert get_invalidated_by_key(m2, key) == get_invalidated_by_key(m1, key)
    assert list_pending_review(m2, feature_area=feature_area) == list_pending_review(m1, feature_area=feature_area)


# ============================================================================
# Adversarial cross-slice cases
# ============================================================================

# Duplicate ingestion mid-lifecycle: re-submitting the *original* documentation
# claim after the item has since evolved does not resurrect or duplicate it -
# it is evaluated against current disk state, not against ingestion order.
def test_adversarial_duplicate_ingestion_mid_lifecycle(memory):
    kwargs = dict(
        key="desktop.filters.dup", feature_area="desktop.filters",
        content="original claim", source_ref="doc.pptx#1", captured_by="ingestion-script",
        relation_to_previous=Relation.NEW,
    )
    v1 = memory.ingest_existing_documentation(**kwargs)
    item_id = memory.get_or_create_knowledge_item(kwargs["key"], KnowledgeType.DOCUMENTATION, kwargs["feature_area"]).id
    memory.approve_state(item_id, v1.version, approved_by="maintainer")

    # exact same call, with the same explicit relation, resubmitted after approval -
    # dedup still recognizes it and creates no new record even though the item now
    # has a current state
    repeat = memory.ingest_existing_documentation(**kwargs)
    assert repeat.version == v1.version
    assert len(memory.get_knowledge_item(item_id).states) == 1


# Conflicting evidence: two independent contradicting proposals against the same
# current state both surface for review; neither silently wins.
def test_adversarial_conflicting_evidence_both_flagged(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.conflict", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = memory.propose_state(item.id, "says A", [_screenshot(memory, "a.png").id])
    memory.approve_state(item.id, v1.version, approved_by="maintainer")

    memory.propose_state(item.id, "says B", [_screenshot(memory, "b.png").id], relation_to_previous=Relation.CONTRADICTS)
    memory.propose_state(item.id, "says C", [_screenshot(memory, "c.png").id], relation_to_previous=Relation.CONTRADICTS)

    conflicts = list_conflicts(memory, feature_area="desktop.filters")
    assert {c.content for c in conflicts} == {"says B", "says C"}
    assert get_current_by_key(memory, item.key).content == "says A"


# Invalid lifecycle transitions: approving an already-invalidated state is rejected,
# even when reached via the Slice 4/7 combination (ingest then invalidate then approve).
def test_adversarial_invalid_transition_after_ingestion_and_invalidation(memory):
    v1 = memory.ingest_existing_documentation(
        key="desktop.filters.bad", feature_area="desktop.filters",
        content="claim", source_ref="doc.pptx", captured_by="ingestion-script",
    )
    item_id = memory.get_or_create_knowledge_item(
        "desktop.filters.bad", KnowledgeType.DOCUMENTATION, "desktop.filters"
    ).id
    memory.invalidate_state(item_id, v1.version, invalidated_by="maintainer", reason="never approve this")

    with pytest.raises(InvalidLifecycleTransitionError):
        memory.approve_state(item_id, v1.version, approved_by="maintainer")


# Missing/corrupt Evidence: a corrupted current-state Evidence surfaces loudly via
# retrieval, while the review queue for an unrelated item stays correct and unaffected.
def test_adversarial_corrupt_evidence_isolated_to_its_own_item(memory):
    ev = _screenshot(memory, "will_be_corrupted.png")
    broken = memory.get_or_create_knowledge_item("desktop.filters.broken", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(broken.id, "claim", [ev.id])
    memory.approve_state(broken.id, p.version, approved_by="maintainer")

    healthy = memory.get_or_create_knowledge_item("desktop.filters.healthy", KnowledgeType.PRODUCT, "desktop.filters")
    memory.propose_state(healthy.id, "pending claim", [_screenshot(memory, "healthy.png").id])

    (memory.store.root / "evidence" / f"{ev.id}.json").write_text("{not valid json")

    # corrupt evidence behind a current state surfaces as CorruptProvenanceError
    # (EM-01), chaining the underlying StorageCorruptionError as its cause
    with pytest.raises(CorruptProvenanceError) as excinfo:
        get_current_by_key(memory, broken.key)
    assert isinstance(excinfo.value.__cause__, StorageCorruptionError)

    # unrelated item's review queue is unaffected by the other item's corruption
    pending = list_pending_review(memory, feature_area="desktop.filters")
    assert [p.key for p in pending] == ["desktop.filters.healthy"]


# Malformed persisted JSON: a corrupted KnowledgeItem file fails typed and safely
# across every Slice 3/5/7 retrieval path that touches it.
def test_adversarial_malformed_knowledge_item_json_fails_safely_everywhere(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.corrupt-item", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "claim", [_screenshot(memory, "e.png").id])
    memory.approve_state(item.id, p.version, approved_by="maintainer")

    path = memory.store.root / "knowledge" / item.feature_area / f"{item.id}.json"
    path.write_text("{not valid json")

    with pytest.raises(StorageCorruptionError):
        get_current_by_key(memory, item.key)
    with pytest.raises(StorageCorruptionError):
        get_history_by_key(memory, item.key)
    with pytest.raises(StorageCorruptionError):
        get_invalidated_by_key(memory, item.key)


# Identity/path-traversal protections: Slice 4's feature_area validation reuses EM-03,
# with zero side effects on rejection, exactly like Slice 2's equivalent path.
def test_adversarial_path_traversal_rejected_with_zero_side_effects(memory):
    with pytest.raises(InvalidFeatureAreaError):
        memory.ingest_existing_documentation(
            key="desktop.evil", feature_area="../../escape",
            content="claim", source_ref="doc.pptx", captured_by="ingestion-script",
        )
    assert memory.store.list_knowledge_item_ids() == []
    assert memory.store.list_evidence_ids() == []


# Stale/superseded/invalidated retrieval: all three non-current statuses behave
# correctly together on one item, across Slice 3 (current/history) and Slice 7 (invalidated audit).
def test_adversarial_stale_superseded_invalidated_retrieval_together(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.lifecycle", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = memory.propose_state(item.id, "v1", [_screenshot(memory, "e1.png").id])
    memory.approve_state(item.id, v1.version, approved_by="maintainer")
    v2 = memory.propose_state(item.id, "v2", [_screenshot(memory, "e2.png").id], relation_to_previous=Relation.SUPERSEDES)
    memory.approve_state(item.id, v2.version, approved_by="maintainer")
    v3 = memory.propose_state(item.id, "v3 bad", [_screenshot(memory, "e3.png").id])
    memory.invalidate_state(item.id, v3.version, invalidated_by="maintainer", reason="bad")

    assert get_current_by_key(memory, item.key).version == 2
    assert [s.version for s in get_history_by_key(memory, item.key)] == [1, 2]  # v3 excluded
    assert [s.version for s in get_invalidated_by_key(memory, item.key)] == [3]


# Repeated processing/idempotency: replaying the same maintainer-decision +
# documentation-ingestion workflow twice end-to-end produces identical final state.
def test_adversarial_repeated_processing_is_idempotent_end_to_end(memory):
    def run():
        memory.record_maintainer_decision(
            key="desktop.filters.repeat", feature_area="desktop.filters",
            content="editorial call", source_ref="maintainer-notes", captured_by="maintainer",
            relation_to_previous=Relation.NEW,
        )
        memory.ingest_existing_documentation(
            key="desktop.filters.repeat-doc", feature_area="desktop.filters",
            content="doc claim", source_ref="doc.pptx", captured_by="ingestion-script",
            relation_to_previous=Relation.NEW,
        )

    run()
    item1 = memory.get_or_create_knowledge_item("desktop.filters.repeat", KnowledgeType.EDITORIAL, "desktop.filters")
    item2 = memory.get_or_create_knowledge_item("desktop.filters.repeat-doc", KnowledgeType.DOCUMENTATION, "desktop.filters")
    counts_before = (len(item1.states), len(item2.states), len(memory.store.list_evidence_ids()))

    run()
    run()
    item1_after = memory.get_or_create_knowledge_item("desktop.filters.repeat", KnowledgeType.EDITORIAL, "desktop.filters")
    item2_after = memory.get_or_create_knowledge_item("desktop.filters.repeat-doc", KnowledgeType.DOCUMENTATION, "desktop.filters")
    counts_after = (len(item1_after.states), len(item2_after.states), len(memory.store.list_evidence_ids()))

    assert counts_before == counts_after


# Purge authorization boundaries: purge is always targeted at one exact, already-
# identified (item_id, version) or evidence_id pair - a version that exists on a
# *different* item is not reachable through another item's id.
def test_adversarial_purge_cannot_cross_item_boundaries(memory):
    item_a = memory.get_or_create_knowledge_item("desktop.filters.a", KnowledgeType.PRODUCT, "desktop.filters")
    memory.propose_state(item_a.id, "a v1", [_screenshot(memory, "a.png").id])
    item_b = memory.get_or_create_knowledge_item("desktop.filters.b", KnowledgeType.PRODUCT, "desktop.filters")
    memory.propose_state(item_b.id, "b v1", [_screenshot(memory, "b.png").id])

    # version 1 exists on both items, but purging via item_b's id must not touch item_a
    purge_knowledge_state(memory, item_b.id, 1, purged_by="maintainer", tombstone=False)

    assert memory.get_knowledge_item(item_a.id).states[0].content == "a v1"  # untouched
    assert memory.get_knowledge_item(item_b.id).states == []


# No silent overwrite: purge_knowledge_state's tombstone mode never leaves the entry
# looking like ordinary, un-redacted content - the redaction is always visible, never silent.
def test_adversarial_purge_tombstone_is_never_silent(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.silent", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "sensitive content", [_screenshot(memory, "e.png").id])
    memory.invalidate_state(item.id, p.version, invalidated_by="maintainer", reason="PII")

    stub = purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="PII removal")

    # never silent: a real, attributed tombstone is always left behind (default mode) -
    # the sensitive content itself is gone, but the fact of the purge and why is not
    reloaded = memory.get_knowledge_item(item.id)
    assert reloaded.states == []
    assert stub.purged_by == "maintainer"
    assert stub.reason == "PII removal"
    persisted = _raw_state_entry(memory, item.id, p.version)
    assert persisted is not None
    assert "sensitive content" not in str(persisted)  # the original content never leaks into the tombstone


# Final cross-cutting check: all Slice 1-3 tests plus every Slice 4-7 test still pass
# together in the same process (import-level sanity - the real proof is the full
# suite run recorded in the batch report, not this test alone).
def test_all_modules_importable_together(memory):
    import lib.memory  # noqa: F401
    import lib.models  # noqa: F401
    import lib.store  # noqa: F401
    import lib.errors  # noqa: F401
    import lib.retrieval  # noqa: F401
    import lib.review  # noqa: F401
    import lib.purge  # noqa: F401
