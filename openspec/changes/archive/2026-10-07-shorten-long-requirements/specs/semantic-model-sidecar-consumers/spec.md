# Spec Delta

## MODIFIED Requirements

### Requirement: Inline values and debug variable extraction use the model when available

When `namespace.semantic_model` is set, `inline_value.py` and `debugging_utils.py` SHALL obtain `(range, VariableDefinition)` pairs from the model — the shared candidate extraction (bare-`$var` condition refs from pre-computed `PYTHON_VARIABLE_REF` sub-tokens) plus `model.find_variable()` resolved at the debugger's stopped location (matching legacy visibility semantics, including column-aware visibility on defining lines) — without calling any `ModelHelper` method on the model path.

#### Scenario: Identical inline values under both flag states
- **WHEN** inline values are computed for the same document and stopped location under both flag states
- **THEN** the reported variable ranges and names are identical

#### Scenario: Expression variables appear in debug extraction
- **WHEN** the stopped location covers a `WHILE $counter < 10` line and the model path is active
- **THEN** `$counter` is reported with the same range and resolved `VariableDefinition` as on the legacy path

## ADDED Requirements

### Requirement: Inline values without a model use the legacy path

When the model is absent, `inline_value.py` and `debugging_utils.py` SHALL use the legacy path unchanged.

#### Scenario: No semantic model
- **WHEN** no semantic model is built for a document and inline values are computed at a stop
- **THEN** the legacy path computes them as before
