# Design

## Context

See proposal.md for the motivation. Decision D3 of the maintainer: the `robotcode.robot.*` settings are offered in the IDE as a layer over `robot.toml`, merged as in VS Code. The state that shapes the approach:

- **Settings pages** (since `intellij-settings-pages` and its follow-ups): "Robot Framework" under Languages & Frameworks is a node without settings of its own that lists its sub-pages General, Editing, Analysis, Robocop and Language Server. Their labels follow VS Code (requirement "Labels of the settings pages follow VS Code"): VS Code's setting titles in sentence case, the key parts VS Code shows before a title as groups, and one page per VS Code category; the parent page holds no settings (decision of 2026-10-08). VS Code's "Robot" category holds exactly the nine `robotcode.robot.*` settings.
- **Stored values and settings tree:** project-wide values live in `RobotCodeProjectConfiguration` (`robotcodeSettings.xml`). The settings tree `RobotCodeServerSettings` already has the `robot` section with VS Code's keys and defaults, and its initialization options already pass `robot.pythonPath` and `robot.env`, so the server applies them before it checks Robot Framework. `restartAll()` restarts the server and discovery once, debounced (requirement "One restart per Apply"), and discovery runs again when its command line changes.
- **Run configurations** (since `intellij-run-configuration-target`, `intellij-run-configuration-options` and `intellij-run-selection-args`): `RobotCodeRunConfigurationOptions` holds the configuration's robot arguments, variables, variable files, Python path, languages, include and exclude tags, output directory, mode (`INHERIT`/`RPA`/`NORPA`) and dry run, where an unset value passes nothing. `robotFrameworkArguments(...)` turns them into the arguments after `--` in the order the spec fixes, followed by the selection arguments of a tests-and-suites target (`-I`, `-N`, `-s`, `-bl`, with the names discovery reported) or the paths of a files-and-folders target; path fields expand macros at the start of each run. The run state is a `PythonCommandLineState`, and `runArguments(...)` builds `-dp . debug …` through `robotCodeArguments(...)`, which fixes the order of the global `robotcode` options.
- **Current `-dp .`:** hard-coded in `fullDiscoveryCommandLine` and `fileDiscoveryArguments` (`testing/RobotCodeFileDiscovery.kt`, each with a TODO), in the profile list (`configuration/RobotCodeProfiles.kt`) and in `runArguments`. Nothing passes a mode, a Python path, languages or robot arguments to discovery.
- **Language server:** it reads `robotcode.robot` from the configuration answers. At `initialized` it writes `env` into its environment and puts the `pythonPath` entries, expanded as globs, on `sys.path`. For analysis it combines with the `robot.toml` profile: variables `{**robot.toml, **settings}`, variable files and languages appended, environment updated by the settings. It parses `args`, `mode`, `paths` and `outputDir` but does not use them.
- **robotcode runs:** `robotcode` passes the options of the `robot.toml` profile to Robot Framework before the client's options, so a single-value option from the client wins and list options accumulate. It writes the profile's `env` into the run process's environment, so `robot.toml`'s environment wins over the environment the process got. `-dp` takes effect only when there is no positional path and the profile defines no paths.
- **Several paths and a selection** (checked 2026-10-13 with Robot Framework 7.5): with `-dp smoke -dp tests`, discovery reports a top-level suite `Smoke & Tests` over both folders. A selection with the names of a discovery over the same paths runs; one with the names of a discovery over other paths fails ("Suite '' contains no tests after model modifiers"), so runs need the same `-dp` arguments as discovery. With `-I`, which runs of selected items pass since `intellij-run-selection-args`, several paths fail even with matching names: Robot Framework 6.1 and newer check each path for tests when `--parseinclude` is given ("Suite 'Smoke' contains no tests or tasks", #656). RobotCode does not work around this Robot Framework bug (decision of 2026-10-09); `run-empty-suite = true` in `robot.toml` avoids it.
- **VS Code:** `resolveDebugConfiguration` concatenates `robot.pythonPath`, `robot.args` and `robot.variableFiles` before the launch values, merges `robot.variables` and `robot.env` under them, and takes `outputDir`, `mode` and `languages` from the launch configuration when it sets them (`??`). It never copies settings into launch configurations; its purpose-"default" quirk appends arrays twice, which is not to be ported. Test Explorer runs pass no positional path and the `paths` of a launch configuration with the purpose "test" plus `robot.paths`, or `.`, as the launch `paths`, which the launcher turns into `-dp` arguments. Other launch configurations pass their `target`, such as `${file}` or `.`, as a positional path; `resolveDebugConfiguration` adds no `robot.paths`, so `-dp` comes only from a launch configuration's own `paths`. Discovery passes `-dp` per `robot.paths` or `-dp .` before the subcommand, and after it the mode, `-P` per Python path entry, `--language` per language and `robot.args`; it passes no variables, variable files or environment. `profiles list` gets only the `-dp` arguments.
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

### A "Robot" page for VS Code's "Robot" category

The node gets a "Robot" sub-page. The settings tree lists the sub-pages of a node by name unless they set a `groupWeight`, so it comes after "Robocop", in the alphabetical order that the other sub-pages already have. It shows the nine settings with VS Code's titles: Args, Paths, Python path, Env, Languages, Variables, Variable files, Output dir and Mode. It has no groups, because VS Code shows no key part between the category and these titles. The values extend `RobotCodeProjectConfiguration`, as VS Code users commit `robotcode.robot.*` in `.vscode/settings.json`:

- Paths, Python path, variable files and languages as lists; editors for paths have a browse button, and blank entries are dropped;
- Env and Variables as ordered maps from strings to strings, edited in name/value tables; rows without a name are dropped;
- Args as the command line the user typed, split with `ParametersListUtil` when used;
- Mode as one of `default`, `rpa`, `norpa`, shown as "Default", "RPA" and "Test automation" like the configuration's mode;
- Output dir as a string, edited in a folder field.

Paths are stored as entered. `robotcode` resolves relative paths against the project root it detects, and the server resolves the Python path against the workspace folder; in projects whose `robot.toml` lies in the project folder, both are the same.

Alternatives:

- Two groups on the parent page, "Robot Framework environment" and "Run options", as planned at first: the parent page holds no settings, and the labels would not be VS Code's.
- Several pages by topic: the settings of one VS Code category stay on one page.
- A `groupWeight` on all six sub-pages for the order of VS Code's categories (General, Editing, Robot, Analysis, Robocop, Language Server): the sub-pages keep IntelliJ's alphabetical order (decision of 2026-10-13).

### The settings tree carries the values

The mapper fills the nine keys of the `robot` section, `args`, `paths`, `pythonPath`, `env`, `languages`, `variables`, `variableFiles`, `outputDir` and `mode`, from the stored values, with the types the server parses, instead of VS Code's defaults. The server ignores `args`, `paths`, `outputDir` and `mode`, but VS Code sends them too, and the tree stays the complete set of VS Code's keys.

### Arguments for discovery and default paths, as pure functions

- `defaultPathArguments(paths)` returns `-dp` for each path, or `-dp .` when there is none. Discovery, the profile list and runs call it with the paths of the "Robot" page.
- `discoveryRobotArguments(settings)` returns `--rpa`/`--norpa` unless the mode is `default`, `-P` per Python path entry, `--language` per language and the robot arguments, in VS Code's order.

Both discoveries put the default-path arguments before `discover` and the robot arguments after the discover subcommand and its own options; the profile list puts the default-path arguments before `profiles list`. The global options keep the order of `robotCodeArguments`.

Alternative: building the arguments inline at each call site, as the hard-coded `-dp .` is today. Discovery and runs would drift apart, which is what the parity notes warn about.

### One merge function, applied at the start of every run

The pure function `mergeRobotOptions(project, configuration)` returns the options that `robotFrameworkArguments(...)` turns into arguments:

| Value | Result |
|---|---|
| Python path, variable files, robot arguments | project values, then the configuration's |
| variables | project map, overridden by the configuration's map |
| mode | the configuration's unless `INHERIT`, otherwise the project's (`default` passes nothing) |
| output directory, languages | the configuration's when set (non-empty), otherwise the project's |
| include and exclude tags, dry run | the configuration's (no project setting) |

The run state calls it in `buildPythonExecution`, before the arguments are built and macros are expanded. Project values are never written into a configuration, so a configuration created from the template carries none of them, and nothing is appended twice.

The project's environment variables are added to the execution in `buildPythonExecution` as well, with `PythonExecution.addEnvironmentVariable`. PyCharm adds the configuration's own variables and `.env` files afterwards, so they win for the same name, and the inherited environment stays below both. `robotcode` has no option to set environment variables on its command line, so the execution is the only place for them; `PythonExecution` is experimental API, on which the run state already builds, and this method is the change's only new use of experimental API.

Alternatives:

- Copying the settings into new configurations through the template: later changes would not reach existing configurations, and discovery and the language server could not read a template.
- Adding the project's environment in an override of `customizePythonExecutionEnvironmentVars`, which runs after PyCharm's environment setup: it would need a check per name and another override with experimental parameter types.

### Every run passes the paths of the "Robot" page

`runArguments` replaces its `-dp .` with `defaultPathArguments(paths of the "Robot" page)`, for every kind of target, so runs and discovery pass the same `-dp` arguments and the names of a selection match the suite structure of the run (see Context). Default paths take effect only when the run names no files or folders and `robot.toml` sets no paths, so a configuration that runs other files or folders names them as its target, whose positional paths Robot Framework runs instead.

Alternatives:

- Default paths per run configuration, added before the paths of the "Robot" page, as planned at first and as VS Code's Test Explorer runs combine a launch configuration's `paths` with `robot.paths`: a gutter run of a configuration with its own default paths fails.
- Default paths per configuration only for runs without a selection: a second rule for the same option, for what a target with files and folders already does.

### Apply restarts and rediscovers

Applying the page announces the change with `publishRobotCodeSettingsChanged()`, as the other pages do, and the restart manager compares what the server and the last discovery got with what they would get now (requirement "One restart per Apply"). A changed value changes the settings tree, so the server restarts, because it reads these values when it starts; discovery runs again when its command line changed, that is for the paths, the mode, the Python path, the languages and the args, but not for the variables, the variable files, the environment or the output directory, which discovery does not get.

Alternative: calling `restartAll()` directly, as planned at first: it would also run discovery again when its command line stays the same.

### Texts

The texts below the fields say how the values combine with `robot.toml` (lists add; variables set here win; environment variables win in the editor but not in runs; paths only as a fallback) and that run configurations add their own values: lists after these, a configuration's variables win, and a configuration's mode, output directory and languages replace these. The comments of the run configuration's options that name `robot.toml` mention the "Robot" page as well: lists follow the values of `robot.toml` and of the "Robot" page, the mode "Inherit" takes the page's mode, and the output directory and the languages replace the page's.

## Risks / Trade-offs

- [The same entry in `robot.toml` and in the settings is passed twice, for example `-P libs`] → Harmless for Robot Framework; the texts say that lists add.
- [`robot.toml`'s environment wins in runs, while the IDE's wins in the editor] → This is how the server and `robotcode` work today; the text of "Env" says so.
- [A run's command line holds values that its editor does not show] → The run console starts with the command line, and the texts name the "Robot" page.
- [A configuration should run other folders than the paths of the "Robot" page] → It names them as its target; positional paths win over `-dp`.
- [Changing "Paths" changes the full names that discovery reports, so a saved configuration whose "Tests and suites" target holds the names of an earlier discovery finds no tests, as after a change of `paths` in `robot.toml`] → The configuration is created again from the gutter, or its target is chosen again.
- [Several entries in "Paths" make runs of selected tests fail on Robot Framework 6.1 and newer (#656), as several `paths` in `robot.toml` do, and as in VS Code] → A Robot Framework bug that RobotCode does not work around (decision of 2026-10-09); `run-empty-suite = true` in `robot.toml` avoids it.
- [PyCharm could change the order in which it applies environment variables] → A unit test pins what `buildPythonExecution` adds, and the harness check covers the precedence; if the order changes, the project's variables are added only for names the configuration does not set.
- [A configuration's languages replace the project's instead of adding to them] → VS Code's semantics; the text says so.

## Migration Plan

None. Projects without these settings keep `-dp .` and today's command lines, and a configuration's mode "Inherit" passes nothing as long as "Mode" stays "Default".
