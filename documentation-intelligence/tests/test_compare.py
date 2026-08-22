"""Tests for Documentation Intelligence Slice 1 (`lib.compare`), repaired
against Codex Audit 1 (FAIL, 7 findings) and Re-audit 1 (FAIL, 6 further
findings).

Split per the approved specification's real-vs-synthetic requirement:

- `Test*Real*` classes exercise real project data (the actual production
  Editorial Memory store under `documentation-artifacts/bridge-ui-evidence/
  store`, read-only). `compare()` is read-only by construction; every
  real-data test snapshots the store's exact on-disk bytes before/after
  and asserts no change - not just an id-list comparison.
- `Test*Synthetic*` classes use controlled, locally-constructed fixtures
  (a temp Editorial Memory store) for cases the real dataset does not
  contain. Clearly not real collected Bridge evidence.

Findings covered here specifically:
- Audit 1 finding 1 / accepted relation model: `TestDeterministicRelationReasoning`.
- Audit 1 finding 2 + Re-audit 1 DI-S1-01 (Evidence relevance must come
  from an independently persisted relationship, never caller-supplied
  scope matching): `TestEvidenceRelevance`.
- Audit 1 finding 3 + Re-audit 1 DI-S1-02 (KnowledgeType enforcement
  applies to the exact referenced item regardless of lifecycle status):
  `TestKnowledgeTypeEnforcement`.
- Audit 1 finding 4 (bare-`lib`-first import order): `test_import_order.py`.
- Re-audit 1 DI-S1-04 (alias-first import order): `test_import_alias_first.py`.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from documentation_intelligence.compare import compare  # noqa: E402
from documentation_intelligence._editorial_memory_import import (  # noqa: E402
    EditorialMemory,
    EvidenceQuality,
    EvidenceType,
    KnowledgeType,
    KnowledgeTypeMismatchError,
    Relation,
    UnknownEvidenceError,
)

REAL_STORE = (
    Path(__file__).resolve().parents[2]
    / "documentation-artifacts"
    / "bridge-ui-evidence"
    / "store"
)

REAL_PINNED_CONTENT = (
    "Pinning a message (via a channel message's 'Pin' action) bookmarks it for all "
    "members of that channel and adds it to the channel's Pinned Messages list, "
    "which is reached via the channel header Options kebab -> 'Pinned Messages'. "
    "A confirmation step is shown before pinning, offering an optional room "
    "notification; pinned messages are described in-product as 'visible to "
    "everyone', matching the documentation's 'for all members of the channel' claim."
)
REAL_PINNED_EVIDENCE = ["ev-ed4f26e92961", "ev-f93c8c0c3611"]  # both in the approved state's evidence_refs
REAL_THREAD_EVIDENCE = ["ev-85751d76ea0f", "ev-dce7186b2c30"]
REAL_OPTIONS_MENU_EVIDENCE = "ev-f93c8c0c3611"  # Batch 5 Options-kebab inventory; no "Livestream" entry


def _real_memory() -> EditorialMemory:
    assert REAL_STORE.exists(), f"real store not found at {REAL_STORE}"
    return EditorialMemory(str(REAL_STORE))


def _store_file_hashes(root: Path) -> dict:
    """Byte-level snapshot: sha256 of every file under the store, keyed by
    relative path. Stricter than an id-list comparison - catches any
    incidental content mutation, not only added/removed records."""
    hashes = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


class TestRealRegressionCases:
    """Cases A, B, C, H, L, M from the approved specification, against
    real project data. Every test snapshots the real store's exact bytes
    before/after and asserts no change (TEST-DI-01: this now includes
    every real-data test in this class, with no exceptions)."""

    def test_a_editorial_only_wording_change_no_product_evidence(self):
        before = _store_file_hashes(REAL_STORE)

        report = compare(
            _real_memory(),
            claim_text=(
                "Managing Access Requests (Channel Owners Only): open the public "
                "channel with pending access requests, click Members, click View "
                "Join Requests, review and Accept/Reject."
            ),
            source_ref="documentation-artifacts/masterslide/updated/Masterslides.pdf#page=139",
            feature_area="desktop.channels",
        )

        assert report.matched_product is None
        assert report.evidence_sufficiency == "insufficient"
        assert report.relation_candidate is None
        assert report.product_change_signal == "unresolved"
        assert report.documentation_vs_product == "not_comparable"
        assert _store_file_hashes(REAL_STORE) == before

    def test_b_documentation_semantic_change_no_bridge_evidence(self):
        before = _store_file_hashes(REAL_STORE)

        report = compare(
            _real_memory(),
            claim_text=(
                "Create Team (Pro Feature): enter the Team Name and optionally "
                "add Owners, Members, Admins, and Dispatchers."
            ),
            source_ref="documentation-artifacts/masterslide/updated/Masterslides.pdf#page=120",
            feature_area="desktop.teams",
        )

        assert report.matched_product is None
        assert report.evidence_sufficiency == "insufficient"
        assert report.relation_candidate is None
        assert _store_file_hashes(REAL_STORE) == before

    def test_c_removal_weak_absence_based_corroboration_not_relevant(self):
        """The only real corroboration for Livestream removal is that it's
        absent from the real Options-kebab inventory Evidence. That
        Evidence resolves, but has no persisted evidence_refs link to any
        KnowledgeItem for this subject (none exists) - so it must NOT
        count as relevant, and the case must stay unresolved rather than
        a fabricated relation."""
        before = _store_file_hashes(REAL_STORE)

        report = compare(
            _real_memory(),
            claim_text="Setup Livestream: Options -> Livestream -> enter Livestream URL -> Save.",
            source_ref="MASTER Complete Bridge4PS Desktop-Browser Feature Tutorials.pptx#slide154",
            feature_area="desktop.channels",
            evidence_ids=[REAL_OPTIONS_MENU_EVIDENCE],
        )

        assert len(report.cited_evidence) == 1
        assert report.cited_evidence[0]["id"] == REAL_OPTIONS_MENU_EVIDENCE
        assert report.cited_evidence[0]["relevant"] is False
        assert report.evidence_sufficiency == "insufficient"
        assert report.relation_candidate is None
        assert report.product_change_signal == "unresolved"
        assert _store_file_hashes(REAL_STORE) == before

    def test_h_no_prior_knowledge_and_no_evidence_is_unresolved_not_new(self):
        before = _store_file_hashes(REAL_STORE)

        report = compare(
            _real_memory(),
            claim_text=(
                "Create Workspace: click plus, enter name/topic/members, "
                "Configure the Advanced settings as needed, then click Create."
            ),
            source_ref="documentation-artifacts/masterslide/updated/Masterslides.pdf#page=108",
            feature_area="desktop.workspaces",
        )

        assert report.matched_product is None
        assert report.relation_candidate is None
        assert report.product_change_signal == "unresolved"
        assert _store_file_hashes(REAL_STORE) == before

    def test_l_thread_residual_uncertainty_stays_unresolved(self):
        """Real thread-recording Evidence exists and resolves, but no
        KnowledgeItem exists for this subject at all - so there is no
        persisted evidence_refs link of any kind to check against, and
        the case stays unresolved."""
        before = _store_file_hashes(REAL_STORE)

        report = compare(
            _real_memory(),
            claim_text=(
                "Individual thread reply view: opens from a Threads-panel row or "
                "a message's View thread; shows parent message, replies, a "
                "composer, and an Also send to channel checkbox."
            ),
            source_ref="Expert resources/thread 1.mp4; Expert resources/thread 2.mp4",
            feature_area="desktop.threads",
            evidence_ids=REAL_THREAD_EVIDENCE,
        )

        assert len(report.cited_evidence) == 2
        assert all(e["relevant"] is False for e in report.cited_evidence)
        assert report.evidence_sufficiency == "insufficient"
        assert report.relation_candidate is None
        assert _store_file_hashes(REAL_STORE) == before

    def test_m_pinned_messages_confirms_via_exact_text_and_linked_evidence(self):
        """The real, approved Pinned Messages case: citing the exact
        Evidence ids already linked in the approved state's own
        `evidence_refs` makes them deterministically relevant, and
        supplying the exact current content as the incoming claim
        deterministically yields CONFIRMS (no semantic judgment needed -
        literal equality). This is Slice 1's own reasoning producing a
        real, non-null relation from real data."""
        before = _store_file_hashes(REAL_STORE)

        report = compare(
            _real_memory(),
            claim_text=REAL_PINNED_CONTENT,
            source_ref="documentation-artifacts/masterslide/updated/Masterslides.pdf#page=75",
            feature_area="desktop.messages",
            product_key="pinned-messages-pin-action-behavior",
            documentation_key="pinned-messages-masterslide-claim",
            evidence_ids=REAL_PINNED_EVIDENCE,
            include_proposed_documentation=True,
        )

        assert report.matched_product is not None
        assert report.matched_product["key"] == "pinned-messages-pin-action-behavior"
        assert report.matched_product["status"] == "current"

        assert all(e["relevant"] is True for e in report.cited_evidence)
        assert report.evidence_sufficiency == "sufficient"

        assert report.relation_candidate == "confirms"
        assert report.product_change_signal == "none"
        assert report.review_required is False

        assert report.matched_documentation is not None
        assert report.matched_documentation["key"] == "pinned-messages-masterslide-claim"
        assert report.matched_documentation["status"] == "proposed"

        assert _store_file_hashes(REAL_STORE) == before

    def test_m_documentation_not_surfaced_unless_opted_in(self):
        before = _store_file_hashes(REAL_STORE)

        report = compare(
            _real_memory(),
            claim_text="Pin action.",
            source_ref="n/a",
            feature_area="desktop.messages",
            documentation_key="pinned-messages-masterslide-claim",
        )

        assert report.matched_documentation is None
        assert _store_file_hashes(REAL_STORE) == before

    def test_m_evidence_cited_but_not_linked_is_not_relevant(self):
        """Adversarial real-data case (TEST-DI-01: previously missing the
        byte-snapshot bookend, added here): cite a real, resolvable
        Evidence id (the thread recordings) against the Pinned Messages
        product item - it exists, but was never cited by any state of
        that specific KnowledgeItem, so it must not count as relevant
        even though it's a genuine record."""
        before = _store_file_hashes(REAL_STORE)

        report = compare(
            _real_memory(),
            claim_text=REAL_PINNED_CONTENT,
            source_ref="n/a",
            feature_area="desktop.messages",
            product_key="pinned-messages-pin-action-behavior",
            evidence_ids=["ev-85751d76ea0f"],  # real thread Evidence, never cited by this item
        )
        assert report.cited_evidence[0]["relevant"] is False
        assert report.evidence_sufficiency == "insufficient"
        assert report.relation_candidate is None

        assert _store_file_hashes(REAL_STORE) == before


