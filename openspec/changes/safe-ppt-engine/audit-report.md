# Independent Audit Report — Safe PPT Engine

This file records the history of independent Codex audits of the Safe PPT Engine, as required by `docs/PIPELINE.md` ("independent audit findings → `audit-report.md`") and Codex finding F-06. **This document is a truthful record of past audit results, not an audit performed by Claude.** Claude cannot self-certify closure of an independent audit finding — only Codex's own re-audit can.

## Founder summary

### Where things stand

The Safe PPT Engine has been independently audited by Codex seven times. Every time, real defects were found (Audit 7's PASS WITH FINDINGS still left F-06 and R-02 open). Audits 4, 5, 6, and 7 each reviewed a local, uncommitted diff directly, without requiring it to be pushed or opened as a PR first — establishing that Codex does not need a diff pushed to audit it. Seven repair rounds have addressed every finding raised so far — the first two were pushed and merged; the third through seventh exist only as local, uncommitted working-tree changes as of this record, per explicit instruction. **Audit 7 completed with PASS WITH FINDINGS: F-05 is closed; F-06 and R-02 remain and are addressed by the current local Repair 7; no integration has occurred, and Audit 8 is next. Audit 6 found that Audit Repair 5's fix for Audit 5's F-05 finding was itself unsafe: it retried `os.close(fd)`/probed the fd with `os.fstat` after a reported close failure, which risks touching a file descriptor the process no longer owns if that fd number has already been reused elsewhere. Repair 5's fixes for F-06 and R-02 are not implicated by this - those were separate, narrower governance and test-quality corrections - but this record no longer characterizes any of Repair 5's three fixes as independently confirmed, since Repair 5 was re-audited as Audit 6.** The engine's safety claims should be treated as implementer-verified for the current Repair 7 round until Audit 8 happens.

### Why this matters

This engine exists specifically to prevent PPTX source-file corruption and data loss. Its safety guarantees are exactly the kind of claim that should not rest on self-attestation alone. Seven consecutive audit rounds finding real (if progressively narrower) defects is itself informative: it shows the independent-audit step is doing real work, not a formality - including catching a *fix* that was itself unsafe, which is a stronger signal than catching an unfixed defect. An eighth round is the required final independent re-audit, not assumed to be clean.

### What has already happened

Seven audit rounds, seven repair rounds — see the technical evidence below for the finding-by-finding history. Repairs 1 and 2 are merged to `main`; Repairs 3, 4, 5, 6, and 7 are local only.

### What happens next

Audit 7 completed with PASS WITH FINDINGS as an independent review of the local Repair 6 diff; F-05 is closed, F-06/R-02 remain, and current local Repair 7 addresses them. Audit 8 is next. No integration has occurred — this task explicitly stops after local repair, without committing, pushing, or opening a PR.

### Founder action or decision

None required by this record itself. Founder should be aware that trust in the engine's safety guarantees remains contingent on a pending eighth-round audit, and that Repair 7 is not yet even in a reviewable PR state on GitHub — noting that being unreviewed-as-a-PR is not the same as being unauditable: Audits 4, 5, 6, and 7 already demonstrated Codex reviewing a local, uncommitted diff directly.

### Recommended option and reason

Have Codex independently audit the current local Repair 7 changes directly (Audit 8). Only after that clears should the changes be committed, pushed, and merged through the normal workflow (out of scope for this task).

## Technical evidence

### Verdict

**History across seven rounds (see below for detail):**

| Round | Scope audited | Verdict |
|---|---|---|
| Audit 1 | Safe PPT Engine Builds 1–2 (commit `a475d238f0c36f634d1ca9e23a9f4e2dae8441d5`) | **FAIL** — 8 findings (F-01–F-08: 1 critical, 2 high, 3 medium, 2 low) |
| Audit 2 (re-audit) | Audit Repair 1 (commit `13b3b532528b52a808030840734da9e58d92cfeb`) | **FAIL** — 6 findings remaining (F-02, F-04, F-05, F-06, R-01, R-02); F-01, F-03, F-07, F-08 confirmed CLOSED |
| Audit 3 (re-audit) | Audit Repair 2 (commit `69bb4761921ac7f7b843beb04ab255a2b272865e`) | **FAIL** — 4 findings remaining (F-05, F-06, R-01, R-02); F-01, F-02, F-03, F-04, F-07, F-08 confirmed CLOSED |
| Audit 4 (re-audit) | Local, uncommitted Audit Repair 3 diff (fixes for F-05, F-06, R-01, R-02) | **FAIL** — 3 findings remaining (F-05: `os.close(fd)` failure still untyped/leaked; F-06: governance records inaccurately claimed re-audit of a local diff required a push, and labeled un-approved N/A gates "approved"; R-02: cleanup-warning tests asserted the exception type but not the actual warning text they claimed to verify); R-01 confirmed CLOSED |
| Audit 5 (re-audit) | Local, uncommitted Audit Repair 4 diff (fixes for F-05, F-06, R-02 from Audit 4) | **FAIL** — 3 findings remaining (F-05: the close-failure fix removed the temp pathname but never verified the fd itself stayed closed after a reported close failure; F-06: `spec.md` still said "two rounds of independent audit" though the history had grown to four completed rounds, and the governance record claimed "no leaked staging resource" for a fix that had only verified the pathname; R-02: the `os.close` regression's mock always failed close for the target fd, so it could never actually prove the fd was closed). **This record previously characterized this round as having confirmed Repair 4's F-06 and R-02 fixes closed; that characterization has been removed, since Audit 5's own scope was Repair 4, and neither Audit 5 nor any later round has re-examined Repair 4's F-06/R-02 fixes on their own — recording them as independently "closed" was more than Audit 5 itself established.** |
| Audit 6 (re-audit) | Local, uncommitted Audit Repair 5 diff (fix for F-05 from Audit 5) | **FAIL** — 3 findings remaining (F-05: Repair 5's fix retried `os.close(fd)` and probed the fd with `os.fstat` after a reported close failure - unsafe, since the fd number may already have been reused by unrelated code by the time the retry runs, so the retry could close or query a descriptor the process no longer owns; F-06: the governance record claimed Audit 5 had "confirmed" Repair 4's F-06/R-02 fixes closed, and separately described Repair 5's retry strategy as safe - neither claim was warranted; R-02: the prior regression proved a retry *happened*, not that the fd being retried was still safely the engine's own, so it could not have caught the fd-reuse risk) |
| Audit 7 (re-audit) | Local, uncommitted Audit Repair 6 diff | **PASS WITH FINDINGS** — F-05 CLOSED; F-06 and R-02 remaining; no engine regression |
| Audit 8 (re-audit) | Current local Repair 7 governance/test diff | **NOT YET PERFORMED** |

### Specification reviewed

`openspec/changes/safe-ppt-engine/spec.md`. Did not exist at the time of Audit 1 or Audit 2; created retroactively in response to F-06 (see `spec.md`'s "Process deviation" note) and reviewed for the first time as part of Audit 3.

### Diff and files reviewed

Audit 1: `lib/ppt_engine.py`, `b4ps.py` as of Safe PPT Engine Build 2 (`a475d238f0c36f634d1ca9e23a9f4e2dae8441d5`). Audit 2: the same files as repaired by Audit Repair 1, against commit `13b3b532528b52a808030840734da9e58d92cfeb`. Audit 3: the same files as repaired by Audit Repair 2 (`69bb4761921ac7f7b843beb04ab255a2b272865e`), plus the newly-added `spec.md`/`audit-report.md`, reviewed against the merged commit. Audit 4: the local, uncommitted Audit Repair 3 diff, reviewed directly, without requiring a push. Audit 5: the local, uncommitted Audit Repair 4 diff, reviewed the same way. Audit 6: the local, uncommitted Audit Repair 5 diff (`lib/ppt_engine.py`'s `os.fstat`/retry logic and the governance-record corrections it accompanied). Audit 7: completed with PASS WITH FINDINGS against the local, uncommitted Repair 6 diff; Audit 8: next independent review of the current local Repair 7 governance/test diff.

### Skills declared by prior stages

None — this repository has not activated any external skill library (`phuryn/pm-skills`, `mattpocock/skills`, `coreyhaines31/marketingskills`) for this work; see `docs/SKILLS.md`.

### Evidence reviewed

Audits 1–7 were performed externally (Codex); their internal working evidence is not reproduced here. This record reflects only the founder-communicated finding IDs, severities, and pass/fail verdicts, which is what this repository can truthfully attest to.

### Skill-governance findings

Not applicable — no external skill was used in scope for any repair round.

### Blockers

Audit 7 completed with PASS WITH FINDINGS; F-05 is closed and F-06/R-02 remain. Current local Repair 7 addresses those findings; Audit 8 is next. This is the single blocker to closing the engine's audit history. It does not require the changes to be committed or pushed first — Audits 4, 5, 6, and 7 already demonstrated Codex auditing a local, uncommitted diff directly.

### Non-blocking improvements

None recorded beyond what is already tracked as deferred functionality in `docs/CURRENT.md` (additional mutation primitives, semantic targeting, etc. — all explicitly out of scope for the engine's current mechanical-primitives milestone).

### Security and privacy findings

Audit 1: F-01 (critical) source aliasing could allow the mutation source to be overwritten; F-04 (medium) stale/sensitive media could remain in a saved package after replacement. Audit 2: F-04 was found insufficiently fixed (relationship-cleanup scope too narrow). Audit 3: confirmed F-01, F-02, and F-04 correctly closed; found R-01 and F-05 remaining. Audit 4: confirmed R-01 correctly closed; found F-05 partially fixed. Audit 5: found F-05's fix removed the temp pathname but never verified the fd itself stayed closed. Audit 6: found the fix Audit 5's finding produced (Repair 5's `os.fstat`-then-retry logic) was itself a resource-safety defect - closing or probing a file descriptor after a failed close risks acting on a descriptor now owned by unrelated code, which is a materially different and arguably more concerning category of bug than the original unretried-close gap, since it could affect a file the engine has no relationship to at all. All are addressed in the repair round matching their audit round — see `verification-report.md` for the Repair-6 fix-by-fix account. Independent confirmation of the current Repair 7 fixes is exactly what the pending Audit 8 would provide.

### Regression findings

Audit 2 confirmed F-01, F-03, F-07, F-08 closed by Repair 1 with no regression. Audit 3 confirmed F-01, F-02, F-03, F-04, F-07, F-08 all still closed after Repair 2, with no regression. Audit 4 confirmed R-01 still closed after Repair 3, with no regression. Repair 6's local test suite (`tests/test_ppt_engine_audit_3.py`) includes explicit regression assertions for the full prior set, and all pre-existing tests other than the one replaced this round pass unmodified.

### Test-quality findings

Audit 2's R-02 finding drove mechanism-level tests (call-count spies, call-order assertions) in Repair 2. Audit 3's and Audit 4's R-02 findings applied the same rigor to newly-changed residual cases. Audit 5's R-02 finding was narrower still: Repair 4's `os.close`-failure regression used a mock that always failed `os.close`, so it could never prove the fd was closed. Audit 6's R-02 finding was the sharpest yet: Repair 5's rewritten regression proved a retry *occurred* and that `os.fstat` eventually failed on the fd, but never proved the fd being retried was still the engine's own descriptor at the moment of the retry - so it structurally could not have caught the fd-reuse risk Audit 6 flagged. Repair 6 replaces that test with two: one proving `create_working_copy` never calls `os.close` or `os.fstat` on the failed fd a second time at all, and an adversarial one that lets a different, unrelated file genuinely reuse that exact fd number after the close failure and proves the engine never touches it — see `verification-report.md`.

### Remaining uncertainty

Whether Repair 7 fully satisfies an independent auditor is, by definition, not something this record can establish — that is what Audit 8 exists to determine.

### Recommended next action

Commission an independent Codex audit of the current local, uncommitted Repair 7 changes (Audit 8) before they are committed, pushed, or merged. Do not begin Editorial Memory or Documentation Intelligence before the engine clears independent audit.
