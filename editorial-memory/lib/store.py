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

A purged KnowledgeState (Slice 7 bounded purge) is never stored in a
new location of its own - its tombstone overwrites its own existing
array slot inside the same per-item file it always lived in.
`load_knowledge_item` filters any tombstone-shaped entry back out of
`states` for every ordinary caller; `load_knowledge_item_raw` and
`tombstoned_versions` are the only ways to see a retained tombstone.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from .errors import (
    InvalidEvidenceIdError,
    InvalidFeatureAreaError,
    InvalidKnowledgeItemIdError,
    StorageCorruptionError,
)

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

# `item_id` is always a `slugify()` output too - same safe-token shape
# as `_EVIDENCE_ID_RE` (EM47-02). Purge's `item_id` argument arrives as a
# plain caller-supplied string, not routed through
# `get_or_create_knowledge_item`, so it must be validated as a literal
# safe token in its own right before ever being used to build a lookup
# path, rather than trusted just because it looks like a slug.
_KNOWLEDGE_ITEM_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# The one field present on a purge tombstone (`{id, purged_at, purged_by,
# reason}`) and never on a real KnowledgeState (which has `created_at`/
# `approved_at`/`invalidated_at`, never `purged_at`) - the discriminator
# `is_tombstone_entry` uses to identify a candidate tombstone before
# validating its full shape.
TOMBSTONE_MARKER_KEY = "purged_at"

# The exact, complete key set of the approved non-claim tombstone
# contract - nothing more, nothing less. A dict with `TOMBSTONE_MARKER_KEY`
# whose keys don't match this exactly is never a valid tombstone.
_TOMBSTONE_KEYS = frozenset({"id", "purged_at", "purged_by", "reason"})

# Canonical version-suffix shape for a tombstone `id`: a positive ASCII
# integer with no leading zero. `str.isdigit()` is deliberately not used
# here - it accepts Unicode digits (e.g. superscript "²") that are
# not valid version numbers. "0" and "01" are also rejected: versions are
# 1-based and never zero-padded. Matched with `fullmatch`, not `match`+`$`
# - plain `$` matches just before a trailing newline, so `match` alone
# would wrongly accept a suffix like "1\n".
_TOMBSTONE_VERSION_RE = re.compile(r"[1-9][0-9]*")

# Deterministic, explicit upper bound on a tombstone version suffix's
# digit count, checked *before* any `int()` conversion is attempted.
# Not derived from `sys.int_info.default_max_str_digits` (Python's own
# int-string conversion guard) deliberately: that guard's default value
# has changed across Python versions and is process-configurable, so
# relying on it would make "oversized suffix rejected" a property of the
# interpreter running this code rather than of the data itself. 18
# digits comfortably exceeds any version number this system will ever
# generate (versions increment by 1 per proposal) while staying far
# below every Python version's int-conversion limit on every supported
# version.
_TOMBSTONE_VERSION_MAX_DIGITS = 18


