# Tasks: library-index

## 1. Prerequisites

- [ ] 1.1 Confirm that `doc-cli` is implemented: the documentation command, its output modes, the TUI, and resolving targets through an `ImportsManager` built from robot.toml. Confirm that `analyze-config-in-robot` is applied, which doc-cli requires as well:
  - `AnalyzeConfig` and `get_analyze_config` are importable from `robotcode.robot.config.analyze_config` (`packages/robot/src/robotcode/robot/config/analyze_config.py`);
  - `packages/robot/src/robotcode/robot/config/loader.py` has `BUILTIN_TOOL_CONFIG_CLASSES`, and `get_config_fields()` in `src/robotcode/cli/commands/config.py` iterates over it;
  - `language_server/cli.py` loads the configuration without `extra_tools` and reads the section with `get_analyze_config`;
  - `tests/robotcode/cli/test_config_command.py` exists.

  Note the answer to Q4 of `analyze-config-in-robot`. With (b), the tests of task 4.1 load with `extra_tools=BUILTIN_TOOL_CONFIG_CLASSES`, and task 4.2 reads the section from the configuration that the language server and doc-cli load with that dictionary. Check the interfaces this change takes from doc-cli's design against the implemented command: the `AnalyzeConfig` it reads with `get_analyze_config` (D5), its configuration loading without `extra_tools` (D6), its `--output`, its mode selection and its browser (`repl/_pt/doc_browser.py`, D8), and its test modules `tests/robotcode/repl/test_doc_cli.py` and `test_doc_browser.py` (task 5.2), or their counterparts in the package doc-cli's Q3 chose. Confirm that the maintainer's answers to Q1 to Q5 are recorded in design.md. Rewrite the requirements and tasks marked as conditional where an answer differs from the recommended default. Verify with `hatch run test:test` green on the starting state.

## 2. Index: standard and declared entries

- [ ] 2.1 Create `packages/robot/src/robotcode/robot/diagnostics/library_index.py` with:
  - the frozen dataclasses `IndexEntry`, `InvalidDeclaration` and `LibraryIndex` (D1);
  - `standard_libraries()`, which returns `STDLIBS` without `Easter`/`Reserved`.

  Keep the dependency one way: it imports from `library_doc.py`, never the reverse.

  Verify with a new `tests/robotcode/robot/diagnostics/test_library_index.py`:
  - on RF 7.5 the standard group is exactly `BuiltIn`, `Collections`, `DateTime`, `Dialogs`, `OperatingSystem`, `Process`, `Remote`, `Screenshot`, `String`, `Telnet`, `XML`;
  - on every RF version it equals `STDLIBS - {"Easter", "Reserved"}`.
- [ ] 2.2 Add `declared_entries(group)` for `robotframework.libraries`, `robotframework.resources` and `robotframework.variables`. It reads `importlib.metadata.entry_points(group=...)`, takes distribution and version from `ep.dist`, and never calls `load()`/`.module`. Add the validation rules of D3.

  Verify in `test_library_index.py` with `*.dist-info` directories written to `tmp_path` and added through `monkeypatch.syspath_prepend`:
  - `Acme.Web = acme.web:Web` is listed with `acme 1.0`;
  - `acme/keywords/login.resource` is listed unchanged;
  - the variables entry is not in the index entries;
  - `AcmeLibrary` declared by two distributions yields two entries;
  - each invalid case is reported with its reason: `Bad = not a module`, an empty name, `${VAR}`, `Remote::http://127.0.0.1:8270`, a resource `acme/x.txt`, and a variables `acme/vars.toml`;
  - a variables module name `acme.vars` is accepted;
  - `acme/keywords.robot.md` is invalid on RF < 7.5 and listed on RF 7.5;
  - a declared package whose `__init__.py` raises is listed and not in `sys.modules` afterwards.

## 3. Project resources

- [ ] 3.1 Add `project_resources(root, exclude_patterns, languages)`. It collects files as `load_workspace_documents` does (`iter_files` with `.robotignore`/`.gitignore`, `include_hidden=False`, `DEFAULT_SPEC_RULES` plus the exclude patterns). It keeps suffixes in `ALLOWED_RESOURCE_FILE_EXTENSIONS`, compared case-insensitively, and returns `relative_to(root).as_posix()` names.

  Verify in `test_library_index.py` with a `tmp_path` project:
  - an unimported `resources/unused.resource` is listed;
  - `build/gen.resource` ignored through `.gitignore`, `.venv/x.resource` and `vendor/y.resource` matched by an exclude pattern are not listed;
  - `sub/Upper.RESOURCE` is listed;
  - names use `/` on every OS.
