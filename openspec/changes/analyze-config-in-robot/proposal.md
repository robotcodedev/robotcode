# Proposal: analyze-config-in-robot

## Why

The model of `[tool.robotcode-analyze]` (`AnalyzeConfig` and its sub-sections, `packages/analyze/src/robotcode/analyze/config.py`) lives in `robotcode-analyze`, the package of the `robotcode analyze` command. Most of it configures RobotCode's own analysis in `robotcode-robot`: `modifiers`, `cache`, `exclude-patterns`, `global-library-search-order`, `semantic-model` and `load-library-timeout` go through `to_workspace_analysis_config()` into the `WorkspaceAnalysisConfig` that `robotcode-robot`'s `DocumentsCacheHelper` uses. Only `code`/`extend-code` (`exit-code-mask`, `collect-unused`) belong to the `robotcode analyze code` command. The language server depends on `robotcode-analyze` only for this class (`language_server/cli.py`), so every installation of the language server also installs the `analyze` command. And `robotcode config show`/`info` know the section only when `robotcode-analyze` is installed, because only its plugin hook registers the class.

`code()` in `analyze/code/cli.py` (lines 519-535) and `dump_model()` in `analyze/dump_model.py` (99-115) merge `--variable`, `--variablefile` and `--pythonpath` into the profile with the same code.

Maintainer decision: the packages stay modular. The analysis part of the model moves to `robotcode-robot`, the `code` part stays in `robotcode-analyze` as an extension of it, `robotcode-robot` knows the section as a built-in one, and the language server drops its dependency on `robotcode-analyze`.

Maintainer decision (2026-09-29): the change stands on its own as a modularity cleanup and depends on no other change.

## What Changes

- **Split.** A new module `packages/robot/src/robotcode/robot/config/analyze_config.py` (`robotcode.robot.config.analyze_config`) holds the analysis part: `ModifiersConfig`, `CacheConfig` and the base class `AnalyzeConfig` with every field except `code`/`extend-code`, and `to_workspace_analysis_config()`, all copied unchanged. `packages/analyze/src/robotcode/analyze/config.py` keeps `ExitCodeMask`, `ExitCodeMaskLiteral`, `ExitCodeMaskList`, `CodeConfig` and a subclass of the base class, also named `AnalyzeConfig`, that adds `code`/`extend-code` (maintainer decision, design D2). `robotcode-robot` gets no new dependency.
- **Built-in tool section.** `robotcode-robot`'s `loader.py` gets the dictionary `BUILTIN_TOOL_CONFIG_CLASSES`, which maps `robotcode-analyze` to the base class. The loader itself (`load_robot_config_from_path`) stays unchanged and does not read the section on its own (maintainer decision). The commands that read the section pass the dictionary as `extra_tools`: `robotcode config show`, merged with the classes registered by plugins, where a registered class wins, and the readers of the accessor below. `robotcode config info` lists the fields of the same merged classes. `robotcode analyze code` keeps passing its subclass, so it still gets the `code` keys. `robotcode-analyze` keeps registering its subclass, which now means that it extends the built-in section with the options of `analyze code` (design D3, D4).
- **Accessor.** `get_analyze_config(robot_config)` in the new module returns the loaded section or its defaults. `language-server`, `analyze cache` (twice) and `analyze dump-model` load the configuration with `extra_tools=BUILTIN_TOOL_CONFIG_CLASSES` and call it instead of their lookup with its fallback. `analyze code` keeps its loading block, because it needs the subclass (design D5).
- **Shared `-v/-V/-P` merging.** `merge_variable_and_path_options()` in `packages/robot/src/robotcode/robot/config/utils.py` merges `--variable`, `--variablefile` and `--pythonpath` into a profile. `analyze code` and `analyze dump-model` call it instead of their identical copies.
- **Language server dependency.** `robotcode-language-server` no longer depends on `robotcode-analyze`. Installations that install only the language server (`pip install robotcode[languageserver]` or `robotcode-language-server`) no longer get the `robotcode analyze` command, and the root `languageserver` extra does not add it (maintainer decision, design D8). `robotcode[analyze]` and `robotcode[all]` install it as documented. The VS Code extension and the IntelliJ plugin are not affected, because their bundled libraries contain every RobotCode package. The change is not marked as breaking (maintainer decision).
- **Behaviour.** In installations without `robotcode-analyze`, `robotcode config show` prints the analysis part of `[tool.robotcode-analyze]` typed and validated, without the `code` table, and `robotcode config info` lists its keys. `config show` also prints an empty `[tool.robotcode-analyze]` table when no file sets the section, as it does with `robotcode-analyze` today. Today `config show` prints the section there unvalidated and `config info list "tool.*"` finds nothing. With `robotcode-analyze` installed, both commands show the same keys and values as today, but `config show` prints the `code` table after the other keys of the section instead of first (design D1). `robot`, `discover`, `profiles` and the other commands that do not read the section keep ignoring it, so an invalid value there does not stop them (design D3). An `[tool.*]` section that no class is registered for is no longer printed by `config show` in installations without `robotcode-analyze`, as it is already not printed with it (design D4).
- **Unchanged.** The section name `[tool.robotcode-analyze]`, its keys and their meaning; the JSON schema and the configuration reference, which are regenerated without a diff; the command-line options of `analyze code` and `analyze dump-model`.
- **Docs.** `docs/03_reference/cli.md` says that the `language-server` package does not include `analyze`. The package dependency graph in `.github/copilot-instructions.md` loses the `analyze → language_server` edge.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

