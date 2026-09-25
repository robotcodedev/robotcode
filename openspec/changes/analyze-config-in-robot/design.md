# Design: analyze-config-in-robot

## Context

See proposal.md. Verified facts:

- **The module.** `packages/analyze/src/robotcode/analyze/config.py` holds, in this order, `ModifiersConfig`, `CacheConfig`, `ExitCodeMask`, `ExitCodeMaskLiteral`/`ExitCodeMaskList`, `CodeConfig` and `AnalyzeConfig`, whose first fields are `code`/`extend_code`. It imports only the standard library, `robotcode.robot.config.model` (`BaseOptions`, `field`) and `robotcode.robot.diagnostics.workspace_config`, which itself imports only `robotcode.core`. `robotcode-robot` depends on `robotframework`, `tomli`, `platformdirs` and `robotcode-core`, so the analysis part fits there without a new dependency. `robotcode.robot.config.model` does not import the loader or the new module, so there is no import cycle. The `code` part has two users: `code/cli.py` (`ExitCodeMask`, `CodeConfig`, `analyzer_config.code` for the exit code mask and `collect_unused`, which it passes to `CodeAnalyzer`) and `tests/robotcode/analyze/code/test_result_collector.py` (`ExitCodeMask`, including `TestExitCodeMaskParse`). The other readers use only the analysis part: `language_server/cli.py` and `dump_model.py` call `to_workspace_analysis_config()`, and `cache/cli.py` reads `cache.cache_dir`. No test patches a name in `robotcode.analyze.config`. Neither `docs/`, `dev-docs/`, the chat plugins nor the robotframework-agent-plugins repository mention the module path.
- **Parsing.** `robotcode.core.utils.dataclasses.from_dict` is called with its default `strict=False`, which ignores unknown keys. In a prototype, a class with only the analysis part read a section with a `[tool.robotcode-analyze.code]` table without an error and dropped the table, and a subclass with `code`/`extend_code` read the same section completely. `BaseOptions.add_options` takes the type hints of the instance's own class, so it combines the subclass's fields across files as well.
- **Loader.** `load_config_from_path` creates the `tools` dictionary only when `extra_tools` is not empty. It then creates one instance per class, reads `[tool.<name>]` of every configuration file (`robot.toml`, `.robot.toml` and `pyproject.toml` alike) with `add_options`, and replaces `RobotConfig.tool` with that dictionary. So with `extra_tools`, `tool` holds only the typed sections, and any other `[tool.*]` section is dropped. Without it, `tool` keeps the `[tool.*]` sections as plain dictionaries, those of the last file that has any (a `pyproject.toml` has none, because its `RobotConfig` is read from `[tool.robot]`). The default configuration entry (`__no_user_config__.toml`, used when no user configuration file exists) is skipped before the tools are read, so `tool` can be an empty dictionary. The five places that load the section with `extra_tools={"robotcode-analyze": AnalyzeConfig}` and look it up with a fallback to `AnalyzeConfig()` are `language_server/cli.py` (lines 91-97), `analyze/code/cli.py` (507-513), `analyze/cache/cli.py` (37-41 and 384-388; these two check `isinstance` instead of falling back) and `analyze/dump_model.py` (87-93). `load_robot_config_from_robot_toml_str` does not read tool sections typed and is only used by tests. No code reads an untyped `[tool.*]` section from `RobotConfig.tool`.
- **Registration and the config command.** `robotcode-analyze`'s `hooks.py` registers `ToolConfig("robotcode-analyze", AnalyzeConfig)` through `register_tool_config_classes`, and no other package registers a tool section. `robotcode config show` passes the registered classes as `extra_tools`, and `config info list/desc` lists their fields (`get_config_fields` in `src/robotcode/cli/commands/config.py`). `robotcode-robot` has no `robotcode` entry point and no dependency on `robotcode-plugin`, so it cannot register hooks. The root package, which holds the config command, depends on `robotcode-robot`. Observed today:
  - In the development environment, `config show` validates the section and does not print an unregistered `[tool.foo]` section.
  - In a virtual environment with only `core`, `plugin`, `robot`, `modifiers`, `runner` and the root package, `config show` printed `[tool.robotcode-analyze]` including its `code` table and `[tool.foo]` as plain data, a string where a list belongs passed, and `config info list "tool.*"` printed `Total: 0`.
  - In the development environment, `config show` prints an empty `[tool.robotcode-analyze]` table for a `robot.toml` without that section, because the loader creates an instance of every class in `extra_tools`.
  - `config show` prints the fields of the section in the order of the dataclass fields, through `tomli_w` or `as_json` (`Application.print_data`). Today `code` is the first field. A dataclass subclass puts its own fields after those of its base class, so in a prototype the subclass printed the same keys and values as today, but the `code` table after the other keys, in TOML and in JSON. `config info` sorts its keys, and the schema script writes with `sort_keys=True`. No code or test in the repository reads the output of `config show`.
