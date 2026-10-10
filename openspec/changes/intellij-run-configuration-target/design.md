# Design

## Context

See proposal.md for the motivation. Decision D1 of the maintainer: remote interpreters are a goal, starting with WSL, so run configurations extend PyCharm's `AbstractPythonRunConfiguration` with a `PythonCommandLineState` subclass (option P of the parity analysis), and local runs must keep working as before. This change runs on the local target only; WSL runs come later.

**Builds on `intellij-run-selection-args`** (archived on 2026-10-10). `RobotCodeSelectionArguments.kt` has a resolve step, `resolveSelection(items, model)`, which turns discovery items into `SelectionEntry`s (full name, full name of the suite to pass with `-s` and its `relSource`) plus the top-level suite name, taking the suite of a test or task from the current model by file, and an emit step, `selectionArguments(selection, supportsParseInclude)`, which turns them into `-I`, `-N`, `-s` and `-bl`. `debugArguments(debug, port, robotArguments)` in `RobotCodeRunProfileState.kt` assembles everything after `debug`. A `SelectionEntry` has no kind; the stored entries of this change add it.

**Current plugin code** (checked on 2026-10-10):

- `RobotCodeRunConfiguration` extends `LocatableConfigurationBase<ConfigurationFactory>`; `writeExternal`/`readExternal` only call `super` and carry TODOs. `includedTestItems` (discovery items set by the producer) and `paths` (never read) live in memory. `getState()` first calls `robotCodeEnvironment.ensureUsableForRun()`, which waits for or starts the check of the project interpreter, with a modal progress on the UI thread, and throws a `CantRunException` with the check's message when the interpreter is not usable. `RobotCodeRunConfigurationFactory` declares no options class and keeps the factory id `ROBOT_FRAMEWORK_TEST`; the configuration type id is `RobotCodeConfigurationType`.
- `RobotCodeRunConfigurationEditor` is a UI DSL `SettingsEditor` whose `resetEditorFrom`/`applyEditorTo` are empty.
- `RobotCodeRunProfileState` extends `CommandLineState`. `startProcess()` builds the command line with `Project.buildRobotCodeCommandLine()`: the project interpreter (`robotPythonSdk`, the first module that has a Python SDK), `-u -X utf8`, the bundled `robotcode`, the global options from `robotCodeArguments` (`--no-pager`, `-p` for each selected profile, no robotcode extra args, colors on), then `-dp . debug` and `debugArguments(...)` with the selection from `resolveSelection` and `selectionArguments`, the project folder as working directory and UTF-8. It creates a `KillableColoredProcessHandler`, stores the debug port in the handler and registers itself as process listener; `startNotified()` runs the DAP handshake. `execute()` creates the SM test console (`RobotCodeRunnerConsoleView` with `RobotRunnerConsoleProperties`) on the UI thread and sets the rerun-failed action.
- `RobotCodeProgramRunner` and `RobotCodeDebugProgramRunner` are `AsyncProgramRunner`s that call `state.execute()` on the UI thread and return a resolved promise; the debug runner starts the session with `XDebuggerManager.newSessionBuilder()`. Both are registered in `plugin.xml` without `order`.
- `RobotCodeRunConfigurationProducer` returns no configuration while RobotCode is switched off. It names the configuration "<Type> <name>", stores the found item in `includedTestItems`, and reuses a configuration only if its stored item equals the found one; `RobotCodeTestItem.equals` compares id (with line number), range, children, tags and metadata.
- `pythonInterpreterOf(sdk)` in `RobotCodeEnvironment.kt` classifies an SDK as none, local or remote (`PythonSdkUtil.isRemote`); the environment check uses it to report a remote project interpreter.

**PyCharm 2026.1 API** (javap against `pycharm-2026.1`, build PY-261.22158.340, in the Gradle cache; re-checked on 2026-10-10 against PY-263.6259.38, where `AbstractPythonRunConfiguration`, `PythonCommandLineState` and `AbstractPythonConfigurationFragmentedEditor` have the same signatures for the members below and no class-level `ApiStatus`):

