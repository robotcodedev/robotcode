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

## Goals / Non-Goals

**Goals:**

- One interpreter choice per project that the language server, discovery, the profile list and new run configurations share.
- Problems of a run configuration visible before Run, without duplicating PyCharm's interpreter check and without blocking the IDE.

**Non-Goals:**

- The per-configuration interpreter and environment activation, which the run-configuration rework already brings through PyCharm's options.
- Language servers per module or per content root.
- Supporting remote interpreters.
- Reporting empty targets, which the target fragment already does.

## Decisions

### The module that holds the Robot Framework project

All robotcode processes start in the project folder, and robotcode takes the folder with `robot.toml` or `.robot.toml` above its working directory as the project root. So:

1. When the project folder has a `robot.toml` or `.robot.toml`, the module that contains the project folder holds the Robot Framework project.
2. Otherwise, the module that contains the Robot Framework suite and resource files holds it. When several modules contain such files, the plugin takes the one that contains the project folder, otherwise the first of them in the order of module names, so that the choice is stable.
3. A module counts only with a Python SDK (`PythonSdkUtil.findPythonSdk`). Without such a module, the project SDK follows, and then the first module that has a Python SDK, which is today's rule.

Alternatives:
- Only the module of the project folder: this does not fix #489 when the project folder is not a module's content root or belongs to a module without Robot Framework.
- The module of the file in the editor: one language server serves the whole project, so the interpreter would change with the active file.
- A RobotCode interpreter setting: VS Code deprecated `robotcode.python`, and the analysis decided against it because the SDK model covers the need.

### The choice is part of the environment state

The environment service computes the choice in the background, in a `smartReadAction` with `FileTypeIndex.containsFileOfType` per module scope, and keeps it together with the identity of the chosen interpreter. It computes the choice again on the workspace model changes it already watches, and when the project is marked as using Robot Framework, that is, when its first Robot Framework file is opened. Every consumer reads the cached choice. Before the first choice exists, they see no result, as before the first check. The log line names the interpreter and the step that chose it.

Alternative: resolving on every request. LSP4IJ's `isEnabled` and the banner need an answer without index access or waiting.

### New configurations start with the chosen interpreter

The default of the run-configuration rework, the first module that has a Python SDK, becomes the choice:
- if the choice came from a module, the configuration gets that module with "use module SDK";
- if it came from the project SDK, the configuration gets that SDK as its interpreter.

This applies to the template that the factory creates and to the defaults that configurations from earlier versions receive. A configuration that stores a module or an interpreter keeps it. Without a choice yet, the platform's default stays.

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

- [Robot Framework files in several modules with different interpreters] → One language server serves the project, so the plugin takes one interpreter and logs which one and why. Runs can choose their interpreter per configuration.
- [The validation runs before a check has finished] → The editor validates again on the next change, and the start of a run waits for a missing result anyway.
- [The choice needs smart mode for its index step] → Before smart mode, consumers see no result yet; the environment check starts once the choice exists.
- [The staleness warning compares with a discovery model that may be outdated] → It is a warning only and does not keep the run from starting.

## Migration Plan

None. Configurations keep a stored module or interpreter. Only new configurations, the template, and configurations from earlier versions without stored interpreter options get the new default.
