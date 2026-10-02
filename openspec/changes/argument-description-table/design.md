# Design: argument-description-table

## Context

See proposal.md for the motivation.

- **Rendering today.** `KeywordDoc._get_signature` (`library_doc.py`) collects the arguments without the `*`/`/` markers. If any of them has a description (`ArgumentInfo.doc`), or the keyword has `extra_argument_docs`, it renders `_get_argument_list`: one list item per argument, ``- `name`: `type` = `default` — description``, with the description from `_format_description` (the fragment converted by `_format_doc_fragment`, continuation lines indented, a leading list marker moved into its own block). Otherwise it renders `_get_argument_table`: a headerless table with four columns, `` `name` ``, `: ` and the types joined by ` \| `, `=`, and `` `default` ``. `Return Type`/`Returns` and `Raises` follow either form.
- **Why it is the list.** `rf75-argument-docs` D3 chose the list after the maintainer saw the table followed by a separate description list, where the arguments read as if named twice. A fifth table column was rejected there because single-line cells cannot hold multi-line descriptions, lists or code, and because the cells were seen to wrap into 12-character cells in the REPL at 80 columns.
- **Measured (2026-10-02).**
  - BuiltIn, Collections and OperatingSystem have 201 keywords with arguments on RF 7.4.2; none has an argument description, so all render the table. On RF 7.5 all 203 have descriptions, so all render the list.
  - The 865 argument descriptions of ten RF 7.5 standard libraries include 66 multi-line ones. All of them are prose wrapped at the line length of the docstring: none has a second paragraph, a list item, a code block or a `|`.
  - The REPL renders Markdown with rich. A five-column table for `Log` at 80 columns keeps the description column at about 26 characters and wraps the text in it; at 120 columns it is about 46 characters. rich renders a soft line break as a space and leaves out inline HTML other than `<kbd>` (`rich/markdown.py`, `softbreak`, `html_inline`).
  - The tests that check the argument list are in `tests/robotcode/robot/diagnostics/test_library_doc_rendering.py`; no regression baseline contains it.

## Goals / Non-Goals

**Goals:**
- One form for the arguments of a keyword on every Robot Framework version: the argument table, with a description column when there are descriptions.

**Non-Goals:**
- A header row, or a different layout of the existing four columns.
- Changes to `Return Type`/`Returns`/`Raises`, signature help, completion, and Robot Framework's Libdoc HTML.

## Decisions

### D1: The argument table gets a fifth column

When any argument has a description, or the keyword has `extra_argument_docs`, `_get_signature` renders the four columns of `_get_argument_table` unchanged, plus a fifth column with the description: `| | | | | |`, `|:--|:--|:--|:--|:--|`. An argument without a description has an empty fifth cell. Each name of `extra_argument_docs` gets a row with `` `name` `` in the first cell, its description in the fifth and the other cells empty, after the arguments, in the order of the documentation.

Without any description, the table stays the four-column table of today, byte for byte, so the documentation of RF ≤ 7.4 does not change.

Alternatives:
- The list of today: replaced by maintainer decision (2026-10-02).
- The four-column table followed by a description list: rejected in `rf75-argument-docs` D3, because it names the arguments twice.
- Always five columns, also without descriptions: an empty column on every keyword of RF ≤ 7.4 and of libraries without descriptions.

### D2: The description cell

A table cell holds one line of inline Markdown. The cell text is built from the output of `_format_doc_fragment`, which converts the description and resolves its links as today:
- the lines of a paragraph are joined with a space, as a renderer joins soft line breaks;
- a blank line, a line that starts a list item (`-`, `+`, `*`, `1.` or `1)`), and each line of a code block start a new line in the cell, written as `<br>`. Lines of a code block keep their text; the fence lines are left out;
- indentation at the start of a line is left out;
- `|` becomes `\|`, also inside code spans, as tables in GitHub's Markdown require.

VS Code's hovers and the tooltips of the Keywords view (both with `supportHtml`), the Documentation Viewer (markdown-it with `html: true`) and GitHub render `<br>` as a line break. The REPL leaves it out, so there a list in a description reads as one line, its items separated by spaces. How LSP4IJ shows it in IntelliJ is checked in task 2.2.

Alternative: a cell line per source line, without joining. It breaks wrapped prose in the middle of its sentences, which are all 66 multi-line descriptions of the standard libraries.

## Risks / Trade-offs

- [The REPL and the terminal output of `robotcode doc` lose the line structure of a description with paragraphs or lists] → only the line breaks are lost, not the text; the standard libraries of RF 7.5 have no such descriptions.
- [A code block in a description loses its formatting] → its lines stay, each on its own line in the cell; the standard libraries have none.
- [Narrow surfaces, such as a hover or the REPL at 80 columns, wrap the description column] → measured readable for `Log` at 80 columns.
- [The line breaks are HTML] → the VS Code surfaces and GitHub render them; IntelliJ is checked in task 2.2.

## Migration Plan

A rendering change only. RobotCode's library caches keep the parsed documentation, not the rendered Markdown, so nothing has to be rebuilt. Pages that the Documentation Viewer kept show the list until they are generated again. Rollback: revert the change.
