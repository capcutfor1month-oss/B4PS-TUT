"""Browser Verification pilot - Engineering Slice 1.

The narrowest possible bridge from a bounded, structured browser
observation to Editorial Memory Evidence, per the approved pilot
adoption gate ([[Browser Verification Pilot Requirement]]).

Browser observation is Evidence, and only Evidence. This module never
creates, proposes, or approves a KnowledgeItem/KnowledgeState - it
composes a deterministic, round-trippable payload and hands off to
`EditorialMemory.record_evidence`/`models.Evidence` completely
unmodified. The existing maintainer review/lifecycle
(`propose_state`/`approve_state`) remains the only path from Evidence
to Knowledge; nothing here shortcuts, bypasses, or auto-promotes it.

The one thing a browser observation needs that `Evidence.notes` alone
doesn't structurally provide is the epistemic-safety separation the
pilot's AI-understanding tests (Tests 1-3) established as a hard
requirement: directly observed facts must never be silently blended
with inference or left uncertainty. `BrowserObservation` carries that
separation; its `to_notes`/`from_notes` pair is the deterministic,
lossless encoding stored in the existing `Evidence.notes` field - no
new entity, no schema change to `models.Evidence` itself.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Optional

from .errors import InvalidBrowserObservationError, MalformedBrowserObservationError
from .memory import EditorialMemory
from .models import Evidence, EvidenceQuality, EvidenceType

_NOTES_SCHEMA_VERSION = 1
_REQUIRED_NOTES_KEYS = frozenset({"schema", "workflow", "direct_observations", "inferences", "unknowns", "uncertainty"})

# Deterministic, explicit upper bound on a JSON integer literal's digit
# count, checked *before* Python ever converts the literal's text to an
# `int`. Not derived from `sys.int_info.default_max_str_digits` -
# deliberately: that guard's default value has changed across Python
# versions and is process-configurable (including disable-able via
# `sys.set_int_max_str_digits(0)`), so relying on it would make
# "an oversized integer literal is rejected" a property of the
# interpreter running this code rather than of the data itself. 18
# digits comfortably exceeds any value this schema ever legitimately
# contains (`schema` is always exactly `1`) while staying far below
# every Python version's own int-conversion limit on every supported
# version.
_MAX_JSON_INT_DIGITS = 18


def _strict_parse_int(text: str) -> int:
    """`json.loads(..., parse_int=...)` hook: rejects an oversized
    integer literal - anywhere in the document, not only `schema` -
    before ever calling `int()` on it, so Python's own int-string
    conversion guard (version-varying, process-configurable, and not
    guaranteed to even be enabled) never gets the chance to raise a raw
    `ValueError` first. Raises typed `MalformedBrowserObservationError`
    directly; `json.loads` propagates a hook's exception unwrapped."""
    digits = text[1:] if text.startswith("-") else text
    if len(digits) > _MAX_JSON_INT_DIGITS:
        raise MalformedBrowserObservationError(
            f"Evidence.notes contains a JSON integer literal longer than "
            f"{_MAX_JSON_INT_DIGITS} digits: {text!r}"
        )
    return int(text)


def _strict_object_pairs_hook(pairs: list) -> dict:
    """`json.loads(..., object_pairs_hook=...)` hook: rejects a JSON
    object containing a duplicate member name, at any nesting level,
    instead of Python's default behavior of silently keeping only the
    last value for that key. Raises typed
    `MalformedBrowserObservationError` directly."""
    seen = set()
    result = {}
    for key, value in pairs:
        if key in seen:
            raise MalformedBrowserObservationError(
                f"Evidence.notes contains a duplicate JSON object key: {key!r}"
            )
        seen.add(key)
        result[key] = value
    return result


def _require_json_str_list(value, field_name: str, *, allow_empty: bool) -> tuple:
    """Strict read-side validator for a JSON-decoded list field. Only a
    genuine `list` is accepted - a JSON string is never silently
    exploded into one entry per character, and a JSON object/number is
    never silently coerced. Every entry must be a non-blank string.
    Raises typed `MalformedBrowserObservationError`, never a raw
    `TypeError`."""
    if not isinstance(value, list):
        raise MalformedBrowserObservationError(
            f"Evidence.notes {field_name} must be a JSON array of strings, got {type(value).__name__}"
        )
    if not allow_empty and not value:
        raise MalformedBrowserObservationError(f"Evidence.notes {field_name} must be non-empty")
    for entry in value:
        if not isinstance(entry, str) or not entry.strip():
            raise MalformedBrowserObservationError(
                f"Evidence.notes {field_name} entries must all be non-blank strings, got {entry!r}"
            )
    return tuple(value)


