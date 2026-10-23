# Design: semantic-model-hover

## Context

`hover.py` (371 LOC) works in two stages today: `_hover_default` scans `namespace.variable_references` → `keyword_references` → `namespace_references` linearly, checking `position.is_in_range()` per reference until a hit is found. On a definition in the file itself it matches the definition's `name_range`: the name of a variable without `${` and `}`, or the name of a keyword. A class-dispatch fallback (`hover_TestCase`) handles the header of a test case via AST nodes from `get_nodes_at_position` and shows its documentation, tags and metadata. Cost is O(total references in file) per request, and hover has no access to token structure (type hints, index access, inner calls).

The SemanticModel provides `token_path_at(line, col)` (outermost → innermost token chain), pre-resolved `stmt.keyword_doc` / `stmt.lib_entry`, and `find_variable(name, line, col)`. Tier 1/2 migrations established the pattern: model branch + legacy fallback + dedicated equivalence tests.

## Goals / Non-Goals

**Goals:**
- Hover resolves via one model position query instead of AST walk + reference-dict scans.
- Byte-identical hover output (contents + range) under both flag states.
- First production consumer of `token_path_at()`; run the granularity audit on that basis.

**Non-Goals:**
- No new hover content (scope/visibility info, tag hover — Ideas Collection, later changes). Resolving keywords in inner calls and inline IF bodies is parity, not new content (D2, D5).
- No changes to references.py / rename.py (audit showed they need none).
- No TokenKind merges that alter any consumer's output.

## Decisions

### D1: `token_path_at()` is the primary dispatch, not `statement_at()` + manual scan

The path gives both the leaf (e.g. `VARIABLE_BASE`) and its parents (`VARIABLE` → `ARGUMENT`), which is exactly what hover needs: the leaf decides the hover *type*, the nearest `VARIABLE` or `PARAMETER` on the path supplies the name to look up (D6). This is the designed use case from the Sub-Token Decomposition section of the design doc.

*Alternative*: `token_at()` (deepest only) — rejected; loses the parent VARIABLE token needed for `find_variable()`.

### D2: Dispatch table by TokenKind, statement context via `statement_at()`

| Leaf/path TokenKind | Hover source |
|---|---|
| KEYWORD | enclosing statement's `keyword_doc` |
| ARGUMENT within a `RunKeywordCallStatement` | **inner-call resolution required**: legacy hover shows the *inner* keyword's doc (its range is in `keyword_references`). The outer statement's `tokens` carry inner keyword cells only as ARGUMENT; the keyword tokens live on `inner_calls[*].tokens` as NAMESPACE, `.` and KEYWORD_INNER (not KEYWORD), which `token_path_at()` does **not** see. The dispatch must therefore search `stmt.inner_calls` recursively for a KEYWORD_INNER or NAMESPACE token covering the position and use that inner call's `keyword_doc` or `lib_entry` |
| KEYWORD of a call in the body of an inline IF | **separate statement**: the call is a `KeywordCallStatement` of its own on the line. `statement_at()` returns the `InlineIfStatement`, and `token_path_at()` finds no token at the keyword (checked 2026-10-03 with `IF    ${TRUE}    Log    a    ELSE    No Operation`). The dispatch must take the call of the line whose keyword reference covers the position (D5) |
| NAMESPACE | `stmt.lib_entry` (KeywordCall) or `ImportStatement.lib_entry` |
| VARIABLE_BASE under VARIABLE / VARIABLE_NOT_FOUND, also in an assignment cell or a VARIABLE_NAME (FOR, VAR); PYTHON_VARIABLE_REF | the variable of that name (D6) + existing value-resolution rendering |
| VARIABLE_BASE under PARAMETER (an `[Arguments]` entry, which has no VARIABLE token) | the argument defined there (D6); a variable in its default value is a use |
| the other parts of a variable: `$`, braces, the `=` of an assignment | no hover: legacy matches only the name (`not the equal sign` in the hover test data has none) |
| TEST_NAME | test case hover: documentation, tags and metadata (D7) |
| KEYWORD_NAME | the documentation of the keyword defined there, rendered like the documentation of a call: its `KeywordDoc` from `namespace.library_doc.keywords` by line, as `code_lens.py` finds it |
| IMPORT_NAME | import hover (same content as legacy namespace hover) |
| anything else | no hover (matches legacy misses) |

A use of an argument from `[Arguments]` stays a VARIABLE token: `argument-usage-tokens` only adds the model-internal `TokenModifier.ARGUMENT`, which renders as the type `parameter`, not as a modifier, and `PARAMETER` stays the kind of the declaration.

Range returned = the range of the token that decides the hover: for a variable its VARIABLE_BASE, because the legacy `name_range` and reference ranges cover the name without `${` and `}` (characters 2–7 of `${A VAR}=` in the hover test data); otherwise the matched token. It must equal the legacy `found_range` (parity tests enforce it).

### D3: Parity before value

The model path must reproduce legacy hover byte-for-byte (markdown contents and highlight range). All rendering helpers (`_my_repr`, value resolution via `imports_manager.resolve_variable`, doc formatting) are reused unchanged — only the *resolution* step changes. Enhancements land in later changes once parity is proven; this mirrors how Tier 1/2 were landed.

