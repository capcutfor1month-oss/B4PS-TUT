"""Adversarial regression tests for the EM47 audit findings against the
Slices 4-7 completion batch.

Each section below is named after its finding and proves the specific
defect described in the audit is fixed - not a general re-test of the
slice it lives in (those already exist in `test_slice4_..7_*.py`).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from lib import (
    CorruptEvidenceRecordError,
    CorruptProvenanceError,
    EditorialMemory,
    EvidenceType,
    InvalidKnowledgeItemIdError,
    KnowledgeType,
    MissingPurgeAuthorizationError,
    Relation,
    StateStatus,
)
from lib.purge import get_invalidated_by_key, purge_evidence, purge_knowledge_state
from lib.retrieval import get_current_by_key
from lib.review import list_pending_review


@pytest.fixture
def memory(tmp_path):
    return EditorialMemory(tmp_path / "store")


def _evidence(memory, ref="e.png"):
    return memory.record_evidence(evidence_type=EvidenceType.SCREENSHOT, source_ref=ref, captured_by="maintainer")


# ============================================================================
# EM47-01: omitted-relation exact repeats must be idempotent (Slice 2 + 4)
# ============================================================================

def test_em47_01_slice2_omitted_relation_repeat_is_idempotent(memory):
    kwargs = dict(
        key="desktop.filters.omitted", feature_area="desktop.filters",
        content="editorial call", source_ref="maintainer-notes", captured_by="maintainer",
        # relation_to_previous deliberately omitted on every call
    )
    first = memory.record_maintainer_decision(**kwargs)
    second = memory.record_maintainer_decision(**kwargs)
    third = memory.record_maintainer_decision(**kwargs)

    assert first.version == second.version == third.version == 1
    assert first.relation_to_previous == Relation.NEW
    item_id = memory.get_or_create_knowledge_item(kwargs["key"], KnowledgeType.EDITORIAL, kwargs["feature_area"]).id
    assert len(memory.get_knowledge_item(item_id).states) == 1
    assert len(memory.store.list_evidence_ids()) == 1


def test_em47_01_slice4_omitted_relation_repeat_is_idempotent(memory):
    kwargs = dict(
        key="desktop.filters.omitted-doc", feature_area="desktop.filters",
        content="doc claim", source_ref="doc.pptx", captured_by="ingestion-script",
    )
    first = memory.ingest_existing_documentation(**kwargs)
    second = memory.ingest_existing_documentation(**kwargs)
    third = memory.ingest_existing_documentation(**kwargs)

    assert first.version == second.version == third.version == 1
    item_id = memory.get_or_create_knowledge_item(
        kwargs["key"], KnowledgeType.DOCUMENTATION, kwargs["feature_area"]
    ).id
    assert len(memory.get_knowledge_item(item_id).states) == 1


def test_em47_01_omitted_relation_repeat_survives_approval_in_between(memory):
    # regression proof: without the fix, a repeat submitted *after* the item
    # already has one state recomputes its default as REFINES (item no
    # longer empty) and fails to match the original state's stored NEW -
    # creating a spurious duplicate. Approving the first state in between
    # (as a real reviewer would) must not change this.
    kwargs = dict(
        key="desktop.filters.omitted-approved", feature_area="desktop.filters",
        content="claim", source_ref="doc.pptx", captured_by="ingestion-script",
    )
    v1 = memory.ingest_existing_documentation(**kwargs)
    item_id = memory.get_or_create_knowledge_item(
        kwargs["key"], KnowledgeType.DOCUMENTATION, kwargs["feature_area"]
    ).id
    memory.approve_state(item_id, v1.version, approved_by="maintainer")

    repeat = memory.ingest_existing_documentation(**kwargs)
    assert repeat.version == v1.version
    assert len(memory.get_knowledge_item(item_id).states) == 1


def test_em47_01_explicit_relation_still_requires_exact_match(memory):
    # S2-02 protection must survive EM47-01's fix: an explicit relation is
    # still compared exactly, never treated as omitted.
    kwargs = dict(
        key="desktop.filters.explicit", feature_area="desktop.filters",
        content="claim", source_ref="doc.pptx", captured_by="ingestion-script",
    )
    memory.ingest_existing_documentation(**kwargs, relation_to_previous=Relation.NEW)
    second = memory.ingest_existing_documentation(**kwargs, relation_to_previous=Relation.CONTRADICTS)

    item_id = memory.get_or_create_knowledge_item(
        kwargs["key"], KnowledgeType.DOCUMENTATION, kwargs["feature_area"]
    ).id
    assert len(memory.get_knowledge_item(item_id).states) == 2
    assert second.relation_to_previous == Relation.CONTRADICTS


def test_em47_01_materially_different_omitted_relation_call_still_creates_new_state(memory):
    kwargs = dict(
        key="desktop.filters.omitted-diff", feature_area="desktop.filters",
        content="first claim", source_ref="doc.pptx", captured_by="ingestion-script",
    )
    first = memory.ingest_existing_documentation(**kwargs)
    second = memory.ingest_existing_documentation(**{**kwargs, "content": "revised claim"})

    assert second.version == first.version + 1
    assert second.relation_to_previous == Relation.REFINES  # correct default for a genuinely new submission


# ============================================================================
# EM47-02: purge item_id must be a validated literal, no glob/wildcard
# ============================================================================

def test_em47_02_purge_rejects_glob_wildcard_item_id(memory):
    with pytest.raises(InvalidKnowledgeItemIdError):
        purge_knowledge_state(memory, "*", 1, purged_by="maintainer")


def test_em47_02_purge_rejects_path_traversal_item_id(memory):
    with pytest.raises(InvalidKnowledgeItemIdError):
        purge_knowledge_state(memory, "../../escape", 1, purged_by="maintainer")


def test_em47_02_wildcard_item_id_cannot_reach_a_real_item(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.real", KnowledgeType.PRODUCT, "desktop.filters")
    memory.propose_state(item.id, "real content", [_evidence(memory).id])

    with pytest.raises(InvalidKnowledgeItemIdError):
        purge_knowledge_state(memory, f"{item.id[:3]}*", 1, purged_by="maintainer")

    # the real item is completely untouched - the rejection happened before any disk access
    reloaded = memory.get_knowledge_item(item.id)
    assert reloaded.states[0].content == "real content"


def test_em47_02_bracket_and_question_mark_wildcards_rejected(memory):
    for bad_id in ["item?", "item[0-9]", "it[em]"]:
        with pytest.raises(InvalidKnowledgeItemIdError):
            purge_knowledge_state(memory, bad_id, 1, purged_by="maintainer")


# ============================================================================
# EM47-03: new state version = max(existing) + 1, unique after purge + reload
# ============================================================================

def test_em47_03_new_version_unique_after_interior_full_removal_purge(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.gap", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = memory.propose_state(item.id, "v1", [_evidence(memory, "e1.png").id])
    memory.approve_state(item.id, v1.version, approved_by="maintainer")
    v2 = memory.propose_state(item.id, "v2", [_evidence(memory, "e2.png").id])
    memory.invalidate_state(item.id, v2.version, invalidated_by="maintainer", reason="bad")
    v3 = memory.propose_state(item.id, "v3", [_evidence(memory, "e3.png").id])

    purge_knowledge_state(memory, item.id, v2.version, purged_by="maintainer", tombstone=False)
    reloaded = memory.get_knowledge_item(item.id)
    assert [s.version for s in reloaded.states] == [1, 3]

    v4 = memory.propose_state(item.id, "v4", [_evidence(memory, "e4.png").id])
    assert v4.version == 4  # not 3 (len(states)+1 after removal would collide with v3)

    all_versions = [s.version for s in memory.get_knowledge_item(item.id).states]
    assert len(all_versions) == len(set(all_versions))  # no duplicate version numbers


def test_em47_03_new_version_unique_after_highest_version_full_removal_purge(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.tail", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = memory.propose_state(item.id, "v1", [_evidence(memory, "e1.png").id])
    memory.approve_state(item.id, v1.version, approved_by="maintainer")
    v2 = memory.propose_state(item.id, "v2 bad", [_evidence(memory, "e2.png").id])

    purge_knowledge_state(memory, item.id, v2.version, purged_by="maintainer", tombstone=False)
    assert [s.version for s in memory.get_knowledge_item(item.id).states] == [1]

    # version 2 is now genuinely free (nothing in states carries it anymore), so
    # max(existing)+1 correctly reassigns it - EM47-03 requires uniqueness among
    # what's actually present, not a monotonically-ever-increasing counter
    v3 = memory.propose_state(item.id, "v3", [_evidence(memory, "e3.png").id])
    assert v3.version == 2
    all_versions = [s.version for s in memory.get_knowledge_item(item.id).states]
    assert len(all_versions) == len(set(all_versions))


def test_em47_03_version_uniqueness_survives_reload(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    item = m1.get_or_create_knowledge_item("desktop.filters.reload-gap", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = m1.propose_state(item.id, "v1", [m1.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="e1.png", captured_by="maintainer").id])
    m1.approve_state(item.id, v1.version, approved_by="maintainer")
    v2 = m1.propose_state(item.id, "v2", [m1.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="e2.png", captured_by="maintainer").id])
    purge_knowledge_state(m1, item.id, v2.version, purged_by="maintainer", tombstone=False)

    m2 = EditorialMemory(root)
    v3 = m2.propose_state(item.id, "v3", [m2.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="e3.png", captured_by="maintainer").id])
    assert v3.version == 2  # version 2 was fully removed, so it's genuinely free again
    versions = [s.version for s in m2.get_knowledge_item(item.id).states]
    assert len(versions) == len(set(versions))


# ============================================================================
# EM47-04: tombstoned KnowledgeState must never remain current/retrievable
# as truth; blank purged_by rejected; attribution preserved without a
# schema change
# ============================================================================

def test_em47_04_purging_current_state_removes_it_from_current_retrieval(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.live", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = memory.propose_state(item.id, "sensitive content", [_evidence(memory).id])
    memory.approve_state(item.id, v1.version, approved_by="maintainer")
    assert get_current_by_key(memory, item.key) is not None  # sanity: it really was current

    purge_knowledge_state(memory, item.id, v1.version, purged_by="maintainer", reason="PII")

    assert get_current_by_key(memory, item.key) is None
    assert memory.get_current(item.id) is None
    # revised for finding 5: a purged state is fully removed, not left behind
    # in any redacted/status-flipped form
    reloaded = memory.get_knowledge_item(item.id)
    assert reloaded.states == []


def test_em47_04_purging_proposed_state_removes_it_from_review_queue(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.pending", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "sensitive draft", [_evidence(memory).id])
    assert len(list_pending_review(memory, feature_area="desktop.filters")) == 1

    purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="PII")

    assert list_pending_review(memory, feature_area="desktop.filters") == []


def test_em47_04_blank_purged_by_rejected_for_knowledge_state(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.blank", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])

    for bad in ["", "   ", None]:
        with pytest.raises(MissingPurgeAuthorizationError):
            purge_knowledge_state(memory, item.id, p.version, purged_by=bad)

    # zero side effects - the state is completely untouched by any rejected attempt
    reloaded = memory.get_knowledge_item(item.id)
    assert reloaded.states[0].content == "content"
    assert reloaded.states[0].status == StateStatus.PROPOSED


def test_em47_04_blank_purged_by_rejected_for_evidence(memory):
    ev = _evidence(memory)
    for bad in ["", "   ", None]:
        with pytest.raises(MissingPurgeAuthorizationError):
            purge_evidence(memory, ev.id, purged_by=bad)

    assert memory.get_evidence(ev.id).source_ref == "e.png"  # untouched


# revised for finding 5: attribution/reason are preserved via the canonical
# {id, purged_at, purged_by, reason} tombstone contract, not by reusing
# invalidated_by/invalidated_at/invalidation_reason on a redacted-in-place state
def test_em47_04_attribution_and_reason_preserved_via_canonical_tombstone(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.attrib", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "sensitive content", [_evidence(memory).id])

    stub = purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer-x", reason="contained a home address")

    assert stub.purged_by == "maintainer-x"
    assert stub.reason == "contained a home address"
    assert stub.purged_at is not None
    # the purged state itself is gone from every normal query path - the tombstone
    # carries attribution *instead of*, not alongside, any surviving claim content
    assert get_invalidated_by_key(memory, item.key) == []
    assert memory.get_knowledge_item(item.id).states == []


def test_em47_04_purge_of_already_invalidated_state_is_still_authorization_checked(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.dbl", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "bad claim", [_evidence(memory).id])
    memory.invalidate_state(item.id, p.version, invalidated_by="maintainer", reason="wrong")

    with pytest.raises(MissingPurgeAuthorizationError):
        purge_knowledge_state(memory, item.id, p.version, purged_by="")

    # zero side effects from the rejected attempt - the invalidated state is
    # still there, still invalidated, not purged by the failed call
    assert len(get_invalidated_by_key(memory, item.key)) == 1

    stub = purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="PII found later")
    assert stub.reason == "PII found later"
    assert get_invalidated_by_key(memory, item.key) == []  # gone now that purge actually ran


# ============================================================================
# EM47-05: a tombstoned/malformed Evidence record must surface as a typed
# Editorial Memory provenance failure, never a raw KeyError
# ============================================================================

def test_em47_05_get_evidence_on_tombstoned_record_raises_typed_error_not_keyerror(memory):
    ev = _evidence(memory)
    purge_evidence(memory, ev.id, purged_by="maintainer")

    with pytest.raises(CorruptEvidenceRecordError):
        memory.get_evidence(ev.id)


def test_em47_05_get_current_on_state_citing_tombstoned_evidence_chains_typed_errors(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.chain", KnowledgeType.PRODUCT, "desktop.filters")
    ev = _evidence(memory)
    p = memory.propose_state(item.id, "claim", [ev.id])
    memory.approve_state(item.id, p.version, approved_by="maintainer")

    purge_evidence(memory, ev.id, purged_by="maintainer", tombstone=True)

    with pytest.raises(CorruptProvenanceError) as excinfo:
        memory.get_current(item.id)
    # full typed chain: CorruptProvenanceError <- CorruptEvidenceRecordError <- KeyError
    assert isinstance(excinfo.value.__cause__, CorruptEvidenceRecordError)
    assert isinstance(excinfo.value.__cause__.__cause__, KeyError)


def test_em47_05_no_raw_keyerror_reaches_the_caller_anywhere(memory):
    ev = _evidence(memory)
    purge_evidence(memory, ev.id, purged_by="maintainer")

    try:
        memory.get_evidence(ev.id)
        assert False, "expected an exception"
    except KeyError:
        pytest.fail("a raw KeyError leaked past the typed Editorial Memory error boundary")
    except CorruptEvidenceRecordError:
        pass  # expected
