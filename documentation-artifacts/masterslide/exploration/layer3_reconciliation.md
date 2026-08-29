# Layer 3 — Cross-Specialist Reconciliation

Explicit reconciliation pass, not a concatenation of Layer 2's outputs. Each item below states
the conflict, the resolution (or explicit non-resolution), and what evidence justified it.

## 1. Pattern naming overlap: B1 vs. B2 vs. B3 (Procedural Hero Screenshot family)

**Conflict:** B2 (Secondary Panel) and B3 (Before/After) are both variations on B1, raising the
question of whether they should be merged into one pattern.

**Resolution: keep separate, but explicitly nested.** B1 is the base composition; B2 and B3 are
named variants distinguished by a real visual distinction, not a Layer 0 picture-count threshold
(Layer 0's `picture_count` field is materially higher than 1–2 for every confirmed instance of
all three patterns — see Layer 2-B1/B2/B3): B1 has one visually dominant screenshot, B2 adds a
visibly smaller adjacent dialog/panel screenshot, and B3's is a second full app-state screenshot
joined by a progression arrow. Merging them would lose real,
useful distinguishing information for future editing (the presence of a progression arrow
changes what "preserving the composition" means). Splitting them further would fragment one
family without new evidence.

## 2. Cluster ≠ visual family (the central reconciliation finding of this exploration)

**Conflict:** Layer 2-B and Layer 2-D each independently found that the confirmed Current-Style-
candidate grammar (B1/B2/B3) appears in BOTH structural cluster 3 and cluster 4, while cluster 1
produces at least one visually-plain instance of the same grammar despite a very different
structural signature (bound connectors).

**Resolution:** the 5 Layer-0 structural clusters and the visual-grammar families (B1–B7) are
**related but not equivalent classification systems**. Structural clusters group slides by
shape-type/connector/crop statistics; visual families group slides by actual rendered
composition. `connector_count == 0` is a bounded observation across the selected B1/B2/B3
examples — it holds in 7 of the 8 directly-confirmed instances (slide 34 is a directly-sampled
exception with `connector_count = 1` that is visually identical to the rest of the family). It
must NOT be treated as a hard classification/retrieval filter for these families: it is neither
proven necessary (slide 34 contradicts it) nor sufficient (most of cluster 3's 88 members share
`connector_count == 0` without independent visual confirmation of the grammar). No replacement
hard threshold is proposed — this remains an open classification question, not an approximation
to be resolved further with current evidence.

## 3. Contradictory representative-slide selection: cluster 1 (slide 34)

**Conflict:** Layer 2-B lists slide 34 as a B1 representative (by visual appearance); Layer 2-D
lists it as the sole representative of the "Bound-Connector, Visually Plain" family (by
structural signature).

**Resolution: KEPT UNRESOLVED, deliberately.** Both classifications are independently
evidence-supported and not mutually exclusive — slide 34 can be visually a clean B1 instance
AND structurally a member of a cluster whose defining connector signal has no visible
counterpart on this particular slide. The candidate Presentation Memory (below) lists slide 34
under both, with this note attached, rather than forcing a single assignment.

## 4. Current-style candidate vs. Relationship-Heavy family (B4/cluster 2) — genuine
## disagreement, not resolved

**Conflict:** Is B4 (the dense, real-connector, multi-target composition used for topics like
Export Messages and Reactions) part of the current editorial style for genuinely complex
multi-target actions, or a superseded convention?

**Resolution: KEPT UNRESOLVED.** No evidence collected this pass distinguishes these. B4 shares
Bridge Deck Identity elements with every other family and uses a real, deliberate visual
grammar (Section C) — it is not obviously "worse" or "older," only structurally and visually
distinct in how it handles slides that must reference multiple screen regions at once. This is
flagged explicitly for founder input (Layer 4-E) rather than silently classified either way.

## 5. Theme identity vs. layout style — confirmed, no conflict

Layer 2-A's separation of stable Bridge Deck Identity elements from variable Editorial Layout
Style held up against every other specialist's findings without contradiction — every visual
family (B1 through B6) shares the logo, header band, title convention, page numbering, and
red/gray color vocabulary. No reconciliation needed here.

## 6. Uncertain PDF↔PPT mappings

**Conflict/gap:** the PDF (147 pages) is shorter than the PPTX (170 slides); no fixed offset
exists. Because the mapping is not one-to-one, the raw page/slide count difference is not a valid
estimate of how many PPT slides lack a PDF counterpart — complete PPT↔PDF correspondence remains
unresolved.

**Resolution:** every PDF↔PPT pairing used anywhere in this exploration was established by
direct title-text matching, never by page-number arithmetic — recorded explicitly in Layer 1's
method note and consolidated in its canonical sampling ledger. Full correspondence is left as an
open item for a future, larger-budget pass (e.g. full PDF title extraction), not silently
assumed to be any particular set or count of slides.

## 7. Anomalous slides — cross-checked, not forced into patterns

- **Slide 74** (Message Actions): independently flagged as an outlier by Layer 0's statistics
  AND explained by prior-session deep OOXML evidence AND excluded from every visual family
  candidate list. All three lines of evidence agree — this is a resolved anomaly (a real,
  different composition), not an unresolved one.
- **Slide 142** (Change a Team Member's Role): flagged as a statistical outlier and directly
  visually confirmed (PDF p.141) as an ordinary B1 instance. Resolved: the outlier signal
  reflects incidental text density (the "Note:" paragraph), not a different visual family.
- **Slide 141** (Renew Pro License): flagged as a statistical outlier. A prior round of this
  exploration incorrectly claimed this slide was directly visually confirmed by PDF p.141 — that
  page's title actually matches slide 142, a different slide (see above and the canonical
  sampling ledger). Corrected: slide 141 remains **UNRESOLVED / structurally observed only**; no
  visual evidence has been collected for it.
- **Slide 34** (Users Directory): see item 3 above — deliberately left dual-classified.
- **The duplicate-topic divergence pairs** (Manually Manage Data Retention, Manually Delete
  Entire Room, Message Formatting, Clear Browser Cache, Moving & Converting a Channel,
  Notifications - General): retained as the single most important piece of evidence for the "no
  clean chronological boundary" finding, explicitly NOT reinterpreted as proof of editorial
  authorship or era — see Layer 1B for the caveat already attached to each.
- **Slide 169** (`Mobile:` title): retained as a recorded anomaly with a plausible but unproven
  benign explanation.

## 8. Provenance conflicts

No genuine provenance conflict arose this pass — every DETERMINISTIC-PPTX claim came from the
single integrated Layer 0 publication (`is_tree_valid() == True`, re-verified at the start of
this pass), and every VISUAL-PDF-INFERRED claim came from a page this session directly opened
and read, with the exact page number recorded. No claim in any Layer 1/2/3 document mixes these
without labeling which is which.

## Net effect on the Candidate Presentation Memory

- Current Editorial Style candidate (B1/B2/B3) proceeds to Layer 4 as CANDIDATE — FOUNDER
  UNCONFIRMED, explicitly noting its cluster-3/cluster-4 span and the cluster-1 contradiction.
- The Relationship-Heavy family (B4) is presented as a separate, evidenced pattern with an open
  question for the founder, not folded into or excluded from the current-style candidate.
- Cluster 1's true visual meaning, cluster 3's internal homogeneity, and cluster 0's internal
  split remain explicitly unresolved in the memory rather than papered over.
