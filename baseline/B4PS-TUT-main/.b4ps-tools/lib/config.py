"""Paths, deck registry, and self-tuning confidence thresholds."""

import json
import os
import tempfile

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(TOOLS_DIR)

# Small and worth keeping: these live with the project so they survive sessions.
STATE_DIR = os.path.join(TOOLS_DIR, "state")
ANCHOR_DIR = os.path.join(STATE_DIR, "anchors")
REPORT_DIR = os.path.join(TOOLS_DIR, "reports")

# Bulky and disposable: `apply` stages one rewritten ~148MB .pptx here before
# copying it over the live file. Nothing is unpacked to disk any more (deck.py
# reads/writes the zip directly), but the staged copy is still sizeable, so it
# stays out of the project folder to avoid a needless OneDrive sync.
WORK_DIR = os.path.join(tempfile.gettempdir(), "b4ps-work")

CORRECTIONS_LOG = os.path.join(STATE_DIR, "corrections.jsonl")
THRESHOLDS_FILE = os.path.join(STATE_DIR, "thresholds.json")

# Each deck: where the .pptx lives, where its screenshots are dropped, and the
# slide range that the deck's own Table of Contents actually links to. Slides
# outside toc_range are out of scope (see PPT-UPDATE-WORKFLOW.md).
DECKS = {
    "Desktop": {
        "pptx": os.path.join(
            PROJECT_DIR, "Current update", "Desktop",
            "MASTER Complete Bridge4PS Desktop-Browser Feature Tutorials.pptx"),
        "screenshots": os.path.join(PROJECT_DIR, "Source", "Desktop", "Screenshots"),
        "backups": os.path.join(PROJECT_DIR, "Current update", "Desktop", "Backups"),
        "toc_range": (7, 149),
    },
    "Mobile": {
        "pptx": os.path.join(
            PROJECT_DIR, "Current update", "Mobile",
            "Copy of MASTER Complete Bridge4PS Mobile Feature Tutorials.pptx"),
        "screenshots": os.path.join(PROJECT_DIR, "Source", "Mobile", "Screenshots"),
        "backups": os.path.join(PROJECT_DIR, "Current update", "Mobile", "Backups"),
        "toc_range": (8, 164),
    },
}

BACKUP_KEEP = 3


class MissingDeckSourceError(Exception):
    """Raised instead of letting a bare zipfile/OS error surface when a
    deck's source .pptx is not present on disk (for example: not yet
    imported, or - as with this repository's own baseline import - present
    upstream only as an unresolved Git LFS pointer)."""


def require_pptx(deck_name):
    """Fail clearly, before any read/write attempt, if a deck's source file
    is missing or empty. Returns the verified path on success."""
    spec = DECKS[deck_name]
    path = spec["pptx"]
    if not os.path.exists(path):
        raise MissingDeckSourceError(
            "%s deck source not found: %s\n"
            "This file is not present in this checkout. If it was expected "
            "to come from an imported baseline, check docs/CURRENT.md for "
            "any documented Git LFS availability limitation before assuming "
            "this is a bug." % (deck_name, path))
    if os.path.getsize(path) == 0:
        raise MissingDeckSourceError(
            "%s deck source is empty (0 bytes): %s" % (deck_name, path))
    return path

# Starting bars. `tune` raises these when the corrections log shows a band that
# has been wrong too often; it never lowers them automatically.
DEFAULT_THRESHOLDS = {
    # template-match score (0-1) below which a box move is never auto-applied
    "min_match_score": 0.80,
    # max pixels the two independent methods may disagree by and still auto-apply
    "max_method_disagree_px": 6.0,
    # combined confidence needed to auto-apply without asking
    "auto_apply_confidence": 0.90,
    # image aspect ratio may differ from the frame by at most this fraction
    "max_aspect_drift": 0.01,
    # how many logged outcomes a confidence band needs before tuning trusts it
    "min_samples_to_tune": 12,
    # observed error rate in a band that forces the bar upward
    "tune_error_rate": 0.15,
}


def load_thresholds():
    values = dict(DEFAULT_THRESHOLDS)
    if os.path.exists(THRESHOLDS_FILE):
        with open(THRESHOLDS_FILE, encoding="utf-8") as fh:
            values.update(json.load(fh))
    return values


def save_thresholds(values):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(THRESHOLDS_FILE, "w", encoding="utf-8") as fh:
        json.dump(values, fh, indent=2)


def ensure_dirs():
    for path in (STATE_DIR, ANCHOR_DIR, REPORT_DIR, WORK_DIR):
        os.makedirs(path, exist_ok=True)
