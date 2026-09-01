"""Presentation Editing Intelligence / Scene-Aware Editing - Slice 1.

The smallest generalizable pilot proving: correct content edit +
formatting preservation + local relationship preservation + layout
maintenance, on one real Bridge4PS slide. See
`openspec/changes/presentation-editing-intelligence-slice-1/spec.md` for
the governed scope this package implements.

Public entry point: `pilot.apply_scene_aware_edit`.
"""

from .pilot import PilotResult, apply_scene_aware_edit

__all__ = ["PilotResult", "apply_scene_aware_edit"]
