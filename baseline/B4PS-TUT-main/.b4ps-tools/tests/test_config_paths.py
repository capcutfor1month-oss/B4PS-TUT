"""Reproducibility: paths must derive from the checkout location, never a
hardcoded per-machine path."""

import os

from lib import config


def test_project_dir_is_derived_from_file_location():
    # TOOLS_DIR/PROJECT_DIR must be computed relative to config.py's own
    # location, so this works from any checkout path, not one developer's
    # machine. Confirmed by checking the actual relationship, not by
    # asserting a specific absolute string.
    assert config.TOOLS_DIR == os.path.dirname(os.path.dirname(os.path.abspath(config.__file__)))
    assert config.PROJECT_DIR == os.path.dirname(config.TOOLS_DIR)
    assert os.path.isdir(config.PROJECT_DIR)


def test_deck_paths_live_under_project_dir():
    for name, spec in config.DECKS.items():
        assert spec["pptx"].startswith(config.PROJECT_DIR), name
        assert spec["screenshots"].startswith(config.PROJECT_DIR), name
        assert spec["backups"].startswith(config.PROJECT_DIR), name


def test_no_hardcoded_personal_path_in_config_source():
    with open(config.__file__, encoding="utf-8") as fh:
        text = fh.read()
    assert "/Users/" not in text