@dataclasses.dataclass(frozen=True)
class BrowserObservation:
    """The structured payload one bounded browser-observation pilot run
    produces. A transport/encoding shape carried inside
    `Evidence.notes` - not a fourth Editorial Memory entity, not
    persisted anywhere of its own.

    `direct_observations` is the only required, non-empty part: per
    the pilot's core observation rule, an observation asserting
    nothing was actually seen is not evidence of anything.
    `inferences`/`unknowns`/`uncertainty` are kept separate so a reader
    (human or future automated review) can never mistake interpretation
    for something directly witnessed."""

    workflow: str
    direct_observations: tuple
    inferences: tuple = ()
    unknowns: tuple = ()
    uncertainty: Optional[str] = None

    def to_notes(self) -> str:
        """Deterministic (sorted-key JSON) encoding for `Evidence.notes`.
        Same `BrowserObservation` content always yields the same
        string, so persistence/reload is byte-for-byte reproducible."""
        payload = {
            "schema": _NOTES_SCHEMA_VERSION,
            "workflow": self.workflow,
            "direct_observations": list(self.direct_observations),
            "inferences": list(self.inferences),
            "unknowns": list(self.unknowns),
            "uncertainty": self.uncertainty,
        }
        return json.dumps(payload, sort_keys=True)

    @classmethod
    def from_notes(cls, notes: str) -> "BrowserObservation":
        """Inverse of `to_notes`. Strict by construction - every check
        below raises typed `MalformedBrowserObservationError` and
        nothing is silently coerced, truncated, character-split, or
        dropped:

        - malformed JSON, or JSON that doesn't decode to an object
        - a duplicate JSON object key at any nesting level (rejected
          outright - never silently resolved to the last-seen value)
        - a JSON integer literal (anywhere in the document) longer than
          `_MAX_JSON_INT_DIGITS` digits - rejected deterministically,
          before Python's own version-varying int-string-conversion
          guard ever gets a chance to raise a raw `ValueError` first
        - any extra or missing key (exact key-set match required)
        - `schema` not exactly the integer `1` (`true` is rejected -
          `bool` is a `int` subclass in Python, so this checks `type(...)
          is int`, not `isinstance(..., int)`, specifically to catch it)
        - `workflow`/`uncertainty` not a string (`uncertainty` may be
          `None`)
        - `direct_observations`/`inferences`/`unknowns` not a JSON
          array (a bare string is rejected outright - never silently
          exploded into one entry per character), or containing any
          non-string/blank entry
        - `direct_observations` present but empty"""
        try:
            payload = json.loads(
                notes,
                object_pairs_hook=_strict_object_pairs_hook,
                parse_int=_strict_parse_int,
            )
        except (TypeError, ValueError) as exc:
            # `_strict_object_pairs_hook`/`_strict_parse_int` raise
            # `MalformedBrowserObservationError` directly and
            # `json.loads` propagates a hook's exception unwrapped, so
            # it never reaches this clause - only genuine JSON-decode
            # failures (a `ValueError` subclass) and Python's own
            # int-conversion `ValueError`, on the rare input that
            # somehow reaches it before `_strict_parse_int` does, land
            # here.
            raise MalformedBrowserObservationError(
                f"Evidence.notes is not valid browser-observation JSON: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise MalformedBrowserObservationError(
                f"Evidence.notes must decode to a JSON object, got {type(payload).__name__}"
            )
        if set(payload.keys()) != _REQUIRED_NOTES_KEYS:
            raise MalformedBrowserObservationError(
                f"Evidence.notes keys {sorted(payload.keys())} do not exactly match the "
                f"required browser-observation keys {sorted(_REQUIRED_NOTES_KEYS)} - "
                "no extra or missing keys allowed"
            )

        schema = payload["schema"]
        if type(schema) is not int or schema != _NOTES_SCHEMA_VERSION:
            raise MalformedBrowserObservationError(
                f"Evidence.notes browser-observation schema {schema!r} is not exactly "
                f"the supported schema {_NOTES_SCHEMA_VERSION!r}"
            )

        workflow = payload["workflow"]
        if not isinstance(workflow, str) or not workflow.strip():
            raise MalformedBrowserObservationError(
                f"Evidence.notes workflow must be a non-blank string, got {workflow!r}"
            )

        direct_observations = _require_json_str_list(
            payload["direct_observations"], "direct_observations", allow_empty=False
        )
        inferences = _require_json_str_list(payload["inferences"], "inferences", allow_empty=True)
        unknowns = _require_json_str_list(payload["unknowns"], "unknowns", allow_empty=True)

        uncertainty = payload["uncertainty"]
        if uncertainty is not None and (not isinstance(uncertainty, str) or not uncertainty.strip()):
            raise MalformedBrowserObservationError(
                f"Evidence.notes uncertainty must be null or a non-blank string, got {uncertainty!r}"
            )

        return cls(
            workflow=workflow,
            direct_observations=direct_observations,
            inferences=inferences,
            unknowns=unknowns,
            uncertainty=uncertainty,
        )


