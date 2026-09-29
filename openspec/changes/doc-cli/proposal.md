# Proposal: doc-cli

## Why

RobotCode has no command that shows the documentation of a library or resource file the way the project sees it. `robotcode libdoc` hands everything to Robot Framework's Libdoc, which has no options for variables or variable files (`${...}` in `Name::args` stays literal). `robotcode libdoc` also resolves relative paths against the project root instead of the directory it was started in (`packages/runner/src/robotcode/runner/cli/libdoc.py:72`). Before RF 7.5, `libdoc … show` prints raw Robot markup wrapped at 78 characters. Yet the `robotcode` agent skill sends every keyword lookup there.

RobotCode's own full-library Markdown, `LibraryDoc.to_markdown(only_doc=False)`, is used only by the REPL's `.doc` and the unused `type=md` branch of the documentation server. It is not fit to be read, searched or published. The keyword order changes from process to process. Keyword headings sit at the level of the library title. On RF 7.5, `---` separators turn paragraphs into headings (dozens in the BuiltIn page). Data types are missing. Private keywords are shown. The scope reads `Scope.GLOBAL` on RF 7.

## What Changes

- **New command group `robotcode doc`** in `robotcode-repl` (maintainer decision):
  - `doc lib TARGET`: the full documentation of a library, a resource file or the keywords of a suite file.
  - `doc keywords TARGET [PATTERN …] [--tag TAG …]`: an overview of the keywords with name, arguments and short documentation. A pattern selects keywords whose name contains it (`*` and `?` allowed; case, spaces and underscores ignored).
  - `doc keyword TARGET NAME [NAME …]`: the full documentation of keywords, found by exact name, by glob or by a concrete call of an embedded-argument keyword, followed by the data types their arguments use. A name without a match is an error that suggests similar names.
  - `doc browse TARGET`: the full documentation in the REPL's documentation viewer (links, search, back/forward). In AI-agent sessions, in pipes and without a terminal it prints the Markdown instead.
- **Targets like Libdoc:** a library name, a library path, a resource file (RF 7.5 `.md` resources included) or a suite file (maintainer decision), with import arguments appended as `Name::arg1::arg2`. A suite file is documented as Libdoc has done since RF 6.0: its keywords, under the suite's name, with the type `SUITE`. So is a suite initialization file such as `__init__.robot`, under the suite name of its directory, on every RF version (maintainer decision (2026-09-29)).
- **Live generation on every call** (maintainer decision): `robot.toml` and the selected profiles (environment, python path, variables, variable files and, as `robot` uses them, languages) plus `-v`, `-V`, `-P`, `--language` and `--base-dir`. `--language` adds to the configured languages, as the language server adds `robotcode.robot.languages` to them, so that `vscode-doc-browser` can pass that setting (maintainer decision (2026-09-29)); RF 5.0 has no language support and rejects it. No analysis settings and no cache. Relative paths are resolved against the directory the command was started in.
- **Output:** Markdown through RobotCode's terminal output (rendered on a colour terminal, raw in pipes, with `--no-color` and in AI-agent sessions), `-o FILE` for a file, and the global `--format json` with a fixed contract that `vscode-doc-browser` consumes.
- **Failing loads abort like Libdoc** (maintainer decision): a target that cannot be found, imported or initialised with the given arguments produces no documentation, an error and a non-zero exit code. Other load errors go to standard error and the rest is documented.
- **The existing full-page renderer is fixed** (maintainer decision; no new renderer module): keywords sorted by name, a consistent heading hierarchy, blank lines before separators, private keywords left out, a keyword index, a `Data types` section, links from references to types in documentation text to their heading there, and links from Robot-format names in single backticks as in Libdoc (maintainer decisions), but no links from argument names or double-backtick code, also where they equal a type name (maintainer decision (2026-09-29)), GitHub-style anchors, Robot Framework variables in text written as inline code. The REPL's `.doc` shows the fixed page.
- **Fixes for all surfaces:** in the Robot-format converter, a `|` inside a table cell is escaped and link targets no longer contain `\#`. The scope is stored as Libdoc names it (`GLOBAL`), which the library hover shows too. Heading anchors follow GitHub's rule, which changes the targets of table-of-contents links in library hovers and the REPL viewer's anchor map. The hover keeps its compact rendering otherwise.
- **Agent skill:** the `robotcode` skill in robotframework-agent-plugins switches its lookups from `robotcode libdoc … list/show` to `robotcode doc keywords/keyword`. The vendored copy in `chat-plugins/robotcode` is re-synced.
- **Docs:** a new page `docs/03_reference/browsing-documentation.md`; the CLI reference is regenerated.
- **Not in this change:** `robotcode doc suites/tests PATH` (like Testdoc) and `robotcode doc types TARGET` are possible later extensions. Also out: `robotcode libdoc` itself, several targets per call, HTML output, and Libdoc spec files as targets.

