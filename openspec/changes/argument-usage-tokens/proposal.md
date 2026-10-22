# Proposal

## Why

The language server sends a `parameter` token only for the declaration of a keyword's argument in `[Arguments]`. Every use of the argument in the keyword's body is a `variable` token, although LSP defines `parameter` for identifiers that "declare or reference" a parameter. Clients that name a place by its token therefore call a use of `${user}` a variable. In PyCharm, Show Usages started from such a use would be titled "Variable user" instead of "Argument user" once it searches from the name at the caret (J13 of the PyCharm findings). LSP Reference(s) on such a use is already titled that way, because LSP4IJ titles its popup by the first location, which is a use since `references-declaration-last`.

## What Changes

- Every use of an argument declared in `[Arguments]` gets a `parameter` token instead of a `variable` token, like the declaration. This covers:
  - uses in arguments and settings, also with item access, the extended syntax and inside nested variables;
  - assignments that set the argument again, such as `${user}=    Set Variable    x` and `VAR    ${user}    x`.
- The language server decides this from the same resolution that Find References and Rename use, on the default analysis path and on the semantic model, so both send the same tokens.
- Highlighting: PyCharm colours `parameter` like `variable` unless the colour scheme sets it apart. VS Code colours it through the theme's `variable.parameter` scope, so in themes that style parameters, uses look like their declaration.
- The locations that Find References, Rename and Show Usages find do not change.

Not part of this change:
- Searching from the name at the caret in PyCharm (J13), which builds on this.
- Other kinds of variables: local, test, suite, global, built-in or environment variables keep their tokens.
- Embedded arguments of a keyword's name: their declaration is a `variable` token, so their uses stay `variable` tokens too.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `semantic-highlighting`: uses of a keyword's arguments are parameters, not variables.

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/`: the analyzer marks variable tokens that resolve to an argument; the semantic model's token kinds stay as they are.
- `packages/language_server/src/robotcode/language_server/robotframework/parts/semantic_tokens.py`: both renderings send `parameter` for these names.
- Tests: targeted tests on both paths; the regression outputs of `test_semantic_tokens.py` change for the argument uses in the test data, and the parity suite (`test_semantic_tokens_flag_parity.py`) stays green.
- Planned semantic-model changes (`semantic-model-switchover`, `semantic-model-token-rendering`, `semantic-model-hover`) get a note about the marker.
