# Design

## Context

See proposal.md for the motivation.

**Builds on planned changes.** None of the three changes this one builds on is implemented yet:
- `intellij-settings-pages` (planned, artifacts exist): the "Robot Framework" node with the id `dev.robotcode.robotcode4ij.projectsettings`, child pages registered with that `parentId`, and the shared state `RobotCodeProjectConfiguration` in `robotcodeSettings.xml`. Its settings mapper leaves client-only settings, including `debug` and `run`, out of the tree the language server receives.
- `intellij-run-configuration-target` (planned, artifacts exist): the options class of the run configuration, the fragmented editor, the run state on `PythonCommandLineState` whose argument assembly is one pure function, and runners that start the run off the UI thread.
- `intellij-async-run-and-debug` (not planned yet; its section B.9 of the parity notes and the planning brief): the DAP handshake moves into a background coroutine bound to the process, a failed connection prints a console message and ends the process, every DAP call has a timeout, and the connect wait follows the debuggee's default `--wait-for-client-timeout`. This change only sets how long that wait lasts.

**Current code and the debugger** (checked on 2026-10-03):

- The run passes no debugger option: `RobotCodeRunProfileState` connects with a fixed wait of 10 seconds (`tryConnectToServerWithTimeout(..., 10000, 100)`).
- `RobotCodeDebugProtocolClient` parses `robotExited` into `reportFile`, `logFile`, `outputFile` and `exitCode` and fires `onRobotExited`, but nothing subscribes.
- `RobotCodeDebugProcess` handles every stop reason other than `breakpoint` and `exception` with `positionReached`, so the `entry` stop needs no new handling.
- The output converter shows every DAP output event that is not `stderr` as test output of the current node, so the `messages` category is shown like log output.
- `robotcode debug` (`debugger/cli.py`): `--stop-on-entry` (pauses at the start of the top-level suite with reason `entry`, only in debug mode, `debugger.py`), `--wait-for-client-timeout` (default 15), `--output-messages` (default off; category `messages`), `--output-log` (default on), `--output-timestamps` (default off).
- `robotcode` (`cli/__init__.py`): `--wrapper` takes one string that `robotcode` splits with `shlex.split` (POSIX rules) and that overrides the profile's wrapper; `--no-wrapper` disables any wrapper.
- VS Code: the settings `robotcode.debug.launchWrapper` (`[]`), `outputMessages` (`false`), `outputLog` (`true`), `outputTimestamps` (`false`) and `robotcode.run.openOutputAfterRun` (`none`) are fallbacks for the launch attributes. The launcher puts `-p`, `-dp`, `--wrapper` (an `shlex.join` of the array) and `robotCodeArgs` before `debug`, and `--no-debug`, `--tcp`, `--wait-for-client-timeout`, `--output-messages`, `--no-output-log`, `--output-timestamps`, `--stop-on-entry` and `debuggerArgs` after it. It turns a missing `outputLog` into `--no-output-log`.
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

### Project defaults on a Run & Debug page

The page holds only what VS Code offers as settings: the launch wrapper, the three debugger output switches and what to open after a run. `robotcode` arguments for runs, stop on entry and the connection timeout are launch attributes in VS Code (`robotCodeArgs`, `stopOnEntry`, `debuggerTimeout`) and get no project default here either: stop on entry as a project default would pause every Debug start, and the others belong to a particular configuration.

A child page with the id `dev.robotcode.robotcode4ij.projectsettings.runAndDebug`, built with the Kotlin UI DSL like the Editing page and with the Editing page's `nonDefaultProject` value, holds the defaults. Its values extend `RobotCodeProjectConfiguration`, which writes only values that differ from their defaults. Applying the page restarts nothing, because the values are read at the start of each run. The settings mapper keeps them out of the language server's tree.

Alternative: the run configuration template as the only place for defaults. A template is copied when a configuration is created, so later changes would not reach existing configurations, unlike VS Code, where the settings apply at every launch.

