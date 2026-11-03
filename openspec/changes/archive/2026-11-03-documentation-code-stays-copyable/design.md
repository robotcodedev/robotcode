# Design: documentation-code-stays-copyable

## Context

See proposal.md, section Why, for the problem.

**How the formatter works today** (`packages/robot/src/robotcode/robot/utils/markdownformatter.py`):
- `LineFormatter` handles paragraphs, list items and table cells. It runs over the whole line in this order: escape `<`, escape `#`, bold, italic, code, links. The code step only turns double backticks into single ones, so the text of a span changes before and after it.
- With a name linker, names in single backticks become links first. A link waits behind a placeholder (`N`), so the other steps cannot change it. The name pattern also matches inside double backticks.
- `PreformattedFormatter` writes a ` ```text ` block and only calls `LinkFormatter.remove_link`. Bold, italic, names and double backticks stay as written.
- `markdown_docs.code_span()` already writes a code span with a fence longer than any run of backticks in it.

**What Libdoc does** (real runs on RF 7.4 and 7.5). It runs the same steps and nests the results inside `<code>` and `<pre>`:

| Docstring | Libdoc |
|---|---|
| ``` ``vscode/<n>`` ``` | `<code>vscode/&lt;n&gt;</code>` |
| ``` ``a *b* c`` ``` | `<code>a <b>b</b> c</code>` |
| ``` ``see http://x now`` ``` | `<code>see <a href=…>…</a> now</code>` |
| ``` ``see [a\|b] now`` ``` | `<code>see <a href="a">b</a> now</code>` |
| ``` ``x `Noop` y`` ``` | `<code>x <a class="name">Noop</a> y</code>` |
| `` `Noop` `` in a `| ` block | a link without backticks |
| `*** Test Cases ***` in a `| ` block | `<b>*</b> Test Cases <b>*</b>` |

Robot Framework's format has no way to say which language a preformatted block holds. It can contain Robot Framework code, JavaScript, JSON or anything else.

It has no way to escape a backtick either. Libdoc replaces every pair in a line with `` re.sub("`(.+?)`", …) ``. A backslash and `&#96;` stay visible, and a single backtick in a line stays as it is. As a side effect of that pattern, three backticks in a row show as one: ```` ```date``` ```` gives `` `date` ``.

**What real documentation contains.** Browser 21.0.0, SeleniumLibrary, SSHLibrary, DatabaseLibrary, RequestsLibrary, and the standard libraries of RF 7.4 without Telnet; the standard libraries of RF 7.5 are written in Markdown.
- 4113 code spans: 3 hold a URL, all in Browser; none holds bold, italic or `[a|b]`.
- About 1200 distinct lines in preformatted blocks: 355 hold names in single backticks and 25 hold double backticks, partly the same lines; 1 holds a link; 6 are headers like `*** Settings ***`.
- The 364 names in those blocks are 356 keywords of the same library, 6 of another checked library, and in SSHLibrary one library name and one user keyword. No JavaScript or shell in backticks.

## Goals / Non-Goals

**Goals:**
- What a reader copies from code can be pasted without rework.
- One rule for code spans and preformatted blocks, on every surface.

