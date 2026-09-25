# Proposal: library-index

## Why

`doc-cli` and `vscode-doc-browser` document libraries and resources only when they are named explicitly: a name on the command line, or the import or keyword at the cursor. Nothing tells the user which libraries and resources are available at all. Robot Framework has no mechanism for this: its only list is `STDLIBS` in `robot.libraries`, and it reads no package metadata (research: no `importlib.metadata`, `entry_points` or `pkg_resources` use in RF 5.0.1 to 7.5). Library packages declare nothing that names their library module or class. Three packages on PyPI have each invented their own entry-point group for this, spelled three different ways (`robotframework_libraries`, `robotframework.libraries`, `robot.libraries`), and no tool is known to read them.

RobotCode's own import completion is no substitute. `complete_library_import` lists every top-level module and directory on `sys.path` without checking anything (219 modules, 135 files and 84 folders for an empty prefix in the `rf75` environment, including `abc` and `antigravity`), and its "Module (Internal)" group also offers `robot.libraries` helper modules that are not libraries (`dialogs_py` on RF 5.0 to 7.5, `normalizer` on RF 7.4 and 7.5).

## What Changes

- **Package convention.** Three entry-point groups for packages: `robotframework.libraries`, `robotframework.resources` and `robotframework.variables`. The entry-point name is the exact string a user writes after `Library`, `Resource` or `Variables`, for example `Browser`, `DocTest.VisualTest` or `acme/keywords.resource`. Names may contain `/`, which the entry-point specification allows. The value is the module or package it lives in (`module` or `module:Class`). This is a convention for tools such as language servers and documentation browsers; Robot Framework itself does not read it. It is documented for library authors. Where that documentation lives is open.
- **Listing reads metadata only.** RobotCode reads the groups with `importlib.metadata.entry_points(group=...)`. It never imports or loads an entry, so there is no pluggy `load_setuptools_entrypoints`. An entry is opened by resolving its name exactly as Robot Framework resolves an import. If two distributions declare the same name, both are shown. Invalid entries are reported with their reason and are not guessed. Packages without declarations keep working when they are named explicitly.
- **Project resources.** All resource files that RobotCode's project file discovery finds are listed, whether they are imported or not. Discovery is core `iter_files` with `.robotignore`/`.gitignore`, without hidden files and with the configured exclude patterns, as for the language server's workspace loading and `robotcode analyze code`. The resource extensions are the ones valid for the running Robot Framework version. The workspace scan today only takes `.robot` and `.resource`. Open: which of the discovered files count as resources. The proposal is not to list suite files with test or task sections, suite initialization files, nor documents that contain no Robot Framework code.
- **Project Python libraries.** An explicit list in an own tool section of the RobotCode configuration, like the analysis settings in `[tool.robotcode-analyze]`, and not top-level `robot.toml` keys (maintainer decision). The section is `[tool.robotcode-doc]` (the name is open) with the key `libraries` and its variant `extend-libraries`. Like every tool section, it is read from `robot.toml`, `.robot.toml`, `pyproject.toml` and the user configuration, and it is not part of a profile. It takes the shape of `listeners`, a table from a library name to its import arguments, so arguments are allowed. The string decides between module and file import exactly as in Robot Framework: `CustomerLib` goes through the Python path, `lib/legacy/Old.py` is a path relative to the project root, as relative `python-path` entries are (the base is part of the open question). The section feeds neither the analysis nor Robot Framework. Deriving the libraries from `python-path` instead would be a heuristic and is rejected. The section is a built-in tool section of the configuration loader in `robotcode-robot`, as `analyze-config-in-robot` makes `[tool.robotcode-analyze]` one (maintainer decision). No plugin registers it. The language server and `robotcode doc` read it with an accessor, and `robotcode config show`/`info` know it in every installation. Every command that loads the configuration reports an invalid value in it as a configuration error, as it does for `[tool.robotcode-analyze]` after that change (its Q4).
- **Standard libraries** from Robot Framework's `STDLIBS` are the third source. The index is made of project, installed and standard entries, and building it imports nothing.
- **Consumers.**
  - `robotcode doc` (`doc-cli`) without targets shows the index instead of documenting anything. The TUI shows it in its sidebar. Piped output is a Markdown list, and JSON is offered only if `doc-cli` offers JSON.
  - The documentation browser in VS Code (`vscode-doc-browser`) gets an index view in its sidebar, fed by a new language server request.
  - Import completion for `Library`, `Resource` and `Variables` keeps today's `sys.path` listing, but ranks declared entries first.
  - Variables entries are never shown in the documentation browser.
