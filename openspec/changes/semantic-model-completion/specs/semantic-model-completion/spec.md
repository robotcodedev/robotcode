# Spec: semantic-model-completion

## ADDED Requirements

### Requirement: Completion context is derived from the SemanticModel

When the `robotcode.experimental.semanticModel` flag is active (`namespace.semantic_model` populated), `completion.py` SHALL determine the completion context from the SemanticModel — `model.statement_at(line)` for the statement kind/subclass and `model.token_path_at(line, col)` for the in-token position — instead of walking the AST with `get_node_at_position` and dispatching on RF AST node classes.

#### Scenario: Keyword-call context selects keyword completion

- **WHEN** the cursor is in the keyword-name cell of a keyword-call line and completion runs on the model path
- **THEN** the context is resolved from `statement_at()` returning a `KeywordCallStatement`, and keyword-name items are offered

#### Scenario: Inside a variable brace selects variable completion

- **WHEN** the cursor is inside `${…}` in an argument and completion runs on the model path
- **THEN** `token_path_at()` reports a variable sub-token leaf and variable items from `model.get_variables_at(line)` are offered

### Requirement: Completion resolution reads pre-resolved model data

On the model path, keyword-name, argument, and keyword-snippet completion SHALL read `stmt.keyword_doc`, `stmt.keyword_doc.arguments_spec`, and `stmt.lib_entry` from the SemanticStatement rather than calling `find_keyword` or `ModelHelper`. `ModelHelper` SHALL be referenced only from the legacy fallback path.

#### Scenario: Namespace-qualified keyword completion

- **WHEN** the cursor follows `BuiltIn.` and completion runs on the model path
- **THEN** the offered keywords are those of the library resolved via `stmt.lib_entry` / the NAMESPACE token, with no `find_keyword` re-resolution

### Requirement: Completion output parity between model and legacy paths

For every completion test position in the LSP test data, the completion item list produced on the model path SHALL equal the list produced on the legacy path (item labels, kinds, sort text, insert text/format, and edit ranges). Any deviation SHALL be a documented xfail naming the position and reason, permitted only where the model output is demonstrably more correct than legacy.

#### Scenario: Dual-protocol corpus parity

- **WHEN** `test_completion_model.py` runs completion over the corpus with the flag OFF and ON
- **THEN** every position yields identical item lists, or is a reasoned xfail; the flag-on fixture asserts `namespace.semantic_model` is populated before comparing

#### Scenario: No new completion kinds

- **WHEN** the model path runs on any position
- **THEN** it offers only the item kinds the legacy path already offers (no named-argument, block-option, BDD-prefix, or template-row completions introduced by this change)
