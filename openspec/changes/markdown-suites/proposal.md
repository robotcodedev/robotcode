# Proposal: markdown-suites

## Why

Robot Framework 7.5 executes tests embedded in Markdown files (`*.robot.md`, and `*.md`/`*.markdown` via `--extension`/`--parseinclude`) and accepts Markdown resources, alongside the reStructuredText support it has had since 3.1. RobotCode only nominally accepts these files: the raw Markdown/reST text is tokenised as Robot syntax, so an imported `keywords.md`/`keywords.rst` resource yields a false "resource is empty" warning and "keyword not found" errors, `.robot.md`/`.robot.rst` suites get no hover, completion, diagnostics or navigation in the editor, `analyze code` silently skips them, `discover files` does not list them, and the test explorer navigates to wrong lines because Robot Framework reports line numbers relative to the concatenated code blocks (an upstream report is planned in `support-rf75`, task 6.1; once filed, its URL is the trigger for switching the remap off).

## What Changes

- **Extraction with file-accurate positions.** A shared helper in the `robot` package extracts the Robot Framework code blocks of Markdown (fenced ```` ``` ````/`~~~` blocks with info string `robotframework`/`robot`, mirroring RF's `MarkdownParser`) and reStructuredText (`code`/`code-block`/`sourcecode` directives with `robotframework`, via docutils like RF's reader) files, keeping every non-code line as an empty line and dedenting each block like RF does while recording the removed margin, so tokens, statements and blocks carry the file's own line and column positions. It also provides RF's concatenated text (for parity tests) and the extracted-line → file-line table.
- **Language server.** `.robot.md` (RF ≥ 7.5) and `.robot.rst` are typed as suites, `.md`/`.markdown` (RF ≥ 7.5) and `.rst`/`.rest` as resources, `__init__.md`/`__init__.rst` as init files (RobotCode's decision; RF does so only with a configured extension), `__init__.robot.md` as a suite (RF skips `_`-prefixed files in directory runs); all analysis runs on the extracted text; resource imports of such files resolve their keywords; the extension-detected language id takes precedence over the client-sent one; whole-document edits (formatting, end-of-file quick fixes, text-based refactors) are disabled for embedded documents; Robocop receives the extracted text; missing docutils produces one clear diagnostic instead of an exception; the file watcher covers the new extensions.
- **VS Code.** `.robot.md`/`.robot.rst` keep their Markdown/reST language (preview, Markdown tooling and the existing fenced-block highlighting stay); the language client adds path-pattern document selectors from a new setting (default `**/*.robot.md`, `**/*.robot.rst`), the test explorer, run/debug commands and tools accept these files by pattern in addition to language id.
- **CLI.** `discover` reports file-accurate `lineno`/`range`/ids for tests in embedded suites (remapping RF's block-relative numbers behind one version-gated switch); `discover files` lists `*.robot.md` (RF ≥ 7.5) and `*.robot.rst`; `analyze code` scans them in workspaces and accepts any Markdown/reST file passed explicitly.
- **IntelliJ.** An LSP4IJ file-name-pattern mapping sends `*.robot.md`/`*.robot.rst` to the server as `robotframework`; test-manager refreshes accept them; gutter positions come from the remapped discover output.
- **Documentation.** A page on Markdown/reST suites and resources: the selector setting, docutils not being bundled, and known limitations (no formatting/EOF quick fixes in embedded documents, `__init__.robot.md` is not an init file, debugger breakpoints and run-time markers in embedded suites still use RF's block-relative lines).

Depends on `support-rf75` (Markdown resource extensions, Libdoc guard, `rf75` env). Left for its own follow-up: debugger breakpoint/stack-frame line mapping for embedded suites (`embedded-suites-debugging`). Plain `.md` files are not treated as suites unless RF is configured to parse them (`--extension`/`parse-include`), the selector setting includes them, or they are passed explicitly.

## Capabilities

### New Capabilities

- `embedded-robot-data`: How RobotCode recognises, extracts and analyses Robot Framework data embedded in Markdown and reStructuredText files — document typing, file-accurate positions, editor features, edit guards, resource imports, `analyze`/`discover` behaviour, and the VS Code and IntelliJ associations.
- `markdown-resource-imports`: modifies the requirement "Markdown resource imports are accepted on RF 7.5" introduced by `support-rf75` (not yet archived; `support-rf75` must be archived first) so that Markdown resources are loaded from their code blocks and resolve their keywords instead of being loaded as raw text.

### Modified Capabilities

<!-- markdown-resource-imports is modified, but it exists only as a delta of support-rf75 until that change is archived -->

## Impact

- New `packages/robot/src/robotcode/robot/utils/embedded_code.py`: extraction helper, extension constants, version constants (Markdown on RF ≥ 7.5; remap switch).
- `packages/robot/src/robotcode/robot/diagnostics/document_cache_helper.py`: compound-suffix document typing, tokenisation of extracted text with column shift, access to the block table; `imports_manager.py` and `library_doc.py`: import the extension constants from `embedded_code.py` (the unused `REST_EXTENSIONS` in `imports_manager` is deleted).
- `packages/core/src/robotcode/core/documents_manager.py`: compound-suffix language detection.
- `packages/language_server/.../robotframework/protocol.py` (language definitions, file extensions), `common/parts/documents.py` (language id precedence), `parts/robot_workspace.py` (preload), `parts/formatting.py`, `parts/code_action_quick_fixes.py`, `parts/code_action_refactor.py`, `parts/code_action_helper_mixin.py`, `parts/robocop_diagnostics.py`.
- `packages/analyze/src/robotcode/analyze/code/robot_framework_language_provider.py`, `code_analyzer.py`.
- `packages/runner/src/robotcode/runner/cli/discover/discover.py`: line remapping, `files` filter.
- `vscode-client/extension/languageclientsmanger.ts`, `testcontrollermanager.ts`, `debugmanager.ts`, `languageToolsManager.ts`, `keywordsTreeViewProvider.ts`, `package.json` (setting, activation events, enablement/menus).
- `intellij-client/src/main/resources/META-INF/plugin.xml`, `src/main/kotlin/.../testing/RobotCodeTestManager.kt` (and optionally `EditorNotificationProvider.kt`).
- Docs: new page under `docs/`; `docs/03_reference/discovering-tests.md` (`lineno` semantics for embedded suites, `files`); `docs/03_reference/cli.md` regenerated for the changed `discover files` help.
- Tests: extraction unit and RF-parity tests, `test_document_cache_helper.py`, namespace/import tests, new LS regression data files (`embedded_markdown.robot.md`, `embedded_rest.robot.rst`) with baselines, discover and analyze acceptance tests; manual checklist for the clients.
