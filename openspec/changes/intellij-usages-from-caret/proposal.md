# Proposal

## Why

In PyCharm, Find Usages and Show Usages on a resource import such as `Resource    ../resources/shop.resource` show nothing, not even a message (J13 of the PyCharm findings).

The cause: PyCharm builds the action's targets from the element that the name at the caret resolves to. For an import, that element is the start of the resource file, where the language server has no references. RobotCode's target at the caret, which would find the imports and the prefixed calls, is hidden in that case.

The same rule makes PyCharm search from the declaration whenever it lies in a Robot Framework file, while VS Code always asks at the caret.

## What Changes

- Find Usages and Show Usages in a Robot Framework file search from the name at the caret, also when that name resolves to a place in a Robot Framework file:
  - on a resource import they list the imports of the file and the calls with its prefix;
  - on the prefix of a call, on a keyword and on a variable they list the same usages as before.
- The titles stay as L1 names them, such as "Argument user" for a use of a keyword argument.
- The PyCharm guide says that Find Usages also works on libraries and resource files.

This builds on two planned changes of the language server, which have to be in place first:
- `namespace-prefix-references`: References on the prefix of a call. Without it, a search from `shop.` would find only the import.
- `argument-usage-tokens`: uses of an argument are `parameter` tokens. Without it, the title for a use of `${user}` would be "Variable user".

Not part of this change:
- Reporting to LSP4IJ that Find Usages gets the declaration instead of the place at the caret. This stays noted in J13 for later.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-navigation`: Find Usages and Show Usages search from the name at the caret, also for imports and for names that resolve into a Robot Framework file.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/RobotCodeUsageTargetProvider.kt`: also answers for the element that the name at the caret resolves to.
- Platform tests next to `RobotCodeUsageTargetProviderTest`.
- `docs/src/content/docs/guides/pycharm/finding-information.mdx`: one sentence.
- Users: Find Usages and Show Usages on resource imports find the file's usages. Show Usages may name the file of the caret instead of the file of the declaration after the title.
