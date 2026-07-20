# Spec: semantic-model-hover

## ADDED Requirements

### Requirement: Hover resolves via the SemanticModel when available
When `namespace.semantic_model` is set, hover SHALL resolve the symbol under the cursor via `model.token_path_at()` (with statement context from `model.statement_at()`), dispatching on `TokenKind`. The model path SHALL NOT walk the AST and SHALL NOT iterate the full `variable_references` / `keyword_references` / `namespace_references` dictionaries. When the model is absent, the legacy path SHALL be used unchanged.

#### Scenario: Keyword call hover
- **WHEN** the cursor is on a keyword name in a keyword call and the model path is active
- **THEN** hover shows the same documentation and highlight range as the legacy path, sourced from the enclosing statement's pre-resolved `keyword_doc`

#### Scenario: Variable hover with value resolution
- **WHEN** the cursor is on `${var}` (or on its VARIABLE_BASE sub-token) and the variable is resolvable
- **THEN** hover shows the same rendered value and range as the legacy path, with the definition found via `model.find_variable()`

#### Scenario: Position without hover target
- **WHEN** the cursor is on a position where the legacy path produces no hover (e.g. a separator)
- **THEN** the model path also produces no hover

### Requirement: Hover output parity between flag states
For every hover position covered by the existing hover test suites, the response (markdown contents and range) SHALL be identical whether `robotcode.experimental.semanticModel` is off or on. Documented xfails are permitted only where the legacy output is demonstrably wrong, following the existing parity-exception precedent.

#### Scenario: Dual-protocol parity suite
- **WHEN** `test_hover_model.py` runs hover requests through two protocols (flag off / flag on) over the hover test data
- **THEN** all responses match exactly, or carry a documented xfail with reason

### Requirement: Sub-token granularity audit is performed and documented
The variable-related `TokenKind` vocabulary SHALL be audited against actual consumers (semantic tokens map, signature help, code actions, inlay hints, hover dispatch). The resulting keep/merge table SHALL be recorded in `dev-docs/semantic-model.md`. Kinds merged SHALL be limited to those with zero distinct consumers, and merging SHALL NOT change any consumer's output.

#### Scenario: Audit result is recorded
- **WHEN** the audit completes
- **THEN** the design document contains a table listing every variable-related TokenKind with its consumers and a keep/merge verdict

#### Scenario: Merges are behavior-neutral
- **WHEN** a TokenKind merge is applied
- **THEN** `test_semantic_tokens_flag_parity.py`, the analyzer snapshot tests, and all `test_*_model.py` suites pass without output changes
