# Proposal

## Why

Robot Framework runs in PyCharm and IntelliJ IDEA cannot be shaped the way VS Code users shape theirs:

- There is no launch wrapper. VS Code's `robotcode.debug.launchWrapper` runs tests through a command such as `xvfb-run -a`, for example for headless browser tests; in PyCharm only a wrapper in a `robot.toml` profile works.
- There is no way to pass `robotcode` options to a run, such as `--no-wrapper` (VS Code: `robotCodeArgs`).
- What the debugger sends cannot be changed: Robot Framework's messages, log messages and timestamps (VS Code: `robotcode.debug.outputMessages`, `outputLog`, `outputTimestamps`). Debug cannot stop on entry.
- The plugin waits a fixed 15 seconds for the debugger connection. A wrapper or an interpreter that starts more slowly makes the run end with the message that the debugger did not accept the connection.
- Report and log are never opened after a run (VS Code: `robotcode.run.openOutputAfterRun`), and the run tab offers no way to open them.

## What Changes

- Two pages below Settings | Languages & Frameworks | Robot Framework hold the project defaults that VS Code also has as settings, split and labelled like VS Code's "Debug" and "Run" settings:
  - "Debug": "Launch wrapper", a command line, where empty means that the wrapper of the `robot.toml` profile applies; and the debugger output "Output messages" (off), "Output log" (on) and "Output timestamps" (off), as in VS Code;
  - "Run": "Open output after run": nothing, the report or the log (nothing).
- Every Robot Framework run configuration can override each of these values behind "Modify options", in a "Run & Debug" group, with the same labels. Values a configuration does not override follow the project default at the start of each run, so existing configurations pick up a changed default. For the wrapper, a configuration chooses the project default, the profile's wrapper, a custom command or no wrapper at all.
- The same group holds the options that VS Code has only per launch configuration, without a project default: `robotcode` arguments for the run, stop on entry for Debug (off), the connection timeout (empty means the debugger's default of 15 seconds) and extra debugger arguments.
- Runs pass the values as `robotcode` options: `--wrapper` or `--no-wrapper` and the `robotcode` arguments before `debug`; after `debug` the debugger options `--output-messages`, `--no-output-log` (only when the output log is switched off), `--output-timestamps`, `--stop-on-entry` (only for Debug), `--wait-for-client-timeout`, and extra debugger arguments.
- The plugin waits for the debugger connection as long as the connection timeout allows.
- After a run, the report or the log opens in the browser when the configuration or the default says so. The run tab gets "Open Report" and "Open Log", enabled once Robot Framework has written the files.

Behaviour that users notice, for the release notes (not breaking): nothing opens after a run unless the new setting asks for it, as in VS Code. The wait for the debugger connection can be set per run configuration; without a value it stays 15 seconds.

Not part of this change: viewing the report inside the IDE; grouping the output; debugging Python code in the same run; console kinds and terminal emulation; extra arguments for the language server and the helper processes; a separate tab for Robot Framework's log messages.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-settings`: the Run and Debug pages with the project defaults for the wrapper, the debugger output and what opens after a run.
- `intellij-run-configurations`: the Run & Debug options of a run configuration, how values set to "Project default" follow the pages, and the `robotcode` options runs get from them.
- `intellij-test-results`: opening the report or the log after a run, and the Open Report and Open Log actions of the run tab.
- `intellij-debugging`: stop on entry, the debugger output options, and the run configuration's connection timeout for the wait for the debugger.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/configuration/`: the Run and Debug pages and new values in `RobotCodeProjectConfiguration`.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/`: new properties in the run configuration's options class, a "Run & Debug" fragment group, the resolution against the project defaults, the argument assembly, the connection timeout, opening report or log, and the run tab actions.
- `intellij-client/src/main/resources/META-INF/plugin.xml`: the Run and Debug pages as child configurables.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the texts.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the debugger, discovery or `robot.toml`.
