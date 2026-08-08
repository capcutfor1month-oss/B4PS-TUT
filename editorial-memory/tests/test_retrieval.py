"""Proof tests for Editorial Memory Slice 3 - retrieval functions.

Exercises lib.retrieval against Slice 1/2's real lifecycle (propose /
approve / invalidate), not a mock - retrieval must respect whatever the
existing lifecycle actually did, not a simplified model of it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from lib import EditorialMemory, EvidenceType, KnowledgeType, Relation, StorageCorruptionError
from lib.retrieval import (
    get_current_by_key,
    get_history_by_key,
    list_current_by_feature_area,
    list_current_by_knowledge_type,
)


@pytest.fixture
def memory(tmp_path):
    return EditorialMemory(tmp_path / "store")


def _evidence(memory, ref="Source/Desktop/Screenshots/filters.png"):
    return memory.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT,
        source_ref=ref,
        captured_by="maintainer",
    )


def _approved_item(memory, key="desktop.filters.button-label", feature_area="desktop.filters",
                    knowledge_type=KnowledgeType.PRODUCT, content="Filters button says 'Filters'",
                    rationale="matches slide 148 template"):
    item = memory.get_or_create_knowledge_item(key, knowledge_type, feature_area)
    ev = _evidence(memory)
    proposed = memory.propose_state(item.id, content, [ev.id], rationale=rationale)
    memory.approve_state(item.id, proposed.version, approved_by="maintainer")
    return item, ev


# 1. retrieval by exact KnowledgeItem key returns the current approved state
def test_get_current_by_key_returns_current_state(memory):
    item, _ = _approved_item(memory)
    result = get_current_by_key(memory, item.key)
    assert result is not None
    assert result.id == item.id
    assert result.key == item.key
    assert result.content == "Filters button says 'Filters'"
    assert result.status == "current"


# 2. retrieval by feature area returns the correct current items
def test_list_current_by_feature_area(memory):
    _approved_item(memory, key="desktop.filters.a", feature_area="desktop.filters")
    _approved_item(memory, key="desktop.members.a", feature_area="desktop.members")
    results = list_current_by_feature_area(memory, "desktop.filters")
    assert [r.key for r in results] == ["desktop.filters.a"]


# 3. retrieval by knowledge type returns the correct current items
def test_list_current_by_knowledge_type(memory):
    _approved_item(memory, key="desktop.filters.a", knowledge_type=KnowledgeType.PRODUCT)
    _approved_item(memory, key="desktop.filters.b", feature_area="desktop.filters",
                    knowledge_type=KnowledgeType.EDITORIAL)
    results = list_current_by_knowledge_type(memory, KnowledgeType.EDITORIAL)
    assert [r.key for r in results] == ["desktop.filters.b"]


# 4. superseded state is not returned as current
def test_superseded_state_excluded_from_current(memory):
    item, _ = _approved_item(memory)
    ev2 = _evidence(memory, "Source/Desktop/Screenshots/filters_v2.png")
    proposed2 = memory.propose_state(
        item.id, "Filters button now says 'Filter'", [ev2.id], relation_to_previous=Relation.SUPERSEDES
    )
    memory.approve_state(item.id, proposed2.version, approved_by="maintainer")

    result = get_current_by_key(memory, item.key)
    assert result.version == proposed2.version
    assert result.content == "Filters button now says 'Filter'"


# 5. proposed newer state does not displace current approved state
def test_proposed_state_does_not_displace_current(memory):
    item, _ = _approved_item(memory)
    ev2 = _evidence(memory, "Source/Desktop/Screenshots/filters_guess.png")
    memory.propose_state(item.id, "maybe it changed", [ev2.id], relation_to_previous=Relation.REFINES)

    result = get_current_by_key(memory, item.key)
    assert result.content == "Filters button says 'Filters'"
    assert result.version == 1


# 6. contradictory/review-required proposed state does not become current
def test_contradiction_does_not_become_current(memory):
    item, _ = _approved_item(memory)
    ev2 = _evidence(memory, "Source/Desktop/Screenshots/filters_conflict.png")
    memory.propose_state(item.id, "Filters button says 'Filter' now", [ev2.id],
                          relation_to_previous=Relation.CONTRADICTS)

    result = get_current_by_key(memory, item.key)
    assert result.content == "Filters button says 'Filters'"
    assert memory.has_pending_conflict(item.id) is True


# 7. invalidated knowledge is excluded from normal current retrieval
def test_invalidated_excluded_from_current(memory):
    item, _ = _approved_item(memory)
    memory.invalidate_state(item.id, version=1, invalidated_by="maintainer", reason="bad ingestion")

    assert get_current_by_key(memory, item.key) is None
    assert list_current_by_feature_area(memory, item.feature_area) == []


# 8. provenance/evidence references survive retrieval
def test_evidence_refs_survive_retrieval(memory):
    item, ev = _approved_item(memory)
    result = get_current_by_key(memory, item.key)
    assert result.evidence_refs == [ev.id]


# 9. rationale survives retrieval
def test_rationale_survives_retrieval(memory):
    item, _ = _approved_item(memory)
    result = get_current_by_key(memory, item.key)
    assert result.rationale == "matches slide 148 template"


# 10. approval metadata survives retrieval
def test_approval_metadata_survives_retrieval(memory):
    item, _ = _approved_item(memory)
    result = get_current_by_key(memory, item.key)
    assert result.approved_by == "maintainer"
    assert result.approved_at is not None
    assert result.created_at is not None


# 11. explicit history retrieval returns complete ordered lifecycle history
def test_history_retrieval_ordered_and_complete(memory):
    item, _ = _approved_item(memory)
    ev2 = _evidence(memory, "Source/Desktop/Screenshots/filters_v2.png")
    proposed2 = memory.propose_state(
        item.id, "Filters button now says 'Filter'", [ev2.id], relation_to_previous=Relation.SUPERSEDES
    )
    memory.approve_state(item.id, proposed2.version, approved_by="maintainer")

    history = get_history_by_key(memory, item.key)
    assert [s.version for s in history] == [1, 2]
    assert history[0].status.value == "superseded"
    assert history[1].status.value == "current"


# 12. deterministic ordering across reload
def test_deterministic_ordering_across_reload(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    _approved_item(m1, key="desktop.filters.b", feature_area="desktop.filters")
    _approved_item(m1, key="desktop.filters.a", feature_area="desktop.filters")

    m2 = EditorialMemory(root)  # fresh instance, forces a real reload from disk
    first = [r.key for r in list_current_by_feature_area(m1, "desktop.filters")]
    second = [r.key for r in list_current_by_feature_area(m2, "desktop.filters")]
    assert first == second == sorted(first)


# --- S3-01 adversarial tests: invalidated states excluded from get_history_by_key ---

# S3-01.1: approved -> invalidated state is absent from get_history_by_key()
def test_history_excludes_invalidated_state(memory):
    item, _ = _approved_item(memory)
    memory.invalidate_state(item.id, version=1, invalidated_by="maintainer", reason="bad ingestion")

    history = get_history_by_key(memory, item.key)
    assert history == []
    # the raw, unfiltered lifecycle history still has it - proves this is a
    # retrieval-layer filter, not a change to Slice 1's own get_history.
    raw = memory.get_history(item.id)
    assert [s.status.value for s in raw] == ["invalidated"]


# S3-01.2: mixed history with current/superseded/invalidated excludes only invalidated
def test_history_excludes_only_invalidated_from_mixed_history(memory):
    item, _ = _approved_item(memory)  # v1: current

    ev2 = _evidence(memory, "Source/Desktop/Screenshots/filters_v2.png")
    proposed2 = memory.propose_state(
        item.id, "Filters button now says 'Filter'", [ev2.id], relation_to_previous=Relation.SUPERSEDES
    )
    memory.approve_state(item.id, proposed2.version, approved_by="maintainer")  # v1 -> superseded, v2: current

    ev3 = _evidence(memory, "Source/Desktop/Screenshots/filters_bad.png")
    proposed3 = memory.propose_state(item.id, "hallucinated claim", [ev3.id], relation_to_previous=Relation.REFINES)
    memory.invalidate_state(item.id, version=proposed3.version, invalidated_by="maintainer",
                             reason="hallucinated")  # v3: invalidated, does not touch v2's current status

    raw = memory.get_history(item.id)
    assert [s.status.value for s in raw] == ["superseded", "current", "invalidated"]

    history = get_history_by_key(memory, item.key)
    assert [s.version for s in history] == [1, 2]
    assert [s.status.value for s in history] == ["superseded", "current"]


# S3-01.3: ordering of remaining history stays deterministic
def test_history_ordering_deterministic_after_invalidation_filter(memory):
    item, _ = _approved_item(memory)
    for i in range(2, 5):
        ev = _evidence(memory, f"Source/Desktop/Screenshots/filters_v{i}.png")
        proposed = memory.propose_state(
            item.id, f"version {i} content", [ev.id], relation_to_previous=Relation.SUPERSEDES
        )
        memory.approve_state(item.id, proposed.version, approved_by="maintainer")

    # invalidate an interior, non-terminal state (not first, not last)
    memory.invalidate_state(item.id, version=2, invalidated_by="maintainer", reason="turned out wrong")

    history_a = get_history_by_key(memory, item.key)
    history_b = get_history_by_key(memory, item.key)
    assert [s.version for s in history_a] == [1, 3, 4]  # oldest -> newest, gap where v2 was filtered
    assert [s.version for s in history_b] == [1, 3, 4]  # repeated call, same order


# S3-01.4: behavior survives reload
def test_history_invalidation_filter_survives_reload(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    item, _ = _approved_item(m1)
    m1.invalidate_state(item.id, version=1, invalidated_by="maintainer", reason="bad ingestion")

    m2 = EditorialMemory(root)  # fresh instance, forces a real reload from disk
    assert get_history_by_key(m2, item.key) == []


# 13. malformed/corrupt persisted records fail safely through existing typed errors
def test_corrupt_record_raises_typed_error(memory, tmp_path):
    item, _ = _approved_item(memory)
    path = tmp_path / "store" / "knowledge" / item.feature_area / f"{item.id}.json"
    path.write_text("{not valid json")

    with pytest.raises(StorageCorruptionError):
        get_current_by_key(memory, item.key)


# unknown key / no current state both resolve to None, not an error
def test_unknown_key_returns_none(memory):
    assert get_current_by_key(memory, "no.such.key") is None
    assert get_history_by_key(memory, "no.such.key") is None


def test_item_with_only_proposed_state_has_no_current(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.new", KnowledgeType.PRODUCT, "desktop.filters")
    ev = _evidence(memory)
    memory.propose_state(item.id, "not yet approved", [ev.id])

    assert get_current_by_key(memory, item.key) is None
    assert list_current_by_feature_area(memory, "desktop.filters") == []


def test_retrieval_never_mutates_store(memory):
    item, _ = _approved_item(memory)
    before = memory.get_history(item.id)

    get_current_by_key(memory, item.key)
    list_current_by_feature_area(memory, item.feature_area)
    list_current_by_knowledge_type(memory, item.knowledge_type)
    get_history_by_key(memory, item.key)

    after = memory.get_history(item.id)
    assert before == after
