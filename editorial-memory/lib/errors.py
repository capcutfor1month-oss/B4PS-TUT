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
