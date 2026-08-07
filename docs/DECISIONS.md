# Bridge4PS Decision Log

Durable decisions for the Bridge4PS Documentation Engineer repository. This log records this project's own decisions. It is separate from the Project-Pipeline decision log (`capcutfor1month-oss/project-Pipline` → `docs/DECISIONS.md`), which governs the pipeline itself.

## PROJ-001 — Pipeline adoption

**Decision:** Bridge4PS adopts the Universal Agentic Project Pipeline from `capcutfor1month-oss/project-Pipline` at source commit `e755ece0caf62f8e7df1a6c168727049c362cd4c` to govern repository-development workflow only.

**Reason:** Give this repository a repeatable, founder-friendly process for clarifying, specifying, implementing, testing, auditing, and releasing changes without adopting any pipeline concept as Bridge4PS product or domain content.

**Status:** Active

---

## PROJ-002 — Inherited pipeline decision: DEC-014 — Collaborative founder decision rule

**Decision (inherited from Project-Pipeline):** ChatGPT is the founder's brainstorming, explanation, and strategy partner. The founder and ChatGPT discuss evidence, options, risks, and recommendations before deciding the next product move. Claude implements approved work, and Codex audits independently when the approved workflow reaches the audit step. When the founder shares agent output, the default response is explanation and discussion — not automatic generation of another agent prompt.

**Applies to Bridge4PS as:** every agent working in this repository follows this rule unchanged.

**Status:** Active

---

## PROJ-003 — Inherited pipeline decision: DEC-017 — Target-domain / development-governance separation

**Decision (inherited from Project-Pipeline):** Two authorities apply together and must never be merged. Bridge4PS's own canonical documents (`docs/PRODUCT.md`, `docs/ARCHITECTURE.md`) govern what the product is. Project-Pipeline governs only how repository changes are clarified, approved, specified, investigated, implemented, tested, audited, and released. Being given, pointed to, or reading the Project-Pipeline repository never authorizes adopting its concepts as Bridge4PS domain content.

**Applies to Bridge4PS as:** the binding authority-boundary rule recorded in `docs/INDEX.md`.

**Status:** Active

---

## PROJ-004 — Baseline import deferred

**Decision:** The canonical raw baseline `B4PS-TUT-main.zip` is designated as the source of the Bridge4PS implementation but is not imported during pipeline bootstrap.

**Reason:** Bootstrap scope is limited to adopting the pipeline. Importing and verifying the baseline is a separately approved task, recorded as the exact next action in `docs/CURRENT.md`.

**Status:** Superseded by PROJ-005.

---

## PROJ-005 — Baseline imported; canonical ZIP is fidelity authority, GitHub materialization is a 50/58 publication view

**Decision:** `B4PS-TUT-main.zip` (SHA-256 `00f5e41f475b8205535481da11f73c4e4f0bd614e0d3b1efff938e921b9eb6ee`, 58 files, embedded source commit `85af51a123e237c14f61f5bb43094292db664561`) was imported and is the founder-approved final publication model: the unmodified archive is committed at `baseline/source-artifacts/B4PS-TUT-main.zip` as the authority for exact raw-baseline fidelity. Its extraction is committed at `baseline/B4PS-TUT-main/` with its original `.gitattributes` unmodified, containing 50 of the 58 source files byte-for-byte. The remaining 8 files are pre-existing Git LFS pointer-text files whose real binaries were never available; GitHub's server-side Git LFS enforcement (`GH008`) rejects any push referencing those objects regardless of `.gitattributes` content (confirmed by two prior failed attempts, one editing `.gitattributes` and one additionally squashing history — both still rejected). The founder approved omitting those 8 paths from the extracted GitHub tree only, while keeping their exact pointer representations preserved inside the canonical ZIP. The full omission manifest (path, LFS OID, declared size) is recorded in `docs/CURRENT.md`.

**Reason:** The canonical ZIP alone cannot be the only published artifact without also giving GitHub a materialized, browsable tree; but GitHub's LFS enforcement makes publishing pointer-text files impossible without either fabricating binaries (forbidden) or altering their content (forbidden, would destroy evidence they originated as LFS pointers). Splitting the two artifacts — ZIP as immutable fidelity authority, extracted tree as a 50/58 publication view with a documented, non-fabricated gap — satisfies "preserve raw-baseline defects and limitations as baseline evidence" without either fabricating content or leaving the import unpublishable.

**Status:** Active. This decision does not authorize Repository Hardening Batch 1, resolving the 8 missing binaries, or any other baseline content change.
