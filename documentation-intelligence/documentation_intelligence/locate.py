"""Documentation Intelligence - Slice 2: Existing Documentation Text Locator.

Implements the approved Slice 2 specification
(`openspec/changes/documentation-intelligence-slice-2/spec.md`). Read-only:
given one target `.pptx` and one already-known *existing-documentation*
text string, deterministically locates that text's slide/shape in the
deck via the existing, unmodified Safe PPT Engine `inspect_deck()`, or
reports an explicit unresolved result. Reuses `inspect_deck()` unchanged;
adds no new deck-parsing or Safe PPT Engine capability.

Locked boundaries this module enforces in code, not only documentation:

- Zero PPT mutation - no Safe PPT Engine mutation primitive
  (`set_shape_text`, `move_shape`, `resize_shape`, `set_shape_geometry`,
  `replace_picture`) is called or imported anywhere in this module.
- Zero Editorial Memory access - this function takes no `EditorialMemory`
  handle, no product/documentation key, and performs no retrieval of any
  kind. Approved **product** Knowledge never participates in locating
  existing documentation text - product truth and documentation wording
  are separate concepts, and only the caller-supplied
  `documentation_text` is ever searched for.
- Deterministic, structural matching only - exact text equality,
  whitespace-normalized equality, or unambiguous bounded substring
  containment. No fuzzy/semantic/embedding/LLM matching.
- Conservative ambiguity: every shape that matches by any rule is one
  candidate, counted once. Zero candidates or two-or-more candidates both
  resolve to an explicit `unresolved` result with a stated reason -
  never a guess, never "pick the first."
"""

from __future__ import annotations

import dataclasses
from typing import Optional

from ._safe_ppt_engine_import import inspect_deck

__all__ = ["LocateResult", "locate_documentation_text"]


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


@dataclasses.dataclass
class LocateResult:
    """The full read-only Slice 2 output. `to_dict()` is the
    machine-readable form; every field is also directly attribute-
    accessible for a human-reviewing caller."""

    status: str  # "matched" | "unresolved"
    slide_index: Optional[int] = None
    shape_index: Optional[int] = None
    shape_id: Optional[int] = None
    matched_text: Optional[str] = None
    match_basis: Optional[str] = None  # "exact" | "whitespace_normalized" | "bounded_substring"
    unresolved_reason: Optional[str] = None  # "no_match" | "ambiguous_multiple_matches"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "slide_index": self.slide_index,
            "shape_index": self.shape_index,
            "shape_id": self.shape_id,
            "matched_text": self.matched_text,
            "match_basis": self.match_basis,
            "unresolved_reason": self.unresolved_reason,
        }


def _match_basis(documentation_text: str, normalized_target: str, shape_text: str) -> Optional[str]:
    if shape_text == documentation_text:
        return "exact"

    normalized_shape_text = _normalize_whitespace(shape_text)
    if normalized_shape_text == normalized_target:
        return "whitespace_normalized"

    if normalized_target and normalized_shape_text and (
        normalized_target in normalized_shape_text
        or normalized_shape_text in normalized_target
    ):
        return "bounded_substring"

    return None


def locate_documentation_text(deck_path: str, documentation_text: str) -> LocateResult:
    """Slice 2's one entry point. Read-only: calls only `inspect_deck()`
    on `deck_path` - never a Safe PPT Engine mutation primitive.

    Searches every shape's text (as `inspect_deck()` already reports it)
    for `documentation_text`, using exact / whitespace-normalized /
    bounded-substring matching only, in that priority order per shape.
    Returns `status="matched"` only when exactly one shape in the entire
    deck matches by any rule; otherwise returns an explicit
    `status="unresolved"` result with a reason. Never raises to signal
    "no match" or "ambiguous" - those are ordinary results, not errors.

    Propagates `inspect_deck()`'s own typed `SafeDeckError` subclasses
    (e.g. `DeckSourceError`) unmodified for a missing/invalid `.pptx` -
    that is a caller/reference error, not a locate result.

    A `documentation_text` that is empty or whitespace-only (Codex
    finding DI-S2-01) never produces a structural match, even against an
    equally blank shape: it is rejected as `unresolved`/`no_match` before
    any candidate matching happens, deterministically, every time. A bad
    `deck_path` is still surfaced as a typed error either way - the blank-
    query check does not shadow it.
    """
    structure = inspect_deck(deck_path)
    normalized_target = _normalize_whitespace(documentation_text)
    if not normalized_target:
        return LocateResult(status="unresolved", unresolved_reason="no_match")

    candidates = []
    for slide in structure["slides"]:
        for shape in slide["shapes"]:
            shape_text = shape.get("text")
            if shape_text is None:
                continue
            basis = _match_basis(documentation_text, normalized_target, shape_text)
            if basis is not None:
                candidates.append((slide["slide_index"], shape, basis))

    if not candidates:
        return LocateResult(status="unresolved", unresolved_reason="no_match")
    if len(candidates) > 1:
        return LocateResult(status="unresolved", unresolved_reason="ambiguous_multiple_matches")

    slide_index, shape, basis = candidates[0]
    return LocateResult(
        status="matched",
        slide_index=slide_index,
        shape_index=shape["shape_index"],
        shape_id=shape["shape_id"],
        matched_text=shape["text"],
        match_basis=basis,
    )
