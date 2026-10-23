# Design

## Context

VS Code decides whether to open the Debug Console after the launch of a session, with `session.configuration.internalConsoleOptions || debug.internalConsoleOptions` (`debugService.ts`, VS Code 1.143.1). The setting's default `openOnFirstSessionStart` opens the Debug Console for the first session of a window. A value in the session's configuration takes precedence over the setting.

RobotCode resolves every `launch` configuration in `RobotCodeDebugConfigurationProvider._resolveDebugConfiguration` (`debugmanager.ts`):
- **Merge order:** it lays `robotcode.debug.defaultConfiguration`, then the `launch.json` configuration with `purpose` `default`, then the configuration itself over each other.
- **Test Explorer runs:** before that, they add the `launch.json` configuration with `purpose` `test`.
- **Console:** `console` falls back to `robotcode.debug.defaultConsole`.

So when RobotCode has resolved the console, every place where a user can set `internalConsoleOptions` for a run is already merged into the configuration.

## Goals / Non-Goals

**Goals:**
- One rule for all runs and debug sessions in a terminal, wherever they are started from.

**Non-Goals:**
- `attach` configurations. Their only output is the Debug Console.
- The Python debug session that `attachPython` starts as a child session. It is started from its own configuration and stays as it is.

## Decisions

### D1: RobotCode sets `internalConsoleOptions` in the resolved configuration

In the `launch` branch, RobotCode sets `internalConsoleOptions` to `neverOpen` when all of the following hold:
- the resolved `console` is not `internalConsole`;
- the configuration sets no `internalConsoleOptions`;
- the user has not set `debug.internalConsoleOptions` (D2).

`neverOpen` means that VS Code never opens the Debug Console by itself, which is the behavior the specs ask for.

**Alternatives considered:**
- **Show the terminal again once the session has started.** That races with VS Code's own opening of the Debug Console and lets the panel flicker. `internalConsoleOptions` is VS Code's own option for this.
- **A `configurationDefaults` value for `debug.internalConsoleOptions`.** That would change the default for every debugger, such as Python or Node.js, and not only for RobotCode's runs.
- **Ignore the setting, as the Python debugger does.** That would override a value that the user chose deliberately.

### D2: "Set by the user" means an explicit value in the settings

RobotCode reads `vscode.workspace.getConfiguration("debug", folder).inspect("internalConsoleOptions")`. The setting counts as set when it has a `globalValue`, a `workspaceValue` or a `workspaceFolderValue`. A value that equals VS Code's default counts too, because the user wrote it into the settings.

### D3: Checked in the isolated VS Code, before and after

The behavior is VS Code's panel, and the resolver has no unit tests. The check therefore runs in the isolated VS Code with default settings, each time as the first run after a reload of the window:
- With the change, a test run from the Test Explorer and a debug session stay in RobotCode's run terminal. With the change reverted once, the run switches to the Debug Console.
- With `"debug.internalConsoleOptions": "openOnFirstSessionStart"` in the user settings, the Debug Console opens.
- With a launch configuration with `"internalConsoleOptions": "openOnSessionStart"`, the Debug Console opens.
- With `robotcode.debug.defaultConsole` set to `internalConsole`, the Debug Console opens.

## Risks / Trade-offs

- [The Debug Console holds output that a user no longer sees right away, such as the log messages of `robotcode.debug.outputLog`.] → The run's own output is in the terminal, and the guide names <kbd>Ctrl+Shift+Y</kbd> for the Debug Console. When a launch fails, VS Code opens the Debug Console by itself if anything was written to it, independent of `internalConsoleOptions` (`debugService.ts`).
- [A user who liked the Debug Console opening at the first run loses that.] → Setting `debug.internalConsoleOptions` brings it back (D2), and the guide says so.

## Migration Plan

Nothing to migrate. A user who wants the old behavior sets `debug.internalConsoleOptions` or `internalConsoleOptions` in a launch configuration.
