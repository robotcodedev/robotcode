# Tasks: analyze-config-in-robot

## 1. Split the configuration model

- [ ] 1.1 Create `packages/robot/src/robotcode/robot/config/analyze_config.py` with `ModifiersConfig`, `CacheConfig` and `AnalyzeConfig` copied unchanged from `packages/analyze/src/robotcode/analyze/config.py`, without `code`/`extend_code`, `ExitCodeMask`, `ExitCodeMaskLiteral`, `ExitCodeMaskList`, `CodeConfig` and the imports only they use. Add `get_analyze_config(robot_config: RobotConfig) -> AnalyzeConfig` (D5). In the same task, trim `packages/analyze/src/robotcode/analyze/config.py` to `ExitCodeMask`, `ExitCodeMaskLiteral`, `ExitCodeMaskList`, `CodeConfig` and the subclass `AnalyzeConfig` of the base class, with the docstring `robotcode-analyze configuration.` and the unchanged `code`/`extend_code` fields (D1, D2, Q3). Also import `CacheConfig` and `ModifiersConfig` in `packages/analyze/src/robotcode/analyze/code/cli.py` from `robotcode.robot.config.analyze_config`, with no re-export (D7). Every `robotcode` command imports `code/cli.py` when it starts, so these changes go together. Leave `hooks.py`, `scripts/create_robot_toml_json_schema.py` and `tests/robotcode/analyze/code/test_result_collector.py` unchanged (D2). Verify:
  - save `git show HEAD:packages/analyze/src/robotcode/analyze/config.py` to a scratch file, and `git diff --no-index` against the new module shows only the removed `code` part with the imports only it uses, and the added `get_analyze_config` with its import of `RobotConfig`;
  - `git grep -n -E "from (robotcode\.analyze\.|\.+)config import .*(ModifiersConfig|CacheConfig)"` finds nothing;
  - `hatch run test:test -- tests/robotcode/analyze` passes.
- [ ] 1.2 Add `tests/robotcode/robot/config/test_analyze_config.py`:
  - `get_analyze_config` returns defaults (`AnalyzeConfig()`) for a `RobotConfig()` without `tool`, for `tool={}` and for a section held as a plain dictionary;
  - it returns the loaded section for a `robot.toml` in `tmp_path` loaded with `load_robot_config_from_path`;
  - it returns an instance of a subclass defined in the test when that subclass is passed in `extra_tools`.

## 2. Built-in tool section

- [ ] 2.1 In `packages/robot/src/robotcode/robot/config/loader.py`, add `BUILTIN_TOOL_CONFIG_CLASSES: Dict[str, Type[Any]] = {"robotcode-analyze": AnalyzeConfig}` with the base class, and pass `{**BUILTIN_TOOL_CONFIG_CLASSES, **(extra_tools or {})}` from `load_robot_config_from_path` to `load_config_from_path` (D3, Q4). Leave `load_config_from_path` and `load_robot_config_from_robot_toml_str` unchanged. Verify with new tests in `tests/robotcode/robot/config/test_loader.py`, with configuration files in `tmp_path`:
  - without `extra_tools`, `tool["robotcode-analyze"]` is an `AnalyzeConfig` with the values of `[tool.robotcode-analyze]` and `[tool.robotcode-analyze.modifiers]`;
  - a section that also has a `[tool.robotcode-analyze.code]` table loads without an error, and the result has no `code` attribute;
  - `ignore = "VariableNotFound"` raises `ConfigTypeError` with `[tool.robotcode-analyze]` in its message;
  - a subclass defined in the test with one extra field, passed in `extra_tools` for `robotcode-analyze`, replaces the built-in class and reads that field.
- [ ] 2.2 In `src/robotcode/cli/commands/config.py`, let `get_config_fields()` iterate over `BUILTIN_TOOL_CONFIG_CLASSES` merged with the registered classes, with the registered class winning for the same name (D4). `config show` stays unchanged. Verify with a new `tests/robotcode/cli/test_config_command.py`, cross-platform with `tmp_path`:
  - invoke the `robotcode` group in-process with `CliRunner` and `--root <tmp_path> --format json`;
  - patch `robotcode.cli.commands.config.PluginManager` so that `instance().tool_config_classes` is either empty or `[ToolConfig("robotcode-analyze", AnalyzeConfig)]` with the class from `robotcode.analyze.config`;
  - patch `robotcode.robot.config.utils.get_user_config_file` to return `None`;
  - use a `robot.toml` with `[tool.robotcode-analyze.modifiers]` and `[tool.robotcode-analyze.code]`.

  Without the registration, `config show` prints `modifiers` and no `code` under `tool.robotcode-analyze`, and `config info list "tool.robotcode-analyze.*"` names `tool.robotcode-analyze.modifiers.ignore` but no `tool.robotcode-analyze.code` key. With the registration, both commands include the `code` keys. Without the registration, `config show` with `ignore = "VariableNotFound"` fails.

