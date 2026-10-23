# Proposal

## Why

When a run writes its output to a terminal, VS Code switches the panel to the Debug Console at the first run of each window, and the terminal with the run's output disappears behind it. The cause is VS Code's own setting `debug.internalConsoleOptions`, whose default `openOnFirstSessionStart` opens the Debug Console once the launch has finished, after RobotCode has shown the terminal (`debugService.ts` of VS Code 1.143.1).

Seen in the isolated VS Code 1.142 with default settings, running a test file from the editor:
- The first run shows the Test Results, then the run terminal, and about a second later the Debug Console.
- The second and third run, and a debug run, stay in the terminal.
- After a reload of the window, the first run switches to the Debug Console again.

The Python debugger avoids this. For a run in a terminal, it sets `internalConsoleOptions` of the launch configuration to `neverOpen` when the configuration does not set it (`launch.ts` of `vscode-python-debugger`). A launch configuration with `"internalConsoleOptions": "neverOpen"` kept the first run of a reloaded window in RobotCode's run terminal; without it, the panel switched to the Debug Console.

## What Changes

- **Terminal consoles:** For a run whose console is a terminal (`robotcodeTerminal`, `integratedTerminal` or `externalTerminal`), VS Code no longer opens the Debug Console by itself, and the terminal stays in front. This holds for runs and debug sessions started from the Test Explorer, from the editor and from `launch.json`.
- **Launch configuration:** `internalConsoleOptions` in a launch configuration still decides. This includes a configuration with `purpose` `test` or `default`, and `robotcode.debug.defaultConfiguration`.
- **User setting:** Unlike the Python debugger, RobotCode respects a value of `debug.internalConsoleOptions` that the user has set in user, workspace or folder settings. Only VS Code's default is replaced.
- **Internal console:** With `internalConsole` nothing changes: the Debug Console is where the run writes its output.
- **Guide:** The VS Code guide says this in "The output of a run".

## Capabilities

### New Capabilities

### Modified Capabilities
- `vscode-run-terminal`: the Debug Console stays closed for a run in a terminal.
- `vscode-user-guide`: the page Running and debugging says that the Debug Console does not open by itself for a run in a terminal.

## Impact

- **Code:** `vscode-client/extension/debugmanager.ts`, the `launch` branch of `RobotCodeDebugConfigurationProvider._resolveDebugConfiguration`.
- **Docs:** `docs/src/content/docs/guides/vscode/running-and-debugging.mdx`.
- **Not touched:**
  - `attach` configurations;
  - the Python debug session that `attachPython` starts;
  - RobotCode's settings and its launch configuration schema. VS Code already offers `internalConsoleOptions` in the launch configurations of every debugger.