The hover test data already has positions for TEST_NAME, KEYWORD_NAME, IMPORT_NAME, `[Arguments]` entries with and without default values, a FOR variable, assignments and the arguments of `Run Keyword` and `Run Keywords`; `test_hover_test_metadata.py` covers tags and metadata. Missing are positions on a keyword in an inline IF body and on the keyword of the existing `Run Keyword If` call (both lines are in `hover.robot`), and on the variable of a VAR statement (Robot Framework 7.0 and newer).

### D4: Granularity audit is evidence-based and behavior-neutral

Method: for each of the 28+ variable-related TokenKinds, grep/record which consumer branches on it (Tier 1 `_TOKEN_KIND_TO_SEM_TOKEN` map, signature help, code actions, inlay hints, new hover dispatch). Output: keep/merge table appended to the design doc. Merge only kinds with **zero** consumers and identical LSP mapping; every merge must keep `test_semantic_tokens_flag_parity.py` (in its **repaired**, non-vacuous form — prerequisite from `semantic-model-tier1-completion`) and all analyzer snapshots green. If in doubt, keep the kind — the audit's job is documentation first, deletion second.

### D5: One lookup for the keyword call at a position, for hover and documentation target

Two kinds of calls are not the statement that `statement_at()` returns for their line: the calls in the body of an inline IF (statements of their own on the line, D2) and the inner calls of a Run Keyword variant (`inner_calls`, D2). One lookup returns the `KeywordCallStatement` whose keyword reference (NAMESPACE, `.`, and KEYWORD or, in an inner call, KEYWORD_INNER tokens) covers a position: the statement of the line, the other statements of an inline IF line, and the inner calls, searched recursively.

Two consumers use it:
- the hover dispatch (D2);
- `_target_at_from_model` in `code_action_documentation.py`. It answers today only for the statement of the line, so on the model path a keyword in an inline IF body or in Run Keyword arguments has no documentation source actions and no link in the heading of its hover. The legacy path has both (checked 2026-10-03 in VS Code; `doc-viewer-access` records it as a known gap).

`statement_at()` keeps one statement per line, so the lookup needs the other statements of a line: a per-line list built in `build_index()`, or a scan of `statements` if that measures cheap. The method belongs to the model, because both consumers need the same answer.

### D6: On a definition the hover shows the variable defined there; a use asks `find_variable()`

The legacy path matches a definition by its `name_range`, so the hover on the name of an assignment, a FOR or VAR variable, an `[Arguments]` entry or a `*** Variables ***` entry shows the variable defined at that place. `find_variable(name, line, col)` answers which variable a use sees: on its own line an assignment target is visible from the start of its name, but an `[Arguments]` entry only after its cell, so it would not find an argument at its own name. The dispatch therefore takes the definition whose name range is the VARIABLE_BASE range (from the enclosing definition's `local_variables` or the file's own variables) and calls `find_variable()` with the column only for uses.

### D7: The test case hover takes its content from the test's RF node

The model keeps no documentation, tags or metadata of a test: `DefinitionStatement.tags` and `DefinitionBlock.tags` exist, but the analyzer never fills them. The legacy hover reads these values from the RF `TestCase` node with Robot Framework's own properties (`Documentation.value`, `Tags.values`, the `robot.model.Metadata` mapping). On the model path the TEST_NAME token decides the hover and gives the range; the content comes from the same RF node, looked up by the line of the definition, and the rendering of `hover_TestCase` is reused. The other model paths that need something the model does not carry read the AST as well: `selection_range.py` keeps its structural steps on the AST, and `debugging_utils.py` finds the statement and token there.

*Alternative considered*: the analyzer stores the documentation, tags and metadata of every test in the model. Rejected: every cached model grows for a hover on test names, the cache layout changes, and the values would still have to come from Robot Framework to stay identical.

## Risks / Trade-offs

- [Legacy hover range comes from reference-dict `Location.range`, model range from `SemanticToken.range`; off-by-one differences (e.g. embedded arguments, BDD prefixes) would fail parity] → dual-protocol tests over every hover position in the existing test data; mismatches are analyzed individually — if legacy is wrong, document as xfail with reason (precedent exists).
- [Multiple hover sources match one position (variable inside keyword argument)] → legacy precedence is variable → keyword → namespace; the model dispatch must encode the same precedence (leaf-first path order does this naturally; verified by tests).
- [`model.find_variable()` looks up by position: it misses an argument above the `[Arguments]` line and finds it in `[Tags]` and `[Documentation]` below it, unlike Robot Framework and the references the legacy hover reads (Context of `argument-usage-tokens`)] → take the variable of a VARIABLE token from the references, or cover these orders in the parity tests.
- [Audit merges break external theme/token expectations] → merges restricted to kinds that never reach LSP output distinctly (identical mapping), hence invisible to clients.

## Migration Plan

Ordered commits: (1) model branch + dispatch with parity tests, (2) TEST_NAME and KEYWORD_NAME on the model path, where the class dispatch over `get_nodes_at_position` no longer runs and the test case hover keeps its rendering (D7), (3) audit table + zero-consumer merges, (4) design-doc checklist updates. Rollback = revert; flag default remains `false`.

## Open Questions

None.
