# Editorial Memory — Implementation Audit

> **Design audit + founder-approved amendments. Still design only.** Nothing in this document has been built — no schema code, no repository structure, no implementation.

## Document layers

This document has grown in two passes, kept explicitly separate so nothing gets silently rewritten:

| Layer | What it is | Where |
|---|---|---|
| **Original audit** | The initial design audit — reasoning, tradeoffs, why 3 entities and not 6. Unmodified below. | §1–§13 |
| **Founder amendments** | Six refinements approved after the original audit shipped, each layered onto a specific part of the original design via an inline `[Amendment N]` marker. | §14 (full log), inline markers in §2.2, §3, §7 |
| **Final implementation contract** | The single merged, unambiguous spec — original + amendments together — that an implementation should actually be built against. | §17 |

**If anything below reads as if it conflicts between layers, §17 governs.** (It doesn't, in practice — see the Amendment Log's conflict check in §14.1.)

## TL;DR

| | |
|---|---|
| **Question** | What's the *smallest* Editorial Memory that's still living, evolving, version-aware, provenance-preserving, and history-preserving — per the locked founder clarification? |
| **Answer** | 3 record types. No ontology. No database. Plain files. |
| **Verdict** | ✅ **BUILD** |

**The 3 record types:**

```
KnowledgeItem   →  a claim that evolves over time (product / documentation / editorial)
Evidence        →  a pointer to a source (screenshot, recording, doc, browser check, maintainer note)
Annotation      →  a freeform note attached to either — never authoritative on its own
```

