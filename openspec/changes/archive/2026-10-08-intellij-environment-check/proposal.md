# Proposal

## Why

Before RobotCode starts anything in PyCharm or IntelliJ IDEA, it checks that the project's Python interpreter can run it. Whenever no result is cached, that check blocks whoever asks: the language server start, the editor banner and the status bar wait for up to two Python processes of five seconds each. A check that only times out, for example on a slow first start, is cached like a broken interpreter, so RobotCode stays off until the next SDK event. The banner cannot tell a missing Robot Framework from an old one, and a run with an unusable interpreter fails with a generic text.

At the same time RobotCode starts its language server and a full test discovery in every project, also in pure Python projects and in PyCharm's Welcome project. It restarts both on every SDK or module event, for example when PyCharm refreshes the SDK roots after opening a project, but misses a change of the project SDK for modules that inherit it. A remote interpreter (WSL, Docker or SSH) is reported as "invalid", or, if its path also exists on the local machine, checked and run with the local Python.

## What Changes

- The environment check runs in the background. No editor, banner, status bar or language server start waits for it anymore. Until a result exists, RobotCode simply does not start yet.
- The check gives a separate result for each problem, and the editor banner and the error of a run name it:
  - no Python interpreter;
  - an interpreter path that does not exist;
  - a Python older than 3.10, with the detected version;
  - Robot Framework not installed;
  - Robot Framework older than 5.0, with the detected version;
  - a remote interpreter, which RobotCode does not support yet;
  - a check that failed or timed out.
- A check that fails or times out is not taken as a result about the interpreter. The banner says that the check failed, idea.log gets the command line, the exit code and the output, and the next restart, interpreter change or run checks again.
- One Python process checks the Python and the Robot Framework version together, instead of two processes.
- RobotCode checks again and restarts only when the interpreter it uses really changes: another SDK, another path, or a new project SDK for modules that inherit it. A refresh of the SDK roots or a newly excluded folder restarts nothing. When the interpreter is not usable, a change of its packages is checked again, so installing Robot Framework from a terminal is picked up without a restart.
- A run whose interpreter is not usable fails with the IDE's usual "Error running" message, which names the problem. A run that starts before the first check has finished waits for it, with a progress dialog that can be cancelled.
- When a project opens, RobotCode starts the language server and the first discovery only if the project contains Robot Framework files or a robot.toml. In any other project, both start when the first Robot Framework file is opened. The default project and LightEdit never start them.
- RobotCode finds its bundled files through its own plugin installation, wherever the IDE installed the plugin.

Behaviour that users notice, for the release notes (not breaking): RobotCode no longer starts in projects without Robot Framework files until such a file is opened. Remote interpreters get a clear "not supported yet" message instead of "invalid".

Not part of this change: which interpreter RobotCode uses in projects with several modules; actions in the banner beyond the existing link, a switch per project and a status widget; support for remote interpreters.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-python-environment`: the background check of the interpreter, its separate results, the cases in which it runs again, and how runs and the editor report an unusable interpreter.
- `intellij-language-server`: the language server starts only in Robot Framework projects, and the plugin finds its bundled files in its own installation.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/RobotCodeHelpers.kt`: the check and its cache move into a new project service in the plugin's root package, with a topic for state changes; `buildRobotCodeCommandLine` only reads the state; bundled paths come from the directory of the plugin's jar.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/RobotCodePostStartupActivity.kt`: activation by index lookup and the filtered reaction to SDK and module changes.
- `lsp/RobotCodeLanguageServer.kt`: turns the run error of the builder into LSP4IJ's start error, as it does with today's exception.
- `lsp/RobotCodeLanguageServerFactory.kt`, `lsp/RobotCodeLanguageServerManager.kt`, `editor/EditorNotificationProvider.kt`, `editor/RobotCodeStatusBarWidgetFactory.kt`, `execution/RobotCodeRunProfileState.kt` and `testing/RobotCodeTestManager.kt`: read the state instead of running the check.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the messages of the new results.
- New unit tests under `intellij-client/src/test/kotlin/`; `CheckPythonAndRobotVersionTest` and the tests that use the old cache key change with the code they test.
- No change to the language server, the VS Code extension or the bundled `check_robot_version.py`, which VS Code keeps using.
