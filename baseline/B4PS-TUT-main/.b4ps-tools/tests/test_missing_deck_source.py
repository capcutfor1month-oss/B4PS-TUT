"""Failure behavior: a missing/empty/corrupt deck source must fail clearly
with a specific exception, not a bare OS/zipfile traceback - covering both
the currently-missing production decks (an unresolved Git LFS pointer
limitation, not a bug) and generic filesystem edge cases via small synthetic
fixtures. No production PPTX content is fabricated anywhere here."""

import os
import zipfile

import pytest

from lib import config, deck as deck_io

FAKE_DECK = "FixtureDeck"


@pytest.fixture
def fake_deck(tmp_path, monkeypatch):
    """Register a throwaway deck pointing at tmp_path, restored after the test."""
    spec = {
        "pptx": str(tmp_path / "fixture.pptx"),
        "screenshots": str(tmp_path / "Screenshots"),
        "backups": str(tmp_path / "Backups"),
        "toc_range": (1, 1),
    }
    monkeypatch.setitem(config.DECKS, FAKE_DECK, spec)
    return spec


def _write_minimal_pptx_like_zip(path):
    """A tiny, valid zip archive - enough to prove filesystem/zip-open
    behavior, not a real presentation."""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")


def test_require_pptx_missing_file(fake_deck):
    with pytest.raises(config.MissingDeckSourceError, match="not found"):
        config.require_pptx(FAKE_DECK)


def test_require_pptx_empty_file(fake_deck):
    open(fake_deck["pptx"], "wb").close()
    with pytest.raises(config.MissingDeckSourceError, match="empty"):
        config.require_pptx(FAKE_DECK)


def test_require_pptx_present_file_returns_path(fake_deck):
    _write_minimal_pptx_like_zip(fake_deck["pptx"])
    assert config.require_pptx(FAKE_DECK) == fake_deck["pptx"]


def test_deck_reader_missing_source_raises_clear_error(fake_deck):
    with pytest.raises(config.MissingDeckSourceError):
        deck_io.DeckReader(FAKE_DECK)


def test_deck_reader_corrupt_zip_raises_clear_error(fake_deck):
    with open(fake_deck["pptx"], "wb") as fh:
        fh.write(b"not a zip file")
    with pytest.raises(config.MissingDeckSourceError, match="not a valid"):
        deck_io.DeckReader(FAKE_DECK)


def test_deck_reader_opens_present_fixture(fake_deck):
    _write_minimal_pptx_like_zip(fake_deck["pptx"])
    reader = deck_io.DeckReader(FAKE_DECK)
    try:
        assert reader.has("[Content_Types].xml")
    finally:
        reader.close()


def test_backup_missing_source_raises_clear_error(fake_deck):
    with pytest.raises(config.MissingDeckSourceError):
        deck_io.backup(FAKE_DECK)


def test_backup_copies_present_fixture(fake_deck):
    _write_minimal_pptx_like_zip(fake_deck["pptx"])
    dest = deck_io.backup(FAKE_DECK)
    assert os.path.isfile(dest)
