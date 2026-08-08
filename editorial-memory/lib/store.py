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


def slugify(key: str) -> str:
    """Deterministic id derivation from a KnowledgeItem's natural key.
    Same input always yields the same id - this is what makes
    `get_or_create_knowledge_item` idempotent without a separate index."""
    slug = re.sub(r"[^a-z0-9]+", "-", key.strip().lower()).strip("-")
    if not slug:
        raise ValueError("key must contain at least one alphanumeric character")
    return slug


class JSONStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.evidence_dir = self.root / "evidence"
        self.knowledge_dir = self.root / "knowledge"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

    # --- Evidence -----------------------------------------------------

    def _evidence_path(self, evidence_id: str) -> Path:
        return self.evidence_dir / f"{evidence_id}.json"

    def save_evidence(self, data: dict) -> None:
        path = self._evidence_path(data["id"])
        _atomic_write_json(path, data)

    def load_evidence(self, evidence_id: str) -> Optional[dict]:
        path = self._evidence_path(evidence_id)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def list_evidence_ids(self) -> list:
        return sorted(p.stem for p in self.evidence_dir.glob("*.json"))

    # --- KnowledgeItem (embeds its states) -----------------------------

    def _knowledge_path(self, item_id: str, feature_area: Optional[str] = None) -> Path:
        if feature_area is not None:
            return self.knowledge_dir / feature_area / f"{item_id}.json"
        # feature_area unknown (lookup-by-id path) - search for it.
        matches = list(self.knowledge_dir.glob(f"*/{item_id}.json"))
        if matches:
            return matches[0]
        return self.knowledge_dir / f"{item_id}.json"  # not found; caller checks existence

    def save_knowledge_item(self, data: dict) -> None:
        path = self._knowledge_path(data["id"], data["feature_area"])
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(path, data)

    def load_knowledge_item(self, item_id: str) -> Optional[dict]:
        path = self._knowledge_path(item_id)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def list_knowledge_item_ids(self) -> list:
        return sorted(p.stem for p in self.knowledge_dir.glob("*/*.json"))


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write a complete temp file then rename - a reader never observes
    a partially-written record, matching the atomic-publish discipline
    already established for this repository's other persistence code."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)
