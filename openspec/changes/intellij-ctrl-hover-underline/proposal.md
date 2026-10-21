# Proposal

## Why

Holding Ctrl over a keyword in a Robot Framework file underlines nothing (J10 of the PyCharm findings). This is a regression from the fix for #464 (ec80cc8a), which is not released yet. On a call with a prefix such as `BuiltIn.Log`, Ctrl+hover on the prefix underlines the whole call. The hint on `Log` describes the library instead of the keyword, and on `${arg2: str}` the type is underlined too. Ctrl+click itself already goes to the right target for each part. The language server marks each part with its own semantic token, but LSP4IJ's Go to Declaration handler takes over and makes the IDE underline the whole cell.

## What Changes

- Holding Ctrl over a keyword call underlines the keyword again, also in `Test Setup` and as an argument of a keyword such as `Run Keyword And Expect Error`.
- On a call with a library or resource prefix, Ctrl+hover underlines the part under the mouse: the prefix or the keyword, each as the language server marks it.
  - The hint describes the target of that part, such as the keyword `Log` or the library `BuiltIn`.
  - The same holds for keywords whose name contains a dot, because the language server decides where a prefix ends.
- On a variable with a type, such as `${arg2: str}`, Ctrl+hover underlines the name without the type.
- Ctrl+click keeps going to the same targets as today.

Not part of this change:
- `Given` and the other BDD prefixes, the names of keyword definitions and tags; Ctrl+hover there behaves as today.
- Show Usages on the keyword of a call with a prefix, which opens no popup today.
- Reporting to LSP4IJ that its handler resolves semantic-token references itself, ignores `LocationLink.originSelectionRange` and accepts only standard token types as references. This is noted in J10 for later.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-navigation`: new requirements on what Ctrl+hover underlines, what its hint describes and where Ctrl+click goes in Robot Framework files.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/RobotCodeTokensFileViewProviderFactory.kt`: how the view provider hands keyword tokens to LSP4IJ, and what it answers LSP4IJ's Go to Declaration handler.
- Users of the plugin: Ctrl+hover underlines keywords again, and only the part under the mouse. The location in the title of Show Usages on a keyword call becomes the file of the keyword's definition.
