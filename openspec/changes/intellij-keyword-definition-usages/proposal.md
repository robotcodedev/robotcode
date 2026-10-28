# Proposal

## Why

In PyCharm and IntelliJ IDEA, Ctrl+click or **Navigate | Declaration or Usages** (Ctrl+B) on the name of a keyword definition only shows "Cannot find declaration to go to" (GitHub issue #677). For other languages the IDE lists the usages of a name when the caret is already on its declaration. The IntelliJ plugin has never supported this: nothing tells the IDE that the name in a keyword definition is a declaration. RobotCode's own PSI consists of lexer tokens only, and LSP4IJ offers declarations to the IDE only for files without a language of their own. Calls, Find Usages and Show Usages are not affected.

## What Changes

- Ctrl+click and **Navigate | Declaration or Usages** on the name of a keyword definition open the Show Usages popup with the keyword's definition and calls, as Show Usages on that name does.
- Holding Ctrl over that name underlines it and shows the keyword's documentation, as it does over a call of the keyword. Today nothing is underlined there.
- The IntelliJ plugin tells the IDE that the name of a keyword definition is a declaration. It does so with a target element evaluator for Robot Framework files, and by handing the server's `keywordName` tokens to LSP4IJ with a standard token type.
- Test and task names, variable definitions and everything else behave as before. Variable definitions get their own change: there the language server first has to mark declarations, and in the semantic-model path that only takes effect behind `robotcode.experimental.semanticModel` until the switchover.

## Capabilities

### New Capabilities

### Modified Capabilities

- `intellij-navigation`: Ctrl+click and Ctrl+hover on the name of a keyword definition.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/RobotCodeTokensFileViewProviderFactory.kt`: `keywordName` tokens go to LSP4IJ as `function`; a lookup of the keyword name token in a range.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/`: a new `RobotCodeTargetElementEvaluator`, registered in `plugin.xml` for the language `robotframework`.
- Tests in `intellij-client/src/test/kotlin/`.
- `docs/src/content/docs/guides/pycharm/finding-information.mdx`: one sentence in "Go to declaration".
- No change to the language server, LSP4IJ or the VS Code extension.
