# Tasks: semantic-model-completion

## 1. Preparation

- [ ] 1.1 Confirm the SemanticModel is available and proven correct (`semantic-model-tier1-completion` parity suite green) — soft sequencing, no hard prerequisite on other feature changes; do not *merge* before tier1-completion, but development can run in parallel
- [ ] 1.2 Inventory the `complete_<NodeType>` dispatch: list every handler and the AST context signal it reads (node class, sibling inspection, column math), and map each to a model equivalent (`stmt.kind` / subclass, `token_path_at()` leaf/parent kind)

## 2. Model-branch skeleton

- [ ] 2.1 Add `_create_completion_items_from_model()`: `statement_at(line)` + `token_path_at(line, col)` dispatch, branch in `create_completion_items` on `namespace.semantic_model`; unmigrated contexts temporarily delegate to the legacy handler (incremental parity)
- [ ] 2.2 Add `test_completion_model.py`: dual-protocol (flag OFF/ON) comparison of full completion item lists over all existing completion test positions (vacuity guard: assert `namespace.semantic_model` populated in the flag-on protocol)

## 3. Migrate contexts (each green before the next)

- [ ] 3.1 Keyword-name completion: `KeywordCallStatement` context → offer keywords; namespace-qualified (`Lib.`) via `token_path_at()` NAMESPACE/SEPARATOR + `lib_entry`
- [ ] 3.2 Argument completion: `stmt.keyword_doc.arguments_spec` for positional/named context (legacy items only)
- [ ] 3.3 Variable completion inside `${…}`: `token_path_at()` leaf in a VARIABLE sub-token → `model.get_variables_at(line)`
- [ ] 3.4 Setting-value contexts: `SettingStatement` / `ImportStatement` (import path, WITH NAME), template keyword (`TEMPLATE_KEYWORD`), template-data rows (`TemplateDataStatement`)
- [ ] 3.5 Control-flow option contexts: FOR/WHILE/EXCEPT/VAR option cells via block/statement subclass (legacy behavior only)
- [ ] 3.6 Definition-header + section-header + empty-cell/new-line contexts; verify `statement_at()` position semantics match `get_node_at_position` for empty/partial lines (design Risk 2)

## 4. Close the gap to green

- [ ] 4.1 Iterate the completion corpus until parity; for each remaining deviation decide fix vs. reasoned xfail (only where the model is more correct than legacy)
- [ ] 4.2 Confirm `ModelHelper` is referenced only from the legacy fallback in `completion.py`
- [ ] 4.3 `hatch run test:test` green (all RF versions); `hatch run lint:all`

## 5. Documentation

- [ ] 5.1 Update `dev-docs/semantic-model.md`: tick the Tier 4 completion item; note completion enhancements remain in the Ideas Collection
