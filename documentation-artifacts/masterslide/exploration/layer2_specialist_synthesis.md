# Layer 2 — Specialist Synthesis

Each specialist consumes only Layer 1's evidence (range evidence + anomaly audit), not the raw
170-slide deck.

---

## A. Bridge Deck Identity

Stable across every structural family and every directly-sampled visual page:

- **Logo/branding**: "BRIDGE4 Public Safety" wordmark, top-left, on every sampled page — though
  on 4 of the 10 sampled pages (35, 120, 141, 147) the wordmark is partially clipped/cropped by
  the page edge rather than fully visible; the element's presence, not its full legibility, is
  the consistent signal.
- **Header band**: light gray full-width band containing the title.
- **Title convention**: `Desktop: **Bold Feature Name**` — the `Desktop:` prefix in regular
  weight, the feature name in bold, centered. 163/170 slides (95.9%) extract this via the exact
  same header-region pattern (DETERMINISTIC-PPTX, `title_extraction_basis`). The 7 exceptions
  are the deck's own title page and 5 ToC pages (no `Desktop:` heading exists) plus one
  `Mobile:`-titled appendix slide — none contradict the convention, they are simply outside its
  scope.
- **Canvas**: white working area below the header band.
- **Page numbering**: bottom-right, confirmed on every directly-sampled page.
- **Color vocabulary**: red = interaction/attention/emphasis (numbered step badges, click-target
  outlines, connector lines where present); gray = progression/association (arrows between
  screenshots or from label to target); blue/teal = sub-topic heading color, seen specifically
  in the Reference/Concept Glossary pattern (slide 75/76).
- **Screenshot-centric identity**: every directly-sampled page uses at least one real, high-
  fidelity application screenshot as primary evidence — never a purely textual/diagrammatic
  slide outside the 5 ToC pages.

**Theme identity vs. editorial layout style — kept separate per instruction:** the above are
THEME IDENTITY (present in every family, including the relationship-heavy/dense cluster 2
pages and the reference-glossary page). What varies between families is EDITORIAL LAYOUT STYLE:
how many screenshots, whether connector lines are drawn, whether badges sit above one screenshot
or accompany a two-screenshot progression, and instruction density. Section B/C below cover
that variation; this section deliberately does not.

**Confidence: HIGH** (multiple independent visual confirmations across ranges + full structural
consistency across 163/170 slides for the title convention alone).

---

## B. Slide Pattern Library

Starting candidate set evaluated against actual evidence; none rejected outright, one added,
none merged (each remained visually and structurally distinguishable).

### B1. Procedural Hero Screenshot
- **Structural note**: `connector_count == 0` in every directly-confirmed instance of this
  pattern except slide 34, which is visually indistinguishable from B1 yet has
  `connector_count = 1` (see Counterexamples below) — this is a bounded observation across the
  sampled examples, not a hard classification rule; do not use `connector_count` as a retrieval
  filter for this family (see Layer 3 §2). Layer 0's actual `picture_count` field is materially
  higher than "one" for every confirmed instance (e.g. slide 121 = 4, slide 125 = 5, slide 142 =
  4 pictures total, including small chrome/icon elements) — the pattern is defined by which
  screenshot is visually dominant, not by a deterministic picture count.
- **Visual signature (VISUAL-PDF-INFERRED)**: numbered red badges in a horizontal row, concise
  bold-keyword instructions, one visually dominant contextual screenshot below.
- **Representative slides**: 121 (Create Team, PDF p.120), 125 (Add Users to Existing Team, PDF
  p.124), 142 (Change a Team Member's Role, PDF p.141 — corrected from a prior mapping error that
  named slide 141, whose own title is "Renew PRO License," a different slide not visually
  sampled this pass).
- **Counterexamples**: slide 34 (Users Directory) is structurally cluster 1 (`connector_count=1`,
  `bound_connector_count=1`) yet visually indistinguishable from this pattern — see Section F.
- **Confidence: HIGH.**