- **Side fix.** The "Module (Internal)" group of library import completion only offers names in `STDLIBS`.

Builds on `doc-cli` (the command, its output modes and the TUI). It also depends on `analyze-config-in-robot`, which moves the analysis part of the model of `[tool.robotcode-analyze]` to `robotcode-robot` (`robotcode.robot.config.analyze_config`). From that change it takes `get_analyze_config`, which reads the exclude patterns of the listing in the CLI, and the loader's built-in tool sections (`BUILTIN_TOOL_CONFIG_CLASSES`), to which it adds its own section. Its VS Code part extends the sidebar of `vscode-doc-browser` and needs that change first. The library behaviour attribute (`args`/`volatile`) belongs to `library-keyword-set-declaration`, and the convention document may point to it.

## Capabilities

### New Capabilities

- `library-discovery`: Which libraries and resources RobotCode lists without importing anything, and how the listing is used. It covers the entry-point convention and its validation, standard libraries, project resources, project Python libraries, the listing in `robotcode doc` and in the VS Code documentation browser, and the ranking in import completion.

### Modified Capabilities

- `documentation-cli` (`doc-cli`): a call without targets shows the index instead of failing with a usage error; lookup options (`-k`, `--list`, `--search`, `--search-regex`) and directory output without targets stay usage errors. The index view adds to `vscode-documentation-browser` (`vscode-doc-browser`) without changing its requirements.

## Impact

- New `packages/robot/src/robotcode/robot/diagnostics/library_index.py`: builds the index (standard, entry points, project resources, project libraries), validates entries, and renders the Markdown listing. It depends on `library_doc.py` for `STDLIBS` and the extension sets, and `library_doc.py` does not import it.
- New `packages/robot/src/robotcode/robot/config/library_index_config.py`: `LibraryIndexConfig`, the class of the new tool section, and its accessor `get_library_index_config`, next to `AnalyzeConfig` and `get_analyze_config` (`robotcode.robot.config.analyze_config`, added by `analyze-config-in-robot`).
- `packages/robot/src/robotcode/robot/config/loader.py`: `"robotcode-doc"` joins `BUILTIN_TOOL_CONFIG_CLASSES`.
- `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: `complete_library_import` filters the internal modules by `STDLIBS`.
- `packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py`: `Library`, `Resource` and `Variables` import completion rank declared entries first and name the declaring distribution.
- `packages/language_server/src/robotcode/language_server/robotframework/parts/documentation_browser.py`, the part that `vscode-doc-browser` adds for `robot/documentation/getDocument`: the new request `robot/documentation/getIndex`.
- `packages/language_server/src/robotcode/language_server/cli.py`, `robotframework/server.py` and `robotframework/protocol.py`: the language server reads the tool section from the configuration it loads and passes it to its protocol.
- The `robotcode doc` command and its TUI (`doc-cli`): the behaviour without targets. It reads the tool section from the configuration it loads.
- VS Code (`vscode-doc-browser`): the index view in the webview sources under `vscode-client/documentationBrowser/`, and its request in `vscode-client/extension/documentationBrowser.ts`.
- The tool section in the configuration schema:
  - `scripts/create_robot_toml_json_schema.py` gets the section next to `robotcode-analyze`, because the script uses neither the plugin hook nor the built-in tool sections;
  - `docs/public/schemas/robot.toml.json` and `docs/03_reference/config.md` are regenerated.
- Docs:
  - the page for library authors on the entry-point convention;
  - the `robotcode doc` page from `doc-cli` (listing without targets);
  - `docs/03_reference/cli.md`, regenerated for the help text of `robotcode doc`.
- The robotcode skill in `robotframework-agent-plugins` and its vendored copy under `chat-plugins/`: `robotcode doc` without targets.
- Tests on RF 5.0 to 7.5, Linux, Windows and macOS. Fake `*.dist-info` directories under `tmp_path` stand in for installed packages, so nothing is installed into the environments.
- No change to the IntelliJ plugin. The completion ranking reaches it through LSP.
