# Spec: semantic-model-sole-implementation

## ADDED Requirements

### Requirement: LSP features have no legacy fallback path

Every migrated LSP feature SHALL run only the SemanticModel path — the legacy `else` fallback (AST walk + `ModelHelper`) SHALL be removed from semantic tokens, inlay hints, signature help, all code actions, hover, completion, selection range, inline value, and debugging utils. No feature SHALL branch on the presence of `namespace.semantic_model`.

#### Scenario: No feature branches on the flag

- **WHEN** any migrated LSP feature part is inspected after this change
- **THEN** it contains no `if namespace.semantic_model … else …` fallback and no `ModelHelper` import

### Requirement: The Namespace scope API delegates to the SemanticModel

`Namespace.find_variable`, `get_variable_matchers`, and `get_resolvable_variables` SHALL delegate to `model.find_variable` / `model.get_variables_at` (with the resolution step ported for `get_resolvable_variables`). `NamespaceData` SHALL NOT carry a `local_scopes` field, and `from_data()` SHALL NOT reconstruct a `ScopeTree`.

#### Scenario: Variable lookup uses the model

- **WHEN** `Namespace.find_variable(name, position)` is called after this change
- **THEN** it returns the result of `model.find_variable(name, line)` with no `ScopeTree` involved

#### Scenario: Resolvable variables preserve resolution semantics

- **WHEN** `Namespace.get_resolvable_variables(position)` is called
- **THEN** it returns the same resolved variable set the pre-change `ScopeTree`-backed implementation returned (verified by unit test)

### Requirement: Legacy subsystems and the feature flag are removed

`namespace_analyzer.py`, `model_helper.py`, and `scope_tree.py` SHALL be deleted, and the `robotcode.experimental.semanticModel` flag SHALL be removed from `package.json`, `workspace_config.py`, and the analyzer-selection plumbing. No source file SHALL import `NamespaceAnalyzer`, `ModelHelper`, `ScopeTree`, `LocalScope`, or `ScopedVariable`.

#### Scenario: Retired classes are gone

- **WHEN** the repository is grepped after this change
- **THEN** there are no definitions of or imports for `NamespaceAnalyzer`, `ModelHelper`, or `ScopeTree`, and no references to the `semanticModel` experimental flag

### Requirement: Comparison tests are removed and parity tests become single-path

Level-E comparison/performance tests that measured the model against `NamespaceAnalyzer` SHALL be removed, and Level-D flag parameterization SHALL be dropped so the `test_*_model.py` suites run as single-path tests.

#### Scenario: No test references the deleted analyzer

- **WHEN** the test suite runs after this change
- **THEN** no test imports or compares against `NamespaceAnalyzer`, and the full suite is green on all RF versions