- **Validation today.** With `ignore = "VariableNotFound"` (a string instead of a list) in `[tool.robotcode-analyze.modifiers]`, `robotcode profiles list` and `robotcode discover tests` succeed. `config show` in the development environment fails with `Parsing "…/robot.toml" failed: Reading [tool.robotcode-analyze] failed: Invalid value for "modifiers.ignore": Value 'VariableNotFound' must be of type `List | None` but is `str`.`, and a prototype of the built-in section raised the same message as a `ConfigTypeError`. A string for the top-level `python-path` stops `robotcode profiles list` with exit code 255. `robot`, `discover` and `repl` load the configuration in `handle_robot_options` (`runner/cli/robot.py`), which turns a `TypeError` or `ValueError` into a `click.ClickException`. `rebot`, `libdoc`, `testdoc`, `results` and `profiles` call `load_robot_config_from_path` themselves. The wrapper detection in `src/robotcode/cli/__init__.py` catches every exception and leaves the report to the command.
- **Import cost.** In the runner-only environment above, importing `robotcode.robot.diagnostics.workspace_config` after the CLI has loaded its plugins took about 4 ms, because the LSP types it pulls in are already loaded by then.
- **Generated files.** `hatch run create-json-schema` writes only `docs/public/schemas/robot.toml.json`. `scripts/create_robot_toml_json_schema.py` imports `AnalyzeConfig` from `robotcode.analyze.config` and lists the section in its own `ToolConfig` dataclass, with `AnalyzeConfig.__doc__` as the description. It does not use the hook. mashumaro names a definition after the class's `__name__` and uses it as the definition's title, and the script's plugin takes the definition's description from the class docstring. Prototypes against the committed schema, which the unchanged script reproduces byte-identically:
  - A subclass named `AnalyzeConfig` with the docstring `robotcode-analyze configuration.` gave a byte-identical schema.
  - The same subclass named `AnalyzeCodeConfig` changed three lines: the definition key, its `title` and the `$ref` of `tool.robotcode-analyze`.

  `docs/03_reference/config.md` (`hatch run robotcode config info desc`) contains no class name of the section. Its 54 `tool.robotcode-analyze.*` entries are exactly the fields of the subclass. The analysis part alone has 46, without `code`, `extend-code` and their six sub-keys. The committed file is reproduced byte-identically today. `etc/robot.toml.json` is a frozen copy for older RobotCode versions (`fafb1681`) and is not written by the script.
