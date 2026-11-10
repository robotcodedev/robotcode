# Proposal: markdown-suites

## Why

Robot Framework 7.5.1 runs tests and loads resources from the `robot`/`robotframework` code blocks of Markdown files, with line and column numbers of the file. RobotCode reads these files as plain Robot syntax or not at all: a `.robot.md` suite gets no editor support and `analyze code` skips it, and a `Resource    keywords.md` import is read together with its prose and fence lines, so its keywords are not what Robot Framework sees.

## What Changes

- **Markdown as an opt-in format.** It is active on Robot Framework ≥ 7.5.1 for the Markdown extensions (`md`, `markdown`, `robot.md`) that the `extensions` option of the robot.toml profile lists. Robot Framework's default extensions do not switch it on.
- **`robotcode discover info`** reads the configuration with the selected profiles and lists the active document formats with their extensions, so that editors know which files the language server serves.
- **Language server.** It serves the files of the active Markdown extensions as Robot Framework documents, whatever language the client sends. The analysis runs on the data Robot Framework reads from the code blocks, at the positions in the file. Completion and ranges stay inside the blocks, code that code actions place goes into a block, and Robocop checks and formats these files with its own Markdown support (Robocop ≥ 9.2).
- **Markdown resources.** A `Resource` import of a `.md`/`.markdown` file is read like Robot Framework reads it, from its code blocks, on Robot Framework ≥ 7.5.1, whether the format is active or not.
- **`analyze code`** checks the files of the active Markdown extensions in the workspace like `.robot` files.
- **VS Code.** Before it starts a folder's language server, the extension asks `discover info` and sends the files of the active extensions to the server; they keep their Markdown language in the editor.
- **Documentation.** A page on Markdown suites and resources: how to switch them on, what works, the limits.

Not part of this change: reStructuredText, Gherkin and formats of other packages (and hooks for them), PyCharm (Markdown support there is left out for now), discovery and the debugger (Robot Framework 7.5.1 already reports file lines), and the test explorer's refresh when a Markdown file changes.

## Capabilities

### New Capabilities

- `document-formats`: which document formats besides Robot Framework files are active in a project, how `discover info` reports them, and how VS Code hands their files to the language server.
- `markdown-robot-data`: how RobotCode analyses the Markdown files of an active format — which code blocks hold Robot Framework data, positions, where editor features apply, placed code, Robocop and `analyze code`.

### Modified Capabilities

- `markdown-resource-imports`: requirement "Markdown resource imports are accepted on RF 7.5" — on Robot Framework ≥ 7.5.1 an imported Markdown resource is loaded from its code blocks, like Robot Framework does, instead of as raw text.

## Impact

- `packages/robot`: new `document_formats.py` (active formats from the profile) and `utils/markdown_blocks.py` (block scanner with Robot Framework's rule, Robot Framework's Markdown data); `diagnostics/document_cache_helper.py` (document type by active extension, Markdown tokens, tokens of imported Markdown resources).
- `packages/language_server/src/robotcode/language_server`: `robotframework/protocol.py` (language definition and file extensions), `common/parts/documents.py` (language id of served Markdown files), and in `robotframework/parts/`: `robot_workspace.py` (preload), `completion.py`, `folding_range.py`, `selection_range.py`, `document_symbols.py`, `code_action_helper_mixin.py`, `code_action_quick_fixes.py`, `code_action_refactor.py`, `formatting.py`, `robocop_diagnostics.py`.
- `packages/analyze/src/robotcode/analyze/code/robot_framework_language_provider.py` (workspace scan).
- `packages/runner/src/robotcode/runner/cli/discover/`: `discover.py`, `_models.py`, `_render.py` (`info`); `docs/src/content/docs/reference/cli.md` regenerated.
- `vscode-client/extension/languageclientsmanger.ts` (document selector from `discover info`).
- Documentation: a new page; tests for each part.
- No new dependency. Robot Framework's private `MarkdownParser._read_markdown_data` is used in one helper; Robocop's Markdown support needs Robocop ≥ 9.2.