**Non-Goals:**
- Same formatting as Libdoc inside code. A URL in code is not clickable.
- Telling Robot Framework code from other code. Blocks stay ` ```text `.
- Plain text outside of code, including where Markdown reads it differently from Libdoc, such as `1. ` becoming a list.
- Headings, documentation in Markdown or reStructuredText.

## Decisions

### Code leaves the line before the other formatting

`LineFormatter.format` takes every code span out of the line first and puts it behind the placeholder the name links already use. The other steps then cannot touch it, and bold around code still works: ``` *bold ``<a>`` bold* ``` gives `` **bold `<a>` bold** ``. This also stops the name linker from reaching into double backticks. The code step leaves the chain of formatters.

Alternative: make each step skip code spans. That repeats the same check in five places.

### What we write as code, Markdown has to read as code

A backslash can't protect `<` inside code, so the text of code is only safe if Markdown really reads it as code. Two passes find it:
1. Robot Framework's own code pattern, unchanged. It decides first, over the whole line, so ``` ``a``b`` ``` stays one span as in Libdoc, and an unpaired ``` `` ``` before ``` ``a`` ``` cannot take its opener.
2. A scan of the rest, left to right, with three branches: a backslash and the character after it, which Markdown reads as an escape and which stay as they are; a run of backticks up to the next run of the same length, which is how Markdown reads a code span (`` `<x>` ``, ``` ``<a>``s ```); and a run without a partner, whose backticks get escaped, or Markdown would pair them with the code written here. A span can't reach across code that is already held.

A span of single backticks with a link target from the name linker becomes the link, as today, and everything else stays code.

Alternative: only Robot Framework's code pattern, as the issue describes. `` `<div data-automation="automation-id-2">` `` in SeleniumLibrary would keep its backslash.

### One helper gives the text of code

A helper applies `remove_link` and drops the backticks of names. Code in double backticks and single-backtick spans go through it and are written with `code_span()`. That also fixes ``` ``a`b`` ```, which today falls apart into `` `a`b` ``.

Other backtick runs stay exactly as written. For Robot Framework they are no code at all, and Libdoc shows stray backticks there: ``` ``<a>``s ``` becomes ``<span class="name">`&lt;a&gt;</span>`s``. Copying that accident has no value.

### Blocks drop what the whole block makes redundant

`PreformattedFormatter` removes double backticks with Robot Framework's code pattern, then applies the same helper. `*` and `_` stay.

Three backticks in a row become one, as the last step, so that the result cannot pair up as a name. This is the only way an author can keep backticks in a block, such as ``const s = ```Hello ${name}```;``, and it gives the same text as Libdoc. It relies on a side effect that Robot Framework does not document. There are no such lines in the checked libraries. Only exactly three count: longer runs depend on what follows them in Libdoc and stay as written.

### `remove_link` touches only links

Today it runs on every token of the line, so `| a | b [x|y] c | d` becomes `byd`. It now handles only the link tokens, the way `format_link` already separates them.

Its image branch goes too. `[Title|image.png]` writes `![Title](image.png)` as text into the block, which nobody can paste. The rule `[url|text]` → `text` gives `image.png`; there are no real occurrences. `[image.png|Title]` keeps giving `Title`. A link without text gives its target, as `_get_link` and Libdoc do: `[,|]` gives `,`.

### Fences

`code_span` takes the shortest fence that no run of backticks in the text has, so ``` ``True``/``False`` ``` stays `` `True``/``False` `` as before. The fence detection in `markdown_docs` and in argument descriptions follows CommonMark: a backtick fence has no other backtick on its line, so `` ```x``` y `` is no code block. A preformatted block takes a fence longer than any run of backticks in it, or a line of four would end it.

### The viewer finds the heading, not a code line

Without backticks, a block line can read exactly like the next heading, and the REPL's viewer finds headings by comparing text. Per heading, it now skips as many matches as code blocks since the heading before it have such lines. `Start Coverage` in Browser ends its example with `` `Stop Coverage` ``.

### Rejected: splitting code spans around links and bold

Ending the span around a nested part gives the look of Libdoc: `` `see `[`http://x`](http://x)` now` ``. A prototype matched Libdoc per character in 40 of 49 cases, in markdown-it and marked. It was rejected because Robot Framework's formatting inside code is not worth keeping: code has to be copyable. It would also need about twice the code for 3 URL spans in real documentation.

### Rejected: everything in code strictly as written

Browser's real line ``` `Wait For Response`   [https://…|response] => … ``` would then show the link markup, where today it shows `response => …`, and 355 lines would keep their backticks. All of that needs rework after copying.

## Risks / Trade-offs

- **Other code in a block loses backticks.** A JavaScript template string or `` `date` `` in a block is read as a name → This is what Libdoc shows too, so authors already see it there and can write three backticks instead. The checked libraries have no such case.
- **Robot Framework changes its pattern.** Three backticks would then show differently in Libdoc → They stay one in RobotCode until someone notices; a test pins it.
- **Literal `[a|b]` in code becomes `b`.** A regular expression, for example → Also what Libdoc shows. There are no such spans in the checked libraries, and the one real block hit is an intended link.
- **`*bold*` in code shows its asterisks,** where Libdoc shows bold → Intended. This keeps `*** Test Cases ***` intact, which Libdoc breaks.
- **Blocks written for Libdoc look odd.** Browser writes `***** *Variables* *****`, which Libdoc shows as `*** Variables ***` → They stay as written. Robot Framework still parses them as the section.
- **The placeholder characters in a documentation itself** would read as placeholders → A documentation's own U+E000 is held first, like code, and comes back last.
- **Cases that stay as they are.** Each needs input that the checked libraries don't have: a variable directly before a span that Robot Framework does not read as code (`` ${v}``<x>`` ``), code in a link target (``[``my file``|text]``, broken in Libdoc too), runs that Libdoc pairs differently (`` | `a``` ``), a block inside an argument description. Backslashes in plain text belong to `documentation-text-keeps-its-characters`.

## Checked with a prototype

A prototype in a scratchpad, patched into the formatter, not in the repo:
- All 4113 code spans and 1180 of 1193 distinct block lines show the same text as Libdoc. The other 13 hold `*`, such as `*** Settings ***`.
- `test_names_in_headings_and_preformatted_text_stay` fails, as expected. The other tests in `test_markdownformatter.py`, `test_markdown_docs.py` and `test_dot_commands.py` pass on RF 7.5, and the hover, completion, viewer and Markdown server tests pass on RF 7.4. Not the whole matrix.
- The baselines of all RF versions contain no escaped code span and no `text` block.
