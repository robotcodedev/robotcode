# Design

## Context

See proposal.md for the motivation. The state that shapes the approach:

- **Today on main:**
  - `Project.robotPythonModule` returns the first module that has a Python SDK, and `Project.robotPythonSdk` its SDK (`RobotCodeHelpers.kt:59-68`).
  - `RobotCodeEnvironment.projectInterpreter` is the interpreter of `robotPythonSdk` (`RobotCodeEnvironment.kt:281`). The language server, both discovery calls, the profile list and the banner use it.
  - `RobotCodeRunConfiguration.applyRobotCodeDefaults` gives new configurations, the template and configurations from earlier versions `robotPythonModule` with "use module SDK" (`execution/RobotCodeRunConfiguration.kt:44-51`).
  - `RobotCodeRootPythonPath.rootPythonPath` takes the content and source roots of `robotPythonModule` and the modules it depends on (#430).
- **Archived changes this builds on:**
  - `intellij-environment-check`: `RobotCodeEnvironment` keeps the environment state per interpreter, checks in the background, watches the workspace model (`watchWorkspaceModel`) and compares interpreter identities. `RobotCodeLanguageServerFactory.isEnabled` and the test manager read the state without waiting; the banner in `editor/EditorNotificationProvider.kt` follows it.
  - `intellij-run-configuration-target`: Robot Framework run configurations extend `AbstractPythonRunConfiguration`; targets are "Configured paths", "Files and folders" and "Tests and suites". A run with a remote interpreter is refused when it starts (`execution/RobotCodeRunProfileState.kt:172`).
  - `intellij-extra-args` and `intellij-profiles`: the personal component `RobotCodePersonalConfiguration` (state `RobotCodePersonalSettings`, `.idea/workspace.xml`) holds the extra arguments, the profiles and "Disable extension". `checkConfiguration()` warns about unknown profiles from the cached profile list.
  - `intellij-settings-pages`: the "General" page under "Robot Framework" (`RobotCodeGeneralConfigurable`) shows these personal rows.
  - `intellij-source-roots-python-path`: the switches "Add content roots to the Python path" and "Add source roots to the Python path" of the "Robot" page.
- **Restarts:** a settings change (`publishRobotCodeSettingsChanged()`) reaches the restart manager (`RobotCodeHelpers.kt:143`), which compares what the running server and the last discovery got with what they would get now, and restarts only what changed.
- **A gap at the start of runs:** `RobotCodeRunConfiguration.getState` calls `RobotCodeEnvironment.ensureUsableForRun()`, which checks `projectInterpreter` (`RobotCodeEnvironment.kt:305`), while the run uses the configuration's interpreter. The requirement "Runs report an unusable interpreter" of `intellij-python-environment` already speaks of the interpreter the run uses.
- **Modules without roots:** on 2026-10-21 a PyCharm project with the pyproject.toml project model had two modules with the same interpreter: one without any roots first, and the module that PyCharm manages for the `pyproject.toml`, with the project folder and the folders marked as Sources, second. RobotCode took the first, and the roots never reached the server.
- **`AbstractPythonRunConfiguration` in PyCharm 2026.1** (javap):
  - `checkConfiguration()` calls `super`, then `checkSdk()` and then `checkExtensions()`, which runs the validation of Python run-configuration extensions.
  - In PyCharm (`PlatformUtils.isPyCharm()`), `checkSdk()` only requires a non-blank interpreter path: "Please select a valid Python interpreter". In other IDEs it requires, in module mode, a module with a Python SDK ("Please select a module with a valid Python SDK"); without an SDK home, a Python project SDK ("Please specify a Python SDK"); and for an explicit SDK, that it seems valid. It checks neither the Python version, nor Robot Framework, nor remote interpreters, nor targets.
  - `getSdk()` returns the module's Python SDK in module mode, otherwise the explicit SDK or the SDK found by its home path.
- **Validation API:** `RuntimeConfigurationError` and `RuntimeConfigurationWarning` have unannotated constructors `(String, Runnable)` whose `Runnable` becomes the fix. `ConfigurationQuickFix` is `@ApiStatus.Experimental` in 2026.1.
- **The Python Interpreter page** has the configurable id `com.jetbrains.python.configuration.PyActiveSdkModuleConfigurable`, both in PyCharm and in the Python plugin for IntelliJ IDEA (`python-ce` plugin.xml). PyCharm's own interpreter quick fixes open it by that id.
- **SDK lookup:** `com.jetbrains.python.sdk.PythonSdkUtil.findPythonSdk(Module)` (unannotated) returns a module's Python SDK, including one inherited from the project.
- **How VS Code detects a Robot Framework project** (`languageclientsmanger.ts`, `isRobotProject`): a workspace folder qualifies with a `robot.toml` or `.robot.toml`, a `pyproject.toml` that matches `ROBOT_DEPENDENCY_IN_PYPROJECT` after comment lines are removed, a `requirements.txt` that matches `ROBOT_REQUIREMENT` (both for the packages `robotframework` and `robotcode`), or a Robot Framework file found by a search that skips `.*`, `_*`, `CVS`, `node_modules`, `target`, `build`, `dist` and `venv` and gives up after 5 seconds.
- **One language server per project:** LSP4IJ starts one instance per server definition and project. lsp4ij#1352 ended with workspace folders for that one instance (#1492), which does not give a module its own interpreter. lsp4ij#1701 (2026-10-16) asks for a scope API that allows one instance per module; it has no answer yet.

## Goals / Non-Goals

**Goals:**

- One interpreter choice per project that the language server, discovery, the profile list, new run configurations and the roots of the "Robot" page's switches share, without guessing when several modules qualify.
- No waiting for the index in projects with one module or with a remembered choice.
- Problems of a run configuration visible before Run, without duplicating PyCharm's interpreter check and without blocking the IDE.

**Non-Goals:**

- The per-configuration interpreter and environment activation, which PyCharm's run configuration options already bring.
- Language servers per module or per content root, which wait for lsp4ij#1701.
- Supporting remote interpreters.
- Reporting empty targets, which the target fragment already does.

## Decisions

### One module, the remembered choice, then detection

The plugin resolves the module in this order:

1. When exactly one module has a Python SDK (`PythonSdkUtil.findPythonSdk`, which includes an inherited project SDK), that module is used at once. This covers the usual PyCharm project and needs no index.
2. When several modules have one and the personal component names one of them, that module is used at once.
3. Otherwise the plugin detects the Robot Framework projects among those modules:
   - the content roots' `robot.toml`, `.robot.toml`, `pyproject.toml` and `requirements.txt` are read through the VFS, with the same patterns as the VS Code client;
   - the Robot Framework files are found with `FileTypeIndex.containsFileOfType` for the suite and resource file types in each module's content scope, in a `smartReadAction`.

   With exactly one result the module is used and written to the personal component. With none the first module that has a Python SDK is used, which is today's rule, and nothing is stored. With several, nothing is used yet; see the next decision.

Modules that share one interpreter count separately: a module without content roots has neither files nor a `robot.toml`, so the detection passes it over.

Only the first opening of a project with several modules waits for the index. The resolved module and the reason go to idea.log.

The plugin resolves again when the stored module no longer exists or no longer has a Python SDK, and detects again when modules or their content roots change. A request for a detection that runs for the same modules repeats it once it is done instead of cancelling it, so that frequent changes do not keep it from finishing. It does not ask again because a second module gets Robot Framework files later: a stored choice stays until the user changes it.

Alternatives:
- Breaking a tie by the module of the project folder and then by module name: it guesses, and a wrong guess starts the language server with an interpreter without Robot Framework, which is #489 again.
- One language server per module, registered at runtime through LSP4IJ's `LanguageServersRegistry`: the registry is application-wide, every module would show up as a server of its own, and the language mapping and the semantic-tokens provider in `plugin.xml` are bound to the server id `RobotCode`.
- Taking the roots of every module with the chosen interpreter, without a module choice: RobotCode would work around the module structure instead of choosing the module that holds the Robot Framework project, and decided against it on 2026-10-21.
- A path setting for the interpreter, like VS Code's deprecated `robotcode.python`: the module choice keeps the SDK model of the IDE as the source of the interpreter.

### The roots follow the chosen module

`robotPythonModule` returns the chosen module, and `robotPythonSdk` its interpreter. `rootPythonPath`, `projectInterpreter` and `applyRobotCodeDefaults` read them as today, so the roots of the "Robot" page's switches, the language server, discovery, the profile list and new run configurations follow the choice without changes of their own.

Alternative: a separate function for the module of the roots. Two answers to "which module" could disagree.

### Several Robot Framework modules: ask, start nothing meanwhile

When the detection finds several modules, the plugin shows a sticky notification that names them, with one action per module, and the editor banner on Robot Framework files says the same with the same actions. Choosing a module writes it to the personal component, closes the notification, refreshes the banners and calls `publishRobotCodeSettingsChanged()`; the restart manager then starts the language server and discovery, whose interpreter changed. Until then, `isEnabled` returns false and discovery does not run, so nothing starts with an interpreter that may lack Robot Framework.

Alternative: starting with the first candidate and offering a switch. That starts processes with an interpreter the user did not choose, which may fail for the same reason as #489.

### The choice is personal and shown on the "General" page

The chosen module is a module name in a new field of `RobotCodePersonalConfiguration` (`.idea/workspace.xml`). The "General" page shows a personal row "Module for RobotCode" next to "Disable extension", the extra arguments and the profiles, with the modules that have a Python SDK, only while there are several. Applying another module stores it and calls `publishRobotCodeSettingsChanged()`.

Alternative: the shared `robotcodeSettings.xml`. The module structure is shared, but what one user picks should not change a file under version control.

### The choice is part of the environment state

`RobotCodeEnvironment` resolves the choice from the modules, the stored module and the cached result of the detection, which runs in the background. Each access resolves once and takes the module, its interpreter and its state from that one resolution, which needs neither the index nor waiting. Before the detection has a result, consumers see no result, as before the first check. The last choice and interpreter are kept to log and follow a change.

Alternative: caching the resolved module as well. With one module or a stored module the resolution is cheap, and a cache would need its own invalidation on module and SDK changes.

### New configurations start with the chosen interpreter

`applyRobotCodeDefaults` already gives new configurations, the template and configurations from earlier versions `robotPythonModule` with "use module SDK", so they get the chosen module. A configuration that stores a module or an interpreter keeps it. While the choice is missing, the platform's default stays.

Alternative: setting the module in the producer for each gutter run. Users who choose an interpreter in the template would then be overruled.

### Validation reads the state and reports in addition to PyCharm

`checkConfiguration()` calls `super` first, so PyCharm reports a missing or invalid interpreter in its own words, and RobotCode adds nothing about it. The warning about unknown profiles stays. If `getSdk()` returns an SDK, the plugin reads the state of that interpreter from `RobotCodeEnvironment`:
- no result yet: it requests a check in the background and reports nothing;
- a result that is not usable: an error with the message of the result and the fix;
- remote: an error that runs with remote interpreters are not supported yet, without a fix;
- a failed check: a warning.

It then checks the target:
- each path of a "Files and folders" target, after macro expansion and relative to the project folder, must exist; Robot Framework stops a run with a missing path anyway;
- the full names of a "Tests and suites" target are compared with the current discovery model when discovery has a result and the configuration's profiles resolve to the profiles of the project, which discovery uses; missing items give a warning.

The fix is the `Runnable` of the `(String, Runnable)` constructors. It opens the Python Interpreter page with `ShowSettingsUtil.showSettingsDialog(project, predicate, null)`, where the predicate matches the configurable id. The refusal of remote interpreters at the start of a run stays as a safety net for starts without validation.

Alternatives:
- `ConfigurationQuickFix` constructors: experimental in 2026.1.
- Opening the page by its display name: this fails with localized IDEs.
- PyCharm's `InterpreterSettingsQuickFix.showPythonInterpreterSettings`: it opens the same id, and its fallback to Project Structure is not needed because both IDEs register the id. It lives in the Python plugin's implementation module.

### The start of a run checks the configuration's interpreter

`ensureUsableForRun` takes the interpreter of the configuration's `getSdk()` instead of `projectInterpreter`, so a configuration with its own usable interpreter runs while the project's interpreter is unusable, and one with an unusable interpreter does not run while the project's is usable. The waiting with a progress indication for a missing result stays as it is. A result that is not usable is checked again when the SDK of its interpreter changes and on Retry and Restart, for the interpreters of run configurations as for the project's, so that a configuration is not refused for an interpreter that has Robot Framework by now.

Alternative: keeping the project's interpreter. A run would be refused or allowed by an interpreter it does not use.

## Risks / Trade-offs

- [Robot Framework files in several modules with different interpreters] → One language server serves the project with the chosen module's interpreter, and files of other modules are analysed with it. Runs can choose their interpreter per configuration. One server per module waits for lsp4ij#1701.
- [The user ignores the notification] → The banner on every Robot Framework file keeps asking, and the "General" page offers the choice as well.
- [The validation runs before a check has finished] → The editor validates again on the next change, and the start of a run waits for a missing result anyway.
- [The first opening of a project with several modules waits for the index] → Only that case uses the index; projects with one module and later openings with a stored choice start at once.
- [The patterns for `pyproject.toml` and `requirements.txt` drift from the VS Code client] → The Kotlin patterns name the VS Code constants they copy, and their unit tests cover dependency tables, extras, version specifiers and comment lines.
- [The staleness warning compares with a discovery model that may be outdated] → It is a warning only and does not keep the run from starting.

## Migration Plan

None. Configurations keep a stored module or interpreter. Only new configurations, the template, and configurations from earlier versions without stored interpreter options get the new default.
