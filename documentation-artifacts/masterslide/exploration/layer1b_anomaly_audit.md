# Layer 1B — Anomaly / Outlier Auditor

Independent pass after range evidence. Sources: Layer 0's own statistical outlier list
(`structural_analysis.json.structural_clusters.outliers_top20`, distance-from-own-centroid,
DETERMINISTIC-PPTX/statistical provenance) plus manual cross-checks this session (duplicate-topic
divergence, title-convention anomalies). No outlier is forced into a pattern.

## Statistical structural outliers (top 20, Layer 0-computed)

| Slide | Topic | Cluster | Distance | Note |
|---|---|---|---|---|
| 73 | Mentions | 3 | 0.488 | highest in deck; not independently visually sampled this pass |
| 8 | Auto Join Channels | 3 | 0.468 | not independently visually sampled |
| 99 | Notifications - General | 1 | 0.455 | part of the 99/100/101 duplicate-topic 3-way cluster split (see R4) |
| 32 | Room Actions – Expanded | 2 | 0.449 | within the confirmed relationship-heavy pocket (R0/R1 seam) |
| 25 | Manually Manage Data Retention | 2 | 0.435 | one side of the strongest duplicate-topic divergence pair (vs. 163) |
| 27 | Notifications Preferences | 2 | 0.431 | within the R0/R1 seam pocket |
| 100 | Notifications - General | 2 | 0.431 | see 99 above |
| 167 | Manually Delete Entire Room | 1 | 0.430 | one side of a second duplicate-topic divergence pair (vs. 159) |
| 17 | Custom Channel-Room Retention Policy | 2 | 0.397 | within the R0/R1 seam pocket |
| 158 | Add Reaction | 0 | 0.393 | distinct from "Reactions" (78, cluster 2) — legitimately different sub-topic |
| 68 | Download Files | 3 | 0.391 | not independently visually sampled |
| 74 | Message Actions | 0 | 0.386 | **directly explained** — see below |
| 78 | Reactions | 2 | 0.385 | directly visually/structurally confirmed (real bound connector) |
| 31 | Room Actions – Basic | 2 | 0.369 | R0/R1 seam pocket |
| 10 | Channel Search Commands | 4 | 0.350 | not independently visually sampled |
| 137 | Requesting/Managing Access to Workspace Channel | 4 | 0.341 | not independently visually sampled |
| 163 | Manually Manage Data Retention | 0 | 0.333 | other side of the retention divergence pair (vs. 25) |
| 142 | Change a Team Member's Role (Pro) | 4 | 0.333 | **directly visually confirmed** (PDF p.141) — plain C1 grammar, no visible anomaly; the statistical distance likely reflects the added "Note:" callout paragraph, not a distinct visual family |
| 20 | Group by Folders | 3 | 0.332 | not independently visually sampled |
| 141 | Renew Pro License | 4 | 0.330 | not independently visually sampled — **UNRESOLVED / structurally observed only** (a prior mapping of PDF p.141 to this slide was incorrect; p.141 actually corresponds to slide 142, see below) |

## Directly explained outliers

**Slide 74 (Message Actions, cluster 0, dist 0.386).** Cross-checked against prior-session deep
OOXML evidence on this exact slide (unchanged since — same canonical source hash): 8 unbound
freeform connector-shaped elements, 3 groups, known (from earlier Presentation Scene
Understanding research on this project) to render as a **Pin/Star-style definitions list**, not
a numbered-procedure composition. It shares cluster 0's high-crop-rate signature (screenshots
present) but not the rest of that cluster's typical shape — genuinely a different composition
sharing one structural feature. This is a real, resolved anomaly, not noise.

