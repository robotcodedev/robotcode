# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- **Configuration type and runners:** `RobotCodeConfigurationType` has one factory, id `ROBOT_FRAMEWORK_TEST`. `RobotCodeRunConfigurationProducer.getConfigurationFactory()` returns `configurationFactories.first()`. The Run runner accepts only `RobotCodeRunConfiguration` with the Run executor, the Debug runner only `RobotCodeRunConfiguration` with the Debug executor.
- **Sessions:** `RobotCodeDebugProcess` takes the launch state, `RobotCodeRunProfileState`, and reads the DAP client and server from it. The launch state always starts a local process and connects to `127.0.0.1`; it sends `attach` with an empty map.
- **The debugger side** (`packages/debugger/src/robotcode/debugger/`):
  - `attach` stores `pathMappings` (`localRoot`, `remoteRoot`) and marks the debugger as attached (`server.py`);
  - the debugger maps the paths of its frames, of the sources of its output and of the breakpoint lookup to the client side, so the client sends local paths and receives local paths (`Debugger.map_path_to_client`); a relative `remoteRoot` is resolved against the debugger's working directory;
  - `disconnect` without `terminateDebuggee` detaches and resumes a paused run; `terminate` raises SIGINT inside the run and resumes it, which ends it gracefully;
  - the debugger refuses a second client while one is connected, and by default waits 15 s for a client before the run starts (`--wait-for-client-timeout`); it listens on `127.0.0.1` unless an address is given, for example `--tcp 0.0.0.0:6612`.
- **VS Code** connects to `connect.host`/`connect.port` (default `127.0.0.1:6612`) for a launch configuration with `request: attach` and sends its `pathMappings` in the `attach` request; Stop sends `disconnect`, and the run continues (`vscode-client/extension/debugmanager.ts`, `package.json`).
- **Planned, not implemented yet:**
  - `intellij-run-configuration-target` moves the launch configuration onto PyCharm's `AbstractPythonRunConfiguration` (decision D1) and keeps the type id and the factory id `ROBOT_FRAMEWORK_TEST`. Its design records that PyCharm's `PythonRunner` accepts every `AbstractPythonRunConfiguration` for Run, that `PyDebugRunner` and PyCharm Professional's profile and concurrency runners accept them for their executors, that `checkConfiguration()` requires a valid interpreter, and that hiding PyCharm's editor fragments goes through `@Internal` API.
  - `intellij-async-run-and-debug` runs the DAP handshake in a coroutine scope bound to the process handler; `intellij-debugger-breakpoints` orders it: `initialize`, `initialized`, configuration requests, `attach`, `configurationDone`.
  - `intellij-run-stop` adds the stop policy that sends `terminate` and falls back when the debugger does not confirm.
  - `debugger-dap-e2e-tests` makes a detached run stop waiting for acknowledgements of its synced events; without that fix, every such event of a detached run waits 15 s.

## Goals / Non-Goals

**Goals:**

- One debug process for launched and attached runs, so breakpoints, frames, variables and evaluation behave the same.
- An attach configuration that shows only fields that take effect.

**Non-Goals:**

- Feeding the test results tree from an attached run; its result ids and sources are the run's own paths, which the debugger does not map.
- Starting or uploading anything on the other side.
- Python debugging of keyword code.

## Decisions

### The attach configuration does not share the run configuration base

The attach configuration extends the platform's `RunConfigurationBase` with its own options class, returned by its factory's `getOptionsClass()`: host, port and a list of path mappings with a local and a remote folder each. It does not extend the Python run configuration base that the launch configuration gets with D1:

- It starts no process. The interpreter, interpreter options, working directory, environment variables, `.env` files and `PYTHONPATH` options that the Python base brings, with their editor fragments, would take no effect, and the base's interpreter check would flag an attach configuration in a project whose run lives in a container and has no local interpreter at all.
- PyCharm's Python runners accept every Python run configuration for Run, profiling and concurrency diagrams, while the attach configuration must be startable with Debug only. With the platform base, no runner but RobotCode's Debug runner accepts it.
- The target support that motivated D1 decides where the IDE starts a process. The attach configuration starts none, and its path mappings are explicit and applied by the debugger.
- It keeps a configuration that needs nothing from PythonCore independent of PythonCore classes, which change with every release.

