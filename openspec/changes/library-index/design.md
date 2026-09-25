# Design: library-index

## Context

See proposal.md for the motivation and specs/library-discovery/spec.md for the requirements. These facts were verified:

- **Robot Framework.**
  - `robot.libraries.STDLIBS` holds `BuiltIn`, `Collections`, `DateTime`, `Dialogs`, `Easter`, `OperatingSystem`, `Process`, `Remote`, `Screenshot`, `String`, `Telnet` and `XML` on RF 5.0 to 7.5, plus `Reserved` before RF 7.0.
  - The package `robot.libraries` also contains `dialogs_py` (RF 5.0 to 7.5) and `normalizer` (RF 7.4 and 7.5). Neither is a library.
  - `Easter` contains only `none_shall_pass`. `Reserved` only provides keywords for the reserved control words, which fail when called.
  - `robot.utils.robotpath.find_file` turns `/` into `os.sep` and looks for a relative path first in the base directory, then in each `sys.path` entry. A resource shipped inside a package therefore imports as `Resource    acme/keywords.resource` on every OS.
  - Robot Framework imports a `Variables` name by path only when it ends in a variable-file extension, `/` or `os.sep` (`Namespace._is_import_by_path`). Any other name is imported as a module.
  - Robot Framework recognises a suite initialization file by the name `__init__` before the extension, compared case-insensitively (`robot.parsing.suitestructure`).
  - Reading a file with `ResourceFileBuilder().build(path)` behaves the same on RF 5.0 to 7.5:
    - a reStructuredText document, and on RF 7.5 a Markdown document, without a Robot Framework code block becomes an empty resource;
    - a `.robot` file with a `*** Test Cases ***` or `*** Tasks ***` section raises `DataError` ("Resource file with '…' section is invalid");
    - a `.robot` file with only keywords builds fine;
    - an `__init__.robot` with `Suite Setup` and a `Library` import builds without raising: the setting is only logged as an error, and the import is kept.
  - Version differences in the same check:
    - a `package.json` raises `DataError` on RF 6.1 and newer;
    - a German `*** Schlüsselwörter ***` header without a `Language:` line builds only with `lang="de"`, and `ResourceFileBuilder` has had a `lang` parameter since RF 6.0;
    - an unrecognised section header only logs an `[ ERROR ]` and yields an empty resource on RF 5.0 and 6.0, and raises `DataError` on RF 6.1 and newer.
  - Outside `LOGGER.cache_only`, such builds print their warnings and errors to the console (for example "Imported resource file '…' is empty."). Under `LOGGER.cache_only` nothing is printed on RF 5.0 to 7.5. The messages stay in the logger's message cache and are relayed to a console logger that is registered later (`Logger._relay_cached_messages`).
- **Python packaging.**
  - On Python 3.10 to 3.14, `importlib.metadata.entry_points(group=...)` returns entry points whose name contains `/` unchanged (`acme/lib/Legacy.py`, `acme/keywords.robot.md`).
  - It returns one entry point per distribution when two distributions declare the same name.
  - Each entry point has `.dist.name` and `.dist.version`.
  - An invalid value (`not a module`) is returned as it is, and `.module` then raises: `AttributeError` up to 3.12, `AssertionError` on 3.13 and 3.14.
  - A distribution added while the process runs is found by the next call.
  - Cost in the `rf75` environment with 60 distributions: about 15 ms to import `importlib.metadata`, then about 2 ms per group.
  - The research found no RF library package that declares an entry-point group identifying its library. It also found that uv installs a project, and so its entry points, only when a build system is defined or `tool.uv.package = true` is set.