class TestDeterministicRelationReasoning:
    """The accepted relation model, proven as Slice 1's own derivation,
    never a caller assertion. There is no `asserted_relation` parameter
    at all."""

    @pytest.fixture()
    def memory(self, tmp_path):
        return EditorialMemory(str(tmp_path / "store"))

    def _approved_product_item(self, memory, key="synthetic.widget-behavior", content="Widget does X."):
        ev = memory.record_evidence(
            EvidenceType.BROWSER_OBSERVATION,
            source_ref="synthetic-fixture://baseline",
            captured_by="test fixture",
            notes="Synthetic baseline observation, not real Bridge evidence.",
            evidence_quality=EvidenceQuality.HIGH,
        )
        item = memory.get_or_create_knowledge_item(key, KnowledgeType.PRODUCT, "synthetic.widget")
        memory.propose_state(item.id, content, [ev.id], relation_to_previous=Relation.NEW)
        memory.approve_state(item.id, 1, approved_by="test fixture")
        return key, ev

    def test_new_when_item_exists_with_no_current_but_evidence_already_linked(self, memory):
        """DI-S1-01-consistent NEW case: the subject already has a
        KnowledgeItem with a *proposed* (never approved) state whose
        evidence_refs already include the cited Evidence - a genuinely
        persisted relationship, just not yet approved to `current`. No
        current product Knowledge exists (get_current_by_key returns
        None), so this is the NEW branch."""
        ev = memory.record_evidence(
            EvidenceType.RECORDING, source_ref="synthetic-fixture://new", captured_by="test fixture", notes="n",
        )
        item = memory.get_or_create_knowledge_item("synthetic.new-widget", KnowledgeType.PRODUCT, "synthetic.widget")
        memory.propose_state(item.id, "New widget does Z.", [ev.id], relation_to_previous=Relation.NEW)
        # deliberately not approved - product_key must still resolve no *current* state

        report = compare(
            memory,
            claim_text="New widget does Z.",
            source_ref="synthetic",
            feature_area="synthetic.widget",
            product_key="synthetic.new-widget",
            evidence_ids=[ev.id],
        )
        assert report.matched_product is None  # nothing current
        assert report.relation_candidate == "new"
        assert report.product_change_signal == "not_applicable"

    def test_new_never_produced_when_no_knowledgeitem_exists_at_all(self, memory):
        """DI-S1-01 core regression: with no `product_key` (or one that
        resolves to no KnowledgeItem at all), there is no persisted
        structure of any kind to check Evidence against - NEW must not
        be produced no matter how the Evidence is described."""
        ev = memory.record_evidence(
            EvidenceType.RECORDING, source_ref="x", captured_by="test fixture", notes="no persisted link exists",
        )
        report = compare(
            memory,
            claim_text="New widget does Z.",
            source_ref="synthetic",
            feature_area="synthetic.widget",
            evidence_ids=[ev.id],
            # no product_key at all -> nothing persisted to check relevance against
        )
        assert report.relation_candidate is None
        assert "no Evidence relevant" in report.unresolved_reason

    def test_confirms_only_on_exact_normalized_text_match(self, memory):
        key, ev = self._approved_product_item(memory, content="Widget does X.")
        report = compare(
            memory,
            claim_text="Widget   does\nX.  ",  # whitespace-only difference
            source_ref="synthetic",
            feature_area="synthetic.widget",
            product_key=key,
            evidence_ids=[ev.id],  # already linked -> relevant
        )
        assert report.relation_candidate == "confirms"
        assert report.product_change_signal == "none"
        assert report.review_required is False

    def test_confirms_requires_relevant_evidence_too_not_text_match_alone(self, memory):
        """The accepted model requires *both* an exact text match *and*
        safely relevant Evidence for CONFIRMS - text match alone, with no
        relevant Evidence cited, must stay unresolved."""
        key, _ev = self._approved_product_item(memory, content="Widget does X.")
        unrelated_ev = memory.record_evidence(
            EvidenceType.RECORDING, source_ref="unrelated", captured_by="t", notes="never cited by this item",
        )
        report = compare(
            memory,
            claim_text="Widget does X.",  # exact match to current content
            source_ref="synthetic",
            feature_area="synthetic.widget",
            product_key=key,
            evidence_ids=[unrelated_ev.id],  # but not a relevant/linked Evidence id
        )
        assert report.relation_candidate is None
        assert report.evidence_sufficiency == "insufficient"

    def test_differing_text_is_unresolved_not_refines_or_contradicts(self, memory):
        """Differing text against real, relevant Evidence must NOT
        produce REFINES, CONTRADICTS, or SUPERSEDES - this slice has no
        deterministic way to distinguish them, so it must stay
        unresolved. This is the accepted, deliberate scope boundary."""
        key, ev = self._approved_product_item(memory, content="Widget does X.")
        report = compare(
            memory,
            claim_text="Widget does X via a keyboard shortcut.",
            source_ref="synthetic",
            feature_area="synthetic.widget",
            product_key=key,
            evidence_ids=[ev.id],
        )
        assert report.relation_candidate is None
        assert report.relation_candidate not in {"refines", "contradicts", "supersedes"}
        assert report.product_change_signal == "unresolved"
        assert report.review_required is True  # unresolved always requires review

    def test_contradicting_looking_text_still_unresolved_not_contradicts(self, memory):
        """Even text that a human would obviously read as a contradiction
        must not be auto-classified CONTRADICTS - Slice 1 has no
        deterministic (non-semantic) way to tell "contradicts" apart from
        any other kind of difference."""
        key, ev = self._approved_product_item(memory, content="Widget is visible to all users.")
        report = compare(
            memory,
            claim_text="Widget is NOT visible to all users.",
            source_ref="synthetic",
            feature_area="synthetic.widget",
            product_key=key,
            evidence_ids=[ev.id],
        )
        assert report.relation_candidate is None
        assert report.product_change_signal == "unresolved"

    def test_new_never_produced_when_current_already_exists(self, memory):
        key, ev = self._approved_product_item(memory)
        report = compare(
            memory,
            claim_text="Something entirely different.",
            source_ref="synthetic",
            feature_area="synthetic.widget",
            product_key=key,
            evidence_ids=[ev.id],
        )
        assert report.relation_candidate != "new"

    def test_documentation_vs_product_capped_at_three_deterministic_values(self, memory):
        key, ev = self._approved_product_item(memory, content="Widget is visible to all users.")
        aligned = compare(
            memory, claim_text="Widget is visible to all users.", source_ref="s",
            feature_area="synthetic.widget", product_key=key, evidence_ids=[ev.id],
        )
        differs = compare(
            memory, claim_text="Widget is admin-only.", source_ref="s",
            feature_area="synthetic.widget", product_key=key, evidence_ids=[ev.id],
        )
        not_comparable = compare(
            memory, claim_text="Widget is admin-only.", source_ref="s", feature_area="synthetic.widget",
        )
        assert aligned.documentation_vs_product == "aligned"
        assert differs.documentation_vs_product == "differs"
        assert not_comparable.documentation_vs_product == "not_comparable"
        # "conflicts" is deliberately not a reachable value - see module docstring.
        assert {aligned.documentation_vs_product, differs.documentation_vs_product,
                not_comparable.documentation_vs_product} <= {"aligned", "differs", "not_comparable"}