- `AbstractPythonRunConfiguration<T>` has no class-level `ApiStatus`. Its `@Internal` members are `patchCommandLine`, `patchCommandLineFirst`, `getUseRunTool`/`setUseRunTool` and `shouldDebugJustMyCode`/`setDebugJustMyCode`. It extends `AbstractRunConfiguration` (`ModuleBasedConfiguration<RunConfigurationModule, Element>`).
- Persistence: `AbstractPythonRunConfiguration.writeExternal` calls `super` first and then writes its own JDOM fields (`INTERPRETER_OPTIONS`, `SDK_HOME`, `SDK_NAME`, `ENV_FILES`, `WORKING_DIRECTORY`, `IS_MODULE_SDK`, `ADD_CONTENT_ROOTS`, `ADD_SOURCE_ROOTS`, `DEBUG_JUST_MY_CODE`, envs, module). Further up, `RunConfigurationBase.writeExternal` serializes the BaseState options object with `XmlSerializer`, and `readExternal` deserializes it with the class the factory returns from `getOptionsClass()`. `ModuleBasedConfiguration.clone()` copies configurations with `Element` state by writing and reading them.
- Defaults: the constructor sets `ADD_CONTENT_ROOTS` and `ADD_SOURCE_ROOTS` to `true` and picks any first module. `readExternal` reads a missing `ADD_*` field as `true` and a missing `IS_MODULE_SDK` as `false`. With neither SDK nor SDK home stored, `getSdkHome()` falls back to the module's Python SDK. An empty working directory resolves to the project base path (`getWorkingDirectorySafe()`).
- `checkConfiguration()` calls `checkSdk()`, which raises a `RuntimeConfigurationError` for a missing or invalid interpreter.
- `getConfigurationEditor()` is final: it returns `createConfigurationEditor()` directly when the registry key `python.new.run.config` is on (default `true`) and `isNewUiSupported()` returns `true`; otherwise it wraps the editor in a legacy group.
- `AbstractPythonConfigurationFragmentedEditor` (package `com.jetbrains.python.run.configuration`, unannotated) builds Before launch, the run header, "Allow multiple instances", the interpreter and environment fragments of `PyCommonFragmentsBuilder`, interpreter options (`py.interpreter.options`), content and source roots (`py.add.content.roots`, `py.add.source.roots`), the Python debugger option `justMyCode`, an optional run-tool tag, then calls the abstract `customizeFragments(list)`, and adds the editor-extension and logs fragments. `addToFragmentsBeforeEditors` is a public helper. PyCharm's own target chooser `AbstractPyRunConfigTargetChooserFragment` is `@Internal`; `SettingsEditorFragment.isAvailable` and the static `applyEditorTo` are `@Internal`.
- `PythonCommandLineState` (no class-level `ApiStatus`): `execute(Executor)` is the target-aware path. It resolves the interpreter's target request, calls the overridable `buildPythonExecution(HelpersAwareTargetEnvironmentRequest)`, sets the working directory, applies the environment (including virtualenv/conda activation when the registry key `python.activate.virtualenv.on.run` is on, default `true`) and the `PYTHONPATH` roots, prepares the target environment, starts the process, and calls the overridable `createProcessHandler(Process, String, TargetEnvironment, TargetedCommandLine)` and `createAndAttachConsole(Project, ProcessHandler, Executor)`. The default `buildPythonExecution` asserts a background thread. `execute(Executor, ProgramRunner)` starts a process only for PyCharm's own runners and otherwise returns a console with an empty process handler. `@Internal` members: `createAndAttachConsoleInEDT`, `buildPythonPath`, `collectPythonPath`, `canRun`.
- `PythonExecution`, `PythonScriptExecution`, `PythonModuleExecution`, `TargetEnvironmentRequest` and `TargetEnvironment` are `@ApiStatus.Experimental`. `LocalTargetEnvironment`, `KillableColoredProcessHandler(Process, String, Charset)` and `com.jetbrains.python.sdk.PythonSdkUtil.isRemote`/`findPythonSdk` are unannotated; `com.jetbrains.python.sdk.legacy.PythonSdkUtil` is `@Internal`.
- Runners: `PythonRunner.canRun` accepts every `AbstractPythonRunConfiguration` for Run and runs `PythonCommandLineState.execute(Executor)` in a background coroutine before it shows the content on the UI thread. `PyDebugRunner` accepts a `DebugAwareConfiguration` only if `canRunUnderDebug()` is `true`, otherwise every `AbstractPythonRunConfiguration`. PyCharm Professional adds `PythonCoverageRunner` (guarded by `canRunWithCoverage()`), and `PythonProfileRunner` and `PyConcurrencyDebugRunner`, which accept every `AbstractPythonRunConfiguration` for their executors.
- PyCharm's run tool: `startProcess` wraps the command in a tool when the registry key `run.with.py.tool` is on (default `true`) and a `PyRunToolProvider` exists for the SDK, which in 2026.1 is only `UvRunToolProvider` for uv interpreters, with "on" as its initial state. The command then becomes `uv run <interpreter> <interpreter parameters> <script> <arguments>` with `VIRTUAL_ENV` and `UV_PROJECT_ENVIRONMENT` set. The configuration's stored `RUN_TOOL` value overrides the initial state; its accessors `getUseRunTool`/`setUseRunTool` are `@Internal`, and the editor's run-tool tag sets it.
- `RunConfigurationProducer` calls `RunManager.setUniqueNameIfNeeded`, which adds "(1)" when a new context configuration gets the name of an existing one.

