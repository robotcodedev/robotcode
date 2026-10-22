# Proposal

## Why

Find References on the prefix of a keyword call, such as `BuiltIn` in `BuiltIn.Log` or `shop` in `shop.Open Shop As`, finds nothing. On the import of the same library or resource it lists every import and every call with that prefix. The language server already records these prefixes, but it answers References only at the import. In PyCharm this shows as LSP Reference(s) doing nothing on a prefix, found while reviewing J11 and J13 of the PyCharm findings.

## What Changes

- Find References on the prefix of a keyword call lists the same locations as on the import of that library or resource:
  - for a library, every import of it and every call with its name as prefix;
  - for a resource file, every import of it and every call with its name as prefix;
  - for a library imported with an alias, every call with that alias as prefix.
- This also holds for the libraries Robot Framework imports by itself, such as `BuiltIn`, which have no import statement.
- In PyCharm, LSP Reference(s) on a prefix shows these locations.
- The VS Code guide says that Find All References also works on a prefix.

Not part of this change:
- Find Usages on resource imports in PyCharm (J13). There the IDE searches the import's definition, which the language server cannot answer, and the fix belongs in the plugin.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `workspace-references`: Find References answers on the prefix of a keyword call.
- `intellij-navigation`: LSP Reference(s) on the prefix of a keyword call shows the usages of its library or resource.

## Impact

- `packages/language_server/src/robotcode/language_server/robotframework/parts/references.py`: the lookup for a position on a prefix and the reuse of the import's references.
- New tests in `tests/robotcode/language_server/robotframework/parts/test_references.py`. The data files stay as they are. The regression outputs of the two markers that already stand on a prefix, `firstresource.` in `references.robot`, change from no result to the references of the import.
- `docs/src/content/docs/guides/vscode/finding-information.mdx`: one sentence.
- Clients get locations where they got none before: VS Code's Find All References and PyCharm's LSP Reference(s) on a prefix. PyCharm's Show Usages and Find Usages on the prefix of a library without an import, such as `BuiltIn`, list the prefixed calls besides the library's class.