- **Git.** Git records no renames and detects them when it compares. In a throwaway repository, a new file with the analysis part plus the trimmed old file showed up in `git diff -C` as a copy. `git log --follow` on the new file reached the original commit, and `git blame -C` attributed 378 of its 380 lines to it.
- **Duplicated `-v/-V/-P` merging.** `code()` in `analyze/code/cli.py` (lines 519-535) and `dump_model()` in `analyze/dump_model.py` (99-115) contain the same code, run on the profile returned by `combine_profiles(...).evaluated_with_env()`. Each `--variable` is split at the first `:` into name and value, with an empty value when there is no `:`, and added to `variables`. The `--pythonpath` entries are appended to `python_path` and the `--variablefile` entries to `variable_files`. Each field is created when it is `None`. `semantic-model-inspection` requires `dump-model` to use "the same configuration path as `robotcode analyze code` (robot.toml, profiles, `-v`/`-V`/`-P` overrides)". `tests/robotcode/analyze/test_dump_model_cli.py` runs `robotcode analyze dump-model` in-process. No test runs `analyze code` through its CLI, `analyze cache`'s configuration loading or the language server's.
- **Packaging.**
  - The dependency and the import came with `fa37dba7` (`feat(robot.toml): introduce new settings for analysis in robot.toml`, v0.91.0).
  - In the root `pyproject.toml`, every extra except `all` names exactly one package (`languageserver = ["robotcode-language-server==2.7.0"]`, `analyze = ["robotcode-analyze==2.7.0"]`). `all` and the `all` dependency group contain both.
  - hatch: the `default` and `lint` environments use the `all` group, and `hatch-test` installs every package through `scripts/install_packages.py`.
  - Bundling: `scripts/package.py` and `scripts/install_bundled_editable.py` install every directory under `packages/` into the git-ignored `bundled/libs`, with `--no-deps`. The IntelliJ plugin copies the same `bundled/` directory (`prepareSandboxConfig` in `build.gradle.kts`).
  - Neither the VS Code extension (`vscode-client/extension`) nor the IntelliJ plugin sources call `robotcode analyze` or install extras. The chat plugins ask for `robotcode[runner,analyze,repl]` explicitly.
  - All packages are versioned in lockstep with exact `==` pins (`scripts/update_git_versions.py`), and there is no lock file.
  - The plugin manager loads every entry point when the CLI starts, and `language_server/hooks.py` imports its `cli.py`, so an import error in that file breaks every `robotcode` command. The same holds for `analyze/hooks.py`, whose `cli.py` imports `cache/cli.py`, `code/cli.py` and `dump_model.py`.
- **Docs.** `docs/03_reference/cli.md` and `analyzing-code.md` describe `analyze` as a separate optional package (`pip install robotcode[analyze]`), and nothing says that `languageserver` brings it. `.github/copilot-instructions.md` draws `analyze → language_server` in its package graph and states "`language_server` depends on `jsonrpc2`, `robot`, `analyze`, and the root `robotcode` CLI". No document says which installation `config show`/`info` know the section in.
- **Release.** commitizen (`cz_conventional_commits`, `version_scheme = "semver2"`, `major_version_zero` commented out) turns a breaking commit into a major version. The last breaking commits (`feat!:` for Python 3.10+ and for the Robotidy removal) were released as v2.0.0.

## Goals / Non-Goals

**Goals:**
- `robotcode-robot` reads the analysis part of `[tool.robotcode-analyze]` by itself, for the language server, `doc-cli` and `library-index`.
- `robotcode config show`/`info` know the analysis part in every installation, and the `code` part where `robotcode-analyze` is installed.
- `robotcode-language-server` neither imports nor depends on `robotcode-analyze`.
- `robotcode analyze code` reads the whole section as before. The JSON schema and the configuration reference do not change.

**Non-Goals:**
- Renaming the section or its keys, or changing fields, docstrings or `to_workspace_analysis_config()`.
- Moving anything else out of `robotcode-analyze` (`CodeAnalyzer`, `RobotFrameworkLanguageProvider`).
- Sharing the click declarations of `-v/-V/-P`. Only the merging moves.
- Keeping unregistered `[tool.*]` sections in `RobotConfig.tool` or in the output of `config show`.
- A hook or registry in `robotcode-robot`. The built-in sections are a fixed dictionary.

