# Proposal: argument-description-table

## Why

Since `rf75-argument-docs`, a keyword whose arguments have descriptions shows its arguments as a list, while a keyword without descriptions keeps the argument table. Robot Framework 7.5 adds argument descriptions to every keyword with arguments in BuiltIn, Collections and OperatingSystem; with 7.4 none of them has one. So the same keyword shows a table with RF 7.4 and a list with RF 7.5, and with 7.5 a page can mix both forms. The maintainer wants one form: the argument table, with the descriptions in an additional column (maintainer decision (2026-10-02)).

## What Changes

- A keyword with argument descriptions shows the argument table with a fifth column for the description. An argument without a description gets an empty cell. A name that the `Args:` section documents without being an argument of the keyword, such as a name accepted through `**kwargs`, gets a row of its own with only its name and description.
- A description is written into its cell as one line. A line break within a paragraph becomes a space, and each new paragraph and each list item starts a new line in the cell. A `|` is escaped.
- Unchanged:
  - a keyword without argument descriptions keeps the four-column table, byte for byte;
  - the return type with its description, `Returns` and `Raises`;
  - signature help and completion, which show the descriptions on their own.
- This replaces decision D3 of `rf75-argument-docs`, which lists the arguments instead of showing the table.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `keyword-documentation-rendering`: the requirement "Argument descriptions are rendered with the signature" shows documented arguments in the argument table with a description column instead of a list.

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: `KeywordDoc._get_signature` renders the table with the description column instead of the list.
- Every surface that renders keyword documentation shows the new table: hover, the Keywords view, the REPL (`.kw`, `.doc`), `robotcode doc lib` and `robotcode doc keyword`, and the Documentation Viewer of VS Code. Robot Framework's Libdoc HTML of "Open Documentation" is not affected.
- Tests: `tests/robotcode/robot/diagnostics/test_library_doc_rendering.py` and the page tests that check argument sections.