def is_tombstone_entry(entry: dict, item_id: str) -> bool:
    """Strict discrimination between a real KnowledgeState dict and a
    purge tombstone (round-4 finding 1). A dict is only ever treated as
    a tombstone if its keys are *exactly* the canonical contract -
    `{id, purged_at, purged_by, reason}` - and its `id` parses as
    `"<item_id>#<version>"` for *this* item_id specifically.

    A dict with no `TOMBSTONE_MARKER_KEY` at all is unambiguously a real
    state (returns `False` immediately, no further inspection).

    Any dict that *does* contain `TOMBSTONE_MARKER_KEY` but doesn't match
    the exact shape or identity above is ambiguous - it could be a
    malformed tombstone, or a real `KnowledgeState` that has somehow
    acquired a stray `purged_at` field (corruption, a bug, tampering) -
    and must never be silently resolved either way: treating a corrupted
    real state as a tombstone would silently make current/history truth
    disappear from every normal query path (`get_current`, `get_history`,
    the Slice 5 review queue, `get_invalidated_by_key`); treating a
    malformed tombstone as a real state would either crash
    `KnowledgeState.from_dict` with a raw `KeyError`, or - if it happened
    to also carry enough real-state-shaped fields - silently coerce
    unsafe/incomplete data into a claim nobody actually made. Raises
    typed `StorageCorruptionError` for this ambiguous case instead -
    never a raw `KeyError`/`IndexError` reaches the caller."""
    if TOMBSTONE_MARKER_KEY not in entry:
        return False
    if set(entry.keys()) != _TOMBSTONE_KEYS:
        raise StorageCorruptionError(
            f"persisted entry for KnowledgeItem {item_id!r} has a "
            f"{TOMBSTONE_MARKER_KEY!r} field but its keys {sorted(entry.keys())} "
            f"do not match the canonical tombstone contract {sorted(_TOMBSTONE_KEYS)} "
            "- refusing to silently treat this as either a tombstone or a real state"
        )
    entry_id = entry.get("id")
    prefix = f"{item_id}#"
    if (
        not isinstance(entry_id, str)
        or not entry_id.startswith(prefix)
        or not _TOMBSTONE_VERSION_RE.fullmatch(entry_id[len(prefix):])
    ):
        raise StorageCorruptionError(
            f"tombstone entry {entry_id!r} does not match the expected "
            f"{prefix!r}<version> identity for KnowledgeItem {item_id!r}"
        )
    # The regex alone doesn't bound length: an oversized numeric suffix
    # (thousands of digits) still fullmatches. Reject anything over the
    # explicit, version-independent digit-count bound *before* ever
    # calling `int()` on it, rather than relying on Python's own
    # int-string conversion guard (whose default threshold - and whether
    # it exists at all - varies across supported Python versions). Parsed
    # once, here, at the single validation choke point every caller
    # already routes through, so every caller downstream gets the same
    # typed error, on every Python version.
    version_suffix = entry_id[len(prefix):]
    if len(version_suffix) > _TOMBSTONE_VERSION_MAX_DIGITS:
        raise StorageCorruptionError(
            f"tombstone entry {entry_id!r} has a version suffix longer than "
            f"{_TOMBSTONE_VERSION_MAX_DIGITS} digits for KnowledgeItem {item_id!r}"
        )
    int(version_suffix)
    return True


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
    if not isinstance(feature_area, str) or not _FEATURE_AREA_RE.fullmatch(feature_area):
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
    if not isinstance(evidence_id, str) or not _EVIDENCE_ID_RE.fullmatch(evidence_id):
        raise InvalidEvidenceIdError(
            f"evidence_id {evidence_id!r} is not a safe generated-id token "
            "(lowercase alphanumerics/hyphens only)"
        )
    return evidence_id


def validate_knowledge_item_id(item_id: str) -> str:
    """Reject any `item_id` that isn't a safe generated-id token
    (EM47-02) - mirrors `validate_evidence_id`. Purge's `item_id`
    argument is a plain caller-supplied string, not something the
    normal `get_or_create_knowledge_item` path already validated, so it
    must be checked here before ever being used to build a lookup
    path."""
    if not isinstance(item_id, str) or not _KNOWLEDGE_ITEM_ID_RE.fullmatch(item_id):
        raise InvalidKnowledgeItemIdError(
            f"item_id {item_id!r} is not a safe generated-id token "
            "(lowercase alphanumerics/hyphens only)"
        )
    return item_id


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

    def delete_evidence(self, evidence_id: str) -> None:
        """Full, traceless removal of one Evidence record (Slice 7 purge,
        `tombstone=False`), for the rarer case where even a tombstone
        stub's own metadata would be unsafe to retain."""
        path = self._evidence_path(evidence_id)
        path.unlink(missing_ok=True)

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

    def load_knowledge_item_raw(self, item_id: str) -> Optional[dict]:
        """Unfiltered read - includes any retained purge tombstone in
        `states` exactly as persisted. Used only where tombstone-aware
        logic itself needs to see them (`tombstoned_versions`, purge's
        own target lookup, `EditorialMemory._save_item`'s merge); every
        ordinary caller uses `load_knowledge_item` instead, which
        filters them out."""
        path = self._knowledge_path(item_id)
        if not path.exists():
            return None
        return _load_json(path)

    def load_knowledge_item(self, item_id: str) -> Optional[dict]:
        data = self.load_knowledge_item_raw(item_id)
        if data is None:
            return None
        data["states"] = [s for s in data["states"] if not is_tombstone_entry(s, item_id)]
        return data

    def list_knowledge_item_ids(self) -> list:
        return sorted(p.stem for p in self.knowledge_dir.glob("*/*.json"))

    def tombstoned_versions(self, item_id: str) -> set:
        """Every version number this KnowledgeItem has a retained purge
        tombstone for (finding 1) - read directly from the raw persisted
        record, bypassing `load_knowledge_item`'s filtering, since this
        is exactly the information that filtering hides from ordinary
        callers. Version allocation (`memory._next_version`) must never
        reuse one of these numbers while its tombstone still exists,
        even though the tombstoned state itself is no longer present as
        a real `KnowledgeState`."""
        raw = self.load_knowledge_item_raw(item_id)
        if raw is None:
            return set()
        out = set()
        for entry in raw["states"]:
            if is_tombstone_entry(entry, item_id):
                out.add(int(entry["id"].rsplit("#", 1)[1]))
        return out


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write a complete temp file then rename - a reader never observes
    a partially-written record, matching the atomic-publish discipline
    already established for this repository's other persistence code."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)
