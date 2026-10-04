# Design

## Context

See proposal.md for the motivation. Decision D3 of the maintainer: the `robotcode.robot.*` settings are offered in the IDE as a layer over `robot.toml`, merged as in VS Code. The state that shapes the approach:

- **Builds on planned changes.** None of them is implemented yet; this design builds on their planned designs:
  - the settings pages change: the "Robot Framework" parent page for project-wide settings, the shared state `RobotCodeProjectConfiguration` in `robotcodeSettings.xml`, and the typed settings model whose `robot` section holds VS Code's keys and defaults, with stored values copied in only for settings that have a control;
  - the run configuration target change: the run configuration's options class, the fragmented editor, PyCharm's environment options, and the run state on `PythonCommandLineState`, whose `buildPythonExecution` assembles `--no-pager -dp . debug [--no-debug] [--tcp <port>] [-- <robot arguments>]`;
  - the run configuration options change: the configuration's Robot Framework options (robot arguments, variables, variable files, Robot Framework Python path, languages, include and exclude tags, output directory, mode `INHERIT`/`RPA`/`NORPA`, dry run), where an unset value passes nothing "so that project-wide defaults can later fill in unset values", a pure function that turns them into the arguments after `--` in the launcher's order, and macro expansion at the start of each run;
  - the profiles or the extra-arguments change, whichever lands first: the pure function `robotCodeArguments(...)` that fixes the order of the global `robotcode` options.
  With the planned analysis settings change, the initialization options take `pythonPath` and `env` from the settings tree, so the Python path and environment set here then also apply before the server checks Robot Framework.
- **Current code:** both discoveries in `RobotCodeTestManager` and the run state hard-code `-dp .` with a TODO; the planned profile list does the same. Nothing passes a mode, a Python path, languages or robot arguments to discovery.
- **Language server:** it reads `robotcode.robot` from the configuration answers. At `initialized` it writes `env` into its environment and puts the `pythonPath` entries, expanded as globs, on `sys.path`. For analysis it combines with the `robot.toml` profile: variables `{**robot.toml, **settings}`, variable files and languages appended, environment updated by the settings. It parses `args`, `mode`, `paths` and `outputDir` but does not use them.
- **robotcode runs:** `robotcode` passes the options of the `robot.toml` profile to Robot Framework before the client's options, so a single-value option from the client wins and list options accumulate. It writes the profile's `env` into the run process's environment, so `robot.toml`'s environment wins over the environment the process got. `-dp` takes effect only when there is no positional path and the profile defines no paths.
- **VS Code:** `resolveDebugConfiguration` concatenates `robot.pythonPath`, `robot.args` and `robot.variableFiles` before the launch values, merges `robot.variables` and `robot.env` under them, and takes `outputDir`, `mode` and `languages` from the launch configuration when it sets them (`??`). It never copies settings into launch configurations; its purpose-"default" quirk appends arrays twice, which is not to be ported. Test Explorer runs pass the launch `paths` plus `robot.paths`, or `.`. Discovery passes `-dp` per `robot.paths` or `-dp .` before the subcommand, and after it the mode, `-P` per Python path entry, `--language` per language and `robot.args`; it passes no variables, variable files or environment. `profiles list` gets only the `-dp` arguments.
- **PyCharm 2026.1 (bytecode):** `PythonCommandLineState` calls `buildPythonExecution` first and then `initEnvironment`, which adds the configuration's environment variables and `.env` files to the execution with `PythonExecution.addEnvironmentVariable` (appending to `PYTHONPATH` instead of replacing it); the inherited environment comes in when the process starts. `BaseOSProcessHandler.startNotify()` prints the command line as system output, so the run console starts with it.

## Goals / Non-Goals

**Goals:**

- One stored set of project values that the language server, discovery and runs use, as VS Code's settings are.
- One pure, unit-tested merge function that combines them with a configuration's options at the start of every run.
- `-dp` from one place instead of four hard-coded `-dp .`.

**Non-Goals:**

- Importing values from `robot.toml`; settings per folder or module.
- Passing variables, variable files or the environment to discovery, which VS Code does not do either.
- Changing how the server or `robotcode` combine these values with `robot.toml`.

## Decisions

### Two groups on the parent page, stored in the shared state

The "Robot Framework" page gets the groups "Robot Framework environment" and "Run options" below the existing content. The values extend the shared state, as VS Code users commit `robotcode.robot.*` in `.vscode/settings.json`:

