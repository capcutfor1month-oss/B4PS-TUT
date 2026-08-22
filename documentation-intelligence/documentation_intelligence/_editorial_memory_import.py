"""Bridges to the sibling `editorial-memory/lib` package.

`editorial-memory` is a top-level directory with a hyphen in its name, so
it cannot be imported as a normal dotted Python package. This module
guarantees at most one loaded copy of `editorial-memory/lib` process-wide,
regardless of what already imported it or under what name, so
`Relation`/`KnowledgeType`/every exception class is always the same
object everywhere in the process.

History (Audit 1 finding 4, repaired; Re-audit 1 DI-S1-04, repaired
again):

The first version loaded `editorial-memory/lib` under a fixed private
alias from inside a sibling package that was itself also named `lib`
(`documentation-intelligence/lib`), colliding with
`editorial-memory/tests/test_editorial_memory.py`'s own established bare
`from lib import ...` convention. Fixed by renaming this package to
`documentation_intelligence` (it no longer contends for the name `lib`
at all) and having this module claim the canonical name `lib` for
`editorial-memory/lib` itself, so later plain imports elsewhere converge
on it via Python's own `sys.modules` cache.

That fix still had a gap Codex reproduced: if `editorial-memory/lib` was
already loaded under some *other*, non-canonical alias before this module
ran - e.g. a different consumer's own private-alias `importlib` load,
matching the exact shape this module's own first version used - this
module's `_find_already_loaded` scan correctly found and reused that
object, but never *also* registered it under the canonical name `lib`.
A later, unrelated plain `import lib` elsewhere in the same process would
then find `lib` still unclaimed, and freshly re-import
`editorial-memory/lib` from disk under that name - creating a second,
non-`is`-identical copy, the exact defect this module exists to prevent.

Fixed here: whenever an already-loaded copy is found under a
non-canonical name, it is *canonicalized* - registered under `lib` too
(Option A: "safely canonicalized under `lib` ... preserving identity") -
so every subsequent import, under any name, converges on the single
existing object. If `lib` is already bound to something that is
genuinely not `editorial-memory/lib` (a real name collision with an
unrelated package, not merely a different alias for the same file), this
module refuses to guess and raises `EditorialMemoryImportConflictError`
explicitly (Option B: "the unsupported state fails explicitly and safely
before duplicate identities can exist") rather than silently proceeding
under an alias that could diverge from what everyone else's plain
`import lib` resolves to.

That fix still had one remaining gap Codex reproduced (Re-audit 2,
DI-S1-04): if `lib` was already bound to something genuinely unrelated
*and* no already-loaded copy of `editorial-memory/lib` existed anywhere
to canonicalize, `_load_editorial_memory_lib` fell back to loading a
fresh copy under a fixed private alias instead of failing - reintroducing
exactly the divergent-identity risk this module exists to prevent, just
via a different code path than the one already closed above. Fixed here:
that fallback is removed. When `lib` is occupied by an unrelated module
and no existing copy can be canonicalized instead, this module now raises
`EditorialMemoryImportConflictError` before loading anything, rather than
loading under any alias.

This does not modify, wrap, or reimplement anything in `editorial-memory`
- it only guarantees a single shared identity for its existing `lib`
package, then re-exports exactly the names Slice 1 (and its tests) need
from that single copy.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Optional

_EM_LIB_DIR = (Path(__file__).resolve().parents[2] / "editorial-memory" / "lib").resolve()
_EM_LIB_INIT = _EM_LIB_DIR / "__init__.py"
_CANONICAL_NAME = "lib"


class EditorialMemoryImportConflictError(ImportError):
    """Raised when `editorial-memory/lib` cannot be safely canonicalized
    under the name `lib` because that name is already bound to a module
    that is genuinely something else - not merely a different alias for
    the same source file. Raised instead of silently proceeding under a
    private alias that could diverge from what a later plain `import lib`
    elsewhere in the process would resolve to."""


def _resolved_file(module: object) -> Optional[Path]:
    candidate_file = getattr(module, "__file__", None)
    if candidate_file is None:
        return None
    try:
        return Path(candidate_file).resolve()
    except OSError:
        return None


def _find_already_loaded():
    for module in list(sys.modules.values()):
        if _resolved_file(module) == _EM_LIB_INIT:
            return module
    return None


def _canonicalize_under_lib(module, loaded_as_name: str) -> None:
    """Register `module` - already loaded under `loaded_as_name` - under
    the canonical name `lib` too, so any later plain `import lib` /
    `from lib import X` anywhere else in the process is a cache hit
    against this exact object rather than a fresh, duplicate re-import.

    Also re-registers any of its already-imported submodules under the
    equivalent `lib.<name>` key, covering a hypothetical future consumer
    that imports a submodule path directly (`from lib.memory import X`)
    rather than the flat `from lib import X` this repository's actual
    consumers use - `lib/__init__.py` already re-exports every name this
    module needs as flat attributes, so this repository's real callers
    never depend on the submodule keys themselves, but canonicalizing
    them too costs nothing and closes the gap completely rather than
    partially.
    """
    existing_lib = sys.modules.get(_CANONICAL_NAME)
    if existing_lib is not None and existing_lib is not module:
        raise EditorialMemoryImportConflictError(
            f"cannot canonicalize editorial-memory/lib (currently loaded as "
            f"{loaded_as_name!r}) under the name {_CANONICAL_NAME!r}: that name is "
            f"already bound to a different module ({existing_lib!r}), not a mere "
            f"alias of the same file. Refusing to proceed under a private alias "
            f"that could diverge from what a later plain `import lib` elsewhere in "
            f"this process would resolve to."
        )

    sys.modules[_CANONICAL_NAME] = module
    if loaded_as_name != _CANONICAL_NAME:
        prefix = loaded_as_name + "."
        for name, submodule in list(sys.modules.items()):
            if name.startswith(prefix):
                canonical_submodule_name = _CANONICAL_NAME + name[len(loaded_as_name):]
                sys.modules.setdefault(canonical_submodule_name, submodule)


def _load_editorial_memory_lib():
    existing = _find_already_loaded()
    if existing is not None:
        _canonicalize_under_lib(existing, existing.__name__)
        return existing

    already_named_lib = sys.modules.get(_CANONICAL_NAME)
    if already_named_lib is not None:
        # `_find_already_loaded()` found nothing, so whatever currently owns
        # `lib` is not editorial-memory/lib under any name - a genuine,
        # unrelated occupant. Loading under `_PRIVATE_ALIAS` here would be
        # exactly the silent fallback Re-audit 2 (DI-S1-04) found: it lets
        # Documentation Intelligence proceed on a copy that a later plain
        # `import lib` elsewhere in the process would never converge on.
        raise EditorialMemoryImportConflictError(
            f"cannot load editorial-memory/lib under the canonical name "
            f"{_CANONICAL_NAME!r}: that name is already bound to an unrelated "
            f"module ({already_named_lib!r}), and no already-loaded copy of "
            f"editorial-memory/lib exists elsewhere to canonicalize instead. "
            f"Refusing to fall back to a private alias that could diverge "
            f"from what a later plain `import lib` elsewhere in this process "
            f"would resolve to."
        )
    target_name = _CANONICAL_NAME

    spec = importlib.util.spec_from_file_location(
        target_name,
        _EM_LIB_INIT,
        submodule_search_locations=[str(_EM_LIB_DIR)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[target_name] = module
    spec.loader.exec_module(module)
    return module


_em = _load_editorial_memory_lib()

# `editorial-memory/lib/__init__.py` already re-exports its full public API
# as flat names on the package object itself, regardless of how/under what
# name the package was loaded - so every name below is a direct attribute
# lookup on the single shared `_em` module object, never a fresh submodule
# import that could create a second copy of anything.
EditorialMemory = _em.EditorialMemory
Evidence = _em.Evidence
EvidenceQuality = _em.EvidenceQuality
EvidenceType = _em.EvidenceType
KnowledgeItem = _em.KnowledgeItem
KnowledgeType = _em.KnowledgeType
Relation = _em.Relation
CurrentKnowledge = _em.CurrentKnowledge
get_current_by_key = _em.get_current_by_key
list_current_by_feature_area = _em.list_current_by_feature_area
UnknownEvidenceError = _em.UnknownEvidenceError
KnowledgeTypeMismatchError = _em.KnowledgeTypeMismatchError

# `slugify` is not part of `lib/__init__.py`'s re-exported public API, so it
# is reached via the `store` submodule, which is guaranteed to already be an
# attribute of `_em` (Python binds an imported submodule onto its parent
# package automatically - `memory.py`'s own `from .store import ...`
# already triggered this as a side effect of loading `_em` above).
slugify = _em.store.slugify

__all__ = [
    "EditorialMemory",
    "Evidence",
    "EvidenceQuality",
    "EvidenceType",
    "KnowledgeItem",
    "KnowledgeType",
    "Relation",
    "CurrentKnowledge",
    "get_current_by_key",
    "list_current_by_feature_area",
    "UnknownEvidenceError",
    "KnowledgeTypeMismatchError",
    "slugify",
    "EditorialMemoryImportConflictError",
]
