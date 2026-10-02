# Tasks: argument-description-table

## 1. Rendering

- [x] 1.1 In `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`, let `KeywordDoc._get_signature` render, when an argument has a description or the keyword has `extra_argument_docs`, the four-column argument table plus the description column of design D1, with the cell text of D2, instead of `_get_argument_list`. Without descriptions it keeps `_get_argument_table` unchanged. Update `tests/robotcode/robot/diagnostics/test_library_doc_rendering.py`:
  - `Log` on RF 7.5 has rows with `message`, `object` and "The message to log.", and `level` with `INFO` and "The log level to use.";
  - the description "What to paint:" with the items `walls` and `doors` is one cell with `<br>` before each item, and every row has six `|`;
  - the documented name `missing`, which is no argument, has its own row with empty type and default cells;
  - a description with a `|` and one with a code block;
  - a keyword without descriptions renders the four-column table as before;
  - `Return Type`, `Returns` and `Raises` are unchanged.

  Verify with `hatch run test:test -- tests/robotcode/robot/diagnostics/test_library_doc_rendering.py`.

## 2. Verification

- [x] 2.1 Run `hatch run lint:all` and `hatch run test:test`, and confirm that both pass and that no regression baseline changes.
- [x] 2.2 Look at the result on the surfaces with RF 7.5 and RF 7.4: the hover of `Log` and the Documentation Viewer on `BuiltIn` in the isolated VS Code harness (the `<br>` lines of a description with a list break), `.kw Log` in the REPL at 80 columns, `robotcode doc keyword BuiltIn Log`, and the hover of `Log` in IntelliJ by the maintainer.
