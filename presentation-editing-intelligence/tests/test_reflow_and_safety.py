"""Reflow planning and deterministic safety checks, against synthetic
scenes built directly as `LocalScene`/`Relationship` objects (no `.pptx`
needed - `scene.py`'s extraction is already covered separately)."""

from __future__ import annotations

from presentation_editing_intelligence.reflow import plan_reflow
from presentation_editing_intelligence.relationships import Relationship
from presentation_editing_intelligence.safety import check_edit
from presentation_editing_intelligence.scene import ConnectorEndpoints, Geometry, LocalScene, SceneShape


def _shape(index, shape_id, left, top, width, height, is_line=False, text=None):
    return SceneShape(
        shape_index=index, shape_id=shape_id, shape_type="TEXT_BOX (17)" if not is_line else "LINE (9)",
        name="s%d" % shape_id, geometry=Geometry(left, top, width, height), z_order=index,
        text=text, line_color_rgb=None, line_width_emu=None, fill_color_rgb=None,
        is_line_shape=is_line, is_freeform=False, group_shape_index=None, connector_endpoints=None,
    )


def _stacked_scene():
    """target (growable text) -> divider (anchored-to target, separates
    target/next) -> next entry, all horizontally overlapping - mirrors
    the real Pin/divider/Star chain's shape."""
    target = _shape(0, 100, left=0, top=0, width=1_000_000, height=500_000, text="Target")
    divider = _shape(1, 101, left=0, top=550_000, width=1_000_000, height=0, is_line=True)
    next_entry = _shape(2, 102, left=0, top=650_000, width=1_000_000, height=500_000, text="Next")
    scene = LocalScene(slide_index=0, target_shape_index=0, shapes=[target, divider, next_entry])
    relationships = [
        Relationship(source_shape_id=101, target_shape_id=100, relation_type="anchored-to",
                     confidence="HIGH", evidence="test fixture"),
        Relationship(source_shape_id=101, target_shape_id=100, relation_type="depends-on",
                     confidence="HIGH", evidence="test fixture"),
        Relationship(source_shape_id=101, target_shape_id=100, relation_type="separates",
                     confidence="HIGH", evidence="test fixture"),
        Relationship(source_shape_id=101, target_shape_id=102, relation_type="separates",
                     confidence="HIGH", evidence="test fixture"),
    ]
    return scene, relationships


def test_reflow_shifts_the_evidenced_dependent_chain_by_the_growth_delta():
    scene, relationships = _stacked_scene()
    target = scene.target
    grown = Geometry(target.geometry.left, target.geometry.top, target.geometry.width,
                      target.geometry.height + 100_000)

    plan = plan_reflow(scene, relationships, grown)

    assert plan.delta_height_emu == 100_000
    moved_ids = {m.shape_id for m in plan.moves}
    assert moved_ids == {101, 102}  # divider AND the next entry, in the evidenced chain
    for move in plan.moves:
        assert move.delta_top_emu == 100_000


def test_reflow_is_a_noop_when_geometry_is_unchanged():
    scene, relationships = _stacked_scene()
    plan = plan_reflow(scene, relationships, scene.target.geometry)
    assert plan.is_noop


def test_reflow_does_not_move_shapes_outside_the_evidenced_chain():
    target = _shape(0, 100, left=0, top=0, width=1_000_000, height=500_000, text="Target")
    unrelated = _shape(1, 200, left=5_000_000, top=5_000_000, width=1_000_000, height=500_000, text="Unrelated")
    scene = LocalScene(slide_index=0, target_shape_index=0, shapes=[target, unrelated])
    grown = Geometry(target.geometry.left, target.geometry.top, target.geometry.width,
                      target.geometry.height + 200_000)
    plan = plan_reflow(scene, [], grown)
    assert plan.moves == []  # no evidenced dependency -> nothing else moves


def test_safety_check_passes_for_a_correctly_reflowed_edit():
    scene, relationships = _stacked_scene()
    target = scene.target
    grown = Geometry(target.geometry.left, target.geometry.top, target.geometry.width,
                      target.geometry.height + 100_000)
    plan = plan_reflow(scene, relationships, grown)
    report = check_edit(scene, relationships, grown, plan,
                         slide_width_emu=10_000_000, slide_height_emu=10_000_000)
    assert report.ok
    assert report.critical == []


def test_safety_check_flags_collision_when_growth_is_not_reflowed():
    scene, relationships = _stacked_scene()
    target = scene.target
    grown = Geometry(target.geometry.left, target.geometry.top, target.geometry.width,
                      target.geometry.height + 400_000)  # would now overlap the divider/next entry

    from presentation_editing_intelligence.reflow import ReflowPlan
    no_reflow = ReflowPlan(moves=[], delta_height_emu=400_000, delta_width_emu=0)

    report = check_edit(scene, relationships, grown, no_reflow,
                         slide_width_emu=10_000_000, slide_height_emu=10_000_000)
    assert not report.ok
    assert any(i.check == "overlap" for i in report.critical)


def test_safety_check_flags_out_of_bounds():
    scene, relationships = _stacked_scene()
    target = scene.target
    huge = Geometry(target.geometry.left, target.geometry.top, target.geometry.width, 50_000_000)
    from presentation_editing_intelligence.reflow import ReflowPlan
    no_reflow = ReflowPlan(moves=[], delta_height_emu=huge.height - target.geometry.height, delta_width_emu=0)
    report = check_edit(scene, relationships, huge, no_reflow,
                         slide_width_emu=1_000_000, slide_height_emu=1_000_000)
    assert not report.ok
    assert any(i.check == "out_of_bounds" for i in report.critical)


def test_safety_check_flags_broken_points_to_when_only_one_side_moves():
    target = _shape(0, 100, left=0, top=0, width=1_000_000, height=500_000, text="Target")
    divider = _shape(1, 101, left=0, top=550_000, width=1_000_000, height=0, is_line=True)
    pointed_at = _shape(2, 300, left=5_000_000, top=550_000, width=500_000, height=500_000)
    scene = LocalScene(slide_index=0, target_shape_index=0, shapes=[target, divider, pointed_at])
    relationships = [
        Relationship(source_shape_id=101, target_shape_id=100, relation_type="depends-on",
                     confidence="HIGH", evidence="test"),
        # The divider also (per this fixture) points at a shape that is
        # NOT part of the reflow chain - if the divider moves but the
        # thing it points at does not, that pointer becomes misdirected.
        Relationship(source_shape_id=101, target_shape_id=300, relation_type="points-to",
                     confidence="HIGH", evidence="test"),
    ]
    grown = Geometry(target.geometry.left, target.geometry.top, target.geometry.width,
                      target.geometry.height + 100_000)
    plan = plan_reflow(scene, relationships, grown)
    assert 101 in {m.shape_id for m in plan.moves}
    assert 300 not in {m.shape_id for m in plan.moves}

    report = check_edit(scene, relationships, grown, plan,
                         slide_width_emu=10_000_000, slide_height_emu=10_000_000)
    assert not report.ok
    assert any(i.check == "relationship_target_displacement" for i in report.critical)


def test_estimate_line_count_flags_growth_when_text_lengthens():
    from presentation_editing_intelligence.safety import estimate_line_count
    geometry = Geometry(left=0, top=0, width=3_000_000, height=500_000)
    short = estimate_line_count("Short text.", geometry, font_size_pt=12)
    long = estimate_line_count("Short text." * 10, geometry, font_size_pt=12)
    assert long > short
