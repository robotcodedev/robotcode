# Proposal

## Why

In documentation written in Robot Framework's format, Markdown reads text that Robot Framework does not read as markup, so readers see other characters than in Libdoc. `\\d+` shows as `\d+`, `C:\\temp` as `C:\temp`, `\${name}` as `${name}`, and `*HTML*Test` loses its stars. Examples in tables are affected too, so what a reader copies from them is wrong.

## What Changes

- Plain text shows the same characters as in Libdoc, in paragraphs, list items and table cells: backslashes, stars, underscores, entities such as `&lt;`, `[text](url)`, `~~text~~`.
- At the start of a paragraph, `> `, `+ `, `* `, a lone `-`, `1. `, `1) ` and `[x]:` stay text. Numbered paragraphs no longer become Markdown lists: they read as in Libdoc, and `1)` no longer turns into `1.`.
- Markdown written in Robot-format documentation is no longer rendered as Markdown. It shows as written, as in Libdoc.
- Bold, italic, links and images as Robot Framework reads them stay.
- Headings, keyword names and the names of tests in the hover show their text too: `= Section <b> here =` and a keyword named `Run <x> Now` no longer lose `<b>` and `<x>` to Markdown's HTML.
- The raw Markdown of `robotcode doc` only gets a backslash where Markdown would otherwise change the text: `snake_case_name`, `${list}[0]`, `2 * 3`, `R&D` and `C:\temp` stay as they are.
- On a documentation page, a variable that becomes inline code shows its text: `${x#y}` no longer shows as `${x\#y}`. An escaped variable such as `\${name}` shows as written and does not become code.

This builds on `documentation-code-stays-copyable`, which takes code out of the line before the other formatting.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `keyword-documentation-rendering`: new requirement that plain text in Robot-format documentation keeps its characters, and the statements that other text and the hover stay as before name plain text as an exception.

## Impact

- `packages/robot/src/robotcode/robot/utils/markdownformatter.py`: `LineFormatter`, `LinkFormatter`, `HeaderFormatter`.
- `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: the headings of keywords.
- `packages/language_server/src/robotcode/language_server/robotframework/parts/hover.py`: the heading of a test or task.
- `packages/robot/src/robotcode/robot/utils/markdown_docs.py`: the step that writes variables as inline code.
- Tests in `tests/robotcode/robot/utils/` and `tests/robotcode/robot/diagnostics/test_library_doc_page.py`.
- Visible wherever Robot-format documentation is shown: hover, Documentation Viewer, signature help and completion, `robotcode doc`, the REPL. Robot Framework 7.5's own standard libraries are written in Markdown and do not go through this formatter; on older versions they do.
- No new settings, dependencies or API.
