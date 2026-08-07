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

**Status:** Active
