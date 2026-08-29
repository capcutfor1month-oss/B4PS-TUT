# Layer 1 — Range Evidence

**Status: evidence collection only. No deck-wide era or Current Style declared here.**
**Scope: 170/170 canonical PPTX slides (slide_index 0–169), full DETERMINISTIC-PPTX coverage.**

## Provenance and method

- **DETERMINISTIC-PPTX** evidence for every slide comes directly from the integrated Layer 0
  publication (`documentation-artifacts/masterslide/layer0/tier_a_summary.json`,
  `structural_analysis.json`), re-verified `is_tree_valid() == True` before this pass began.
  The 5 structural clusters and their member lists are Layer 0's own output, reused here, not
  recomputed.
- **VISUAL-PDF-INFERRED** evidence comes from direct visual inspection of specific pages of
  the canonical `documentation-artifacts/masterslide/updated/Masterslides.pdf` (147 pages),
  performed this session. Exactly 10 pages were directly opened and visually read: the 7
  founder-flagged candidate pages (120, 124, 131, 133, 141, 145, 147) plus 3 pages sampled to
  cross-check structural clusters 1, 2, and the reference/glossary pattern (35, 30, 77
  respectively). This is a **bounded, representative sample of 10 pages**, not full 147-page
  coverage — see the Coverage/Provenance Audit in the final response, and the canonical sampling
  ledger immediately below, for the exact accounting.
- PDF page number and PPT slide index are **not** a fixed arithmetic offset — confirmed
  empirically. Every PDF↔PPT pairing below was established by **title-text matching** via
  `tier_a_summary.json`, not by position — see the canonical sampling ledger for the exact
  page→slide mapping used everywhere downstream. The PDF has 147 pages against the PPTX's 170
  slides; because the mapping is not one-to-one, **complete PPT↔PDF correspondence remains
  unresolved** — no numeric estimate of unmapped slides is made (see Layer 1B).
- No OfficeCLI rendering was used anywhere in this pass.

## Canonical sampling ledger

The single authoritative record of every PDF page directly opened this pass. All other
exploration documents (Layer 1B, Layer 2, Layer 3, the Candidate Presentation Memory, the
Founder Packet) must cite this ledger rather than repeating their own page/slide counts.

| PDF page | Visible title/topic | PPT candidate slide(s) | Mapping confidence | Mapping basis | Provenance | Observed pattern/finding | Used in |
|---|---|---|---|---|---|---|---|
| 120 | Create Team (Pro Feature) | 121 | HIGH | title unique to this slide (no repeated occurrence) | VISUAL-PDF-INFERRED | B1 Procedural Hero Screenshot | R4, Layer 2-B1/E, Layer 4-B |
| 124 | Add Users to Existing Team (Pro Feature) | 125 | HIGH | title unique to this slide | VISUAL-PDF-INFERRED | B1 Procedural Hero Screenshot | R4, Layer 2-B1/D, Layer 4 |
| 131 | Invite Members Using a QR Code | **132 / 133 (ambiguous)** | **AMBIGUOUS / MEDIUM** | title/topic ("Invite Members Using a QR Code") occurs on both slide 132 and slide 133; title match alone does not distinguish which occurrence this page corresponds to — no independent evidence (e.g. distinguishing screenshot content) was collected this pass to resolve it | VISUAL-PDF-INFERRED | B1/B2 composition (main screenshot or dialog panel — occurrence not distinguished) | R4, Layer 2-B2/E |
| 133 | Adding and Removing Workspace Members | **134 / 135 (ambiguous)** | **AMBIGUOUS / MEDIUM** | title/topic ("Adding and Removing Workspace Members") occurs on both slide 134 and slide 135; title match alone does not distinguish which occurrence — corrected from a prior, invalid exact mapping to slide 133 (slide 133's actual topic is "Invite Members Using a QR Code", not this one) | VISUAL-PDF-INFERRED | B1/B2 composition (occurrence not distinguished) | R4, Layer 2-B2/E |
| 141 | Change a Team Member's Role (Pro Feature) | 142 | HIGH | title unique to this slide — corrected from a prior, invalid mapping to slide 141 (slide 141's actual topic is "Renew PRO License", a different slide) | VISUAL-PDF-INFERRED | B1 Procedural Hero Screenshot | R5, Layer 2-B1 |
| 145 | Manage Folder | 146 | HIGH | title unique to this slide | VISUAL-PDF-INFERRED | B3 Before/After progression | R5, Layer 2-B3 |
| 147 | Export View - Download Export (Pro Feature) | 148 | HIGH | title unique to this slide | VISUAL-PDF-INFERRED | B3 Before/After progression | R5, Layer 2-B3 |
| 35 | Users Directory | 34 | HIGH | title unique to this slide | VISUAL-PDF-INFERRED | Visually plain B1-style page; contradicts cluster 1's bound-connector signature (slide 34 has `connector_count=1`, `bound_connector_count=1`) | R1, Layer 2-B1/D/F, Layer 3 §3 |
| 30 | Export Messages - Retain Data by Date Range (Pro Feature) | 29 | HIGH | title unique to this slide — direct visual confirmation is restricted to slide 29 only; slide 30 (a different topic, "Retention - Retain Individual Posts") was **not** visually sampled and must not be described as confirmed | VISUAL-PDF-INFERRED | B4 Relationship-Heavy Connector Grammar | R0, Layer 2-B4/D |
| 77 | Message Formatting (glossary of `/`-commands) | 75, 76 (spanning) | MEDIUM | both slides share topic_key "message formatting" (different clusters); the one glossary page's content plausibly spans both adjacent same-topic slides rather than picking one occurrence — not the same single-slide ambiguity as 131/133, since the composition itself covers material attributable to both | VISUAL-PDF-INFERRED | B6 Reference/Concept Glossary — no numbered badges present | R3, Layer 2-B6 |

