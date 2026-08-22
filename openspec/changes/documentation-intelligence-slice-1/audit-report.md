# Audit Report — Documentation Intelligence, Slice 1

## Audit chronology

| Round | Scope | Verdict |
|---|---|---|
| Audit 1 | Slice 1 Build 1 (initial implementation) | **FAIL** — 4 code findings, 3 governance findings |
| Repair Round 1 | Fix for all 7 Audit 1 findings | Superseded by Re-audit 1 below |
| Re-audit 1 | Repair Round 1's local diff | **FAIL** — 3 code findings (DI-S1-01, DI-S1-02, DI-S1-04), 3 governance/test findings (TEST-DI-01, GOV-DI-01, GOV-DI-03) |
| Repair Round 2 | Fix for all 6 Re-audit 1 findings | Superseded by Re-audit 2 below |
| Re-audit 2 | Repair Round 2's local diff | **FAIL** — 1 residual code finding (DI-S1-04 unrelated-`lib` fallback); other 5 Re-audit 1 findings confirmed closed |
| Repair Round 3 | Fix for the Re-audit 2 residual finding (this record) | Not yet independently re-audited |

## Audit 1 — FAIL

1. **Caller-supplied semantic relation treated as authoritative.** Build 1's `compare()` accepted `asserted_relation`/`asserted_documentation_vs_product` and reported them essentially as-is, subject only to structural consistency checks.
2. **Evidence sufficiency defined as mere Evidence-id existence.** Any cited Evidence id that resolved via `get_evidence` counted as sufficient, with no check that it actually bore on the claimed subject or scope.
3. **No Knowledge-type enforcement on the dual-key contract.** `product_key`/`documentation_key` were resolved via plain `get_current_by_key` with no `knowledge_type` check.
4. **Import-collision defect: duplicate class/Enum/exception identities depending on import order.** Build 1's bridge loaded `editorial-memory/lib` under a fixed private alias from inside a sibling package that was itself also named `lib`, colliding with `editorial-memory`'s own established bare-`lib` test convention.
5. **(Governance) Insufficient test coverage** for the above.
6. **(Governance) No OpenSpec/governance record set existed** for this change at all.
7. **(Governance) Stale repository status documentation** — `docs/CURRENT.md`/`docs/DECISIONS.md` not reconciled with the founder-confirmed live-Obsidian state.

**Repair Round 1** fixed all 7 (see `spec.md` → "Audit 1 findings" for the per-finding fix description).

## Re-audit 1 — FAIL

Independent Codex re-audit of Repair Round 1's local diff found Repair Round 1's own fixes for findings 1–4 above insufficiently strict in three cases, plus three further governance/test gaps:

1. **DI-S1-01 — Evidence relevance still exploitable.** Repair Round 1's relevance check accepted either (a) the Evidence already appearing in the current product state's `evidence_refs`, or (b) a caller-supplied `expected_verification_scope` intersecting the Evidence's own `verification_scope`. Path (b) was the defect: both the "expected" scope and the Evidence's own declared scope are inputs a single `compare()` call's caller can influence, so a caller could fabricate an apparent match for genuinely unrelated Evidence and obtain a positive `NEW`/`CONFIRMS` result with no real backing. Caller-selected scope overlap alone must never establish positive relevance; positive relevance must come from an independently persisted relationship already present in repository state.
2. **DI-S1-02 — KnowledgeType enforcement escapable via non-current items.** Repair Round 1's `_resolve_typed_current` only type-checked the object `get_current_by_key` returned — if the referenced KnowledgeItem existed but had no *current* state (only proposed, or only invalidated/superseded), `get_current_by_key` returned `None` before the type check ever ran, and a wrong-typed item silently resolved as if nothing existed at all. The exact item referenced by `product_key`/`documentation_key` must be type-checked regardless of lifecycle status, including when only proposed states exist and proposed-documentation opt-in is false.
3. **DI-S1-04 — Alias-first import identity gap.** Repair Round 1's bridge correctly detected and *reused* an already-loaded copy of `editorial-memory/lib` found under a non-canonical alias, but never additionally registered that object under the canonical name `lib`. A later, unrelated plain `import lib` elsewhere in the same process would then find `lib` unclaimed and freshly re-import the module from disk, creating a second, non-`is`-identical package/type identity — the exact defect the bridge exists to prevent, reachable via a different ordering than the one Repair Round 1's own regression test covered.
4. **TEST-DI-01 — Byte snapshot completeness.** One real-data test (`test_m_evidence_cited_but_not_linked_and_no_scope_is_not_relevant`) lacked the before/after whole-store byte-hash snapshot every other real-data test already had, weakening — by omission, not by a false claim — the "every real-data test proves zero mutation" documentation claim.
5. **GOV-DI-01 — OpenSpec completeness.** `spec.md` did not contain the `docs/TESTING.md`-required Classification section (base tier, rationale, specialized evidence profiles, explicit independent-audit requirement).
6. **GOV-DI-03 — `docs/INDEX.md` scope accounting.** `docs/INDEX.md` described `documentation-artifacts/bridge-ui-evidence/` as "empty until Browser Verification work resumes" — false, and had been false since well before Slice 1 began (the store already held 38 Evidence records and 2 KnowledgeItems). Also required: clearly delimiting Slice 1's own integration scope from the unrelated raw `masterslide/` decks, `Expert resources/` videos, and build caches, without silently folding any of those into the change's own scope.

