"""Bridge to the sibling Safe PPT Engine module
(`baseline/B4PS-TUT-main/.b4ps-tools/lib/ppt_engine.py`).

`ppt_engine.py` has no internal package-relative imports of its own
(verified: it imports only stdlib, `PIL`, and `pptx`) - it is a single
self-contained file, not a package with siblings that need to resolve
`from . import` against a shared parent name. That means this bridge
never *needs* to claim the bare name `lib` for its own private load - it
can load the file directly under a fixed private module name via
`importlib.util`, with no `sys.path` change and no name-claiming.

History (Codex audit finding DI-S2-02, repaired):

The private load above is correct but incomplete on its own: the Safe
PPT Engine's own *established* import path - `from lib import
ppt_engine`, used by `baseline/B4PS-TUT-main/.b4ps-tools/tests/` itself,
which inserts `.b4ps-tools` onto `sys.path` via its own `conftest.py` -
loads the exact same physical file under the bare name `lib.ppt_engine`.
If that established path ran first in the same process, this bridge's
private load created a second, non-`is`-identical copy - duplicate
`SafeDeckError`/`DeckSourceError`/module identity, the same shape of bug
Slice 1's `_editorial_memory_import.py` bridge exists to prevent for
`editorial-memory/lib`.

Fixed for that direction (established path already loaded, this bridge
runs second): before doing any private load, this module checks whether
`sys.modules["lib"]` already exists *and* already has a `ppt_engine`
attribute whose `__file__` resolves to this exact expected path - i.e.
the established path already did the real work - and if so, reuses that
exact object instead of loading a second copy. This is read-only
detection: `sys.modules["lib"]` itself is never written, claimed, or
overwritten by this bridge, so an unrelated `lib` (in particular
`editorial-memory/lib`, which has no `ppt_engine` attribute at all) is
left completely untouched, and this bridge falls back to its own private
load exactly as before.

**Reported, not fixed - the reverse direction (Codex DI-S2-02, order B:
this bridge's private load runs first, and the established `from lib
import ppt_engine` path runs afterward in the same process) cannot be
safely closed within this repository's current package structure.**
Making that later import converge on this bridge's already-loaded object
would require this bridge to itself claim `sys.modules["lib"]` for
`.b4ps-tools/lib` proactively, before knowing whether the process will
ever run `.b4ps-tools`'s own tests at all. `editorial-memory/lib` (a
second, genuinely different real package) is *also* only ever willing to
occupy the bare name `lib` for itself, and correctly refuses (raises
`EditorialMemoryImportConflictError`, see `_editorial_memory_import.py`)
to reuse or silently coexist with an unrelated occupant. If this bridge
claimed `lib` for `.b4ps-tools/lib` first, a later, completely normal
import of `documentation_intelligence.compare` (which every
`documentation-intelligence/tests/` run already does, in the same
process, via `test_compare.py`) would then find `lib` occupied by the
wrong package and fail outright - breaking Slice 1 to chase a narrower
Slice 2 ordering. Closing order B for real requires a repository-wide
decision about which package (if either) is allowed to own the bare name
`lib` process-wide - out of scope for this bounded repair. Order B
therefore remains two independently-correct, non-`is`-identical module
objects for the same file; nothing is corrupted, silently misresolved,
or torn - see `tests/test_ppt_engine_import_order.py`, which documents
this exact, current, honest behavior rather than asserting a false
identity equality.

This does not modify, wrap, or reimplement anything in the Safe PPT
Engine - it only guarantees, wherever safely possible, a single shared
identity for `ppt_engine.py`, then re-exports exactly the names Slice 2
needs.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Optional

_PPT_ENGINE_FILE = (
    Path(__file__).resolve().parents[2]
    / "baseline"
    / "B4PS-TUT-main"
    / ".b4ps-tools"
    / "lib"
    / "ppt_engine.py"
).resolve()
_MODULE_NAME = "_documentation_intelligence_safe_ppt_engine"
_ESTABLISHED_LIB_NAME = "lib"


def _resolved_file(module: object) -> Optional[Path]:
    candidate_file = getattr(module, "__file__", None)
    if candidate_file is None:
        return None
    try:
        return Path(candidate_file).resolve()
    except OSError:
        return None


def _find_via_established_lib_path():
    """Read-only: if the Safe PPT Engine's own established `from lib
    import ppt_engine` path has already loaded the exact expected
    `ppt_engine.py` under the bare name `lib`, return that submodule
    object. Never writes to `sys.modules["lib"]`. Returns `None` for
    every other case - `lib` unclaimed, or claimed by something without a
    matching `ppt_engine` attribute (e.g. `editorial-memory/lib`) - so
    this bridge never touches an unrelated or Editorial-Memory-owned
    `lib`."""
    lib_pkg = sys.modules.get(_ESTABLISHED_LIB_NAME)
    if lib_pkg is None:
        return None
    candidate = getattr(lib_pkg, "ppt_engine", None)
    if candidate is None:
        return None
    if _resolved_file(candidate) != _PPT_ENGINE_FILE:
        return None
    return candidate


def _load_ppt_engine():
    cached = sys.modules.get(_MODULE_NAME)
    if cached is not None:
        return cached

    established = _find_via_established_lib_path()
    if established is not None:
        sys.modules[_MODULE_NAME] = established
        return established

    spec = importlib.util.spec_from_file_location(_MODULE_NAME, _PPT_ENGINE_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


_engine = _load_ppt_engine()

inspect_deck = _engine.inspect_deck
set_shape_text = _engine.set_shape_text
load_deck = _engine.load_deck
file_sha256 = _engine.file_sha256
SafeDeckError = _engine.SafeDeckError
DeckSourceError = _engine.DeckSourceError
MutationError = _engine.MutationError
ValidationError = _engine.ValidationError

__all__ = [
    "inspect_deck",
    "set_shape_text",
    "load_deck",
    "file_sha256",
    "SafeDeckError",
    "DeckSourceError",
    "MutationError",
    "ValidationError",
]
