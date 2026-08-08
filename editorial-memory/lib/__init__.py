"""Editorial Memory - Slice 1.

Editorial Memory is a knowledge system, not a truth system. It stores
claims, evidence, provenance, approvals, lifecycle state, and history.
Current truth is determined by approval and lifecycle rules, not by the
mere existence of an evidence artifact.

Public API: see `memory.EditorialMemory`.
"""

from .memory import EditorialMemory
from .models import (
    Evidence,
    EvidenceQuality,
    EvidenceType,
    KnowledgeItem,
    KnowledgeState,
    KnowledgeType,
    Relation,
    StateStatus,
)
from .errors import (
    CorruptProvenanceError,
    EditorialMemoryError,
    InvalidEvidenceIdError,
    InvalidFeatureAreaError,
    InvalidLifecycleTransitionError,
    KeyCollisionError,
    MissingProvenanceError,
    StorageCorruptionError,
    UnknownEvidenceError,
    UnknownKnowledgeItemError,
    UnknownStateVersionError,
)

__all__ = [
    "EditorialMemory",
    "Evidence",
    "EvidenceQuality",
    "EvidenceType",
    "KnowledgeItem",
    "KnowledgeState",
    "KnowledgeType",
    "Relation",
    "StateStatus",
    "CorruptProvenanceError",
    "EditorialMemoryError",
    "InvalidEvidenceIdError",
    "InvalidFeatureAreaError",
    "InvalidLifecycleTransitionError",
    "KeyCollisionError",
    "MissingProvenanceError",
    "StorageCorruptionError",
    "UnknownEvidenceError",
    "UnknownKnowledgeItemError",
    "UnknownStateVersionError",
]