## 3. Readers of the section

- [ ] 3.1 Load the configuration without `extra_tools` and read the section with `get_analyze_config` in:
  - `packages/language_server/src/robotcode/language_server/cli.py` (D8);
  - both helpers in `packages/analyze/src/robotcode/analyze/cache/cli.py`, which drop their `isinstance` check;
  - `packages/analyze/src/robotcode/analyze/dump_model.py`.

  Remove the imports of `AnalyzeConfig` that are no longer used. Leave the loading block of `analyze/code/cli.py` (lines 507-513) as it is (D5). Verify:
  - `git grep -n "extra_tools" -- packages src` finds only the loader, `analyze/code/cli.py` and `src/robotcode/cli/commands/config.py`;
  - `git grep -n "robotcode.analyze" -- packages/language_server` finds nothing;
  - `hatch run test:test -- tests/robotcode/analyze tests/robotcode/language_server` passes.
- [ ] 3.2 Add `merge_variable_and_path_options(profile, *, variable=(), variablefile=(), pythonpath=())` to `packages/robot/src/robotcode/robot/config/utils.py` (D6). Replace the duplicated code in `code()` of `analyze/code/cli.py` and in `dump_model()` of `analyze/dump_model.py` with a call to it. Verify with a new `tests/robotcode/robot/config/test_utils.py` on a `RobotBaseProfile()`:
  - `-v NAME:value`, `-v NAME` (empty value) and `-v NAME:a:b` (value `a:b`);
  - `variablefile` and `pythonpath` entries appended in order;
  - existing `variables`, `variable_files` and `python_path` kept and extended;
  - empty arguments leave `None` fields `None`.

  `hatch run test:test -- tests/robotcode/analyze/test_dump_model_cli.py` also passes.

## 4. Language server dependency

- [ ] 4.1 Remove `"robotcode-analyze==2.7.0"` from `packages/language_server/pyproject.toml`. Leave the root `pyproject.toml` extras and dependency groups and `hatch.toml` as they are (D8, Q2). Verify that `git grep -n -E "robotcode\.analyze|robotcode-analyze==" -- packages/language_server` finds nothing.
- [ ] 4.2 From the repository root, create a fresh virtual environment and run `uv pip install ./packages/core ./packages/plugin ./packages/robot ./packages/jsonrpc2 ./packages/language_server .` in it. Before the change, the same command also installs `robotcode-analyze` from the workspace. Verify in that environment:
  - `uv pip list` shows no `robotcode-analyze`.
  - `robotcode --help` lists `language-server` and not `analyze`.
  - In a project whose `robot.toml` has `[tool.robotcode-analyze.modifiers]` with `ignore = "VariableNotFound"` (a string instead of a list), `robotcode --verbose language-server --stdio < /dev/null` reports `Reading [tool.robotcode-analyze] failed: …`.
  - With `ignore = ["VariableNotFound"]` and a `[tool.robotcode-analyze.code]` table, the same command starts and ends without an error.
  - With the same file, `robotcode config show` prints the analysis part without the `code` table, and `robotcode config info list "tool.*"` lists the analysis keys and no `tool.robotcode-analyze.code` key (D4).

## 5. Generated files and docs

- [ ] 5.1 Run `hatch run create-json-schema` and `hatch run robotcode config info desc > docs/03_reference/config.md` (CONTRIBUTING.md). Verify with `git diff --exit-code docs/public/schemas/robot.toml.json docs/03_reference/config.md` that neither file changed (D2, D9). Leave `etc/robot.toml.json` alone.
- [ ] 5.2 In `docs/03_reference/cli.md`, add one sentence to the `language-server` package entry: the package does not include the `analyze` command, and `pip install robotcode[languageserver,analyze]` (or `robotcode[all]`) installs both. In `.github/copilot-instructions.md`, remove the `analyze → language_server` edge from the package dependency graph and `analyze` from the sentence "`language_server` depends on …". Verify with `npm run docs:build`.

## 6. Verification

- [ ] 6.1 Run `hatch run lint:all` and `hatch run test:test` and confirm that both pass. Check by hand in the development environment:
  - `robotcode analyze code` on a suite that calls an unknown keyword reports `KeywordNotFound` without configuration and reports nothing with `[tool.robotcode-analyze.modifiers] ignore = ["KeywordNotFound"]` in its `robot.toml`.
  - With `[tool.robotcode-analyze.code] collect-unused = true`, it reports an unused keyword.
  - `robotcode analyze cache path` prints a directory below the one set with `[tool.robotcode-analyze.cache] cache-dir`.
  - `robotcode robot --dryrun` with `ignore = "VariableNotFound"` stops with the loader's message for `[tool.robotcode-analyze]` (D3, Q4).

  Check in VS Code, after `hatch run build:install-bundled-editable`, that the `ignore` entry suppresses the diagnostic in the editor.
