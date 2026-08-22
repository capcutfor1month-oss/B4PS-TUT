"""Documentation Intelligence - Slice 1: read-only delta comparison.

Implements the approved Slice 1 specification as repaired against Codex
Audit 1 (FAIL, 7 findings) and Re-audit 1 (FAIL, 6 further findings). This
module never writes to Editorial Memory - no `propose_state`, no
`ingest_existing_documentation`, no `approve_state`. It reuses
`editorial-memory`'s existing models/retrieval/store APIs unmodified.

Locked boundaries this module enforces in code, not only documentation:

- Zero Editorial Memory writes (no mutating method of `EditorialMemory`
  is ever called).
- Product and documentation Knowledge are retrieved and reported
  separately - never merged into one object - and the exact KnowledgeItem
  referenced by `product_key` / `documentation_key` is type-checked
  against its expected `KnowledgeType` **unconditionally**, regardless of
  lifecycle status (Re-audit 1, DI-S1-02): even an item with no current
  state, only proposed states, or one the caller's own opt-in choices
  would not otherwise surface, still raises `KnowledgeTypeMismatchError`
  on a role/type mismatch. The type boundary is a property of the item's
  identity, not of what happens to be currently visible.
- Retrieval is exact-key only (the caller-supplied `product_key` /
  `documentation_key`), via the existing `get_current_by_key`. No
  embeddings, fuzzy matching, vector search, or semantic-ID resolution.
- A documentation KnowledgeItem's *current* approved state is tried
  first, exactly like the product side. A `proposed`-only documentation
  state is only ever surfaced when the caller explicitly opts in via
  `include_proposed_documentation`, and is always labeled `"proposed"`
  in the report - never presented as current truth.

Relation reasoning (Audit 1 finding 1 - repaired, accepted unchanged by
the founder after Re-audit 1):

`relation_candidate` is determined **by this module itself**, using only
bounded, deterministic structural rules - never a caller-supplied
semantic assertion. The rules this module is authorized to use, and no
others:

- No current product Knowledge exists, and at least one cited Evidence
  record is relevant (see below) -> `NEW`.
- Current product Knowledge exists, and the incoming claim text is
  *exactly* equal to the current content (after only whitespace/line-
  ending normalization - no case-folding, no similarity scoring, no
  token overlap), and at least one cited Evidence record is relevant ->
  `CONFIRMS`.
- Anything else -> **unresolved**. `REFINES`, `CONTRADICTS`, and
  `SUPERSEDES` are never produced by this slice - reaching them safely
  requires semantic judgment of natural-language content (LLM/
  embeddings/fuzzy matching), explicitly out of scope. This is an
  accepted, deliberate scope boundary, not an oversight.

Evidence relevance / sufficiency (Audit 1 finding 2, repaired; Re-audit 1
DI-S1-01, repaired again - this is the current, corrected rule):

A cited Evidence id must resolve (`get_evidence` succeeds, raising typed
`UnknownEvidenceError` otherwise) AND be *relevant* to count toward
`evidence_sufficiency`. Relevance is decided by exactly one test, with no
caller-influenceable alternative:

  The Evidence id already appears in `evidence_refs` of **any** state
  (any lifecycle status - `proposed`, `current`, `superseded`,
  `contradicted` - not only the current one) already recorded on the
  KnowledgeItem `product_key` resolves to.

This is the strongest, and now the *only*, relevance proof this module
uses: an independently persisted relationship, established through
Editorial Memory's own normal propose/approve lifecycle at some point in
the past, never through anything this `compare()` call's own arguments
assert about themselves. Earlier drafts also accepted a caller-supplied
`expected_verification_scope` intersected against the Evidence's own
`verification_scope` as an alternative relevance path - Codex correctly
identified that as exploitable: since both the "expected" scope and (in
principle) an Evidence's own scope are attacker/caller-influenceable
inputs to a single `compare()` call, a caller could fabricate an
apparent match for genuinely unrelated Evidence, producing a positive
NEW/CONFIRMS result with no real backing. That path has been removed
entirely - `verification_scope` plays no role in relevance any more.

If `product_key` does not resolve to any KnowledgeItem at all - the
subject has never been proposed, approved, or otherwise recorded under
that key by anyone - there is no persisted structure of any kind to
check Evidence against, and no amount of caller-supplied metadata in a
single `compare()` call can substitute for one. Per the founder's
explicit instruction, this fails conservatively: no Evidence can be
relevant, `evidence_sufficiency` is `"insufficient"`, and
`relation_candidate` is `None` ("unresolved") - even in what would
otherwise be the `NEW` case. This is a real, accepted limitation, not a
bug: a genuinely first-ever observation of a brand-new subject cannot be
safely classified `NEW` by this slice alone; it requires the subject to
already have at least one recorded state (of any status) whose evidence
already includes the id being cited now.

`documentation_vs_product` is derived the same deterministic way (exact
normalized-text equality against `matched_product`, when both are
present) and is capped at `{"aligned", "differs", "not_comparable"}` -
"conflicts" is not a reachable value, since distinguishing a genuine
semantic conflict from a benign restatement requires the same excluded
capability. This field never drives `relation_candidate` or
`product_change_signal` in either direction - a documentation delta,
however classified here, never implies a product-truth change by itself.
"""

