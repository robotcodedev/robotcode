# Spec: semantic-model-sole-implementation

## Purpose

The SemanticModel and the `SemanticAnalyzer` are the only analysis and query path: the legacy fallbacks, the feature flag, `NamespaceAnalyzer`, `ModelHelper`, `KeywordTokenAnalyzer` and `ScopeTree` are gone, and the `Namespace` scope API delegates to the model.

## ADDED Requirements

### Requirement: LSP features have no legacy fallback path

Every LSP feature SHALL run only the SemanticModel path — the legacy `else` fallback (AST walk + `ModelHelper`) SHALL be removed from semantic tokens (with `KeywordTokenAnalyzer`), inlay hints, signature help, all code actions, selection range, inline value, and debugging utils. No feature SHALL branch on the presence of `namespace.semantic_model` or use `ModelHelper`; completion keeps its context detection on the current text, with the helpers it needs in its own module.

#### Scenario: No feature branches on the flag

- **WHEN** any LSP feature part is inspected after this change
- **THEN** it contains no `if namespace.semantic_model … else …` fallback and no `ModelHelper` import

### Requirement: The Namespace scope API delegates to the SemanticModel

`Namespace.find_variable`, `get_variable_matchers`, and `get_resolvable_variables` SHALL delegate to `model.find_variable` / `model.get_variables_at` (with the resolution step ported for `get_resolvable_variables`). The `SemanticAnalyzer` SHALL NOT build a `ScopeTree`; `AnalyzerResult` and `NamespaceData` SHALL NOT carry one or its `local_scopes`, and `from_data()` SHALL NOT reconstruct one.

#### Scenario: Variable lookup uses the model

- **WHEN** `Namespace.find_variable(name, position)` is called after this change
- **THEN** it returns the result of `model.find_variable(name, line)` with no `ScopeTree` involved

#### Scenario: Resolvable variables preserve resolution semantics

- **WHEN** `Namespace.get_resolvable_variables(position)` is called
- **THEN** it returns the same resolved variable set the pre-change `ScopeTree`-backed implementation returned (verified by unit test)

#### Scenario: Visible variables keep position and precedence

- **WHEN** `Namespace.get_variable_matchers(position)` is called inside a keyword whose local variable has the name of an own variable, and on the line where a local variable is assigned, before and after the assignment
- **THEN** it returns the same variables with the same precedence as the pre-change `ScopeTree`-backed implementation (verified by the comparison test over the LSP test data)

### Requirement: Legacy subsystems are removed

`namespace_analyzer.py`, `model_helper.py`, and `scope_tree.py` SHALL be deleted, and so SHALL `KeywordTokenAnalyzer`. No source file SHALL import `NamespaceAnalyzer`, `ModelHelper`, `ScopeTree`, `LocalScope`, or `ScopedVariable`.

#### Scenario: Retired classes are gone

- **WHEN** the repository is grepped after this change
- **THEN** there are no definitions of or imports for `NamespaceAnalyzer`, `ModelHelper`, `KeywordTokenAnalyzer` or `ScopeTree`

### Requirement: The semantic-model flag is removed

The semantic-model flag SHALL be removed wherever it can be set or is stored: the VS Code setting `robotcode.experimental.semanticModel` (`package.json`, `workspace_config.py`), the IntelliJ setting, the `semantic-model` option of robot.toml, the analyzer-selection plumbing, the namespace cache metadata and `dump-model`. A robot.toml that still sets the option SHALL load without an error.

#### Scenario: No flag remains

- **WHEN** the repository is grepped after this change
- **THEN** no source file, setting definition, schema or generated reference page refers to the semantic-model flag

#### Scenario: A robot.toml that still sets the option

- **WHEN** a robot.toml sets `semantic-model = false` under `[tool.robotcode-analyze]`
- **THEN** it loads without an error, and the SemanticModel is used

### Requirement: Comparison tests are removed and parity tests become single-path

Level-E comparison/performance tests that measured the model against `NamespaceAnalyzer`, and the tests that compare the model path with the legacy path, SHALL be removed; tests that check expected results of their own SHALL run as single-path tests, and Level-D flag parameterization SHALL be dropped.

#### Scenario: No test references the deleted analyzer

- **WHEN** the test suite runs after this change
- **THEN** no test imports or compares against `NamespaceAnalyzer`, and the full suite is green on all RF versions
