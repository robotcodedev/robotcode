# Proposal

## Why

In Robot Framework files, Show Usages titles its popup "LSP Usage Triggered Psi Element **Open Shop As**", and Find Usages uses the same words in its messages. That is LSP4IJ's class name split into words (L1 of the PyCharm findings). LSP4IJ 0.21.0 describes only its own elements and returns nothing once it finds RobotCode's own PSI at the place, so the platform falls back to the class name. On a local variable or a keyword argument the popup goes to the declaration instead, and the title reads "LSP Symbol **${**", where even the name is wrong. Elsewhere in PyCharm the title names the kind of thing searched for, such as "Function foo".

## What Changes

- Show Usages and Find Usages name the kind of the place in Robot Framework files: "Keyword" on keyword calls and definitions, "Argument" on keyword arguments, "Variable" on variables, "Namespace" on the names of imports and on the library or resource prefix of a keyword call. Where the kind is unknown, such as on a tag, the word is "Symbol".
- The kind comes from the language server's semantic tokens, which RobotCode now also records by type. Where there is no token, the plugin's own lexer decides between keyword and variable.
- The title shows the name of the place as it is written, without the variable's `${` and `}`, so "${" no longer stands in for a variable's name.
- Side fix in `psi/ElementTypes.kt`: `KEYWORD_NAME` gets the debug name `KEYWORD_NAME` instead of `TESTCASE_NAME`, and `ENVIRONMENT_VARIABLE_BEGIN`/`_END` get their own debug names instead of those of `VARIABLE_BEGIN`/`_END`. Debug names appear only in the PSI viewer and debug output; lexer, highlighter and brace matcher compare the element types themselves.

Not part of this change:
- LSP4IJ's usages window as such, and that it counts the definition twice (the second part of L1).
- Semantic tokens for tags from the language server.

## Capabilities

### New Capabilities

- `intellij-navigation`: how the IntelliJ plugin presents navigation in Robot Framework files, starting with how Show Usages and Find Usages name what is searched for.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/`:
  - `RobotCodeTokensFileViewProvider.kt` records the type of each semantic token it keeps.
  - A new description provider names the kind and the name.
  - `plugin.xml` registers the provider ahead of LSP4IJ's.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/psi/ElementTypes.kt`: three debug names.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the words of the kinds.
- Platform tests of the provider.
- `docs/src/assets/screenshots/pycharm/finding-usages-{light,dark}.png`: the pictures of Show Usages in the PyCharm guide, taken again with the new title.
- Users of the plugin: other titles in Show Usages and other wording in Find Usages messages. Nothing else changes in what the IDE finds or shows.
