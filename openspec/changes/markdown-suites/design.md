# Design: markdown-suites

## Context

See proposal.md for the motivation. Verified facts (Robot Framework 7.5.1, Robocop 9.3.0 and 9.4.0, RobotCode main of 2026-11-10):

- **Robot Framework.** `MarkdownParser` serves `md`, `markdown` and `robot.md`. Its private `_read_markdown_data(reader)` (identical on master) returns the file's lines with every line outside a robot block and both fence lines blanked, block lines dedented by `min(indent, fence indent)`, and the column offsets of the dedented lines; blocks and empty lines in blocks cannot be recovered from it. Block rule: open `(\s*)(`{3,}|~{3,})\s*(\S+)` with `robot`/`robotframework` (case-insensitive), close at a line of only the same character, at least as many; unclosed runs to the end; other fences are not tracked. `ResourceFileBuilder` picks `MarkdownParser` by suffix, whatever `--extension` says. The default extensions include `.robot.md`; `--extension` replaces them. `__init__.robot.md` is not an init file (robotframework/robotframework#5853, open).
- **RobotCode.** `DocumentsCacheHelper` types documents by single suffix (`.robot`, `.resource`, `__init__.robot`) and tokenises `document.text()` with `robot.api.get_*_tokens`; imported resources always go through `get_resource_tokens` on the raw text. 39 handlers in 21 language-server modules are gated on the language id `robotframework`, which the client sends (VS Code sends `markdown` for `.robot.md`). The language server, `analyze code` and `discover` already load the robot.toml profile; the language server gets it at start and VS Code restarts it when the robot.toml changes. `discover info` reads no configuration. `analyze code` scans `.robot`/`.resource`. Robocop gets RobotCode's model (`SourceFile(path, config, _model=model)`), formatting uses `format_until_stable`.
- **Robocop ≥ 9.2** supports Markdown itself: `EmbeddedSourceFile` builds one model per block, translates positions and leaves prose untouched; `reload_model()` builds the models from the given `_source_lines`, so unsaved editor text works; `RobocopFormatter.format_embedded` formats each block alone (its own `format_file` calls it for embedded files, and then saves). Given RobotCode's model instead, Robocop treats the file as plain Robot data: findings in the prose and formatting that drops the prose. Robocop reads each block on its own, Robot Framework reads them as one text: a block that continues a test gets `*** Comments ***` inserted when formatting, and the linter reports `can-be-resource-file` and `not-allowed-char-in-filename` for such files (measured, left to Robocop).
- **VS Code.** The client's document selector is language-based; `PythonManager.executeRobotCode(folder, args, profiles, format)` runs CLI commands with the folder's interpreter.
- **Semantic model.** Both analyzers work on the model built from the tokens, so Markdown tokens reach both without analyzer changes.

## Goals / Non-Goals

**Goals:**
- The same blocks and positions as Robot Framework.
- One function decides the active formats, for `discover info`, the language server and `analyze code`.
- RobotCode's own edits never touch prose or fence lines.

**Non-Goals:**
- Format classes or hooks for other packages (the format interface is only as large as Markdown needs).
- Changing how Robocop reads blocks.
- The test explorer, run and debug commands for Markdown files in VS Code.

## Decisions

### D1: Active formats from the profile, in `robotcode-robot`

`packages/robot/src/robotcode/robot/document_formats.py` holds a `DocumentFormat` dataclass (name, extensions), `MARKDOWN_SUPPORTED = RF_VERSION >= (7, 5, 1)` at module scope, and `active_document_formats(profile)`, which splits the evaluated `extensions` option at colons, normalises each entry like Robot Framework (lower case, no leading dot) and keeps the Markdown ones. The language server, `analyze code` and `discover info` call it with the profile they already load. Rejected: each consumer reading the robot.toml itself (three rules that can drift).

### D2: Robot Framework's data for the analysis, an own scanner for the block boundaries

`packages/robot/src/robotcode/robot/utils/markdown_blocks.py` provides `read_markdown_data(text)`, the only caller of `MarkdownParser._read_markdown_data`, and `find_robot_blocks(text)`, which returns `RobotBlock` dataclasses (opening and closing fence line, content lines) with Robot Framework's two expressions. Tokens come from `get_tokens`/`get_init_tokens`/`get_resource_tokens` on Robot Framework's data, with the column offset added per line like Robot Framework's `ColumnOffsetUpdater`. A parity test in the Robot Framework matrix keeps the scanner on Robot Framework's rule. Rejected: a CommonMark library such as markdown-it-py, which sees other blocks than Robot Framework (fences in quotes, fences indented by four or more spaces) and adds a dependency; an own extraction of the data, since Robot Framework's method gives its dedent exactly.