**The one rule that matters most:** a claim only becomes `current` when a maintainer approves it. New evidence can *propose* an update, even contradict what's on record — it can never silently overwrite it.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Recommended Data Model](#2-recommended-data-model)
3. [Evidence Hierarchy](#3-evidence-hierarchy)
4. [Provenance Model](#4-provenance-model)
5. [Evolution Model](#5-evolution-model)
6. [Verification Model](#6-verification-model)
7. [Retrieval Model](#7-retrieval-model)
8. [Efficiency Strategy](#8-efficiency-strategy)
9. [Repository Structure](#9-repository-structure)
10. [Bootstrap Strategy](#10-bootstrap-strategy)
11. [Failure Modes](#11-failure-modes)
12. [Acceptance Criteria](#12-acceptance-criteria)
13. [Final Recommendation](#13-final-recommendation)

**Founder amendments (added after the original audit):**

14. [Amendment Log](#14-amendment-log)
15. [Invalidation & Purge Model](#15-invalidation--purge-model)
16. [Phase 3 Boundary (Accepted Scope)](#16-phase-3-boundary-accepted-scope)
17. [Final Implementation Contract](#17-final-implementation-contract)
18. [Implementation Slices (Plan Only)](#18-implementation-slices-plan-only)

---

## 1. Executive Summary

Editorial Memory needs to do exactly three things:

1. **Hold claims** about the product and its documentation, each trusted at a different level depending on who or what said it, and when.
2. **Never destroy a claim when a newer one shows up.** New evidence confirms, refines, contradicts, or supersedes it — it never overwrites in place.
3. **Let Documentation Intelligence ask "what's true right now?"** without having to read everything that was *ever* true.

Everything beyond that — a full ontology, a taxonomy, a query language, a database — is scope the locked clarification doesn't ask for. This audit doesn't recommend building it yet.

That's it — three entities carry the whole design:

| Entity | What it is |
|---|---|
| `KnowledgeItem` | A stable claim with its own append-only version history. A `knowledge_type` field (`product` / `documentation` / `editorial`) keeps the three claim categories separate without needing three schemas. |
| `Evidence` | An immutable pointer to a source observation. Never itself "knowledge" — it's what a `KnowledgeItem` version cites as its grounding. |
| `Annotation` | Freeform commentary attached to either of the above. Never gates status, never becomes "current" on its own. |

"History" isn't a fourth entity — it's just a property of `KnowledgeItem`: its version list only ever grows, never gets edited or deleted.

This is buildable now. It needs no live Bridge4PS access, and it gives Documentation Intelligence a stable surface to query against later.

---

## 2. Recommended Data Model

### 2.1 Why 3 entities, not 6

The brief lists six things that must stay distinct: product knowledge, documentation knowledge, editorial knowledge, annotation knowledge, evidence, and history. Read literally as "six schemas," that's an ontology — exactly what the brief says not to build. Read as "six *concepts* that must stay independently queryable," three entities cover it:

| The brief's concept | How it stays distinct here |
|---|---|
| Product knowledge | `KnowledgeItem` where `knowledge_type = product` |
| Documentation knowledge | `KnowledgeItem` where `knowledge_type = documentation` |
| Editorial knowledge | `KnowledgeItem` where `knowledge_type = editorial` |
| Annotation knowledge | `Annotation` — separate entity, never auto-promotes to a claim |
| Evidence | `Evidence` — separate entity, cited by reference, never embedded |
| History | The append-only `states` list every `KnowledgeItem` carries |

A discriminator field isn't "merging" — it's the smallest structure that still lets each category be filtered, retrieved, and trusted independently.

### 2.2 The schemas

```yaml
KnowledgeItem:
  id: string                    # e.g. "km-desktop.filters-sidebar-location"
  knowledge_type: product | documentation | editorial
  feature_area: string          # e.g. "desktop.filters" — dot-delimited convention, [Amendment 4]
  states: [KnowledgeState]      # append-only, oldest → newest, never edited after creation

KnowledgeState:
  version: integer              # 1, 2, 3... per KnowledgeItem
  content: string                # a sentence or two — never a document dump
  status: proposed | current | superseded | contradicted | deprecated | invalidated   # invalidated added by [Amendment 5]
  relation_to_previous: new | confirms | refines | contradicts | supersedes | null
  evidence_refs: [Evidence.id]
  source_trust_tier: 1-6         # derived from evidence_refs — see §3
  approved_by: string | null     # null while status = proposed
  approved_at: datetime | null
  created_at: datetime
  superseded_by: integer | null  # version that replaced this one, if any
  rationale: string | null       # [Amendment 3] optional — the human "why" behind this claim
  # --- fields below only ever set when status = invalidated, [Amendment 5] ---
  invalidated_by: string | null
  invalidated_at: datetime | null
  invalidation_reason: string | null

Evidence:
  id: string
  evidence_type: maintainer_decision | browser_observation | existing_documentation
               | screenshot | recording
  captured_at: datetime
  captured_by: string
  source_ref: string             # path/URL to the raw artifact — never inlined
  notes: string | null
  verification_scope: [visual | workflow | behavior | role-specific       # [Amendment 2]
                       | permission-specific | terminology
                       | documentation-only | editorial] | null           # recommended, not enforced — see §3

Annotation:
  id: string
  target_id: KnowledgeItem.id | Evidence.id
  target_type: knowledge_item | evidence
  author: string
  created_at: datetime
  text: string                   # freeform, non-authoritative
```

That's the whole model for day-to-day operation. No relationship table, no tagging taxonomy, no separate "fact" vs. "claim" vs. "assertion" hierarchy. `feature_area` is a plain string using a `<platform>.<feature>` naming convention (e.g. `desktop.filters`, `mobile.members`) adopted from day one, but it is still just a string, not a controlled vocabulary or registry — see §14's Amendment 4. If naming drifts over time, that's a maintainer cleanup task, not a schema problem.

A fourth, narrow structure — a **tombstone** — exists only for the rare hard-purge path (§15, Amendment 6). It is not part of the 3-entity model above and is never used in normal evolution.

### 2.3 Deliberately left out

- **No graph between `KnowledgeItem`s** (e.g. "this depends on that"). If it's ever needed, that's new scope requiring its own founder decision.
- **No numeric confidence score** beyond the founder's six-tier evidence hierarchy. Inventing one would be structure the brief never asked for.
- **No full-text search.** `feature_area` + `knowledge_type` is the only retrieval key for now (§7).

---

## 3. Evidence Hierarchy

This audit doesn't change the founder-specified hierarchy — it just maps each tier onto the record model:

| # | Evidence type | Trust | Auto-promotes to `current`? |
|---|---|---|---|
| 1 | Maintainer Decisions | Highest | ✅ Yes — the decision *is* the approval. |
| 2 | Browser Verification | Highest | ❌ No. Evidence, not memory — always lands `proposed`, needs a maintainer to promote it (§6). |
| 3 | Existing Documentation | Historical | ❌ No. Describes what was *written*, not what's true today — lands `proposed` (§10). |
| 4 | Screenshots | Visual only | ❌ No, unless corroborated — see below. |
| 5 | Screen Recordings | Workflow/sequence only | ❌ No, unless corroborated — see below. |
| 6 | Future Human Corrections | Highest (same as #1) | ✅ Yes — same mechanism as #1, whenever it arrives. |

### What screenshots and recordings actually prove

| Artifact | Proves | Doesn't prove |
|---|---|---|
| **Screenshot** | Visual layout & appearance at a moment in time | Interactive behavior, permission gating, workflow order, whether every user role can reach that state |
| **Recording** | Observed sequence, timing, state transitions | That the same access applies to other roles; that the path shown is the *only* path; the business rules behind what's shown |

**In practice:** if a claim is about *permissions* or *workflow generality* and its only evidence is a screenshot or recording, it stays `proposed`. If a claim is about *pure appearance* (e.g. "the sidebar icon is currently a funnel glyph"), a screenshot alone is enough to promote it — that's exactly what a screenshot proves. Drawing that line is a human judgment call at review time, not something the schema enforces mechanically (enforcing it would mean inventing a claim-type taxonomy the brief doesn't ask for).

**`[Amendment 2]`** — this judgment call now has a small, named vocabulary instead of living only in a maintainer's head: `Evidence.verification_scope`, a short list drawn from `visual | workflow | behavior | role-specific | permission-specific | terminology | documentation-only | editorial`. A screenshot's evidence record would typically carry `[visual]`; a recording, `[workflow]`. It's set at evidence-capture time (by whoever produces the evidence), recommended but not mechanically enforced — same as before, this is a review aid, not a gate the code checks automatically. It does **not** become a seventh entity or a controlled taxonomy: it's one small enum field on the one `Evidence` record that already exists.

---

## 4. Provenance Model

Every `KnowledgeState` answers all six required provenance questions from its own fields — no joins, no lookups elsewhere:

| Question | Answered by |
|---|---|
| Where did this come from? | `evidence_refs` → `Evidence.source_ref` |
| When? | `created_at` (state) + `Evidence.captured_at` (source) |
| Which source? | `Evidence.evidence_type` |
| Who approved it? | `approved_by` (`null` until approved) |
| Is it current? | `status == current` |
| Has it been superseded? | `status == superseded`, with `superseded_by` pointing at what replaced it |

Provenance isn't a separate record to keep in sync — it's baked into every state at the moment it's created, so nothing can drift.

---

## 5. Evolution Model

Bridge4PS changes every 2–3 months. The evolution rule is the same regardless of how much time passes between updates:

```
new evidence arrives
        │
        ▼
new KnowledgeState created under the SAME KnowledgeItem.id
        │
        ▼
   relation_to_previous is set:

   confirms     → new evidence agrees. New version recorded (freshness signal), content unchanged.
   refines      → new evidence adds detail without conflicting.
   contradicts  → new evidence conflicts. Lands as status=contradicted, NOT current.
                  The existing `current` state is untouched until a maintainer resolves it.
   supersedes   → a maintainer has resolved a contradiction, or the product genuinely moved on.
                  Old state → status=superseded, superseded_by=<new version>.
                  New state → status=current.
```

**Nothing is ever deleted.** A `superseded` or `contradicted` state stays in the `states` list forever — history isn't a log you dig up in an emergency, it's just always there.

This makes "latest approved knowledge" a cheap query: for any `KnowledgeItem`, there's exactly zero or one state with `status = current` at a time (enforced by convention here, not a database constraint — there is no database). Everything else in `states` is retrievable history, just not returned by default.

**`[Amendments 5 & 6]`** — this section describes *product evolution*: a claim that was genuinely true and later stopped being true. Two narrower situations sit outside this flow entirely and are covered in §15: a claim that was **never trustworthy** (`invalidated` — hallucination, bad ingestion, injected content) is not a `supersede`, and content that must be **struck from the record entirely** (secrets, PII, legally-required deletion) is not an append at all. Neither weakens "nothing is ever deleted" for genuine product history — they're separate, narrower paths for content that was never valid history in the first place.

---

## 6. Verification Model

Live Bridge4PS access currently exists only on the maintainer's machine. This section designs the integration point — without making it a requirement for the first build.

**The integration point:** `Evidence.evidence_type = browser_observation`, filled in by whoever/whatever checks the live product:

```yaml
evidence_type: browser_observation
captured_at: <timestamp>
captured_by: <maintainer or agent identity>
source_ref: <url observed, + a screenshot path if one was taken>
notes: <what was checked and what was seen>
```

Once that record exists, it flows through the exact same pipeline as any other evidence type: it can ground a new `proposed` `KnowledgeState`, and it needs maintainer promotion to become `current` (§3). The founder's rule — *"browser verification is evidence, not memory"* — is enforced by that approval gate, not by special-casing this evidence type.

**Why it's safe to defer:** nothing in the record model, the repo structure, or bootstrap (§10) depends on browser verification existing yet. The evidence type and promotion rule are defined now; the actual producer — a manual template today, maybe a browser-automation agent later — is separate work that can land whenever live access is actually used.

---

## 7. Retrieval Model

Documentation Intelligence needs a small, fixed set of queries — not a general query language:

| Query | What it returns | When it's used |
|---|---|---|
| `get_current(feature_area, knowledge_type=None)` | The `current` state(s) for a feature area | The default, common-path lookup: "what do we currently know about X?" |
| `get_history(knowledge_item_id)` | The ordered `states` list, **excluding `invalidated`** — `[Amendment 5]` | Audit, understanding why a claim changed, explaining provenance to a human. Superseded and contradicted states are included and clearly labeled by `status`; invalidated ones are not, since they were never valid history (see §15). |
| `get_by_type(knowledge_type, feature_area=None)` | Current items filtered to one category | Deliberately asking for only editorial judgment, or only product facts |
| `get_evidence(knowledge_item_id, version=None)` | The `Evidence` backing a state | Checking a claim against its source rather than trusting it at face value |
| `get_pending(feature_area=None)` | `proposed` + `contradicted` states | The maintainer's review queue |
| `get_invalidated(feature_area=None)` | `invalidated` states — `[Amendment 5]`, new query | Deliberate audit/review access to rejected knowledge. Never called by Documentation Intelligence's normal retrieval path. |

All six are plain lookups by `feature_area` / `knowledge_type` / id — no fuzzy search, no ranking, no embeddings. That's deliberately the smallest surface that gives Documentation Intelligence a stable contract to build against. A semantic-search layer on top is a reasonable future enhancement, but it's new scope, not part of the minimum.

**`[Amendment 5]` retrieval exclusion rule, stated once for clarity:** `proposed` and `contradicted` states are excluded from `get_current` (they're not approved) but remain visible via `get_history`/`get_pending`. `invalidated` states are excluded from **every** normal-path query (`get_current`, `get_history`, `get_by_type`) — they only surface via the dedicated `get_invalidated`. Purged content isn't a retrieval-time exclusion at all; it's simply gone (or replaced by a tombstone, see §15) before any query runs against it.

---

## 8. Efficiency Strategy

Token cost is a first-class requirement. The model is built around **extract once → store small → retrieve narrow**:

- **Extraction happens once, at ingestion.** A PPT, script, screenshot, or recording is parsed exactly once into `KnowledgeItem` proposals plus an `Evidence` pointer. Nothing in the retrieval path re-parses raw source.
- **`content` is short by design** — a sentence or two, never a document excerpt. The raw artifact stays referenced (`source_ref`), never inlined.
- **Retrieval returns only what was asked for.** `get_current(feature_area)` returns just the small `current` states for that area — not full history, not evidence content, not neighboring areas. Those are separate calls, fetched only when actually needed.
- **A flat index avoids full scans.** A single small index file maps `feature_area → item ids`, so a lookup never has to open every `KnowledgeItem` file to find what's relevant (§9).
- **No LLM in the retrieval path itself.** Plain structured lookup, no embedding-based search — unnecessary complexity and cost at this scale.

---

## 9. Repository Structure

Editorial Memory is neither raw baseline content nor a governance record — it's a new, durable data layer, so it gets its own top-level directory:

```
editorial-memory/
  SCHEMA.md                    # the 3 record types, documented (mirrors §2)
  index.yaml                   # feature_area → [KnowledgeItem.id, ...]
  knowledge/
    <feature-area>/
      <item-slug>.yaml         # one file per KnowledgeItem — states list lives inline, append-only
  evidence/
    screenshots/
    recordings/
    browser-observations/
    doc-excerpts/
  annotations/
    <target-id>.yaml           # one file per Annotation
```

**Why this shape:**

- **Plain text, git-diffable, no database.** Consistent with how the rest of this repository already works. A `KnowledgeItem`'s append-only version history is naturally visible both in the file's own append-only list *and* in git history — redundant, auditable, for free.
- **`feature_area`-keyed directories** keep related knowledge physically together, useful for a human skimming the tree — even though retrieval itself goes through `index.yaml`, not directory listing.
- **Evidence lives separately from knowledge**, mirroring the schema — a screenshot isn't a claim, and separating them makes that visible at the filesystem level too.
- **No location for Documentation Intelligence yet** — out of scope here; that's the next milestone, not this one.

**`[Amendment 4]`** — `knowledge/<feature-area>/` directories use the `<platform>.<feature>` naming convention from day one: `desktop.filters`, `desktop.members`, `desktop.channels`, `mobile.filters`, `mobile.members`, etc. This is guidance for consistency, not a registry to maintain or validate against — the taxonomy is expected to emerge from real data as features get ingested, not be modeled upfront.

**`[Amendment 6]`** — a hard purge (§15) is a manual maintenance operation on this same tree: it deletes or replaces the specific file(s) affected, optionally leaving a tombstone stub in place. It doesn't add a new directory or change this structure.

---

## 10. Bootstrap Strategy

The first Editorial Memory dataset comes entirely from evidence that already exists — no live Bridge4PS access required:

| Step | What happens |
|---|---|
| **1. Maintainer decisions first** | Existing editorial reasoning/corrections/judgment goes in directly as `editorial`-type items, `status = current`, `approved_by = maintainer`. Per Priority 1, a maintainer decision is self-approving. |
| **2. Existing docs ingested as `proposed`, never `current`** | Desktop PPT, Mobile PPT, tutorial scripts, current repo docs — parsed once into `existing_documentation` evidence + `documentation`-type proposals. Per Priority 3, this is historical knowledge, not automatically today's truth. |
| **3. Screenshots/recordings ingested as evidence only** | Not auto-promoted into claims. Available to ground future proposals, but can't create `current` knowledge alone (§3). |
| **4. Maintainer works the `proposed` queue at their own pace** | Gradual, not a one-time gate. Unreviewed items stay usable (retrievable via `get_history`/`get_pending`), just not returned by the default `get_current` query. |
| **5. Browser verification enriches later, additively** | Once live-access evidence exists, it follows the same confirm/refine/contradict/supersede path (§5) against the bootstrap dataset — it doesn't replace or reset it. |

This ordering matters: Editorial Memory is usable from day one of ingestion, even incomplete, and only gets more accurate over time. It's never *wrong* in the sense of asserting unverified claims as current — unverified content simply stays `proposed`.

---

## 11. Failure Modes

| Failure mode | Why it happens | How this design handles it |
|---|---|---|
| Stale `current` knowledge after a product update | Nothing auto-forces re-verification | Out of scope to enforce automatically. `Evidence.captured_at` gives Documentation Intelligence (or a maintainer) enough to flag "this claim's newest evidence is N months old" later. |
| Two maintainers approve conflicting states at once | No locking (plain files) | Acceptable at this scale. Both states persist in history; the conflict is visible for a human to resolve. |
| Too many tiny `KnowledgeItem`s per feature area | No enforced granularity | `feature_area` grouping keeps items discoverable; a maintainer can merge later by superseding. Not auto-solved — that would be premature ontology work. |
| Evidence artifact goes missing on disk | `source_ref` is a plain path | `Evidence` records are never deleted even if the target file is lost — metadata survives as provenance. Known, accepted limitation. |
| Annotation mistaken for authoritative knowledge | Sits conceptually near `KnowledgeItem` | Structurally prevented: `Annotation` has no `status` field and is never returned by `get_current`/`get_by_type`. |
| Retrieval accidentally returns too much (token blowup) | Careless future implementation inlines evidence | Prevented by design: `content` is short, evidence is a separate `get_evidence` call — a constraint for whoever implements retrieval to hold to. |
| Contradiction silently overwrites current knowledge | Implementation shortcut skips the approval gate | **Explicitly disallowed** (§5): a `contradicts` relation must land `contradicted`, never `current`, until approved. **The single most important rule to preserve at implementation time.** |

---

## 12. Acceptance Criteria

A Phase 3 implementation satisfies this audit only if **all** of the following hold:

- [ ] Exactly 3 record types exist (`KnowledgeItem`, `Evidence`, `Annotation`) — no ontology/taxonomy layer.
- [ ] `KnowledgeItem.states` is append-only — nothing edits or deletes a previously-created state.
- [ ] Every `KnowledgeState` carries `evidence_refs`, `status`, `approved_by`/`approved_at`, `created_at` — the full §4 provenance set, no external join needed.
- [ ] `status = current` is only reachable via explicit approval — no evidence type, including browser verification, auto-promotes.
- [ ] A `contradicts` relation never overwrites `current` — it creates a new `contradicted` state pending resolution.
- [ ] Only the 5 retrieval functions from §7 exist — no ranked/fuzzy search required.
- [ ] Bootstrap runs on maintainer input + existing docs + screenshots + recordings alone — live browser access is not a hard dependency.
- [ ] "Current knowledge for a feature area" never requires re-parsing a PPT, script, or screenshot at query time.
- [ ] The §9 repository structure (or an equivalent flat, plaintext, git-diffable layout) is used — no database introduced.
- [ ] This document (or its successor) is the schema's single source of truth — `docs/DECISIONS.md` records the decision to build against it once implementation is actually approved.

**Added by the founder amendments — see §17 for the full, current list:**

- [ ] Product/documentation/editorial knowledge remain independently retrievable (never blended into one untyped result) — `[Amendment 1]`.
- [ ] `Evidence.verification_scope` exists and is used as a review-time signal, not a mechanical gate — `[Amendment 2]`.
- [ ] `rationale` is a supported, optional field on `KnowledgeState` — `[Amendment 3]`.
- [ ] `feature_area` follows the `<platform>.<feature>` convention from the first record onward — `[Amendment 4]`.
- [ ] `invalidated` is a distinct status from `superseded`/`contradicted`, excluded from every normal retrieval path — `[Amendment 5]`.
- [ ] A bounded, human-authorized hard-purge operation exists and does not require a schema or architecture change to use — `[Amendment 6]`.

---

## 13. Final Recommendation

## ✅ BUILD

The locked founder clarification — living, evolving, version-aware, provenance-preserving, history-preserving — is fully satisfiable by a three-entity, append-only model with no ontology, no database, and no dependency on live Bridge4PS access. None of the ten questions in the brief surfaced a genuine unknown or a reason to research further — the evidence hierarchy, provenance requirements, and evolution rules translate directly into schema fields and process rules, with no new architectural decisions needed beyond what's already locked.

**Two things are explicitly out of scope for this build — not blockers, just not this phase:**

1. **The `browser_observation` producer** (script, template, or future agent). The integration *point* is designed (§6); building the producer is separate work for whenever live access is actually used.
2. **Documentation Intelligence's own retrieval logic.** This audit defines the contract it will call against (§7) — implementing Documentation Intelligence itself is the next milestone.

No implementation was performed as part of this audit, per instruction.

> **Amendment status (see §14–§18 below):** the founder has since reviewed this audit and approved it as the basis for Phase 3, with six specific refinements. The verdict is unchanged: **BUILD.** No amendment required redesigning anything above — each extends a specific field, status, or query already present in this design. §17 is the merged, current spec; §18 is the smallest implementation plan against it. Nothing has been implemented.

---

## 14. Amendment Log

Six refinements, approved after the original audit (§1–§13) shipped. Each is layered onto a specific part of the original design rather than replacing it — see the inline `[Amendment N]` markers in §2.2, §3, §5, §7, and §9 for exactly where.

| # | Refinement | What it adds | Where it lands |
|---|---|---|---|
| 1 | Knowledge categories must remain distinct | Reinforces the existing `knowledge_type` discriminator — product/documentation/editorial must stay independently retrievable, never blended into one interchangeable "truth" | Already satisfied by §2.1's design; no schema change |
| 2 | Verification scope | `Evidence.verification_scope` — a small enum naming what an evidence artifact actually proves (visual, workflow, permission-specific, etc.) | §2.2 schema, §3 |
| 3 | Editorial rationale | `KnowledgeState.rationale` — optional freeform field preserving the human "why" behind a claim | §2.2 schema |
| 4 | Feature-area naming convention | `<platform>.<feature>` dot-delimited convention adopted from day one, still just a string, no registry | §2.2, §9 |
| 5 | Invalid/polluted knowledge | New `invalidated` status, distinct from `superseded` — for content that was never trustworthy, not content that was once true | §2.2 schema, §5, §7, full detail in §15 |
| 6 | Hard purge / deletion | A bounded, human-authorized exception to "nothing is ever deleted," for secrets/PII/legal takedown, with an optional tombstone | Full detail in §15 |

### 14.1 Conflict check

**No amendment conflicts with the original audit.** Specifically:

- Amendments 1–4 add fields or reinforce existing structure — they don't touch the 3-entity boundary, the append-only rule, or the approval gate.
- Amendment 5 (`invalidated`) is a genuinely new status value, but it's additive: it doesn't change what `superseded`/`contradicted`/`current`/`proposed` mean, and it doesn't weaken the original claim that "nothing is ever deleted" — it clarifies that claim applies to *valid* history, and defines a separate category for content that was never valid.
- Amendment 6 (hard purge) is the one amendment that's in tension with a literal reading of §5's "nothing is ever deleted" — but that line was always describing normal product-knowledge evolution, and the founder's refinement explicitly scopes purge to exceptional, human-authorized, legally/security-driven cases outside that flow. §15 states this distinction explicitly so it's never ambiguous at implementation time.
- The record model stays at exactly 3 entities for normal operation. The tombstone (§15) is not a 4th entity in the working model — it's a narrow, rarely-used stub shape that only appears in place of something that was purged.

No redesign occurred. No ontology was introduced. No database was introduced.

---

## 15. Invalidation & Purge Model

### 15.1 Invalidated ≠ superseded

These answer different questions and must not be conflated:

| | Was the claim ever true? | What happens to it |
|---|---|---|
| **Superseded** | Yes — it was correct when approved, then the product changed | Stays in `states` forever, `status = superseded`, retrievable as valid history via `get_history` |
| **Invalidated** | No — it was never trustworthy (hallucination, bad ingestion, injected content, wrong attribution, stale material wrongly promoted) | Stays in `states` (nothing is silently deleted from the record), `status = invalidated`, excluded from `get_current`, `get_history`, and `get_by_type` — visible only via the dedicated `get_invalidated` |

**Example:** "Filters opened a popover" → Bridge4PS changes it to a sidebar → the popover state is `superseded`. That's real historical product truth. Contrast: an ingestion run mistakenly creates a claim from a corrupted screenshot, or an AI proposal hallucinates a permission rule that was never real. That claim is `invalidated` — it was never true at any point, so it must never be presented to Documentation Intelligence (or a human) as "this used to be the case."

### 15.2 Invalidation fields

Already in the §2.2 schema:

```yaml
status: invalidated
invalidated_by: string      # who/what flagged it
invalidated_at: datetime
invalidation_reason: string  # short explanation — omitted only if the reason itself would be unsafe to record
```

An invalidated state is never returned by normal retrieval (§7). It retains enough provenance to explain the rejection *unless doing so would itself be unsafe* (see 15.3) — in which case `invalidation_reason` may be omitted or generalized rather than describing the unsafe content.

### 15.3 Hard purge

Purge is a different, more severe operation than invalidation: invalidation keeps the record but excludes it from truth; purge removes content that must not remain stored at all — secrets, credentials, personal information, confidential data, maliciously ingested material, or anything under a legal deletion requirement.

**Purge is not part of the normal evolution flow (§5).** It is:

- **Human-authorized only.** No evidence-ingestion pipeline, approval workflow, or automated process can trigger it. It's a deliberate maintenance action.
- **Bounded.** It operates on one specific record (a `KnowledgeState`, an `Evidence` record, or an `Annotation`) at a time — not a bulk operation, not a schema migration.
- **Two modes, in order of preference:**
  1. **Purge with tombstone** (default): the unsafe content is removed; a small stub remains at the same location: `{ id, purged_at, purged_by, reason }`. This preserves the *fact that something was here and why it's gone* without preserving the unsafe content itself.
  2. **Purge with full removal**: used only when even the tombstone's metadata (the id, the reason text) would itself be unsafe to retain. In that case nothing remains — no trace, no stub. This must always be available; a design that *required* a tombstone would itself be a data-safety bug.
- **Requires no architectural change.** Both modes are direct file operations against the existing plaintext store (§9) — delete a file, optionally write a tiny tombstone file in its place. Nothing about the `KnowledgeItem`/`Evidence`/`Annotation` schema, the retrieval functions, or the evolution rules needs to change to support this; purge operates *underneath* them, on the storage layer directly.

A purged record simply isn't there for any query to find — this isn't a new retrieval-exclusion rule like `invalidated` is; it's the absence of the record (or the presence of a clearly-non-claim tombstone stub) doing the work.

---

## 16. Phase 3 Boundary (Accepted Scope)

Explicit accepted scope for this phase, so there's no ambiguity about what "Editorial Memory" includes:

**Editorial Memory may:**

- Ingest evidence
- Create proposed knowledge
- Approve knowledge
- Preserve provenance
- Preserve history
- Evolve records (confirm/refine/contradict/supersede)
- Invalidate bad knowledge
- Purge exceptional unsafe knowledge
- Retrieve current knowledge
- Retrieve history
- Expose pending-review items

**Editorial Memory must NOT yet:**

- Determine every affected slide for a product update
- Autonomously plan PPT changes
- Execute PPT changes
- Perform full documentation impact analysis
- Build a generalized Bridge4PS ontology
- Build browser-exploration infrastructure

All six "must not" items belong to Documentation Intelligence or a later phase — none of them are part of this design, and nothing in §1–§15 requires building any of them to satisfy the acceptance criteria in §12.

---

## 17. Final Implementation Contract

This section is the single merged spec — original audit + all six amendments — collapsed into one place. If an implementer only reads one section, it's this one.

**Entities (exactly 3, plus one narrow exception path):**

- `KnowledgeItem` — `id`, `knowledge_type` (`product`/`documentation`/`editorial`), `feature_area` (`<platform>.<feature>` convention), `states[]` (append-only).
- `KnowledgeState` — `version`, `content`, `status` (`proposed`/`current`/`superseded`/`contradicted`/`deprecated`/`invalidated`), `relation_to_previous`, `evidence_refs[]`, `source_trust_tier`, `approved_by`/`approved_at`, `created_at`, `superseded_by`, `rationale` (optional), `invalidated_by`/`invalidated_at`/`invalidation_reason` (only when `status = invalidated`).
- `Evidence` — `id`, `evidence_type`, `captured_at`, `captured_by`, `source_ref`, `notes`, `verification_scope` (optional, recommended).
- `Annotation` — `id`, `target_id`, `target_type`, `author`, `created_at`, `text`. Never authoritative.
- **Tombstone** (purge-only, not part of normal operation) — `id`, `purged_at`, `purged_by`, `reason` (all optional if unsafe to retain).

**The rules that govern everything else:**

1. `status = current` is reachable only via explicit maintainer approval (`approved_by` set). No evidence type — including browser verification — auto-promotes.
2. A `contradicts` relation lands `contradicted`, never overwrites `current`.
3. Nothing in normal evolution is ever deleted or edited after creation.
4. `invalidated` is for content that was never trustworthy; it is excluded from every normal retrieval path.
5. Purge is a separate, human-authorized, bounded exception outside the append-only flow, for content that must not remain stored at all.
6. Retrieval is 6 fixed lookups by `feature_area`/`knowledge_type`/id — no search, no ranking, no embeddings.
7. Extraction happens once at ingestion; retrieval never re-parses raw source; raw evidence is referenced, never inlined.
8. Repository structure is plaintext, git-diffable, no database, under `editorial-memory/` (§9).

Everything in §1–§16 is the reasoning behind these rules. This section is what to build against.

---

## 18. Implementation Slices (Plan Only)

Per instruction, this is a plan, not implementation — nothing below has been built. Ordered so each slice is independently useful and testable before the next begins.

**Slice 1 — Schema + storage skeleton**
Define the record shapes (§17) as the actual file format (YAML or similar) and lay down the `editorial-memory/` tree (§9) with `SCHEMA.md` and an empty `index.yaml`. No ingestion, no retrieval yet — just "can a `KnowledgeItem` file with one `current` state round-trip correctly."

**Slice 2 — Maintainer-decision bootstrap (Priority 1 only)**
The narrowest possible ingestion path: a maintainer directly authors `editorial`-type `KnowledgeItem`s (self-approving, per §10 step 1). Proves the append-only/provenance mechanics end-to-end with the simplest possible evidence source, before touching anything that needs parsing.

**Slice 3 — Retrieval functions**
Implement the 6 functions from §17 rule 6 against Slice 1's storage. At this point Documentation Intelligence has something to call, even with a tiny hand-authored dataset.

**Slice 4 — Existing-documentation ingestion (`proposed` only)**
Parse existing docs (Desktop/Mobile PPT, tutorial scripts, current repo docs — whatever the real evidence sources turn out to be) once each into `Evidence` + `documentation`-type `proposed` `KnowledgeItem`s, per §10 step 2. Nothing here reaches `current` automatically — this slice proves ingestion, not trust.

**Slice 5 — Review queue**
`get_pending`, and a maintainer promotes a `proposed` state to `current` for the first time via this path (not the Slice 2 self-approval path). Closes the loop the founder clarification cares about most: evidence → proposal → human approval → durable current knowledge.

**Slice 6 — Evolution in practice**
The first real `confirms`/`refines`/`contradicts`/`supersedes` case against an already-`current` item. Proves the evolution rules (§5, §17 rules 2–3) hold up against a second, later piece of evidence — not just theoretically.

**Slice 7 — Invalidation + purge**
Last, deliberately: these are exception paths (§15), not the common case, and don't need to exist before there's real knowledge in the system to invalidate or purge. Implement `invalidated` status + `get_invalidated`, then the manual purge operation (tombstone and full-removal modes).

**Explicitly not a slice — separate future work, not part of Editorial Memory:**

- The `browser_observation` producer (§6) — build whenever live access is actually used.
- Documentation Intelligence's own consumption logic — the next milestone, not this one.