- **RobotCode.**
  - `complete_library_import` (`library_doc.py`) runs in the `ImportsManager` worker process, a `ProcessPoolExecutor` with the spawn context. A worker keeps the `sys.path` it was started with. For an empty name the function offers `iter_module_names("robot.libraries")` minus `DEFAULT_LIBRARIES` as `MODULE_INTERNAL`, plus every top-level `.py` file and directory on `sys.path` and in the base directory.
  - `complete_resource_import` and `complete_variables_import` list `sys.path` and the base directory in the same way.
  - The LS (`parts/completion.py`) gives every such item `sort_text=f"030_{label}"` and `detail=kind.value`. For `Library` and `Variables` it completes the segment after the last `.`, or after the last `/` or path separator when the name contains one. For `Resource` it completes the segment after the last `/` or path separator. `first_part` is the text before that segment.
  - Project files are collected in the same way in `RobotWorkspaceProtocolPart.load_workspace_documents` and `RobotFrameworkLanguageProvider.collect_workspace_folder_files`, keeping only `.robot`/`.resource` (compared case-sensitively in the LS and case-insensitively in analyze). The call is `iter_files(root, ignore_files=[".robotignore", ".gitignore"], include_hidden=False, parent_spec=IgnoreSpec.from_list([*DEFAULT_SPEC_RULES, *exclude_patterns], root))`.
  - The exclude patterns come from `[tool.robotcode-analyze] exclude-patterns` plus, in the LS, `robotcode.workspace.excludePatterns`. The LS reads the first from `analysis_config.exclude_patterns` of its protocol, a `WorkspaceAnalysisConfig` built with `AnalyzeConfig.to_workspace_analysis_config()` (`parts/robot_workspace.py`). `[tool.robotcode-analyze]`, which also holds `load-library-timeout` and `cache`, is modelled by `AnalyzeConfig`, today in `robotcode-analyze` (`analyze/config.py`). `analyze-config-in-robot` moves its analysis part, `exclude-patterns` included, to `robotcode-robot` (`robotcode.robot.config.analyze_config`) with the accessor `get_analyze_config(robot_config)`. `doc-cli` reads the section with that accessor, without depending on `robotcode-analyze` (its D7), so it is available in every variant of doc-cli's hosting-package question Q3.
  - `ALLOWED_RESOURCE_FILE_EXTENSIONS` is:
    - `.robot`, `.resource`, `.rst` and `.rest`;
    - plus `.json` and `.rsrc` on RF 6.1 and newer;
    - plus `.md` and `.markdown` on RF 7.5.
  - `is_library_by_path` treats a name ending in `.py`, `/` or `os.sep` as a path. `is_variables_by_path` does the same for the variable-file extensions of the running version.
  - The LS inserts `python-path` into its own `sys.path` in `server_initialized`, before the worker is spawned.
  - RobotCode's only entry-point use is its own `robotcode` plugin group, loaded through pluggy, which imports every module.
  - Tool sections of the configuration (`[tool.<name>]`):
    - They exist only in the field `tool` of the top-level `RobotConfig` (`config/model.py`). Profiles have no such field, and `combine_profiles` returns a `RobotBaseProfile` without it, so a tool section is not per profile.
    - `load_config_from_path` (`config/loader.py`) creates one instance for each class passed in `extra_tools`, for every configuration file it reads. It reads `[tool.<name>]` from each configuration file, in `robot.toml`, `.robot.toml` and `pyproject.toml` alike, in the order of `get_config_files`: the user configuration, `pyproject.toml`, `robot.toml`, `.robot.toml`. It combines them with `add_options`, which merges `extend-*` dictionaries into the base key. A file without the section yields an instance with defaults. When only the default configuration applies (no configuration file), `tool` is an empty dictionary.
    - Nothing evaluates a tool section. `evaluated_with_env`, which evaluates `{expr = …}` values, is only called on the combined profile.
    - `[tool.robotcode-analyze]` is `AnalyzeConfig`, today in `robotcode-analyze`, which registers it with the plugin hook `register_tool_config_classes` (`analyze/hooks.py`), `robotcode config show` passes the registered classes in `extra_tools`, and `robotcode config info` lists their fields (`get_config_fields`). `docs/03_reference/config.md` is generated with `robotcode config info desc`. `analyze code`, `analyze cache`, `analyze dump-model` and `language_server/cli.py` pass the class in `extra_tools` themselves.
    - `analyze-config-in-robot` changes this (its D3 to D5):
      - `loader.py` gets `BUILTIN_TOOL_CONFIG_CLASSES: Dict[str, Type[Any]] = {"robotcode-analyze": AnalyzeConfig}`, with the analysis part as base class. `load_robot_config_from_path` passes `{**BUILTIN_TOOL_CONFIG_CLASSES, **(extra_tools or {})}` to `load_config_from_path`, so a class passed in `extra_tools` replaces the built-in one for the same name.
      - `get_config_fields()` iterates over the built-in sections merged with the registered classes, a registered class winning for the same name. `config show` stays unchanged and gets the built-in sections from the loader.
      - `get_analyze_config(robot_config)` returns `tool["robotcode-analyze"]` when it is an `AnalyzeConfig`, and `AnalyzeConfig()` otherwise. It is a free function because `analyze_config.py` imports `model.py`. The language server, `analyze cache`, `analyze dump-model` and later `doc-cli` load without `extra_tools` and use it.
      - Its tasks assume its Q4 (a): every command that loads the configuration through `load_robot_config_from_path` validates the built-in sections. With (b), the loader does not add them, and `config show`, the language server and `doc-cli` pass `BUILTIN_TOOL_CONFIG_CLASSES` as `extra_tools` themselves.
    - A prototype with a second class in the dictionary of built-in sections, `{"robotcode-analyze": AnalyzeConfig, "robotcode-doc": <class with libraries/extend-libraries>}`, passed to `load_config_from_path`:
      - `libraries` in `robot.toml` plus `extend-libraries` in `.robot.toml` combined to all entries;
      - a section only in `pyproject.toml` was read;
      - a `robot.toml` without the section gave an instance with defaults;
      - only the default configuration gave `tool == {}`;
      - `libraries = ["CustomerLib"]` raised `ConfigTypeError` with `Parsing "…/robot.toml" failed: Reading [tool.robotcode-doc] failed: Invalid value for "libraries": …`;
      - `_get_config_fields_for_type` of the config command gave `tool.robotcode-doc.libraries` and `tool.robotcode-doc.extend-libraries`.
    - `robotcode config show` prints a section that the files do not set as an empty table. In the development environment it prints `[tool.robotcode-analyze]` for a `robot.toml` without that section.
    - The language server loads the configuration once at start, in `language_server/cli.py`, with the configuration files and root given on its command line. It passes the combined profile and `AnalyzeConfig.to_workspace_analysis_config()` through `run_server`, `RobotLanguageServer` and `RobotLanguageServerProtocol`. If loading raises a `TypeError` or `ValueError`, it reports the error and passes `None` for what it has not read yet, and the protocol falls back to `RobotBaseProfile()` and `WorkspaceAnalysisConfig()`. VS Code restarts the language server of a workspace folder when a `pyproject.toml`, `robot.toml` or `.robot.toml` in it changes (`languageclientsmanger.ts`).
    - `scripts/create_robot_toml_json_schema.py` lists the tool sections of the JSON schema in its own `ToolConfig` dataclass, today only `robotcode-analyze`. It uses neither the plugin hook nor, after `analyze-config-in-robot`, the built-in sections.
    - `robotcode-robot` does not depend on `robotcode-plugin`, so it registers no hooks. `robotcode-analyze`, `robotcode-runner` and `robotcode-language-server` depend on `robotcode-robot`, and `robotcode-repl` depends on `robotcode-runner`. `robotcode-robot` does not depend on `robotcode-analyze`.
  - Only profile fields with `robot_priority` metadata reach Robot Framework's command line (`build_command_line`).

