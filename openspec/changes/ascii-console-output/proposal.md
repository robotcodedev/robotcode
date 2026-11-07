# Proposal

## Why

On Windows, Python writes to a pipe or a file in the ANSI code page (cp1252 for Western Europe) and stops with `UnicodeEncodeError` at the first character the code page lacks. robotcode's own text has many: the status icons ✅❌, `→` in `results diff`, 😥 in `config` and `profiles`, `—`, `·` and `…` in headings, tables and help texts. So `robotcode results summary` exits with 128 and prints nothing whenever a CI step or an AI agent captures it (#683), even for a run whose names are plain ASCII.

## What Changes

- robotcode composes the text it writes to the console from ASCII only:
  - help texts and messages;
  - headings, tables, status markers and separators;
  - the REPL's text output and the help of its dot-commands;
  - the decoration of `robotcode doc`.
- Status icons are dropped; the bold status name stays (`**FAIL**`). 😥 is dropped.
- ASCII equivalents replace the rest: `->` for `→`, `...` for `…`, `, ` for `·`, `: ` or ` - ` for `—` in headings and item lines, sentences rewritten where `—` joined clauses, `-` for box-drawing lines and empty values, `+/-` for `±`.
- `--format json` writes every character outside ASCII as a `\u` escape, so JSON output works on any stream encoding without losing anything.
- With `--color` on a stream whose encoding is not UTF, robotcode writes the Markdown without colors, because rich's own bullets and quote bars can't be encoded there.
- `robotcode doc` marks argument kinds with ASCII on the console; the hovers of the language server keep 🏷 and `⟶`.
- What comes from the user's data stays as it is: names, messages, metadata, paths and library documentation. The guide says how to get UTF-8 output for it (`PYTHONUTF8=1`, the default from Python 3.15 on).
- The guide's example outputs are updated, and `reference/cli.md` is regenerated.

## Capabilities

### New Capabilities

- `cli-ascii-output`: the characters of the text robotcode writes to the console, the JSON escapes, and the plain output with `--color` on a stream that can't take Unicode.

### Modified Capabilities

- `results-compare`: per-group values are separated by `, ` instead of ` · `.
- `results-html-messages`: an embedded file is shown as `_(embedded <link text> - see artefacts)_`.
- `keyword-documentation-rendering`: `robotcode doc` writes the return description as `` `T` - description `` on the console; hovers keep `—`.

## Impact

- `packages/runner/src/robotcode/runner/cli/` (`_markdown.py`, `results/`, `discover/`), `src/robotcode/cli/` (`config`, `profiles`, root options), `packages/analyze/src/robotcode/analyze/` (`cache`, `code`, `dump_model`), `packages/repl/src/robotcode/repl/` (`cli.py`, `console_interpreter.py`, `doc_cli.py`), `packages/plugin/src/robotcode/plugin/__init__.py` (`print_data`, `echo_as_markdown`), `packages/robot/src/robotcode/robot/diagnostics/library_doc.py` (ASCII decoration for `robotcode doc`).
- Tests that assert the old characters; new tests that run the commands with an ASCII stdout.
- `docs/src/content/docs/guides/cli/analyzing-results.md`, `getting-started/command-line.md`, `guides/tips/variable-not-found.md` and other pages with example output; `reference/cli.md`.
- Not affected: the language server and the debug adapter (UTF-8 by protocol), the prompt_toolkit interface of the REPL, `robotcode robot`'s Robot Framework output.
