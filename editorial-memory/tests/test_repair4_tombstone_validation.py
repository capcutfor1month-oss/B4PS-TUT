"""Adversarial regression tests for the fourth Slices 4-7 audit repair
round: strict tombstone shape/identity validation, and exact array-slot/
order preservation across later saves and reload.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

import pytest

from lib import (
    EditorialMemory,
    EvidenceType,
    InvalidEvidenceIdError,
    InvalidFeatureAreaError,
    InvalidKnowledgeItemIdError,
    KnowledgeType,
    StorageCorruptionError,
)
from lib.purge import purge_knowledge_state
from lib.retrieval import get_current_by_key, get_history_by_key
from lib.store import (
    _TOMBSTONE_VERSION_MAX_DIGITS,
    is_tombstone_entry,
    validate_evidence_id,
    validate_feature_area,
    validate_knowledge_item_id,
)


@pytest.fixture
def memory(tmp_path):
    return EditorialMemory(tmp_path / "store")


def _evidence(memory, ref="e.png"):
    return memory.record_evidence(evidence_type=EvidenceType.SCREENSHOT, source_ref=ref, captured_by="maintainer")


def _item_path(memory, item):
    return memory.store.root / "knowledge" / item.feature_area / f"{item.id}.json"


def _write_raw(memory, item, raw):
    _item_path(memory, item).write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n")


# ============================================================================
# Finding 1: strict tombstone shape/identity validation
# ============================================================================

def test_valid_state_with_stray_purged_at_raises_typed_error_not_silently_hidden(memory):
    # a real, otherwise-complete KnowledgeState that has somehow acquired a
    # stray `purged_at` field (corruption/bug/tampering) must NEVER be
    # silently filtered out of `states` as if it were a legitimate tombstone -
    # that would silently make current/history truth disappear.
    item = memory.get_or_create_knowledge_item("desktop.filters.stray", KnowledgeType.PRODUCT, "desktop.filters")
    ev = _evidence(memory)
    p = memory.propose_state(item.id, "current content", [ev.id])
    memory.approve_state(item.id, p.version, approved_by="maintainer")

    raw = memory.store.load_knowledge_item_raw(item.id)
    raw["states"][0]["purged_at"] = "2026-01-01T00:00:00+00:00"  # stray field, not a real tombstone
    _write_raw(memory, item, raw)

    with pytest.raises(StorageCorruptionError):
        memory.get_knowledge_item(item.id)
    with pytest.raises(StorageCorruptionError):
        get_current_by_key(memory, item.key)
    with pytest.raises(StorageCorruptionError):
        get_history_by_key(memory, item.key)


def test_malformed_tombstone_missing_fields_raises_typed_error(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.malformed", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])
    purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="test")

    raw = memory.store.load_knowledge_item_raw(item.id)
    assert "purged_at" in raw["states"][0]
    del raw["states"][0]["reason"]  # now missing a required tombstone field
    _write_raw(memory, item, raw)

    with pytest.raises(StorageCorruptionError):
        memory.get_knowledge_item(item.id)


def test_tombstone_with_extra_field_raises_typed_error(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.extra", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])
    purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="test")

    raw = memory.store.load_knowledge_item_raw(item.id)
    raw["states"][0]["unexpected_extra_field"] = "not part of the contract"
    _write_raw(memory, item, raw)

    with pytest.raises(StorageCorruptionError):
        memory.get_knowledge_item(item.id)


def test_tombstone_with_wrong_item_id_raises_typed_error(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.wrongid", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])
    purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="test")

    raw = memory.store.load_knowledge_item_raw(item.id)
    raw["states"][0]["id"] = f"some-other-item#{p.version}"  # wrong item prefix
    _write_raw(memory, item, raw)

    with pytest.raises(StorageCorruptionError):
        memory.get_knowledge_item(item.id)


def test_tombstone_with_non_numeric_version_suffix_raises_typed_error(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.badver", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])
    purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="test")

    raw = memory.store.load_knowledge_item_raw(item.id)
    raw["states"][0]["id"] = f"{item.id}#not-a-number"
    _write_raw(memory, item, raw)

    with pytest.raises(StorageCorruptionError):
        memory.get_knowledge_item(item.id)


def test_no_raw_exceptions_leak_from_tombstone_validation(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.noraw", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])
    purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="test")

    raw = memory.store.load_knowledge_item_raw(item.id)
    raw["states"][0]["id"] = 12345  # not even a string
    _write_raw(memory, item, raw)

    try:
        memory.get_knowledge_item(item.id)
        assert False, "expected an exception"
    except (KeyError, IndexError, TypeError):
        pytest.fail("a raw KeyError/IndexError/TypeError leaked past the typed validation boundary")
    except StorageCorruptionError:
        pass  # expected


def test_is_tombstone_entry_directly_rejects_ambiguous_shapes():
    assert is_tombstone_entry({"version": 1, "content": "x"}, "item-a") is False  # ordinary real state
    with pytest.raises(StorageCorruptionError):
        is_tombstone_entry({"purged_at": "x", "id": "item-a#1"}, "item-a")  # missing purged_by/reason
    with pytest.raises(StorageCorruptionError):
        is_tombstone_entry(
            {"id": "item-a#1", "purged_at": "x", "purged_by": "m", "reason": None, "extra": "y"}, "item-a"
        )
    assert is_tombstone_entry(
        {"id": "item-a#1", "purged_at": "x", "purged_by": "m", "reason": None}, "item-a"
    ) is True


# ============================================================================
# Round 5 finding: tombstone `id` version suffix must be a canonical
# positive ASCII integer, no leading zero, no Unicode digit look-alikes.
# ============================================================================

@pytest.mark.parametrize(
    "bad_suffix",
    [
        "²",  # Unicode superscript "2" - str.isdigit() accepts it, int(...) does not mean "version 2"
        "0",  # versions are 1-based; "#0" is never a valid version
        "01",  # leading zero - not the canonical decimal form
        "007",  # leading zero, multi-digit
        "1\n",  # trailing newline - plain `$` matches just before it, `fullmatch` must not
        "1\r\n",  # trailing CRLF
        "1 ",  # trailing space
        " 1",  # leading space
    ],
)
def test_tombstone_id_rejects_non_canonical_version_suffix(memory, bad_suffix):
    item = memory.get_or_create_knowledge_item("desktop.filters.badsuffix", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])
    purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="test")

    raw = memory.store.load_knowledge_item_raw(item.id)
    raw["states"][0]["id"] = f"{item.id}#{bad_suffix}"
    _write_raw(memory, item, raw)

    with pytest.raises(StorageCorruptionError):
        memory.get_knowledge_item(item.id)


def test_tombstone_id_rejects_non_canonical_suffix_no_raw_valueerror(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.novalueerror", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])
    purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="test")

    raw = memory.store.load_knowledge_item_raw(item.id)
    raw["states"][0]["id"] = f"{item.id}#²"  # Unicode digit, would raise ValueError if fed to int()
    _write_raw(memory, item, raw)

    try:
        memory.get_knowledge_item(item.id)
        assert False, "expected an exception"
    except ValueError:
        pytest.fail("a raw ValueError leaked past the typed validation boundary")
    except StorageCorruptionError:
        pass  # expected


def test_is_tombstone_entry_directly_rejects_unicode_digit_and_zero_and_leading_zero():
    with pytest.raises(StorageCorruptionError):
        is_tombstone_entry(
            {"id": "item-a#²", "purged_at": "x", "purged_by": "m", "reason": None}, "item-a"
        )
    with pytest.raises(StorageCorruptionError):
        is_tombstone_entry(
            {"id": "item-a#0", "purged_at": "x", "purged_by": "m", "reason": None}, "item-a"
        )
    with pytest.raises(StorageCorruptionError):
        is_tombstone_entry(
            {"id": "item-a#01", "purged_at": "x", "purged_by": "m", "reason": None}, "item-a"
        )
    with pytest.raises(StorageCorruptionError):
        is_tombstone_entry(
            {"id": "item-a#1\n", "purged_at": "x", "purged_by": "m", "reason": None}, "item-a"
        )
    with pytest.raises(StorageCorruptionError):
        is_tombstone_entry(
            {"id": "item-a#1\r\n", "purged_at": "x", "purged_by": "m", "reason": None}, "item-a"
        )
    with pytest.raises(StorageCorruptionError):
        is_tombstone_entry(
            {"id": "item-a#1 ", "purged_at": "x", "purged_by": "m", "reason": None}, "item-a"
        )
    assert is_tombstone_entry(
        {"id": "item-a#1", "purged_at": "x", "purged_by": "m", "reason": None}, "item-a"
    ) is True
    assert is_tombstone_entry(
        {"id": "item-a#12", "purged_at": "x", "purged_by": "m", "reason": None}, "item-a"
    ) is True


# ============================================================================
# Round 7 finding: an oversized numeric version suffix (thousands of
# digits) fullmatches the version regex but trips Python's int-string
# conversion length guard with a raw ValueError the moment anything
# downstream calls int() on it.
# ============================================================================

_OVERSIZED_SUFFIX = "1" + "0" * 5000  # 5001-digit canonical-looking integer


def test_is_tombstone_entry_directly_rejects_oversized_version_suffix():
    with pytest.raises(StorageCorruptionError):
        is_tombstone_entry(
            {"id": f"item-a#{_OVERSIZED_SUFFIX}", "purged_at": "x", "purged_by": "m", "reason": None},
            "item-a",
        )


def test_is_tombstone_entry_oversized_suffix_no_raw_valueerror():
    try:
        is_tombstone_entry(
            {"id": f"item-a#{_OVERSIZED_SUFFIX}", "purged_at": "x", "purged_by": "m", "reason": None},
            "item-a",
        )
        assert False, "expected an exception"
    except ValueError:
        pytest.fail("a raw ValueError leaked past the typed validation boundary")
    except StorageCorruptionError:
        pass  # expected


def test_tombstoned_versions_rejects_oversized_suffix_no_raw_valueerror(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.oversized", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])
    purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="test")

    raw = memory.store.load_knowledge_item_raw(item.id)
    raw["states"][0]["id"] = f"{item.id}#{_OVERSIZED_SUFFIX}"
    _write_raw(memory, item, raw)

    try:
        memory.store.tombstoned_versions(item.id)
        assert False, "expected an exception"
    except ValueError:
        pytest.fail("a raw ValueError leaked past the typed validation boundary")
    except StorageCorruptionError:
        pass  # expected


def test_propose_state_rejects_oversized_tombstone_suffix_no_raw_valueerror(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.oversized-propose", KnowledgeType.PRODUCT, "desktop.filters")
    p = memory.propose_state(item.id, "content", [_evidence(memory).id])
    purge_knowledge_state(memory, item.id, p.version, purged_by="maintainer", reason="test")

    raw = memory.store.load_knowledge_item_raw(item.id)
    raw["states"][0]["id"] = f"{item.id}#{_OVERSIZED_SUFFIX}"
    _write_raw(memory, item, raw)

    try:
        memory.propose_state(item.id, "new content", [_evidence(memory, "e2.png").id])
        assert False, "expected an exception"
    except ValueError:
        pytest.fail("a raw ValueError leaked past the typed validation boundary")
    except StorageCorruptionError:
        pass  # expected


def test_valid_canonical_tombstone_ids_still_accepted_after_oversized_guard():
    # the length guard must not reject ordinary, already-valid version
    # suffixes - only ones too large for int() to parse.
    for suffix in ("1", "2", "12", "999999"):
        assert is_tombstone_entry(
            {"id": f"item-a#{suffix}", "purged_at": "x", "purged_by": "m", "reason": None}, "item-a"
        ) is True


# ============================================================================
# Round 8 finding 1: the oversized-suffix guard must be an explicit,
# version-independent digit-count bound checked before int() is ever
# called - not a reliance on Python's own (version-varying, process-
# configurable) int-string conversion limit.
# ============================================================================

def test_oversized_suffix_rejected_at_explicit_runtime_independent_boundary():
    # one digit over the documented bound - must raise regardless of
    # what Python's own int() conversion limit happens to be on this
    # interpreter/version.
    suffix = "1" * (_TOMBSTONE_VERSION_MAX_DIGITS + 1)
    with pytest.raises(StorageCorruptionError):
        is_tombstone_entry(
            {"id": f"item-a#{suffix}", "purged_at": "x", "purged_by": "m", "reason": None}, "item-a"
        )


def test_suffix_exactly_at_max_digit_boundary_still_accepted():
    # the bound must not be off-by-one in the strict direction either -
    # a suffix exactly at the documented maximum is still valid.
    suffix = "1" + "0" * (_TOMBSTONE_VERSION_MAX_DIGITS - 1)
    assert is_tombstone_entry(
        {"id": f"item-a#{suffix}", "purged_at": "x", "purged_by": "m", "reason": None}, "item-a"
    ) is True


# ============================================================================
# Round 8 finding 2: literal-token validators (feature_area, evidence_id,
# knowledge_item_id) must use full-string matching so a trailing
# LF/CRLF/whitespace character cannot pass.
# ============================================================================

_TRAILING_JUNK_CASES = ["\n", "\r\n", " "]
_LEADING_JUNK_CASES = ["\n", "\r\n", " "]


@pytest.mark.parametrize("junk", _TRAILING_JUNK_CASES)
def test_feature_area_rejects_trailing_newline_or_whitespace(junk):
    with pytest.raises(InvalidFeatureAreaError):
        validate_feature_area(f"desktop.filters{junk}")


@pytest.mark.parametrize("junk", _LEADING_JUNK_CASES)
def test_feature_area_rejects_leading_newline_or_whitespace(junk):
    with pytest.raises(InvalidFeatureAreaError):
        validate_feature_area(f"{junk}desktop.filters")


@pytest.mark.parametrize("junk", _TRAILING_JUNK_CASES)
def test_evidence_id_rejects_trailing_newline_or_whitespace(junk):
    with pytest.raises(InvalidEvidenceIdError):
        validate_evidence_id(f"ev-abc{junk}")


@pytest.mark.parametrize("junk", _LEADING_JUNK_CASES)
def test_evidence_id_rejects_leading_newline_or_whitespace(junk):
    with pytest.raises(InvalidEvidenceIdError):
        validate_evidence_id(f"{junk}ev-abc")


@pytest.mark.parametrize("junk", _TRAILING_JUNK_CASES)
def test_knowledge_item_id_rejects_trailing_newline_or_whitespace(junk):
    with pytest.raises(InvalidKnowledgeItemIdError):
        validate_knowledge_item_id(f"item{junk}")


@pytest.mark.parametrize("junk", _LEADING_JUNK_CASES)
def test_knowledge_item_id_rejects_leading_newline_or_whitespace(junk):
    with pytest.raises(InvalidKnowledgeItemIdError):
        validate_knowledge_item_id(f"{junk}item")


def test_literal_token_validators_still_accept_valid_canonical_tokens():
    assert validate_feature_area("desktop.filters") == "desktop.filters"
    assert validate_evidence_id("ev-abc") == "ev-abc"
    assert validate_knowledge_item_id("item") == "item"


# ============================================================================
# Finding 2: tombstone remains in its exact original array slot; relative
# order of live states + tombstones is preserved across later saves/reload
# ============================================================================

def test_tombstone_remains_in_original_slot_after_later_proposals(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.slot", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = memory.propose_state(item.id, "v1", [_evidence(memory, "e1.png").id])
    memory.approve_state(item.id, v1.version, approved_by="maintainer")
    v2 = memory.propose_state(item.id, "v2", [_evidence(memory, "e2.png").id])
    memory.approve_state(item.id, v2.version, approved_by="maintainer")

    purge_knowledge_state(memory, item.id, v1.version, purged_by="maintainer", reason="test")  # index 0 becomes a tombstone

    raw_before = memory.store.load_knowledge_item_raw(item.id)
    assert is_tombstone_entry(raw_before["states"][0], item.id)  # tombstone at index 0
    assert raw_before["states"][1]["version"] == 2  # v2 still at index 1

    v3 = memory.propose_state(item.id, "v3", [_evidence(memory, "e3.png").id])  # a later, unrelated mutation

    raw_after = memory.store.load_knowledge_item_raw(item.id)
    assert is_tombstone_entry(raw_after["states"][0], item.id)  # still at index 0 - not moved to front/back
    assert raw_after["states"][1]["version"] == 2  # v2 still at its original index
    assert raw_after["states"][2]["version"] == 3  # v3 appended at the end, where it belongs


def test_tombstone_slot_preserved_across_multiple_further_mutations_and_reload(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    item = m1.get_or_create_knowledge_item("desktop.filters.slot2", KnowledgeType.PRODUCT, "desktop.filters")
    v1 = m1.propose_state(item.id, "v1", [m1.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="e1.png", captured_by="maintainer").id])
    v2 = m1.propose_state(item.id, "v2", [m1.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="e2.png", captured_by="maintainer").id])
    m1.approve_state(item.id, v1.version, approved_by="maintainer")

    purge_knowledge_state(m1, item.id, v2.version, purged_by="maintainer", reason="middle purge")  # index 1 tombstoned

    # further mutations on the surviving real state (index 0) and a new one
    m1.invalidate_state(item.id, v1.version, invalidated_by="maintainer", reason="later invalidated")
    v3 = m1.propose_state(item.id, "v3", [m1.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="e3.png", captured_by="maintainer").id])

    raw = m1.store.load_knowledge_item_raw(item.id)
    assert raw["states"][0]["version"] == 1  # original slot 0, content/status updated in place
    assert is_tombstone_entry(raw["states"][1], item.id)  # original slot 1, untouched
    assert raw["states"][2]["version"] == 3  # appended at the end

    m2 = EditorialMemory(root)  # fresh instance, forces a real reload from disk
    raw_reloaded = m2.store.load_knowledge_item_raw(item.id)
    assert raw_reloaded["states"][0]["version"] == 1
    assert is_tombstone_entry(raw_reloaded["states"][1], item.id)
    assert raw_reloaded["states"][2]["version"] == 3
    # the filtered view is unaffected by raw ordering - still just the two real states
    assert [s.version for s in m2.get_knowledge_item(item.id).states] == [1, 3]


def test_multiple_tombstones_each_stay_at_their_own_original_slot(memory):
    item = memory.get_or_create_knowledge_item("desktop.filters.multi-slot", KnowledgeType.PRODUCT, "desktop.filters")
    versions = []
    for i in range(4):
        v = memory.propose_state(item.id, f"v{i+1}", [_evidence(memory, f"e{i+1}.png").id])
        versions.append(v.version)

    # purge the 2nd and 4th entries (indices 1 and 3)
    purge_knowledge_state(memory, item.id, versions[1], purged_by="maintainer", reason="p1")
    purge_knowledge_state(memory, item.id, versions[3], purged_by="maintainer", reason="p2")

    v5 = memory.propose_state(item.id, "v5", [_evidence(memory, "e5.png").id])  # later mutation

    raw = memory.store.load_knowledge_item_raw(item.id)
    assert raw["states"][0]["version"] == versions[0]
    assert is_tombstone_entry(raw["states"][1], item.id)
    assert raw["states"][2]["version"] == versions[2]
    assert is_tombstone_entry(raw["states"][3], item.id)
    assert raw["states"][4]["version"] == v5.version  # new state appended at the very end