class TestEvidenceRelevance:
    """Audit 1 finding 2, repaired again per Re-audit 1 DI-S1-01: positive
    Evidence relevance must come from an independently persisted
    relationship already present in repository state - never from
    anything a single `compare()` call's own arguments assert about
    themselves. There is no `expected_verification_scope` parameter
    (or any other scope-matching mechanism) any more."""

    @pytest.fixture()
    def memory(self, tmp_path):
        return EditorialMemory(str(tmp_path / "store"))

    def test_unrelated_evidence_not_relevant(self, memory):
        item = memory.get_or_create_knowledge_item("synthetic.a", KnowledgeType.PRODUCT, "synthetic.area")
        base_ev = memory.record_evidence(EvidenceType.RECORDING, source_ref="a", captured_by="t", notes="a")
        memory.propose_state(item.id, "A does X.", [base_ev.id], relation_to_previous=Relation.NEW)
        memory.approve_state(item.id, 1, approved_by="t")

        unrelated_ev = memory.record_evidence(
            EvidenceType.RECORDING, source_ref="unrelated", captured_by="t",
            notes="Completely unrelated subject.",
        )
        report = compare(
            memory, claim_text="A does X.", source_ref="s", feature_area="synthetic.area",
            product_key="synthetic.a", evidence_ids=[unrelated_ev.id],
        )
        assert report.cited_evidence[0]["relevant"] is False
        assert report.evidence_sufficiency == "insufficient"
        assert report.relation_candidate is None

    def test_di_s1_01_reproduction_scope_like_metadata_alone_is_never_sufficient(self, memory):
        """Exact Codex reproduction: Evidence whose own metadata (notes,
        source_ref) *looks* thematically related to the claim, and would
        have matched under the old (removed) caller-supplied
        `expected_verification_scope` mechanism, must still be
        insufficient on its own - there is no scope-matching path left at
        all, and this Evidence was never actually cited by any state of
        the target KnowledgeItem."""
        item = memory.get_or_create_knowledge_item("synthetic.widget2", KnowledgeType.PRODUCT, "synthetic.area")
        base_ev = memory.record_evidence(EvidenceType.RECORDING, source_ref="a", captured_by="t", notes="baseline")
        memory.propose_state(item.id, "Widget2 does X.", [base_ev.id], relation_to_previous=Relation.NEW)
        memory.approve_state(item.id, 1, approved_by="t")

        lookalike_ev = memory.record_evidence(
            EvidenceType.RECORDING,
            source_ref="synthetic-fixture://widget2-visual-workflow",
            captured_by="t",
            notes="Widget2 visual workflow observation - thematically about the exact same subject.",
            verification_scope=["visual", "workflow"],  # would have matched an old expected_verification_scope=[...]
        )
        report = compare(
            memory,
            claim_text="Widget2 does X.",
            source_ref="s",
            feature_area="synthetic.area",
            product_key="synthetic.widget2",
            evidence_ids=[lookalike_ev.id],
            # note: compare() no longer even accepts a scope-matching argument -
            # this call itself proves the exploit path is gone at the API level.
        )
        assert report.cited_evidence[0]["relevant"] is False
        assert report.evidence_sufficiency == "insufficient"
        assert report.relation_candidate is None
        assert report.product_change_signal == "unresolved"

    def test_relevant_via_proposed_state_history_not_only_current(self, memory):
        """Relevance is checked across the item's *full* state history
        (any lifecycle status), not only its current state - proven here
        via a second, still-`proposed` state citing a new Evidence id
        that was never part of the original approved state."""
        item = memory.get_or_create_knowledge_item("synthetic.b", KnowledgeType.PRODUCT, "synthetic.area")
        base_ev = memory.record_evidence(EvidenceType.RECORDING, source_ref="a", captured_by="t", notes="a")
        memory.propose_state(item.id, "B does X.", [base_ev.id], relation_to_previous=Relation.NEW)
        memory.approve_state(item.id, 1, approved_by="t")

        second_ev = memory.record_evidence(EvidenceType.RECORDING, source_ref="b", captured_by="t", notes="b")
        memory.propose_state(item.id, "B does X, refined.", [second_ev.id], relation_to_previous=Relation.REFINES)
        # left proposed, not approved - still a real, persisted evidence_refs link

        report = compare(
            memory, claim_text="B does X.", source_ref="s", feature_area="synthetic.area",
            product_key="synthetic.b", evidence_ids=[second_ev.id],
        )
        assert report.cited_evidence[0]["relevant"] is True
        assert report.evidence_sufficiency == "sufficient"

    def test_absence_only_evidence_not_relevant(self, memory):
        """An inventory Evidence record that simply doesn't mention the
        claimed subject (an absence, not a direct observation), and was
        never cited by any state of the target item, must not count as
        relevant just because it resolves."""
        inventory_ev = memory.record_evidence(
            EvidenceType.BROWSER_OBSERVATION, source_ref="menu-inventory", captured_by="t",
            notes="Full menu inventory: Files, Pinned Messages, Starred Messages. No 'Foo' item present.",
        )
        report = compare(
            memory, claim_text="Foo feature removed.", source_ref="s", feature_area="synthetic.area",
            evidence_ids=[inventory_ev.id],
        )
        assert report.cited_evidence[0]["relevant"] is False
        assert report.relation_candidate is None


