# Proposal: markdown-suites

## Why

Robot Framework 7.5.1 runs tests and loads resources from the `robot`/`robotframework` code blocks of Markdown files, with line and column numbers of the file. RobotCode reads these files as plain Robot syntax or not at all: a `.robot.md` suite gets no editor support and `analyze code` skips it, and a `Resource    keywords.md` import is read together with its prose and fence lines, so its keywords are not what Robot Framework sees.

## What Changes

- **Markdown files as Robot Framework parses them.** On Robot Framework ≥ 7.5.1, RobotCode serves the Markdown files (`md`, `markdown`, `robot.md`) that Robot Framework parses with the selected profiles: `.robot.md` by Robot Framework's default extensions, the Markdown extensions of `extensions` when that option replaces the defaults, and the extension of a `parse-include` pattern, whose patterns also limit the files.
- **`robotcode discover info`** reads the configuration with the selected profiles and lists the document formats Robot Framework parses with them (`robot`, `rest`, `json`, `markdown`), with their extensions, so that editors know which Markdown files the language server serves.
- **Language server.** It serves these Markdown files as a language of its own, `robotframework-markdown`, next to Robot Framework, whatever language the editor sends for them: the features that work on them as they are accept both languages, and the Markdown behaviour lives in parts of its own. The analysis runs on the data Robot Framework reads from the code blocks, at the positions in the file. Completion and ranges stay inside the blocks, code that code actions place goes into a block, and Robocop checks and formats these files with its own Markdown support (Robocop ≥ 9.2).
- **Markdown resources.** A `Resource` import of a `.md`/`.markdown` file is read like Robot Framework reads it, from its code blocks, on Robot Framework ≥ 7.5.1, whether the format is active or not.
- **`analyze code`** checks these Markdown files in the workspace like `.robot` files, through a Markdown provider of its own.
- **VS Code.** Before it starts a folder's language server, the extension asks `discover info` and sends the files of the Markdown format's extensions to the server; they keep their Markdown language in the editor. Breakpoints can be set in the Markdown files the language server serves.
- **Documentation.** A page on Markdown suites and resources: which files RobotCode serves, what works, the limits.

Not part of this change: reStructuredText, the JSON format (`.rbt`), Gherkin and formats of other packages (and hooks for them), PyCharm (Markdown support there is left out for now), discovery and the debugger itself (Robot Framework 7.5.1 already reports file lines), and the test explorer's refresh when a Markdown file changes.

## Capabilities

### New Capabilities

- `document-formats`: which document formats besides Robot Framework files are active in a project and which of their files RobotCode serves, how `discover info` reports them, and how VS Code hands their files to the language server.
- `markdown-robot-data`: how RobotCode analyses the Markdown files it serves — which code blocks hold Robot Framework data, positions, where editor features apply, placed code, Robocop and `analyze code`.

### Modified Capabilities

- `markdown-resource-imports`: requirement "Markdown resource imports are accepted on RF 7.5" — on Robot Framework ≥ 7.5.1 an imported Markdown resource is loaded from its code blocks, like Robot Framework does, instead of as raw text.

## Impact

- `packages/core`: `language.py` (an optional file condition of a language definition) and `documents_manager.py` (language detection for extensions of more than one part and with the file condition).
- `packages/robot`: new `document_formats.py` (active formats, the files Robot Framework parses and the Markdown language definition from the profile) and `utils/markdown_blocks.py` (block scanner with Robot Framework's rule, Robot Framework's Markdown data); `diagnostics/document_cache_helper.py` (reader by language, Markdown tokens, tokens of imported Markdown resources); `diagnostics/imports_manager.py` (gate).
- `packages/language_server/src/robotcode/language_server`: `robotframework/protocol.py` (Markdown language definition, file extensions, Markdown parts); new `robotframework/parts/markdown/` (completion, ranges, placed code, Robocop); in `robotframework/parts/`: the gates of the shared handlers, `robot_workspace.py` (preload), an overridable range step in `folding_range.py`, `document_symbols.py` and `selection_range.py`, the placement event in `code_action_helper_mixin.py` and `code_action_quick_fixes.py`.
- `packages/analyze/src/robotcode/analyze/code/`: new `markdown_language_provider.py`; `language_provider.py` and `code_analyzer.py` (language definitions from the profile); `robot_framework_language_provider.py` (gate).
- `packages/runner/src/robotcode/runner/cli/discover/`: `discover.py`, `_models.py`, `_render.py` (`info`); `docs/src/content/docs/reference/cli.md` regenerated.
- `vscode-client/extension/languageclientsmanger.ts` (document selector from `discover info`, the context key for breakpoints in Markdown files) and `package.json` (breakpoints in Markdown files).
- Documentation: a new page; tests for each part.
- No new dependency. Robot Framework's private `MarkdownParser._read_markdown_data` is used in one helper; Robocop's Markdown support needs Robocop ≥ 9.2.
