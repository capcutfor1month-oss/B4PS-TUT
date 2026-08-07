# Documentation Index

This repository stores Bridge4PS Documentation Engineer's product truth and its adopted development-governance layer.

## Authority-boundary record

This project's own canonical documents (`docs/PRODUCT.md`, `docs/ARCHITECTURE.md`) hold target-domain authority: product purpose, features, architecture, methodology, and terminology. `capcutfor1month-oss/project-Pipline` (Project-Pipeline) governs repository-development workflow only — how changes are clarified, approved, specified, investigated, implemented, tested, audited, and released. Adopting Project-Pipeline does not supersede Bridge4PS's own product/domain methodology, and no acting agent may redesign Bridge4PS around Project-Pipeline terminology or stages.

## Bridge4PS canonical documents

| File | Purpose |
|---|---|
| `README.md` | Project introduction and current boundary |
| `docs/PRODUCT.md` | Approved product problem, users, and scope |
| `docs/ARCHITECTURE.md` | Approved current system architecture |
| `docs/CURRENT.md` | Current state and exact next action |
| `docs/DECISIONS.md` | Bridge4PS durable decision log |
| `docs/SKILLS.md` | Approved skill sources, availability, deferred capabilities, and Bridge4PS-specific safety boundaries |

## Adopted pipeline documents (Project-Pipeline, development governance only)

| File | Purpose |
|---|---|
| `START_HERE.md` | Fresh-session recovery entry point |
| `BOOTSTRAP_CONTRACT.md` | Safe pipeline-application rules |
| `MANIFEST.md` | Required pipeline files and readiness definition |
| `AGENTS.md` | Shared AI-agent and skill-governance rules |
| `CLAUDE.md` | Claude implementation and builder-review rules |
| `GEMINI.md` | Gemini CLI investigation rules |
| `docs/FOUNDER_AUTOPILOT.md` | Product-language founder interface and automatic orchestration contract |
| `docs/FOUNDER_COMMUNICATION.md` | Founder-friendly response order, tone, term translation, and action guidance |
| `docs/CONTEXT_MANAGEMENT.md` | Context, ticket, handoff, and fresh-review rules |
| `docs/PIPELINE.md` | End-to-end operating model and automatic stage routing |
| `docs/TOOLING.md` | Tool and approved skill-source registry |
| `docs/TESTING.md` | Validation strategy |
| `docs/RELEASE.md` | Pipeline version and adoption guidance |
| `docs/PIPELINE_UPDATE_RECOMMENDATIONS.md` | Approved improvement roadmap and pilot plan (inherited) |

These documents are adopted from `capcutfor1month-oss/project-Pipline` at source commit `e755ece0caf62f8e7df1a6c168727049c362cd4c` and carry the pipeline's own generic process language. They are not Bridge4PS product or domain content.

## Supporting folders

- `templates/change/`
- `prompts/`
- `scripts/`
- `.github/`

## Anti-duplication rule

One canonical document exists per purpose. Git history stores older versions. External skills and temporary agent output must map durable approved results into these canonical documents rather than create parallel sources of truth.