**Not visually sampled, cited elsewhere only as DETERMINISTIC-PPTX/OOXML evidence:** slide 74
(prior-session deep OOXML evidence, not this pass's PDF sample) and slide 78 (formally bound
`stCxn` connector confirmed from OOXML, no PDF page opened for it this pass — do not describe
slide 78 as a direct visual confirmation).

**Count (corrected):** 10 PDF pages directly inspected; some map ambiguously to repeated-title
PPT occurrences. 7 pages map to a single exact PPT slide each (121, 125, 142, 146, 148, 34, 29).
1 page (77) evidences a composition spanning two adjacent same-topic slides (75, 76). 2 pages
(131, 133) map **ambiguously** to two same-title candidate slides each (132/133 and 134/135
respectively) — title matching alone does not distinguish the exact occurrence, and no
additional distinguishing evidence was collected this pass. Do not describe 131 or 133 as an
exact one-to-one PPT slide confirmation, and do not count each ambiguous page as two
independently visually confirmed slides.

## Range plan

Adopted directly from Layer 0's own adaptive range proposal
(`structural_analysis.json.range_proposal`), which already applies the seam-merge and
minimum-range-size logic — no arbitrary re-splitting was applied. All 6 ranges are 18–36 slides
(within/near the 15–30 target), and every accepted seam is a genuine structural-fingerprint
discontinuity, not a fixed-N cut.

| Range | Slides | Count | Seam evidence |
|---|---|---|---|
| R0 | 0–28 | 29 | deck start / seam at 29 |
| R1 | 29–46 | 18 | seam at 29 → 47 |
| R2 | 47–66 | 20 | seam at 47 → 67 |
| R3 | 67–98 | 32 | seam at 67 → 99 |
| R4 | 99–133 | 35 | seam at 99 → 134 |
| R5 | 134–169 | 36 | seam at 134 → deck end |

Modest overlap for reconciliation: adjacent-range boundary slides (e.g. 27–31, 65–69, 96–101,
132–136) were cross-checked against both neighbors below where a duplicate-topic or cluster
transition was found near a seam.

---

## R0 (slides 0–28, n=29)

**Cluster mix:** c4=8 (ToC/title/reference), c3=15 (baseline no-connector), c2=4 (dense/connector),
c1=2 (bound-connector).

