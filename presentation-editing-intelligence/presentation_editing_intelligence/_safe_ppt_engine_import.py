"""Bridge to the sibling Safe PPT Engine module
(`baseline/B4PS-TUT-main/.b4ps-tools/lib/ppt_engine.py`), mirroring
`documentation_intelligence._safe_ppt_engine_import`'s own bridge exactly
(same private-load-with-established-path-detection pattern, same known,
documented "order B" limitation - see that module's docstring for the
full rationale, not repeated here).

Codex finding PEI-S1-01: this package's actual real-file mutation must
not implement its own publication protocol. `set_shape_text_runs_and_geometry`
is a new primitive *added to `ppt_engine.py` itself* (not reimplemented
here) - it reuses that file's own private staging/publication machinery
(`_staged_copy`, `_finalize_transaction`, `_publish_atomically`'s
race-free `os.link`-based no-clobber publication) directly, since that
machinery is private to that module and only usable from inside it. This
bridge only re-exports the finished, already-audited public functions -
`text_mutation.py` calls this one primitive and nothing lower-level.
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
_MODULE_NAME = "_presentation_editing_intelligence_safe_ppt_engine"
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
    lib_pkg = sys.modules.get(_ESTABLISHED_LIB_NAME)
    if lib_pkg is None:
        return None
    candidate = getattr(lib_pkg, "ppt_engine", None)
    if candidate is None:
        return None
    if _resolved_file(candidate) != _PPT_ENGINE_FILE:
        return None
    return candidate


def _find_via_documentation_intelligence_bridge():
    """Read-only: if `documentation_intelligence`'s own bridge has
    already loaded `ppt_engine.py` under its private module name, reuse
    that exact object instead of loading a third copy. Never imports
    `documentation_intelligence` itself (that would be a new, unwanted
    cross-package dependency) - only checks `sys.modules` for what may
    already be there."""
    cached = sys.modules.get("_documentation_intelligence_safe_ppt_engine")
    if cached is None:
        return None
    if _resolved_file(cached) != _PPT_ENGINE_FILE:
        return None
    return cached


def _load_ppt_engine():
    cached = sys.modules.get(_MODULE_NAME)
    if cached is not None:
        return cached

    established = _find_via_established_lib_path()
    if established is not None:
        sys.modules[_MODULE_NAME] = established
        return established

    di_bridge = _find_via_documentation_intelligence_bridge()
    if di_bridge is not None:
        sys.modules[_MODULE_NAME] = di_bridge
        return di_bridge

    spec = importlib.util.spec_from_file_location(_MODULE_NAME, _PPT_ENGINE_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


_engine = _load_ppt_engine()

inspect_deck = _engine.inspect_deck
load_deck = _engine.load_deck
file_sha256 = _engine.file_sha256
move_shape = _engine.move_shape
resize_shape = _engine.resize_shape
set_shape_geometry = _engine.set_shape_geometry
set_shape_text_runs_and_geometry = _engine.set_shape_text_runs_and_geometry
SafeDeckError = _engine.SafeDeckError
DeckSourceError = _engine.DeckSourceError
OutputPathError = _engine.OutputPathError
MutationError = _engine.MutationError
ValidationError = _engine.ValidationError
TransactionIOError = _engine.TransactionIOError

__all__ = [
    "inspect_deck",
    "load_deck",
    "file_sha256",
    "move_shape",
    "resize_shape",
    "set_shape_geometry",
    "set_shape_text_runs_and_geometry",
    "SafeDeckError",
    "DeckSourceError",
    "OutputPathError",
    "MutationError",
    "ValidationError",
    "TransactionIOError",
]
