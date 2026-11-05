# Design

## Context

See `proposal.md` for the motivation. `packages/repl/src/robotcode/repl/doc_cli.py` holds the `doc` command group. `_load` loads a target like `robot` does, and `keyword` selects keywords by name (lines 573-584) and writes Markdown through `_write_markdown`.

What the keyword documents already have: `KeywordDoc.source` and `KeywordDoc.line_no`, for Python libraries and for resource files. `end_line_no` is `-1` for library keywords, so the last line isn't known.

What was checked on 2026-11-05, in the example project of the AI agents guide:

- For all 404 keywords of `ShopLibrary`, `BuiltIn`, `Collections`, `String`, `OperatingSystem` and `Browser`, the reported line lies between the first decorator and the `def` of a function in the file. So the function can be found with `ast`.
- `robot.parsing.get_resource_model` gives the `Keyword` blocks of `resources/orders.resource` with the same line as the keyword document and an `end_lineno`, which includes the blank lines after the keyword.
- The largest keywords of these libraries have 197 lines, and the median per library is up to 44.
- `Browser`'s class is in `Browser/browser.py`, and `New Page` in `Browser/keywords/playwright_state.py`.

## Goals / Non-Goals

**Goals:**

- One call gives the place and the code of a keyword, or of a whole file.
- The output is short enough to read and exact enough to refer to a line.

**Non-Goals:**

- A search by keyword name without a target.
- Code of a keyword as Robot Framework runs it at the moment, such as with arguments or from a paused run. That stays with the debugger.

## Decisions

### D1: A subcommand of `doc`, with an optional NAME

The maintainer decided against a line in the output of `doc keyword`, because an agent would still get the whole documentation. As a subcommand of `doc`, it takes targets and options the agent already knows, and shares `_load`.

Without a NAME, the command shows the file of the target. The maintainer asked for this, and it needs no second command.

### D2: How the code of a keyword is found

- **Python:** Parse the file with `ast` and take the function whose first decorator or `def` line reaches the reported line, from its first decorator to its `end_lineno`. A docstring belongs to it.
- **Robot Framework files:** Parse the file with `get_resource_model`, with the languages of the command, and take the `Keyword` block with the reported line, without its trailing blank lines.
- **Anything else,** such as a JSON resource file or a library without a Python source, counts as code that can't be shown.

Printing a fixed number of lines, as `.source` does on the plain backend, was the alternative. It would cut long keywords and show the start of the next one, and the check above shows that the exact range is available.

### D3: The Markdown output

A keyword:

````markdown
### Keyword *Greeting*

`libraries/ShopLibrary.py:40`

```python
  39      @keyword
  40      def greeting(self) -> str:
  41          """Returns the greeting the shop shows the user who is logged in."""
  42          return f"Welcome back, {self._user}!"
```
````

The fence names `python` for `.py` and `robot` for Robot Framework files. Several keywords are separated with `---`, as in `doc keyword`. A file has the path without a line as its place, under a heading with the name of the library, resource or suite.

The line numbers are in the code block, as in `.source`, because an agent refers to lines and `results` and `analyze` print `path:line`. For copying code, JSON and the file itself are there. So JSON has `code` without numbers, and `start_lineno` says where it starts.

### D4: The selection is shared with `doc keyword`

The lines that select keywords and collect the names without a match move into a helper that both commands use, and so does the report of those names. So both select the same keywords, and there's no second way of matching.

### D5: Paths

Markdown shows paths relative to the project root when the file is in the project, because that's what the other commands print, and otherwise absolute. JSON has the absolute `source`, as `doc keyword` does. `handle_robot_options` gives the root, and `_load` already calls it.

### D6: What `.source` keeps

`.source` keeps its behavior. Its window and viewer belong to the REPL, and they find keywords from what is imported at runtime. The new command works from a target. Neither calls the other.

## Risks / Trade-offs

- **A whole file can be long: `BuiltIn.py` has 5,417 lines** → That is what the call asks for. The skill names the form with a keyword, and the output is paged on a terminal.
- **`get_resource_model` or `end_lineno` may differ between Robot Framework versions** → The tests run on the whole matrix. Where the block with the reported line isn't found, the code counts as not available.
- **A file changes between loading and reading, or isn't UTF-8** → The code counts as not available, and the error is reported.
- **Agents may keep using `grep`** → That's acceptable: the maintainer considers reading files fine. The eval case only checks that the skill leads to the command when an agent is asked for a keyword's code.
