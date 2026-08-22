"""Codex audit finding DI-S2-02 regression: the Slice 2 bridge
(`_safe_ppt_engine_import.py`) and the Safe PPT Engine's own established
import path (`from lib import ppt_engine`, used by
`baseline/B4PS-TUT-main/.b4ps-tools/tests/` itself via its own
`conftest.py` sys.path insertion) must converge on one shared module/type
identity whenever that is safely possible - and must never corrupt or
silently misresolve `sys.modules["lib"]` (in particular, must never
disturb `editorial-memory/lib`'s own separate, legitimate claim on that
same bare name) in the direction where true convergence is not safely
achievable.

Two process-isolated orderings, exactly as Codex specified:

  A. established path first, Slice 2 bridge second -> fixed, converges.
  B. Slice 2 bridge first, established path second -> NOT safely
     closable without this bridge claiming `sys.modules["lib"]`
     proactively for `.b4ps-tools/lib`, which would break every normal
     `documentation-intelligence/tests/` run (`test_compare.py` already
     claims `lib` for `editorial-memory/lib` in the same process) the
     moment `.b4ps-tools` also happened to be on `sys.path`. See
     `_safe_ppt_engine_import.py`'s own module docstring for the full
     reasoning. This test documents the current, honest, non-corrupting
     behavior for order B rather than asserting a false identity
     equality.

Process isolation (subprocess) for the same reason as
`test_import_alias_first.py`: which module claims a name first is a
real, one-time, process-global fact.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOLS_DIR = _REPO_ROOT / "baseline" / "B4PS-TUT-main" / ".b4ps-tools"
_DI_DIR = _REPO_ROOT / "documentation-intelligence"
_EM_LIB_INIT = _REPO_ROOT / "editorial-memory" / "lib" / "__init__.py"

_ORDER_A_SCRIPT = textwrap.dedent(
    f"""
    import sys
    sys.path.insert(0, r"{_TOOLS_DIR}")
    from lib import ppt_engine as established

    sys.path.insert(0, r"{_DI_DIR}")
    import documentation_intelligence._safe_ppt_engine_import as bridge

    assert bridge._engine is established, "module identity did not converge"
    assert bridge.SafeDeckError is established.SafeDeckError
    assert bridge.DeckSourceError is established.DeckSourceError

    # Repeated bridge import stability: re-importing must not reload or
    # change identity.
    import importlib
    reimported = importlib.import_module("documentation_intelligence._safe_ppt_engine_import")
    assert reimported.inspect_deck is bridge.inspect_deck
    assert reimported is bridge

    print("ORDER-A-CONVERGED-OK")
    """
)

_ORDER_B_SCRIPT = textwrap.dedent(
    f"""
    import sys
    sys.path.insert(0, r"{_DI_DIR}")
    import documentation_intelligence._safe_ppt_engine_import as bridge

    # Editorial Memory's own bridge must be able to claim `lib` for
    # itself in the same process, completely unaffected by the Safe PPT
    # Engine bridge having already run - this is the invariant that
    # makes closing order A safe never having to touch `lib` at all.
    from documentation_intelligence._editorial_memory_import import EditorialMemory
    assert sys.modules["lib"].__file__ == r"{_EM_LIB_INIT}", (
        "editorial-memory/lib must still own the bare name `lib` after "
        "the Safe PPT Engine bridge ran first"
    )

    # Now the Safe PPT Engine's own established path runs, in a process
    # where `lib` is already legitimately claimed by editorial-memory.
    # Python's own import machinery uses the cached `sys.modules["lib"]`
    # (editorial-memory's package, whose `__path__` only ever searches
    # `editorial-memory/lib/`) and correctly fails loudly - it does NOT
    # silently reuse or corrupt editorial-memory's `lib`, and it does NOT
    # fall through to `.b4ps-tools/lib` even though that directory is
    # also on `sys.path` now, since `lib` was never re-resolved from
    # scratch.
    sys.path.insert(0, r"{_TOOLS_DIR}")
    raised = False
    try:
        from lib import ppt_engine as established
    except ImportError:
        raised = True
    assert raised, (
        "expected ImportError: editorial-memory's `lib` package has no "
        "`ppt_engine` submodule, and must not silently fall through to "
        "`.b4ps-tools/lib` instead"
    )

    assert sys.modules["lib"].__file__ == r"{_EM_LIB_INIT}", (
        "editorial-memory/lib must remain untouched and uncorrupted "
        "regardless of what the Safe PPT Engine's established path did"
    )

    print("ORDER-B-EM-LIB-PRESERVED-OK")
    """
)

_ORDER_B_NO_EM_SCRIPT = textwrap.dedent(
    f"""
    import sys
    sys.path.insert(0, r"{_DI_DIR}")
    import documentation_intelligence._safe_ppt_engine_import as bridge

    sys.path.insert(0, r"{_TOOLS_DIR}")
    from lib import ppt_engine as established

    # Documented, honest current behavior: without an already-loaded
    # editorial-memory/lib in the way, order B still does not converge -
    # two independently-correct, non-identical module objects for the
    # same file. Not corrupted, not crashed, just not `is`-identical.
    # See `_safe_ppt_engine_import.py` for why closing this direction
    # would require claiming `lib` preemptively, which is unsafe.
    identical = (
        bridge._engine is established
        and bridge.SafeDeckError is established.SafeDeckError
        and bridge.DeckSourceError is established.DeckSourceError
    )
    assert identical is False, (
        "order B unexpectedly converged - if this now passes, "
        "DI-S2-02 order B has been closed and this test (and the "
        "module docstring's reported-limitation note) should be updated"
    )

    # Not corrupted: `sys.modules["lib"]` really is the genuine
    # `.b4ps-tools/lib` package (nothing hijacked or pre-claimed it), and
    # both module objects still work correctly on their own.
    assert sys.modules["lib"].ppt_engine is established
    assert callable(bridge.inspect_deck)
    assert callable(established.inspect_deck)

    print("ORDER-B-DOCUMENTED-NON-CONVERGENCE-OK")
    """
)


def _run(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_order_a_established_path_first_converges():
    result = _run(_ORDER_A_SCRIPT)
    assert result.returncode == 0, (
        f"order A convergence regression failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "ORDER-A-CONVERGED-OK" in result.stdout


def test_order_b_bridge_first_never_corrupts_editorial_memory_lib():
    result = _run(_ORDER_B_SCRIPT)
    assert result.returncode == 0, (
        f"order B EM-lib-preservation regression failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "ORDER-B-EM-LIB-PRESERVED-OK" in result.stdout


def test_order_b_bridge_first_documented_non_convergence_without_em():
    result = _run(_ORDER_B_NO_EM_SCRIPT)
    assert result.returncode == 0, (
        f"order B documented-behavior regression failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "ORDER-B-DOCUMENTED-NON-CONVERGENCE-OK" in result.stdout
