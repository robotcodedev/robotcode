# Design

## Context

See proposal.md for the motivation. The state that shapes the approach:

- **Today on main:** `Project.robotPythonSdk` returns the Python SDK of the first module that has one (`RobotCodeHelpers.kt:40-43`). The environment check and `buildRobotCodeCommandLine` use it for the language server, both discovery calls and runs.
- **Planned changes this builds on, not implemented yet:**
  - `intellij-environment-check`: a project service keeps the environment state per interpreter, resolves the project interpreter with `robotPythonSdk`, watches the workspace model (modules, SDKs, project settings) and compares interpreter identities; LSP4IJ, the banner, discovery and the run path read that state, and the run path asks for the interpreter it runs with.
  - `intellij-run-configuration-target`: Robot Framework run configurations extend `AbstractPythonRunConfiguration`. New configurations, the template and configurations from earlier versions get the first module that has a Python SDK, with the module's interpreter. Targets are "Configured paths", "Files and folders" and "Tests and suites". A target without paths or items runs like "Configured paths", and the target fragment warns about it. `buildPythonExecution` refuses a remote interpreter with an `ExecutionException`. A stale selection runs no test, and that design leaves the warning about it to validation before the run.
- **`AbstractPythonRunConfiguration` in PyCharm 2026.1** (javap):
  - `checkConfiguration()` calls `super`, then `checkSdk()` and then `checkExtensions()`, which runs the validation of Python run-configuration extensions.
  - In PyCharm (`PlatformUtils.isPyCharm()`), `checkSdk()` only requires a non-blank interpreter path: "Please select a valid Python interpreter". In other IDEs it requires, in module mode, a module with a Python SDK ("Please select a module with a valid Python SDK"); without an SDK home, a Python project SDK ("Please specify a Python SDK"); and for an explicit SDK, that it seems valid. It checks neither the Python version, nor Robot Framework, nor remote interpreters, nor targets.
  - `getSdk()` returns the module's Python SDK in module mode, otherwise the explicit SDK or the SDK found by its home path.
  - The constructor picks any first module.
