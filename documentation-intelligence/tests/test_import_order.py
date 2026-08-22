"""Codex Audit 1 finding 4 regression: the import bridge must produce one
canonical set of Editorial Memory class/Enum/exception identities
regardless of what already imported `editorial-memory/lib` and under
what name.

This scenario is deliberately import-order-sensitive at the level of
*this test module's own top-level statements*, not something a test
function body can fake after the fact: Python's `import` statement is a
`sys.modules` cache lookup by name first, so "which side claimed a name
first" is a real, one-time, process-wide fact. This file's own imports
establish the "editorial-memory's own established `sys.path` + bare
`from lib import ...` convention runs first" ordering explicitly, then
imports the Documentation Intelligence bridge afterward and proves it
reused the identical objects rather than creating a second copy.

The reverse ordering (Documentation Intelligence's bridge runs first) is
already exercised, implicitly, by every other test in this package: none
of them fail, and none of them would produce a working comparison at all
if the bridge's `EditorialMemory`/`Relation`/etc. were not the real,
correctly-functioning classes - so a dedicated reverse-order test would
be redundant with the whole rest of the suite. What was genuinely
untested before this repair was the direction that broke: something else
claiming `lib` first.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EM_DIR = str(_REPO_ROOT / "editorial-memory")
_DI_DIR = str(_REPO_ROOT / "documentation-intelligence")

# Establish "editorial-memory's own bare `lib` convention runs first" as a
# real, one-time fact for this process, before anything Documentation-
# Intelligence-side touches `sys.modules`.
sys.path.insert(0, _EM_DIR)
import lib as _editorial_memory_lib_direct  # noqa: E402  (bare `lib`, exactly test_editorial_memory.py's own style)

sys.path.insert(0, _DI_DIR)
from documentation_intelligence._editorial_memory_import import (  # noqa: E402
    EditorialMemory as BridgeEditorialMemory,
    Relation as BridgeRelation,
    UnknownEvidenceError as BridgeUnknownEvidenceError,
)


def test_bridge_reuses_the_already_loaded_bare_lib_module():
    """The module object itself must be the same object, not merely an
    equal-looking duplicate."""
    assert sys.modules["lib"] is _editorial_memory_lib_direct


def test_relation_enum_is_identical_object_not_a_duplicate():
    assert BridgeRelation is _editorial_memory_lib_direct.Relation
    assert BridgeRelation.CONFIRMS is _editorial_memory_lib_direct.Relation.CONFIRMS


def test_exception_type_is_identical_object_not_a_duplicate():
    assert BridgeUnknownEvidenceError is _editorial_memory_lib_direct.UnknownEvidenceError


def test_editorial_memory_class_is_identical_and_usable_interchangeably(tmp_path):
    """Functional proof, not just `is` on the class: an object created
    via one import path is a valid instance under the other path's class
    reference, and typed errors raised through one path are catchable
    via the other."""
    assert BridgeEditorialMemory is _editorial_memory_lib_direct.EditorialMemory

    memory = BridgeEditorialMemory(str(tmp_path / "store"))
    assert isinstance(memory, _editorial_memory_lib_direct.EditorialMemory)

    try:
        memory.get_evidence("ev-does-not-exist")
    except _editorial_memory_lib_direct.UnknownEvidenceError:
        pass
    else:
        raise AssertionError("expected UnknownEvidenceError")
