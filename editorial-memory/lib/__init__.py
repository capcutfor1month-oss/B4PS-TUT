"""Editorial Memory - Slice 1.

Editorial Memory is a knowledge system, not a truth system. It stores
claims, evidence, provenance, approvals, lifecycle state, and history.
Current truth is determined by approval and lifecycle rules, not by the
mere existence of an evidence artifact.

Public API: see `memory.EditorialMemory`.
"""

from .memory import EditorialMemory
from .retrieval import (
    CurrentKnowledge,
    get_current_by_key,
    get_history_by_key,
    list_current_by_feature_area,
    list_current_by_knowledge_type,
)
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
    FeatureAreaMismatchError,
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
    "CurrentKnowledge",
    "get_current_by_key",
    "get_history_by_key",
    "list_current_by_feature_area",
    "list_current_by_knowledge_type",
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
    "FeatureAreaMismatchError",
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