- [ ] 3.2 Q2 as recommended (rewrite this task first if Q2 is decided otherwise): list `.resource`/`.rsrc` without reading them. Read every other candidate with `ResourceFileBuilder` under `LOGGER.cache_only`, with `lang` set to the project's languages on RF ≥ 6.0 (resolved once at module level). Keep a candidate only if the build does not raise and yields at least one keyword, variable or import.

  Verify in `test_library_index.py`:
  - `tests/login.robot` with `*** Test Cases ***` and `tasks.robot` with `*** Tasks ***` are not listed;
  - `tests/__init__.robot` with `Suite Setup` and a `Library` import is not listed;
  - `common/shared.robot` with only keywords is listed;
  - `README.md` without a code block is not listed and `keywords.md` with a `robotframework` block is listed on RF 7.5, while neither is listed on RF 7.4;
  - `notes.rst` without a code block is not listed;
  - `package.json` is not listed on RF ≥ 6.1;
  - a German keyword-only `.robot` file without a `Language:` line is listed with `languages=["de"]` on RF ≥ 6.0, and not listed without languages;
  - nothing is printed (`capfd`, because Robot Framework's console output goes to `sys.__stdout__`/`sys.__stderr__`, which `capsys` does not capture).

## 4. Project Python libraries (tool section named per Q1, `robotcode-doc` recommended)

- [ ] 4.1 Create `packages/robot/src/robotcode/robot/config/library_index_config.py` next to `analyze_config.py` (D6) with:
  - `LibraryIndexConfig(BaseOptions)`: a docstring that describes the section, `libraries: Optional[Dict[str, List[str]]]` and `extend_libraries` (alias `extend-libraries`), each with a description and a TOML example under `[tool.robotcode-doc]`;
  - `get_library_index_config(robot_config: RobotConfig) -> LibraryIndexConfig`, which returns `robot_config.tool["robotcode-doc"]` when that is a `LibraryIndexConfig` and `LibraryIndexConfig()` otherwise.

  Add `"robotcode-doc": LibraryIndexConfig` to `BUILTIN_TOOL_CONFIG_CLASSES` in `packages/robot/src/robotcode/robot/config/loader.py`. No `hooks.py` registers the section. Add `robotcode_doc: Optional[LibraryIndexConfig]` (alias `robotcode-doc`, description `LibraryIndexConfig.__doc__`) to the `ToolConfig` dataclass of `scripts/create_robot_toml_json_schema.py`, next to `robotcode_analyze`. Regenerate the schema and the reference with `hatch run create-json-schema` and `hatch run robotcode config info desc > docs/03_reference/config.md`, and note the commands in the commit.

  Verify in a new `tests/robotcode/robot/config/test_library_index_config.py`. Write the configuration files to `tmp_path`, load them with `load_robot_config_from_path(...)` without `extra_tools`, and read the section with `get_library_index_config`:
  - `[tool.robotcode-doc.libraries]` in `robot.toml` and `[tool.robotcode-doc.extend-libraries]` in `.robot.toml` combine to all entries;
  - the same section in `pyproject.toml` is read;
  - with a profile `ci` in the same configuration, `combine_profiles("ci").build_command_line()` contains nothing from the section;
  - `libraries = ["CustomerLib"]` raises `ConfigTypeError` with `[tool.robotcode-doc]` in its message;
  - `get_library_index_config` returns `LibraryIndexConfig()` for a `RobotConfig()` without `tool`, for `tool={}` and for a section held as a plain dictionary (`load_robot_config_from_robot_toml_str`).

  In `tests/robotcode/cli/test_config_command.py`, with `PluginManager` patched to register no class, as the tests of `analyze-config-in-robot` there do:
  - `config info list "tool.robotcode-doc.*"` names `tool.robotcode-doc.libraries` and `tool.robotcode-doc.extend-libraries`;
  - `config show` prints the entries of a `[tool.robotcode-doc.libraries]` in the project's `robot.toml`.

  Check that the regenerated schema and `config.md` contain `libraries` and `extend-libraries` of the section.
- [ ] 4.2 Read the section where the configuration is loaded (D6):
  - in `packages/language_server/src/robotcode/language_server/cli.py`, read `get_library_index_config(robot_config)` in the `try` block next to `get_analyze_config`. Pass it as `library_index_config` through `run_server`, `RobotLanguageServer` (`robotframework/server.py`) and `RobotLanguageServerProtocol` (`robotframework/protocol.py`), as `analysis_config` is passed. The protocol falls back to `LibraryIndexConfig()` for `None`;
  - in doc-cli's command, read it with `get_library_index_config(robot_config)` from the configuration it loads (doc-cli's D7).

  Neither adds `extra_tools`. Verify with the CLI tests of 4.3 and 5.2 and the LS protocol test of 6.3. With `analyze-config-in-robot` Q4 (a), `git grep -n "extra_tools" -- packages src` also finds only the loader, `analyze/code/cli.py` and `src/robotcode/cli/commands/config.py`.
