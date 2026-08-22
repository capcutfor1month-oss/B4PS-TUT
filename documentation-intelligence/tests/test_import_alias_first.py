"""Re-audit 1 finding DI-S1-04 regression: `editorial-memory/lib` already
loaded under some *other*, non-canonical alias before the Documentation
Intelligence bridge ever runs must be canonicalized under `lib`, not
merely reused - otherwise a later, unrelated plain `import lib` elsewhere
in the process would find `lib` still unclaimed and freshly re-import
`editorial-memory/lib` from disk, creating a second, non-`is`-identical
copy.

This condition is fundamentally about *which module claims a name
first, once, per process* - Python's `sys.modules` cache is process-
global and a name-claim cannot be "undone" or re-ordered after the fact
within one process. `test_import_order.py` already covers the bare-
`lib`-first scenario using this test suite's own real collection order.
That trick does not extend to the alias-first scenario without either
(a) forcing this file to always collect before every other test file
that might import the bridge (fragile, and it already doesn't hold - the
bridge is transitively imported by `test_compare.py`, which collects
first alphabetically), or (b) full process isolation. This test uses (b):
a fresh, clean Python subprocess performs the exact sequence Codex
reproduced, self-checks it, and reports pass/fail via exit code and
stdout - avoiding any dependency on this suite's own collection order or
on what any other test file in this session has already imported.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EM_LIB_INIT = _REPO_ROOT / "editorial-memory" / "lib" / "__init__.py"
_DI_DIR = _REPO_ROOT / "documentation-intelligence"

_SUBPROCESS_SCRIPT = textwrap.dedent(
    f"""
    import importlib.util
    import sys

    # Step 1: simulate "editorial-memory/lib already loaded under some
    # other, non-canonical alias" - exactly the condition Codex
    # reproduced - *before* anything Documentation-Intelligence-side has
    # touched sys.modules at all.
    ALIAS = "some_other_consumers_private_alias_for_editorial_memory_lib"
    em_lib_dir = r"{_EM_LIB_INIT.parent}"
    em_lib_init = r"{_EM_LIB_INIT}"
    spec = importlib.util.spec_from_file_location(
        ALIAS, em_lib_init, submodule_search_locations=[em_lib_dir],
    )
    alias_module = importlib.util.module_from_spec(spec)
    sys.modules[ALIAS] = alias_module
    spec.loader.exec_module(alias_module)

    assert "lib" not in sys.modules, "precondition violated: lib already claimed"

    # Step 2: only now does the Documentation Intelligence bridge run.
    sys.path.insert(0, r"{_DI_DIR}")
    from documentation_intelligence._editorial_memory_import import (
        EditorialMemory as BridgeEditorialMemory,
        Relation as BridgeRelation,
    )

    # Check A: the bridge must have reused the alias-loaded object, not
    # created an independent duplicate.
    assert BridgeRelation is alias_module.Relation, "bridge created a duplicate Relation class"
    assert BridgeEditorialMemory is alias_module.EditorialMemory, "bridge created a duplicate EditorialMemory class"

    # Check B (the actual DI-S1-04 defect): the alias-loaded module must
    # now ALSO be canonicalized under the bare name `lib`, so a later,
    # completely unrelated plain `import lib` elsewhere in this same
    # process converges on the identical object instead of triggering a
    # fresh, independent re-import from disk.
    assert "lib" in sys.modules, "editorial-memory/lib was not canonicalized under `lib` after alias-first load"
    assert sys.modules["lib"] is alias_module, "sys.modules['lib'] does not point at the alias-loaded object"

    # Check C: prove it functionally - a later plain import really does
    # get the identical, non-duplicated object.
    import importlib
    later_direct_import = importlib.import_module("lib")
    assert later_direct_import is alias_module, "a later plain `import lib` created a duplicate copy"
    assert later_direct_import.Relation is BridgeRelation, "duplicate Relation identity across import paths"

    print("DI-S1-04-REGRESSION-OK")
    """
)


def test_alias_first_load_is_canonicalized_under_lib_no_duplicate_identity():
    result = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_SCRIPT],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"alias-first import regression failed\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "DI-S1-04-REGRESSION-OK" in result.stdout