## Goals / Non-Goals

**Goals:**
- One index module in `robotcode-robot` that the CLI, the language server and completion all use. Building the index imports nothing.
- The entry-point convention exists as a document that library authors can follow, and RobotCode is its first reader.

**Non-Goals:**
- Collecting imports across the project to infer which installed packages are libraries (maintainer decision: only explicitly named libraries are documented).
- Documenting every entry of the index at once, for example in a directory output of `robotcode doc` without targets.
- Import arguments or argument variants in entry points. A declaration names a library, not a keyword set. Argument-dependent keyword sets belong to `library-keyword-set-declaration`.
- Trove classifiers, `top_level.txt`, `packages_distributions()` or heuristics over `sys.path` as sources.
- An index view in the IntelliJ plugin, which has no documentation view.
- Changing Robot Framework, or asking it to read the groups.

## Decisions

### D1: One index module in `robotcode-robot`

New `packages/robot/src/robotcode/robot/diagnostics/library_index.py`. It has three frozen dataclasses:
- `IndexEntry`:
  - `kind`: `library` or `resource`;
  - `origin`: `standard`, `installed` or `project`;
  - `name`;
  - `distribution` and `version`, for installed entries;
  - `value`, the entry-point value;
  - `args`, for project libraries.
- `InvalidDeclaration`: group, name, value, distribution, version and reason.
- `LibraryIndex`, which holds both lists.

The class of the tool section for project libraries, `LibraryIndexConfig`, lives next to `AnalyzeConfig` in `robotcode.robot.config` (D6), and `library_index.py` imports it from there.

The index is built from four small functions:
- `standard_libraries()`;
- `declared_entries(group)`, which returns valid and invalid entries;
- `project_resources(root, exclude_patterns, languages)`;
- `project_libraries(config)`, over the tool section of D6.

`build_library_index(...)` combines them. `index_to_markdown(index)` renders the listing (D8).

The module imports `STDLIBS`, the extension sets and `is_library_by_path`/`is_variables_by_path` from `library_doc.py`. `library_doc.py` does not import it, so there is no import cycle.

Rejected:
- Placing it in `imports_manager.py`: building the index needs no `ImportsManager`.
- An index object cached in the LS, which would need invalidation by file watchers. It is built on each request (D9).
- Naming it after the existing `ProjectIndex` (references index): the two are unrelated.

### D2: Entry points are read as metadata only