from __future__ import annotations

import dataclasses
from typing import Optional, Sequence

from ._editorial_memory_import import (
    CurrentKnowledge,
    EditorialMemory,
    KnowledgeItem,
    KnowledgeType,
    KnowledgeTypeMismatchError,
    Relation,
    get_current_by_key,
    list_current_by_feature_area,
    slugify,
)

_NOTES_EXCERPT_LENGTH = 200

# Deterministic, non-gating lookup: what a given relation_candidate implies
# about product-state change. This is read *off* relation_candidate; it
# never influences what relation_candidate is allowed to be.
_PRODUCT_CHANGE_SIGNAL_BY_RELATION = {
    Relation.NEW: "not_applicable",
    Relation.CONFIRMS: "none",
    Relation.REFINES: "none",
    Relation.CONTRADICTS: "possible",
    Relation.SUPERSEDES: "possible",
}


def _normalize(text: str) -> str:
    """The only text transformation this module performs anywhere:
    collapse whitespace runs and strip the ends. Deliberately NOT
    case-folded, NOT tokenized, NOT compared by similarity - a bright-
    line structural normalization (irrelevant formatting only), not a
    semantic-leniency mechanism."""
    return " ".join(text.split())


def _resolve_item_by_key(memory: EditorialMemory, key: str) -> Optional[KnowledgeItem]:
    """Read-only key -> KnowledgeItem lookup, mirroring
    `retrieval._resolve_key`'s own collision convention exactly (an
    unknown key, or a key that collides at the slug level with a
    *different* stored key, both resolve to "no such item" rather than
    raising). Unlike `get_current_by_key`, this resolves the item
    regardless of whether it has ever had a state approved - required for
    (a) the KnowledgeType check to apply unconditionally (DI-S1-02) and
    (b) collecting evidence_refs across the item's full state history for
    relevance (DI-S1-01)."""
    item_id = slugify(key)
    data = memory.store.load_knowledge_item(item_id)
    if data is None:
        return None
    item = KnowledgeItem.from_dict(data)
    return item if item.key == key else None


def _resolve_typed_item(
    memory: EditorialMemory, key: Optional[str], expected_type: KnowledgeType
) -> Optional[KnowledgeItem]:
    """Resolve and type-check the exact KnowledgeItem `key` refers to, if
    any exists - unconditionally, regardless of lifecycle status. A
    wrong-typed item raises `KnowledgeTypeMismatchError` even when it has
    no current state, only proposed states, or would not otherwise be
    surfaced by the caller's own opt-in choices (Re-audit 1, DI-S1-02)."""
    if not key:
        return None
    item = _resolve_item_by_key(memory, key)
    if item is None:
        return None
    if item.knowledge_type != expected_type:
        raise KnowledgeTypeMismatchError(
            f"key {key!r} resolves to a KnowledgeItem of type "
            f"{item.knowledge_type.value!r}, not the expected "
            f"{expected_type.value!r} for this role"
        )
    return item


