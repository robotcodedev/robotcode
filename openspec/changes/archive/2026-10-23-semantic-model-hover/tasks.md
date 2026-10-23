# Tasks: semantic-model-hover

## 1. Preparation

- [x] 1.1 Prerequisites are archived (`semantic-model-sidecar-cleanup`, `semantic-model-tier1-completion`); confirm the mixin is gone from `hover.py` and `PYTHON_VARIABLE_REF` is on CONDITION tokens

## 2. Documentation target on the model path

- [x] 2.1 Add the model lookup of D2 (the keyword call whose keyword reference covers a position: the statement of the line, the other statements of an inline IF line, `inner_calls` recursively); verify with unit tests on analyzed models for an inline IF, `Run Keyword`, a nested `Run Keyword If` and a namespace prefix, and for positions outside any keyword reference
- [x] 2.2 `_target_at_from_model` in `code_action_documentation.py` uses the lookup; test the targets on both paths for an inline IF, `Run Keyword` and a nested `Run Keyword If`, and remove the known-gap note from `doc-viewer-access` (`design.md`, Risks) or its archived copy

## 3. Parity of the hover

- [x] 3.1 Add `test_hover_model.py` (D3): dual-protocol (flag OFF/ON) comparison of the full hover responses at positions over every cell and variable of the LSP test data, in the documents of `test_hover_test_metadata.py` and `test_hover_documentation_links.py` (the latter with viewer links on), and on keywords in an inline IF body, in `Run Keyword` and in a nested `Run Keyword If` with viewer links on; analyze every mismatch, fix it or document an xfail with its reason
- [x] 3.2 `hatch run test:test` green (all RF versions); `hatch run lint:all`

## 4. Design doc

- [x] 4.1 Update `dev-docs/semantic-model.md`: hover needs no migration, like references and rename; the documentation target on the model path finds keywords in inline IF bodies and Run Keyword arguments; the granularity audit waits for completion