def _non_blank_str(value, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidBrowserObservationError(f"{field_name} must be a non-blank string")
    return value


def _require_ordered_str_sequence(value, field_name: str, *, allow_empty: bool) -> tuple:
    """Strict write-side validator for an observation/inference/unknown
    collection argument. Only `list`/`tuple` is accepted - never a bare
    `str` (which is itself iterable and would otherwise be silently
    exploded into one entry per character), never a `set`/`frozenset`
    (unordered - would break deterministic serialization), and never
    any other non-iterable value passed straight to `tuple()` (which
    would raise a raw `TypeError`). Every entry must be a non-blank
    string. Raises typed `InvalidBrowserObservationError` in every
    rejection case - no raw `TypeError`/`AttributeError` ever reaches
    the caller."""
    if isinstance(value, (str, bytes)):
        raise InvalidBrowserObservationError(
            f"{field_name} must be a list/tuple of strings, not a single string"
        )
    if isinstance(value, (set, frozenset)):
        raise InvalidBrowserObservationError(
            f"{field_name} must be an ordered sequence (list/tuple), not a set - "
            "serialization order must be deterministic"
        )
    if not isinstance(value, (list, tuple)):
        raise InvalidBrowserObservationError(
            f"{field_name} must be a list or tuple, got {type(value).__name__}"
        )
    if not allow_empty and not value:
        raise InvalidBrowserObservationError(f"{field_name} must be non-empty")
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise InvalidBrowserObservationError(f"every entry in {field_name} must be a non-blank string")
    return tuple(value)


def record_browser_observation(
    memory: EditorialMemory,
    *,
    workflow: str,
    source_ref: str,
    captured_by: str,
    direct_observations,
    inferences=(),
    unknowns=(),
    uncertainty: Optional[str] = None,
    verification_scope: Optional[list] = None,
    captured_at: Optional[str] = None,
    evidence_quality: Optional[EvidenceQuality] = None,
) -> Evidence:
    """Record one bounded Browser Verification pilot observation as
    Editorial Memory Evidence - Evidence only.

    Never creates, proposes, or approves a KnowledgeItem/KnowledgeState.
    `evidence_type` is always `BROWSER_OBSERVATION` - not caller-
    supplied - since that is definitionally what this function records.
    Delegates the actual write to the existing, unmodified
    `EditorialMemory.record_evidence`; this function's only job is
    validating and deterministically encoding the structured payload
    that `record_evidence`'s plain `notes: Optional[str]` parameter
    doesn't itself understand.

    Raises typed `InvalidBrowserObservationError` - never a raw
    `TypeError`/`AttributeError`/`ValueError` - for any of: a blank/
    wrong-typed text field; `direct_observations`/`inferences`/
    `unknowns` given as a bare string (would silently explode into one
    entry per character), a set/frozenset (unordered - would break
    deterministic serialization), any other non-list/tuple, or
    containing a non-string/blank entry; an empty `direct_observations`;
    an invalid `verification_scope` shape; or an `evidence_quality` that
    isn't an `EvidenceQuality` member or `None`."""
    workflow = _non_blank_str(workflow, "workflow")
    source_ref = _non_blank_str(source_ref, "source_ref")
    captured_by = _non_blank_str(captured_by, "captured_by")

    direct_observations = _require_ordered_str_sequence(
        direct_observations, "direct_observations", allow_empty=False
    )
    inferences = _require_ordered_str_sequence(inferences, "inferences", allow_empty=True)
    unknowns = _require_ordered_str_sequence(unknowns, "unknowns", allow_empty=True)
    if uncertainty is not None:
        uncertainty = _non_blank_str(uncertainty, "uncertainty")

    if verification_scope is not None:
        verification_scope = list(
            _require_ordered_str_sequence(verification_scope, "verification_scope", allow_empty=True)
        )
    if evidence_quality is not None and not isinstance(evidence_quality, EvidenceQuality):
        raise InvalidBrowserObservationError(
            f"evidence_quality must be an EvidenceQuality member or None, got {evidence_quality!r}"
        )

    observation = BrowserObservation(
        workflow=workflow,
        direct_observations=direct_observations,
        inferences=inferences,
        unknowns=unknowns,
        uncertainty=uncertainty,
    )
    return memory.record_evidence(
        evidence_type=EvidenceType.BROWSER_OBSERVATION,
        source_ref=source_ref,
        captured_by=captured_by,
        captured_at=captured_at,
        notes=observation.to_notes(),
        verification_scope=verification_scope,
        evidence_quality=evidence_quality,
    )


def get_browser_observation(evidence: Evidence) -> BrowserObservation:
    """Recover the structured `BrowserObservation` payload from an
    Evidence record produced by `record_browser_observation`.

    Raises typed `MalformedBrowserObservationError` - never a raw
    `json.JSONDecodeError`/`KeyError` - if `evidence` is not tagged
    `evidence_type=browser_observation`, has no `notes`, or its `notes`
    does not parse as the expected structured shape (e.g. hand-edited
    or corrupted storage)."""
    if evidence.evidence_type != EvidenceType.BROWSER_OBSERVATION:
        raise MalformedBrowserObservationError(
            f"Evidence {evidence.id!r} has evidence_type {evidence.evidence_type!r}, "
            "not browser_observation"
        )
    if not evidence.notes:
        raise MalformedBrowserObservationError(
            f"Evidence {evidence.id!r} has no notes payload to parse as a browser observation"
        )
    return BrowserObservation.from_notes(evidence.notes)
