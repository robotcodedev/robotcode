# Design

## Context

See proposal.md for the motivation.

**Builds on landed changes** (all archived):
- The settings pages: the "Robot Framework" node with the id `dev.robotcode.robotcode4ij.projectsettings` and its sub-pages General, Editing, Robot, Analysis, Robocop and Language Server, registered as child configurables with that `parentId`; the shared state `RobotCodeProjectConfiguration` in `robotcodeSettings.xml`, which writes only values that differ from their defaults. The settings tree the language server receives holds no settings for the debugger or runs (intellij-settings, "Exceptions in the settings tree"), and the labels of the pages follow VS Code ("Labels of the settings pages follow VS Code").
- The run configuration: the options class `RobotCodeRunConfigurationOptions`, where `RobotRunMode.INHERIT` already stands for "the value of the settings page"; the "Robot Framework" group of "Modify options" (`RobotCodeOptionFragments.kt`); the argument assembly in the pure functions `runArguments` (the global options, `-dp` and `debug`) and `debugArguments` (`--no-debug`, `--tcp`, then `--` and the arguments for Robot Framework) in `RobotCodeRunProfileState.kt`. The values of the Robot page are combined with the configuration's at the start of every run and never copied into configurations.
- `intellij-async-run-and-debug`: `connectDebugger(handler, port, timeoutMillis)` connects in the run's background scope, for 15 seconds by default (`DEBUGGER_CONNECT_TIMEOUT_MILLIS`, the debugger's default `--wait-for-client-timeout`). When the time runs out while the process runs, it writes "The RobotCode debugger did not accept the connection within N seconds, so the run ends." to the console and ends the process. This change only sets how long the wait lasts.

**Current code and the debugger** (checked on 2026-10-14):

- Runs pass no debugger option besides `--no-debug` and `--tcp`.
- `RobotCodeDebugProtocolClient` parses `robotExited` into `reportFile`, `logFile`, `outputFile` and `exitCode` and fires `onRobotExited`, but nothing subscribes.
- `RobotCodeDebugProcess` handles every stop reason other than `breakpoint` and `exception` with `positionReached`, so the `entry` stop needs no new handling.
- For a folder suite, the debugger sends a frame without a source and with the hint `subtle` (`source_from_entry` in `debugger.py`), so a stop on entry at a top-level folder suite shows a grey frame without a source position.
- The output converter shows every DAP output event that is not `stderr` as test output of the current node, so the `messages` category is shown like log output.
- `robotcode debug` (`debugger/cli.py`): `--stop-on-entry` (pauses at the start of the top-level suite with reason `entry`, only in debug mode, `debugger.py`), `--wait-for-client-timeout` (default 15), `--output-messages` (default off; category `messages`), `--output-log` (default on), `--output-timestamps` (default off).
- `robotcode` (`cli/__init__.py`): `--wrapper` takes one string that `robotcode` splits with `shlex.split` (POSIX rules) and that overrides the profile's wrapper; `--no-wrapper` disables any wrapper.
- VS Code: the settings `robotcode.debug.launchWrapper` (`[]`), `outputMessages` (`false`), `outputLog` (`true`) and `outputTimestamps` (`false`) of its "Debug" category and `robotcode.run.openOutputAfterRun` (`none`) of its "Run" category are fallbacks for the launch attributes. The launcher (`debugger/launcher/server.py`) puts `-p`, `-dp`, `--wrapper` (an `shlex.join` of the array) and `robotCodeArgs` before `debug`, and `--no-debug`, `--tcp`, `--wait-for-client-timeout`, `--output-messages`, `--no-output-log`, `--output-timestamps`, `--stop-on-entry` and `debuggerArgs` after it. It turns a missing `outputLog` into `--no-output-log`. The launch attributes `launcherTimeout` and `debuggerTimeout` default to 10 seconds.
- `BrowserUtil.browse(Path)` is unannotated in 2026.1; `browse(File)` is `@ApiStatus.Obsolete`.

## Goals / Non-Goals

**Goals:**

- VS Code's run and debug settings as project defaults, with an override in every run configuration, resolved at the start of each run. Options that VS Code has only per launch configuration stay per run configuration.
- The same `robotcode` options as VS Code's launcher, except for the trap that turns a missing value into `--no-output-log`.

**Non-Goals:**

- A view of the report inside the IDE.
- `groupOutput`, console kinds, terminal emulation, and debugging Python code in the same run.
- Personal storage of these defaults.
- A separate tab for Robot Framework's log messages.

## Decisions

### Project defaults on a Run and a Debug page

The pages hold only what VS Code offers as settings, split and labelled like VS Code's settings categories, as the intellij-settings requirement "Labels of the settings pages follow VS Code" asks: the "Debug" page holds "Launch wrapper", "Output messages", "Output log" and "Output timestamps", the "Run" page holds "Open output after run". `robotcode` arguments for runs, stop on entry and the connection timeout are launch attributes in VS Code (`robotCodeArgs`, `stopOnEntry`, `debuggerTimeout`) and get no project default here either: stop on entry as a project default would pause every Debug start, and the others belong to a particular configuration.