class TestKnowledgeTypeEnforcement:
    """Audit 1 finding 3, repaired again per Re-audit 1 DI-S1-02: the
    exact KnowledgeItem `product_key`/`documentation_key` refers to is
    type-checked unconditionally, regardless of lifecycle status."""

    @pytest.fixture()
    def memory(self, tmp_path):
        return EditorialMemory(str(tmp_path / "store"))

    def test_product_key_resolving_to_documentation_type_raises(self, memory):
        ev = memory.record_evidence(EvidenceType.EXISTING_DOCUMENTATION, source_ref="s", captured_by="t", notes="n")
        item = memory.get_or_create_knowledge_item("synthetic.doc", KnowledgeType.DOCUMENTATION, "synthetic.area")
        memory.propose_state(item.id, "Doc claim.", [ev.id], relation_to_previous=Relation.NEW)
        memory.approve_state(item.id, 1, approved_by="t")

        with pytest.raises(KnowledgeTypeMismatchError):
            compare(
                memory, claim_text="x", source_ref="s", feature_area="synthetic.area",
                product_key="synthetic.doc",  # wrong role: this key is a documentation item
            )

    def test_documentation_key_resolving_to_product_type_raises(self, memory):
        ev = memory.record_evidence(EvidenceType.BROWSER_OBSERVATION, source_ref="s", captured_by="t", notes="n")
        item = memory.get_or_create_knowledge_item("synthetic.prod", KnowledgeType.PRODUCT, "synthetic.area")
        memory.propose_state(item.id, "Product claim.", [ev.id], relation_to_previous=Relation.NEW)
        memory.approve_state(item.id, 1, approved_by="t")

        with pytest.raises(KnowledgeTypeMismatchError):
            compare(
                memory, claim_text="x", source_ref="s", feature_area="synthetic.area",
                documentation_key="synthetic.prod",  # wrong role: this key is a product item
                include_proposed_documentation=True,
            )

    def test_wrong_type_not_silently_accepted_as_none_either(self, memory):
        """A swapped-role key must raise, not silently resolve to None as
        if nothing existed - that would hide a real caller error as
        epistemic uncertainty."""
        ev = memory.record_evidence(EvidenceType.BROWSER_OBSERVATION, source_ref="s", captured_by="t", notes="n")
        item = memory.get_or_create_knowledge_item("synthetic.prod2", KnowledgeType.PRODUCT, "synthetic.area")
        memory.propose_state(item.id, "Product claim.", [ev.id], relation_to_previous=Relation.NEW)
        memory.approve_state(item.id, 1, approved_by="t")

        with pytest.raises(KnowledgeTypeMismatchError):
            compare(memory, claim_text="x", source_ref="s", feature_area="a", documentation_key="synthetic.prod2")

    def test_product_key_wrong_type_raises_even_with_no_current_state(self, memory):
        """DI-S1-02 core regression: an item with only a *proposed*
        (never approved) state - `get_current_by_key` would return None
        for it - must still be type-checked. Build-1-era code resolved
        the item only via `get_current_by_key`, so a wrong-typed item
        with no current state silently passed through as if nothing
        existed at all."""
        ev = memory.record_evidence(EvidenceType.EXISTING_DOCUMENTATION, source_ref="s", captured_by="t", notes="n")
        item = memory.get_or_create_knowledge_item(
            "synthetic.doc-proposed-only", KnowledgeType.DOCUMENTATION, "synthetic.area"
        )
        memory.propose_state(item.id, "Doc claim, never approved.", [ev.id], relation_to_previous=Relation.NEW)
        # deliberately not approved - no current state exists for this item at all

        with pytest.raises(KnowledgeTypeMismatchError):
            compare(
                memory, claim_text="x", source_ref="s", feature_area="synthetic.area",
                product_key="synthetic.doc-proposed-only",
            )

    def test_documentation_key_wrong_type_raises_even_when_opt_in_is_false(self, memory):
        """DI-S1-02 core regression: the type check must fire even when
        `include_proposed_documentation=False` (the default) - the
        Build-1-era code only type-checked the documentation side inside
        the opt-in branch, so a wrong-typed key with no current state and
        opt-in left off skipped the check entirely."""
        ev = memory.record_evidence(EvidenceType.BROWSER_OBSERVATION, source_ref="s", captured_by="t", notes="n")
        item = memory.get_or_create_knowledge_item(
            "synthetic.prod-proposed-only", KnowledgeType.PRODUCT, "synthetic.area"
        )
        memory.propose_state(item.id, "Product claim, never approved.", [ev.id], relation_to_previous=Relation.NEW)
        # deliberately not approved - no current state exists for this item at all

        with pytest.raises(KnowledgeTypeMismatchError):
            compare(
                memory, claim_text="x", source_ref="s", feature_area="synthetic.area",
                documentation_key="synthetic.prod-proposed-only",
                include_proposed_documentation=False,  # explicit default - the check must still fire
            )


