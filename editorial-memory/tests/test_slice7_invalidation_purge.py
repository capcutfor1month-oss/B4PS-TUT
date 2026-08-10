"""Proof tests for Editorial Memory Slice 7 - invalidated-knowledge audit
access and bounded, human-authorized purge.

Kept in its own file: this slice adds a dedicated audit query for
`invalidated` states (never exposed by Slice 3/5's normal-path retrieval)
and a narrow, storage-level purge operation that sits outside the normal
evolution flow entirely. Neither touches Slice 1's lifecycle mechanism
(`invalidate_state` itself is unchanged and already proven by
`test_editorial_memory.py`); this file proves the new audit/purge surface.
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
    InvalidEvidenceIdError,
    InvalidKnowledgeItemIdError,
    KnowledgeType,
    MissingPurgeAuthorizationError,
    StateStatus,
    UnknownEvidenceError,
    UnknownKnowledgeItemError,
    UnknownStateVersionError,
)
from lib.purge import (
    get_invalidated_by_key,
    list_invalidated_by_feature_area,
    list_invalidated_by_knowledge_type,
    purge_evidence,
    purge_knowledge_state,
)
from lib.retrieval import get_current_by_key, get_history_by_key
from lib.review import list_pending_review


@pytest.fixture
def memory(tmp_path):
    return EditorialMemory(tmp_path / "store")


def _evidence(memory, ref="Source/Desktop/Screenshots/e.png"):
    return memory.record_evidence(evidence_type=EvidenceType.SCREENSHOT, source_ref=ref, captured_by="maintainer")


def _invalidated_item(memory, key="desktop.filters.bad-claim", feature_area="desktop.filters",
                       knowledge_type=KnowledgeType.PRODUCT, content="hallucinated claim"):
    item = memory.get_or_create_knowledge_item(key, knowledge_type, feature_area)
    ev = _evidence(memory)
    p = memory.propose_state(item.id, content, [ev.id])
    memory.invalidate_state(item.id, p.version, invalidated_by="maintainer", reason="bad ingestion")
    return item


# --- Invalidated-knowledge audit access ----------------------------------

# S7-01: invalidated knowledge is retrievable by key via the dedicated audit query
def test_s7_01_get_invalidated_by_key_returns_the_invalidated_state(memory):
    item = _invalidated_item(memory)
    invalidated = get_invalidated_by_key(memory, item.key)
    assert len(invalidated) == 1
    assert invalidated[0].content == "hallucinated claim"
    assert invalidated[0].invalidated_by == "maintainer"
    assert invalidated[0].invalidation_reason == "bad ingestion"


# S7-02: invalidated states never appear in Slice 3's current retrieval or Slice 5's review queue
def test_s7_02_invalidated_excluded_from_current_and_review_queue(memory):
    item = _invalidated_item(memory)
    assert get_current_by_key(memory, item.key) is None
    assert get_history_by_key(memory, item.key) == []  # S3-01: history excludes invalidated too
    assert list_pending_review(memory) == []


# S7-03: invalidated retrieval by feature_area / knowledge_type
def test_s7_03_filter_by_feature_area_and_knowledge_type(memory):
    _invalidated_item(memory, key="desktop.filters.a", feature_area="desktop.filters",
                       knowledge_type=KnowledgeType.PRODUCT)
    _invalidated_item(memory, key="desktop.members.a", feature_area="desktop.members",
                       knowledge_type=KnowledgeType.EDITORIAL)

    by_area = list_invalidated_by_feature_area(memory, "desktop.filters")
    assert [r.key for r in by_area] == ["desktop.filters.a"]

    by_type = list_invalidated_by_knowledge_type(memory, KnowledgeType.EDITORIAL)
    assert [r.key for r in by_type] == ["desktop.members.a"]


# S7-04: unknown key -> None (not an error); no invalidated states -> empty list
def test_s7_04_unknown_key_and_no_invalidated_states(memory):
    assert get_invalidated_by_key(memory, "no.such.key") is None

    item = memory.get_or_create_knowledge_item("desktop.filters.clean", KnowledgeType.PRODUCT, "desktop.filters")
    ev = _evidence(memory)
    p = memory.propose_state(item.id, "fine claim", [ev.id])
    memory.approve_state(item.id, p.version, approved_by="maintainer")
    assert get_invalidated_by_key(memory, item.key) == []


# S7-05: a mixed item's superseded/current states are NOT returned as invalidated
def test_s7_05_only_invalidated_status_returned_not_superseded_or_current(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.mixed", KnowledgeType.PRODUCT, "desktop.filters")
    ev1 = _evidence(memory, "e1.png")
    v1 = memory.propose_state(item.id, "v1", [ev1.id])
    memory.approve_state(item.id, v1.version, approved_by="maintainer")

    ev2 = _evidence(memory, "e2.png")
    v2 = memory.propose_state(item.id, "v2", [ev2.id])
    memory.approve_state(item.id, v2.version, approved_by="maintainer")  # v1 -> superseded, v2 -> current

    ev3 = _evidence(memory, "e3.png")
    v3 = memory.propose_state(item.id, "bad", [ev3.id])
    memory.invalidate_state(item.id, v3.version, invalidated_by="maintainer", reason="bad")

    invalidated = get_invalidated_by_key(memory, item.key)
    assert [s.version for s in invalidated] == [3]


# S7-06: deterministic ordering across reload
def test_s7_06_deterministic_ordering_across_reload(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    _invalidated_item(m1, key="desktop.filters.b", feature_area="desktop.filters")
    _invalidated_item(m1, key="desktop.filters.a", feature_area="desktop.filters")

    m2 = EditorialMemory(root)
    first = [r.key for r in list_invalidated_by_feature_area(m1, "desktop.filters")]
    second = [r.key for r in list_invalidated_by_feature_area(m2, "desktop.filters")]
    assert first == second == sorted(first)


# S7-07: audit queries never mutate memory
def test_s7_07_audit_queries_never_mutate_store(memory):
    item = _invalidated_item(memory)
    before = memory.get_knowledge_item(item.id)

    get_invalidated_by_key(memory, item.key)
    list_invalidated_by_feature_area(memory, item.feature_area)
    list_invalidated_by_knowledge_type(memory, item.knowledge_type)

    assert memory.get_knowledge_item(item.id) == before


# --- Bounded, human-authorized purge --------------------------------------

# S7-08: purge_evidence with tombstone (default) leaves a stub, not the original content
def test_s7_08_purge_evidence_tombstone_default(memory):
    ev = _evidence(memory, "Source/Desktop/Screenshots/sensitive.png")
    stub = purge_evidence(memory, ev.id, purged_by="maintainer", reason="contained an API key")

    assert stub.id == ev.id
    assert stub.purged_by == "maintainer"
    assert stub.reason == "contained an API key"
    # see test_s7_09 for proof the stub no longer parses as a real Evidence record


# S7-09 / EM47-05: after a tombstone purge, loading the record as Evidence fails
# typed (CorruptEvidenceRecordError), never a raw KeyError, and no fake data is returned
def test_s7_09_purged_evidence_stub_does_not_parse_as_a_real_evidence_record(memory):
    ev = _evidence(memory)
    purge_evidence(memory, ev.id, purged_by="maintainer")

    with pytest.raises(CorruptEvidenceRecordError) as excinfo:
        memory.get_evidence(ev.id)  # Evidence.from_dict requires evidence_type - the stub has none
    assert isinstance(excinfo.value.__cause__, KeyError)  # underlying cause still visible, not swallowed

    # but the raw stub is still readable directly via the store, proving the tombstone itself persisted
    raw = memory.store.load_evidence(ev.id)
    assert raw["purged_by"] == "maintainer"


# S7-10: purge_evidence with tombstone=False removes the file with no trace
def test_s7_10_purge_evidence_full_removal_leaves_no_trace(memory):
    ev = _evidence(memory)
    result = purge_evidence(memory, ev.id, purged_by="maintainer", tombstone=False)

    assert result is None
    assert memory.store.load_evidence(ev.id) is None
    assert ev.id not in memory.store.list_evidence_ids()


# S7-11: purging unknown Evidence raises typed UnknownEvidenceError, not a bare exception
def test_s7_11_purge_unknown_evidence_raises_typed_error(memory):
    with pytest.raises(UnknownEvidenceError):
        purge_evidence(memory, "ev-doesnotexist", purged_by="maintainer")


# S7-12: purge_evidence rejects an unsafe evidence_id the same way normal reads do (EM-04 reused)
def test_s7_12_purge_evidence_rejects_path_traversal_id(memory):
    with pytest.raises(InvalidEvidenceIdError):
        purge_evidence(memory, "../../escape", purged_by="maintainer")


# S7-13: purging evidence still cited by a current state surfaces loudly via CorruptProvenanceError,
# never silently - purge does not special-case or hide this, matching Slice 1's EM-01 protection
def test_s7_13_purging_evidence_behind_current_state_surfaces_via_corrupt_provenance(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.live", KnowledgeType.PRODUCT, "desktop.filters")
    ev = _evidence(memory)
    p = memory.propose_state(item.id, "current claim", [ev.id])
    memory.approve_state(item.id, p.version, approved_by="maintainer")

    purge_evidence(memory, ev.id, purged_by="maintainer", tombstone=False)

    with pytest.raises(CorruptProvenanceError):
        memory.get_current(item.id)


def _raw_state_entry(memory, item_id, version):
    """Test helper: the raw persisted entry for one version (real state
    or tombstone), read via the unfiltered accessor - `None` if there is
    no entry at all for that version."""
    raw = memory.store.load_knowledge_item_raw(item_id)
    for entry in raw["states"]:
        marker_id = entry.get("id", "")
        if "purged_at" in entry and marker_id == f"{item_id}#{version}":
            return entry
        if "purged_at" not in entry and entry.get("version") == version:
            return entry
    return None


# S7-14 (revised for round-3 finding 2): purge_knowledge_state replaces the
# entry *in place, at its existing array slot* with the canonical
# {id, purged_at, purged_by, reason} tombstone - the same canonical record
# location the real state occupied, never a separate file or directory.
def test_s7_14_purge_knowledge_state_replaces_entry_with_canonical_tombstone_in_place(memory):
    item = _invalidated_item(memory, content="a name and address that should never have been in here")
    invalidated = get_invalidated_by_key(memory, item.key)[0]

    stub = purge_knowledge_state(memory, item.id, invalidated.version, purged_by="maintainer", reason="PII")

    reloaded = memory.get_knowledge_item(item.id)
    assert reloaded.states == []  # invisible to every normal read path

    assert stub.id == f"{item.id}#{invalidated.version}"
    assert stub.purged_by == "maintainer"
    assert stub.reason == "PII"
    raw = _raw_state_entry(memory, item.id, invalidated.version)
    assert raw == {"id": stub.id, "purged_at": stub.purged_at, "purged_by": "maintainer", "reason": "PII"}
    assert set(raw.keys()) == {"id", "purged_at", "purged_by", "reason"}  # exactly the approved contract, nothing more
    # the tombstone lives in the SAME per-item file as everything else about this item -
    # no new top-level directory was created for it
    assert not (memory.store.root / "tombstones").exists()


# S7-15: purge_knowledge_state with tombstone=False removes the entry entirely;
# sibling states' versions/content are completely unaffected
def test_s7_15_purge_knowledge_state_full_removal_preserves_sibling_versions(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.multi", KnowledgeType.PRODUCT, "desktop.filters")
    ev1 = _evidence(memory, "e1.png")
    v1 = memory.propose_state(item.id, "v1 content", [ev1.id])
    memory.approve_state(item.id, v1.version, approved_by="maintainer")
    ev2 = _evidence(memory, "e2.png")
    v2 = memory.propose_state(item.id, "v2 bad content", [ev2.id])
    memory.invalidate_state(item.id, v2.version, invalidated_by="maintainer", reason="bad")
    ev3 = _evidence(memory, "e3.png")
    v3 = memory.propose_state(item.id, "v3 content", [ev3.id])

    result = purge_knowledge_state(memory, item.id, v2.version, purged_by="maintainer", tombstone=False)

    assert result is None  # no tombstone stub returned
    assert _raw_state_entry(memory, item.id, v2.version) is None  # and none persisted - fully gone
    reloaded = memory.get_knowledge_item(item.id)
    assert [s.version for s in reloaded.states] == [1, 3]
    assert reloaded.states[0].content == "v1 content"
    assert reloaded.states[1].content == "v3 content"
    assert memory.get_current(item.id).content == "v1 content"


# S7-16: purging an unknown KnowledgeItem/version raises typed errors, not bare exceptions
def test_s7_16_purge_knowledge_state_unknown_item_and_version_raise_typed_errors(memory):
    with pytest.raises(UnknownKnowledgeItemError):
        purge_knowledge_state(memory, "no-such-item", 1, purged_by="maintainer")

    item = _invalidated_item(memory)
    with pytest.raises(UnknownStateVersionError):
        purge_knowledge_state(memory, item.id, 99, purged_by="maintainer")


# S7-17: purge is never triggered by ordinary ingestion/approval/evolution - proven by
# absence: a full Slice 4/6 lifecycle run leaves every purge-only marker untouched
def test_s7_17_ordinary_lifecycle_never_invokes_purge(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.untouched", KnowledgeType.PRODUCT, "desktop.filters")
    ev = _evidence(memory)
    p = memory.propose_state(item.id, "content", [ev.id])
    memory.approve_state(item.id, p.version, approved_by="maintainer")
    memory.invalidate_state(item.id, p.version, invalidated_by="maintainer", reason="changed my mind")
    # nothing above called purge_evidence/purge_knowledge_state - the record is
    # still fully present, not tombstoned or removed
    assert memory.get_evidence(ev.id).source_ref is not None
    reloaded = memory.get_knowledge_item(item.id)
    assert reloaded.states[0].content == "content"  # not "[purged]"


# S7-18: purge and audit-retrieval survive a fresh reload identically
def test_s7_18_purge_and_audit_survive_reload(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    item = _invalidated_item(m1)
    invalidated = get_invalidated_by_key(m1, item.key)[0]
    purge_knowledge_state(m1, item.id, invalidated.version, purged_by="maintainer", reason="PII")

    m2 = EditorialMemory(root)
    # the purged state is gone from every normal query path, on a fresh instance too
    assert get_invalidated_by_key(m2, item.key) == []
    assert m2.get_knowledge_item(item.id).states == []
    # the tombstone itself persisted and is readable via a fresh instance
    raw = _raw_state_entry(m2, item.id, invalidated.version)
    assert raw["purged_by"] == "maintainer"
    assert raw["reason"] == "PII"