### B2. Procedural + Secondary Panel
- **Structural note**: same `connector_count == 0` bounded observation as B1. Not distinguished
  from B1 by a deterministic picture-count threshold — Layer 0 reports 4 pictures for slide 121,
  7 for slide 132, and 12 for slide 133, none of which is "two."
- **Visual signature (VISUAL-PDF-INFERRED)**: one visually dominant screenshot plus a visibly
  smaller adjacent dialog screenshot, both under the same numbered-badge row.
- **Representative slides**: 121 (Create Team dialog alongside main app); PDF p.131 (Invite via
  QR Code — main screenshot, exact occurrence ambiguous between slides 132/133) and PDF p.133
  (Adding and Removing Workspace Members — dialog-style panel, exact occurrence ambiguous between
  slides 134/135; corrected from a prior mapping error that claimed an exact match to slide 133 —
  see canonical sampling ledger). Both pairs are cluster-consistent (132/133 both c3, 134/135
  both c4), so the visual pattern is confirmed even though the exact slide is not.
- **Confidence: MEDIUM** (a real, repeated variant of B1 rather than a fully independent
  pattern — kept separate per instruction since the composition genuinely differs, reconciled
  further in Layer 3).

### B3. Before/After or Progression
- **Structural note**: a large gray freeform/arrow shape between two screenshots, per direct
  visual observation. Not distinguished from B1/B2 by a deterministic picture-count threshold
  (Layer 0 reports 5 pictures for slide 146, 3 for slide 148).
- **Visual signature (VISUAL-PDF-INFERRED)**: two side-by-side screenshots connected by one large
  gray arrow showing a state transition, each with its own numbered-badge instruction group
  above it.
- **Representative slides**: 146 (Manage Folder, PDF p.145), 148 (Export View, PDF p.147).
- **Confidence: HIGH** (2 independent, founder-flagged confirmations, visually consistent).

### B4. Relationship-Heavy Connector Grammar (renamed from generic "Annotated Interface Map" —
### the evidence supports a more specific name)
- **Structural signature**: cluster 2's centroid — high shape count (avg 52.6), elevated real
  connector usage, denser text.
- **Visual signature**: numbered badges bound to explicit right-angle red connector lines drawn
  directly across one or more screenshots, pointing at specific UI targets; intro paragraph;
  inline + footer "Note:" callouts.
- **Representative slides**: 29 (Export Messages, PDF p.30, directly VISUAL-PDF-INFERRED
  confirmed), 78 (Reactions — DETERMINISTIC-PPTX/OOXML confirmed real bound `stCxn` connector
  only; **not** visually sampled this pass, see canonical sampling ledger).
- **Confidence: HIGH** for slide 29 (direct visual confirmation); **MEDIUM** for slide 78's
  membership in this visual family (structural/OOXML evidence only, no direct visual
  confirmation that it renders the same composition).

### B5. Multi-Example Grid — **not independently confirmed this pass**
- No directly-sampled page matched this description cleanly. The closest candidate (Message
  Formatting, see B6) is better described as a glossary than a grid. Retained as an open
  candidate, not asserted.
- **Confidence: LOW / unconfirmed — do not treat as an established pattern yet.**

### B6. Reference/Concept Glossary (added this pass — not in the original candidate list, but
### directly evidenced)
- **Structural signature**: no numbered badges; multiple independent labeled sub-sections on one
  slide.
- **Visual signature**: bold colored sub-headings (e.g. `/giphy`, `/topic`, `/shrug`, `/hide`),
  each with a short paragraph and small annotated screenshot, connected by gray arrows from text
  to the relevant screenshot region.
- **Representative slides**: 75/76 (Message Formatting, PDF p.77).
- **Confidence: MEDIUM** (1 directly-sampled instance; structurally these land in different
  clusters (c3 and c0) despite an identical visual pattern — another case where cluster ≠
  visual family, consistent with the B1 finding).

### B7. Table of Contents / Nonprocedural
- **Structural signature**: cluster 4's most distinctive members; no `Desktop:` title, uses
  fallback title extraction.
- **Visual signature**: not directly visually sampled this pass (no PDF page was opened for
  slides 0–5) — structurally self-evident from title/layout data alone.
