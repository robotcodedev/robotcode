# Spec: semantic-model-tier1-parity

## ADDED Requirements

### Requirement: The parity suite provably exercises the model path
`test_semantic_tokens_flag_parity.py` SHALL pass the feature flag in the nested settings shape the workspace lookup expects, and SHALL fail loudly (not compare vacuously) if the model path is inactive: the flag-on fixture MUST assert that `namespace.semantic_model` is populated before any token comparison runs.

#### Scenario: Vacuity guard trips when the flag does not land
- **WHEN** the flag-on protocol is created but `namespace.semantic_model` is `None` for an opened document
- **THEN** the suite errors in the fixture instead of reporting green comparisons

#### Scenario: Flag reaches the server
- **WHEN** the flag-on protocol opens any `.robot` test document
- **THEN** `namespace.semantic_model` is a populated `SemanticModel`

### Requirement: Model rendering descends into sub-tokens
`collect_tokens_from_model()` SHALL emit the leaf sub-tokens of any token that carries `sub_tokens` (recursively) instead of the flat parent token, so that variables inside arguments, conditions, and other compound values render as the same fragment sequence the legacy path produces.

#### Scenario: Variable inside an argument
- **WHEN** semantic tokens are collected via the model path for `Log    Hello ${name}!`
- **THEN** the argument renders as text/variable fragments identical to the legacy path's encoded output, not as one flat ARGUMENT token

### Requirement: Inner keyword calls render as keywords
For `RunKeywordCallStatement`, the model renderer SHALL render cells covered by `inner_calls[*].tokens` from the inner token lists (KEYWORD kind, argument decomposition), position-merged with the remaining outer tokens, producing strictly ascending token positions.

#### Scenario: Run Keyword If branches
- **WHEN** semantic tokens are collected via the model path for `Run Keyword If    ${cond}    Log    a    ELSE    My KW    b`
- **THEN** `Log` and `My KW` render as keyword tokens and `ELSE` as control flow, matching the legacy path's output exactly

### Requirement: Context modifiers match the legacy path
The model renderer SHALL emit the same semantic-token modifiers as the legacy path (builtin keywords, builtin/local/environment variables, and the remaining legacy modifier inventory), derived from pre-resolved model data (`stmt.keyword_doc`, `model.find_variable()`).

#### Scenario: BuiltIn keyword modifier
- **WHEN** semantic tokens are collected via the model path for a `BuiltIn.Log` call
- **THEN** the keyword token carries the same modifier bits as on the legacy path

### Requirement: Full-corpus parity with documented exceptions only
With the repaired suite, the model path's encoded token data SHALL equal the legacy path's for every `.robot` file in the LSP test data (including `versions/**`). Any deviation SHALL be a documented xfail naming the file and the reason, and is permitted only where the model output is demonstrably more correct than legacy.

#### Scenario: Corpus run
- **WHEN** the parity suite runs over the full test-data corpus
- **THEN** every file passes or is a reasoned xfail; there are no silent skips
