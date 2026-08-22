"""Re-audit 2 finding DI-S1-04 regression: if `sys.modules["lib"]` is
already occupied by a genuinely unrelated module - not editorial-memory's
own `lib`, under any alias - and no already-loaded copy of
`editorial-memory/lib` exists anywhere to canonicalize instead, the bridge
must raise `EditorialMemoryImportConflictError` before loading anything.

Repair Round 2's fix only closed the *alias-first* ordering (an existing
copy found under a different name gets canonicalized under `lib`). It
left one path open: `lib` occupied by something unrelated, with no
existing editorial-memory copy anywhere to reuse. That path used to fall
back to loading a fresh copy under a fixed private alias, silently -
exactly the divergent-identity risk this module exists to prevent, via a
different door.

Process isolation (subprocess), same rationale as
`test_import_alias_first.py`: which module claims the name `lib` first is
a real, one-time, process-global fact that cannot be staged reliably
inside this suite's own already-running process.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DI_DIR = _REPO_ROOT / "documentation-intelligence"

_SUBPROCESS_SCRIPT = textwrap.dedent(
    f"""
    import sys
    import types

    # Step 1: an unrelated module claims `lib` first - nothing to do with
    # editorial-memory at all.
    unrelated = types.ModuleType("lib")
    unrelated.some_unrelated_attribute = "not editorial-memory"
    sys.modules["lib"] = unrelated

    # Step 2: only now does the Documentation Intelligence bridge run.
    sys.path.insert(0, r"{_DI_DIR}")
    try:
        import documentation_intelligence._editorial_memory_import as bridge
    except Exception as exc:
        assert type(exc).__name__ == "EditorialMemoryImportConflictError", (
            f"expected EditorialMemoryImportConflictError, got {{type(exc).__name__}}: {{exc}}"
        )
    else:
        raise AssertionError("expected EditorialMemoryImportConflictError, no exception raised")

    # Step 3: prove editorial-memory was NOT silently loaded under the old
    # private alias as a fallback.
    assert "documentation_intelligence._editorial_memory_import" not in sys.modules
    assert sys.modules["lib"] is unrelated, "unrelated `lib` binding must be left untouched"
    assert not any(
        name.endswith("_documentation_intelligence_editorial_memory_lib")
        for name in sys.modules
    ), "editorial-memory/lib must not have been loaded under the old private alias"

    print("DI-S1-04-CONFLICT-REGRESSION-OK")
    """
)


def test_unrelated_lib_occupant_raises_conflict_error_not_silent_alias_fallback():
    result = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_SCRIPT],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"unrelated-lib conflict regression failed\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "DI-S1-04-CONFLICT-REGRESSION-OK" in result.stdout
