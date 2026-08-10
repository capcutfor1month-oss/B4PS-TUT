"""Proof tests for Editorial Memory Slice 5 - review queue.

Kept in its own file: this slice adds no lifecycle, no mutation, and no
new status - only `lib.review`'s deterministic retrieval over Slice 1's
existing `get_pending`/`get_conflicts`/`review_required`. Approval and
rejection themselves are exercised via the unchanged
`EditorialMemory.approve_state`/`invalidate_state`, already proven by
`test_editorial_memory.py`; this file proves the queue view is correct,
not the underlying lifecycle again.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from lib import EditorialMemory, EvidenceType, KnowledgeType, Relation, StateStatus
from lib.review import list_conflicts, list_pending_review


@pytest.fixture
def memory(tmp_path):
    return EditorialMemory(tmp_path / "store")


def _evidence(memory, ref="Source/Desktop/Screenshots/filters.png"):
    return memory.record_evidence(evidence_type=EvidenceType.SCREENSHOT, source_ref=ref, captured_by="maintainer")


def _proposed_item(memory, key="desktop.filters.button-label", feature_area="desktop.filters",
                    knowledge_type=KnowledgeType.PRODUCT, content="maybe the button says 'Filters'"):
    item = memory.get_or_create_knowledge_item(key, knowledge_type, feature_area)
    ev = _evidence(memory)
    memory.propose_state(item.id, content, [ev.id])
    return item


# S5-01: a fresh proposal appears in the pending-review queue
def test_s5_01_fresh_proposal_appears_in_pending_queue(memory):
    item = _proposed_item(memory)
    pending = list_pending_review(memory)
    assert len(pending) == 1
    assert pending[0].id == item.id
    assert pending[0].key == item.key
    assert pending[0].review_required is False  # NEW relation, not a contradiction


# S5-02: review-required (unresolved contradiction) is distinct from a plain pending proposal
def test_s5_02_contradiction_is_flagged_review_required(memory):
    item, _ = _approved_then_contradicted(memory)
    pending = list_pending_review(memory)
    assert len(pending) == 1
    assert pending[0].review_required is True


def _approved_then_contradicted(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.a", KnowledgeType.PRODUCT, "desktop.filters")
    ev1 = _evidence(memory, "Source/Desktop/Screenshots/filters_v1.png")
    p1 = memory.propose_state(item.id, "says Filters", [ev1.id])
    memory.approve_state(item.id, p1.version, approved_by="maintainer")

    ev2 = _evidence(memory, "Source/Desktop/Screenshots/filters_v2.png")
    memory.propose_state(item.id, "says Filter", [ev2.id], relation_to_previous=Relation.CONTRADICTS)
    return item, ev2


# S5-03: current (approved) knowledge is never returned by the review queue
def test_s5_03_current_knowledge_excluded_from_pending_queue(memory):
    item, _ = _approved_then_contradicted(memory)
    pending = list_pending_review(memory)
    # only the contradicting v2 proposal is pending - v1 is current, not proposed
    assert [p.version for p in pending] == [2]


# S5-04: list_conflicts returns only review-required items, list_pending_review returns all proposed
def test_s5_04_list_conflicts_is_the_review_required_subset(memory):
    _proposed_item(memory, key="desktop.filters.plain", content="plain new proposal")
    _approved_then_contradicted(memory)  # contributes one review_required=True pending item

    all_pending = list_pending_review(memory)
    conflicts = list_conflicts(memory)
    assert len(all_pending) == 2
    assert len(conflicts) == 1
    assert conflicts[0].review_required is True


# S5-05: filtering by feature_area
def test_s5_05_filter_by_feature_area(memory):
    _proposed_item(memory, key="desktop.filters.a", feature_area="desktop.filters")
    _proposed_item(memory, key="desktop.members.a", feature_area="desktop.members")
    pending = list_pending_review(memory, feature_area="desktop.filters")
    assert [p.key for p in pending] == ["desktop.filters.a"]


# S5-06: filtering by knowledge_type
def test_s5_06_filter_by_knowledge_type(memory):
    _proposed_item(memory, key="desktop.filters.a", knowledge_type=KnowledgeType.PRODUCT)
    _proposed_item(memory, key="desktop.filters.b", knowledge_type=KnowledgeType.EDITORIAL)
    pending = list_pending_review(memory, knowledge_type=KnowledgeType.EDITORIAL)
    assert [p.key for p in pending] == ["desktop.filters.b"]


# S5-07: approving a pending item removes it from the queue (human decision via existing lifecycle)
def test_s5_07_approval_removes_item_from_queue(memory):
    item = _proposed_item(memory)
    state = memory.get_pending(item.id)[0]
    memory.approve_state(item.id, state.version, approved_by="maintainer")

    assert list_pending_review(memory) == []


# S5-08: rejecting (invalidating) a pending item removes it from the queue and never promotes it
def test_s5_08_rejection_via_invalidate_removes_item_from_queue(memory):
    item = _proposed_item(memory)
    state = memory.get_pending(item.id)[0]
    memory.invalidate_state(item.id, state.version, invalidated_by="maintainer", reason="not accurate")

    assert list_pending_review(memory) == []
    assert memory.get_current(item.id) is None


# S5-09: resolving a contradiction by approving the new proposal supersedes old current and clears the queue
def test_s5_09_resolving_contradiction_by_approval_supersedes_and_clears_queue(memory):
    item, _ = _approved_then_contradicted(memory)
    contradicting = list_conflicts(memory)[0]
    memory.approve_state(item.id, contradicting.version, approved_by="maintainer")

    assert list_pending_review(memory) == []
    current = memory.get_current(item.id)
    assert current.version == contradicting.version
    history = memory.get_history(item.id)
    assert history[0].status == StateStatus.SUPERSEDED


# S5-10: resolving a contradiction by rejecting it leaves the original current state intact
def test_s5_10_resolving_contradiction_by_rejection_preserves_original_current(memory):
    item, _ = _approved_then_contradicted(memory)
    contradicting = list_conflicts(memory)[0]
    memory.invalidate_state(item.id, contradicting.version, invalidated_by="maintainer", reason="unverified")

    assert list_pending_review(memory) == []
    current = memory.get_current(item.id)
    assert current.version == 1
    assert current.content == "says Filters"


# S5-11: deterministic ordering across reload
def test_s5_11_deterministic_ordering_across_reload(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    _proposed_item(m1, key="desktop.filters.b", feature_area="desktop.filters")
    _proposed_item(m1, key="desktop.filters.a", feature_area="desktop.filters")

    m2 = EditorialMemory(root)
    first = [p.key for p in list_pending_review(m1, feature_area="desktop.filters")]
    second = [p.key for p in list_pending_review(m2, feature_area="desktop.filters")]
    assert first == second == sorted(first)


# S5-12: invalidated knowledge never reappears in the review queue
def test_s5_12_invalidated_state_excluded_from_queue(memory):
    item = _proposed_item(memory)
    state = memory.get_pending(item.id)[0]
    memory.invalidate_state(item.id, state.version, invalidated_by="maintainer", reason="bad ingestion")
    assert list_pending_review(memory) == []
    assert list_conflicts(memory) == []


# S5-13: review queue never mutates memory
def test_s5_13_review_queue_never_mutates_store(memory):
    item, _ = _approved_then_contradicted(memory)
    before = memory.get_history(item.id)

    list_pending_review(memory)
    list_conflicts(memory)
    list_pending_review(memory, feature_area=item.feature_area)
    list_conflicts(memory, knowledge_type=item.knowledge_type)

    assert memory.get_history(item.id) == before


# S5-14: provenance/rationale/evidence_refs survive the queue view
def test_s5_14_provenance_and_rationale_survive(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.c", KnowledgeType.PRODUCT, "desktop.filters")
    ev = _evidence(memory)
    memory.propose_state(item.id, "content", [ev.id], rationale="why this claim exists")

    pending = list_pending_review(memory)[0]
    assert pending.evidence_refs == [ev.id]
    assert pending.rationale == "why this claim exists"