<!-- none -->

None, so the change sets `skip_specs: true` in `.openspec.yaml`:

- The keys of `[tool.robotcode-analyze]` and their meaning stay the same. The requirement "Generated model, schema and reference stay consistent" of `robot-toml-option-coverage` holds unchanged, because the schema and the reference are regenerated without a diff.
- `analyze dump-model` keeps "the same configuration path as `robotcode analyze code` (robot.toml, profiles, `-v`/`-V`/`-P` overrides)" required by `semantic-model-inspection`. Both commands call the same merging function.
- No capability describes the `robotcode config` command or which command validates which part of `robot.toml`, so the behaviour notes above modify no requirement. A new capability only for them would specify the output of `config show`/`info` per installed package, which this change does not set out to define.
- The dropped dependency is a packaging change and not a requirement of any capability.

## Impact

- Code: `packages/robot/src/robotcode/robot/config/analyze_config.py` (new), `loader.py` and `utils.py` in the same directory; `packages/analyze/src/robotcode/analyze/{config.py, code/cli.py, cache/cli.py, dump_model.py}`; `packages/language_server/src/robotcode/language_server/cli.py`; `src/robotcode/cli/commands/config.py`. `packages/analyze/src/robotcode/analyze/hooks.py`, `scripts/create_robot_toml_json_schema.py` and `tests/robotcode/analyze/code/test_result_collector.py` stay unchanged, because the subclass keeps the name `AnalyzeConfig` (design D2).
- Packaging: `packages/language_server/pyproject.toml` (dependency removed). The root `pyproject.toml` extras and dependency groups, `hatch.toml`, `bundled/libs` (built from every package with `--no-deps`) and the IntelliJ plugin stay as they are.
- Generated files: `docs/public/schemas/robot.toml.json` and `docs/03_reference/config.md` are regenerated, with no diff expected. `etc/robot.toml.json` (a frozen copy for older RobotCode versions) is left alone.
- Tests: new tests for loading with `BUILTIN_TOOL_CONFIG_CLASSES`, `get_analyze_config`, `merge_variable_and_path_options` and `robotcode config show`/`info` with and without the registration of `robotcode-analyze`.
- Docs: `docs/03_reference/cli.md`, `.github/copilot-instructions.md`.
- Follow-ups: the parked changes `library-index` and `library-keyword-set-declaration` build on the new module. `library-index` plans to add `[tool.robotcode-doc]` to `BUILTIN_TOOL_CONFIG_CLASSES`, so the commands that pass the dictionary would read that section too. `library-keyword-set-declaration` edits the descriptions of `ignored-libraries` and `ignore-arguments-for-library` in the new module.