Two child pages with the ids `dev.robotcode.robotcode4ij.projectsettings.run` and `dev.robotcode.robotcode4ij.projectsettings.debug`, built with the Kotlin UI DSL like the Editing page and with the Editing page's `nonDefaultProject` value, hold the defaults. The settings tree sorts the sub-pages by name, so their position follows from their names. Their values extend `RobotCodeProjectConfiguration`. Applying them restarts nothing, because the values are read at the start of each run, and the settings tree for the language server leaves them out like the other debugger and run settings.

Alternatives:
- One "Run & Debug" page: VS Code has no category of that name, and users who know VS Code look for its "Run" and "Debug" settings (user decision of 2026-10-14).
- The run configuration template as the only place for defaults: a template is copied when a configuration is created, so later changes would not reach existing configurations, unlike VS Code, where the settings apply at every launch.

### Explicit "Project default" states in the configuration

The options class gets, with `INHERIT` for "Project default" as in `RobotRunMode`:
- "Launch wrapper" as `INHERIT`, `PROFILE`, `CUSTOM` or `NONE`, plus the custom command;
- "Output messages", "Output log" and "Output timestamps" as `INHERIT`, `ON` or `OFF`;
- "Open output after run" as `INHERIT`, `NONE`, `REPORT` or `LOG`;
- without a project default: the `robotcode` arguments (empty: none), stop on entry (a boolean, off), the connection timeout (empty: the debugger's default of 15 seconds) and the extra debugger arguments.

New configurations start with every value that has a project default at "Project default". A pure function turns the configuration's values and the project defaults into the effective values at the start of each run. In the editor these options form a "Run & Debug" group of "Modify options", next to the "Robot Framework" group, with the labels of the pages.

### The command line

`runArguments` and `debugArguments` get the effective values:
- **Before `debug`**, after `-dp`, as in the launcher: `--wrapper <command>` or `--no-wrapper`, then the `robotcode` arguments.
- **After `debug`**, in the launcher's order: `--no-debug`, `--tcp`, `--wait-for-client-timeout` (only when the timeout differs from the debugger's default of 15 seconds), `--output-messages`, `--no-output-log` (only when the output log is explicitly off, since the command-line default is on), `--output-timestamps`, `--stop-on-entry` (only under Debug), and the extra debugger arguments; then `--` and the arguments for Robot Framework.

The wrapper command is split with `ParametersListUtil`, like the other command-line fields of the editor, and joined again with POSIX quoting, so that `robotcode`'s `shlex.split` gets back the same words on every operating system. This is what VS Code does with `shlex.join`.

Alternative: passing the typed text unchanged. `shlex.split` would then treat the backslashes of Windows paths as escape characters.

### One connection timeout for both sides

The configuration's connection timeout, or 15 seconds when it is empty, is the timeout of `connectDebugger` and is passed as `--wait-for-client-timeout`, so that the debugger does not give up before the plugin. The plugin connects as soon as the debugger listens, so one value covers a slow start, such as a wrapper or interpreter activation, on both sides. When the time runs out, `connectDebugger` reports it in the console as before, with the configured number of seconds.

Alternative: two values like VS Code's `launcherTimeout` and `debuggerTimeout`. `launcherTimeout` belongs to VS Code's launcher process, which the plugin does not use.

### Report and log open in the external browser

The run state subscribes to `onRobotExited` and keeps the reported paths. When the run ends and the effective value is "Report" or "Log", and the file exists, the plugin opens it with `BrowserUtil.browse(Path)`, VS Code's `externalFile` behaviour. "Open Report" and "Open Log" are added to the actions of the run tab and, through the debug process's additional actions, to the debug tab. They are enabled once the reported file exists.

Alternative: `HTMLEditorProvider.openEditor` for a view inside the IDE. It is public but lives in an implementation package and needs JCEF; VS Code's in-editor view relies on the language server's documentation server instead. It stays out of this change.

### The Robot Log tab

The "Robot Log" tab for Robot Framework's log messages is planned separately. If it needs an on/off default, that setting belongs on the Debug page, next to the output settings, and whichever of the two changes lands first owns the page entry. This change adds no such setting.

## Risks / Trade-offs

- [Two kinds of extra `robotcode` arguments: those of a run configuration, and those for the language server and helper processes on the settings pages] → The configuration field's comment says that its arguments reach only that configuration's runs.
- [Browser calls cannot be seen in the harness] → The harness points the IDE's browser setting to a script that records its arguments.

## Migration Plan

None. Existing projects and configurations have none of the new values, so runs keep VS Code's defaults, and nothing opens after a run.
