# Tasks: semantic-model-sidecar-cleanup

## 1. Flag-independent removals

- [ ] 1.1 Remove the `ModelHelper` mixin and import from `http_server.py` (no call sites; verify with grep + `hatch run lint:all`)
- [ ] 1.2 Remove the `ModelHelper` mixin and import from `keywords_treeview.py` (same verification)
- [ ] 1.3 In `code_lens.py`, replace `self.get_keyword_definition_at_line(namespace.library_doc, line)` with a local lookup (`next((k for k in library_doc.keywords.keywords if k.line_no == line), None)`), remove the mixin and import; run the existing code-lens tests
- [ ] 1.4 Remove the dead `ModelHelper` mixin and import from `hover.py`, `references.py`, and `rename.py` (audit: zero member calls); existing hover/references/rename E2E suites must pass unchanged

## 2. Analyzer: PYTHON_VARIABLE_REF on expression tokens

- [ ] 2.1 Extend the CONDITION token builders in `semantic_analyzer/analyzer.py` to attach `PYTHON_VARIABLE_REF` sub-tokens for bare `$var` refs, positions sourced from `_iter_expression_variables_from_token`
- [ ] 2.2 Add analyzer tests: `$x` in `IF` / `WHILE` / inline-IF conditions produces a `PYTHON_VARIABLE_REF` sub-token with exact range; no sub-token for `${x}` duplication
- [ ] 2.3 Verify guard suites stay green: `test_variable_pipeline_comparison.py` + analyzer snapshot tests (diagnostics/references must not change; Tier 1 output cannot be affected — the model collector does not render sub-tokens yet, and `test_semantic_tokens_flag_parity.py` is currently vacuous)

## 3. selection_range

- [ ] 3.1 Add model branch to `selection_range.py` for the variable step only: keep the structural AST node/token walk (SemanticNode has no column info), replace `iter_variables_from_token(..., return_not_found=True)` with a `VARIABLE`/`VARIABLE_NOT_FOUND` sub-token lookup at the position; legacy path unchanged as fallback
- [ ] 3.2 Add `test_selection_range_model.py` equivalence test (dual protocol flag OFF/ON, pattern from `test_semantic_tokens_flag_parity.py`)

## 4. inline_value and debugging_utils

- [ ] 4.1 Add model branch to `inline_value.py`: `(range, VariableDefinition)` from `VARIABLE`/`PYTHON_VARIABLE_REF` sub-tokens + `model.find_variable()` resolved at the **stopped location** (legacy: `context.stopped_location.start`), found definitions only, `${CURDIR}` filtered; restrict to the request range like the legacy path
- [ ] 4.2 Add model branch to `debugging_utils.py` with the same extraction helper (consider one shared private helper if both files end up identical)
- [ ] 4.3 Add `test_inline_value_model.py` equivalence test; unit-test the debug extraction against a built model under both flag states (no ModelHelper calls on the model path)

## 5. Wrap-up

- [ ] 5.1 Full test run `hatch run test:test` plus `hatch run lint:all`
- [ ] 5.2 Reflect the resolved sidecar consumers in `dev-docs/semantic-model.md` (Impact-on-LSP section) if relevant — progress is tracked in OpenSpec, not in the doc
