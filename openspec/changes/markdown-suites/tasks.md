# Tasks: markdown-suites

## 1. Formats and Markdown data (`robotcode-robot`)

- [ ] 1.1 Create `packages/robot/src/robotcode/robot/document_formats.py` (D1: `DocumentFormat`, `MARKDOWN_SUPPORTED`, `active_document_formats(profile)`); verify with `tests/robotcode/robot/test_document_formats.py`: `robot:robot.md`, `robot:MD`, `.md`, `robot:md:markdown`, an expression value, no `extensions`, and the version gate (no format below Robot Framework 7.5.1)
- [ ] 1.2 Create `packages/robot/src/robotcode/robot/utils/markdown_blocks.py` (D2: `RobotBlock`, `find_robot_blocks`, `read_markdown_data`); verify with `tests/robotcode/robot/utils/test_markdown_blocks.py`: ``` and ~~~ fences, a longer closing fence, letter case and further words of the info string, indented fences, an unclosed block, a block with only empty lines, other-language fences, a robot fence inside a python fence (opens a block, like Robot Framework), CRLF fixtures written with `write_bytes`; and a parity test (skipped below 7.5.1) that every line Robot Framework keeps lies in a found block and that the block lines equal Robot Framework's lines
- [ ] 1.3 Extend `diagnostics/document_cache_helper.py` (D3): document type from the active extensions, Markdown tokens with column offsets in the three tokenisers, tokens of imported `.md`/`.markdown` resources from Robot Framework's data on ≥ 7.5.1, and access to a document's blocks; verify with `tests/robotcode/robot/diagnostics/test_document_cache_helper.py` (typing incl. `__init__.md` and `__init__.robot.md`, the indented-block position of the spec) and a namespace test that a `.robot` suite importing `keywords.md` resolves `Greet` without `extensions`, with the definition at its file line, and does not offer the prose line as a keyword

## 2. Language server

- [ ] 2.1 Language id, language definition, file extensions and workspace preload from the active formats (D3: `robotframework/protocol.py`, `common/parts/documents.py`, `parts/robot_workspace.py`); verify with language-server tests that a `.robot.md` document opened with the language id `markdown` gets diagnostics, and that the preload of a folder with `README.md` and `shop.robot.md` (only `robot.md` active) opens only `shop.robot.md`
- [ ] 2.2 Completion only on block lines and ranges inside blocks (D4: `parts/completion.py`, `folding_range.py`, `selection_range.py`, `document_symbols.py`); verify with tests for completion in prose, on an empty line of a block and in a block with only an empty line, and for the folding and symbol range of a keyword followed by prose
- [ ] 2.3 Block-aware placement in `parts/code_action_helper_mixin.py`, `code_action_quick_fixes.py` and `code_action_refactor.py` (D4); verify with tests that "Create Keyword" inserts a new keyword section before the closing fence of the last block, that an existing keyword section in the first block gets the keyword before its closing fence, and that "Create suite variable" and "Extract keyword" leave prose and fences unchanged
- [ ] 2.4 Robocop's Markdown support in `parts/robocop_diagnostics.py` and `parts/formatting.py` (D5); verify with tests that empty prose lines get no Robocop finding, that formatting changes `    Log      badly   spaced` and leaves prose and fences unchanged, and, with the Robocop version patched below 9.2, that formatting returns no edit with the message and the linter reports nothing for the file
- [ ] 2.5 Add a language-server test data folder with its own robot.toml (`extensions = "robot:robot.md"`) and a `.robot.md` file with marker lines at column 0 inside non-indented blocks, served by its own server like the existing topic groups, and a test module for hover, definition, references, semantic tokens and document symbols; record the baselines with `hatch run test.rf75:test-reset <module>` (none below RF 7.5); verify that `git status` shows only the new baseline files, that they show file positions, and that `hatch run test:test -- tests/robotcode/language_server` passes

## 3. CLI

- [ ] 3.1 `discover info` (D6: `discover.py`, `_models.py`, `_render.py`), with its help text mentioning the formats; regenerate `docs/src/content/docs/reference/cli.md` with `hatch run create-cmd-line-docs` and keep only the `discover info` hunk; verify with acceptance tests in `tests/robotcode/runner/cli/discover/` (`tmp_path` projects): `documentFormats` for `extensions = "robot:md"`, none without `extensions`, the format from a selected profile, and a failing command for an unreadable robot.toml
- [ ] 3.2 `analyze code` scan (D8); verify with a test under `tests/robotcode/analyze/code/` that a `tmp_path` project with `extensions = "robot:robot.md"`, `shop.robot.md` calling an undefined keyword and `README.md` reports "keyword not found" for `shop.robot.md` and analyses one file

## 4. VS Code

- [ ] 4.1 Selector from `discover info` in `vscode-client/extension/languageclientsmanger.ts` (D7), as a pure function with a unit test in `vscode-client/test/`; verify with `npm run lint`, `npm run compile`, `xvfb-run -a npm test`, and in the isolated VS Code harness (without the agent environment variables) that `shop.robot.md` shows a hover inside a block and none in the prose, and none after `extensions` is removed and the server has restarted

## 5. Documentation

- [ ] 5.1 Add a page on Markdown suites and resources under the guides (place chosen by the groups in `CONTRIBUTING.md`): switching the format on with `extensions`, Markdown resources without configuration, what works in VS Code, the limits (PyCharm not yet, Robocop reads blocks on their own, `__init__.robot.md`, no test-explorer refresh on changes of Markdown files); name Markdown files in "Finding Robot Files" (`docs/src/content/docs/guides/robot-toml/ignoring-files.md`) where it lists `.robot` and `.resource`; verify with `npm run docs:build` and a look at the page in `npm run docs:dev`

## 6. Integration

- [ ] 6.1 Run `hatch run lint:all` and `hatch run test:test` and confirm both pass