Depends on `library-loading-robustness`, whose `LibraryDoc.loaded_without_arguments` marker tells the command that the keywords come from a load without the given arguments; this change is archived after it. `vscode-doc-browser` builds on this change.

## Capabilities

### New Capabilities

- `library-documentation-markdown`: The full-page Markdown documentation of a library, resource file or suite file: structure and heading hierarchy, keyword order, private keywords, keyword index, data types and the links to them, links from names in Robot-format documentation, anchors, variables in text, and where the page is shown.
- `documentation-cli`: The `robotcode doc` command group: targets, resolution with the project configuration, live generation, abort behaviour, Markdown and JSON output, keyword overview and lookup, and the terminal browser.

### Modified Capabilities

- `keyword-documentation-rendering`: The guarantee that non-Markdown keywords without argument descriptions render "exactly as before" gets an exception for the converter corrections and no longer covers the full page. New requirements cover those corrections (escaped `|` in table cells, no `\#` in link targets), the library scope as Libdoc names it, and GitHub anchors for links to headings. The requirement on Markdown reference links names `robotcode doc lib` and `browse` among the full-document views. There, references to types now link to their heading in the new `Data types` section. The hover, signature help, completion, the keyword output of `robotcode doc` and the `doc` and `short_doc` fields of its JSON keep inline code.

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: the `only_doc=False` branch of `LibraryDoc.to_markdown` (with the links from names and to types, without `_link_inline_links`) and `_get_doc_for_keywords`, `_create_toc`/`_link_inline_links` (shared slug rule, `#` instead of `\#`), `get_reference_targets` (the headings of a Robot-format introduction), `get_library_doc_from_library` (scope name), `KeywordDoc` (the documentation conversion of `to_markdown` made public for the JSON fields, names in single backticks in Robot-format documentation).
- `packages/robot/src/robotcode/robot/utils/markdown_docs.py`: `slugify` with GitHub's rule, heading anchors with numbered repeats, inline code for variables in text. `packages/robot/src/robotcode/robot/utils/markdownformatter.py`: escaped `|` in table cells, no `\#` in link targets.
- New `packages/repl/src/robotcode/repl/doc_cli.py`, registered in `packages/repl/src/robotcode/repl/hooks.py`; `cli.py` (the `-v`, `-V` and `-P` options shared with `doc`); `console_interpreter.py` (`.doc` passes `header_level=0`); `_pt/doc_viewer.py` (anchor map with the shared slug rule). No new package dependency.
- Tests on RF 5.0–7.5 (Linux, Windows, macOS): renderer, converter, slug, viewer and CLI tests. The golden tests of `tests/robotcode/robot/diagnostics/test_library_doc_rendering.py` and `tests/robotcode/language_server/robotframework/parts/test_http_server_markdown.py` change where they show the full page, the scope or anchors.
- Docs: new `docs/03_reference/browsing-documentation.md`, entries in `docs/03_reference/index.md`, the package overview of `docs/03_reference/cli.md` and the page map of `docs-next/scripts/convert.mjs`; the generated part of `cli.md`; the `.doc` row of `docs/03_reference/repl.md`; the lookup sentence of `docs/03_reference/ai-agents.md`.
- Agent plugin: `plugins/robotcode/skills/robotcode/SKILL.md` and `references/{authoring,install,repl,workflows}.md` in /home/daniel/develop/robot/robotframework-agent-plugins, then `hatch run build:sync-chat-plugin`.
- Unchanged: `robotcode libdoc`; the language server apart from the shared rendering fixes and the page of the unused `type=md` branch of its documentation server; the VS Code extension; the IntelliJ plugin.
