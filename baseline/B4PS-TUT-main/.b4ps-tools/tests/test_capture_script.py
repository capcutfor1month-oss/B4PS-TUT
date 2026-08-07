"""Reproducibility regression: the capture script must resolve its project
root at run time instead of hardcoding one developer's machine path."""

import os
import subprocess

SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts", "capture_and_rename.sh")


def test_no_hardcoded_personal_path():
    with open(SCRIPT, encoding="utf-8") as fh:
        text = fh.read()
    assert "/Users/" not in text


def test_script_is_valid_bash():
    result = subprocess.run(["bash", "-n", SCRIPT], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
