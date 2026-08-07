# Bridge4PS Documentation Engineer

## Repository identity — read this first

This is the Bridge4PS product repository. It stores the Bridge4PS product, its architecture, and its implementation.

This repository has adopted the [Universal Agentic Project Pipeline](https://github.com/capcutfor1month-oss/project-Pipline) (source commit `e755ece0caf62f8e7df1a6c168727049c362cd4c`) to govern how changes in this repository are clarified, approved, specified, investigated, implemented, tested, audited, and released.

**Authority boundary:** Project-Pipeline governs repository-development workflow only. It supplies no product, feature, philosophy, methodology, or domain content. Adopting it does not authorize applying the Pipeline's own concepts, terminology, or stage names as Bridge4PS product or domain content, and it does not authorize redesigning or reinterpreting Bridge4PS architecture, terminology, or scope. `capcutfor1month-oss/project-Pipline` remains the canonical, independent source of the pipeline itself; this repository only carries an adopted copy of that governance layer alongside its own product truth.

Bridge4PS's own canonical documents (`docs/PRODUCT.md`, `docs/ARCHITECTURE.md`) remain authoritative for what the product is. See `docs/INDEX.md` for the full authority-boundary record.

## What Bridge4PS is

Bridge4PS Documentation Engineer is a PPT/tutorial-maintenance automation project. See `docs/PRODUCT.md` for the approved product problem and scope, and `docs/CURRENT.md` for exact current state and the next permitted action.

## Current boundary

- Research: completed and closed.
- Architecture v0.1: founder-approved and locked (`docs/ARCHITECTURE.md`).
- Detailed architecture specification: not yet migrated into GitHub. Do not reconstruct or invent it here.
- Product implementation: not started.
- Canonical raw baseline (`B4PS-TUT-main.zip`): the complete, unmodified archive is committed at `baseline/source-artifacts/B4PS-TUT-main.zip` and is the authority for exact raw-baseline fidelity. The GitHub materialization at `baseline/B4PS-TUT-main/` contains 50 of 58 source files byte-for-byte; 8 unresolved Git LFS pointer entries are intentionally omitted from that extracted tree (GitHub rejects unresolved LFS references) but remain preserved in the canonical ZIP. See `docs/CURRENT.md` for the full manifest.

## Pipeline reference

Read `START_HERE.md`, `BOOTSTRAP_CONTRACT.md`, `MANIFEST.md`, `docs/FOUNDER_AUTOPILOT.md`, and `docs/PIPELINE.md` before applying further pipeline changes to this repository.