## Decisions

### D1: A new module for the analysis part, the `code` part stays in `robotcode.analyze.config`

`packages/robot/src/robotcode/robot/config/analyze_config.py` is a new file. It contains `ModifiersConfig`, `CacheConfig` and `AnalyzeConfig` with the analysis fields, the docstrings and `to_workspace_analysis_config()`, copied unchanged from the old module, plus `get_analyze_config` (D5). Only `code`, `extend_code`, `ExitCodeMask*`, `CodeConfig` and the imports that only they need are left out. The module name `robotcode.robot.config.analyze_config` is fixed, because `doc-cli` and `library-index` refer to it.

`packages/analyze/src/robotcode/analyze/config.py` keeps its path and is trimmed to `ExitCodeMask`, `ExitCodeMaskLiteral`, `ExitCodeMaskList`, `CodeConfig` and the subclass (D2). The subclass imports the base class under another name, adds `code` and `extend_code` unchanged and has the same docstring. Its fields follow those of the base class, so `config show` prints the `code` table after the other keys of the section instead of first, with the same keys and values (Context, Risks). No `git mv` is used: the old path stays, so git records a modified file and a new one, and `git diff -C`, `git log --follow` and `git blame -C` still lead the copied lines to their history (Context).

Rejected: moving the `code` part to a new module such as `robotcode.analyze.code.config`, so that git detects a rename of `analyze/config.py`. The history is reachable either way, and the new path would change `hooks.py`, `code/cli.py`, the schema script and `test_result_collector.py`.

### D2: The subclass keeps the name `AnalyzeConfig` (Q3)

The tasks assume that the subclass is named `AnalyzeConfig`, like the base class, with the docstring `robotcode-analyze configuration.`. Then `robotcode.analyze.config.AnalyzeConfig` still means the whole section, and:
- `scripts/create_robot_toml_json_schema.py` stays unchanged. It keeps importing the whole class from `robotcode.analyze.config` and produces a byte-identical schema (Context, prototype). The script runs in the development environment, where `robotcode-analyze` is installed.
- `hooks.py` stays unchanged and registers the subclass.
- `code/cli.py` keeps its loading block (D5), and `test_result_collector.py` keeps its import of `ExitCodeMask`.
- `config.md` does not depend on the name (Context).

With another name, such as the placeholder `AnalyzeCodeConfig`, `hooks.py`, `code/cli.py` and the schema script import it by that name, and the regenerated schema changes the definition name, its title and one `$ref` (three lines, Context).

### D3: `robotcode-robot`'s loader knows `[tool.robotcode-analyze]` as a built-in section

`packages/robot/src/robotcode/robot/config/loader.py` gets a module-level dictionary `BUILTIN_TOOL_CONFIG_CLASSES: Dict[str, Type[Any]] = {"robotcode-analyze": AnalyzeConfig}`, with the base class from `.analyze_config`. `load_robot_config_from_path` passes `{**BUILTIN_TOOL_CONFIG_CLASSES, **(extra_tools or {})}` to `load_config_from_path`. A class passed in `extra_tools` for the same name therefore replaces the built-in one. `load_config_from_path`, whose `config_type` can be any options class, and `load_robot_config_from_robot_toml_str` stay as they are. `library-index` adds `"robotcode-doc"` to the same dictionary.

Consequences (Context):
- Every `RobotConfig` from `load_robot_config_from_path` has a typed `tool["robotcode-analyze"]` as soon as a configuration file was read.
- `RobotConfig.tool` no longer holds unregistered `[tool.*]` sections as plain dictionaries. No code reads them. `config show` printed them only in installations where nothing is registered.
- Every command that loads the configuration validates the analysis part and stops on an invalid value with the loader's message, for example `robot`, `discover`, `profiles`, `rebot`, `libdoc`, `testdoc`, `results` and `repl` (Q4). The `code` table is ignored by the base class, so only `analyze code`, and `config` with `robotcode-analyze` installed, validate it.

