# Provenance

How each entry in SKILL.md was measured, 2026-08-02, against
`Current update/Desktop/MASTER Complete Bridge4PS Desktop-Browser Feature Tutorials.pptx`
via `python-pptx`.

- **Title size/run-split**: slides 10, 28, 60, 90, 100, 120, 140, 145, 148,
  149. Title text extracted by matching the actual title shape (text
  starting `"Desktop:"`), not by grabbing the first text shape on the slide
  — an earlier blind pass caught itself picking up slide-number
  placeholders instead of real titles on several slides and was corrected.
- **Caption size vs. text length**: slides 12, 60, 100, 120, 140, 148, 149
  — run size paired with caption character count, specifically to test (and
  disprove) the add-in's claim that caption size "flexes" with sentence
  length.
- **Badge/box shape type + line width**: slides 12, 60, 100, 120, 140, 148,
  149 — distinguished by `auto_shape_type` (OVAL vs RECTANGLE), not just
  line color, to avoid conflating the two shape kinds.
- **Picture border**: slides 12, 148, 149.

The two UNVERIFIED claims in SKILL.md (inline icon captions, inset zoom
crops as deliberate convention) originated from the Claude PowerPoint
add-in's self-reported study inside a Claude Project, pasted in by the
user. One sibling claim from the same source — caption size flexing with
length — was checked this way and found false. Treat any further
add-in-reported claim the same way: measure it against real XML before
trusting it, regardless of how precise or confident it sounds.