- Python path, variable files, default paths and languages as lists; editors for paths have a browse button, and blank entries are dropped;
- environment variables and variables as ordered maps from strings to strings, edited in name/value tables; rows without a name are dropped;
- robot arguments as the command line the user typed, split with `ParametersListUtil` when used;
- mode as one of `default`, `rpa`, `norpa`;
- output directory as a string, edited in a folder field.

Paths are stored as entered. `robotcode` resolves relative paths against the project root it detects, and the server resolves the Python path against the workspace folder; in projects whose `robot.toml` lies in the project folder, both are the same.

Alternative: a separate "Robot Framework" child page. The settings node reserves its parent page for settings of the whole project, which these are, and the parity notes place them there.

### The settings tree carries the values

The settings mapper copies all nine values into `robotcode.robot`: `pythonPath`, `env`, `variables`, `variableFiles`, `languages`, `args`, `mode`, `paths` and `outputDir`, with the types the server parses. The server ignores the last four, but VS Code sends them too, and the tree stays the complete set of VS Code's keys.

### Arguments for discovery and default paths, as pure functions

- `defaultPathArguments(configurationPaths, projectPaths)` returns `-dp` for each configuration path and then each project path, or `-dp .` when both are empty. Discovery and the profile list call it without configuration paths; runs call it with theirs.
- `discoveryRobotArguments(settings)` returns `--rpa`/`--norpa` unless the mode is `default`, `-P` per Python path entry, `--language` per language and the robot arguments, in VS Code's order.

Both discoveries put the default-path arguments before `discover` and the robot arguments after the discover subcommand and its own options; the profile list puts the default-path arguments before `profiles list`. The global options keep the order of `robotCodeArguments`.

Alternative: building the arguments inline at each call site, as the hard-coded `-dp .` is today. Discovery and runs would drift apart, which is what the parity notes warn about.

### One merge function, applied at the start of every run

The pure function `mergeRobotOptions(project, configuration)` returns the options that the run configuration options change's argument function turns into arguments:

| Value | Result |
|---|---|
| Python path, variable files, robot arguments | project values, then the configuration's |
| variables | project map, overridden by the configuration's map |
| mode | the configuration's unless `INHERIT`, otherwise the project's (`default` passes nothing) |
| output directory, languages | the configuration's when set (non-empty), otherwise the project's |
| include and exclude tags, dry run | the configuration's (no project setting) |

The run state calls it in `buildPythonExecution`, before the arguments are built and macros are expanded. Project values are never written into a configuration, so a configuration created from the template carries none of them, and nothing is appended twice.

The project's environment variables are added to the execution in `buildPythonExecution` as well. PyCharm adds the configuration's own variables and `.env` files afterwards, so they win for the same name, and the inherited environment stays below both.

Alternatives:
- Copying the settings into new configurations through the template: later changes would not reach existing configurations, and discovery and the language server could not read a template.
- Adding the project's environment in an override of `customizePythonExecutionEnvironmentVars`, which runs after PyCharm's environment setup: it would need a check per name and another override with experimental parameter types.

### Default paths per configuration

The run configuration's options class gets `defaultPaths`, a list, and the editor a "Default paths" fragment under "Modify options", a list with a browse button and macro support whose values are expanded at the start of each run like the configuration's other paths. The run state replaces its `-dp .` with `defaultPathArguments(configuration paths, project paths)`. VS Code passes `robot.paths` only for Test Explorer runs; IntelliJ has no separate kind of run, so every run gets them.

### Apply restarts and rediscovers

Applying the page restarts the language server and runs discovery once through the debounced `restartAll()`, because the server reads these values when it starts and discovery uses the run options.

### Texts

The group comments say how the values combine with `robot.toml` (lists add; variables set here win; environment variables win in the editor but not in runs; default paths only as a fallback) and that run configurations add their own values: lists after these, a configuration's variables win, and a configuration's mode, output directory and languages replace the project's.

## Risks / Trade-offs

- [The same entry in `robot.toml` and in the settings is passed twice, for example `-P libs`] → Harmless for Robot Framework; the texts say that lists add.
- [`robot.toml`'s environment wins in runs, while the IDE's wins in the editor] → This is how the server and `robotcode` work today; the group comment says so.
- [A run's command line holds values that its editor does not show] → The run console starts with the command line, and the texts name the project settings.
- [PyCharm could change the order in which it applies environment variables] → A unit test pins what `buildPythonExecution` adds, and the harness check covers the precedence; if the order changes, the project's variables are added only for names the configuration does not set.
- [A configuration's languages replace the project's instead of adding to them] → VS Code's semantics; the text says so.

## Migration Plan

None. Projects without these settings keep `-dp .` and today's command lines.