- **Confidence: MEDIUM** (structural evidence only, no direct visual confirmation this pass).

---

## C. Visual Grammar Specialist

Recurring semantics, evidenced (not inferred from color alone — each entry below is backed by
at least one directly-sampled page, and the structural correlate is noted where one exists):

| Element | Meaning | Structural correlate | Evidence |
|---|---|---|---|
| Red circle numbered badge | Sequential step marker | none specific (appears across clusters) | 9 of 10 sampled pages (absent from page 77, the Reference/Concept Glossary composition, which uses labeled sub-headings instead) |
| Red rectangle outline | Click-target attention on a screenshot | none specific | 124, 131, 133, 141, 145, 147 |
| Red right-angle connector **line** | Explicit binding from a step badge to a specific UI target across/within a screenshot | correlates with cluster 2 (dense) membership, but not with Layer 0's `bound_connector` flag specifically — see unresolved item in Section F | 29 (PDF p.30) |
| Gray arrow (large, between two screenshots) | State progression / before-after transition | visually two dominant screenshots (not a specific Layer 0 `picture_count` value — see B3) | 145, 147 |
| Gray arrow (small, label-to-screenshot-region) | Association from a reference-glossary label to its example | multi-textbox, no badges | 75/76 (PDF p.77) |
| Bold "Note:" prefix paragraph | Caveat, permission requirement, or scope clarification | slightly elevated text_length | PDF pages 30, 141, 124 |
| "Pro License Feature" footer label | Marks a feature as a paid-tier capability | none structural (a text convention only) | 120 (PDF p.141 removed — the page's title contains "(Pro Feature)" but no literal footer-label instance was confirmed there on inspection) |
| Blue/teal bold sub-heading | Sub-topic label within a reference/glossary composition | co-occurs with pattern B6 only | 75/76 |

**Do not over-generalize:** the red-connector-line vs. red-rectangle-outline distinction and the
two different gray-arrow meanings (progression vs. association) are both real, evidenced, and
NOT interchangeable — conflating them would misrepresent the grammar.

**Confidence: HIGH** for badge/outline/Pro-label meanings (repeated, unambiguous across samples);
**MEDIUM** for the two connector-line/arrow distinctions (each backed by real but fewer
independent samples).

---

## D. Historical Style Profiles

Presented as **structural/visual families**, not authorship or chronology claims, per
instruction.

### Family "Baseline / Simple Procedural" (≈ Layer 0 cluster 3, 88 slides, the deck majority)
- **Characteristics**: no real connector bindings, moderate crop usage, generally lower text
  density than cluster 2.
- **Representative slides**: 8, 68, 73, 20 (all statistical outliers within this large cluster,
  meaning the cluster itself is internally heterogeneous — see uncertainty below).
- **Relationship to other families**: this is the largest and least visually homogeneous
  cluster; the confirmed C1-grammar visual pattern (PDF p.131, exact occurrence ambiguous between
  slides 132/133, both cluster 3) and unconfirmed members coexist here. Treating "cluster 3" as
  one visual family would be an overreach the evidence does not support.
- **Evidence**: DETERMINISTIC-PPTX (full cluster membership); VISUAL-PDF-INFERRED only for the
  PDF p.131 composition (occurrence ambiguous, see canonical sampling ledger).
- **Uncertainty: HIGH regarding this cluster's internal visual homogeneity** — this is the
  single largest open question this exploration did not fully resolve (see Layer 3).

### Family "Low-Connector / Text-Forward" (≈ Layer 0 cluster 4, 36 slides)
- **Characteristics**: lowest crop rate (centroid 0.192), highest sp_rate (0.745) — text/shape-
  forward, includes all 5 ToC pages and the "Pro Feature" Teams-admin block.
- **Representative slides**: 121, 125, 142 — all 3 directly visually confirmed as clean C1
  Procedural Hero Screenshot instances.
- **Relationship to other families**: strongest visually-confirmed overlap with the candidate
  Current Editorial Style (Section E) — see Layer 3 for the reconciliation of "cluster 4 ≠
  exclusively current style" (cluster 3 members also confirmed C1).
- **Evidence**: DETERMINISTIC-PPTX (full) + 3 direct visual confirmations.
- **Uncertainty: LOW-MEDIUM.**

### Family "High-Crop Screenshot-Dense" (≈ Layer 0 cluster 0, 26 slides)
- **Characteristics**: highest crop rate (92.3%), low connector usage, concentrated in R5
  (16/26 members) and R3 (8/26).
- **Representative slides**: 74 (Message Actions — confirmed a Pin/Star definitions-list
  composition, NOT procedural), 158/163/167/168 (the late-deck retention/reaction/room-deletion
  re-coverage run).
- **Relationship to other families**: internally mixed — slide 74's composition is confirmed
  different from the late-R5 members. Not a single visual family; a structural grouping that
  spans at least two real visual compositions.
- **Evidence**: DETERMINISTIC-PPTX (full) + deep prior-session OOXML evidence on slide 74
  specifically.
- **Uncertainty: MEDIUM-HIGH** (structurally coherent, visually mixed).

### Family "Relationship-Heavy / Dense" (≈ Layer 0 cluster 2, 11 slides)
- **Characteristics**: highest shape count and text density of any cluster by a wide margin
  (avg 52.6 shapes vs. 17–28 for others).
- **Representative slides**: 29 (Export Messages, PDF p.30, directly VISUAL-PDF-INFERRED
  confirmed), 78 (Reactions — DETERMINISTIC-PPTX/OOXML confirmed real bound connector; not
  visually sampled this pass).
- **Relationship to other families**: the most visually distinctive and internally consistent
  family found this pass, based on its one directly visually confirmed member.
- **Evidence**: DETERMINISTIC-PPTX (full) + 1 direct visual confirmation (slide 29) + 1
  deterministic/OOXML-only confirmation (slide 78, the deck's cleanest confirmed real connector
  binding, but not visually observed).
- **Uncertainty: LOW** for slide 29's classification; **MEDIUM** for whether slide 78 renders the
  same visual composition (structural evidence only).

### Family "Bound-Connector, Visually Plain" (≈ Layer 0 cluster 1, 9 slides)
- **Characteristics**: highest formal `bound_connector` rate (96.3%) of any cluster, yet the one
  directly-sampled member (34, Users Directory) shows no visible connector line at all.
- **Representative slides**: 34 (visually plain, structurally bound), 99/167 (both statistical
  outliers within this small cluster).
- **Relationship to other families**: genuinely unresolved — see Section F and Layer 3. This is
  the clearest case in the whole exploration where a strong DETERMINISTIC-PPTX signal and the
  available VISUAL-PDF-INFERRED evidence point in different directions.
- **Evidence**: DETERMINISTIC-PPTX (full) + 1 direct visual sample (which complicated rather than
  confirmed the hypothesis).
- **Uncertainty: HIGH — explicitly unresolved, not forced to a conclusion.**

---

## E. Current Editorial Style — CANDIDATE — FOUNDER UNCONFIRMED

**Do not treat this as authoritative. Status remains CANDIDATE — FOUNDER UNCONFIRMED throughout
this document and every downstream artifact.**

**Candidate description:** the *Procedural Hero Screenshot* family (B1, with its *Secondary
Panel* and *Before/After* variants, B2/B3) — numbered red circle badges, concise bold-keyword
instructions above one or two large, high-fidelity contextual screenshots, restrained red
rectangle attention outlines (never dense connector-line overlays), generous whitespace,
occasional bold "Note:" caveat paragraphs, "Pro License Feature" footer label where relevant.

**Why this candidate appears strongest:**
- It is the **only** pattern independently confirmed across 8 of the 10 directly-sampled PDF
  pages: 6 map to an exact confirmed slide (121, 125, 142, 146, 148, 34) and 2 (PDF pages 131 and
  133) confirm the same visual pattern with the exact PPT occurrence left ambiguous between a
  same-title slide pair each — see the canonical sampling ledger for the exact accounting. This
  spans both range 4 and range 5 and both structural clusters 3 and 4 — i.e. it is not an
  artifact of any single structural cluster or deck region.
- All 7 of the founder's originally-flagged candidate PDF pages (120, 124, 131, 133, 141, 145,
  147) fall cleanly into this family by visual composition (with 145/147 as the confirmed
  Before/After variant); page 141 corresponds to slide 142, not slide 141 (corrected mapping).