**Content:** Deck opener (slide 0 title page, slides 1–5 Table of Contents), then core
channel/room lifecycle actions (Archive, Join-Search, Auto Join, Change Roles, Create New
Channel, Hide/Leave Room, Favorite, Group by Folders) and early admin topics (Retention,
Notifications Preferences, Add/Remove Users).

**Structural pattern:** Mostly cluster 3 (no real connector bindings, moderate crop). A cluster-2
sub-pocket (13, 17, 25, 27) covers retention/cache/notification-preference topics — denser,
multi-panel.

**Visual/editorial pattern (VISUAL-PDF-INFERRED, slide 29 sampled at PDF p.30):** the c2 member
just past this range's boundary (slide 29, "Export Messages") shows the clearest visually
confirmed pattern in this whole deck: numbered red badges bound to real right-angle red
connector lines running across two side-by-side screenshots, plus a gray progression arrow
between them, an intro paragraph, and both inline and page-footer "Note:" callouts. This is
**DETERMINISTIC-PPTX cluster 2 = a genuine, visually distinct "relationship-heavy connector"
family**, not merely a statistical artifact.

**Screenshot treatment:** predominantly single-screenshot-per-slide in c3/c4 members; c2 members
use 2+ coordinated screenshots.

**Candidate layout family:** c3/c4 members trend toward *Procedural Hero Screenshot*; c2 members
toward *Relationship-Heavy Connector Grammar* (see Layer 2-C).

**Representative slides:** 8 (Auto Join Channels, c3, also a statistical outlier — see 1B), 15
(Create New Channel, c4), 29 (Export Messages, c2, PDF p.30 visually confirmed).

**Anomalous/outlier in range:** slide 8 (0.468 outlier distance, c3) — flagged for Layer 1B.

**Uncertainty:** slides 1–5 (ToC) intentionally structurally distinct (non-procedural), correctly
isolated in cluster 4 — not an anomaly, expected.

**Provenance:** DETERMINISTIC-PPTX (full), VISUAL-PDF-INFERRED (1 slide, boundary sample).
**Confidence:** structural — HIGH; visual-family attribution for the c2 pocket — MEDIUM (one
directly-sampled instance, pattern is internally consistent with cluster fingerprint).

---

## R1 (slides 29–46, n=18)

**Cluster mix:** c2=4 (retention/room-actions, continues from R0's seam), c3=11, c1=2, c4=1.

**Content:** Continues Pro-feature retention/export topics (29–32, shared with the R0 seam),
then Users Directory, User Status, Video Call, file/threads views, and a run of
display-preference toggles (Hide Username/Avatars, Display Condensed/Extended, Collapse
Embedded Media, Auto Load Images) — a genuinely repetitive settings-toggle sub-sequence.

**Structural pattern:** c2 pocket at the range start is the same real seam as R0's — reconciled
as one contiguous relationship-heavy pocket spanning the R0/R1 boundary (slides 25–32), not two
separate events.

**Visual/editorial pattern (VISUAL-PDF-INFERRED, slide 34 sampled at PDF p.35):** "Users
Directory" (cluster 1, bound_rate 96% at the cluster level) renders as a **plain** C1-style page
— numbered badges, one screenshot, a body paragraph below — with **no visually obvious
connector line**. This is a real, notable finding: cluster 1's defining structural signal (a
formally bound `stCxn`/`endCxn` connector) does not correspond to an obviously visible red
pointer line in this instance. Flagged as unresolved in Layer 2-F / Layer 3.

**Repeated toggle sub-sequence (40–45):** six consecutive slides sharing an identical
minimal-instruction, single-screenshot toggle-setting composition — a strong within-range
repeated pattern, candidate for its own minor pattern variant ("Toggle Setting" — a lightweight
sub-type of Procedural Hero Screenshot with a single step, not multiple numbered steps).

**Representative slides:** 29–32 (Export/Retention/Room Actions, c2), 34 (Users Directory, c1,
PDF p.35 visually confirmed), 40–45 (toggle-setting run).

**Anomalous/outlier in range:** none in this range's own top-20 list, though 25/27/17 (technically
range-0-adjacent) are outliers — see 1B.

**Provenance:** DETERMINISTIC-PPTX (full), VISUAL-PDF-INFERRED (1 slide).
**Confidence:** structural — HIGH; cluster-1 visual-grammar attribution — LOW (contradicts the
"bound connector = visible line" assumption; genuinely unresolved).

