# Design: documentation-text-keeps-its-characters

## Context

See proposal.md, section Why, for the problem. This change builds on `documentation-code-stays-copyable`: by the time plain text is handled, code already waits behind placeholders.

**How the formatter works then** (`packages/robot/src/robotcode/robot/utils/markdownformatter.py`): `LineFormatter` holds code, then runs over the line in this order: escape `<`, escape `#`, bold, italic, links. `LinkFormatter._target` has to undo the `\#`, because the escape comes before the links. Nothing else is escaped, so Markdown reads the rest.

**What this does in real documentation.** Whole documents compared word by word with Libdoc: Browser 21.0.0, SeleniumLibrary, SSHLibrary, DatabaseLibrary, RequestsLibrary and the standard libraries of RF 7.4 without Telnet, 1264 documents.
- 25 places lose a backslash: `\\d+`, `C:\\temp`, `\${name}`, `Reg\\w{3}`.
- 3 lose stars: `*HTML*`, twice, and `\\[.*\\].*:`.
- 38 numbered paragraphs become lists, and `1)` shows as `1.`.
- Not in these libraries, tested by hand: `__init__` becomes bold `init`, `2*3*4` loses its stars, `&lt;` becomes `<`, `> x` becomes a quote, `[a](b)` becomes a link.

**A step after the formatter.** On a documentation page, `code_span_variables` writes every scalar variable as inline code. It takes the text as it finds it, so an escape inside a variable ends up in the code span: today `${x#y}` shows as `${x\#y}`. It leaves an escaped variable, an odd number of backslashes before `$`, as it is.

## Goals / Non-Goals

**Goals:**
- Plain text shows the same characters as in Libdoc.
- A backslash in the raw Markdown only where Markdown would otherwise change the text.
- Only Markdown comes out: backslash escapes and Markdown syntax, no HTML, and none of the private-use characters the conversion uses on the way.

**Non-Goals:**
- Links whose target exists in Libdoc but not on our page, such as `[#type-Proxy|Proxy]`. Decided: they stay as they are.
- Code, by `documentation-code-stays-copyable`.
- Rows in tables that move or disappear, and other findings of the comparison.
- Bold, italic and links in headings: they stay plain text, as in Libdoc.

## Decisions

### Escape last, and mark the formatter's own syntax

The escape moves to the end, after Robot Framework's markup has been read: hold code, bold, italic, links, escape, restore code. What the formatter writes itself (`**`, `*`, `[`, `](target)`, `![title](src)`) is wrapped in a pair of private-use markers, and the escape step leaves those regions alone. Link text and the text of bold and italic stay outside the markers, so they get escaped like any other text.

`LinkFormatter._target` no longer undoes `\#`, and it now escapes `<` itself where a target needs angle brackets. `_format_link` looks for `#` instead of `\#`.

The markers travel in the string because `_line_formatter` is shared between threads, so the formatter cannot keep this state on an instance.

Alternative: keep escaping first and undo it where needed. That is what `_target` does today for `#`; with more characters, every URL and every link target would need it.

### Escape only where Markdown would change the text

| Character | Escaped | Stays as it is |
|---|---|---|
| `\` | before ASCII punctuation | `C:\temp` |
| `*` | unless it has space on both sides | `2 * 3` |
| `_` | unless it is inside a word | `snake_case_name`, `${my_var}` |
| `&` | where it reads as an entity | `R&D`, `&{dict}` |
| `]` | before `(` | `${list}[0]` |
| `~` | next to another `~` | `a~b` |
| `<`, `#` | always, as today | |

Alternative: escape all ASCII punctuation. That is simple, but the raw Markdown of `robotcode doc` becomes hard to read, and `${list}\[0]` is no longer found as a variable.

### Block markers only at the start of the line

`>`, `+`, `-`, `1.`, `1)` and `[x]:` are only special at the start, so only the start of a line is checked. `*` and `#` are already covered above.

This also runs for table cells, where these markers mean nothing. The backslash does not show there, and the formatter stays simpler than with a separate path for cells.

Numbered paragraphs follow from the rule that everything Robot Framework does not read as markup is escaped. Robot Framework has no numbered lists; Libdoc shows them as paragraphs.

### Headings and keyword names use the same escape

`= Section <b> here =` and a keyword named `Run <x> Now` give `## Section <b> here` and `### Run <x> Now` today: Markdown reads `<b>` as HTML and shows nothing, while Libdoc shows the text. Headings get the same escape as other text, and code in them stays, so a name in backticks stays as it is. The anchor of a heading is worked out from its title: links and anchors must keep matching, which the page tests cover. There are no such headings or keyword names in the checked libraries.

### Backticks without a partner are part of the escape

`documentation-code-stays-copyable` escapes them right after the scan. The escape here doubles a backslash before punctuation, so it would break `` \` ``. This escape therefore moves into the final step, so that one pass handles all of them.

### An escaped variable stays one

For `\${name}`, doubling the backslash alone gives `\\${name}`, which `code_span_variables` reads as a backslash plus a variable. So after an odd number of backslashes, `$` gets escaped too: `\\\${name}`. Markdown shows `\${name}`, and the variable step leaves it alone. `\\${name}` stays a backslash plus a variable, as in Robot Framework.

### Variables drop Markdown escapes when they become code

`code_span_variables` removes `\` before ASCII punctuation from the text it puts into a code span. Inside code an escape would show. This is also right for documentation written in Markdown, where `${a\_b}` means `${a_b}`.

Alternative: leave variables unescaped in the formatter. In the hover, which does not make them code, `${_x_}` would then lose its underscores.

## Risks / Trade-offs

- **More backslashes in raw Markdown.** Visible in the output of `robotcode doc` → Of 6669 distinct paragraphs, list items and table cells, 107 change, mostly `\*` in patterns and `1\.`.
- **Markdown in Robot-format documentation stops working.** An author who wrote `[a](b)` and only looked at it in RobotCode sees it as text → It already is text in Libdoc. There are no such places in the checked libraries.
- **Numbered paragraphs lose the list look** on 38 places → They read as in Libdoc, and the text is the same.
- **`marked` links a URL in plain text on its own,** so `[text\](http://x)` shows a clickable URL → The text stays right.

## Checked with a prototype

A prototype in a scratchpad, patched on top of `documentation-code-stays-copyable`, not in the repo:
- In the same 1264 documents, all differences above are gone. What stays are the decided differences in code and URLs in blocks, a few stray backticks that Libdoc shows by accident, and `%TOC%`, which only the page replaces.
- In all 1497 documents with their pages' variable step, markdown-it reads no HTML and no private-use character is left.
- 20 hand-written cases show the same text as Libdoc in markdown-it and in the REPL's renderer, and the same text in marked.
- Existing tests pass: `test_markdownformatter.py`, `test_markdown_docs.py`, `test_dot_commands.py`, `test_library_doc_page.py` and `test_library_doc_rendering.py` on RF 7.5, and the hover and completion tests on RF 7.4. Not the whole matrix.
