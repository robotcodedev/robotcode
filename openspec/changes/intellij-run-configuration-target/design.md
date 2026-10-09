# Design

## Context

See proposal.md for the motivation. Decision D1 of the maintainer: remote interpreters are a goal, starting with WSL, so run configurations extend PyCharm's `AbstractPythonRunConfiguration` with a `PythonCommandLineState` subclass (option P of the parity analysis), and local runs must keep working as before. This change runs on the local target only; WSL runs come later.

**Builds on a planned change.** The pure selection-argument builder comes from the planned change `intellij-run-selection-args`, which is not implemented yet. This design relies on its planned form: a resolve step that turns a selection into entries (kind, full name, suite name and `relSource` for `-s` and `-I`, top-level suite name), and a pure emit step that turns entries plus the parse-include flag into the arguments after `--`.

**Current plugin code** (checked on 2026-10-03):

- `RobotCodeRunConfiguration` extends `LocatableConfigurationBase<ConfigurationFactory>`; `writeExternal`/`readExternal` only call `super` and carry TODOs. `includedTestItems` (discovery items set by the producer) and `paths` (never read) live in memory. `RobotCodeRunConfigurationFactory` declares no options class and keeps the factory id `ROBOT_FRAMEWORK_TEST`; the configuration type id is `RobotCodeConfigurationType`.
- `RobotCodeRunConfigurationEditor` is a UI DSL `SettingsEditor` whose `resetEditorFrom`/`applyEditorTo` are empty.
- `RobotCodeRunProfileState` extends `CommandLineState`. `startProcess()` builds the command line with `Project.buildRobotCodeCommandLine()`: the first module that has a Python SDK, `-u -X utf8`, the bundled `robotcode`, the project folder as working directory, UTF-8, and the project's environment check as a gate. It creates a `KillableColoredProcessHandler`, stores the debug port in the handler and registers itself as process listener; `startNotified()` runs the DAP handshake. `execute()` creates the SM test console (`RobotCodeRunnerConsoleView` with `RobotRunnerConsoleProperties`) on the UI thread and sets the rerun-failed action.
- `RobotCodeProgramRunner` and `RobotCodeDebugProgramRunner` are `AsyncProgramRunner`s that call `state.execute()` on the UI thread and return a resolved promise; the debug runner starts the session with `XDebuggerManager.newSessionBuilder()`. Both are registered in `plugin.xml` without `order`.
- `RobotCodeRunConfigurationProducer` names the configuration "<Type> <name>", stores the found item, and reuses a configuration only if its stored item equals the found one; `RobotCodeTestItem.equals` compares id (with line number), range, children, tags and metadata.

**PyCharm 2026.1 API** (javap against `pycharm-2026.1`, build PY-261.22158.340, in the Gradle cache):