---

## R2 (slides 47–66, n=20)

**Cluster mix:** c3=16 (dominant), c4=1, c0=2, c1=1.

**Content:** Continuation of preference/settings toggles (Room Name, Sort by Activity, Mark
Unread, Keyboard Shortcuts, Group by Type), then User Settings (59), Bridge4PS Channel Types
(60), and message-handling actions (Add Reminder, Audio Messages, Copy Content, Delete File/
Posts), ending at Discussions (66, cluster 1).

**Structural pattern:** almost entirely cluster 3 — the least structurally distinctive range in
the deck. Two cluster-0 members appear here (59, 60) — the first appearance of the high-crop
(92%), no-connector family in slide-index order, though — per R5 below — cluster 0 recurs much
more heavily late in the deck. This is itself evidence against a clean chronological boundary:
cluster 0 is not confined to "early" or "late."

**Visual/editorial pattern:** no additional PDF page was sampled specifically for this range
(budget-bounded); structural signature (c3-dominant, low connector/crop) is consistent with the
toggle-setting/simple-procedural pattern already visually confirmed in R1's 40–45 run.

**Representative slides:** 59 (User Settings, c0), 66 (Discussions, c1).

**Anomalous/outlier in range:** none in top-20.

**Provenance:** DETERMINISTIC-PPTX (full). No direct visual sample this range.
**Confidence:** structural — HIGH; visual-family attribution — LOW/inferred-by-analogy only.

---

## R3 (slides 67–98, n=32)

**Cluster mix:** c3=21, c0=8, c2=2, c4=1.

**Content:** Message-object actions (Discussions, Download Files, Edit Message, Copy Link, Read
Receipts, Mentions), the Message Actions/Message Formatting/Reactions cluster (74–78, already
deeply structurally profiled in earlier session research — see below), then the Slash Commands
family (81–89) and a long run of small message-composition toggles (90–98).

**Deep-evidence cross-check (carried forward from prior-session OOXML work on this exact
deck, re-verified consistent with the current Layer 0 publication):**
- Slide 74 ("Message Actions", cluster 0, **also a statistical outlier**, dist 0.386): 8
  `cxnSp` connector shapes, all genuinely **unbound** (confirmed against raw XML in an earlier
  pass — zero `stCxn`/`endCxn` anywhere on this slide), 8 freeform paths, 3 groups. Visually this
  slide is known (from the earlier Presentation Scene Understanding research this project
  already completed) to be a **Pin/Star-style definitions list**, not a numbered-procedure
  layout — structurally and visually distinct from the C1 procedural grammar. This explains why
  it is both cluster-0-classified *and* a statistical outlier within that cluster: it shares
  cluster 0's high-crop signature but not its (assumed) typical composition.
- Slide 78 ("Reactions", cluster 2): 2 connectors, **1 formally bound** (`stCxn id="2551"
  idx="3"`, confirmed against raw XML), the deck's cleanest confirmed real connector binding.

**Visual/editorial pattern:** slides 75/76 ("Message Formatting", duplicate topic, DIFFERENT
clusters — c3 then c0) sampled at PDF p.77 (title-matched to this topic): the PDF page is a
**Reference/Concept glossary layout** — colored bold sub-headings (`/giphy`, `/topic`, `/shrug`,
`/hide`) each with a short paragraph and a small annotated screenshot, connected by **gray
arrows** pointing from text to the relevant screenshot region. This is visually and functionally
distinct from both the plain procedural grammar and the R0/R1 red-connector grammar — a third,
genuinely separate visual family, candidate-named **Annotated Reference Glossary**.

**Representative slides:** 74 (Message Actions — anomaly + deep prior evidence), 78 (Reactions —
cleanest confirmed bound connector), 75/76 (Message Formatting, PDF p.77, Reference Glossary
pattern).

**Anomalous/outlier in range:** 73 (Mentions, dist 0.488, the single highest outlier in the
entire deck), 8 is range-0 but conceptually related; 68 (Download Files, dist 0.391), 74
(Message Actions, dist 0.386).

