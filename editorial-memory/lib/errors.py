"""Typed errors for Editorial Memory.

Every failure mode raises a specific, typed exception rather than a bare
ValueError/KeyError - callers can distinguish "the reference you gave
doesn't exist" from "the transition you asked for isn't allowed" from
"you didn't provide required provenance," matching the typed-error
convention already used by the Safe PPT Engine (`lib/ppt_engine.py`).
"""


class EditorialMemoryError(Exception):
    """Base class for every typed Editorial Memory failure."""


class UnknownKnowledgeItemError(EditorialMemoryError):
    """Raised when a KnowledgeItem id/key does not exist."""


class UnknownEvidenceError(EditorialMemoryError):
    """Raised when an Evidence id does not exist."""


class UnknownStateVersionError(EditorialMemoryError):
    """Raised when a KnowledgeItem has no state with the given version."""


class MissingProvenanceError(EditorialMemoryError):
    """Raised when a KnowledgeState is proposed without any evidence_refs.

    This is the code-level enforcement of the core invariant: every
    KnowledgeState must reference Evidence. No evidence record may
    automatically create approved/current knowledge, and no
    KnowledgeState may exist without provenance to check.
    """


class InvalidLifecycleTransitionError(EditorialMemoryError):
    """Raised when a requested lifecycle transition is not allowed.

    Examples: approving a state that is already current/superseded/
    invalidated; invalidating a state that is already invalidated.
    """


class CorruptProvenanceError(EditorialMemoryError):
    """Raised by `get_current` when the state it would otherwise return
    cites Evidence that is missing or corrupt (EM-01).

    `get_current` never silently returns a state whose provenance can't
    actually be checked - returning it as if it were trustworthy would
    be exactly the "evidence-less current knowledge" failure mode this
    module exists to prevent, just arrived at by storage decay instead
    of a missing propose_state() argument. The underlying
    `UnknownEvidenceError`/`StorageCorruptionError` is chained via
    `__cause__` so the specific evidence problem is still visible.
    """


class CorruptEvidenceRecordError(EditorialMemoryError):
    """Raised by `get_evidence` (EM47-05) when a stored Evidence record is
    valid JSON but structurally incomplete/malformed - missing or
    invalid required fields - most commonly a Slice 7 purge tombstone
    stub (`{id, purged_at, purged_by, reason}`) being loaded as if it
    were still a real Evidence record. Distinct from
    `StorageCorruptionError` (the file isn't even valid JSON) and
    `UnknownEvidenceError` (no record exists at all). Ensures a
    malformed/tombstoned record always surfaces as a typed Editorial
    Memory error - including through `get_current`'s existing
    `CorruptProvenanceError` wrapping (EM-01), unchanged - rather than a
    raw `KeyError`/`TypeError` escaping from `Evidence.from_dict`.
    """


class InvalidBrowserObservationError(EditorialMemoryError):
    """Raised by `browser_evidence.record_browser_observation` when the
    structured payload for a bounded Browser Verification pilot
    observation is missing or malformed - most importantly, no
    `direct_observations` at all. A browser observation asserting
    nothing was actually, directly seen is not evidence of anything;
    this is rejected before any Evidence record is ever written, the
    same "reject at the boundary, never write something ambiguous"
    posture `MissingProvenanceError` and `MissingPurgeAuthorizationError`
    already use elsewhere in this module.
    """


class MalformedBrowserObservationError(EditorialMemoryError):
    """Raised by `browser_evidence.get_browser_observation` when an
    Evidence record's `notes` field cannot be parsed back into the
    structured browser-observation shape `record_browser_observation`
    writes - not valid JSON, missing a required key, or not tagged
    `evidence_type=browser_observation` at all. Distinct from
    `CorruptEvidenceRecordError` (which covers the outer Evidence
    record itself being structurally incomplete): this covers only the
    inner, browser-observation-specific payload inside an otherwise
    valid Evidence record's `notes` string. Never a raw
    `json.JSONDecodeError`/`KeyError` reaches the caller.
    """