def _latest_proposed_state(item: KnowledgeItem):
    for state in reversed(item.states):
        if state.status.value == "proposed":
            return state
    return None


def _all_recorded_evidence_ids(item: Optional[KnowledgeItem]) -> frozenset:
    """Every Evidence id ever cited by any state (any lifecycle status) of
    `item` - the sole, persisted, non-caller-influenceable source of
    Evidence relevance this module uses (DI-S1-01)."""
    if item is None:
        return frozenset()
    ids = set()
    for state in item.states:
        ids.update(state.evidence_refs)
    return frozenset(ids)


def _knowledge_view(current: Optional[CurrentKnowledge], include_evidence_refs: bool) -> Optional[dict]:
    if current is None:
        return None
    view = {
        "item_id": current.id,
        "key": current.key,
        "version": current.version,
        "content": current.content,
        "status": current.status,
    }
    if include_evidence_refs:
        view["evidence_refs"] = list(current.evidence_refs)
    return view


@dataclasses.dataclass
class ComparisonReport:
    """The full read-only Slice 1 output. See module docstring and the
    approved specification for field semantics. `to_dict()` is the
    machine-readable form; every field is also directly attribute-
    accessible for a human-reviewing caller."""

    claim: dict
    matched_product: Optional[dict]
    matched_documentation: Optional[dict]
    documentation_vs_product: str
    relation_candidate: Optional[str]
    product_change_signal: str
    evidence_sufficiency: str
    unresolved_reason: Optional[str]
    review_required: bool
    cited_evidence: list
    other_feature_area_items: list

    def to_dict(self) -> dict:
        return {
            "claim": self.claim,
            "matched_knowledge": {
                "product": self.matched_product,
                "documentation": self.matched_documentation,
            },
            "documentation_vs_product": self.documentation_vs_product,
            "relation_candidate": self.relation_candidate,
            "product_change_signal": self.product_change_signal,
            "evidence_sufficiency": self.evidence_sufficiency,
            "unresolved_reason": self.unresolved_reason,
            "review_required": self.review_required,
            "provenance": {"cited_evidence": self.cited_evidence},
            "other_feature_area_items": self.other_feature_area_items,
        }