- **Validation API:** `RuntimeConfigurationError` and `RuntimeConfigurationWarning` have unannotated constructors `(String, Runnable)` whose `Runnable` becomes the fix. `ConfigurationQuickFix` is `@ApiStatus.Experimental` in 2026.1.
- **The Python Interpreter page** has the configurable id `com.jetbrains.python.configuration.PyActiveSdkModuleConfigurable`, both in PyCharm and in the Python plugin for IntelliJ IDEA (`python-ce` plugin.xml). PyCharm's own interpreter quick fixes open it by that id.
- **SDK lookup:** `com.jetbrains.python.sdk.PythonSdkUtil.findPythonSdk(Module)` (unannotated) returns a module's Python SDK, including one inherited from the project.
- **How VS Code detects a Robot Framework project** (`languageclientsmanger.ts`, `isRobotProject`): a workspace folder qualifies with a `robot.toml` or `.robot.toml`, a `pyproject.toml` that matches `ROBOT_DEPENDENCY_IN_PYPROJECT` after comment lines are removed, a `requirements.txt` that matches `ROBOT_REQUIREMENT` (both for the packages `robotframework` and `robotcode`), or a Robot Framework file found by a search that skips `.*`, `_*`, `CVS`, `node_modules`, `target`, `build`, `dist` and `venv` and gives up after 5 seconds.
- **Personal settings:** the plugin has only the shared state component today. `intellij-extra-args` and `intellij-profiles` plan the personal component `RobotCodePersonalConfiguration` (state name `RobotCodePersonalSettings`, `StoragePathMacros.WORKSPACE_FILE`); whichever change lands first creates it.
- **The "Robot Framework" settings page:** `intellij-settings-pages` plans the parent page with the shared settings, and `intellij-profiles` adds personal rows to it.
- **One language server per project:** LSP4IJ starts one instance per server definition and project, and its maintainer calls several instances "not trivial" (lsp4ij#1352). One server per module therefore waits for workspace folder support in the RobotCode language server.

## Goals / Non-Goals

**Goals:**

- One interpreter choice per project that the language server, discovery, the profile list and new run configurations share, without guessing when several modules qualify.
- No waiting for the index in projects with one module or with a remembered choice.
- Problems of a run configuration visible before Run, without duplicating PyCharm's interpreter check and without blocking the IDE.

**Non-Goals:**

- The per-configuration interpreter and environment activation, which the run-configuration rework already brings through PyCharm's options.
- Language servers per module or per content root.
- Supporting remote interpreters.
- Reporting empty targets, which the target fragment already does.

## Decisions

### One module, the remembered choice, then detection

The plugin resolves the interpreter in this order:

1. When exactly one module has a Python SDK (`PythonSdkUtil.findPythonSdk`, which includes an inherited project SDK), that module is used at once. This covers the usual PyCharm project and needs no index.
2. When several modules have one and the personal component names one of them, that module is used at once.
3. Otherwise the plugin detects the Robot Framework projects among those modules:
   - the content roots' `robot.toml`, `.robot.toml`, `pyproject.toml` and `requirements.txt` are read through the VFS, with the same patterns as the VS Code client;
   - the Robot Framework files are found with `FileTypeIndex.containsFileOfType` for the suite and resource file types in each module's content scope, in a `smartReadAction`.

   With exactly one result the module is used and written to the personal component. With none the first module that has a Python SDK is used, which is today's rule, and nothing is stored. With several, nothing is used yet; see the next decision.

Only the first opening of a project with several modules waits for the index. The resolved module and the reason go to idea.log.

The plugin resolves again when the stored module no longer exists or no longer has a Python SDK, and on the workspace model changes that `intellij-environment-check` watches. It does not ask again because a second module gets Robot Framework files later: a stored choice stays until the user changes it.

Alternatives:
- Breaking a tie by the module of the project folder and then by module name, as this plan proposed before: it guesses, and a wrong guess starts the language server with an interpreter without Robot Framework, which is #489 again.
- One language server per module, registered at runtime through LSP4IJ's `LanguageServersRegistry`: public but undocumented API for a case that LSP4IJ does not support (lsp4ij#1352).
- A path setting for the interpreter, like VS Code's deprecated `robotcode.python`: the module choice keeps the SDK model of the IDE as the source of the interpreter.

### Several Robot Framework modules: ask, start nothing meanwhile

When the detection finds several modules, the plugin shows a sticky notification that names them, with one action per module, and the editor banner on Robot Framework files says the same with the same actions. Choosing a module writes it to the personal component, closes the notification, refreshes the banners and starts the language server and discovery through the restart path. Until then, LSP4IJ's `isEnabled` returns false and discovery does not run, so nothing starts with an interpreter that may lack Robot Framework.

Alternative: starting with the first candidate and offering a switch. That starts processes with an interpreter the user did not choose, which may fail for the same reason as #489.

### The choice is personal and shown on the settings page

The chosen module is a module name in `RobotCodePersonalConfiguration` (`.idea/workspace.xml`). This change creates the component if neither `intellij-extra-args` nor `intellij-profiles` has done so, or adds its field. The "Robot Framework" page shows a personal row "Module for RobotCode" with the modules that have a Python SDK, only while there are several. Applying another module restarts the language server and discovery through the restart path.

Alternative: the shared `robotcodeSettings.xml`. The module structure is shared, but the decision follows D2: what one user picks should not change a file under version control.

### The choice is part of the environment state

The environment service of `intellij-environment-check` keeps the resolved module, or "waiting for a choice", together with the identity of the chosen interpreter, and resolves it in the background. Every consumer reads the cached result. Before the first result exists, they see no result, as before the first check.

Alternative: resolving on every request. LSP4IJ's `isEnabled` and the banner need an answer without index access or waiting.

### New configurations start with the chosen interpreter

The default of the run-configuration rework, the first module that has a Python SDK, becomes the chosen module, with "use module SDK". This applies to the template that the factory creates and to the defaults that configurations from earlier versions receive. A configuration that stores a module or an interpreter keeps it. Without a choice yet, the platform's default stays.

Alternative: setting the module in the producer for each gutter run. Users who choose an interpreter in the template would then be overruled.

### Validation reads the state and reports in addition to PyCharm

`checkConfiguration()` calls `super` first, so PyCharm reports a missing or invalid interpreter in its own words, and RobotCode adds nothing about it. If `getSdk()` returns an SDK, the plugin reads the state of that interpreter from the environment service:
- no result yet: it requests a check in the background and reports nothing;
- a result that is not usable: an error with the message of the result and the fix;
- remote: an error that runs with remote interpreters are not supported yet, without a fix;
- a failed check: a warning.

It then checks the target:
- each path of a "Files and folders" target, after macro expansion and relative to the project folder, must exist; Robot Framework stops a run with a missing path anyway;
- the full names of a "Tests and suites" target are compared with the current discovery model when discovery has a result, and missing items give a warning.

The fix is the `Runnable` of the `(String, Runnable)` constructors. It opens the Python Interpreter page with `ShowSettingsUtil.showSettingsDialog(project, predicate, null)`, where the predicate matches the configurable id. The launch refusal of remote interpreters in `buildPythonExecution` stays as a safety net for starts without validation.

Alternatives:
- `ConfigurationQuickFix` constructors: experimental in 2026.1.
- Opening the page by its display name, as the editor banner does today: this fails with localized IDEs.
- PyCharm's `InterpreterSettingsQuickFix.showPythonInterpreterSettings`: it opens the same id, and its fallback to Project Structure is not needed because both IDEs register the id. It lives in the Python plugin's implementation module.

## Risks / Trade-offs

- [Robot Framework files in several modules with different interpreters] → One language server serves the project with the chosen module's interpreter, and files of other modules are analysed with it. Runs can choose their interpreter per configuration. One server per module waits for workspace folder support in the language server.
- [The user ignores the notification] → The banner on every Robot Framework file keeps asking, and the settings page offers the choice as well.
- [The validation runs before a check has finished] → The editor validates again on the next change, and the start of a run waits for a missing result anyway.
- [The first opening of a project with several modules waits for the index] → Only that case uses the index; projects with one module and later openings with a stored choice start at once.
- [The patterns for `pyproject.toml` and `requirements.txt` drift from the VS Code client] → The Kotlin patterns name the VS Code constants they copy, and their unit tests cover dependency tables, extras, version specifiers and comment lines.
- [The staleness warning compares with a discovery model that may be outdated] → It is a warning only and does not keep the run from starting.

## Migration Plan

None. Configurations keep a stored module or interpreter. Only new configurations, the template, and configurations from earlier versions without stored interpreter options get the new default.
