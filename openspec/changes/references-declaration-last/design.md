# Design

## Context

See proposal.md for the motivation and the specs for the behavior. What the change builds on, read from LSP4IJ 0.21.0 and measured in the headless PyCharm on 2026-10-21 (J12 in `playground/pycharm-befunde.md`):

- **LSP Reference(s)** (`LSP.GotoReference`) asks for the references at the caret with `includeDeclaration = true`. `LSPUsagesManager.findShowUsagesInPopup` then:
  - shows a message for no location;
  - goes to a single location;
  - for several locations, builds the popup's target at the **first** location and starts Show Usages with it. If no language server serves that file, the search finds nothing.
- **The server** builds the list in `_find_keyword_references` and `_find_variable_references` in `references.py`. With the declaration included, both put it first. For a library keyword the declaration is in the library's Python file, for a variable from a variables file in that Python file.
- **Other callers** do not depend on the order:
  - Rename edits every location.
  - The references code lens counts without the declaration.
  - The hints on unused keywords and variables only check for any reference, also without the declaration.
  - `robotcode analyze` asks the project index directly.
- **Imports** already add their declaration after the references (`references_LibraryImport`, the alias of a library, `references_ResourceImport`).
- **VS Code** sorts references by file and position before it shows them (`ReferencesModel._compareReferences`).
- **Tests:** `test_references.py` sorts the locations before it writes its regression output, so the existing outputs do not change.
- **Prototype**, harness, PyCharm 2026.1, server from a patched copy over `PYTHONPATH` (scratchpad `proto-j12.diff`, ephemeral): the declaration moved after the references in both functions. Result:
  - LSP Reference(s) shows the popup for `Log` and `BuiltIn.Log` (11 rows), `Append To List` (2) and `${GREETING}` from `shopvars.py` (2);
  - `Add To Cart` (5) and `${user}` (3) are as before;
  - Show Usages is unchanged, and `idea.log` has no new entries.

## Goals / Non-Goals

**Goals:**

- Every client that takes the first location as the place to search from finds a usage there, as long as the name has one.

**Non-Goals:**

- Changing which locations Find References returns.
- Ordering the usages among themselves.

## Decisions

### The declaration goes last

`_find_keyword_references` and `_find_variable_references` add the declaration after the references instead of before them. With `stop_at_first`, the result keeps the first reference and the declaration, now in that order.

Alternatives:
- Only report it to LSP4IJ: PyCharm users would keep the problem until an LSP4IJ release fixes it. The report can still follow, as noted in J12.
- Leave out declarations that lie in Python files: Find References would no longer show where a library keyword is defined, in any client.
- Sort all locations by file: changes more than needed and still puts a Python file first when its path sorts first.

## Risks / Trade-offs

- [A client relies on the declaration coming first] → LSP sets no order, and VS Code sorts the locations itself.
- [A keyword or variable has no usage] → The result then holds only the declaration. LSP4IJ goes straight to it, as before.