def compare(
    memory: EditorialMemory,
    *,
    claim_text: str,
    source_ref: str,
    feature_area: str,
    product_key: Optional[str] = None,
    documentation_key: Optional[str] = None,
    evidence_ids: Sequence[str] = (),
    include_proposed_documentation: bool = False,
) -> ComparisonReport:
    """Slice 1's one entry point. Read-only: calls only
    `get_current_by_key`, `list_current_by_feature_area`, and
    `get_evidence` on `memory` - never a mutating method.

    Every field of the returned report is derived deterministically from
    what is actually retrieved and cited - there is no caller-supplied
    relation, judgment, or scope-matching parameter. See the module
    docstring for the exact bounded rules used.

    Raises `UnknownEvidenceError` if any id in `evidence_ids` does not
    resolve, and `KnowledgeTypeMismatchError` if the KnowledgeItem
    `product_key` / `documentation_key` resolves to (if any) is not of
    the expected type for that role - checked unconditionally, regardless
    of lifecycle status. Both are input/reference errors, not epistemic
    uncertainty, so neither is silently downgraded to "unresolved".
    """
    # --- Retrieval: dual-key, exact-key only, product and documentation
    # kept fully separate, each type-checked unconditionally. ------------
    product_item = _resolve_typed_item(memory, product_key, KnowledgeType.PRODUCT)
    product_current = get_current_by_key(memory, product_key) if product_key else None
    product_view = _knowledge_view(product_current, include_evidence_refs=True)

    documentation_item = _resolve_typed_item(memory, documentation_key, KnowledgeType.DOCUMENTATION)
    documentation_current = get_current_by_key(memory, documentation_key) if documentation_key else None
    documentation_view: Optional[dict]
    if documentation_current is not None:
        documentation_view = _knowledge_view(documentation_current, include_evidence_refs=False)
    elif include_proposed_documentation and documentation_item is not None:
        proposed = _latest_proposed_state(documentation_item)
        documentation_view = (
            {
                "item_id": documentation_item.id,
                "key": documentation_item.key,
                "version": proposed.version,
                "content": proposed.content,
                "status": "proposed",
            }
            if proposed is not None
            else None
        )
    else:
        documentation_view = None

    # Informational only - never used to select a match.
    matched_keys = {v["key"] for v in (product_view, documentation_view) if v is not None}
    other_feature_area_items = [
        {"key": ck.key, "knowledge_type": ck.knowledge_type.value}
        for ck in list_current_by_feature_area(memory, feature_area)
        if ck.key not in matched_keys
    ]

    # --- Evidence: resolve, then determine relevance from persisted
    # repository state only - never from anything this call's own
    # arguments assert about themselves (DI-S1-01). ----------------------
    recorded_evidence_ids = _all_recorded_evidence_ids(product_item)

    cited_evidence = []
    any_relevant = False
    for evidence_id in evidence_ids:
        ev = memory.get_evidence(evidence_id)  # raises UnknownEvidenceError if invalid
        relevant = evidence_id in recorded_evidence_ids
        any_relevant = any_relevant or relevant
        notes = ev.notes or ""
        cited_evidence.append(
            {
                "id": ev.id,
                "evidence_type": ev.evidence_type.value,
                "source_ref": ev.source_ref,
                "notes_excerpt": notes[:_NOTES_EXCERPT_LENGTH] or None,
                "relevant": relevant,
            }
        )
    evidence_sufficiency = "sufficient" if any_relevant else "insufficient"

    # --- documentation_vs_product: deterministic exact-match only. -------
    if product_view is None:
        documentation_vs_product = "not_comparable"
    elif _normalize(claim_text) == _normalize(product_view["content"]):
        documentation_vs_product = "aligned"
    else:
        documentation_vs_product = "differs"

    # --- relation_candidate: bounded deterministic rules, this module's
    # own decision - never a caller assertion. ---------------------------
    relation_candidate: Optional[Relation] = None
    unresolved_reason: Optional[str] = None

    if evidence_sufficiency == "insufficient":
        unresolved_reason = (
            "no Evidence relevant to this subject is recorded in Editorial Memory "
            "(product_key has no persisted evidence-linked state to check against, "
            "or none of the cited Evidence ids appear in it)"
        )
    elif product_view is None:
        relation_candidate = Relation.NEW
    elif _normalize(claim_text) == _normalize(product_view["content"]):
        relation_candidate = Relation.CONFIRMS
    else:
        unresolved_reason = (
            "claim text differs from current product knowledge; safely distinguishing "
            "REFINES/CONTRADICTS/SUPERSEDES requires semantic judgment outside this "
            "slice's bounded deterministic rules"
        )

    product_change_signal = (
        _PRODUCT_CHANGE_SIGNAL_BY_RELATION[relation_candidate] if relation_candidate is not None else "unresolved"
    )

    review_required = relation_candidate is None or relation_candidate == Relation.CONTRADICTS

    return ComparisonReport(
        claim={"text": claim_text, "source_ref": source_ref, "feature_area": feature_area},
        matched_product=product_view,
        matched_documentation=documentation_view,
        documentation_vs_product=documentation_vs_product,
        relation_candidate=relation_candidate.value if relation_candidate is not None else None,
        product_change_signal=product_change_signal,
        evidence_sufficiency=evidence_sufficiency,
        unresolved_reason=unresolved_reason,
        review_required=review_required,
        cited_evidence=cited_evidence,
        other_feature_area_items=other_feature_area_items,
    )
