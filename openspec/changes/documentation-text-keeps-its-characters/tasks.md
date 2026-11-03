# Tasks

## 1. Escaping plain text

- [ ] 1.1 Move the escape in `LineFormatter.format` to the end and mark the syntax the formatter writes itself, in bold, italic and `LinkFormatter`. `_target` no longer undoes `\#` and escapes `<` in angle brackets; `_format_link` looks for `#`. Verify that the existing tests in `tests/robotcode/robot/utils/test_markdownformatter.py` still pass, among them `test_link_target_keeps_its_fragment`, `test_url_keeps_its_fragment_in_the_target` and `test_image_path_with_spaces_stays_an_image`. Add a test for the scenario "Only Markdown comes out": a documentation with bold, italic, code, links, a table and a block gives the expected Markdown, with no private-use character left.
- [ ] 1.2 Escape the characters of the table in design.md, and `$` after an odd number of backslashes. Verify with new tests for the scenarios of the requirement "Plain text keeps its characters": backslashes, `\${name}`, stars, underscores, entities, `[a](b)`, `~~a~~`, in a paragraph, a list item and a table cell. They pass with the fix and fail without it. The scenarios "Robot Framework's markup stays" and "Backslashes only where Markdown needs them" pin behaviour that already holds.
- [ ] 1.3 Escape block markers at the start of a line: `>`, `+`, `-`, `1.`, `1)` and `[x]:`. Verify with new tests that pass with the fix and fail without it; `* star item` passes through 1.2.

- [ ] 1.4 Escape headings and keyword names the same way, with code in them unchanged. Verify with tests: `= Section <b> here =` and a keyword named `Run <x> Now` show their text, a name in backticks in a heading stays, and on a page every link to such a heading still finds its anchor. They pass with the fix and fail without it.
- [ ] 1.5 Move the escape of backticks without a partner into the final step, so that `` \` `` stays one escape. Verify with the existing tests from `documentation-code-stays-copyable`.
- [ ] 1.6 Correct the statements "Other Robot-format text converts as before" and "identical to the hover before this change" for plain text. Verify with `openspec validate --strict`.

## 2. Variables on a documentation page

- [ ] 2.1 In `code_span_variables`, remove Markdown escapes from the text that becomes inline code. Verify with tests in `tests/robotcode/robot/utils/test_markdown_docs.py`: `${x\#y}` gives `` `${x#y}` ``, and `\\\${name}` stays as it is. They pass with the fix and fail without it.
- [ ] 2.2 Add a test to `tests/robotcode/robot/diagnostics/test_library_doc_page.py` for the page of a Robot-format library that writes `${_x_}`, `${x#y}`, `\${name}` and `\\d+`: the page contains `` `${_x_}` ``, `` `${x#y}` ``, `\\\${name}` and `\\\d+`. It passes with the fix and fails without it.

## 3. Real documentation

- [ ] 3.1 Try it on Browser 21.0.0 and on BuiltIn of RF 7.4: compare `robotcode doc lib` before and after and read the diff. Expected: only added backslashes in plain text and at the start of lines, nothing in code and nothing in link targets.
- [ ] 3.2 Look at it in VS Code through the harness: the hover of a keyword with `\\d` in its table on RF 7.4, and the same keyword in the Documentation Viewer, before and after.
- [ ] 3.3 Run `hatch run test:test` and `hatch run lint:all`; both pass. If a regression baseline changes, read the diff before accepting it.

## Workflow follow-up

- Apply after `documentation-code-stays-copyable` is committed.
- Archive the change after review.
