# Proposal

## Why

In PyCharm and IntelliJ IDEA, Ctrl+click or **Navigate | Declaration or Usages** (Ctrl+B) on the name of a variable definition goes to that same place, so nothing visible happens. On the name of a keyword definition the IDE now lists the keyword's usages (#677); variable definitions are the follow-up. The IntelliJ plugin can tell the IDE that a name is a declaration only when the language server marks it as one, and today the server marks keyword and test names only, no variables. This change covers the semantic model only: with `robotcode.experimental.semanticModel` off, everything stays as it is.

## What Changes

- With the semantic model, the language server gives a variable's name the semantic token modifier `declaration` where the semantic analyzer creates the variable's definition: in `*** Variables ***`, in `[Arguments]`, as an embedded argument in a keyword name, at the first assignment of a local variable, and in `VAR`, `FOR` and `EXCEPT ... AS`. An assignment to a variable that already exists and an item assignment such as `${DICT}[key]=` stay without it: the analyzer counts them as uses of that variable.
- In PyCharm, with the semantic model, Ctrl+click and **Navigate | Declaration or Usages** on such a name open the Show Usages popup of the variable or argument, as Show Usages on that name does. On an assignment to an existing variable, Ctrl+click still goes to its definition.
- The IntelliJ plugin names a `variable` or `parameter` token with the modifier `declaration` as a declaration for the IDE, as it names keyword definitions.
- Ctrl+hover, colors, Find Usages, Show Usages and rename on variable names stay as they are, also in VS Code, which receives the modifier too.
- The full-corpus parity test of the semantic tokens leaves the new modifier out of its comparison. It is the one intended difference between the model path and the legacy path.

## Capabilities

### New Capabilities

### Modified Capabilities

- `semantic-highlighting`: with the semantic model, variable and argument names carry `declaration` where the variable is defined.
- `semantic-model-tier1-parity`: the full-corpus comparison leaves out the `declaration` modifier on variable and argument names.
- `intellij-navigation`: Ctrl+click on the name of a variable definition shows its usages, with the semantic model.

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/analyzer.py`: marks the variable token of every definition it creates with `TokenModifier.DECLARATION`. The renderer in `packages/language_server/src/robotcode/language_server/robotframework/parts/semantic_tokens.py` already maps that modifier to `declaration`.
- Tests in `tests/robotcode/robot/diagnostics/test_semantic_analyzer/` and `tests/robotcode/language_server/robotframework/parts/` (`test_semantic_tokens_variables.py`, `test_semantic_tokens_flag_parity.py`), and the analyzer snapshots that carry token modifiers.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/RobotCodeTokensFileViewProviderFactory.kt` and `RobotCodeTargetElementEvaluator.kt`, with tests in `intellij-client/src/test/kotlin/`.
- No change to the legacy path (`NamespaceAnalyzer` and the semantic tokens without the model), to LSP4IJ or to the VS Code extension. The user guides stay as they are: they do not describe the experimental semantic model.