class TestZeroWriteGuarantee:
    """compare() must never call a mutating EditorialMemory method."""

    def test_no_evidence_or_knowledge_created_by_compare(self, tmp_path):
        memory = EditorialMemory(str(tmp_path / "store"))
        ev = memory.record_evidence(
            EvidenceType.BROWSER_OBSERVATION,
            source_ref="synthetic-fixture://x",
            captured_by="test fixture",
            notes="baseline",
        )
        z_item = memory.get_or_create_knowledge_item("synthetic.z", KnowledgeType.PRODUCT, "synthetic.area")
        memory.propose_state(z_item.id, "Z does A.", [ev.id])

        before_ev = sorted(memory.store.list_evidence_ids())
        before_items = {
            item_id: memory.get_knowledge_item(item_id).to_dict()
            for item_id in memory.store.list_knowledge_item_ids()
        }

        compare(
            memory,
            claim_text="Z does A.",
            source_ref="synthetic",
            feature_area="synthetic.area",
            product_key="synthetic.z",
            evidence_ids=[ev.id],
        )

        after_ev = sorted(memory.store.list_evidence_ids())
        after_items = {
            item_id: memory.get_knowledge_item(item_id).to_dict()
            for item_id in memory.store.list_knowledge_item_ids()
        }
        assert before_ev == after_ev
        assert before_items == after_items

    def test_invalid_evidence_id_raises_typed_error_not_silently_unresolved(self, tmp_path):
        memory = EditorialMemory(str(tmp_path / "store"))
        with pytest.raises(UnknownEvidenceError):
            compare(
                memory,
                claim_text="Anything.",
                source_ref="synthetic",
                feature_area="synthetic.area",
                evidence_ids=["ev-does-not-exist"],
            )
