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


class StorageCorruptionError(EditorialMemoryError):
    """Raised when a persisted record file exists but cannot be parsed
    as the JSON this module wrote - a corrupted, truncated, or
    hand-edited-into-invalidity file, distinct from the record simply
    not existing (`Unknown*Error`) or referencing something that
    doesn't exist (`UnknownEvidenceError`/`UnknownKnowledgeItemError`).
    """
