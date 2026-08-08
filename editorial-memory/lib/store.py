"""Deterministic local JSON-file persistence for Editorial Memory.

Plain files, one per record, no new dependency, git-diffable - the
smallest mechanism sufficient to prove durable storage and reload for
Slice 1. No graph database, vector database, embeddings, or hosted
service; nothing here requires infrastructure beyond the filesystem.

Layout, matching the already-approved repository-structure design:

    <root>/
      evidence/
        <evidence-id>.json
      knowledge/
        <feature-area>/
          <item-id>.json      # embeds the full states[] list, append-only

`JSONStore` is stateless between calls - every read goes to disk. For
Slice 1's scale this is simple and correct by construction: there is no
in-memory cache that can drift from what is actually persisted, so
"reload from storage gives identical results" holds trivially rather
than needing to be separately guaranteed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from .errors import InvalidEvidenceIdError, InvalidFeatureAreaError, StorageCorruptionError

# `<platform>.<feature>`-style convention (see docs/EDITORIAL_MEMORY_IMPLEMENTATION_AUDIT.md
# Amendment 4): one or more dot-separated segments, each lowercase
# alphanumerics/hyphens only. No `/`, `\`, `..`, leading/trailing dots,
# or empty segments - which also makes it structurally impossible for a
# validated feature_area to escape the knowledge/ directory it's joined
# onto as a path component.
_FEATURE_AREA_SEGMENT = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_FEATURE_AREA_RE = re.compile(rf"^{_FEATURE_AREA_SEGMENT}(?:\.{_FEATURE_AREA_SEGMENT})*$")

# Same safe-token shape as a slugify() output / a `record_evidence()`-
# generated id ("ev-" + hex) - lowercase alphanumerics/hyphens only, no
# `/`, `\`, `..`, or leading/trailing separators (EM-04).
_EVIDENCE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slugify(key: str) -> str:
    """Deterministic id derivation from a KnowledgeItem's natural key.
    Same input always yields the same id - this is what makes
    `get_or_create_knowledge_item` idempotent without a separate index.

    This mapping is lossy by construction (e.g. "a.b" and "a-b" both
    normalize to "a-b") - callers that create/find a KnowledgeItem are
    responsible for detecting when two distinct natural keys collide
    into the same slug and refusing to silently merge them (EM-02; see
    `EditorialMemory.get_or_create_knowledge_item`, which compares the
    stored key against the requested one and raises `KeyCollisionError`
    rather than trusting the slug alone)."""
    slug = re.sub(r"[^a-z0-9]+", "-", key.strip().lower()).strip("-")
    if not slug:
        raise ValueError("key must contain at least one alphanumeric character")
    return slug


def validate_feature_area(feature_area: str) -> str:
    """Reject any `feature_area` that isn't a safe `<platform>.<feature>`
    path segment (EM-03) - in particular anything containing `/`, `\\`,
    `..`, or other characters that could let a caller-supplied value
    write or read outside the configured memory root."""
    if not isinstance(feature_area, str) or not _FEATURE_AREA_RE.match(feature_area):
        raise InvalidFeatureAreaError(
            f"feature_area {feature_area!r} is not a safe '<platform>.<feature>' "
            "path segment (lowercase alphanumerics/hyphens, dot-separated only)"
        )
    return feature_area


def validate_evidence_id(evidence_id: str) -> str:
    """Reject any `evidence_id` that isn't a safe generated-id token
    (EM-04) - in particular anything containing `/`, `\\`, `..`, or an
    absolute path, whether it arrived as a direct caller argument or was
    read back out of a persisted KnowledgeState's evidence_refs."""
    if not isinstance(evidence_id, str) or not _EVIDENCE_ID_RE.match(evidence_id):
        raise InvalidEvidenceIdError(
            f"evidence_id {evidence_id!r} is not a safe generated-id token "
            "(lowercase alphanumerics/hyphens only)"
        )
    return evidence_id


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise StorageCorruptionError(
            f"stored record at {path} is not valid JSON: {exc}"
        ) from exc


class JSONStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.evidence_dir = self.root / "evidence"
        self.knowledge_dir = self.root / "knowledge"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

    # --- Evidence -----------------------------------------------------

    def _evidence_path(self, evidence_id: str) -> Path:
        validate_evidence_id(evidence_id)
        path = self.evidence_dir / f"{evidence_id}.json"

        # Defense in depth, mirroring `_knowledge_path`: confirm the
        # resolved path still lands inside evidence_dir even though the
        # regex above should already make that structurally impossible.
        resolved_root = self.evidence_dir.resolve()
        resolved_path = path.resolve()
        try:
            resolved_path.relative_to(resolved_root)
        except ValueError:
            raise InvalidEvidenceIdError(
                f"resolved evidence path {resolved_path} escapes the configured memory root {resolved_root}"
            )
        return path

    def save_evidence(self, data: dict) -> None:
        path = self._evidence_path(data["id"])
        _atomic_write_json(path, data)

    def load_evidence(self, evidence_id: str) -> Optional[dict]:
        path = self._evidence_path(evidence_id)
        if not path.exists():
            return None
        return _load_json(path)

    def list_evidence_ids(self) -> list:
        return sorted(p.stem for p in self.evidence_dir.glob("*.json"))

    # --- KnowledgeItem (embeds its states) -----------------------------

    def _knowledge_path(self, item_id: str, feature_area: Optional[str] = None) -> Path:
        if feature_area is not None:
            validate_feature_area(feature_area)
            path = self.knowledge_dir / feature_area / f"{item_id}.json"
        else:
            # feature_area unknown (lookup-by-id path) - search for it.
            # `item_id` itself is always a `slugify()` output (safe
            # alnum/hyphen only), so the glob pattern cannot itself
            # traverse outside knowledge_dir.
            matches = list(self.knowledge_dir.glob(f"*/{item_id}.json"))
            path = matches[0] if matches else self.knowledge_dir / f"{item_id}.json"

        # Defense in depth: even a validated feature_area must resolve
        # to a real path inside knowledge_dir before we touch disk -
        # catches the case where a symlink somewhere under knowledge_dir
        # would otherwise let a lexically-safe path resolve outside it.
        # `resolve(strict=False)` works for not-yet-existing paths too.
        resolved_root = self.knowledge_dir.resolve()
        resolved_path = path.resolve()
        try:
            resolved_path.relative_to(resolved_root)
        except ValueError:
            raise InvalidFeatureAreaError(
                f"resolved knowledge path {resolved_path} escapes the configured memory root {resolved_root}"
            )
        return path

    def save_knowledge_item(self, data: dict) -> None:
        path = self._knowledge_path(data["id"], data["feature_area"])
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(path, data)

    def load_knowledge_item(self, item_id: str) -> Optional[dict]:
        path = self._knowledge_path(item_id)
        if not path.exists():
            return None
        return _load_json(path)

    def list_knowledge_item_ids(self) -> list:
        return sorted(p.stem for p in self.knowledge_dir.glob("*/*.json"))


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write a complete temp file then rename - a reader never observes
    a partially-written record, matching the atomic-publish discipline
    already established for this repository's other persistence code."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)
