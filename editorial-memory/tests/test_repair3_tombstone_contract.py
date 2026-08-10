"""Adversarial regression tests for the third Slices 4-7 audit repair
round: tombstone version reuse, the canonical in-place tombstone storage
contract (no new directory), and purge write atomicity.

Each section proves the specific defect its finding describes - not a
general re-test of purge (that already exists in
`test_slice7_invalidation_purge.py`/`test_repair2_purge_and_dedup.py`).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from lib import EditorialMemory, EvidenceType, KnowledgeType, Relation, UnknownStateVersionError
from lib.purge import get_invalidated_by_key, purge_knowledge_state
from lib.retrieval import get_current_by_key


@pytest.fixture
def memory(tmp_path):
    return EditorialMemory(tmp_path / "store")


def _evidence(memory, ref="e.png"):
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
# Finding 1: version allocation must never reuse a version while its
# tombstone still exists
# ============================================================================

def test_tombstone_live_version_collision_never_happens(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.tv1", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = memory.propose_state(item.id, "v1", [_evidence(memory, "e1.png").id])

    purge_knowledge_state(memory, item.id, v1.version, purged_by="maintainer", reason="test")  # v1 tombstoned

    v2 = memory.propose_state(item.id, "v2", [_evidence(memory, "e2.png").id])
    assert v2.version == 2  # never reuses 1 - its tombstone still exists

    # the tombstone and the new live state must never collide at the same version
    tombstone = _raw_state_entry(memory, item.id, 1)
    live = memory.get_knowledge_item(item.id).states[0]
    assert "purged_at" in tombstone
    assert live.version == 2
    assert tombstone["id"] == f"{item.id}#1"


def test_tombstone_version_never_reused_even_after_several_more_purges(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.tv2", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = memory.propose_state(item.id, "v1", [_evidence(memory, "e1.png").id])
    purge_knowledge_state(memory, item.id, v1.version, purged_by="maintainer")  # tombstone v1

    v2 = memory.propose_state(item.id, "v2", [_evidence(memory, "e2.png").id])
    purge_knowledge_state(memory, item.id, v2.version, purged_by="maintainer")  # tombstone v2

    v3 = memory.propose_state(item.id, "v3", [_evidence(memory, "e3.png").id])
    assert v3.version == 3  # not 1, not 2 - both tombstones still hold their identities

    raw = memory.store.load_knowledge_item_raw(item.id)
    assert len(raw["states"]) == 3  # two tombstones + one live state, no collision, none silently dropped


# ============================================================================
# Reload behavior
# ============================================================================

def test_reload_after_tombstone_preserves_version_uniqueness(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    item = m1.get_or_create_knowledge_item("desktop.filters.tv-reload", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = m1.propose_state(item.id, "v1", [m1.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="e1.png", captured_by="maintainer").id])
    purge_knowledge_state(m1, item.id, v1.version, purged_by="maintainer")

    m2 = EditorialMemory(root)  # fresh instance, forces a real reload from disk
    v2 = m2.propose_state(item.id, "v2", [m2.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="e2.png", captured_by="maintainer").id])
    assert v2.version == 2  # the reloaded instance still respects the retained tombstone

    tombstone = _raw_state_entry(m2, item.id, 1)
    assert "purged_at" in tombstone
    assert m2.get_knowledge_item(item.id).states[0].version == 2


def test_reload_shows_identical_tombstone_and_live_state_view(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    item = m1.get_or_create_knowledge_item("desktop.filters.tv-reload2", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = m1.propose_state(item.id, "v1", [m1.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="e1.png", captured_by="maintainer").id])
    stub = purge_knowledge_state(m1, item.id, v1.version, purged_by="maintainer", reason="reload check")

    m2 = EditorialMemory(root)
    reloaded_tombstone = _raw_state_entry(m2, item.id, v1.version)
    assert reloaded_tombstone["purged_by"] == stub.purged_by
    assert reloaded_tombstone["reason"] == stub.reason
    assert reloaded_tombstone["purged_at"] == stub.purged_at
    assert m2.get_knowledge_item(item.id).states == []  # still invisible on a fresh instance


# ============================================================================
# Re-purge identity safety
# ============================================================================

def test_repurging_an_already_tombstoned_version_is_rejected(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.repurge", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])
    purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="first purge")

    with pytest.raises(UnknownStateVersionError):
        purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="second purge attempt")

    # the original tombstone (first purge's attribution) is untouched by the rejected second attempt
    tombstone = _raw_state_entry(memory, item.id, p.version)
    assert tombstone["reason"] == "first purge"


def test_repurging_after_full_removal_is_also_rejected(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.repurge2", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])
    purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", tombstone=False)

    with pytest.raises(UnknownStateVersionError):
        purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer")


# ============================================================================
# Finding 3: tombstone write failure must not remove the state - single
# atomic write, proven via fault injection
# ============================================================================

def test_tombstone_write_failure_preserves_original_state(memory, monkeypatch):
    item = memory.get_or_create_knowledge_item("desktop.filters.fault1", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "irreplaceable content", [_evidence(memory).id])

    import lib.store as store_module

    def failing_write(path, data):
        raise OSError("simulated disk full during purge write")

    monkeypatch.setattr(store_module, "_atomic_write_json", failing_write)

    with pytest.raises(OSError):
        purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="should not survive")

    monkeypatch.undo()  # restore normal writes so the verifying read below is unaffected

    reloaded = memory.get_knowledge_item(item.id)
    assert len(reloaded.states) == 1
    assert reloaded.states[0].content == "irreplaceable content"  # untouched, not removed or redacted
    assert reloaded.states[0].version == p.version


def test_tombstone_write_failure_during_rename_preserves_original_state(memory, monkeypatch):
    # a distinct failure point: the temp file write itself succeeds, but the
    # atomic rename (Path.replace) fails - the original file must still survive
    item = memory.get_or_create_knowledge_item("desktop.filters.fault2", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content that must survive", [_evidence(memory).id])

    from pathlib import Path as PathClass
    real_replace = PathClass.replace

    def failing_replace(self, target):
        if str(self).endswith(".tmp"):
            raise OSError("simulated rename failure during purge write")
        return real_replace(self, target)

    monkeypatch.setattr(PathClass, "replace", failing_replace)

    with pytest.raises(OSError):
        purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer")

    monkeypatch.undo()

    reloaded = memory.get_knowledge_item(item.id)
    assert reloaded.states[0].content == "content that must survive"


def test_full_removal_write_failure_also_preserves_original_state(memory, monkeypatch):
    item = memory.get_or_create_knowledge_item("desktop.filters.fault3", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])

    import lib.store as store_module

    def failing_write(path, data):
        raise OSError("simulated failure")

    monkeypatch.setattr(store_module, "_atomic_write_json", failing_write)

    with pytest.raises(OSError):
        purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", tombstone=False)

    monkeypatch.undo()

    reloaded = memory.get_knowledge_item(item.id)
    assert len(reloaded.states) == 1  # not removed - the failed write left the file untouched


# ============================================================================
# No new tombstone directory
# ============================================================================

def test_no_tombstones_directory_created_anywhere(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.nodir", KnowledgeType.PRODUCT, "desktop.filters")
    p1 = memory.propose_state(item.id, "v1", [_evidence(memory, "e1.png").id])
    purge_knowledge_state(memory, item.id, p1.version, purged_by="maintainer", reason="tombstone mode")
    p2 = memory.propose_state(item.id, "v2", [_evidence(memory, "e2.png").id])
    purge_knowledge_state(memory, item.id, p2.version, purged_by="maintainer", tombstone=False)

    assert not (memory.store.root / "tombstones").exists()
    # only the two originally-approved top-level directories exist
    top_level = {p.name for p in memory.store.root.iterdir() if p.is_dir()}
    assert top_level == {"evidence", "knowledge"}


def test_store_has_no_tombstone_directory_attribute(memory):
    assert not hasattr(memory.store, "tombstone_dir")
    assert not hasattr(memory.store, "save_knowledge_state_tombstone")
    assert not hasattr(memory.store, "load_knowledge_state_tombstone")