Rejected: registering the section from `robotcode-robot` through a hook, since the package has no plugin dependency and no entry point. Also rejected: a separate parameter to switch the built-in sections off for commands that do not read them. That would add a mechanism the maintainer did not ask for (Q4).

### D4: `robotcode config` uses the built-in sections and the registered classes

`config show` stays unchanged: it passes the registered classes as `extra_tools`, and the loader adds the built-in sections (D3). `get_config_fields()` iterates over `{**BUILTIN_TOOL_CONFIG_CLASSES, **{entry.tool_name: entry.config_class for entry in PluginManager.instance().tool_config_classes}}` instead of the registered classes alone. It keeps the `dataclasses.is_dataclass` check and the sorting by key. A registered class wins for the same name. `robotcode-analyze` keeps registering its subclass, so with it installed `config show`/`info` include the `code` keys. Without it, they know the analysis part.

### D5: `get_analyze_config` and the readers of the section

`analyze_config.py` gets `get_analyze_config(robot_config: RobotConfig) -> AnalyzeConfig`. It returns `robot_config.tool["robotcode-analyze"]` when that is an `AnalyzeConfig` (the built-in class or a subclass passed in `extra_tools`), and `AnalyzeConfig()` otherwise: when `tool` is `None`, empty (no configuration file read), or holds the section as a plain dictionary (a `RobotConfig` from `load_robot_config_from_robot_toml_str`). It is a free function and not a method of `RobotConfig`, because `analyze_config.py` imports `model.py`, and a method would need the reverse import.

`language_server/cli.py`, both helpers in `cache/cli.py` and `dump_model.py` load the configuration without `extra_tools` and read the section with `get_analyze_config`. `dump_model.py` needs only `to_workspace_analysis_config()` and none of the `code` options (Context), so it reads the built-in class like the others. The approved plan had `dump-model` read the subclass, like `analyze code`. The command has no option for the `code` table and reads none of its fields, so the design deviates from the plan here (Q5). `cache/cli.py` drops its `isinstance` check, which the function now does.

`analyze code` is the only reader of the `code` part. It keeps lines 507-513 as they are: it passes its subclass as `extra_tools={"robotcode-analyze": AnalyzeConfig}`, which replaces the built-in class, and falls back to its own `AnalyzeConfig()`. Rejected:
- A type parameter on `get_analyze_config`, only for this one call site.
- A second accessor in `robotcode-analyze`.
- `get_analyze_config` plus a cast or `isinstance` in `code/cli.py`. Its fallback is the base class without `code`, so `code/cli.py` would still need its own fallback.

### D6: `merge_variable_and_path_options` in `robotcode.robot.config.utils`

`packages/robot/src/robotcode/robot/config/utils.py` gets `merge_variable_and_path_options(profile: RobotBaseProfile, *, variable: Sequence[str] = (), variablefile: Sequence[str] = (), pythonpath: Sequence[str] = ()) -> None`. It changes `profile` in place exactly as the duplicated code does today (Context), and the parameter names match the click parameters of both commands. `code()` and `dump_model()` call it where the duplicated code is today, after `combine_profiles(...).evaluated_with_env()`. `doc-cli` calls it the same way. The function sits next to `get_config_files` in `robotcode-robot`, which `analyze`, `repl` and every other command package depend on.

### D7: No re-export

After the change, `robotcode.analyze.config` defines `AnalyzeConfig` (the subclass), `CodeConfig`, `ExitCodeMask`, `ExitCodeMaskLiteral` and `ExitCodeMaskList`. `ModifiersConfig` and `CacheConfig` are importable only from `robotcode.robot.config.analyze_config`, and `code/cli.py` imports them from there. Reasons:
- All packages are released in lockstep with exact `==` pins, so every `robotcode-analyze` finds the new module in the `robotcode-robot` it requires.
- After the change, no code, test or documentation in the repository imports the two classes from the old path.
- The module is not documented as a Python API.