- [ ] 4.3 Add `project_libraries(config)`. It returns project library entries with their arguments from `config.libraries`, and opening them uses `get_libdoc_for_library_import(name, args, base_dir=root, variables=…)`.

  Verify in `test_library_index.py` and the CLI test module of doc-cli with a `tmp_path` project:
  - `CustomerLib` is found through `python-path`;
  - `lib/legacy/Old.py` with `["strict"]` is documented from the file below the project root with that argument;
  - an argument `${X}` is resolved from the profile's `variables`;
  - the section changes no diagnostic of a suite in the same project.

## 5. Listing and command line

- [ ] 5.1 Add `build_library_index(...)` and `index_to_markdown(index)`. The listing has the heading `# Libraries and resources`, then the sections in the order of the spec, empty sections left out, and entries sorted case-insensitively and then by distribution. Installed entries carry `(distribution version)`, project libraries their arguments, and invalid declarations their group, distribution, version and reason.

  Verify with golden strings in `test_library_index.py` built from a hand-made `LibraryIndex`, so no environment is involved.
- [ ] 5.2 In doc-cli's command, handle zero targets as the MODIFIED requirement of `documentation-cli` in this change says:
  - without lookup options, when doc-cli's mode selection does not choose the browser or `--output FILE` is given: write `index_to_markdown` and exit with code 0, also when there are invalid declarations;
  - when doc-cli's mode selection chooses the browser: fill the TUI sidebar with the groups and open a selected entry through the same code path as a command-line target, with the project root as base directory (D7);
  - `-k`, `--list`, `--search`, `--search-regex` or an `--output` directory without targets: keep doc-cli's usage error (exit code 2).

  Build the index with the root folder, the profile, the `exclude_patterns` of the `AnalyzeConfig` from `get_analyze_config` and the languages that doc-cli already loads, and with the tool section of 4.2 (D5, D8). Say in the command's help text what it does without targets, and regenerate `docs/03_reference/cli.md` with `hatch run create-cmd-line-docs` (keep only the hunks of this command, as `CONTRIBUTING.md` describes).

  Verify in doc-cli's CLI test module with a `tmp_path` project and a fake distribution whose module raises on import:
  - `robotcode doc` through a pipe prints the three expected sections, and the module is not imported;
  - `-o out.md` writes the same text;
  - with `[tool.robotcode-doc.libraries]` in the project's `robot.toml`, the listing contains its entries under `## Project libraries`, and `robotcode -p ci doc` with a profile `ci` lists the same;
  - `--list`, `--search x` and `-o site/` without targets exit with code 2;
  - with the TUI test harness of doc-cli, selecting `Collections` shows its documentation;
  - with the same harness, selecting the declared resource `acme/keywords/login.resource`, whose package directory is on `python-path`, shows its keywords.
- [ ] 5.3 Only if doc-cli offers JSON output (Q5): serialise `LibraryIndex` with the same fields. Verify with a CLI test that parses the JSON and finds the entries of 5.2.

## 6. Language server