### D3: Document type and language id from the active extensions

A document whose name ends with an active extension is typed INIT when it is `__init__.<extension>` and the extension is not `robot.md`, otherwise GENERAL; `__init__.robot.md` stays GENERAL until robotframework/robotframework#5853 changes Robot Framework. The language-server protocol adds the active extensions to its language definition and file extensions (watchers, workspace file operations) and the workspace preload, and gives such documents the language id `robotframework`, whatever the client sends, so that the existing gates apply. Imported `.md`/`.markdown` resources get their tokens from Robot Framework's data on Robot Framework ≥ 7.5.1, also without an active format. Rejected: an own language id that all 39 gates would have to accept.

### D4: Block-aware completion, ranges and placed code

Completion returns nothing when the position is not on a content line of a block (D2's scanner). Folding, selection and symbol ranges of Markdown documents end at the element's last line that is not empty in Robot Framework's data, since the trailing empty lines there are prose or fence lines. `create_insert_keyword_workspace_edit` and the variable-section insertion of "Create suite variable" compute block-aware positions: after the last non-empty line of the target section, or, for a new section, before the closing fence of the last block (at the end of the file for an unclosed block). Rejected (by the user): not offering these code actions for Markdown files.

### D5: Robocop's own Markdown support

For Markdown documents and Robocop ≥ 9.2, the Robocop parts build `EmbeddedSourceFile(path=…, config=…, _source_lines=<document lines>)` and call `reload_model()`; the linter runs `run_check` on it, formatting calls `format_embedded` and returns one edit for the whole document when the text changed. With an older Robocop the linter skips Markdown documents and formatting shows a message, like the existing one for a missing Robocop. How Robocop reads blocks is Robocop's matter (user decision, 2026-11-10). Rejected: RobotCode formatting each block itself with the section of the block before as context (own code on Robocop's internals).

### D6: `discover info`

`info` loads the configuration through `handle_robot_options`, as `discover files` does, and adds `document_formats: Optional[List[DocumentFormat]]` to `Info` (left out when no format is active); the Markdown text output gets a section for them. A configuration that cannot be read fails the command like the other `discover` commands.

### D7: VS Code

Before it creates a folder's language client, `languageclientsmanger.ts` runs `discover info` with the folder's profiles and JSON output. A pure function turns the formats into selectors `{ scheme: "file", pattern: "<folder path>/**/*.<extension>" }`, added to the existing ones; a failing call is logged and adds nothing. The restart after a robot.toml change runs the query again. Rejected (by the user): reporting the formats in the `initialize` result, which needs a running server and is of no use to other editors.

### D8: `analyze code`

`RobotFrameworkLanguageProvider.collect_workspace_folder_files` also yields the files whose names end with an active Markdown extension; their analysis is the Robot Framework analysis on the tokens of D2. Rejected: an own Markdown language provider, which would duplicate the Robot Framework analysis although only the tokens differ.

### D9: Tests

Unit tests for D1 and D2 (fence variants, unclosed and empty blocks, other-language fences, CRLF fixtures written with `write_bytes`) plus the parity test, skipped below Robot Framework 7.5.1; `test_document_cache_helper.py` for typing and positions; a namespace test for Markdown resources; language-server tests for the language id, preload, completion, ranges, code actions and Robocop, with a test data folder of their own whose robot.toml sets `extensions`, served by its own server like the existing topic groups, with baselines only under `rf75/`; `discover info` and `analyze code` acceptance tests in `tmp_path` projects; a unit test of D7's selector function in `vscode-client/test/` and a check in the isolated VS Code harness.

## Risks / Trade-offs

- [Robot Framework changes `_read_markdown_data` or its block rule] → one helper and the parity test in the Robot Framework matrix show it; the fix goes there.
- [Robocop reads blocks on their own] → Robocop's findings and formatting of continuing blocks differ from Robot Framework; documented as a known limit.
- [`discover info` adds a process start before each language-server start] → one short CLI call per folder; no call when the folder is not taken up.
- [With `md` active, every `.md` file goes to the language server, README files included] → the user chose it in `extensions`; files without blocks yield empty models.
- [`__init__.robot.md` is no init file] → follows Robot Framework until robotframework/robotframework#5853 changes it.

## Migration Plan

Additive and opt-in: nothing changes until a Markdown extension is listed in `extensions`, except that imported Markdown resources are read like Robot Framework reads them on 7.5.1. Rollback: revert.
