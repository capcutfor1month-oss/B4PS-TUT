"""Proof tests for Editorial Memory Slice 4 - existing-documentation
ingestion.

Kept in its own file, separate from Slice 1/2/3's test files, so the
slice boundary is explicit: this file exercises only
`EditorialMemory.ingest_existing_documentation`, added in Slice 4 on top
of Slice 1's unmodified lifecycle. It never asserts anything about
Slice 1/2/3 behavior directly - `test_editorial_memory.py` and
`test_retrieval.py` remain the source of truth for those.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from lib import (
    EditorialMemory,
    EvidenceType,
    FeatureAreaMismatchError,
    InvalidFeatureAreaError,
    KnowledgeType,
    KnowledgeTypeMismatchError,
    Relation,
    StateStatus,
)


@pytest.fixture
def memory(tmp_path):
    return EditorialMemory(tmp_path / "store")


def _doc_kwargs(**overrides):
    kwargs = dict(
        key="desktop.filters.button-label",
        feature_area="desktop.filters",
        content="The tutorial deck's slide 148 caption calls this the 'Filters' button.",
        source_ref="Current update/Desktop/MASTER Complete Bridge4PS Desktop-Browser Feature Tutorials.pptx#slide148",
        captured_by="ingestion-script",
    )
    kwargs.update(overrides)
    return kwargs


# S4-01: ingestion creates exactly one Evidence(existing_documentation) + one proposed state
def test_s4_01_ingestion_creates_one_evidence_and_one_proposed_state(memory):
    state = memory.ingest_existing_documentation(**_doc_kwargs())

    assert state.status == StateStatus.PROPOSED
    assert state.version == 1
    assert len(state.evidence_refs) == 1
    evidence = memory.get_evidence(state.evidence_refs[0])
    assert evidence.evidence_type == EvidenceType.EXISTING_DOCUMENTATION


# S4-02: ingestion never auto-approves - this is the core rule of the slice
def test_s4_02_ingestion_never_auto_promotes_to_current(memory):
    item_key = _doc_kwargs()["key"]
    memory.ingest_existing_documentation(**_doc_kwargs())

    item = memory.get_knowledge_item(memory.get_or_create_knowledge_item(
        item_key, KnowledgeType.DOCUMENTATION, "desktop.filters"
    ).id)
    assert memory.get_current(item.id) is None
    assert memory.has_pending_conflict(item.id) is False  # NEW relation, not a contradiction
    pending = memory.get_pending(item.id)
    assert len(pending) == 1
    assert pending[0].status == StateStatus.PROPOSED


# S4-03: knowledge_type is always documentation, never caller-overridable
def test_s4_03_knowledge_type_is_always_documentation(memory):
    memory.ingest_existing_documentation(**_doc_kwargs())
    item = memory.get_or_create_knowledge_item(
        _doc_kwargs()["key"], KnowledgeType.DOCUMENTATION, "desktop.filters"
    )
    assert item.knowledge_type == KnowledgeType.DOCUMENTATION
    import inspect
    assert "knowledge_type" not in inspect.signature(memory.ingest_existing_documentation).parameters


# S4-04: only propose_state is invoked, never approve_state (call-spy proof, mirrors S2-10)
def test_s4_04_ingestion_only_calls_propose_state_never_approve_state(memory, monkeypatch):
    calls = []
    real_propose = memory.propose_state
    real_approve = memory.approve_state

    def spy_propose(*a, **kw):
        calls.append("propose_state")
        return real_propose(*a, **kw)

    def spy_approve(*a, **kw):
        calls.append("approve_state")
        return real_approve(*a, **kw)

    monkeypatch.setattr(memory, "propose_state", spy_propose)
    monkeypatch.setattr(memory, "approve_state", spy_approve)

    memory.ingest_existing_documentation(**_doc_kwargs())
    assert calls == ["propose_state"]


# S4-05: source_ref / captured_by / notes / verification_scope survive as Evidence
def test_s4_05_provenance_fields_survive(memory):
    state = memory.ingest_existing_documentation(
        **_doc_kwargs(notes="extracted by scripted OCR pass", verification_scope=["documentation-only"])
    )
    item_id = memory.get_or_create_knowledge_item(
        _doc_kwargs()["key"], KnowledgeType.DOCUMENTATION, "desktop.filters"
    ).id
    evidence = memory.get_provenance(item_id, state.version)[0]
    assert evidence.notes == "extracted by scripted OCR pass"
    assert evidence.verification_scope == ["documentation-only"]
    assert evidence.captured_by == "ingestion-script"


# S4-06: rationale survives when supplied
def test_s4_06_rationale_survives(memory):
    state = memory.ingest_existing_documentation(**_doc_kwargs(rationale="captured verbatim from deck caption"))
    assert state.rationale == "captured verbatim from deck caption"


# S4-07: invalid feature_area is rejected (EM-03 protection reused)
def test_s4_07_invalid_feature_area_rejected(memory):
    with pytest.raises(InvalidFeatureAreaError):
        memory.ingest_existing_documentation(**_doc_kwargs(feature_area="../../escape"))
    assert memory.store.list_knowledge_item_ids() == []
    assert memory.store.list_evidence_ids() == []


# S4-08: feature_area mismatch on an existing item is rejected outright (S2-01-style protection)
def test_s4_08_feature_area_mismatch_rejected_with_zero_side_effects(memory):
    memory.ingest_existing_documentation(**_doc_kwargs(feature_area="desktop.filters"))
    before_evidence_count = len(memory.store.list_evidence_ids())

    with pytest.raises(FeatureAreaMismatchError):
        memory.ingest_existing_documentation(**_doc_kwargs(
            feature_area="desktop.members", content="a different claim entirely"
        ))
    assert len(memory.store.list_evidence_ids()) == before_evidence_count


# S4-09: exact-repeat ingestion is idempotent (no duplicate Evidence/KnowledgeState)
def test_s4_09_exact_repeat_ingestion_is_idempotent(memory):
    # Explicit, matching relation_to_previous on every call: the default
    # relation legitimately differs between "first state on a brand-new
    # item" (NEW) and "a later ingestion on an existing item" (REFINES) -
    # see test_s4_12 for that default behavior - so an exact repeat of the
    # *default* is not what this test exercises; this proves idempotency
    # for the same fields including the same explicit relation (mirrors
    # Slice 2's test_s2_11/test_s2_12, S2-02).
    kwargs = _doc_kwargs(relation_to_previous=Relation.NEW)
    first = memory.ingest_existing_documentation(**kwargs)
    second = memory.ingest_existing_documentation(**kwargs)
    third = memory.ingest_existing_documentation(**kwargs)

    assert first.version == second.version == third.version == 1
    assert len(memory.store.list_evidence_ids()) == 1
    item = memory.get_or_create_knowledge_item(kwargs["key"], KnowledgeType.DOCUMENTATION, kwargs["feature_area"])
    assert len(item.states) == 1


# S4-10: a materially different re-ingestion creates a new proposed state, not a duplicate
def test_s4_10_materially_different_content_creates_new_state(memory):
    kwargs = _doc_kwargs()
    first = memory.ingest_existing_documentation(**kwargs)
    second = memory.ingest_existing_documentation(**{**kwargs, "content": "a revised caption reading"})

    assert second.version == first.version + 1
    assert second.status == StateStatus.PROPOSED
    # first state is untouched - proposing never supersedes/edits an existing proposal
    item = memory.get_or_create_knowledge_item(kwargs["key"], KnowledgeType.DOCUMENTATION, kwargs["feature_area"])
    assert item.states[0].status == StateStatus.PROPOSED
    assert item.states[0].content == kwargs["content"]


# S4-11: ingestion never dedupes against a maintainer decision with identical text (distinct evidence_type)
def test_s4_11_rejects_documentation_ingestion_over_a_maintainer_decision_key(memory):
    # updated for finding 4 (knowledge_type isolation): a maintainer
    # decision always creates an `editorial`-typed KnowledgeItem;
    # ingest_existing_documentation always requires `documentation`. The
    # same natural key colliding across the two bootstrap paths is
    # exactly the cross-type blending finding 4 forbids - it must be
    # rejected outright, not silently allowed to coexist as if they were
    # unrelated evidence on a shared item.
    shared = dict(
        key="desktop.filters.dedupe-check",
        feature_area="desktop.filters",
        content="Filters button says 'Filters'.",
        source_ref="same/ref",
        captured_by="same-actor",
    )
    memory.record_maintainer_decision(**shared)

    with pytest.raises(KnowledgeTypeMismatchError):
        memory.ingest_existing_documentation(**shared)

    item = memory.get_or_create_knowledge_item(shared["key"], KnowledgeType.EDITORIAL, shared["feature_area"])
    assert len(item.states) == 1  # the rejected ingestion created nothing


# S4-12: default relation_to_previous is NEW for a brand-new item, REFINES for a later one
def test_s4_12_default_relation_new_then_refines(memory):
    kwargs = _doc_kwargs()
    first = memory.ingest_existing_documentation(**kwargs)
    second = memory.ingest_existing_documentation(**{**kwargs, "content": "revised text"})

    assert first.relation_to_previous == Relation.NEW
    assert second.relation_to_previous == Relation.REFINES


# S4-13: explicit relation_to_previous is honored (e.g. a doc pass that contradicts current knowledge)
def test_s4_13_explicit_relation_is_honored(memory):
    state = memory.ingest_existing_documentation(**_doc_kwargs(relation_to_previous=Relation.CONTRADICTS))
    assert state.relation_to_previous == Relation.CONTRADICTS
    assert state.review_required is True


# S4-14: ingested proposals require an explicit approve_state to ever become current -
# proving the review/approval boundary is not bypassed by this ingestion path
def test_s4_14_explicit_approval_still_required_and_works_via_ordinary_lifecycle(memory):
    state = memory.ingest_existing_documentation(**_doc_kwargs())
    item = memory.get_or_create_knowledge_item(
        _doc_kwargs()["key"], KnowledgeType.DOCUMENTATION, "desktop.filters"
    )
    assert memory.get_current(item.id) is None

    memory.approve_state(item.id, state.version, approved_by="maintainer")
    current = memory.get_current(item.id)
    assert current is not None
    assert current.version == state.version
    assert current.approved_by == "maintainer"


# S4-15: round-trips through Slice 1 storage/loading unmodified
def test_s4_15_round_trips_through_slice1_loading(memory):
    state = memory.ingest_existing_documentation(**_doc_kwargs())
    item_id = memory.get_or_create_knowledge_item(
        _doc_kwargs()["key"], KnowledgeType.DOCUMENTATION, "desktop.filters"
    ).id

    reloaded = memory.get_knowledge_item(item_id)
    assert reloaded.states[0].version == state.version
    assert reloaded.states[0].content == state.content
    assert reloaded.states[0].status == StateStatus.PROPOSED
