"""Editorial Memory - Slice 1.

Editorial Memory is a knowledge system, not a truth system. It stores
claims, evidence, provenance, approvals, lifecycle state, and history.
Current truth is determined by approval and lifecycle rules, not by the
mere existence of an evidence artifact.

Public API: see `memory.EditorialMemory`.
"""

from .memory import EditorialMemory
from .browser_evidence import (
    BrowserObservation,
    get_browser_observation,
    record_browser_observation,
)
from .retrieval import (
    CurrentKnowledge,
    get_current_by_key,
    get_history_by_key,
    list_current_by_feature_area,
    list_current_by_knowledge_type,
)
from .review import (
    PendingReview,
    list_conflicts,
    list_pending_review,
)
from .purge import (
    InvalidatedKnowledge,
    Tombstone,
    get_invalidated_by_key,
    list_invalidated_by_feature_area,
    list_invalidated_by_knowledge_type,
    purge_evidence,
    purge_knowledge_state,
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
    CorruptEvidenceRecordError,
    CorruptProvenanceError,
    EditorialMemoryError,
    FeatureAreaMismatchError,
    InvalidBrowserObservationError,
    InvalidEvidenceIdError,
    InvalidFeatureAreaError,
    InvalidKnowledgeItemIdError,
    InvalidLifecycleTransitionError,
    KeyCollisionError,
    KnowledgeTypeMismatchError,
    MalformedBrowserObservationError,
    MissingProvenanceError,
    MissingPurgeAuthorizationError,
    StorageCorruptionError,
    UnknownEvidenceError,
    UnknownKnowledgeItemError,
    UnknownStateVersionError,
)

__all__ = [
    "EditorialMemory",
    "BrowserObservation",
    "get_browser_observation",
    "record_browser_observation",
    "CurrentKnowledge",
    "get_current_by_key",
    "get_history_by_key",
    "list_current_by_feature_area",
    "list_current_by_knowledge_type",
    "PendingReview",
    "list_conflicts",
    "list_pending_review",
    "InvalidatedKnowledge",
    "Tombstone",
    "get_invalidated_by_key",
    "list_invalidated_by_feature_area",
    "list_invalidated_by_knowledge_type",
    "purge_evidence",
    "purge_knowledge_state",
    "Evidence",
    "EvidenceQuality",
    "EvidenceType",
    "KnowledgeItem",
    "KnowledgeState",
    "KnowledgeType",
    "Relation",
    "StateStatus",
    "CorruptEvidenceRecordError",
    "CorruptProvenanceError",
    "EditorialMemoryError",
    "FeatureAreaMismatchError",
    "InvalidBrowserObservationError",
    "InvalidEvidenceIdError",
    "InvalidFeatureAreaError",
    "InvalidKnowledgeItemIdError",
    "InvalidLifecycleTransitionError",
    "KeyCollisionError",
    "KnowledgeTypeMismatchError",
    "MalformedBrowserObservationError",
    "MissingProvenanceError",
    "MissingPurgeAuthorizationError",
    "StorageCorruptionError",
    "UnknownEvidenceError",
    "UnknownKnowledgeItemError",
    "UnknownStateVersionError",
]