- [ ] 6.1 Add the match function of D10 to `library_index.py`, and use it in `packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py` to rank `Library`, `Resource` and `Variables` import candidates: valid declared names of the matching group; `full = first_part + label` with `\` normalised to `/`; a match on equality or on the prefix followed by `.` or `/`; `sort_text="020_…"`; `detail` with the distributions.

  Verify the match function in `test_library_index.py`:
  - `DocTest` and `DocTest.VisualTest` match the declared `DocTest.VisualTest`, and `Doc` does not;
  - `acme` and `acme/keywords` match the declared `acme/keywords/login.resource`, also written as `acme\keywords`;
  - a name declared by two distributions names both;
  - an invalid declaration matches nothing.

  Verify the ranking with a new LS test next to `test_completion_argument_docs.py`, using the `protocol` fixture and `open_temp_document`. A fake distribution under `tmp_path`, added to `sys.path` of the test process, declares `DocTest.VisualTest`, `acme/keywords/login.resource` and `acme/vars.yaml`. The folders `DocTest` and `acme` are created next to the test document, because the `ImportsManager` worker lists the base directory but keeps the `sys.path` it was started with (D13):
  - after `Library    ` the item `DocTest` has `020_` and the distribution in its detail;
  - after `Resource    ` the folder `acme` has `020_`;
  - after `Variables    ` the folder `acme` has `020_`;
  - undeclared items keep `030_`.
- [ ] 6.2 In `complete_library_import` (`library_doc.py`), keep only internal modules with `e in STDLIBS and e not in DEFAULT_LIBRARIES`.

  Verify with a test calling `complete_library_import(None, working_dir=str(tmp_path), base_dir=str(tmp_path))` after `monkeypatch.chdir(tmp_path)` (the function changes the working directory), on every RF version:
  - `Collections` is present as `MODULE_INTERNAL`;
  - `dialogs_py` is not present, and on RF ≥ 7.4 neither is `normalizer`;
  - `tests/robotcode/repl/test_completion.py` stays green.
- [ ] 6.3 After `vscode-doc-browser` has added its LS part (which resolves targets whose `context` is a workspace folder URI, its D4): register `robot/documentation/getIndex` (`threaded=True`, parameters `{uri}`, result `{entries, invalid}` as in D9, variables left out), built per request for the workspace folder of `uri`, with that folder's exclude patterns and languages and the tool section the protocol holds (4.2).

  Verify with an LS protocol test on the `protocol` fixture's workspace folder, which is only read, and a fake distribution under `tmp_path` added to `sys.path` of the test process:
  - the result contains `BuiltIn` (standard), the fake installed library and `resources/firstresource.resource`;
  - with `LibraryIndexConfig(libraries={"CustomerLib": []})` set as `library_index_config` on the fixture's protocol through `monkeypatch.setattr`, the result contains the project library `CustomerLib`;
  - the invalid list contains `Bad`;
  - the module of the fake distribution is not imported;
  - `robot/documentation/getDocument` with the D7 target of `Collections` and of `resources/firstresource.resource` (`context` = the workspace folder URI) returns their pages.

## 7. VS Code (after vscode-doc-browser)

- [ ] 7.1 In the webview sources of vscode-doc-browser (`vscode-client/documentationBrowser/`) and its panel manager (`vscode-client/extension/documentationBrowser.ts`), add the index view to the sidebar:
  - it posts the new message `loadIndex(folderUri)` when shown and on its refresh button; the extension accepts it only for the URI of an open workspace folder and answers with the result of `robot/documentation/getIndex` (D9);
  - it shows the groups in the order of the listing, with a name filter;
  - invalid declarations are shown with their reason and are not clickable;
  - selecting an entry posts the D7 target `{kind, name, args, baseDir: <workspace folder path>, context: <workspace folder URI>}` with the existing `open` message to the same panel.

  Verify with `npm run lint` and `npm run compile`, and manually in VS Code: open the browser from "Open in Documentation Browser", switch to the index view, filter for `Coll`, open `Collections`, and open a project resource.
- [ ] 7.2 Only if Q4 is confirmed: contribute the browser's open command to the command palette in `package.json`; run without a target, it opens the panel on the index view for the workspace folder of the active editor. Verify with `npm run lint` and `npm run compile`, and manually in VS Code.

## 8. Documentation and agent skill

- [ ] 8.1 Only if Q3 is confirmed as recommended: write `docs/03_reference/library-entry-points.md` for library authors with the content of D12, including `pyproject.toml` examples and that RobotCode ranks declared entries first in import completion. Link it from the `robotcode doc` page and add it to the list in `docs/03_reference/index.md`. Verify with `npm run docs:build`.
- [ ] 8.2 Extend the `robotcode doc` page of doc-cli with a section on the listing without targets:
  - what the groups contain;
  - that nothing is imported;
  - how project resources are chosen (per Q2);
  - project libraries: the tool section (name per Q1) with `libraries` and `extend-libraries`, module and file names, arguments, and that the section is not per profile. Link its entry in `docs/03_reference/config.md`.

  If Q3 places the convention document outside RobotCode's docs, mention the completion ranking in this section instead, since the docs have no page on completion. Verify with `npm run docs:build`.
- [ ] 8.3 In `/home/daniel/develop/robot/robotframework-agent-plugins` (`plugins/robotcode/skills/robotcode/SKILL.md`, the documentation lookup that doc-cli switched to `robotcode doc`), add that `robotcode doc` without targets lists the available libraries and resources. Then re-sync the vendored copy with `hatch run build:sync-chat-plugin`. Verify with `hatch run build:sync-chat-plugin --check`.

## 9. Verification

- [ ] 9.1 Run `hatch run lint:all` and `hatch run test:test` (full RF matrix 5.0 to 7.5) and confirm both pass. Confirm that CI passes on Linux, Windows and macOS, especially the POSIX path names of the project scan and the `.dist-info` fixtures. Confirm that no regression baseline under `_regtest_outputs` changed. No baseline records the `sort_text` of import completion today.