`declared_entries` calls `importlib.metadata.entry_points(group=...)` for the three groups `robotframework.libraries`, `robotframework.resources` and `robotframework.variables`. It takes the distribution from `ep.dist`, and it never calls `ep.load()` or `ep.module`.

The call runs in the process whose `sys.path` is the analysis' `sys.path`:
- the LS process after `server_initialized`;
- the CLI after doc-cli has applied `python-path`.

It is not cached: the cost is small (see Context), and new installs are picked up.

The group names are a maintainer decision. Robot Framework itself does not read them. The value is shown as the location. It is never used to resolve the entry, because opening goes by name (D7).

Rejected:
- pluggy's `load_setuptools_entrypoints`, which imports each module.
- A RobotCode-owned group name.
- Resolving the value, which would make the index depend on imports.

### D3: Validation instead of guessing

An entry is invalid when:
- its value is not `module` or `module:attr`, where every dot-separated part is a Python identifier. RobotCode's own check is used, and not `ep.module`, which raises different exceptions per Python version;
- its name is empty;
- its name contains a variable (`contains_variable(name, "$@&%")`, as in `_find_library_internal`);
- its name contains `::`, which is the argument separator of libdoc and of doc-cli targets;
- in the resources group, the suffix of its name, lower-cased, is not in `ALLOWED_RESOURCE_FILE_EXTENSIONS`;
- in the variables group, `is_variables_by_path` rejects the name and the name is not a dotted module name (every dot-separated part a Python identifier). Robot Framework imports such a name as a module (see Context), so `acme.vars` is valid and `acme/vars.toml` is not.

The reason text names the rule. Invalid declarations of all three groups appear in the "Invalid declarations" part of the listing, because that part reports package metadata, not documentation. Valid variables entries are never listed (maintainer decision). Import completion only uses valid entries.

### D4: Standard group

The standard group is `STDLIBS` without `Easter` and `Reserved` (see Context for what these two contain). `Remote` is listed. Opening it without arguments behaves as `Library    Remote` does. That this can mean a connection attempt is governed by `library-loading-robustness`.

### D5: Project resources

`project_resources` collects the files as the two existing workspace scans do (Context). It compares suffixes case-insensitively against `ALLOWED_RESOURCE_FILE_EXTENSIONS` of the running version. Each file is listed as `path.relative_to(root).as_posix()`.

The content filter follows Q2, if it is confirmed as recommended:
- `.resource` and `.rsrc` are listed without reading them.
- Every other candidate whose name before the extension is `__init__`, compared case-insensitively, is a suite initialization file and is not listed. Such a file can build as a resource with imports (see Context).
- Every other candidate is read with Robot Framework's `ResourceFileBuilder` under `LOGGER.cache_only`, as `get_model_doc` does. On RF 6.0 and newer it is read with `lang` set to the project's languages, a version difference resolved once at module level.
- A candidate is kept if the build does not raise and yields at least one keyword, variable or import.

The LS takes the languages from `DocumentsCacheHelper.get_languages_for_document(folder.uri)`. The CLI takes them from the profile's `languages`. The exclude patterns are:
- in the LS, those of `load_workspace_documents`;
- in the CLI, `exclude_patterns` of the `AnalyzeConfig` that doc-cli reads with `get_analyze_config(robot_config)` for its `ImportsManager` (doc-cli D7). Both come from `robotcode-robot` (`robotcode.robot.config.analyze_config`, `analyze-config-in-robot`), so the command has them in every variant of doc-cli's Q3.

Rejected:
- Reusing the documents the LS already opened: that covers only `.robot`/`.resource`, and the CLI has no document cache.
- A RobotCode regular expression for Robot Framework code blocks: it would duplicate `RestParser`/`MarkdownParser`.

### D6: Project Python libraries in an own tool section

Project Python libraries are declared in an own tool section, as the analysis settings are in `[tool.robotcode-analyze]`, and not in top-level `robot.toml` keys (maintainer decision). The name of the section is Q1. This design and the spec use the recommended `robotcode-doc`.

A new module `packages/robot/src/robotcode/robot/config/library_index_config.py` gets `LibraryIndexConfig(BaseOptions)`, whose docstring describes the section, as `AnalyzeConfig`'s does. It has two fields, each with a description and a TOML example:
- `libraries: Optional[Dict[str, List[str]]]`, a table from a library name to its import arguments, the shape of `listeners`;
- `extend_libraries` (alias `extend-libraries`), of the same type.

The arguments are plain strings. `listeners` also accepts `{expr = …}` values, but nothing evaluates a tool section (see Context). Variables such as `${X}` in the arguments are resolved when an entry is opened (D7).

