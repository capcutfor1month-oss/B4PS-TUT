"""Browser Verification pilot - Engineering Slice 1 tests.

Fixture is the approved Test 2 pilot observation (the "Favorite" toggle
on the "Bridge4PS Announcements & Resources" channel): a real,
maintainer-reviewed multi-step observation with directly-observed
facts, one inference, unknowns, and an uncertainty note kept separate,
exactly as the pilot's epistemic-safety rule requires.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from lib import (
    EditorialMemory,
    EvidenceQuality,
    EvidenceType,
    InvalidBrowserObservationError,
    KnowledgeType,
    MalformedBrowserObservationError,
    get_browser_observation,
    record_browser_observation,
)
from lib.browser_evidence import BrowserObservation, _NOTES_SCHEMA_VERSION


@pytest.fixture
def memory(tmp_path):
    return EditorialMemory(tmp_path / "store")


# ============================================================================
# Test 2 fixture: the approved "Favorite toggle" pilot observation
# ============================================================================

TEST2_WORKFLOW = (
    "Toggle the 'Favorite' star control on the 'Bridge4PS Announcements & "
    "Resources' channel: favorite it, observe, then un-favorite it, observe."
)
TEST2_SOURCE_REF = "https://bridge4ps.app/channel/bridge4ps-announcements-and-resources"
TEST2_CAPTURED_BY = "browser-verification-pilot-test2"
TEST2_DIRECT_OBSERVATIONS = (
    "Baseline sidebar (before any click) had no 'Favorites' group; the channel was listed under 'Public'.",
    "Clicking the header button labeled 'Favorite Bridge4PS Announcements & Resources' produced a toast "
    "'Bridge4PS Announcements & Resources was added to favorites' and changed the button's accessible "
    "name to 'Unfavorite Bridge4PS Announcements & Resources'.",
    "After that click, the sidebar showed a new 'Favorites' group containing the channel, and the "
    "channel no longer appeared under 'Public'.",
    "Clicking the button again (now labeled 'Unfavorite...') produced a toast "
    "'Bridge4PS Announcements & Resources was removed from favorites' and the button's accessible name "
    "reverted to 'Favorite Bridge4PS Announcements & Resources'.",
    "After that second click, the sidebar exactly matched the original baseline: no 'Favorites' group, "
    "channel back under 'Public'.",
)
TEST2_INFERENCES = (
    "The 'Favorite' control most likely implements a personal, per-user bookmarking feature rather than "
    "a shared/workspace-level pin, based on toast wording alone - not confirmed against a second account.",
)
TEST2_UNKNOWNS = (
    "Whether this same toggle/grouping behavior holds for channels in the Workspaces, Discussions, "
    "Private, or Direct-message sidebar groups was not tested - only one Public channel was exercised.",
    "Whether the favorite state is per-user or shared workspace-wide was not tested - only one account's "
    "view was observed.",
)
TEST2_UNCERTAINTY = (
    "This instance's favorite/unfavorite cycle was fully reversible and internally consistent, but the "
    "run does not establish general product behavior across channel types or across accounts."
)
TEST2_VERIFICATION_SCOPE = ["visual", "workflow"]


def _record_test2(memory):
    return record_browser_observation(
        memory,
        workflow=TEST2_WORKFLOW,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        direct_observations=TEST2_DIRECT_OBSERVATIONS,
        inferences=TEST2_INFERENCES,
        unknowns=TEST2_UNKNOWNS,
        uncertainty=TEST2_UNCERTAINTY,
        verification_scope=TEST2_VERIFICATION_SCOPE,
        evidence_quality=EvidenceQuality.HIGH,
    )


# ============================================================================
# 1. valid browser observation -> Evidence persists and reloads correctly
# ============================================================================

def test_valid_browser_observation_persists_and_reloads(memory):
    evidence = _record_test2(memory)
    assert evidence.evidence_type == EvidenceType.BROWSER_OBSERVATION
    assert evidence.id.startswith("ev-")

    reloaded = memory.get_evidence(evidence.id)
    assert reloaded == evidence


def test_reload_from_fresh_memory_instance_forces_real_disk_read(tmp_path):
    root = tmp_path / "store"
    m1 = EditorialMemory(root)
    evidence = record_browser_observation(
        m1,
        workflow=TEST2_WORKFLOW,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        direct_observations=TEST2_DIRECT_OBSERVATIONS,
    )

    m2 = EditorialMemory(root)  # fresh instance, forces a real reload from disk
    reloaded = m2.get_evidence(evidence.id)
    assert reloaded.notes == evidence.notes
    assert get_browser_observation(reloaded) == get_browser_observation(evidence)


# ============================================================================
# 2. provenance and scope survive round-trip
# ============================================================================

def test_provenance_and_scope_survive_round_trip(memory):
    evidence = _record_test2(memory)
    reloaded = memory.get_evidence(evidence.id)

    assert reloaded.source_ref == TEST2_SOURCE_REF
    assert reloaded.captured_by == TEST2_CAPTURED_BY
    assert reloaded.verification_scope == TEST2_VERIFICATION_SCOPE
    assert reloaded.evidence_quality == EvidenceQuality.HIGH
    assert reloaded.recorded_at
    assert reloaded.evidence_type == EvidenceType.BROWSER_OBSERVATION


def test_captured_at_round_trips_exactly(memory):
    captured_at = "2026-08-11T20:30:00+00:00"
    evidence = record_browser_observation(
        memory,
        workflow=TEST2_WORKFLOW,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        direct_observations=TEST2_DIRECT_OBSERVATIONS,
        captured_at=captured_at,
    )
    assert evidence.captured_at == captured_at
    reloaded = memory.get_evidence(evidence.id)
    assert reloaded.captured_at == captured_at
    # recorded_at (when the record was written here) is distinct from
    # captured_at (when the observation itself happened) - never conflated
    assert reloaded.recorded_at != captured_at


def test_captured_at_omitted_round_trips_as_none(memory):
    evidence = record_browser_observation(
        memory,
        workflow=TEST2_WORKFLOW,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        direct_observations=TEST2_DIRECT_OBSERVATIONS,
    )
    assert evidence.captured_at is None
    assert memory.get_evidence(evidence.id).captured_at is None


# ============================================================================
# 3. uncertainty/interpretation boundaries survive round-trip
# ============================================================================

def test_direct_inferred_unknown_uncertainty_boundaries_survive_round_trip(memory):
    evidence = _record_test2(memory)
    reloaded = memory.get_evidence(evidence.id)

    observation = get_browser_observation(reloaded)
    assert observation.direct_observations == TEST2_DIRECT_OBSERVATIONS
    assert observation.inferences == TEST2_INFERENCES
    assert observation.unknowns == TEST2_UNKNOWNS
    assert observation.uncertainty == TEST2_UNCERTAINTY
    # the categories must never collapse into one another
    assert set(observation.direct_observations).isdisjoint(observation.inferences)
    assert set(observation.direct_observations).isdisjoint(observation.unknowns)
    assert set(observation.inferences).isdisjoint(observation.unknowns)


def test_round_trip_notes_encoding_is_byte_identical(memory):
    evidence = _record_test2(memory)
    reloaded = memory.get_evidence(evidence.id)
    assert reloaded.notes == evidence.notes


def test_observation_with_no_inferences_or_unknowns_round_trips_as_empty_not_missing(memory):
    evidence = record_browser_observation(
        memory,
        workflow=TEST2_WORKFLOW,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        direct_observations=TEST2_DIRECT_OBSERVATIONS,
    )
    reloaded = get_browser_observation(memory.get_evidence(evidence.id))
    assert reloaded.inferences == ()
    assert reloaded.unknowns == ()
    assert reloaded.uncertainty is None


# ============================================================================
# 4. ingestion creates NO Knowledge automatically
# ============================================================================

def test_recording_browser_observation_creates_no_knowledge_item(memory):
    _record_test2(memory)
    assert memory.store.list_knowledge_item_ids() == []
    assert memory.list_knowledge_items() == []


def test_recording_browser_observation_touches_no_pending_or_conflicts(memory):
    _record_test2(memory)
    assert memory.get_pending() == []
    assert memory.get_conflicts() == []


def test_browser_observation_evidence_usable_only_via_existing_normal_lifecycle(memory):
    """The observation becomes usable Knowledge only through the unmodified,
    existing propose_state/approve_state path - never automatically."""
    obs_evidence = _record_test2(memory)
    item = memory.get_or_create_knowledge_item(
        "desktop.filters.favorite-toggle", KnowledgeType.PRODUCT, "desktop.filters"
    )
    # immediately after recording, still no Knowledge exists referencing it
    assert memory.list_knowledge_items() == [item]
    assert item.states == []

    proposed = memory.propose_state(
        item.id, "Favoriting a channel adds it to a Favorites sidebar group.", [obs_evidence.id]
    )
    assert memory.get_current(item.id) is None  # proposing alone still does not make it current
    approved = memory.approve_state(item.id, proposed.version, approved_by="maintainer")
    assert memory.get_current(item.id).version == approved.version
    assert memory.get_current(item.id).evidence_refs == [obs_evidence.id]


# ============================================================================
# 5. malformed browser evidence fails safely
# ============================================================================

def test_empty_direct_observations_rejected_and_nothing_written(memory):
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(
            memory,
            workflow=TEST2_WORKFLOW,
            source_ref=TEST2_SOURCE_REF,
            captured_by=TEST2_CAPTURED_BY,
            direct_observations=(),
        )
    assert memory.store.list_evidence_ids() == []


def test_blank_workflow_rejected(memory):
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(
            memory,
            workflow="   ",
            source_ref=TEST2_SOURCE_REF,
            captured_by=TEST2_CAPTURED_BY,
            direct_observations=("something directly seen",),
        )


def test_blank_source_ref_rejected(memory):
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(
            memory,
            workflow=TEST2_WORKFLOW,
            source_ref="",
            captured_by=TEST2_CAPTURED_BY,
            direct_observations=("something directly seen",),
        )


def test_non_string_direct_observation_entry_rejected(memory):
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(
            memory,
            workflow=TEST2_WORKFLOW,
            source_ref=TEST2_SOURCE_REF,
            captured_by=TEST2_CAPTURED_BY,
            direct_observations=(123,),
        )


def test_blank_inference_entry_rejected(memory):
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(
            memory,
            workflow=TEST2_WORKFLOW,
            source_ref=TEST2_SOURCE_REF,
            captured_by=TEST2_CAPTURED_BY,
            direct_observations=("something directly seen",),
            inferences=("   ",),
        )


def test_get_browser_observation_rejects_wrong_evidence_type(memory):
    evidence = memory.record_evidence(
        evidence_type=EvidenceType.SCREENSHOT, source_ref="s.png", captured_by="maintainer"
    )
    with pytest.raises(MalformedBrowserObservationError):
        get_browser_observation(evidence)


def test_get_browser_observation_rejects_malformed_notes_json(memory):
    evidence = memory.record_evidence(
        evidence_type=EvidenceType.BROWSER_OBSERVATION,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        notes="not valid json {{{",
    )
    with pytest.raises(MalformedBrowserObservationError):
        get_browser_observation(evidence)


def test_get_browser_observation_rejects_missing_notes(memory):
    evidence = memory.record_evidence(
        evidence_type=EvidenceType.BROWSER_OBSERVATION,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
    )
    with pytest.raises(MalformedBrowserObservationError):
        get_browser_observation(evidence)


def test_get_browser_observation_rejects_notes_missing_required_key(memory):
    evidence = memory.record_evidence(
        evidence_type=EvidenceType.BROWSER_OBSERVATION,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        notes=json.dumps({"schema": 1, "workflow": "x"}),  # missing direct_observations etc.
    )
    with pytest.raises(MalformedBrowserObservationError):
        get_browser_observation(evidence)


def test_get_browser_observation_rejects_wrong_schema_version(memory):
    evidence = memory.record_evidence(
        evidence_type=EvidenceType.BROWSER_OBSERVATION,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        notes=json.dumps(
            {
                "schema": 999,
                "workflow": "x",
                "direct_observations": ["a"],
                "inferences": [],
                "unknowns": [],
                "uncertainty": None,
            }
        ),
    )
    with pytest.raises(MalformedBrowserObservationError):
        get_browser_observation(evidence)


def test_no_raw_exceptions_leak_from_malformed_notes_parsing(memory):
    evidence = memory.record_evidence(
        evidence_type=EvidenceType.BROWSER_OBSERVATION,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        notes="{",
    )
    try:
        get_browser_observation(evidence)
        assert False, "expected an exception"
    except MalformedBrowserObservationError:
        pass  # expected
    except (ValueError, KeyError, TypeError):
        pytest.fail("a raw ValueError/KeyError/TypeError leaked past the typed validation boundary")


# ============================================================================
# Repair round: strict write-boundary rejection - no silent coercion,
# character-splitting, or nondeterministic order; no raw exceptions.
# ============================================================================

@pytest.mark.parametrize("field", ["direct_observations", "inferences", "unknowns"])
def test_plain_string_collection_argument_rejected(memory, field):
    kwargs = dict(
        workflow=TEST2_WORKFLOW,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        direct_observations=("a real direct observation",),
    )
    kwargs[field] = "this looks like a collection but is one string"
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(memory, **kwargs)
    assert memory.store.list_evidence_ids() == []


@pytest.mark.parametrize("field", ["direct_observations", "inferences", "unknowns"])
def test_set_collection_argument_rejected(memory, field):
    kwargs = dict(
        workflow=TEST2_WORKFLOW,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        direct_observations=("a real direct observation",),
    )
    kwargs[field] = {"one", "two"}
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(memory, **kwargs)


def test_frozenset_collection_argument_rejected(memory):
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(
            memory,
            workflow=TEST2_WORKFLOW,
            source_ref=TEST2_SOURCE_REF,
            captured_by=TEST2_CAPTURED_BY,
            direct_observations=frozenset({"one", "two"}),
        )


@pytest.mark.parametrize("field", ["direct_observations", "inferences", "unknowns"])
def test_non_iterable_collection_argument_rejected_no_raw_typeerror(memory, field):
    kwargs = dict(
        workflow=TEST2_WORKFLOW,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        direct_observations=("a real direct observation",),
    )
    kwargs[field] = 12345  # not iterable at all
    try:
        record_browser_observation(memory, **kwargs)
        assert False, "expected an exception"
    except InvalidBrowserObservationError:
        pass  # expected
    except (TypeError, AttributeError):
        pytest.fail("a raw TypeError/AttributeError leaked past the typed validation boundary")


def test_dict_collection_argument_rejected(memory):
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(
            memory,
            workflow=TEST2_WORKFLOW,
            source_ref=TEST2_SOURCE_REF,
            captured_by=TEST2_CAPTURED_BY,
            direct_observations={"a": "b"},
        )


def test_non_string_entry_in_inferences_rejected(memory):
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(
            memory,
            workflow=TEST2_WORKFLOW,
            source_ref=TEST2_SOURCE_REF,
            captured_by=TEST2_CAPTURED_BY,
            direct_observations=("a real direct observation",),
            inferences=(None,),
        )


def test_verification_scope_as_plain_string_rejected(memory):
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(
            memory,
            workflow=TEST2_WORKFLOW,
            source_ref=TEST2_SOURCE_REF,
            captured_by=TEST2_CAPTURED_BY,
            direct_observations=("a real direct observation",),
            verification_scope="visual",  # would silently explode into ['v','i','s',...]
        )


def test_verification_scope_as_set_rejected(memory):
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(
            memory,
            workflow=TEST2_WORKFLOW,
            source_ref=TEST2_SOURCE_REF,
            captured_by=TEST2_CAPTURED_BY,
            direct_observations=("a real direct observation",),
            verification_scope={"visual", "workflow"},
        )


def test_verification_scope_non_iterable_rejected_no_raw_typeerror(memory):
    try:
        record_browser_observation(
            memory,
            workflow=TEST2_WORKFLOW,
            source_ref=TEST2_SOURCE_REF,
            captured_by=TEST2_CAPTURED_BY,
            direct_observations=("a real direct observation",),
            verification_scope=42,
        )
        assert False, "expected an exception"
    except InvalidBrowserObservationError:
        pass  # expected
    except (TypeError, AttributeError):
        pytest.fail("a raw TypeError/AttributeError leaked past the typed validation boundary")


def test_verification_scope_non_string_entry_rejected(memory):
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(
            memory,
            workflow=TEST2_WORKFLOW,
            source_ref=TEST2_SOURCE_REF,
            captured_by=TEST2_CAPTURED_BY,
            direct_observations=("a real direct observation",),
            verification_scope=[1, 2],
        )


def test_evidence_quality_wrong_type_rejected(memory):
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(
            memory,
            workflow=TEST2_WORKFLOW,
            source_ref=TEST2_SOURCE_REF,
            captured_by=TEST2_CAPTURED_BY,
            direct_observations=("a real direct observation",),
            evidence_quality="high",  # plain string, not EvidenceQuality.HIGH
        )


def test_evidence_quality_invalid_value_rejected(memory):
    with pytest.raises(InvalidBrowserObservationError):
        record_browser_observation(
            memory,
            workflow=TEST2_WORKFLOW,
            source_ref=TEST2_SOURCE_REF,
            captured_by=TEST2_CAPTURED_BY,
            direct_observations=("a real direct observation",),
            evidence_quality=object(),
        )


def test_valid_evidence_quality_still_accepted(memory):
    evidence = record_browser_observation(
        memory,
        workflow=TEST2_WORKFLOW,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        direct_observations=("a real direct observation",),
        evidence_quality=EvidenceQuality.LOW,
    )
    assert evidence.evidence_quality == EvidenceQuality.LOW


def test_deterministic_ordered_serialization_preserved(memory):
    """Order (not just set membership) must round-trip exactly - the
    encoding must never sort/reorder observations."""
    ordered = ("third-ish observation", "actually-first observation", "middle observation")
    evidence = record_browser_observation(
        memory,
        workflow=TEST2_WORKFLOW,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        direct_observations=ordered,
    )
    reloaded = get_browser_observation(memory.get_evidence(evidence.id))
    assert reloaded.direct_observations == ordered  # exact order preserved, not sorted


def test_list_and_tuple_inputs_serialize_identically(memory):
    """Accepting both list and tuple must not itself become a source of
    nondeterminism - same content, same order, same encoded notes."""
    obs = ["first", "second", "third"]
    ev_list = record_browser_observation(
        memory, workflow=TEST2_WORKFLOW, source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY, direct_observations=obs,
    )
    ev_tuple = record_browser_observation(
        memory, workflow=TEST2_WORKFLOW, source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY, direct_observations=tuple(obs),
    )
    assert ev_list.notes == ev_tuple.notes


# ============================================================================
# Repair round: strict read-boundary (from_notes) rejection - no extra
# keys, no loose schema typing, no coercion of malformed persisted data.
# ============================================================================

def _valid_notes_payload(**overrides):
    payload = {
        "schema": _NOTES_SCHEMA_VERSION,
        "workflow": "some workflow",
        "direct_observations": ["something seen"],
        "inferences": [],
        "unknowns": [],
        "uncertainty": None,
    }
    payload.update(overrides)
    return payload


def test_from_notes_rejects_extra_unexpected_key():
    payload = _valid_notes_payload()
    payload["extra_field_nobody_asked_for"] = "surprise"
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_schema_true_not_treated_as_one():
    payload = _valid_notes_payload(schema=True)
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_schema_as_float():
    payload = _valid_notes_payload(schema=1.0)
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_schema_as_string():
    payload = _valid_notes_payload(schema="1")
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_non_string_workflow():
    payload = _valid_notes_payload(workflow=123)
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_non_string_uncertainty():
    payload = _valid_notes_payload(uncertainty=123)
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_blank_uncertainty():
    payload = _valid_notes_payload(uncertainty="   ")
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_accepts_null_uncertainty():
    payload = _valid_notes_payload(uncertainty=None)
    observation = BrowserObservation.from_notes(json.dumps(payload))
    assert observation.uncertainty is None


def test_from_notes_rejects_empty_direct_observations():
    payload = _valid_notes_payload(direct_observations=[])
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_direct_observations_as_string_no_character_split():
    payload = _valid_notes_payload(direct_observations="not a list")
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_direct_observations_as_dict():
    payload = _valid_notes_payload(direct_observations={"a": "b"})
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_direct_observations_with_non_string_entry():
    payload = _valid_notes_payload(direct_observations=["fine", 42, "also fine"])
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_direct_observations_with_blank_entry():
    payload = _valid_notes_payload(direct_observations=["fine", "   "])
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_inferences_as_dict():
    payload = _valid_notes_payload(inferences={"a": "b"})
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_unknowns_as_int():
    payload = _valid_notes_payload(unknowns=7)
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_unknowns_as_string_no_character_split():
    payload = _valid_notes_payload(unknowns="not a list either")
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(payload))


def test_from_notes_rejects_non_object_top_level():
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(json.dumps(["not", "an", "object"]))


def test_from_notes_no_raw_exceptions_across_all_malformed_shapes():
    malformed_payloads = [
        json.dumps(_valid_notes_payload(schema=True)),
        json.dumps(_valid_notes_payload(direct_observations="x")),
        json.dumps(_valid_notes_payload(direct_observations=[])),
        json.dumps(_valid_notes_payload(workflow=None)),
        json.dumps({**_valid_notes_payload(), "extra": 1}),
        "not json at all",
        "[]",
        "null",
        "42",
    ]
    for notes in malformed_payloads:
        try:
            BrowserObservation.from_notes(notes)
            assert False, f"expected an exception for {notes!r}"
        except MalformedBrowserObservationError:
            pass  # expected
        except (ValueError, KeyError, TypeError, AttributeError):
            pytest.fail(f"a raw exception leaked past the typed validation boundary for {notes!r}")


# ============================================================================
# Repair round 2: duplicate JSON keys and oversized JSON integers must
# never be silently accepted (last-value-wins) or leak a raw ValueError
# from the JSON decoder / Python's int-string conversion guard.
# ============================================================================

_5000_DIGIT_INT = "9" * 5000


def test_from_notes_rejects_duplicate_workflow_key():
    notes = (
        '{"schema":1,"workflow":"first value","workflow":"second value",'
        '"direct_observations":["x"],"inferences":[],"unknowns":[],"uncertainty":null}'
    )
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(notes)


def test_from_notes_does_not_silently_keep_last_value_for_duplicate_key():
    """Confirms rejection, not silent last-value-wins acceptance - the
    exact failure mode plain `json.loads` has by default."""
    notes = (
        '{"schema":1,"workflow":"first value","workflow":"second value",'
        '"direct_observations":["x"],"inferences":[],"unknowns":[],"uncertainty":null}'
    )
    # sanity check: plain json.loads *would* silently accept this and
    # keep only "second value" - proving the vulnerability is real
    assert json.loads(notes)["workflow"] == "second value"
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(notes)


@pytest.mark.parametrize(
    "notes",
    [
        # duplicate top-level key other than workflow
        '{"schema":1,"schema":1,"workflow":"w","direct_observations":["x"],'
        '"inferences":[],"unknowns":[],"uncertainty":null}',
        '{"schema":1,"workflow":"w","direct_observations":["x"],'
        '"inferences":[],"inferences":[],"unknowns":[],"uncertainty":null}',
        '{"schema":1,"workflow":"w","direct_observations":["x"],'
        '"inferences":[],"unknowns":[],"unknowns":[],"uncertainty":null}',
        '{"schema":1,"workflow":"w","direct_observations":["x"],'
        '"inferences":[],"unknowns":[],"uncertainty":null,"uncertainty":null}',
    ],
)
def test_from_notes_rejects_duplicate_keys_generally(notes):
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(notes)


def test_get_browser_observation_rejects_duplicate_workflow_key(memory):
    """The duplicate-key rejection must also apply on the
    `get_browser_observation()` path (Evidence -> parse), not only
    when `from_notes()` is called directly - `get_browser_observation`
    is what every real caller actually uses to read a persisted
    browser observation back."""
    notes = (
        '{"schema":1,"workflow":"first value","workflow":"second value",'
        '"direct_observations":["x"],"inferences":[],"unknowns":[],"uncertainty":null}'
    )
    evidence = memory.record_evidence(
        evidence_type=EvidenceType.BROWSER_OBSERVATION,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        notes=notes,
    )
    with pytest.raises(MalformedBrowserObservationError):
        get_browser_observation(evidence)


def test_from_notes_rejects_nested_duplicate_object_members():
    """The duplicate-key check applies to every JSON object in the
    document, not only the top-level one - a malformed/tampered
    payload could smuggle a duplicate key inside a nested object one
    of the list fields wasn't expecting to contain at all (the field
    is still rejected as not being a list of strings, but the nested
    duplicate must be caught too, not silently resolved to a last
    value first)."""
    notes = (
        '{"schema":1,"workflow":"w","direct_observations":[{"a":1,"a":2}],'
        '"inferences":[],"unknowns":[],"uncertainty":null}'
    )
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(notes)


def test_from_notes_rejects_5000_digit_schema_integer():
    notes = (
        f'{{"schema":{_5000_DIGIT_INT},"workflow":"w","direct_observations":["x"],'
        '"inferences":[],"unknowns":[],"uncertainty":null}'
    )
    with pytest.raises(MalformedBrowserObservationError):
        BrowserObservation.from_notes(notes)


def test_get_browser_observation_rejects_5000_digit_schema_integer(memory):
    notes = (
        f'{{"schema":{_5000_DIGIT_INT},"workflow":"w","direct_observations":["x"],'
        '"inferences":[],"unknowns":[],"uncertainty":null}'
    )
    evidence = memory.record_evidence(
        evidence_type=EvidenceType.BROWSER_OBSERVATION,
        source_ref=TEST2_SOURCE_REF,
        captured_by=TEST2_CAPTURED_BY,
        notes=notes,
    )
    with pytest.raises(MalformedBrowserObservationError):
        get_browser_observation(evidence)


def test_from_notes_no_raw_valueerror_for_oversized_integer_anywhere_in_document():
    # an oversized integer doesn't have to be the schema field to be
    # dangerous - the JSON decoder itself would choke on it regardless
    # of where in the document it appears.
    notes = (
        f'{{"schema":1,"workflow":"w","direct_observations":["x"],'
        f'"inferences":[],"unknowns":[],"uncertainty":null,"extra":{_5000_DIGIT_INT}}}'
    )
    try:
        BrowserObservation.from_notes(notes)
        assert False, "expected an exception"
    except MalformedBrowserObservationError:
        pass  # expected (also carries the extra-key rejection)
    except ValueError:
        pytest.fail("a raw ValueError leaked past the typed validation boundary")


def test_no_raw_exceptions_for_duplicate_keys_or_oversized_integers():
    malformed_payloads = [
        '{"schema":1,"workflow":"w","workflow":"w2","direct_observations":["x"],'
        '"inferences":[],"unknowns":[],"uncertainty":null}',
        f'{{"schema":{_5000_DIGIT_INT},"workflow":"w","direct_observations":["x"],'
        '"inferences":[],"unknowns":[],"uncertainty":null}',
        f'{{"schema":1,"workflow":"w","direct_observations":[{_5000_DIGIT_INT}],'
        '"inferences":[],"unknowns":[],"uncertainty":null}',
    ]
    for notes in malformed_payloads:
        try:
            BrowserObservation.from_notes(notes)
            assert False, f"expected an exception for {notes!r}"
        except MalformedBrowserObservationError:
            pass  # expected
        except (ValueError, KeyError, TypeError, AttributeError):
            pytest.fail(f"a raw exception leaked past the typed validation boundary for {notes!r}")


def test_valid_notes_without_duplicates_or_oversized_ints_still_parse(memory):
    """The new strict decode hooks must not reject ordinary, valid
    payloads - only genuinely duplicate keys or oversized integers."""
    evidence = _record_test2(memory)
    reloaded = get_browser_observation(memory.get_evidence(evidence.id))
    assert reloaded.workflow == TEST2_WORKFLOW
    assert reloaded.direct_observations == TEST2_DIRECT_OBSERVATIONS


# ============================================================================
# 6. existing Editorial Memory behavior remains unchanged
# ============================================================================

def test_existing_record_evidence_unaffected_by_new_module(memory):
    ev = memory.record_evidence(evidence_type=EvidenceType.SCREENSHOT, source_ref="s.png", captured_by="m")
    assert ev.notes is None
    assert memory.get_evidence(ev.id) == ev


def test_full_editorial_memory_test_suite_paths_still_importable():
    # importing the new module must not perturb any existing public symbol
    import lib

    assert lib.EditorialMemory is not None
    assert lib.MissingProvenanceError is not None