- `AbstractPythonRunConfiguration<T>` has no class-level `ApiStatus`. Its `@Internal` members are `patchCommandLine`, `patchCommandLineFirst`, `getUseRunTool`/`setUseRunTool` and `shouldDebugJustMyCode`/`setDebugJustMyCode`. It extends `AbstractRunConfiguration` (`ModuleBasedConfiguration<RunConfigurationModule, Element>`).
- Persistence: `AbstractPythonRunConfiguration.writeExternal` calls `super` first and then writes its own JDOM fields (`INTERPRETER_OPTIONS`, `SDK_HOME`, `SDK_NAME`, `ENV_FILES`, `WORKING_DIRECTORY`, `IS_MODULE_SDK`, `ADD_CONTENT_ROOTS`, `ADD_SOURCE_ROOTS`, `DEBUG_JUST_MY_CODE`, envs, module). Further up, `RunConfigurationBase.writeExternal` serializes the BaseState options object with `XmlSerializer`, and `readExternal` deserializes it with the class the factory returns from `getOptionsClass()`. `ModuleBasedConfiguration.clone()` copies configurations with `Element` state by writing and reading them.
- Defaults: the constructor sets `ADD_CONTENT_ROOTS` and `ADD_SOURCE_ROOTS` to `true` and picks any first module. `readExternal` reads a missing `ADD_*` field as `true` and a missing `IS_MODULE_SDK` as `false`. With neither SDK nor SDK home stored, `getSdkHome()` falls back to the module's Python SDK. An empty working directory resolves to the project base path (`getWorkingDirectorySafe()`).
- `checkConfiguration()` calls `checkSdk()`, which raises a `RuntimeConfigurationError` for a missing or invalid interpreter.
- `getConfigurationEditor()` is final: it returns `createConfigurationEditor()` directly when the registry key `python.new.run.config` is on (default `true`) and `isNewUiSupported()` returns `true`; otherwise it wraps the editor in a legacy group.
- `AbstractPythonConfigurationFragmentedEditor` (unannotated) builds Before launch, the run header, "Allow multiple instances", the interpreter and environment fragments of `PyCommonFragmentsBuilder`, interpreter options (`py.interpreter.options`), content and source roots (`py.add.content.roots`, `py.add.source.roots`), the Python debugger option `justMyCode`, an optional run-tool tag, then calls the abstract `customizeFragments(list)`, and adds the editor-extension and logs fragments. `addToFragmentsBeforeEditors` is a public helper. PyCharm's own target chooser `AbstractPyRunConfigTargetChooserFragment` is `@Internal`; `SettingsEditorFragment.isAvailable` and the static `applyEditorTo` are `@Internal`.
- `PythonCommandLineState` (no class-level `ApiStatus`): `execute(Executor)` is the target-aware path. It resolves the interpreter's target request, calls the overridable `buildPythonExecution(HelpersAwareTargetEnvironmentRequest)`, sets the working directory, applies the environment (including virtualenv/conda activation when the registry key `python.activate.virtualenv.on.run` is on, default `true`) and the `PYTHONPATH` roots, prepares the target environment, starts the process, and calls the overridable `createProcessHandler(Process, String, TargetEnvironment, TargetedCommandLine)` and `createAndAttachConsole(Project, ProcessHandler, Executor)`. The default `buildPythonExecution` asserts a background thread. `execute(Executor, ProgramRunner)` starts a process only for PyCharm's own runners and otherwise returns a console with an empty process handler. `@Internal` members: `createAndAttachConsoleInEDT`, `buildPythonPath`, `collectPythonPath`, `canRun`.
- `PythonExecution`, `PythonScriptExecution`, `PythonModuleExecution`, `TargetEnvironmentRequest` and `TargetEnvironment` are `@ApiStatus.Experimental`. `LocalTargetEnvironment`, `KillableColoredProcessHandler(Process, String, Charset)` and `com.jetbrains.python.sdk.PythonSdkUtil.isRemote`/`findPythonSdk` are unannotated; `com.jetbrains.python.sdk.legacy.PythonSdkUtil` is `@Internal`.
- Runners: `PythonRunner.canRun` accepts every `AbstractPythonRunConfiguration` for Run and runs `PythonCommandLineState.execute(Executor)` in a background coroutine before it shows the content on the UI thread. `PyDebugRunner` accepts a `DebugAwareConfiguration` only if `canRunUnderDebug()` is `true`, otherwise every `AbstractPythonRunConfiguration`. PyCharm Professional adds `PythonCoverageRunner` (guarded by `canRunWithCoverage()`), and `PythonProfileRunner` and `PyConcurrencyDebugRunner`, which accept every `AbstractPythonRunConfiguration` for their executors.
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
- the target kind: `NONE` ("Configured paths", the default), `PATHS` or `SELECTION`;
- the paths of a `PATHS` target;
- the entries of a `SELECTION` target, each with its kind (test, task or suite), its full name below the top-level suite, its `relSource`, and the full name below the top-level suite and `relSource` of the suite to pass with `-s` and `-I`;
- the name of the top-level suite when the selection was made.

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

- `NONE`: no paths and no selection arguments.
- `PATHS`: the paths become the last arguments after `--`.
- `SELECTION`: each entry's full name is completed with the top-level suite name from the current discovery model (the first child of the workspace item), or with the stored name when discovery has no result. The completed entries go to the emit step of the selection-argument builder. An entry the user typed in the editor has only a name: the run looks it up in the current model by full name and fills in its kind and suite; if it is not found, only `-bl` is passed for it.
- A `PATHS` or `SELECTION` target without paths or entries runs like `NONE`; the editor shows a warning through the fragment's validation.

Storing names below the top-level suite follows decision D1 of the test area of the analysis: the top-level suite is named after the project folder unless `robot.toml` sets `name`, so absolute names break when the folder is renamed or checked out elsewhere.

Alternative: storing absolute names and looking up everything in discovery at launch. Shared configurations then break in another checkout, and nothing runs right when discovery failed.

### The run state on `PythonCommandLineState`

`RobotCodeRunProfileState` extends `PythonCommandLineState` and uses its target-aware `execute(Executor)`:
- `buildPythonExecution(request)` checks the project's environment as today (the same gate and message), refuses a remote interpreter (`PythonSdkUtil.isRemote`) with an `ExecutionException` that says remote interpreters are not supported yet, picks the debug port as today, and returns a `PythonScriptExecution` of the bundled `robotcode` with `-u -X utf8` as additional interpreter parameters, UTF-8 and the arguments `--no-pager -dp . debug [--no-debug] [--tcp <port>] [-- <robot arguments>]`.
- `createProcessHandler(...)` creates the `KillableColoredProcessHandler` from the started process, stores the debug port, attaches the termination message and registers the state as process listener, as `startProcess()` does today. The DAP handshake in `startNotified()` stays unchanged.
- `createAndAttachConsole(...)` creates the SM test console as today's `execute()` does; `execute(Executor)` adds the rerun-failed action to the result.

Alternatives:
- A `PythonModuleExecution` of `robotcode.cli`: it needs RobotCode installed in the interpreter; the bundled tool keeps parity with today and with the language server.
- The legacy `GeneralCommandLine` path of `PythonCommandLineState`: not target-capable.

### Runners: first in line, start off the UI thread

