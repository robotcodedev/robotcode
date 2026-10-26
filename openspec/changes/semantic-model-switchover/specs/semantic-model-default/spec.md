# Spec: semantic-model-default

## Purpose

The SemanticModel is the analysis path by default: the flag that selects it defaults to `true`, a `false` in robot.toml or in the editor setting switches it off, and the switch is gated by a cross-feature parity harness and performance budgets.

## ADDED Requirements

### Requirement: A cross-feature parity harness gates the switch

Before the flag default is changed, a Level-D fixture SHALL run the LSP snapshot/regtest suites under both flag states and assert identical output across all LSP features and diagnostics, except the differences their specs record, and a Level-E benchmark suite (`test_analyzer_performance.py`) SHALL assert the design document's budgets: `SemanticAnalyzer` overhead ≤ 30% vs `NamespaceAnalyzer`, `SemanticModel` ≤ 500 KB per file, pickle round-trip + `resolve_references()` ≤ 50 ms per file.

#### Scenario: Harness proves cross-feature parity with the flag still opt-in

- **WHEN** the Level-D fixture runs the LSP suites with `robotcode.experimental.semanticModel` OFF and ON
- **THEN** every LSP feature produces identical output under both states, and every file of the LSP test data the same diagnostics (excepting the sanctioned variable-modifier deviation and the cases of the "Differences from the legacy path" requirements of the feature specs), with the flag default still `false` at this point

#### Scenario: Performance budget is enforced before the flip

- **WHEN** `test_analyzer_performance.py` runs
- **THEN** it fails if any of the three budgets (overhead, memory, serialization) is exceeded, blocking the default flip

### Requirement: The SemanticModel is the default analysis path

The semantic-model flag SHALL default to `true` wherever it can be set: the VS Code setting `robotcode.experimental.semanticModel`, the IntelliJ setting, and the `semantic-model` option of robot.toml when it is not set. With the flag on, `Namespace` SHALL run `SemanticAnalyzer.run()` as the sole source of all `AnalyzerResult` outputs. The flag SHALL remain present (removed only in Phase 4) so the default can be reverted.

#### Scenario: Default analysis uses the SemanticAnalyzer

- **WHEN** a workspace opens a `.robot` file with no explicit `semanticModel` setting
- **THEN** `namespace.semantic_model` is populated and the analysis output comes from `SemanticAnalyzer`

### Requirement: A false setting switches the SemanticModel off

The SemanticModel SHALL be off when robot.toml or the editor setting sets the flag to `false`, in the editor and on the command line alike; otherwise it SHALL be on.

#### Scenario: Switched off in robot.toml

- **WHEN** robot.toml sets `semantic-model = false` and the editor setting keeps its default
- **THEN** `namespace.semantic_model` is `None` in the editor and in `robotcode analyze code`

#### Scenario: Switched off in the editor

- **WHEN** the editor setting is `false` and robot.toml sets `semantic-model = true`
- **THEN** `namespace.semantic_model` is `None`