Rejected: re-exporting the two classes from `robotcode.analyze.config`. That would be a second import path to maintain, and under mypy's `implicit_reexport = false` it would need explicit re-exports, all for third-party imports nobody has asked for.

### D8: Language server and packaging

`language_server/cli.py` imports `get_analyze_config` instead of `AnalyzeConfig`, loads the configuration without `extra_tools`, and computes `analysis_config = get_analyze_config(robot_config).to_workspace_analysis_config()`. The rest of the file stays as it is. `"robotcode-analyze==2.7.0"` is removed from `packages/language_server/pyproject.toml`. The root extras and dependency groups, the hatch environments, the bundled libraries and the IntelliJ plugin stay as they are, because none of them relies on the transitive dependency (Context). `pip install robotcode[languageserver]` no longer installs `robotcode analyze` (proposal). The commit is not marked as breaking, neither with `!` nor with a `BREAKING CHANGE:` footer, so `cz bump` produces no major version (maintainer decision).

Rejected: adding `robotcode-analyze` to the root `languageserver` extra to keep the command there. Every extra except `all` names exactly one package, and the extra would keep the coupling that the change removes from the package (Q2).

### D9: No specs, targeted tests, regenerated files

- **Specs.** No requirement of any capability changes, so `skip_specs: true` (proposal, Capabilities). A requirement such as "the language server package does not depend on the analyze package" would describe package structure, not observable behaviour, and is not written.
- **Tests.** New tests cover the parts that `robotcode-robot` and the config command now own:
  - the loader's built-in section, including a section with a `code` table read by the base class, an invalid value, and a subclass passed in `extra_tools`;
  - `get_analyze_config` and its defaults;
  - `merge_variable_and_path_options`;
  - `config show`/`info` with and without the registration of `robotcode-analyze`.

  The tests in `robotcode-robot` use a subclass defined in the test instead of the one from `robotcode-analyze`. The config command tests patch `PluginManager` in `robotcode.cli.commands.config`, where it is used, and `get_user_config_file` in `robotcode.robot.config.utils`, so that neither the installed plugins nor the developer's user configuration affect them. `test_dump_model_cli.py` covers `dump-model`'s call of `get_analyze_config` and of the merging function. `analyze code`, `analyze cache` and the language server are checked by hand (tasks 4.2 and 6.1). Rejected: a test asserting that importing the language server loads no `robotcode.analyze` module. The development environments install every package, so such a test would catch a new import but not a new dependency entry in `pyproject.toml`.
- **Generated files.** The schema and `config.md` are regenerated with the documented commands, and no diff is expected (Context, D2). `etc/robot.toml.json` is left alone.

## Risks / Trade-offs

- [An invalid value in the analysis part of `[tool.robotcode-analyze]` now stops `robot`, `discover` and every other command that loads the configuration, for example a test run in CI (Q4)] → the message names the file, the section and the key. The same value already fails in `analyze code` and is reported by the language server, and the rest of `robot.toml` is validated the same way. The release notes mention it.
- [Installations with only `robotcode[languageserver]`/`robotcode-language-server` lose `robotcode analyze`, for example setups for Neovim, Sublime Text or Helix (README)] → the documented installation (`robotcode[analyze]`, `robotcode[all]`) is unchanged. `cli.md` states it, and the release notes mention it. The change is not marked as breaking (D8).
- [Third-party code imports `ModifiersConfig` or `CacheConfig` from `robotcode.analyze.config`] → none is known. It fails at import time with an `ImportError`, and the release notes name the new module.
- [Two classes named `AnalyzeConfig` (D2)] → only `code/cli.py`, `hooks.py` and the schema script import the subclass, all from `robotcode.analyze.config`. Every other reader imports the base class from `robotcode.robot.config.analyze_config`.
- [`config show` without `robotcode-analyze` no longer prints the `code` table or unregistered `[tool.*]` sections] → accepted. With `robotcode-analyze` installed, which includes the bundled libraries of both editor plugins, it prints the same keys and values.
- [With `robotcode-analyze` installed, `config show` prints the `code` table after the other keys of the section (D1)] → accepted. No code or test in the repository reads the output of `config show`.

