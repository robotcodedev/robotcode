# Tasks

## 1. Results, discover and the Markdown helpers

- [x] 1.1 In `packages/runner/src/robotcode/runner/cli/`, replace every non-ASCII character of the output by D2:
  - `_markdown.py`: drop the status icons, so `bold_status` writes `**FAIL**`; `·` in the timing suffix;
  - `results/_render.py`: headings, `→`, `—`, `·`, `…`;
  - `results/_html.py`: `_(embedded … - see artefacts)_`;
  - `results/results.py` and `discover/discover.py`: help texts, messages and the cut marker of `_truncate`.

  In a new `tests/robotcode/runner/cli/results/test_ascii_output.py`, cover in-process that `summary`, `show`, `log`, `stats`, `diff` and `compare` with every `--show` view, and `discover`, write only ASCII for ASCII test data. Cover the scenarios "Status as a name" and "ASCII equivalents" (diff `**PASS** -> **FAIL**`, `# Summary: output.xml`, `...`, `_(23:51:01, 1 ms)_`), "User data as it is", the MODIFIED scenarios of `results-compare` (`0/5, 4/5`) and `results-html-messages` (`_(embedded hello.txt - see artefacts)_`). Change the existing tests that assert the old characters. Verify that the new tests pass with the change and fail without it.
- [x] 1.2 In `tests/robotcode/cli/test_exit_codes.py` or a new subprocess test, run `robotcode results summary --failed` with `PYTHONIOENCODING=cp1252` (the #683 case) and check exit 0 and ASCII output. Verify that it fails without 1.1.
- [x] 1.3 Produce the example outputs of `docs/src/content/docs/guides/cli/analyzing-results.md`, `getting-started/command-line.md` and `guides/cli/discovering-tests.md` again with the new output. Add the note of D8 on encodings to `analyzing-results.md`, and change `· ` in its `compare` section to `, `. Regenerate `reference/cli.md` with `hatch run create-cmd-line-docs`. Verify in the docs dev server that the pages render, and that the shown output matches a real run.

## 2. JSON escapes

- [x] 2.1 Give `as_json` in `packages/core/src/robotcode/core/utils/dataclasses.py` an `ensure_ascii` argument, `False` by default, and pass `True` from `Application.print_data` for `json` and `json_indent`, from the JSON reports of `analyze code`, and from `analyze`'s model dump (D4). Cover "JSON with escapes" in a subprocess test: `--format json results show` with a test `Grüße ✓` under `PYTHONIOENCODING=cp1252` exits with 0 and the parsed name is `Grüße ✓`. Check that the JSON-RPC and DAP tests pass unchanged. Verify that the new test passes with the change and fails without it.
- [x] 2.2 Say in the JSON reference of `analyzing-results.md` that characters outside ASCII come as `\u` escapes, and check the page in the dev server.

## 3. Colors on a stream that can't take Unicode

- [x] 3.1 In `Application.echo_as_markdown`, take the plain path when the encoding of rich's console is not a UTF encoding (D6). Cover "Colors only on a stream that takes Unicode" with a subprocess test of `robotcode --color results summary` under `PYTHONIOENCODING=cp1252`, and adjust `tests/robotcode/plugin/test_echo_as_markdown.py` if it pins the old path. Verify that the test passes with the change and fails without it.

## 4. Root CLI, config, profiles and analyze

- [x] 4.1 Replace the non-ASCII characters by D2 in `src/robotcode/cli/` (the help of the root options, 😥 in `commands/config.py` and `commands/profiles.py`) and in `packages/analyze/src/robotcode/analyze/` (`cache/cli.py`: `—` as empty value, `─` lines, `·`; `code/cli.py`: help text). Cover the scenario "No project found" and the `analyze cache` output in tests. Change the existing tests that assert the old characters (`tests/robotcode/analyze/test_cache_cli.py`, `test_dump_model_cli.py`, and others found by the test run). Verify that the tests pass.
- [x] 4.2 Add a test that walks the Click tree of the root group in-process and checks that the help of every command and subcommand is ASCII ("Help of every command"). Verify that it fails before every group's help texts are fixed (it lists the commands it finds) and passes after them.
- [x] 4.3 Produce the example outputs of `guides/cli/analyzing-code.md` again if they show robotcode's output, regenerate `reference/cli.md`, and check the pages in the dev server.

## 5. REPL text output and dot-command help

- [x] 5.1 Replace the non-ASCII characters by D2 in `packages/repl/src/robotcode/repl/cli.py` (help texts) and `console_interpreter.py`:
  - messages;
  - the `.help` listing with ` - ` between command and description, and `, ` between the shortcuts;
  - the stop line;
  - the docstrings of the dot-command methods, which `.help` shows, with `+/-` for `±`.

  Leave the prompt_toolkit interface (`_pt/`) as it is. Cover "Help of the dot-commands" in a subprocess test: `robotcode repl` with piped input `.help`, then `.help <name>` for every dot-command, under `PYTHONIOENCODING=ascii` exits normally and writes only ASCII. Change the existing REPL tests that assert the old characters. Verify that the new test passes with the change and fails without it.
- [x] 5.2 Produce the example outputs of `guides/cli/repl.md` and `guides/cli/robot-debug.md` again where they show robotcode's output. Leave the recorded agent sessions of the AI agents guide as they were recorded. Regenerate `reference/cli.md` and check the pages in the dev server.

## 6. robotcode doc

- [x] 6.1 Give `library_doc.py`'s signature and Markdown builders the ASCII decoration of D5, and use it in `packages/repl/src/robotcode/repl/doc_cli.py`:
  - `/` and `*` markers as in Libdoc;
  - no 🏷, `⟶` or zero-width joiner;
  - the return line `**Return Type**: \`T\` - description`;
  - `—` in `doc_cli.py`'s keyword list as ` - `.

  Cover "Argument kinds in robotcode doc" with a library keyword `pick_rows(table, /, column, *names, limit: int = 10, **options)` for `doc keywords` and `doc keyword`, the MODIFIED return-line scenario of `keyword-documentation-rendering` for the console, and a hover test that still shows `⟶` and `🏷`. Verify that the new tests pass with the change and fail without it, and that the existing hover and signature-help tests pass unchanged.
- [x] 6.2 Produce the example outputs of `guides/cli/browsing-documentation.md` again where they show signatures, regenerate `reference/cli.md`, and check the page in the dev server.

## 7. Whole change

- [x] 7.1 Run the inventory of non-ASCII string literals over the files in scope again (output strings and output docstrings), and check that only data, the excluded areas of the design and comments remain.
- [x] 7.2 Run `hatch run lint:all`, `npm run lint` and `hatch run test:test`, and report failures with their output.
- [x] 7.3 On the Windows VM (ask the user to start it), run the probe of #683 again with the change. Writing to a pipe in cp1252, `results summary --failed` for ASCII names, `--format json results show` and `--color results summary` exit with 0, and the test name `Grüße ✓` comes through in JSON. The text output of `Grüße ✓` stays Python's business and works with `PYTHONUTF8=1`. Record the results in the report.

## Workflow follow-up

- Commit only on request. Suggested: one `fix(...)` commit per area (runner, core/plugin for JSON and colors, cli and analyze, repl, robot for `doc`), the last with `Fixes #683`; the plan as `docs(openspec)`. Not marked breaking; that is the user's call.
- After the push, comment on #683 only on request.
- Archive with `/opsx:archive` after the review, then `openspec validate --specs --strict`.