**Provenance:** DETERMINISTIC-PPTX (full) + prior-session deep OOXML evidence (HIGH confidence,
re-verifiable against the same unchanged canonical source) + VISUAL-PDF-INFERRED (1 page, title-
matched).
**Confidence:** HIGH on slides 74/78 specifically (deep cross-checked evidence); MEDIUM elsewhere
in range.

---

## R4 (slides 99–133, n=35)

**Cluster mix:** c3=21, c4=10, c1=3, c2=1.

**Content:** Notifications sub-panel sequence (99–104, spans 3 clusters — see below), workspace/
navigation features (105–119), the "Pro Feature" Teams admin block (120–125, all cluster 4),
Channels/Search/QR-invite features (126–132).

**Duplicate-topic structural divergence within this range:** "Notifications - General" (Layer 0
`topic_key`) appears at slides 99 (cluster 1), 100 (cluster 2), **and 101** (cluster 4) — three
adjacent slides covering one settings screen's sub-panels, each landing in a **different**
structural cluster. Slide 102 ("Offline Email Notifications") is a genuinely distinct topic, not
part of this divergence. This most likely reflects genuinely different sub-panel complexity (a
legitimate structural difference) rather than an editorial-era signal, but is recorded here
rather than silently resolved.

**Visual/editorial pattern (VISUAL-PDF-INFERRED — see the canonical sampling ledger above for the
exact page→slide mapping and confidence of each):** this range contains PDF pages 120, 124, 131,
and 133, all in the founder-flagged candidate set. Two map to an exact single slide (121 at PDF
p.120, 125 at PDF p.124); two map only ambiguously to a same-title pair of slides (PDF p.131 →
132 or 133; PDF p.133 → 134 or 135 — title matching alone does not distinguish the occurrence,
see the ledger). All 4 pages show clean, consistent C1 Procedural Hero Screenshot compositions:
red numbered badges in a row, concise bold-keyword instructions, one or two large contextual
screenshots below, restrained red rectangle highlight around only the exact clicked element, no
connector lines, "Pro License Feature" footer label where relevant. Slides 121 and 125 are
**cluster 4**; both candidate slides for PDF p.131 (132, 133) are **cluster 3**, and both
candidate slides for PDF p.133 (134, 135) are **cluster 4** — the cluster assignment happens to
be identical for both candidates in each ambiguous pair, so the cluster-spanning finding below
holds regardless of which exact occurrence each page corresponds to. This is the strongest direct
evidence in this pass that the confirmed C1 visual grammar is **not** a single Layer-0 cluster —
it appears across both cluster 3 and cluster 4 members. `connector_count == 0` holds for every
slide in this range's C1-family evidence, but is not asserted as a deck-wide rule (slide 34 in R1
above is a directly-sampled counterexample within the same visual family).

**Representative slides:** 121, 125 (exact, directly visually confirmed C1 grammar); PDF p.131
and PDF p.133 (visual pattern confirmed, exact PPT occurrence among 132/133 and 134/135
respectively left ambiguous — present the PDF page confidently as a founder-facing example
without asserting the exact slide).

**Anomalous/outlier in range:** 99, 100 (Notifications, see above), 137 is range-5-adjacent.

**Provenance:** DETERMINISTIC-PPTX (full) + VISUAL-PDF-INFERRED (4 PDF pages inspected; 2 map to
an exact slide, 2 map ambiguously to a same-title slide pair — see ledger).
**Confidence:** HIGH for the C1-grammar finding in this range (multiple independent confirmations,
including both members of each ambiguous pair sharing one cluster).

---

## R5 (slides 134–169, n=36)

**Cluster mix:** c4=15, c0=16, c3=4, c1=1.

**Content:** Continues the "Pro Feature"/workspace-admin block (134–148, mostly cluster 4),
then Two-Factor Authentication (149, 151), then a dense run of cluster-0 topics re-covering
EARLIER subject matter under a different structural signature (153–168): Livestream Setup, QR
Code Generator, Quote, Custom Room Retention Policy, Add Reaction, Manually Delete Entire Room,
Manually Manage Data Retention, and the deck's final pair (168/169, Desktop/Mobile "Manually
Edit/Delete Individual Posts").