## Goals / Non-Goals

**Goals:**

- One stored, editable and shareable model of what a configuration runs.
- PyCharm's interpreter, environment, working-directory and `PYTHONPATH` options without own copies, on a base that can run on targets later.
- Local runs with the same interpreter, working directory, environment and `robotcode` command line as before, unless the user changes them.
- No `@Internal` platform API.

**Non-Goals:**

- Running on WSL, Docker or SSH targets: port bindings, uploading the bundled tool and path mappings.
- Validating targets before the run beyond PyCharm's interpreter check.
- Changing the language server, discovery or the environment check, which stay project-wide and local.
- Moving the DAP handshake off the UI thread, and the port selection.

## Decisions

### The base: PyCharm's Python run configuration

`RobotCodeRunConfiguration` extends `AbstractPythonRunConfiguration<RobotCodeRunConfiguration>` and implements:
- `SMRunnerConsolePropertiesProvider`, as today;
- `DebugAwareConfiguration` with `canRunUnderDebug() = false`, so that `PyDebugRunner` does not take it.

It overrides `canRunWithCoverage()` to return `false` and `isNewUiSupported()` to return `true`. The configuration type, its id and the factory id `ROBOT_FRAMEWORK_TEST` stay, so stored configurations load into the new class.

Alternative: an own `LocatableConfigurationBase` with `GeneralCommandLine` (option L). It keeps runs local-only and needs own interpreter, environment and working-directory UI; D1 rules it out.

### Persistence: a BaseState options class next to PyCharm's fields

The factory returns a RobotCode options class, a subclass of `ModuleBasedConfigurationOptions`, from `getOptionsClass()`. `RunConfigurationBase` serializes it into the configuration element through the `super` chain that `AbstractPythonRunConfiguration` already calls, next to PyCharm's own JDOM fields, and `clone()` copies it through the same write and read. The class holds:
- the target kind: `PATHS` ("Files and folders", the default) or `SELECTION` ("Tests and suites");
- the paths of a `PATHS` target;
- the entries of a `SELECTION` target, each with its kind (test, task or suite), its full name, its `relSource`, and the full name and `relSource` of the suite to pass with `-s` and `-I`, as discovery reports them;
- the name of the top-level suite that discovery reported when the selection was made.

Property names differ from PyCharm's upper-case field names. Paths are stored as entered; the platform replaces the project path with `$PROJECT_DIR$` when it writes the configuration.

Alternatives:
- A child element written with `XmlSerializer` in `writeExternal`, as the analysis suggested: it works as well but bypasses the platform's options mechanism, which also stores which optional fragments the editor shows.
- Hand-written JDOM fields: more code without a benefit.

### Defaults that keep local runs as before

New configurations and the template get:
- the module whose Python SDK RobotCode uses today: the first module that has one;
- the module's interpreter;
- an empty working directory, which resolves to the project folder;
- both `PYTHONPATH` options off.

A configuration element without the field `ADD_CONTENT_ROOTS`, which PyCharm's `writeExternal` always writes, comes from an earlier version of the plugin. For it, `readExternal` applies the same defaults instead of the values `AbstractPythonRunConfiguration` derives from missing fields.

Alternative: PyCharm's defaults, with both `PYTHONPATH` options on. Runs would then see paths that the language server and command-line runs do not see (#430), and local runs would change without the user asking.

### Resolving the target at the start of a run

- `PATHS`: the paths become the last arguments after `--`. An empty list passes nothing, and robotcode takes the paths of `robot.toml`, or `-dp .` when it sets none, as for any `robotcode robot` call without paths.
- `SELECTION`: the stored entries become a `ResolvedSelection` for `selectionArguments` unchanged; the kind is not needed for that. `-N` gets the stored top-level suite, or the current model's when the target stores none. An entry the user typed in the editor has only a full name: the run looks it up in the current model and resolves the found item with `resolveSelection`; if it is not found, only `-bl` is passed for it.
- A `SELECTION` target without entries runs like an empty `PATHS` target; the editor shows a warning through the fragment's validation.