Loading and combining use the existing tool-section mechanism (see Context), with the section as a built-in tool section (below):
- Every configuration file can contribute a `[tool.robotcode-doc]`, in `robot.toml`, `.robot.toml` and `pyproject.toml` alike.
- `add_options` combines them in the order of `get_config_files`. `extend-libraries` adds its entries to `libraries`.
- The section is not part of a profile, so selecting a profile does not change the list. The variables used for the arguments still come from the selected profile.

Where the class lives and who reads it:
- **Placement.** The class lives in `robotcode-robot`, the lowest package that all its readers depend on: `library_index.py` itself, the language server, and the package that hosts `robotcode doc` in every variant of doc-cli's Q3. Within it, the module sits in `robotcode.robot.config`, next to `AnalyzeConfig` (`analyze_config.py`, `analyze-config-in-robot`) and the configuration model, and is named after the class as `analyze_config.py` is.
- **Built-in section (maintainer decision).** `loader.py` adds `"robotcode-doc": LibraryIndexConfig` to `BUILTIN_TOOL_CONFIG_CLASSES` (`analyze-config-in-robot` D3) and imports the class from `.library_index_config`, as it imports `AnalyzeConfig` from `.analyze_config`. `library_index_config.py` imports `model.py` and not the loader, so there is no import cycle. Every `RobotConfig` from `load_robot_config_from_path` then holds a typed `tool["robotcode-doc"]` as soon as a configuration file was read, without `extra_tools`. No plugin registers the section, and no reader passes the class itself in `extra_tools`.
- **Accessor.** `library_index_config.py` gets `get_library_index_config(robot_config: RobotConfig) -> LibraryIndexConfig`, which follows `get_analyze_config`. It returns `robot_config.tool["robotcode-doc"]` when that is a `LibraryIndexConfig`, and `LibraryIndexConfig()` otherwise: when `tool` is `None`, empty (no configuration file read), or holds the section as a plain dictionary (a `RobotConfig` from `load_robot_config_from_robot_toml_str`). It is a free function and not a method of `RobotConfig`, because `library_index_config.py` imports `model.py`. Like `get_analyze_config`, it is named after its module and class, so it keeps its name whatever section name Q1 settles on.
- **Language server.** After `analyze-config-in-robot`, `language_server/cli.py` loads the configuration without `extra_tools`. In the same `try` block, next to `get_analyze_config`, it reads `get_library_index_config(robot_config)` and passes it as `library_index_config` through `run_server`, `RobotLanguageServer` and `RobotLanguageServerProtocol`, as it passes `analysis_config`. The protocol falls back to `LibraryIndexConfig()` when it gets `None`, which happens when loading failed (Context). `robot/documentation/getIndex` (D9) reads it from the protocol. A change reaches the language server when it restarts, as for `[tool.robotcode-analyze]`. VS Code restarts it when a configuration file of the folder changes (see Context).
- **CLI.** doc-cli's command reads the section with `get_library_index_config(robot_config)` from the configuration it loads without `extra_tools` (its D7) and passes it to `build_library_index`.
- **Config command.** `robotcode config show` and `robotcode config info` know the section in every installation, because they use the built-in sections (`analyze-config-in-robot` D4). The generated `docs/03_reference/config.md` therefore lists its keys. For a configuration that does not set the section, `config show` prints an empty `[tool.robotcode-doc]` table, as it prints `[tool.robotcode-analyze]` (Context).
- **Validation.** Every command that loads the configuration through `load_robot_config_from_path` validates the section. For example, `robotcode robot` stops on `libraries = ["CustomerLib"]` (a list where a table belongs) with the loader's message, which names the file, the section and the key (Context, prototype). This follows `analyze-config-in-robot` Q4 (a). With its (b), only the commands that pass `BUILTIN_TOOL_CONFIG_CLASSES` in `extra_tools` read and validate the section. The language server and `doc-cli` are among them, so they get the section in the same way.
- **Schema.** `scripts/create_robot_toml_json_schema.py` gets `robotcode_doc: Optional[LibraryIndexConfig]` (alias `robotcode-doc`, description `LibraryIndexConfig.__doc__`) in its `ToolConfig` dataclass, next to `robotcode_analyze`, because the script uses neither the plugin hook nor the built-in sections (Context).

`project_libraries(config)` lists each name of `config.libraries` with its arguments. It decides nothing else. Opening an entry decides the mode through `is_library_by_path`, as Robot Framework does:
- a path is resolved against the project root, like relative `python-path` entries;
- a module is resolved through `sys.path`.

The section does not feed the analysis. It is not part of a profile, so `build_command_line` never sees it, and it never reaches Robot Framework.