class KeyCollisionError(EditorialMemoryError):
    """Raised by `get_or_create_knowledge_item` when a new natural key
    slugifies to the same durable id as an existing, different key
    (EM-02) - e.g. "a.b" and "a-b" both slugify to "a-b". Silently
    treating them as the same KnowledgeItem would merge two distinct
    subjects' identity and history; this is refused instead, keeping
    identity for any single key deterministic and stable without
    pretending two different keys are interchangeable.
    """


class InvalidFeatureAreaError(EditorialMemoryError):
    """Raised when a `feature_area` value cannot be used as a safe path
    segment (EM-03) - e.g. it contains `/`, `\\`, `..`, or is otherwise
    not a plain `<platform>.<feature>`-style token. Prevents a
    caller-supplied feature_area from writing or reading outside the
    configured memory root.
    """


class InvalidEvidenceIdError(EditorialMemoryError):
    """Raised when an `evidence_id` value cannot be used as a safe path
    segment (EM-04) - e.g. it contains `/`, `\\`, `..`, is an absolute
    path, or is otherwise not a plain generated-id token. Prevents a
    caller-supplied or persisted-but-tampered evidence_id (including one
    reached indirectly via a KnowledgeState's evidence_refs) from reading
    or writing outside the configured memory root.
    """


class InvalidKnowledgeItemIdError(EditorialMemoryError):
    """Raised by the Slice 7 purge path (EM47-02) when an `item_id` value
    cannot be used as a safe generated-id token - e.g. it contains `/`,
    `\\`, `..`, glob/wildcard metacharacters (`*`, `?`, `[...]`), or is
    otherwise not a plain `slugify()`-shaped id. Prevents a caller-
    supplied `item_id` from being interpreted as a glob pattern by
    `_knowledge_path`'s id-only lookup branch, or from reading/writing
    outside the configured memory root.
    """


class MissingPurgeAuthorizationError(EditorialMemoryError):
    """Raised by `purge_evidence`/`purge_knowledge_state` (EM47-04) when
    `purged_by` is missing, `None`, or blank/whitespace-only. Purge is a
    bounded, human-authorized exception to "nothing is ever deleted"
    (design §15.3) - it must always be an explicit, attributed human
    action, never callable anonymously.
    """


class FeatureAreaMismatchError(EditorialMemoryError):
    """Raised by `record_maintainer_decision` (Slice 2, S2-01) when the
    requested `feature_area` differs from the `feature_area` already
    stored on the existing `KnowledgeItem` for the same natural key.
    Refuses to reuse an existing item under a different feature_area,
    silently move it, or treat a mismatched request as an idempotent
    repeat - no Evidence or KnowledgeState is created when this is
    raised.
    """


class KnowledgeTypeMismatchError(EditorialMemoryError):
    """Raised by `record_maintainer_decision`/`ingest_existing_documentation`
    (finding 4) when the requested `knowledge_type` (`editorial`/
    `documentation` respectively - each bootstrap path always uses one
    fixed type, never caller-supplied) differs from the `knowledge_type`
    already stored on the existing `KnowledgeItem` for the same natural
    key. `feature_area`-mismatch (`FeatureAreaMismatchError`) already
    refuses to silently reuse an item under a different feature_area;
    this is the same protection for `knowledge_type` - product,
    documentation, and editorial knowledge must never blend under one
    `KnowledgeItem`, so a mismatch is rejected outright, before any
    dedup check or mutation, rather than silently appending a
    documentation-ingestion state onto (for example) a product-typed
    item just because the natural key happened to collide.
    """


class StorageCorruptionError(EditorialMemoryError):
    """Raised when a persisted record file exists but cannot be parsed
    as the JSON this module wrote - a corrupted, truncated, or
    hand-edited-into-invalidity file, distinct from the record simply
    not existing (`Unknown*Error`) or referencing something that
    doesn't exist (`UnknownEvidenceError`/`UnknownKnowledgeItemError`).
    """