- `connector_count == 0` holds for every exact-slide confirmation except slide 34
  (`connector_count = 1`, visually identical to the rest of the family) — a bounded observation,
  not a proven necessary or sufficient correlate (see Layer 3 §2). It also holds for all four
  candidate slides behind the two ambiguous pages (132, 133, 134, 135), so the correlate's
  applicability does not depend on resolving that ambiguity.

**Supporting evidence:** see Layer 1 R4/R5 and Layer 2-B1/B2/B3 above, and the canonical sampling
ledger in `layer1_range_evidence.md` — 8 directly-sampled PDF pages, 6 mapping to an exact slide
and 2 mapping ambiguously to a same-title slide pair each.

**Contradictory / complicating slides:**
- Slide 34 (Users Directory) is visually indistinguishable from this candidate family, yet is
  structurally cluster 1 with a 96% formal bound-connector rate — the deterministic correlate
  above is not universal.
- Slide 74 (Message Actions) and the late-R5 cluster-0 run show a *different* high-crop
  composition (Pin/Star-style / dense retention screens) that is NOT this candidate family, even
  though several of those slides are visually plausible as "reasonably current-looking" — they
  were not directly sampled this pass, so no claim is made about them either way.

**Unresolved uncertainties:** whether cluster 1's formally-bound-but-visually-plain slides
belong inside or outside this candidate (see Section F); whether the large, heterogeneous
cluster 3 contains further undiscovered current-style instances beyond the one confirmed via PDF
p.131 (exact occurrence ambiguous between 132/133)
given only a bounded visual sample was taken; whether the Relationship-Heavy family (B4/cluster
2) represents a genuinely different but still-current pattern for complex multi-target actions,
or an older convention being phased out — no evidence collected this pass distinguishes these.

