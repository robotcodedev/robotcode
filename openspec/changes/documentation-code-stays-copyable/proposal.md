# Proposal

## Why

Readers copy code from documentation into their own files, and today that code needs rework first. In documentation written in Robot Framework's format, a code span comes out as `` `vscode/\<n>` `` or with Markdown link syntax in it ([#682](https://github.com/robotcodedev/robotcode/issues/682)), and a preformatted block keeps the backticks around keyword names, so `` `Add Cookie`   foo   bar `` fails when pasted into a test.

## What Changes

- Code keeps the text of the documentation on every surface: nothing in a code span is escaped, and it does not become bold, italic or a link. `` ``vscode/<n>`` `` gives `` `vscode/<n>` ``, and `` ``a *b* c`` `` gives `` `a *b* c` ``.
- This covers everything Markdown reads as a code span, not only double backticks: a name in single backticks without a link target, and spans such as ``` ``<a>``s ```, which Robot Framework does not read as code.
- The markup of links and names falls away in code, as Libdoc does not show it either, and the text stays. `[url|text]` becomes `text`, and a name in backticks becomes the name. This applies to code spans and preformatted blocks.
- In preformatted blocks, double backticks fall away as well: `` # Returns ``${True}`` `` gives `# Returns ${True}`. Three backticks in a row become one, as Libdoc shows them: the format has no way to escape a backtick, so this is how a block keeps one.
- `*` and `_` stay in code, also in preformatted blocks, where Libdoc turns `*** Test Cases ***` into `* Test Cases *`.
- Text around a link in a preformatted block no longer gets lost: `| a | b [x|y] c | d` gives `a | b y c | d`, not `byd`.
- A backtick inside a code span no longer breaks the span.

Plain text stays escaped (`a \< b`), bold and links around code stay, and headings stay as they are.

This deliberately differs from Libdoc, which keeps formatting inside `<code>` and `<pre>`: in Markdown a URL in code is no longer clickable. A code span cannot hold a link, and splitting it around one was rejected in favour of text that can be copied.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `keyword-documentation-rendering`: new requirements for code in Robot-format documentation: it keeps its text, and the markup of links and names falls away.
- `library-documentation-markdown`: names in preformatted text no longer stay as they are; they lose their backticks. Names in headings stay.
- `documentation-cli`: links in the viewer go to the heading, also when a line of a code block reads the same. Without backticks, such a line would otherwise win.

## Impact

- `packages/robot/src/robotcode/robot/utils/markdownformatter.py`: `LineFormatter`, `PreformattedFormatter`, `LinkFormatter.remove_link`.
- `packages/robot/src/robotcode/robot/utils/markdown_docs.py`: `code_span` and fence detection, and `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: fence detection in argument descriptions.
- `packages/repl/src/robotcode/repl/_pt/doc_viewer.py`: the map from anchors to lines.
- `tests/robotcode/robot/utils/test_markdownformatter.py`: new cases, and `test_names_in_headings_and_preformatted_text_stay` changes for blocks.
- Visible wherever Robot-format documentation is shown: hover, Documentation Viewer, signature help and completion, `robotcode doc`, the REPL. Robot Framework 7.5's own standard libraries are written in Markdown and do not go through this formatter; on older versions they do.
- No new settings, dependencies or API. The regression baselines contain neither escaped code spans nor `text` blocks, so no baseline change is expected.
