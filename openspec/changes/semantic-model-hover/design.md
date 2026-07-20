# Design: semantic-model-hover

## Context

`hover.py` (289 LOC) works in two stages today: `_hover_default` scans `namespace.variable_references` → `keyword_references` → `namespace_references` linearly, checking `position.is_in_range()` per reference until a hit is found; a class-dispatch fallback (`hover_TestCase`) handles definition headers via AST nodes from `get_nodes_at_position`. Cost is O(total references in file) per request, and hover has no access to token structure (type hints, index access, inner calls).

The SemanticModel provides `token_path_at(line, col)` (outermost → innermost token chain), pre-resolved `stmt.keyword_doc` / `stmt.lib_entry`, and `find_variable(name, line)`. Tier 1/2 migrations established the pattern: model branch + legacy fallback + dedicated equivalence tests.

## Goals / Non-Goals

**Goals:**
- Hover resolves via one model position query instead of AST walk + reference-dict scans.
- Byte-identical hover output (contents + range) under both flag states.
- First production consumer of `token_path_at()`; run the granularity audit on that basis.

**Non-Goals:**
- No new hover content (scope/visibility info, inner-call hover, tag hover — Ideas Collection, later changes).
- No changes to references.py / rename.py (audit showed they need none).
- No TokenKind merges that alter any consumer's output.

## Decisions

### D1: `token_path_at()` is the primary dispatch, not `statement_at()` + manual scan

The path gives both the leaf (e.g. `VARIABLE_BASE`) and its parents (`VARIABLE` → `ARGUMENT`), which is exactly what hover needs: leaf decides the hover *type*, parent supplies the lookup value (`model.find_variable(parent.value, parent.line)`). This is the designed use case from the Sub-Token Decomposition section of the design doc.

*Alternative*: `token_at()` (deepest only) — rejected; loses the parent VARIABLE token needed for `find_variable()`.

### D2: Dispatch table by TokenKind, statement context via `statement_at()`

| Leaf/path TokenKind | Hover source |
|---|---|
| KEYWORD | enclosing statement's `keyword_doc` |
| ARGUMENT within a `RunKeywordCallStatement` | **inner-call resolution required**: legacy hover shows the *inner* keyword's doc (its range is in `keyword_references`). The outer statement's `tokens` carry inner keyword cells only as ARGUMENT; the structured KEYWORD tokens live on `inner_calls[*].tokens`, which `token_path_at()` does **not** see. The dispatch must therefore search `stmt.inner_calls` recursively for a KEYWORD token covering the position and use that inner call's `keyword_doc` |
| NAMESPACE | `stmt.lib_entry` (KeywordCall) or `ImportStatement.lib_entry` |
| VARIABLE / VARIABLE_NOT_FOUND / VARIABLE_BASE / PYTHON_VARIABLE_REF | `model.find_variable()` + existing value-resolution rendering |
| TEST_NAME / KEYWORD_NAME | definition documentation (replaces `hover_TestCase` AST handler) |
| IMPORT_NAME | import hover (same content as legacy namespace hover) |
| anything else | no hover (matches legacy misses) |

Range returned = the matched SemanticToken's `range` — must equal the legacy `found_range` (reference ranges and token ranges are produced by the same analyzer; parity tests enforce it).

### D3: Parity before value

The model path must reproduce legacy hover byte-for-byte (markdown contents and highlight range). All rendering helpers (`_my_repr`, value resolution via `imports_manager.resolve_variable`, doc formatting) are reused unchanged — only the *resolution* step changes. Enhancements land in later changes once parity is proven; this mirrors how Tier 1/2 were landed.

### D4: Granularity audit is evidence-based and behavior-neutral

Method: for each of the 28+ variable-related TokenKinds, grep/record which consumer branches on it (Tier 1 `_TOKEN_KIND_TO_SEM_TOKEN` map, signature help, code actions, inlay hints, new hover dispatch). Output: keep/merge table appended to the design doc. Merge only kinds with **zero** consumers and identical LSP mapping; every merge must keep `test_semantic_tokens_flag_parity.py` (in its **repaired**, non-vacuous form — prerequisite from `semantic-model-tier1-completion`) and all analyzer snapshots green. If in doubt, keep the kind — the audit's job is documentation first, deletion second.

## Risks / Trade-offs

- [Legacy hover range comes from reference-dict `Location.range`, model range from `SemanticToken.range`; off-by-one differences (e.g. embedded arguments, BDD prefixes) would fail parity] → dual-protocol tests over every hover position in the existing test data; mismatches are analyzed individually — if legacy is wrong, document as xfail with reason (precedent exists).
- [Multiple hover sources match one position (variable inside keyword argument)] → legacy precedence is variable → keyword → namespace; the model dispatch must encode the same precedence (leaf-first path order does this naturally; verified by tests).
- [Audit merges break external theme/token expectations] → merges restricted to kinds that never reach LSP output distinctly (identical mapping), hence invisible to clients.

## Migration Plan

Ordered commits: (1) model branch + dispatch with parity tests, (2) remove `hover_TestCase` AST handler from the model path once TEST_NAME parity holds, (3) audit table + zero-consumer merges, (4) design-doc checklist updates. Rollback = revert; flag default remains `false`.

## Open Questions

- Does `test_hover.py`'s regtest position set cover all TokenKind dispatch rows (e.g. IMPORT_NAME, TEST_NAME)? If not, extend the hover test data minimally before trusting parity.
