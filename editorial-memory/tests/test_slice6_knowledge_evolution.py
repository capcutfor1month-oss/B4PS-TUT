"""Proof tests for Editorial Memory Slice 6 - knowledge evolution.

Slice 6 adds no new code: `propose_state`/`approve_state`/`invalidate_state`
and the `Relation`/`StateStatus` enums already fully implement confirm/
refine/contradict/supersede (Slice 1). What was missing was direct proof
that a real (non-bootstrap) evolution chain - including `Relation.CONFIRMS`,
never previously exercised anywhere in this suite - behaves correctly
end-to-end against an already-`current` item, using ordinary
`propose_state`/`approve_state` calls the way a real reviewer would drive
them, not only through the Slice 2/4 single-call bootstrap paths. This
file is that proof. Kept separate from `test_editorial_memory.py` so the
slice boundary (evolution *usage*, not evolution *mechanism*) is explicit.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from lib import EditorialMemory, EvidenceType, InvalidLifecycleTransitionError, KnowledgeType, Relation, StateStatus


@pytest.fixture
def memory(tmp_path):
    return EditorialMemory(tmp_path / "store")


def _evidence(memory, ref):
    return memory.record_evidence(evidence_type=EvidenceType.SCREENSHOT, source_ref=ref, captured_by="maintainer")


def _new_item(memory, key="desktop.filters.evolution", feature_area="desktop.filters"):
    return memory.get_or_create_knowledge_item(key, KnowledgeType.PRODUCT, feature_area)


# S6-01: CONFIRMS - new evidence agrees, content unchanged, but a new version is
# still recorded as a freshness signal and still requires explicit approval
def test_s6_01_confirms_records_new_version_with_unchanged_content(memory):
    item = _new_item(memory)
    ev1 = _evidence(memory, "Source/Desktop/Screenshots/filters_2026-01.png")
    p1 = memory.propose_state(item.id, "Filters button says 'Filters'", [ev1.id])
    memory.approve_state(item.id, p1.version, approved_by="maintainer")

    ev2 = _evidence(memory, "Source/Desktop/Screenshots/filters_2026-06.png")
    p2 = memory.propose_state(
        item.id, "Filters button says 'Filters'", [ev2.id], relation_to_previous=Relation.CONFIRMS
    )
    assert p2.content == p1.content
    assert p2.version == p1.version + 1
    assert p2.status == StateStatus.PROPOSED  # confirming does not auto-promote

    memory.approve_state(item.id, p2.version, approved_by="maintainer")
    current = memory.get_current(item.id)
    assert current.version == p2.version
    assert current.relation_to_previous == Relation.CONFIRMS
    history = memory.get_history(item.id)
    assert history[0].status == StateStatus.SUPERSEDED
    assert history[0].superseded_by == p2.version


# S6-02: REFINES - adds detail without conflicting, still requires approval
def test_s6_02_refines_adds_detail_without_auto_promotion(memory):
    item = _new_item(memory)
    ev1 = _evidence(memory, "Source/Desktop/Screenshots/filters_basic.png")
    p1 = memory.propose_state(item.id, "Filters button opens a sidebar", [ev1.id])
    memory.approve_state(item.id, p1.version, approved_by="maintainer")

    ev2 = _evidence(memory, "Source/Desktop/Screenshots/filters_detail.png")
    p2 = memory.propose_state(
        item.id, "Filters button opens a sidebar, scoped per-workspace", [ev2.id],
        relation_to_previous=Relation.REFINES,
    )
    assert p2.status == StateStatus.PROPOSED
    assert memory.get_current(item.id).version == p1.version  # unchanged until approved

    memory.approve_state(item.id, p2.version, approved_by="maintainer")
    assert memory.get_current(item.id).version == p2.version


# S6-03: CONTRADICTS never overwrites current - the single most important evolution rule
def test_s6_03_contradicts_never_overwrites_current(memory):
    item = _new_item(memory)
    ev1 = _evidence(memory, "Source/Desktop/Screenshots/filters_v1.png")
    p1 = memory.propose_state(item.id, "says Filters", [ev1.id])
    memory.approve_state(item.id, p1.version, approved_by="maintainer")

    ev2 = _evidence(memory, "Source/Desktop/Screenshots/filters_v2.png")
    p2 = memory.propose_state(item.id, "says Filter", [ev2.id], relation_to_previous=Relation.CONTRADICTS)

    assert p2.status == StateStatus.PROPOSED
    assert p2.review_required is True
    current = memory.get_current(item.id)
    assert current.version == p1.version
    assert current.content == "says Filters"
    assert memory.has_pending_conflict(item.id) is True


# S6-04: SUPERSEDES - a maintainer resolves a contradiction, or the product genuinely
# moved on; old state becomes superseded (never deleted), new state becomes current
def test_s6_04_supersedes_moves_old_current_to_superseded_not_deleted(memory):
    item = _new_item(memory)
    ev1 = _evidence(memory, "Source/Desktop/Screenshots/filters_old.png")
    p1 = memory.propose_state(item.id, "old layout", [ev1.id])
    memory.approve_state(item.id, p1.version, approved_by="maintainer")

    ev2 = _evidence(memory, "Source/Desktop/Screenshots/filters_new.png")
    p2 = memory.propose_state(item.id, "new layout", [ev2.id], relation_to_previous=Relation.SUPERSEDES)
    memory.approve_state(item.id, p2.version, approved_by="maintainer")

    history = memory.get_history(item.id)
    assert [s.status for s in history] == [StateStatus.SUPERSEDED, StateStatus.CURRENT]
    assert history[0].content == "old layout"  # not deleted, not edited
    assert history[0].superseded_by == p2.version


# S6-05: a contradiction resolved via supersession - the full confirm→refine→
# contradict→supersede chain in one run, against a real (non-bootstrap) item
def test_s6_05_full_evolution_chain_confirm_refine_contradict_supersede(memory):
    item = _new_item(memory)

    ev1 = _evidence(memory, "Source/Desktop/Screenshots/e1.png")
    v1 = memory.propose_state(item.id, "v1 content", [ev1.id], relation_to_previous=Relation.NEW)
    memory.approve_state(item.id, v1.version, approved_by="maintainer")

    ev2 = _evidence(memory, "Source/Desktop/Screenshots/e2.png")
    v2 = memory.propose_state(item.id, "v1 content", [ev2.id], relation_to_previous=Relation.CONFIRMS)
    memory.approve_state(item.id, v2.version, approved_by="maintainer")

    ev3 = _evidence(memory, "Source/Desktop/Screenshots/e3.png")
    v3 = memory.propose_state(item.id, "v1 content, plus detail", [ev3.id], relation_to_previous=Relation.REFINES)
    memory.approve_state(item.id, v3.version, approved_by="maintainer")

    ev4 = _evidence(memory, "Source/Desktop/Screenshots/e4.png")
    v4 = memory.propose_state(item.id, "conflicting claim", [ev4.id], relation_to_previous=Relation.CONTRADICTS)
    assert memory.get_current(item.id).version == v3.version  # untouched while unresolved

    ev5 = _evidence(memory, "Source/Desktop/Screenshots/e5.png")
    v5 = memory.propose_state(
        item.id, "resolved: product genuinely changed", [ev5.id], relation_to_previous=Relation.SUPERSEDES
    )
    memory.approve_state(item.id, v5.version, approved_by="maintainer")

    current = memory.get_current(item.id)
    assert current.version == v5.version
    assert current.content == "resolved: product genuinely changed"

    history = memory.get_history(item.id)
    assert [s.version for s in history] == [1, 2, 3, 4, 5]
    assert [s.status for s in history] == [
        StateStatus.SUPERSEDED, StateStatus.SUPERSEDED, StateStatus.SUPERSEDED,
        StateStatus.PROPOSED,  # v4's contradiction was never resolved - still visible, still proposed
        StateStatus.CURRENT,
    ]
    assert history[3].review_required is True  # unresolved contradiction remains flagged in history too
    for state in history:
        assert len(state.evidence_refs) == 1  # provenance intact for every step


# S6-06: current truth is determined by explicit approval, never by "newest version number"
def test_s6_06_current_determined_by_approval_not_newest_version(memory):
    item = _new_item(memory)
    ev1 = _evidence(memory, "Source/Desktop/Screenshots/e1.png")
    v1 = memory.propose_state(item.id, "v1", [ev1.id])
    memory.approve_state(item.id, v1.version, approved_by="maintainer")

    ev2 = _evidence(memory, "Source/Desktop/Screenshots/e2.png")
    memory.propose_state(item.id, "v2 unreviewed", [ev2.id], relation_to_previous=Relation.REFINES)
    ev3 = _evidence(memory, "Source/Desktop/Screenshots/e3.png")
    memory.propose_state(item.id, "v3 also unreviewed", [ev3.id], relation_to_previous=Relation.REFINES)

    # two newer proposals exist (versions 2 and 3), but neither has been approved
    current = memory.get_current(item.id)
    assert current.version == 1
    assert current.content == "v1"


# S6-07: re-approving an already-current or already-superseded state is rejected -
# a lifecycle invariant that must survive real (non-bootstrap) evolution too
def test_s6_07_invalid_lifecycle_transitions_rejected_during_evolution(memory):
    item = _new_item(memory)
    ev1 = _evidence(memory, "Source/Desktop/Screenshots/e1.png")
    v1 = memory.propose_state(item.id, "v1", [ev1.id])
    memory.approve_state(item.id, v1.version, approved_by="maintainer")

    with pytest.raises(InvalidLifecycleTransitionError):
        memory.approve_state(item.id, v1.version, approved_by="someone-else")

    ev2 = _evidence(memory, "Source/Desktop/Screenshots/e2.png")
    v2 = memory.propose_state(item.id, "v2", [ev2.id], relation_to_previous=Relation.SUPERSEDES)
    memory.approve_state(item.id, v2.version, approved_by="maintainer")

    with pytest.raises(InvalidLifecycleTransitionError):
        memory.approve_state(item.id, v1.version, approved_by="maintainer")  # v1 is now superseded


# S6-08: evolution history round-trips identically across a fresh reload
def test_s6_08_evolution_history_survives_reload(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    item = _new_item(m1)
    ev1 = m1.record_evidence(evidence_type=EvidenceType.SCREENSHOT, source_ref="e1.png", captured_by="maintainer")
    v1 = m1.propose_state(item.id, "v1", [ev1.id])
    m1.approve_state(item.id, v1.version, approved_by="maintainer")
    ev2 = m1.record_evidence(evidence_type=EvidenceType.SCREENSHOT, source_ref="e2.png", captured_by="maintainer")
    v2 = m1.propose_state(item.id, "v2", [ev2.id], relation_to_previous=Relation.SUPERSEDES)
    m1.approve_state(item.id, v2.version, approved_by="maintainer")

    m2 = EditorialMemory(root)
    assert m2.get_history(item.id) == m1.get_history(item.id)
    assert m2.get_current(item.id) == m1.get_current(item.id)