**Slide 142 (Change a Team Member's Role, cluster 4, dist 0.333).** Directly visually confirmed
at PDF p.141 (title-matched — "Change a Team Member's Role (Pro Feature)" — not slide 141, whose
own title is "Renew PRO License"; a prior mapping error naming slide 141 here is corrected) as a
completely ordinary, clean instance of the plain procedural grammar with an extra bold "Note:"
callout paragraph. Recorded as explained, not defective.

**Slide 141 (Renew Pro License, cluster 4, dist 0.330) — corrected to UNRESOLVED.** Previously
described as directly visually confirmed at PDF p.141; that was a mapping error — PDF p.141's
title matches slide 142, a different slide, not slide 141. No PDF page has been directly sampled
for slide 141 this pass. Its statistical outlier status returns to **UNRESOLVED / structurally
observed only**; no visual evidence supports or contradicts a distinct-family explanation for it.

## Duplicate-topic structural divergence (found this pass, not in Layer 0's own outlier list —
## these are same-topic pairs landing in different clusters, the clearest available evidence
## against a clean chronological era boundary)

| Topic | Occurrence A | Occurrence B | Reading |
|---|---|---|---|
| Manually Manage Data Retention | slide 25, cluster 2 | slide 163, cluster 0 | same topic, opposite ends of deck, different families — no boundary explains this by position |
| Manually Delete Entire Room | slide 159, cluster 0 | slide 167, cluster 1 | both late in deck, still structurally distinct from each other |
| Message Formatting | slide 75, cluster 3 | slide 76, cluster 0 | adjacent slides, same topic, different clusters |
| Clear Browser Cache | slide 13, cluster 2 | slide 14, cluster 3 | adjacent slides, same topic, different clusters |
| Notifications - General | slide 99 (c1) | slide 100 (c2) | plus slide 101, same topic_key, also lands in a third cluster (c4) — a genuine 3-way split; slide 102 ("Offline Email Notifications") is a separate topic and not part of this divergence. Most plausibly reflects genuinely different sub-panel complexity per slide, not an editorial signal — recorded, not resolved |
| Moving & Converting a Channel to Workspace | slide 127 (c3) | slide 128 (c4) | adjacent slides, same topic, different clusters |

**Do not treat any of these as proof of chronological editing order.** They are exactly the kind
of evidence the founder asked this exploration to surface: legacy-looking and current-looking
treatments of the same subject coexisting without a clean position-based boundary. Some pairs
(e.g. Clear Browser Cache, Message Formatting) may simply be a multi-slide sequence where one
slide is denser than its sibling for legitimate content reasons rather than an editorial-era
signal — this ambiguity is preserved, not resolved, per Layer 3.

## Title-convention anomaly

**Slide 169 ("Mobile: Manually Edit/Delete Individual Posts").** The only `Mobile:`-titled slide
in this Desktop deck; the only slide whose title-extraction basis is `header_region_fallback`
for a reason other than being one of the 5 Table-of-Contents pages (0–5 use `title_placeholder`/
`header_region_fallback` because they have no `Desktop:` heading at all). Structurally
unremarkable (cluster 0, matching its immediate Desktop-titled sibling at slide 168). Read as an
intentional cross-reference/appendix slide, not a misfiled or defective one — but recorded as an
anomaly per instruction, not silently normalized.

## Hybrid/special-layout candidates

No slide in this deck contains a table, chart, SmartArt, or other unsupported structure (Layer 0
confirmed 0 unsupported structures deck-wide, re-verified this pass). No hidden shapes exist
anywhere in the deck. The Table of Contents pages (0–5) are the only slides with a fundamentally
non-procedural composition, and they are already correctly isolated in cluster 4 rather than
appearing as false outliers.

## PDF↔PPT topic-matching uncertainty

Confirmed this pass: the PDF (147 pages) is materially shorter than the PPTX (170 slides), and
page↔slide correspondence is not a fixed offset (see Layer 1 method note). Because the mapping is
not one-to-one, the raw page/slide count difference (170 − 147) is **not** a valid estimate of
how many PPT slides lack a PDF counterpart — some PDF pages may correspond to zero PPT slides,
multiple PDF pages may correspond to one PPT slide, or vice versa. **Complete PPT↔PDF
correspondence remains unresolved.** No systematic attempt was made this pass to establish it —
that would require either full 147-page PDF title extraction or a much larger sampling budget
than this bounded pass used.
