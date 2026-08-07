"""Reproducibility: the CLI must run end-to-end from a clean checkout with
only requirements.txt installed - no reliance on prior local state or a
specific developer's machine."""

import os
import subprocess
import sys

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B4PS_PY = os.path.join(TOOLS_DIR, "b4ps.py")


def _run(*args):
    return subprocess.run(
        [sys.executable, B4PS_PY, *args],
        capture_output=True, text=True, cwd=TOOLS_DIR)


def test_status_runs_clean():
    result = _run("status")
    assert result.returncode == 0, result.stderr
    assert "thresholds:" in result.stdout


def test_scan_runs_clean_even_with_no_screenshots_present():
    result = _run("scan")
    assert result.returncode == 0, result.stderr


def test_unknown_command_fails_with_nonzero_exit():
    result = _run("this-command-does-not-exist")
    assert result.returncode != 0
