# Design: semantic-model-hover

## Context

`hover.py` finds what is at a position in the reference lists of the analysis: it scans `namespace.variable_references` → `keyword_references` → `namespace_references` and falls back to the AST for the header of a test case. Both analyzers produce these lists. The heading of a keyword's hover links to the Documentation Viewer through the documentation target (`target_at` in `code_action_documentation.py`), which also decides the documentation source actions. On the model path `_target_at_from_model` computes the target from `statement_at()` and the statement's tokens.

Two kinds of calls are not the statement that `statement_at()` returns for their line:
- the calls in the body of an inline IF: statements of their own on the line, while `statement_at()` returns the `InlineIfStatement` (checked 2026-10-03 with `IF    ${TRUE}    Log    a    ELSE    No Operation`);
- the inner calls of a Run Keyword variant (`RunKeywordCallStatement.inner_calls`): the outer statement carries the inner keyword cells only as ARGUMENT, the inner calls carry them as NAMESPACE, `.` and KEYWORD_INNER.

For both, the model path has no documentation target today, while the legacy path has one (checked 2026-10-03 in VS Code; `doc-viewer-access` records it as a known gap).

## Goals / Non-Goals

**Goals:**
- The documentation target on the model path finds keywords in inline IF bodies and Run Keyword arguments, nested ones too.
- A test shows that hover answers the same with the flag off and on.

**Non-Goals:**
- No model branch in `hover.py` (D1).
- No new hover content.

## Decisions

### D1: Hover keeps reading the reference lists

A model branch would have to rebuild from the model's tokens the ranges and definitions that the analyzer records as references:
- for `${A + '${B}'}` the reference is `A`, while the VARIABLE_BASE token covers `A + '`;
- an overridden command-line variable has one reference location for two definitions;
- `find_variable()` answers by position, so it misses an argument used above the `[Arguments]` line and finds one in `[Tags]` and `[Documentation]` below it;
- for a call that matches several keywords the model keeps no keyword at all, while the references list each of them.

What it would gain is speed: on Robot Framework 7.5 the hover takes about 4 ms per request in the test files `hover.robot` and `references.robot` and 74 ms in the 4,658-line `very_big_file.robot` (measured 2026-10-23). The references stay after `semantic-model-cleanup`, so the hover needs no model branch to work after the switch; the parity test (D3) guards it through the switch instead.

*Alternative considered*: a model branch with a `token_path_at()` dispatch, the first plan of this change (definitions matched by their name range, the test case hover from the test's RF node, the keywords of an ambiguous call stored in the model). Rejected for the cost above. The sub-token granularity audit that this branch was to trigger moves to `semantic-model-completion`, the first production consumer of `token_path_at()`.

### D2: One model lookup for the keyword call at a position

One lookup returns the `KeywordCallStatement` whose keyword reference (NAMESPACE, `.`, and KEYWORD or, in an inner call, KEYWORD_INNER tokens) covers a position: the statement of the line, the other statements of an inline IF line, and the inner calls, searched recursively. `_target_at_from_model` uses it instead of the statement of the line, so a keyword in an inline IF body or in Run Keyword arguments gets the documentation source actions and the link in the heading of its hover on the model path too.

`statement_at()` keeps one statement per line, so the lookup needs the other statements of a line: a per-line list built in `build_index()`, or a scan of `statements` if that measures cheap (`model_variables.py` already scans `statements` for the statements of a line). It is a position query over the model's statements like `statement_at()` and `token_path_at()`, so it belongs to the model.

### D3: The parity test probes the hover positions of the test data on both paths

Like `test_selection_range_model.py`: two protocols, flag off and on, over the LSP test data. For each file the hover is requested at positions spread over every cell and every variable, and the full responses are compared. A second part opens the documents of `test_hover_test_metadata.py` and `test_hover_documentation_links.py` in both protocols, the latter with viewer links on, together with keywords in an inline IF body, in `Run Keyword` and in a nested `Run Keyword If`. These cover what the hover test data lacks: the keyword of an inline IF body and of the `Run Keyword If` call in `hover.robot` (marker lines there would shift the line numbers of all later regtest outputs) and the variable of a VAR statement. A deviation may become an xfail with a reason only where the legacy output is demonstrably wrong.

## Risks / Trade-offs

- [The `SemanticAnalyzer`'s references differ from the `NamespaceAnalyzer`'s at some positions] → the parity test shows them; each is analyzed and fixed in the `SemanticAnalyzer`, or becomes an xfail with a reason where the legacy output is wrong.
- [Probing every cell of every file takes time on both protocols] → like the selection-range test, skip `very_big_file.robot` and cap the positions per file.
- [After a restart the model comes from the disk cache, and its `keyword_doc`s are copies; those of BuiltIn have no `parent` (found 2026-10-23), so `keyword_target()` finds no import for them] → outside this change; the documentation targets on the model path miss these keywords after a restart until that is fixed separately.

## Migration Plan

Ordered commits: (1) the model lookup and `_target_at_from_model` with tests on both paths, (2) the parity test, (3) the design-doc update. Rollback = revert; the flag default stays `false`.