### Explicit "Project default" states in the configuration

The options class gets:
- the wrapper as `INHERIT`, `PROFILE`, `CUSTOM` or `NONE`, plus the custom command;
- messages, log messages and timestamps as `INHERIT`, `ON` or `OFF`;
- what to open after a run as `INHERIT`, `NONE`, `REPORT` or `LOG`;
- without a project default: the `robotcode` arguments (empty: none), stop on entry (a boolean, off), the connection timeout (empty: the debugger's default of 15 seconds) and the extra debugger arguments.

New configurations start with every value that has a project default at "Project default". A pure function turns the configuration's values and the project defaults into the effective values at the start of each run.

### The command line

The run state's argument assembly gets the effective values:
- **Before `debug`**, after `-dp`, as in the launcher: `--wrapper <command>` or `--no-wrapper`, then the `robotcode` arguments.
- **After `debug`**, in the launcher's order: `--no-debug`, `--tcp`, `--wait-for-client-timeout` (only when the timeout differs from the debugger's default of 15 seconds), `--output-messages`, `--no-output-log` (only when log messages are explicitly off, since the command-line default is on), `--output-timestamps`, `--stop-on-entry` (only under Debug), and the extra debugger arguments; then `--` and the arguments for Robot Framework.

The wrapper command is split with `ParametersListUtil`, like the other command-line fields of the editor, and joined again with POSIX quoting, so that `robotcode`'s `shlex.split` gets back the same words on every operating system. This is what VS Code does with `shlex.join`.

Alternative: passing the typed text unchanged. `shlex.split` would then treat the backslashes of Windows paths as escape characters.

### One connection timeout for both sides

The configuration's connection timeout, or 15 seconds when it is empty, sets how long the plugin's connect loop waits for the debugger, in the background handshake of the async change, and is passed as `--wait-for-client-timeout`, so that the debugger does not give up before the plugin. The default of 15 seconds is the debugger's own default. The plugin connects as soon as the debugger listens, so one value covers a slow start, such as a wrapper or interpreter activation, on both sides.

Alternative: two values like VS Code's `launcherTimeout` and `debuggerTimeout`. `launcherTimeout` belongs to VS Code's launcher process, which the plugin does not use.

### Report and log open in the external browser

The run state subscribes to `onRobotExited` and keeps the reported paths. When the run ends and the effective value is "Report" or "Log", and the file exists, the plugin opens it with `BrowserUtil.browse(Path)`, VS Code's `externalFile` behaviour. "Open Report" and "Open Log" are added to the actions of the run tab and, through the debug process's additional actions, to the debug tab. They are enabled once the reported file exists.

Alternative: `HTMLEditorProvider.openEditor` for a view inside the IDE. It is public but lives in an implementation package and needs JCEF; VS Code's in-editor view relies on the language server's documentation server instead. It stays out of this change.

### The Robot Log tab

The "Robot Log" tab for Robot Framework's log messages is planned separately. If it needs an on/off default, that setting belongs on this page, next to the debugger output options, and whichever of the two changes lands first owns the page entry. This change adds no such setting.

## Risks / Trade-offs

- [The connect wait lives in the handshake that the async change moves] → This change depends on it. If it is implemented first anyway, the timeout replaces the fixed 10 seconds in today's connect loop, which still runs on the UI thread, so a raised timeout lengthens a freeze when the debugger never connects.
- [Stop on entry at a top-level folder suite] → The first frame then names a folder. The harness checks that pausing there shows the frame without an error; if the frame tries to open the folder in an editor, the frame gets no source position for folders.
- [Two kinds of extra `robotcode` arguments: those of a run configuration, and those for the language server and helper processes on the settings pages] → The configuration field's comment says that its arguments reach only that configuration's runs.
- [Browser calls cannot be seen in the harness] → The harness points the IDE's browser setting to a script that records its arguments.

## Migration Plan

None. Existing projects and configurations have none of the new values, so runs keep VS Code's defaults, and nothing opens after a run.