**Duplicate-topic structural divergence — the strongest evidence in the deck against a
chronological era boundary:**
- "Manually Manage Data Retention": slide 25 (cluster 2, range 0, early) vs. slide 163 (cluster
  0, range 5, late) — the SAME topic, structurally different families, at opposite ends of the
  deck.
- "Manually Delete Entire Room": slide 159 (cluster 0) vs. slide 167 (cluster 1, also a
  statistical outlier, dist 0.430) — both late in the deck, but still structurally distinct from
  each other.

This directly confirms the founder's prior instruction: there is no clean "new editor starts at
slide X" boundary, and structurally-older-looking and structurally-newer-looking treatments of
the *same* topic coexist without regard to slide position.

**Visual/editorial pattern (VISUAL-PDF-INFERRED, slide 142 at PDF p.141, slide 146 at PDF p.145,
slide 148 at PDF p.147 — all founder-flagged candidates):** **Correction: PDF page 141's title is
"Change a Team Member's Role (Pro Feature)", which matches slide 142, not slide 141 ("Renew PRO
License") — a prior mapping error is fixed here.** Slide 142 (cluster 4) matches the plain C1
grammar with an added bold "Note:" caveat paragraph. Slide 141 itself has **not** been directly
visually sampled this pass — see the anomaly note below. Slides 146/148 ("Manage Folder", "Export
View - Download Export") both use the **Before/After or Progression** pattern — two side-by-side
screenshots connected by one large gray arrow, each under its own numbered-badge instruction
group. This is a confirmed, distinct sub-pattern of the current-looking family, not a one-off.

**Slide 141 anomaly status (corrected):** slide 141 ("Renew PRO License") was a Layer 0
statistical outlier (dist 0.330, see Layer 1B). It was previously described as directly visually
explained by PDF p.141 — that claim is invalid, since PDF p.141 actually corresponds to slide
142, a different slide. Slide 141 returns to **UNRESOLVED / structurally observed only**; no
direct visual evidence supports or contradicts the outlier signal for this slide this pass.

**Deck-ending anomaly:** slide 169 ("Mobile: Manually Edit/Delete Individual Posts") is the only
`Mobile:`-titled slide in this Desktop deck, and the only slide whose title basis is
`header_region_fallback` for a reason other than being a Table of Contents page. Structurally
unremarkable (cluster 0, consistent with its Desktop-titled sibling at 168). Read as an
intentional cross-reference/bonus appendix slide rather than a misfiled or defective slide — see
Layer 1B.

**Representative slides:** 142, 146, 148 (all founder-flagged, directly confirmed), 163/167
(duplicate-topic divergence evidence). Slide 141 is **not** a representative slide this pass
(no direct visual evidence — see anomaly note above).

**Anomalous/outlier in range:** 167 (statistical outlier), 137, 142 (weak outliers), 141
(statistical outlier, **UNRESOLVED / structurally observed only** — see anomaly note above), 169
(title-convention anomaly, not a statistical outlier).

**Provenance:** DETERMINISTIC-PPTX (full) + VISUAL-PDF-INFERRED (3 PDF pages inspected, all
founder-flagged candidates, each mapping to a single exact slide — 142, 146, 148).
**Confidence:** HIGH for the Before/After sub-pattern and the duplicate-topic divergence finding.

---

## Coverage statement

All 170/170 slides have DETERMINISTIC-PPTX (Tier A) coverage — no gaps. 10 PDF pages were
directly opened this pass (7 founder-flagged + 3 sampled for cluster cross-checks). 7 pages map
to a single exact PPT slide (121, 125, 142, 146, 148, 34, 29); 1 page (77) evidences a composition
spanning two adjacent same-topic slides (75, 76); 2 pages (131, 133) map ambiguously to a
same-title slide pair each (132/133, 134/135) and are not counted as exact confirmations — see
the canonical sampling ledger above for the full accounting. The remaining slides' visual-family
attribution is by structural-cluster analogy only (labelled LOW/MEDIUM confidence throughout,
never asserted as directly confirmed). This is a deliberate token-efficiency/scope tradeoff, not
an oversight — see the Coverage/Provenance Audit section of the final response.