## Repair Round 2 — fixes applied (this record)

All 6 Re-audit 1 findings fixed; see `spec.md` → "Re-audit 1 findings" for the full per-finding fix description, and `verification-report.md` for verification evidence. Summary:

1. `expected_verification_scope` removed entirely from `compare()`'s signature. Relevance is now exactly one deterministic test: Evidence id ∈ union of `evidence_refs` across *every* state (any status) already recorded on the `product_key` KnowledgeItem. No KnowledgeItem at all → no relevance possible → conservative `insufficient`/`unresolved`.
2. `_resolve_typed_item` resolves and type-checks the referenced KnowledgeItem unconditionally (via `_resolve_item_by_key`, independent of `get_current_by_key`), before any lifecycle-status branching, for both `product_key` and `documentation_key`.
3. `_canonicalize_under_lib` registers an alias-discovered `editorial-memory/lib` copy under the canonical name `lib` (and its already-imported submodules under equivalent `lib.<name>` keys), so later imports under any name converge; raises `EditorialMemoryImportConflictError` explicitly if `lib` is already bound to something genuinely unrelated.
4. Byte-snapshot bookend added to the previously-missing real-data test; all `TestRealRegressionCases` tests now have it uniformly.
5. `spec.md` → "Classification" section added (Standard base tier, rationale, both specialized profiles explicitly marked not-applicable with reasoning, independent-audit requirement stated).
6. `docs/INDEX.md` corrected — see `verification-report.md` and `docs/INDEX.md`'s own diff.

Adversarial regressions added for the exact reproduction of each code finding: `TestEvidenceRelevance.test_di_s1_01_reproduction_scope_like_metadata_alone_is_never_sufficient` (DI-S1-01); `TestKnowledgeTypeEnforcement.test_product_key_wrong_type_raises_even_with_no_current_state` and `.test_documentation_key_wrong_type_raises_even_when_opt_in_is_false` (DI-S1-02); `test_import_alias_first.py` (DI-S1-04, run in a fully isolated subprocess to make the alias-first ordering unambiguous, independent of this suite's own file-collection order).

## Re-audit 2 — FAIL

Independent Codex re-audit of Repair Round 2's local diff confirmed 5 of the 6 Re-audit 1 findings (DI-S1-01, DI-S1-02, TEST-DI-01, GOV-DI-01, GOV-DI-03) closed, and found one residual gap in the sixth:

1. **DI-S1-04 (residual) — unrelated-`lib` collision path.** Repair Round 2's `_load_editorial_memory_lib()` only closed the alias-first ordering (an existing editorial-memory copy found under another name is canonicalized under `lib`). If `sys.modules["lib"]` was already occupied by a genuinely unrelated module *and* no already-loaded editorial-memory copy existed anywhere in the process to canonicalize instead, the function silently fell back to loading a fresh copy of `editorial-memory/lib` under the fixed private alias `_documentation_intelligence_editorial_memory_lib` — contradicting the module's own documented intent and reintroducing the divergent-identity risk the module exists to prevent, via a code path Repair Round 2's own regression did not cover.

## Repair Round 3 — fix applied (this record)

`_load_editorial_memory_lib()`: when `_find_already_loaded()` finds no existing editorial-memory copy anywhere, and `sys.modules["lib"]` is already bound to something else, the function now raises `EditorialMemoryImportConflictError` immediately, before any load is attempted. The private-alias fallback (and its constant) is removed entirely — there is no longer any code path that loads editorial-memory under an alias other than the canonical `lib` name or a discovered-and-canonicalized existing copy. All previously-passing paths (Documentation Intelligence first, Editorial Memory first, repeated imports, alias-first load, shared class/Enum/exception identity) are unchanged and re-verified passing.

New regression: `tests/test_import_unrelated_lib_conflict.py` (subprocess-isolated) — preloads an unrelated module under `sys.modules["lib"]`, imports the Documentation Intelligence bridge, asserts `EditorialMemoryImportConflictError` is raised, and asserts editorial-memory was not loaded under the old private alias or under any other name.

## Verdict

**Repair Round 3 is not yet independently re-audited.** This repository's established convention requires a further Codex closure audit of this local diff before it is committed, pushed, merged, or treated as the foundation for further Documentation Intelligence work. That re-audit is the required next action.