The plugin passes discovery's names unchanged and never rewrites the top-level suite: its name is Robot Framework's, which follows from the paths of `robot.toml` or the command line, the suite's `Name` setting and `--name` (decision of 2026-10-10).

Alternative: names below the top-level suite, completed with the current top-level suite at each run, so that a shared configuration matches in a checkout with another folder name. Rejected: it rewrites what Robot Framework reports and solves no real problem.

### The run state on `PythonCommandLineState`

`RobotCodeRunProfileState` extends `PythonCommandLineState` and uses its target-aware `execute(Executor)`:
- The project's environment check stays where it is today, in `getState()` (`ensureUsableForRun()`), with the same gate and message.
- `buildPythonExecution(request)` refuses an interpreter that `pythonInterpreterOf` classifies as remote with an `ExecutionException` that says Robot Framework runs with remote interpreters are not supported yet, picks the debug port as today, and returns a `PythonScriptExecution` of the bundled `robotcode` with `-u -X utf8` as additional interpreter parameters, UTF-8 and the arguments that `robotCodeArguments` builds as today (the selected profiles, no robotcode extra args, colors on), followed by `-dp . debug` and `debugArguments(...)`: `--no-pager [-p <profile>]... -dp . debug [--no-debug] [--tcp <port>] [-- <robot arguments>]`.
- `createProcessHandler(...)` creates the `KillableColoredProcessHandler` from the started process, stores the debug port, attaches the termination message and registers the state as process listener, as `startProcess()` does today. The DAP handshake in `startNotified()` stays unchanged.
- `createAndAttachConsole(...)` creates the SM test console as today's `execute()` does; `execute(Executor)` adds the rerun-failed action to the result.

Alternatives:
- A `PythonModuleExecution` of `robotcode.cli`: it needs RobotCode installed in the interpreter; the bundled tool keeps parity with today and with the language server.
- The legacy `GeneralCommandLine` path of `PythonCommandLineState`: not target-capable.

### Runners: first in line, start off the UI thread

Both program runners get `order="first"` in `plugin.xml`, so `PythonRunner`, which accepts every `AbstractPythonRunConfiguration` for Run, does not take Robot Framework configurations. A third runner, also first, takes the executor `Profiler` for Robot Framework configurations and ends with an `ExecutionException` saying that Robot Framework runs cannot be profiled: PyCharm Professional's `PythonProfileRunner` accepts every `AbstractPythonRunConfiguration` without an opt-out, and the platform offers an executor whenever a runner accepts the configuration (`ExecutorRegistryImpl.RunnerHelper.canRun`), so "Profile" cannot be hidden. Without it, the profiler runs the bundled `robotcode` folder as a script and fails with `IsADirectoryError` plus IDE errors (harness, 2026-10-10). Both runners call `state.execute(executor)` on a background thread, as `PythonRunner` does, because interpreter activation and target preparation must not run on the UI thread. The Run runner then shows the content on the UI thread; the Debug runner builds the debug session on the UI thread with a starter that wraps the existing execution result. The debug process subscribes to the handshake before the platform calls `startNotify()`, as today.

Alternative: keeping `execute()` on the UI thread. The default `buildPythonExecution` asserts a background thread, and reading an activated virtualenv or conda environment runs its activate script in a shell (cached per interpreter).

### The editor: PyCharm's fragments plus a Robot Framework target fragment

`RobotCodeRunConfigurationEditor` extends `AbstractPythonConfigurationFragmentedEditor`. In `customizeFragments` it removes `justMyCode`, which belongs to PyCharm's Python debugger, and adds the target fragment before the editors with `addToFragmentsBeforeEditors`. The run-tool tag ("Run with uv" for a uv interpreter) stays, because runs go through `startProcess`, which applies the tool as for Python runs (decision of 2026-10-10). Checked on the command line with the bundled `robotcode` and Robot Framework 7.5: a run through `uv run` passes, a SIGINT to `uv` stops the run with its report and log, the debug port opens, and `uv run` keeps packages that were installed into the environment by hand. The target fragment is an own `SettingsEditorFragment` built with its public constructor:
- a choice of the two kinds;
- for `PATHS`, a field with an expand button for the files and folders and a button that adds files and folders;
- for `SELECTION`, the same kind of field for the stored full names.

