---
status: FOUNDER APPROVED
schema_version: "1.0.0-approved"
approved_from: candidate_presentation_memory.md §3 (schema_version "0.1.0-candidate")
approval_basis: layer4_founder_validation_packet.md, founder response recorded in this session
source_layer0_commit: f0b656769b7e209619ed13ed3385285a147504c6
source_layer0_hash_valid: true
source_pptx_sha256: e461613baae2874eaeede3268fff1aee081c33a04a6bcbb0c7769b94bab16834
---

# Founder-Approved Bridge4PS Editorial Style

**This document is the founder-approved successor to the Current Editorial Style candidate in
`candidate_presentation_memory.md` §3.** It is a distinct artifact, not an in-place mutation of
the candidate — the candidate document, its evidence, and its full audit/repair history
(Layers 1–4, `openspec/changes/presentation-exploration-layers-1-4/`) remain unchanged and
unresolved-uncertainty-intact. This document records only the decision and the two things the
founder explicitly approved. It does not re-derive, re-litigate, or duplicate the underlying
evidence.

## 1. Approved default Bridge4PS editorial grammar

Future Bridge4PS slide editing should prefer:

- clean numbered instructions at the top;
- concise instructional text with clear hierarchy;
- large contextual screenshots below;
- red highlights around only the exact actionable UI target;
- good whitespace and visual hierarchy;
- restrained use of arrows, connectors, pointers, and similar annotation objects.

This corresponds to the *Procedural Hero Screenshot* family (B1, with its *Secondary Panel* /
*Before-After* variants B2/B3) described in `candidate_presentation_memory.md` §3–4. This is now
the approved default editorial grammar.

## 2. Relationship-aware exception rule (equally part of the approval)

**"Restrained use of arrows/connectors" does NOT mean remove them whenever possible.**

Gray pointers, arrows, connectors, dividers, callouts, highlight relationships, and similar
visual elements remain part of the approved Bridge4PS visual grammar whenever they perform a
real instructional function. Examples include:

- exception conditions;
- dependencies;
- source → target relationships;
- before → after / state progression;
- explanatory callouts;
- associations between text and a screenshot region;
- relationships between multiple UI areas.

These purposeful elements must be preserved and intelligently maintained during future editing.
If an edit moves, resizes, or reflows the text, screenshot, or region a relationship element
relates to, future Presentation Editing Intelligence must understand and preserve that
relationship.

**Example conceptual relationship:** `gray pointer belongs-to note A and points-to screenshot
region B`. If A or B moves, the pointer should be repositioned/reflowed appropriately.

**It must NOT:**
- become crumpled;
- point to the wrong target;
- remain stranded at an old coordinate;
- be deleted simply because the default style is cleaner.

**Founder principle:** *Make the slide clean while preserving purposeful visual relationships
that explain the content.* Every visual element should continue to be treated as potentially
purposeful until evidence shows otherwise.

Both Section 1 (the default grammar) and Section 2 (the exception rule) constitute a single,
inseparable approval — the default grammar was not approved on its own, and must never be
represented as "avoid connectors" without this section.

## 3. What this approval does NOT resolve

Founder approval of the target editorial style does not resolve unrelated research
uncertainties. The following remain exactly as unresolved as they were in
`candidate_presentation_memory.md` (§3, §7) and `layer3_reconciliation.md`:

- exact PDF p.131 → PPT 132/133 occurrence (ambiguous);
- exact PDF p.133 → PPT 134/135 occurrence (ambiguous);
- slide 141 anomaly (UNRESOLVED / structurally observed only);
- historical cause of the duplicate-topic structural-divergence pairs;
- full PPT↔PDF correspondence (unresolved, not estimated);
- visual-family classification of every member of the large Baseline structural cluster (c3, 88
  slides — only 2 directly sampled).

This approval also does not resolve the open question in `candidate_presentation_memory.md` §3
of whether the Relationship-Heavy / Dense family (B4, cluster 2) is itself part of the approved
default grammar for complex multi-target actions, or a separate case — Section 2 above answers
the narrower, general question of when relationship elements are appropriate at all, but the
founder did not separately rule on B4's own status.

## 4. Next-phase requirement (not implemented by this document)

The next separately authorized phase is **Presentation Editing Intelligence / Scene-Aware
Editing**. Its key implementation requirement, established by this approval, is to preserve
semantic visual relationships during edits, including relationship types such as: belongs-to,
moves-with, points-to, highlights, separates, anchored-to, ordered-before/after, aligned-with,
repeated-with, contained-by, depends-on. **None of these relationships are implemented by this
document or by any work in this session.** Implementation requires separate founder/orchestrator
authorization to begin, per this repository's standard phase-gating convention.

## 5. Evidence trail (preserved, not duplicated)

Full supporting evidence, provenance, and the complete audit/repair history for this decision
remain in: `candidate_presentation_memory.md`, `layer4_founder_validation_packet.md`,
`layer1_range_evidence.md`, `layer1b_anomaly_audit.md`, `layer2_specialist_synthesis.md`,
`layer3_reconciliation.md`, and `openspec/changes/presentation-exploration-layers-1-4/
verification-report.md` (Codex Audit 1 FAIL → Build 2 → Codex Audit 2 FAIL → Build 3 → Codex
micro-audit → Fix 1/2/3). None of that history is erased, superseded, or restated here.
