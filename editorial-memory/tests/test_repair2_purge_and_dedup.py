"""Adversarial regression tests for the second Slices 4-7 audit repair
round (findings 1-5, plus GOV-01/02 covered in governance records, not
here).

Each section proves the specific defect its finding describes - not a
general re-test of Slice 4/7 (those already exist in
`test_slice4_documentation_ingestion.py`/`test_slice7_invalidation_purge.py`/
`test_em47_audit_repair.py`).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from lib import (
    CorruptEvidenceRecordError,
    EditorialMemory,
    EvidenceType,
    FeatureAreaMismatchError,
    KnowledgeType,
    KnowledgeTypeMismatchError,
    Relation,
    StateStatus,
)
from lib.purge import get_invalidated_by_key, purge_evidence, purge_knowledge_state
from lib.retrieval import get_current_by_key, get_history_by_key
from lib.review import list_conflicts, list_pending_review


@pytest.fixture
def memory(tmp_path):
    return EditorialMemory(tmp_path / "store")


def _evidence(memory, ref="e.png"):
    return memory.record_evidence(evidence_type=EvidenceType.SCREENSHOT, source_ref=ref, captured_by="maintainer")


def _raw_state_entry(memory, item_id, version):
    """Test helper: the raw persisted entry for one version (real state
    or tombstone), read via the unfiltered accessor - `None` if there is
    no entry at all for that version."""
    raw = memory.store.load_knowledge_item_raw(item_id)
    for entry in raw["states"]:
        if "purged_at" in entry and entry.get("id") == f"{item_id}#{version}":
            return entry
        if "purged_at" not in entry and entry.get("version") == version:
            return entry
    return None


# ============================================================================
# Finding 1: omitted-relation dedup must use stable persisted identity,
# not mutable list position - and must still work after an earlier state
# is fully purged
# ============================================================================

def test_finding1_repeat_dedup_still_works_after_earlier_state_fully_purged(memory):
    key, feature_area = "desktop.filters.f1", "desktop.filters"
    v1 = memory.ingest_existing_documentation(
        key=key, feature_area=feature_area, content="v1 content",
        source_ref="doc1.pptx", captured_by="ingestion-script",
    )
    kwargs2 = dict(
        key=key, feature_area=feature_area, content="v2 content",
        source_ref="doc2.pptx", captured_by="ingestion-script",
    )
    v2 = memory.ingest_existing_documentation(**kwargs2)
    assert v1.version == 1
    assert v2.relation_to_previous == Relation.REFINES  # correctly REFINES relative to v1, at creation time

    item_id = memory.get_or_create_knowledge_item(key, KnowledgeType.DOCUMENTATION, feature_area).id
    purge_knowledge_state(memory, item_id, v1.version, purged_by="maintainer")

    # v2 is now the item's only surviving state and, by array position, "first" -
    # but its own persisted identity (version == 2) still correctly says REFINES,
    # not NEW, so a repeat must still dedupe against it rather than creating a duplicate
    repeat = memory.ingest_existing_documentation(**kwargs2)
    assert repeat.version == v2.version
    assert len(memory.get_knowledge_item(item_id).states) == 1


def test_finding1_repeat_of_purged_original_state_is_treated_as_fresh(memory):
    # if the item's true original state was itself the one purged, nothing
    # carries the "this was first" identity anymore - a resubmission of
    # exactly that original claim correctly creates a new (fresh) state,
    # not a false match against something else
    key, feature_area = "desktop.filters.f1b", "desktop.filters"
    kwargs1 = dict(
        key=key, feature_area=feature_area, content="original content",
        source_ref="doc1.pptx", captured_by="ingestion-script",
    )
    v1 = memory.ingest_existing_documentation(**kwargs1)
    item_id = memory.get_or_create_knowledge_item(key, KnowledgeType.DOCUMENTATION, feature_area).id
    purge_knowledge_state(memory, item_id, v1.version, purged_by="maintainer")

    repeat = memory.ingest_existing_documentation(**kwargs1)
    assert repeat.relation_to_previous == Relation.NEW  # treated as a fresh first state
    assert len(memory.get_knowledge_item(item_id).states) == 1


def test_finding1_dedup_survives_reload_after_purge(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    key, feature_area = "desktop.filters.f1-reload", "desktop.filters"
    v1 = m1.ingest_existing_documentation(
        key=key, feature_area=feature_area, content="v1", source_ref="d1", captured_by="script",
    )
    kwargs2 = dict(key=key, feature_area=feature_area, content="v2", source_ref="d2", captured_by="script")
    v2 = m1.ingest_existing_documentation(**kwargs2)
    item_id = m1.get_or_create_knowledge_item(key, KnowledgeType.DOCUMENTATION, feature_area).id
    purge_knowledge_state(m1, item_id, v1.version, purged_by="maintainer")

    m2 = EditorialMemory(root)  # fresh instance, forces a real reload from disk
    repeat = m2.ingest_existing_documentation(**kwargs2)
    assert repeat.version == v2.version
    assert len(m2.get_knowledge_item(item_id).states) == 1


# ============================================================================
# Finding 2: version allocation must never reuse a version still
# referenced by a surviving state's superseded_by
# ============================================================================

def test_finding2_new_version_never_reuses_a_dangling_superseded_by_reference(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.f2", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = memory.propose_state(item.id, "v1", [_evidence(memory, "e1.png").id])
    memory.approve_state(item.id, v1.version, approved_by="maintainer")
    v2 = memory.propose_state(item.id, "v2", [_evidence(memory, "e2.png").id], relation_to_previous=Relation.SUPERSEDES)
    memory.approve_state(item.id, v2.version, approved_by="maintainer")  # v1.superseded_by = 2

    purge_knowledge_state(memory, item.id, v2.version, purged_by="maintainer", tombstone=False)
    reloaded = memory.get_knowledge_item(item.id)
    assert [s.version for s in reloaded.states] == [1]
    assert reloaded.states[0].superseded_by == 2  # dangling reference, still present on the surviving state

    v3 = memory.propose_state(item.id, "v3", [_evidence(memory, "e3.png").id])
    assert v3.version == 3  # not 2 - version 2 is still "spoken for" by v1's superseded_by


def test_finding2_dangling_reference_from_a_fully_removed_middle_state(memory):
    # three states, remove the middle one whose OWN superseded_by (not just its
    # own version) still gets referenced by another surviving state
    item = memory.get_or_create_knowledge_item("desktop.filters.f2b", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = memory.propose_state(item.id, "v1", [_evidence(memory, "e1.png").id])
    memory.approve_state(item.id, v1.version, approved_by="maintainer")
    v2 = memory.propose_state(item.id, "v2", [_evidence(memory, "e2.png").id], relation_to_previous=Relation.SUPERSEDES)
    memory.approve_state(item.id, v2.version, approved_by="maintainer")
    v3 = memory.propose_state(item.id, "v3", [_evidence(memory, "e3.png").id], relation_to_previous=Relation.SUPERSEDES)
    memory.approve_state(item.id, v3.version, approved_by="maintainer")  # v2.superseded_by = 3

    # purge v3 (current, highest version) fully
    purge_knowledge_state(memory, item.id, v3.version, purged_by="maintainer", tombstone=False)
    reloaded = memory.get_knowledge_item(item.id)
    assert [s.version for s in reloaded.states] == [1, 2]
    assert reloaded.states[1].superseded_by == 3  # v2 still points at the now-gone v3

    v4 = memory.propose_state(item.id, "v4", [_evidence(memory, "e4.png").id])
    assert v4.version == 4  # not 3


def test_finding2_version_uniqueness_and_no_dangling_reuse_survives_reload(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    item = m1.get_or_create_knowledge_item("desktop.filters.f2-reload", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = m1.propose_state(item.id, "v1", [m1.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="e1.png", captured_by="maintainer").id])
    m1.approve_state(item.id, v1.version, approved_by="maintainer")
    v2 = m1.propose_state(item.id, "v2", [m1.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="e2.png", captured_by="maintainer").id],
        relation_to_previous=Relation.SUPERSEDES)
    m1.approve_state(item.id, v2.version, approved_by="maintainer")
    purge_knowledge_state(m1, item.id, v2.version, purged_by="maintainer", tombstone=False)

    m2 = EditorialMemory(root)
    v3 = m2.propose_state(item.id, "v3", [m2.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="e3.png", captured_by="maintainer").id])
    assert v3.version == 3  # the dangling superseded_by=2 reference was reloaded correctly and respected


# ============================================================================
# Finding 3: exact-repeat/dedup paths must use the typed Evidence loader -
# no raw KeyError from tombstoned/corrupt Evidence encountered mid-dedup
# ============================================================================

def test_finding3_dedup_does_not_crash_on_tombstoned_evidence(memory):
    key, feature_area = "desktop.filters.f3", "desktop.filters"
    kwargs = dict(key=key, feature_area=feature_area, content="claim", source_ref="doc.pptx", captured_by="script")
    memory.ingest_existing_documentation(**kwargs)
    item_id = memory.get_or_create_knowledge_item(key, KnowledgeType.DOCUMENTATION, feature_area).id
    ev_id = memory.get_knowledge_item(item_id).states[0].evidence_refs[0]

    purge_evidence(memory, ev_id, purged_by="maintainer")  # tombstone=True default

    # must not raise a raw KeyError - the typed get_evidence() is used internally,
    # and a corrupt/tombstoned candidate is skipped, not fatal to the whole call
    try:
        memory.ingest_existing_documentation(**kwargs)
    except KeyError:
        pytest.fail("a raw KeyError leaked out of dedup while checking tombstoned Evidence")


def test_finding3_dedup_evidence_lookup_uses_typed_loader_directly(memory):
    # a more targeted proof: corrupt (not tombstone) the evidence file with
    # invalid JSON and confirm the typed StorageCorruptionError path (also
    # wrapped by get_evidence into a caught EditorialMemoryError) doesn't crash
    key, feature_area = "desktop.filters.f3b", "desktop.filters"
    kwargs = dict(key=key, feature_area=feature_area, content="claim", source_ref="doc.pptx", captured_by="script")
    memory.ingest_existing_documentation(**kwargs)
    item_id = memory.get_or_create_knowledge_item(key, KnowledgeType.DOCUMENTATION, feature_area).id
    ev_id = memory.get_knowledge_item(item_id).states[0].evidence_refs[0]

    ev_path = memory.store.root / "evidence" / f"{ev_id}.json"
    ev_path.write_text("{not valid json")

    try:
        memory.ingest_existing_documentation(**kwargs)
    except KeyError:
        pytest.fail("a raw KeyError leaked out of dedup while checking corrupt Evidence")


# ============================================================================
# Finding 4: knowledge_type isolation must be enforced across every
# ingestion path before dedup/mutation - product/documentation/editorial
# knowledge must never blend under one KnowledgeItem
# ============================================================================

def test_finding4_maintainer_decision_rejects_existing_product_typed_item(memory):
    key, feature_area = "desktop.filters.f4a", "desktop.filters"
    item = memory.get_or_create_knowledge_item(key, KnowledgeType.PRODUCT, feature_area)
    memory.propose_state(item.id, "product fact", [_evidence(memory).id])

    with pytest.raises(KnowledgeTypeMismatchError):
        memory.record_maintainer_decision(
            key=key, feature_area=feature_area, content="editorial call",
            source_ref="notes", captured_by="maintainer",
        )
    assert len(memory.get_knowledge_item(item.id).states) == 1  # zero side effects


def test_finding4_ingest_documentation_rejects_existing_product_typed_item(memory):
    key, feature_area = "desktop.filters.f4b", "desktop.filters"
    item = memory.get_or_create_knowledge_item(key, KnowledgeType.PRODUCT, feature_area)
    memory.propose_state(item.id, "product fact", [_evidence(memory).id])

    with pytest.raises(KnowledgeTypeMismatchError):
        memory.ingest_existing_documentation(
            key=key, feature_area=feature_area, content="doc claim",
            source_ref="doc.pptx", captured_by="ingestion-script",
        )
    assert len(memory.get_knowledge_item(item.id).states) == 1


def test_finding4_maintainer_decision_rejects_existing_documentation_typed_item(memory):
    key, feature_area = "desktop.filters.f4c", "desktop.filters"
    memory.ingest_existing_documentation(
        key=key, feature_area=feature_area, content="doc claim",
        source_ref="doc.pptx", captured_by="ingestion-script",
    )
    with pytest.raises(KnowledgeTypeMismatchError):
        memory.record_maintainer_decision(
            key=key, feature_area=feature_area, content="editorial call",
            source_ref="notes", captured_by="maintainer",
        )
    item_id = memory.get_or_create_knowledge_item(key, KnowledgeType.DOCUMENTATION, feature_area).id
    assert len(memory.get_knowledge_item(item_id).states) == 1


def test_finding4_ingest_documentation_rejects_existing_editorial_typed_item(memory):
    key, feature_area = "desktop.filters.f4d", "desktop.filters"
    memory.record_maintainer_decision(
        key=key, feature_area=feature_area, content="editorial call",
        source_ref="notes", captured_by="maintainer",
    )
    with pytest.raises(KnowledgeTypeMismatchError):
        memory.ingest_existing_documentation(
            key=key, feature_area=feature_area, content="doc claim",
            source_ref="doc.pptx", captured_by="ingestion-script",
        )
    item_id = memory.get_or_create_knowledge_item(key, KnowledgeType.EDITORIAL, feature_area).id
    assert len(memory.get_knowledge_item(item_id).states) == 1


def test_finding4_feature_area_mismatch_still_checked_before_knowledge_type(memory):
    # both guards must coexist correctly: a request with BOTH a mismatched
    # feature_area AND a mismatched knowledge_type still raises - and raises
    # the feature_area error first, matching S2-01's original before-any-
    # mutation ordering, since it's checked first in the existing code
    key = "desktop.filters.f4e"
    memory.get_or_create_knowledge_item(key, KnowledgeType.PRODUCT, "desktop.filters")

    with pytest.raises(FeatureAreaMismatchError):
        memory.record_maintainer_decision(
            key=key, feature_area="desktop.members", content="x",
            source_ref="notes", captured_by="maintainer",
        )


# ============================================================================
# Finding 5: a purged KnowledgeState's tombstone must be invisible to
# every normal query path
# ============================================================================

def test_finding5_tombstone_invisible_from_every_normal_query_path(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.f5", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = memory.propose_state(item.id, "v1", [_evidence(memory, "e1.png").id])
    memory.approve_state(item.id, v1.version, approved_by="maintainer")
    v2 = memory.propose_state(item.id, "v2 contradiction", [_evidence(memory, "e2.png").id],
                               relation_to_previous=Relation.CONTRADICTS)

    purge_knowledge_state(memory, item.id, v1.version, purged_by="maintainer", reason="test")
    purge_knowledge_state(memory, item.id, v2.version, purged_by="maintainer", reason="test")

    assert get_current_by_key(memory, item.key) is None
    assert memory.get_current(item.id) is None
    assert get_history_by_key(memory, item.key) == []
    assert list_pending_review(memory, feature_area=item.feature_area) == []
    assert list_conflicts(memory, feature_area=item.feature_area) == []
    assert get_invalidated_by_key(memory, item.key) == []
    assert memory.get_knowledge_item(item.id).states == []


def test_finding5_tombstone_is_not_a_knowledge_state_shape(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.f5b", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])
    purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="test")

    raw = _raw_state_entry(memory, item.id, p.version)
    assert set(raw.keys()) == {"id", "purged_at", "purged_by", "reason"}  # exactly the approved contract
    # none of the ordinary KnowledgeState fields exist on the tombstone
    for forbidden in ("version", "content", "status", "relation_to_previous", "evidence_refs"):
        assert forbidden not in raw
    # the tombstone lives in the item's own file - no new top-level directory
    assert not (memory.store.root / "tombstones").exists()


def test_finding5_other_items_unaffected_and_still_load_correctly(memory):
    # the strongest invisibility proof: a purged state living in a *different*
    # item does not break loading of an unrelated, healthy item at all
    purged_item = memory.get_or_create_knowledge_item("desktop.filters.f5c", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(purged_item.id, "content", [_evidence(memory).id])
    purge_knowledge_state(memory, purged_item.id, p.version, purged_by="maintainer")

    healthy_item = memory.get_or_create_knowledge_item("desktop.filters.f5d", KnowledgeType.PRODUCT, "desktop.filters")
    hv = memory.propose_state(healthy_item.id, "healthy content", [_evidence(memory, "h.png").id])
    memory.approve_state(healthy_item.id, hv.version, approved_by="maintainer")

    assert get_current_by_key(memory, healthy_item.key).content == "healthy content"


def test_finding5_reload_confirms_invisibility_and_no_trace_mode(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    item = m1.get_or_create_knowledge_item("desktop.filters.f5-reload", KnowledgeType.PRODUCT, "desktop.filters")
    p = m1.propose_state(item.id, "content", [m1.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="e.png", captured_by="maintainer").id])
    purge_knowledge_state(m1, item.id, p.version, purged_by="maintainer", tombstone=False)

    m2 = EditorialMemory(root)
    assert m2.get_knowledge_item(item.id).states == []
    assert _raw_state_entry(m2, item.id, p.version) is None  # no-trace mode leaves nothing
    assert get_current_by_key(m2, item.key) is None