Rejected:
- Top-level `robot.toml` keys in `RobotBaseProfile` (`known-libraries`/`extend-known-libraries`): maintainer decision.
- The class in `robotcode-analyze`: `library_index.py` in `robotcode-robot` cannot import from that package, and doc-cli's command does not depend on it (doc-cli D7).
- The class in `library_index.py`: the tool-section classes belong next to `AnalyzeConfig` in `robotcode.robot.config` (maintainer decision), and `library_index.py` only reads the section.
- A field in `WorkspaceAnalysisConfig`, which already reaches the protocol: that class carries `[tool.robotcode-analyze]` into the analysis (`DocumentsCacheHelper`), and this section does not feed the analysis.
- Loading the configuration again in the `getIndex` handler: it would not see the configuration files and root given to `robotcode language-server` on its command line.
- Registering the class with `register_tool_config_classes` in the `hooks.py` of the package that hosts `robotcode doc`, with the language server and doc-cli passing it in `extra_tools` (the earlier plan). `config show`/`info` would then know the section only where that package is installed, as they know `[tool.robotcode-analyze]` today only where `robotcode-analyze` is installed (`analyze-config-in-robot`, Context). The maintainer decided on a built-in section instead.
- Passing the class in `extra_tools` in the language server and doc-cli in addition to the built-in entry: the loader already adds the built-in sections.
- A method of `RobotConfig` instead of `get_library_index_config`: `library_index_config.py` imports `model.py`, so a method would need the reverse import, as for `get_analyze_config`.
- Deriving project libraries from `python-path`. Those directories also hold helper modules, telling libraries apart needs imports (the "trial import" route the research found fragile), and module mode and file mode cannot be told apart without the user's string.

### D7: Opening an entry

Every surface opens an entry through its own `ImportsManager`, so the documentation matches the analysis for the same import:
- libraries through `get_libdoc_for_library_import(name, args, base_dir=root, variables=…)`, with `args=()` except for project libraries;
- resources through `get_resource_doc_for_resource_import(name, base_dir=root, …)`.

In the LS that is the workspace folder's `ImportsManager`. In the CLI it is doc-cli's. The variables are the command-line and profile variables of that manager.

Duplicate names are not resolved in the listing, because that would need an import. The opened page shows the source Robot Framework actually used.

In VS Code the client sends vscode-doc-browser's target payload:
- `kind`;
- `name`;
- `args`;
- `baseDir` = the workspace folder path;
- `context` = the workspace folder URI, not a document.

vscode-doc-browser's client command picks the language client by `target.context` (its D5), so the target needs a URI there. vscode-doc-browser defines `context` as a document URI or, when no document is the context, a workspace folder URI, and resolves such a target through that folder's `ImportsManager` with its configured variables (its D1 and D4, step 3; spec scenario "Workspace folder as context").

### D8: `robotcode doc` without targets

