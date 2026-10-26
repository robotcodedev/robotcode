# Spec Delta

## MODIFIED Requirements

### Requirement: Context modifiers match the legacy path
The model renderer SHALL emit the same semantic-token modifiers as the legacy path (builtin keywords/namespaces, embedded arguments, declarations), except the builtin modifier on the name token of a built-in variable, which only the model path sets (`semantic-model-variable-modifiers`). The modifiers SHALL be computed at analysis time and carried on the `SemanticToken` (`modifiers` field); the renderer maps them through a static table without any re-resolution.

#### Scenario: BuiltIn keyword modifier
- **WHEN** semantic tokens are collected via the model path for a `BuiltIn.Log` call
- **THEN** the keyword token carries the same modifier bits as on the legacy path, sourced from the pre-computed token modifiers

### Requirement: Full-corpus parity with documented exceptions only
With the repaired suite, the model path's encoded token data SHALL equal the legacy path's for every `.robot` file in the LSP test data (including `versions/**`), apart from the builtin modifier bit on variable tokens. Any other deviation SHALL be a documented xfail naming the file and the reason, and is permitted only where the model output is demonstrably more correct than legacy.

#### Scenario: Corpus run
- **WHEN** the parity suite runs over the full test-data corpus
- **THEN** every file passes or is a reasoned xfail; there are no silent skips
