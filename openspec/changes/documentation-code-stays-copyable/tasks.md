# Tasks

## 1. Links in preformatted blocks

- [x] 1.1 Change `LinkFormatter.remove_link` to touch only link tokens and to give the text of a link, without the image branch. Verify with new tests in `tests/robotcode/robot/utils/test_markdownformatter.py`: `| a | b [x|y] c | d` gives `a | b y c | d`, `| [https://example.com/x|response] => 1` gives `response => 1`, `| [Title|image.png]` gives `image.png`, `| [image.png|Title]` gives `Title`. They pass with the fix and fail without it.

## 2. Code spans

- [x] 2.1 Add the helper for the text of code: `remove_link`, then drop the backticks of names. In `LineFormatter.format`, take code out of the line before the other formatting, with one pattern (Robot Framework's code pattern, then a Markdown code span) and the existing placeholders; write it with `code_span()`. A span of single backticks with a link target stays a link. Remove the code step from the chain. See design.md.
- [x] 2.2 Add tests to `test_markdownformatter.py` for the scenarios of the requirements "Code keeps the text of the documentation" and "Markup of links and names falls away in code": `<`, `#`, `*`, `_`, a URL, `[a|b]` and a name in double backticks; `` `<x>` ``; ``` ``<a>``s ```; ``` ``a`b`` ```; bold around code; a table cell and a list item; with and without a name linker. Plain text stays escaped. They pass with the fix and fail without it, except the plain-text case, which pins today's behaviour.

## 3. Preformatted blocks

- [x] 3.1 In `PreformattedFormatter.format`, remove double backticks with Robot Framework's code pattern, then apply the helper. Correct the docstring of `MarkDownFormatter.__init__`: only headings keep their names.
- [x] 3.2 Split `test_names_in_headings_and_preformatted_text_stay`: the heading keeps `` `Alpha Kw` ``, a block shows `Alpha Kw`. Add tests for ``| `Add Cookie`   foo   bar``, ``| Get Text    h1    # Returns ``${True}`` `` and `| *** Test Cases ***`. The tests for names and double backticks pass with the fix and fail without it; those for the heading and for `*` pin today's behaviour.
- [x] 3.3 In `PreformattedFormatter.format`, make three backticks in a row one, as the last step. Verify with tests: ``| const s = ```Hello ${name}```;`` gives ``const s = `Hello ${name}`;``, and ``| a ` b`` stays. The first passes with the fix and fails without it; the second pins today's behaviour.

## 4. Real documentation

- [x] 4.1 Add a test to `tests/robotcode/robot/diagnostics/test_library_doc_page.py` for the page of a Robot-format library with code and a preformatted block, including a name that is a keyword of the library: the code has no backslash, the block has no backticks, and the same name outside of code is a link. It passes with the fix and fails without it.
- [x] 4.2 Try it on Browser 21.0.0: compare `robotcode doc lib Browser` before and after and read the diff. Expected: no backslashes or link syntax in code spans, examples in blocks without backticks, and no change outside of code.
- [x] 4.3 Look at it in VS Code through the harness, with Browser: a keyword with examples in the Documentation Viewer and in the hover, before and after, in the light and the dark theme.
- [x] 4.4 Run `hatch run test:test` and `hatch run lint:all`; both pass. If a regression baseline changes against the expectation in design.md, read the diff before accepting it.

## 5. Findings of the review

- [x] 5.1 Take what Robot Framework reads as code first, then the rest; escape backticks without a partner and leave what Markdown reads as escaped. Verify with tests for ``` don`t use ``<a>`` here ```, ``` Use `` in ``a``. ```, `` \`<b>` is escaped `` and ``C:\\`<a>` y``. The first three fail on the state before.
- [x] 5.2 Take the shortest free fence in `code_span`, and read a fence as CommonMark does in `markdown_docs` and in argument descriptions. Verify with tests: ``` ``True``/``False`` enable it. ``` and ```` ```x``` y ```` leave the heading after them.
- [x] 5.3 Give a link without text its target; a block takes a fence longer than any run of backticks in it. Verify with tests for ``` ``[,|]`` ```, `| Use [,|].` and a line of four backticks.
- [x] 5.4 Hold a documentation's own U+E000 first and restore it last. Verify with tests that nothing fails and the characters stay.
- [x] 5.5 Skip code lines that read like the next heading in the viewer's anchor map. Verify with a test in `tests/robotcode/repl/test_doc_viewer.py`.
- [x] 5.6 Correct the two statements of `keyword-documentation-rendering` that this change makes wrong. Verify with `openspec validate --strict`.
- [x] 5.7 Compare all checked documents with the state before: only backticks without a partner change, and the rendered text stays the same. Run `hatch run test:test` and `hatch run lint:all`; both pass.

## Workflow follow-up

- The commit that completes this closes #682 with a `Fixes #682` footer.
- The text of #682 expects `[a|b]` to stay in a code span and calls preformatted blocks not affected; update it on request.
- Archive the change after review.