With zero targets, doc-cli's command builds the index and does not create any documentation. It builds it with the root folder, the profile, the exclude patterns (D5) and the languages it already loads, and with the tool section of D6.
- **Interactive** (when doc-cli's output-mode rules select the browser): the TUI sidebar shows the groups of the listing, with its filter. Selecting an entry takes the same code path as a target given on the command line, with the project root instead of the current directory as base directory (D7).
- **Otherwise:** `index_to_markdown` writes the listing specified in the spec to standard output or to `--output FILE`. It is a pure function over `LibraryIndex`, so golden-string tests need no environment.
- **JSON:** if doc-cli offers JSON output (Q5), the same fields are serialised.
- **Exit code:** 0, also when invalid declarations exist. They are third-party metadata, not a failure of the command.

This covers the command without targets and without lookup options. doc-cli makes every call without targets a usage error; this change replaces that only for the plain call, through a MODIFIED requirement of `documentation-cli`. `-k/--keyword`, `--list`, `--search` and `--search-regex` without targets stay usage errors, because nothing documents everything (maintainer decision), and so does `-o` naming a directory, since the listing is one text.

### D9: VS Code index view

The language server gets the request `robot/documentation/getIndex` (`threaded=True`). It is registered in the LS part that vscode-doc-browser adds for `robot/documentation/getDocument` (`parts/documentation_browser.py`, `RobotDocumentationBrowserProtocolPart`).
- **Parameters:** `{uri}`, a document or workspace folder URI, from which the LS takes the workspace folder.
- **Result:**
  - `entries`: a list of `{kind, origin, name, distribution?, version?, value?, args?}`, without variables;
  - `invalid`: a list of `{group, name, value, distribution, version, reason}`.

The index is built on each request. Its project libraries come from the tool section that the language server loaded at start (D6). The webview requests it when the index view is shown and when the user presses its refresh button. The index view is part of the sidebar of vscode-doc-browser's panel:
- groups as in the listing, with a name filter;
- invalid declarations shown with their reason.

Selecting an entry posts the D7 target to the same panel with vscode-doc-browser's `open(target, anchorId)` message. The webview cannot send LSP requests itself, and vscode-doc-browser's D5 allows only a fixed set of messages, which the extension validates. The index view therefore adds one message, `loadIndex(folderUri)`. The extension accepts it only for a URI of an open workspace folder, sends `robot/documentation/getIndex` to that folder's language client and posts the result back.

### D10: Completion ranking

The completion part of the LS reads the valid declared names of the matching group through `library_index`, in the LS process, once per completion request. For each candidate it forms `full = (first_part or "") + label`, normalising `\` to `/`. A candidate is declared when a declared name equals `full` or starts with `full + "."` or `full + "/"`. Declared candidates get `sort_text=f"020_{label}"`, and their `detail` is `f"{kind.value} ({distributions})"`, with the names of all matching distributions joined by `, `. All other candidates stay unchanged. The match is a pure function over the declared names, so it is tested without a language server.

The worker functions, their `CompleteResult` and the REPL completion do not change, apart from the filter in D11.

Rejected:
- Adding a field to `CompleteResult` for one consumer.
- Reading entry points in the worker, which would also need the declared names passed back through the `CompleteResult` list.

### D11: Side fix for internal modules

In `complete_library_import`, the list of internal modules keeps only names with `e in STDLIBS and e not in DEFAULT_LIBRARIES`. This removes `dialogs_py`, and on RF 7.4 and newer `normalizer`. It also affects the REPL, which calls the same function.

### D12: The convention document

The document is written for library authors. Where it lives is Q3. It contains:
- the three groups;
- the name rule: the exact import string, `/` as the path separator, no variables, no `::`, no arguments;
- the value rule (`module` or `module:attr`);
- `pyproject.toml` examples for a library, a class in a submodule (`DocTest.VisualTest`), a packaged resource and a variable file;
- the rules for tools:
  - listing reads metadata only;
  - opening resolves the name as Robot Framework does;
  - arguments come from the context or are left out, never guessed;
  - invalid entries are reported;
- that plugin and translation packages for another library are not libraries;
- that Robot Framework itself does not read the groups;
- a pointer to the keyword-set attribute of `library-keyword-set-declaration` once that change has landed.

### D13: Tests

Installed packages are simulated. Each test writes a `<name>-<version>.dist-info` directory with `METADATA` and `entry_points.txt` under `tmp_path` and adds it with `monkeypatch.syspath_prepend`. A package whose `__init__.py` raises proves that nothing is imported. Paths are compared as POSIX strings. There are no hard-coded separators, so the tests run on Linux, Windows and macOS.

The test files:
- `tests/robotcode/robot/diagnostics/test_library_index.py`: groups, duplicates, validation, the standard group per RF version, the project scan, the completion match function and `index_to_markdown` golden strings.
- `tests/robotcode/robot/config/test_library_index_config.py`: the tool section loaded without `extra_tools` from configuration files under `tmp_path`, an invalid value, and `get_library_index_config` with its defaults. The files are passed to `load_robot_config_from_path` directly, so the developer's user configuration is not read.
- `tests/robotcode/cli/test_config_command.py` from `analyze-config-in-robot`: `config info` and `config show` know the section with no registered classes.
- An LS test for completion ranking, next to `test_completion_argument_docs.py`. The declarations are read in the test process, where `monkeypatch.syspath_prepend` reaches them. The candidates come from the `ImportsManager` worker, which keeps the `sys.path` it was started with. The candidate folders are therefore created next to the test document, where the worker lists them as base-directory entries.
- A test of the internal-module filter that calls `complete_library_import` directly.
- An LS protocol test for `robot/documentation/getIndex` on the `protocol` fixture's workspace folder, which is only read. The fixture creates `RobotLanguageServer()` without configuration, so the test sets the tool section as `library_index_config` on the fixture's protocol with `monkeypatch.setattr`.
- A CLI test for the listing without targets, in the test module of doc-cli.

## Risks / Trade-offs

- [The Q2 filter reads every non-`.resource` candidate with Robot Framework] → only on explicit index requests (the CLI without targets, the index view), never for completion. `.resource`/`.rsrc` are not read, and hidden, ignored and excluded folders are not entered.
- [Nobody declares entry points yet, so the "Installed" groups start out empty] → packages keep working by explicit name. The convention document gives authors a copyable `pyproject.toml` snippet.
- [Same name from two distributions: which one opens depends on the order of `sys.path`] → both are listed with their distribution. The opened page shows the source Robot Framework used.
- [An entry that is valid by these rules can still fail to open, for example a class that does not exist] → opening shows Robot Framework's import error. `library-loading-robustness` covers how failed loads are shown.
- [doc-cli's implementation differs from its design (hosting package, `ImportsManager` setup, TUI, test harness)] → task 1.1 checks the D5, D7 and D8 interfaces against the implemented command first.
- [The VS Code part needs vscode-doc-browser's LS part, panel and target payload] → the VS Code tasks (6.3, group 7) wait for vscode-doc-browser.
- [A project that uv manages without a build system or `tool.uv.package = true` cannot publish its own libraries through entry points] → project libraries come from the tool section (D6) and project resources from the scan.
- [The tool section is not per profile, so a profile cannot bring its own project libraries] → the same holds for `[tool.robotcode-analyze]`. The variables in the arguments still come from the selected profile, and a local `.robot.toml` can extend the list of `robot.toml` with `extend-libraries`.
- [An invalid value in `[tool.robotcode-doc]` stops every command that loads the configuration, for example `robotcode robot` in CI, although only the index reads the section (D6, `analyze-config-in-robot` Q4 (a))] → the message names the file, the section and the key. The same holds for `[tool.robotcode-analyze]` after `analyze-config-in-robot` and for the rest of `robot.toml`.
- [The language server reads the tool section only at start] → the same as `[tool.robotcode-analyze]`. VS Code restarts a folder's language server when its `robot.toml`, `.robot.toml` or `pyproject.toml` changes.
- [Robot Framework keeps the messages logged under `LOGGER.cache_only` and relays them to a console logger registered later] → the index build does not register one. If doc-cli does in the same process, the messages of the Q2 reads could appear then. Task 3.2 checks that the index build itself prints nothing.

## Migration Plan

Additive. There is no data or configuration migration. The new optional tool section appears in the regenerated schema, in the configuration reference and in the output of `robotcode config show`/`info`. The completion change only affects ordering, item details, and two internal modules that are no longer offered. Archive after `doc-cli` and `analyze-config-in-robot`. The VS Code part needs `vscode-doc-browser` first.

## Open Questions

- **Q1: Name of the tool section for project libraries, and the base of relative paths.**
  - Decided (maintainer): project Python libraries are an explicit list in an own tool section with `libraries` and `extend-libraries` (D6), not top-level `robot.toml` keys and not derived from `python-path`.
  - Section name. Recommended: `robotcode-doc`. It carries the name of the command that shows the index, as `robotcode-analyze` carries the name of `robotcode analyze`, and it follows the final command name of doc-cli's Q2. Other candidates are `robotcode-library-index` and `robotcode-libraries`. Changing the name changes only the placeholder in the spec, the key in `BUILTIN_TOOL_CONFIG_CLASSES` and the one `get_library_index_config` reads, the schema script, the docs and the tests.
  - Base of a relative path such as `lib/legacy/Old.py`: the project root or the configuration file that declares the entry. Recommended: the project root, as RobotCode resolves relative `python-path` entries (against the workspace folder in the LS, the root folder in the CLI). The two differ only for a configuration file outside the project root, such as the user configuration.
  - The spec requirement "Project Python libraries are declared in a RobotCode tool section" and task group 4 use the recommended name and base.
- **Q2: Which discovered files count as project resources.**
  - The recommended default is the D5 filter:
    - `.resource`/`.rsrc` are always listed;
    - other resource extensions only when Robot Framework reads them as a non-empty resource.
  - This includes the proposed rule that `.robot` suite files, and with them their local keywords, are not listed. Suite initialization files (`__init__.*`) are left out by name, because they can build as a resource.
  - Alternatives:
    - extension only, which lists every `README.md` on RF 7.5, every `.rst` document and every `.json`;
    - `.resource`/`.rsrc` only.
  - The paragraph marked in the spec and task 3.2 follow the recommended default.
- **Q3: Where the convention document lives.**
  - Recommended: a page in RobotCode's docs, `docs/03_reference/library-entry-points.md`, linked from the `robotcode doc` page.
  - Alternative: a separate repository or a proposal to the Robot Framework Foundation.
  - Task 8.1 is conditional on it.
- **Q4: A command to open the browser on the index in VS Code.**
  - Without one, the index view is only reachable once the panel is open.
  - Recommended: running vscode-doc-browser's open command without a target, from the command palette, opens the panel on the index view for the workspace folder of the active editor. vscode-doc-browser keeps that command out of the command palette (its D5) and lists a command-palette library picker among its non-goals, so this means contributing a palette entry in `package.json`.
  - Task 7.2 is conditional on it.
- **Q5: JSON listing.** Only if doc-cli decides to offer JSON output (its Q6); the answer there decides this one. Task 5.3 is conditional on it.
