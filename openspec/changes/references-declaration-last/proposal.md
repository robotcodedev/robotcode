# Proposal

## Why

In PyCharm, **LSP Reference(s)** does nothing on a library keyword such as `Log` or `Append To List`, or on a variable from a Python variables file (J12 of the PyCharm findings). Asked with the declaration, the language server lists the declaration first. For these, it lies in a Python file that no language server serves. LSP4IJ builds the target of its usages popup at the first location, so the popup finds nothing. LSP sets no order for the locations, so the server can list the usages first.

## What Changes

- With the declaration included, Find References lists the usages first and the declaration last, for keywords and for variables. The locations themselves stay the same.
- In PyCharm, LSP Reference(s) on a library keyword or on a variable from a Python variables file shows the usages, as it already does for keywords from resource files.
- VS Code shows the same list as before, because it sorts the references by file and position itself.

Not part of this change:
- Reporting to LSP4IJ that it builds the popup's target at the first location even when no language server serves that file. This stays noted in J12.
- Find Usages on resource imports (J13), which has another cause.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `workspace-references`: Find References lists the declaration after the usages.
- `intellij-navigation`: LSP Reference(s) shows the usages of library keywords and of variables from Python variables files.

## Impact

- `packages/language_server/src/robotcode/language_server/robotframework/parts/references.py`: `_find_keyword_references` and `_find_variable_references` add the declaration after the references.
- New tests in `tests/robotcode/language_server/robotframework/parts/test_references.py`. The existing regression outputs sort the locations and stay as they are.
- Rename, the references code lens and the hints on unused keywords and variables do not depend on the order.
- Clients get the locations of `textDocument/references` in another order.
