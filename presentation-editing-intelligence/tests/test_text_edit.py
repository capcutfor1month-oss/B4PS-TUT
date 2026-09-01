"""Unit tests for the pure-Python formatting-preserving diff planner.
No `.pptx` file involved anywhere in this file."""

from __future__ import annotations

from presentation_editing_intelligence.text_edit import RunSpan, plan_single_run_replacement


def test_append_at_end_targets_only_the_last_run():
    runs = [
        RunSpan(0, 0, "Pin:"),
        RunSpan(1, 0, "Messages bookmarked "),
        RunSpan(1, 1, "for all members"),
        RunSpan(1, 2, " of the channel to view in the Pinned Messages list."),
    ]
    old = "Pin:\nMessages bookmarked for all members of the channel to view in the Pinned Messages list."
    new = old + " (approved test update)"
    plan = plan_single_run_replacement(runs, old, new)
    assert plan.status == "resolved"
    assert len(plan.edits) == 1
    edit = plan.edits[0]
    assert (edit.paragraph_index, edit.run_index) == (1, 2)
    assert edit.new_text == " of the channel to view in the Pinned Messages list. (approved test update)"


def test_prepend_at_start_targets_only_the_first_run():
    runs = [RunSpan(0, 0, "World")]
    plan = plan_single_run_replacement(runs, "World", "Hello World")
    assert plan.status == "resolved"
    assert plan.edits[0].new_text == "Hello World"


def test_substitution_wholly_inside_one_run_is_resolved():
    runs = [RunSpan(0, 0, "The quick brown fox")]
    plan = plan_single_run_replacement(runs, "The quick brown fox", "The slow brown fox")
    assert plan.status == "resolved"
    assert plan.edits[0].new_text == "The slow brown fox"


def test_multi_run_preservation_only_touches_the_changed_run():
    # Bold "Pin:" and the underlined-bold middle run must never be
    # touched by an edit confined to the trailing plain run.
    runs = [RunSpan(0, 0, "Pin:"), RunSpan(1, 0, "A"), RunSpan(1, 1, "B"), RunSpan(1, 2, "C")]
    old = "Pin:\nABC"
    plan = plan_single_run_replacement(runs, old, "Pin:\nABCD")
    assert plan.status == "resolved"
    assert len(plan.edits) == 1
    assert plan.edits[0].paragraph_index == 1
    assert plan.edits[0].run_index == 2
    assert plan.edits[0].new_text == "CD"


def test_change_spanning_two_runs_is_unresolved_not_guessed():
    runs = [RunSpan(0, 0, "Hello "), RunSpan(0, 1, "World")]
    plan = plan_single_run_replacement(runs, "Hello World", "Hi There")
    assert plan.status == "unresolved"
    assert "run" in plan.reason
    assert plan.edits == []


def test_stale_expected_old_text_is_unresolved():
    runs = [RunSpan(0, 0, "current text")]
    plan = plan_single_run_replacement(runs, "stale assumed text", "new text")
    assert plan.status == "unresolved"
    assert "changed since" in plan.reason


def test_no_textual_change_is_unresolved():
    runs = [RunSpan(0, 0, "same")]
    plan = plan_single_run_replacement(runs, "same", "same")
    assert plan.status == "unresolved"


def test_empty_runs_is_unresolved():
    plan = plan_single_run_replacement([], "", "new")
    assert plan.status == "unresolved"


def test_new_paragraph_insertion_is_unresolved_not_fabricated():
    # Inserting a whole new paragraph in the middle can't be localized
    # to one existing run - it would require inventing new paragraph
    # structure, which this module refuses to guess at.
    runs = [RunSpan(0, 0, "First"), RunSpan(1, 0, "Second")]
    old = "First\nSecond"
    new = "First\nInserted\nSecond"
    plan = plan_single_run_replacement(runs, old, new)
    assert plan.status == "unresolved"