## Migration Plan

Code, packaging, tests and docs land in one commit; rollback is a revert. The change is applied before `doc-cli`, `library-index` and `library-keyword-set-declaration`, which build on the new module. Users who want `robotcode analyze` next to the language server install `robotcode[languageserver,analyze]` or `robotcode[all]`.

## Open Questions

Q1 (whether the commit is marked as breaking) is decided: it is not (D8). The remaining questions keep their numbers.

- **Q2 `languageserver` extra.** Should `robotcode-analyze` be added to the root `languageserver` extra, so that `pip install robotcode[languageserver]` keeps `robotcode analyze` while the package itself stays independent? **Recommended:** no (D8). The tasks assume no. With yes, task 4.1 adds the pin to the extra in `pyproject.toml` and task 5.2 drops the `cli.md` sentence.
- **Q3 Name of the subclass in `robotcode-analyze`.** (a) `AnalyzeConfig`, like the base class. The schema stays byte-identical, and `hooks.py`, the schema script and `test_result_collector.py` stay unchanged. (b) A name of its own, such as `AnalyzeCodeConfig`. Readers can tell the two classes apart by name, but the regenerated schema changes three lines (definition name, title, `$ref`), and `hooks.py`, `code/cli.py` and the schema script change their imports. **Recommended:** (a), because the maintainer requires a byte-identical schema. The tasks assume (a). With (b), task 1.1 gives the class that name and changes `hooks.py`, the import and the loading block of `code/cli.py` and the script's import accordingly, task 2.2 registers the class by that name, and task 5.1 expects exactly this three-line diff in the schema.
- **Q4 Validation by every command.** With the built-in section in the loader (D3), every command that loads the configuration validates the analysis part, where today only `config` (with `robotcode-analyze`), `analyze` and the language server read it. (a) Accept this. It follows from the decision that the loader always reads the section, and the rest of `robot.toml` is validated the same way (Context). (b) Keep the loader unchanged: `BUILTIN_TOOL_CONFIG_CLASSES` stays in `loader.py`, and `config show`, the four readers of D5 and later `doc-cli` pass it as `extra_tools` themselves. Then `robot`, `discover` and the other commands keep ignoring the section. **Recommended:** (a). The tasks assume (a). With (b), task 2.1 only adds the dictionary and tests loading with it passed in `extra_tools`, `config show` (task 2.2) and the readers of task 3.1 pass it as `extra_tools` (merged with the registered classes in `config show`), and task 6.1 checks that `robotcode robot --dryrun` ignores the invalid value.
- **Q5 Readers of the subclass.** The approved plan said that `get_analyze_config` replaces the loading block at all five places and that `analyze code` and `dump-model` read the subclass. The design uses `get_analyze_config` at four places and lets only `analyze code` read the subclass (D5): `analyze code` keeps its block, because the fallback of `get_analyze_config` has no `code` field, and `dump-model` reads the base class, because it uses no `code` option. (a) As designed. (b) `dump-model` also keeps its loading block with the subclass, as `analyze code` does. **Recommended:** (a). `dump-model` then loads like every other reader that uses only the analysis part, and `doc-cli` (its D7) loads the configuration the way `dump-model` does after (a). The tasks assume (a). With (b), task 3.1 leaves the loading block of `dump_model.py` as it is and task 3.2 removes only its merging code, the `git grep` check of task 3.1 also finds `analyze/dump_model.py`, and `doc-cli` D7 describes its loading without referring to `dump-model`.