Both fields are IntelliJ's `RawCommandLineEditor`, as for "Extra args" on the General page: one line, one entry per line when expanded, and entries with spaces in quotes. Test names and paths may contain semicolons, which the semicolon-separated list field of the settings pages would split (decision of 2026-10-10).

Its comments say that paths replace the paths of `robot.toml` and rename the top-level suite. When applied, lines whose name is unchanged keep their stored entry; new lines become name-only entries. All texts are in `RobotCode.properties`.

Alternative: PyCharm's `AbstractPyRunConfigTargetChooserFragment`, which is `@Internal`.

### The producer compares stable keys

The producer turns the found test, task or suite into an entry with `resolveSelection`, which takes the suite of a test from the current model by file, stores the entry with the item's kind and the top-level suite as discovery reports them, and writes an empty `PATHS` target for the project folder. It still returns no configuration while RobotCode is switched off. `isConfigurationFromContext` compares the target kind and, for `SELECTION`, the entries' kinds and full names, for `PATHS` the paths, so line shifts and refreshed discovery objects no longer break the match. The name stays "<Type> <name>"; the producer changes no other value of the configuration.

## Risks / Trade-offs

- [Experimental API: the state's overrides use `PythonExecution`, `PythonScriptExecution`, `HelpersAwareTargetEnvironmentRequest` and `TargetEnvironment`] → They are confined to `buildPythonExecution` and `createProcessHandler`. `verifyPlugin` runs against 261 and the newer configured versions and reports changes. PyCharm's own test and uv run states override `buildPythonExecution` too, and its test states override `createAndAttachConsole` for their test console.
- [PythonCore classes change with every release] → Only the base class, the state's three overrides and the fragmented editor touch them, and each harness run uses the current PyCharm build.
- [The options class shares the configuration element with PyCharm's JDOM fields] → Distinct property names, and unit tests for the round trip and for `clone()`. If the round trip shows interference, the RobotCode options move into a child element written with `XmlSerializer`; the stored values stay the same.
- [Virtualenv and conda activation changes the environment of runs] → It matches PyCharm's own Python runs and helps conda on Windows; a line in the release notes.
- [With a uv interpreter, runs start through `uv run`, which adds missing packages of the project before each run, while the language server and discovery start the interpreter directly] → It matches PyCharm's own Python runs, "Run with uv" in the editor switches it off, and `uv run` removes no packages; a line in the release notes.
- [PyCharm Professional offers "Profile" for every `AbstractPythonRunConfiguration`] → It cannot be hidden; RobotCode's own runner for it ends with a message instead. "Run with Coverage" is switched off through `canRunWithCoverage()`. The harness runs with a Professional license, so both are checked there.
- [Python run-configuration extensions of other plugins, such as `.env` plugins, now apply to Robot Framework runs] → This is the same behaviour as for Python runs.
- [The process starts off the UI thread, while the DAP handshake still runs on it] → Moving the handshake off the UI thread is separate work; this change only moves what the target API requires.
- [A stored selection that no longer matches ends with Robot Framework's "contains no tests after model modifiers" error] → Only reruns after a rename are affected; a warning for stale entries before the run belongs to the validation of run configurations.
- [The environment check stays project-wide] → A configuration with another interpreter is gated by the project interpreter's check until the check runs per interpreter.
- [A process handler with its own stop handling] → `createProcessHandler` is the one place that creates the handler; a subclass with graceful stop needs a constructor from a started `Process`.
- [Runs no longer build their command line with `Project.buildRobotCodeCommandLine()`, which the language server and discovery keep using] → The run state builds its global options with the same `robotCodeArguments`, so the selected profiles reach runs and the robotcode extra args stay out of them, as the main specs `intellij-configuration-profiles` and `intellij-settings` require; a unit test covers the assembled arguments.

## Migration Plan

- Stored elements keep type and factory ids. An element without RobotCode options and without `ADD_CONTENT_ROOTS` comes from an earlier version: it opens with an empty `PATHS` target and the defaults above, keeps its name and Before launch tasks, and runs the configured paths, as it did after every restart before.
- An old temporary configuration such as "Test First Test Passes" has no target, so the next gutter run of that test creates a new temporary configuration, which the platform names "Test First Test Passes (1)" once. Users can delete the old one; temporary configurations also age out.
- An older plugin version reading a configuration written by this version ignores the unknown fields and runs the project, as it always did.