Both program runners get `order="first"` in `plugin.xml`, so `PythonRunner`, which accepts every `AbstractPythonRunConfiguration` for Run, does not take Robot Framework configurations. Both runners call `state.execute(executor)` on a background thread, as `PythonRunner` does, because interpreter activation and target preparation must not run on the UI thread. The Run runner then shows the content on the UI thread; the Debug runner builds the debug session on the UI thread with a starter that wraps the existing execution result. The debug process subscribes to the handshake before the platform calls `startNotify()`, as today.

Alternative: keeping `execute()` on the UI thread. The default `buildPythonExecution` asserts a background thread, and reading an activated virtualenv or conda environment runs its activate script in a shell (cached per interpreter).

### The editor: PyCharm's fragments plus a Robot Framework target fragment

`RobotCodeRunConfigurationEditor` extends `AbstractPythonConfigurationFragmentedEditor`. In `customizeFragments` it removes `justMyCode` and the run-tool tag, which belong to Python runs, and adds the target fragment before the editors with `addToFragmentsBeforeEditors`. The target fragment is an own `SettingsEditorFragment` built with its public constructor:
- a choice of the three kinds;
- a list of files and folders with a browse button for `PATHS`;
- the stored names, one per line, for `SELECTION`.

Its comments say that paths replace the paths of `robot.toml` and rename the top-level suite. When applied, lines whose name is unchanged keep their stored entry; new lines become name-only entries. All texts are in `RobotCode.properties`.

Alternative: PyCharm's `AbstractPyRunConfigTargetChooserFragment`, which is `@Internal`.

### The producer compares stable keys

The producer writes a `SELECTION` entry for a test, task or suite, taking the suite of a test from the current model by file as the selection-argument builder does, and a `NONE` target for the project folder. `isConfigurationFromContext` compares the target kind and the entries' kinds and names below the top-level suite, so line shifts and refreshed discovery objects no longer break the match. The name stays "<Type> <name>"; the producer changes no other value of the configuration.

## Risks / Trade-offs

- [Experimental API: the state's overrides use `PythonExecution`, `PythonScriptExecution`, `HelpersAwareTargetEnvironmentRequest` and `TargetEnvironment`] → They are confined to `buildPythonExecution` and `createProcessHandler`. `verifyPlugin` runs against 261 and the newer configured versions and reports changes. PyCharm's own test and uv run states override `buildPythonExecution` too, and its test states override `createAndAttachConsole` for their test console.
- [PythonCore classes change with every release] → Only the base class, the state's three overrides and the fragmented editor touch them, and each harness run uses the current PyCharm build.
- [The options class shares the configuration element with PyCharm's JDOM fields] → Distinct property names, and unit tests for the round trip and for `clone()`. If the round trip shows interference, the RobotCode options move into a child element written with `XmlSerializer`; the stored values stay the same.
- [Virtualenv and conda activation changes the environment of runs] → It matches PyCharm's own Python runs and helps conda on Windows; a line in the release notes.
- [PyCharm Professional's Profile and Concurrency Diagram executors accept every `AbstractPythonRunConfiguration`] → The configuration cannot switch them off; they are not supported for Robot Framework runs. "Run with Coverage" is switched off through `canRunWithCoverage()`. The harness runs without the Professional module, so this cannot be checked there.
- [Python run-configuration extensions of other plugins, such as `.env` plugins, now apply to Robot Framework runs] → This is the same behaviour as for Python runs.
- [The process starts off the UI thread, while the DAP handshake still runs on it] → Moving the handshake off the UI thread is separate work; this change only moves what the target API requires.
- [A stored selection that no longer matches ends with Robot Framework's "contains no tests after model modifiers" error] → Only reruns after a rename are affected; a warning for stale entries before the run belongs to the validation of run configurations.
- [The environment check stays project-wide] → A configuration with another interpreter is gated by the project interpreter's check until the check runs per interpreter.
- [A process handler with its own stop handling] → `createProcessHandler` is the one place that creates the handler; a subclass with graceful stop needs a constructor from a started `Process`.
- [Runs no longer build their command line with `Project.buildRobotCodeCommandLine()`, which the language server and discovery keep using] → Global `robotcode` options that later work adds there and that apply to runs, such as profiles (`-p`), must also go into the run state's argument assembly, before `-dp` and in the same order as there. The run state keeps that assembly in one pure function, so both places are easy to find and test. If the profiles or extra-arguments change has landed first, the run state reuses its shared argument function (`robotCodeArguments`) for these options instead of keeping a second copy.

## Migration Plan

- Stored elements keep type and factory ids. An element without RobotCode options and without `ADD_CONTENT_ROOTS` comes from an earlier version: it opens with the `NONE` target and the defaults above, keeps its name and Before launch tasks, and runs the configured paths, as it did after every restart before.
- An old temporary configuration such as "Test First Test Passes" has no target, so the next gutter run of that test creates a new temporary configuration, which the platform names "Test First Test Passes (1)" once. Users can delete the old one; temporary configurations also age out.
- An older plugin version reading a configuration written by this version ignores the unknown fields and runs the project, as it always did.
