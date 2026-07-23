# Spec: semantic-model-sidecar-consumers

## ADDED Requirements

### Requirement: Dead ModelHelper inheritance is removed
`http_server.py`, `keywords_treeview.py`, `hover.py`, `references.py`, and `rename.py` SHALL NOT inherit from or import `ModelHelper` (none of them calls a single member — the mixin is dead weight). `code_lens.py` SHALL NOT import `ModelHelper`; its keyword-definition lookup SHALL be a local query on `namespace.library_doc`. These removals SHALL be unconditional (no feature-flag branch).

#### Scenario: No ModelHelper reference in flag-independent files
- **WHEN** `http_server.py`, `keywords_treeview.py`, `hover.py`, `references.py`, `rename.py`, and `code_lens.py` are inspected after the change
- **THEN** none of them contains an import of or inheritance from `robotcode.robot.diagnostics.model_helper.ModelHelper`

#### Scenario: Hover, references, and rename behavior is unchanged
- **WHEN** the existing hover, references, and rename E2E test suites run after the mixin removal
- **THEN** all tests pass without snapshot changes

#### Scenario: Code lens still resolves the keyword definition
- **WHEN** a code lens for a keyword definition line is resolved with `references_code_lens` enabled
- **THEN** the resolved `KeywordDoc` is the same one the legacy `get_keyword_definition_at_line()` lookup returned for that line

### Requirement: Expression variable references are rendered as model sub-tokens
The `SemanticAnalyzer` SHALL attach `PYTHON_VARIABLE_REF` sub-tokens for bare `$var` expression references on expression-context tokens (`TokenKind.CONDITION`), with positions matching the legacy `iter_expression_variables_from_token()` results. Rendering these sub-tokens SHALL NOT change diagnostics, references, or Tier 1 semantic-token output parity.

#### Scenario: $var in an IF condition gets a sub-token
- **WHEN** a file containing `IF    $x > 1` is analyzed with the semantic model enabled and `${x}` is defined
- **THEN** the `CONDITION` SemanticToken carries a `PYTHON_VARIABLE_REF` sub-token covering exactly `$x`

#### Scenario: Analyzer parity is preserved
- **WHEN** `test_variable_pipeline_comparison.py` and `test_semantic_tokens_flag_parity.py` run after the sub-token addition
- **THEN** all parity assertions pass unchanged (no new xfails)

### Requirement: Selection range uses the model when available
When `namespace.semantic_model` is set, `selection_range.py` SHALL derive variable selection ranges from the model (the shared model-path candidate extraction resolving through `SemanticModel.find_variable()`) instead of calling `iter_variables_from_token()`. The structural node/token hierarchy MAY continue to come from the AST walk (it involves no resolution, and `SemanticNode` carries no column positions). When the model is absent, the legacy path SHALL be used unchanged.

#### Scenario: Identical selection ranges under both flag states
- **WHEN** a selection-range request is issued at the same position in the same document once with `robotcode.experimental.semanticModel` off and once with it on
- **THEN** both responses contain identical range hierarchies

### Requirement: Inline values and debug variable extraction use the model when available
When `namespace.semantic_model` is set, `inline_value.py` and `debugging_utils.py` SHALL obtain `(range, VariableDefinition)` pairs from the model — the shared candidate extraction (bare-`$var` condition refs from pre-computed `PYTHON_VARIABLE_REF` sub-tokens) plus `model.find_variable()` resolved at the debugger's stopped location (matching legacy visibility semantics, including column-aware visibility on defining lines) — without calling any `ModelHelper` method on the model path. When the model is absent, the legacy path SHALL be used unchanged.

#### Scenario: Identical inline values under both flag states
- **WHEN** inline values are computed for the same document and stopped location under both flag states
- **THEN** the reported variable ranges and names are identical

#### Scenario: Expression variables appear in debug extraction
- **WHEN** the stopped location covers a `WHILE $counter < 10` line and the model path is active
- **THEN** `$counter` is reported with the same range and resolved `VariableDefinition` as on the legacy path

### Requirement: ModelHelper usage is confined to legacy fallbacks
After this change, within the nine touched files, `ModelHelper` methods SHALL only be invoked from legacy fallback branches that are unreachable while `namespace.semantic_model` is set.

#### Scenario: Model path never touches ModelHelper
- **WHEN** the feature flag is on and selection range, inline value, and debug variable extraction are exercised
- **THEN** no `ModelHelper` method is called in those code paths (verifiable via test instrumentation or code review of the branch structure)
