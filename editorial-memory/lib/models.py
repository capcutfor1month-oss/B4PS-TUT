"""Core record types for Editorial Memory Slice 1.

Exactly three entities, per the already-approved minimal design (no
ontology, no graph semantics, no universal semantic IDs beyond ordinary
persistence identity):

- `Evidence`   - an artifact/observation/source. Never itself knowledge.
- `KnowledgeItem` - the durable subject/concept being remembered.
- `KnowledgeState` - one versioned claim about a KnowledgeItem, always
  grounded in one or more Evidence records.

`review_required` on `KnowledgeState` is a *computed* property, not a
stored field: it is true exactly when a proposed state's declared
relation to the previous state is `contradicts` and it has not yet been
resolved by approval. Keeping it computed means there is exactly one
place (the stored `status`/`relation_to_previous` pair) that can ever be
out of sync - it cannot itself drift from the data it summarizes.
"""

from __future__ import annotations

import dataclasses
import enum
from typing import Optional


class EvidenceType(str, enum.Enum):
    MAINTAINER_DECISION = "maintainer_decision"
    BROWSER_OBSERVATION = "browser_observation"
    EXISTING_DOCUMENTATION = "existing_documentation"
    SCREENSHOT = "screenshot"
    RECORDING = "recording"


class EvidenceQuality(str, enum.Enum):
    """Quality/reliability of the artifact itself - not confidence that
    any claim built from it is true. Deliberately three fixed values,
    not a numeric score."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class KnowledgeType(str, enum.Enum):
    PRODUCT = "product"
    DOCUMENTATION = "documentation"
    EDITORIAL = "editorial"


class StateStatus(str, enum.Enum):
    PROPOSED = "proposed"
    CURRENT = "current"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"


class Relation(str, enum.Enum):
    NEW = "new"
    CONFIRMS = "confirms"
    REFINES = "refines"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"


@dataclasses.dataclass
class Evidence:
    id: str
    evidence_type: EvidenceType
    source_ref: str
    captured_by: str
    captured_at: Optional[str] = None  # ISO 8601; when the underlying observation happened
    recorded_at: str = ""              # ISO 8601; when this Evidence record was created here
    notes: Optional[str] = None
    verification_scope: Optional[list] = None  # list[str] - informational only, see docs
    evidence_quality: Optional[EvidenceQuality] = None

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["evidence_type"] = self.evidence_type.value
        if self.evidence_quality is not None:
            d["evidence_quality"] = self.evidence_quality.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Evidence":
        data = dict(data)
        data["evidence_type"] = EvidenceType(data["evidence_type"])
        if data.get("evidence_quality") is not None:
            data["evidence_quality"] = EvidenceQuality(data["evidence_quality"])
        return cls(**data)


@dataclasses.dataclass
class KnowledgeState:
    version: int
    content: str
    status: StateStatus
    relation_to_previous: Optional[Relation]
    evidence_refs: list
    created_at: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    superseded_by: Optional[int] = None
    rationale: Optional[str] = None
    invalidated_by: Optional[str] = None
    invalidated_at: Optional[str] = None
    invalidation_reason: Optional[str] = None

    @property
    def review_required(self) -> bool:
        """True exactly when this is a proposed state whose declared
        relation to the previous state is `contradicts` - i.e. a
        conflict has been recorded and not yet resolved by approval.
        Once approved (or superseded some other way) this is false."""
        return self.status == StateStatus.PROPOSED and self.relation_to_previous == Relation.CONTRADICTS

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["status"] = self.status.value
        d["relation_to_previous"] = self.relation_to_previous.value if self.relation_to_previous else None
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeState":
        data = dict(data)
        data.pop("review_required", None)  # computed, never persisted
        data["status"] = StateStatus(data["status"])
        if data.get("relation_to_previous") is not None:
            data["relation_to_previous"] = Relation(data["relation_to_previous"])
        return cls(**data)


@dataclasses.dataclass
class KnowledgeItem:
    id: str                 # deterministic slug of `key` - the durable subject identity
    key: str                # human-supplied natural identity, e.g. "desktop.filters.button-label"
    knowledge_type: KnowledgeType
    feature_area: str       # "<platform>.<feature>" convention, organizational metadata only
    states: list            # list[KnowledgeState], append-only, ordered oldest -> newest

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "knowledge_type": self.knowledge_type.value,
            "feature_area": self.feature_area,
            "states": [s.to_dict() for s in self.states],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeItem":
        return cls(
            id=data["id"],
            key=data["key"],
            knowledge_type=KnowledgeType(data["knowledge_type"]),
            feature_area=data["feature_area"],
            states=[KnowledgeState.from_dict(s) for s in data["states"]],
        )