Alternative: share the Python base and hide its fragments. The interpreter check and the claims of PyCharm's runners would still apply, and hiding PyCharm's fragments needs `@Internal` API.

### A second factory under the Robot Framework type

The attach configuration comes from a second factory of `RobotCodeConfigurationType`, id `ROBOT_FRAMEWORK_ATTACH`, named "Robot Framework (Attach)". Both kinds stay together under "Robot Framework" in the Run/Debug Configurations dialog, as VS Code keeps launch and attach under one debug type. The producer selects the launch factory by its id instead of taking the first factory, so gutter and context runs keep creating run configurations. The Debug runner accepts the attach configuration; the Run runner does not, so the IDE offers no Run for it.

Alternative: an own configuration type, as PyCharm's "Attach to DAP". It works as well but splits the Robot Framework configurations in the dialog.

### The debug process works on a DAP session, not on the launch state

`RobotCodeDebugProcess` depends on a small session interface instead of the launch state: the DAP client, the server proxy once connected, the hook for the configuration requests, and the run's coroutine scope. The launch state and the new attach state both provide it. For launched runs nothing changes.

### An attach state with a process handler that has no process

The attach state starts nothing. Its execution result holds a plain console view, which prints the debugger's `output` events, and a `ProcessHandler` subclass without a process:

- `startNotify` starts the background handshake: connect to host and port, retrying for up to 15 s; `initialize`; `initialized`; the configuration requests; `attach` with the path mappings; `configurationDone`. If no connection is made, or the debugger closes it, for example because another client is attached, the console says so and the handler terminates.
- `detachIsDefault()` is `true`, so Stop detaches. `detachProcessImpl()` sends `disconnect` without `terminateDebuggee`, waits for the answer with a bound, closes the connection and only then reports the detach, so `XDebugProcess.stop()`, which sends `terminate` only while a connection is up, cannot end the run afterwards.
- `destroyProcessImpl()` hands the stop to the stop policy of `intellij-run-stop`: it sends `terminate`; its fallback, without an OS process to signal, closes the connection and terminates the handler.
- The `terminated` and `exited` events, and a lost connection, terminate the handler, with the exit code from `exited` when there is one.

The paths need no mapping in the plugin: breakpoints go out with local paths, and the debugger reports frames and output sources with local paths once it has the mappings.

### Terminating through an action of the session

Because Stop detaches, the debug process registers a "Terminate Run" action in the session's toolbar for attach sessions, through `XDebugProcess.registerAdditionalActions`. It calls `destroyProcess()` on the handler. Closing the session's tab while it is attached also offers Terminate, in the platform's confirmation dialog for running processes.

Alternative: make Stop terminate and offer detaching only when the tab is closed. VS Code's Stop detaches attached sessions, and detaching is the safe default for a run someone else started.

### The editor

A small editor built with the Kotlin UI DSL: a host field, a port field, the platform's `PathMappingsComponent` (public and unannotated in 2026.1) and a comment on how to start a run to attach to: `robotcode debug --tcp <address>:<port> …`, which waits 15 s for the debugger unless started with `--no-wait-for-client`. `checkConfiguration()` reports a blank host, a port outside 1 to 65535 and a mapping with an empty folder.

## Risks / Trade-offs

- [Detaching without the debugger fix makes the run wait 15 s for every synced event] → `debugger-dap-e2e-tests` is a precondition; task 1.1 checks it before anything else.
- [Anyone who can reach the debugger's port can attach] → This is how `robotcode debug` works with every client; the editor comment uses an explicit address, and the default host is the local machine.
- [Another client is already attached] → The debugger closes the second connection, and the session ends with a message instead of hanging.
- [The session interface changes code that launched runs use] → Launched runs keep their behaviour; the harness checks a launched Debug session as well.

## Migration Plan

None. The new factory adds a configuration kind; stored run configurations are unchanged.