---

## F. Anomaly / Unresolved Specialist

Collected here explicitly so nothing below is silently encoded as a rule:

1. **Cluster 1's true visual meaning is unresolved.** A 96%-bound-connector structural signature
   produced a visually plain page in the one instance sampled. Do not assume "bound connector"
   implies "visible connector line" anywhere in this deck without direct visual confirmation.
2. **Cluster 3's internal visual homogeneity is unconfirmed.** It is the deck's largest cluster
   (88 slides) and the least directly visually sampled relative to its size (2/88 confirmed).
   Any future work should not assume cluster 3 is visually uniform.
3. **Cluster 0's two known compositions (Message-Actions-style definitions list vs. the late-R5
   retention/reaction run) may or may not be the same visual family** — not independently
   visually confirmed against each other this pass.
4. **The 99/100/101 Notifications 3-way cluster split** and the **Clear Browser Cache (13/14)**
   and **Moving & Converting a Channel (127/128)** duplicate-topic pairs are recorded as
   duplicate-topic divergence evidence but NOT interpreted as editorial-era signals — they may
   simply reflect legitimately different sub-panel complexity within one multi-slide topic.
5. **Complete PPT↔PDF correspondence remains unresolved.** The PDF (147 pages) is shorter than
   the PPTX (170 slides) but the mapping is not one-to-one, so the raw count difference is not a
   valid estimate of unmapped slides; this exploration did not attempt to establish full
   correspondence.
6. **Slide 169's `Mobile:` title** is recorded as a real anomaly (see Layer 1B) with a plausible
   benign explanation, not resolved to a definite cause.
7. **Multi-Example Grid (B5)** remains an unconfirmed candidate pattern from the original list —
   not rejected, not evidenced either.

None of the above should be encoded as a rule in the Candidate Presentation Memory below without
this caveat attached.
