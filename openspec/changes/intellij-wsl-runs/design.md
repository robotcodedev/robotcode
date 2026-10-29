# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach, checked on 2026-10-29 against the code on main, PyCharm's sources at the tags `pycharm/261.22158.340` (2026.1) and `pycharm/262.10968.92` (2026.2.3), and the debugger package:

**Builds on other changes.**
- Not implemented yet:
  - `intellij-wsl-language-server`, which this change needs first: the WSL interpreter kind in the environment state, with its probe and results; the pure Kotlin path mapper with the roots of the distribution and of the Windows drives; the refusal of runs for the WSL kind, which this change removes.
  - `intellij-debugger-attach-python`, which only the Python debugging of WSL runs needs: with "Attach Python", Debug starts the run through `RobotCodePythonDebugRunner`, a subclass of PyCharm's `PyDebugRunner`; the Robot Framework session keeps the run's handler and test tree, and the Python session runs on the stand-in handler `RobotCodePythonSessionHandler` with PyCharm's Python debug console. It covers local interpreters only.
- Implemented and archived since this design was first written on 2026-10-03: `intellij-run-configuration-target`, `intellij-debugger-breakpoints`, `intellij-test-result-events`, `intellij-async-run-and-debug`, `intellij-run-stop` and `intellij-python-interpreter`. The plugin code below is their result.

**Plugin code on main:**
- `RobotCodeRunConfiguration` extends PyCharm's Python run configuration base, and `RobotCodeRunProfileState` extends `PythonCommandLineState`. `buildPythonExecution(request)` refuses an interpreter for which `interpreterRefusal(pythonInterpreterOf(sdk))` gives a reason, today every remote interpreter (`PythonSdkUtil.isRemote`), picks the run's debugger port with `freeDebugPort()`, an OS-assigned port, and returns a `PythonScriptExecution` of the bundled robotcode's local path (`RobotCodeHelpers.robotCodePath`, below the plugin's `data/bundled` folder, which holds `tool` and `libs`) with `-u -X utf8` and `--no-pager -dp . debug [--no-debug] --tcp <port> … [-- <robot arguments>]`. A "Files and folders" target puts its paths after `--`. `createProcessHandler(Process, String, TargetEnvironment, TargetedCommandLine)` returns `RobotCodeProcessHandler`. Both runners call `state.execute(executor)` on a background thread.
- `RobotCodeRunConfiguration.checkConfiguration` reports the same `interpreterRefusal` as an error in the editor, besides the result of the environment check.
- The handshake runs in the run's coroutine scope once the handler has started: `connectDebugger` connects to `127.0.0.1:<port>` within the run's connection timeout and ends a run that does not connect with a console message; `handshake` sends `initialize`, the configuration requests after `initialized`, `attach` with an empty map, and `configurationDone`. Stop goes through `RobotCodeStopPolicy`: `terminate`, and the inherited destroy when the debugger does not confirm within five seconds.
- The converter builds the location hint as `robotcode:///` plus `Urls.newLocalFileUrl(source)` plus `?line=` (`RobotOutputToGeneralTestEventsConverter.kt`); the run markers build the same URL from the discovered item's `source`, which the WSL language server change maps to the IDE path; `RobotSMTestLocator` resolves the URL's path with `LocalFileSystem`.
- Breakpoints send `file.toNioPath().toString()` as `source.path` (`RobotCodeDebugProcess.kt`); frames open `frame.source.path` with `VfsUtil.findFile` (`RobotCodeStackFrame.kt`).
- The protocol client receives `robotEnqueued`, `robotStarted`, `robotEnded`, `robotSetFailed`, `robotLog`, `robotMessage` and `robotExited` and fires one signal per event (`RobotCodeDebugProtocolClient.kt`). Their path fields carry debuggee paths: `attributes.source` and the `source` of each failed keyword in the execution events, the `source` of log messages, and the output, log and report files of `robotExited`. `robotEnqueued` and the event ids carry ids only.

**The debugger:**
- `robotcode debug --tcp <port>` listens on `127.0.0.1` unless `--bind` is given (`run.py`, `_debug_adapter_server_async`).
- `attach` accepts `pathMappings`, a list of `localRoot`/`remoteRoot` pairs (`server.py`). `map_path_to_client` maps a debuggee path with the first pair whose `remoteRoot` contains it, not the longest, and builds a Windows path when `localRoot` looks like one (`debugger.py`). It is applied to the sources of executing keywords before they are compared with the breakpoints, which the debugger keeps under the client's paths (a `PureWindowsPath`, case-insensitive, for a UNC or drive path), to stack frames and to the sources of output events.
- Robot events are not mapped: their ids (`<path>;<longname>[;<line>]`) and sources are debuggee paths (`listeners.py`).

**PyCharm:**
- `PythonCommandLineState.getTargetPath(TargetEnvironmentRequest, Path)` (protected, unannotated) resolves a local path through the SDK's path mappings, or else through the request's upload roots with `TargetEnvironmentFunctions.targetPath` (`@ApiStatus.Experimental`).
- `TargetEnvironmentRequest`, `TargetEnvironment`, `PythonExecution` and `PythonScriptExecution` are `@ApiStatus.Experimental`; `TargetEnvironment.UploadRoot`, `TargetPath.Temporary`, `TargetPortBinding` and `LocalPortBinding` are data classes nested in `TargetEnvironment` without annotations of their own.
- `LocalTargetEnvironment` resolves every target and local port binding to `127.0.0.1:<port>`.
- In 2026.1 the WSL target environment hands uploads and port bindings to the IDE's WSL agent (an internal Eel environment), and its request does not copy volumes unless asked to. This was read from 2026.1's classes on 2026-10-03; the WSL target's sources are not at the tags' paths.
- For a non-local target, `PythonCommandLineState.createProcessHandler` gives PyCharm's own Python runs a handler that maps paths with a `PyTargetPathMapper` built from the target environment and the SDK's path mappings; that handler class, `ProcessHandlerWithPyPositionConverter`, is `internal`.
- Python debugging: `PyDebugRunner`'s client mode registers a `TargetEnvironment.LocalPortBinding` for the IDE's debug server socket on the target request; once the environment is prepared, it rebinds that socket to the address the target resolved for the binding and passes pydevd the host and port as the target sees them (`--client <host> --port <port>`). `PyDebugProcess` maps paths with the converter of its process handler when that handler implements the public `PositionConverterProvider`, and otherwise with `PyLocalPositionConverter`, which maps nothing. `PyRemotePositionConverter(PyDebugProcess, PathMappingSettings)` is public.

## Goals / Non-Goals

**Goals:**

- WSL runs on the run-configuration base, through PyCharm's target API instead of a second process launcher.
- One path table for the language server, the debugger's path mappings, the Python debugger's path mapping and the plugin's own event locations.
- Local runs keep their command line, connection address, handler and events exactly.

**Non-Goals:**

- Docker, SSH and other targets.
- A robotcode installed in the WSL environment.
- Path mappings that users configure on the interpreter, beyond the automatic WSL mapping.
- Attaching to a debugger started outside the IDE.

## Decisions

### WSL interpreters pass the run gate

`interpreterRefusal` refuses only remote interpreters that are not of the WSL kind. `buildPythonExecution` and `checkConfiguration` both use it, so a WSL interpreter is neither refused at the start of a run nor flagged in the editor. It goes through the environment state as every interpreter does: a usable result starts the run, any other result fails it with its message, and problems of a WSL interpreter, such as a distribution that is not installed, come from that result. The WSL language server change adds the WSL kind and refuses runs for it; that refusal goes away here.

### The bundled robotcode as an upload root

`buildPythonExecution` adds the bundled folder (`data/bundled`, which holds `tool` and `libs`, whose relative layout the entry script relies on) as an upload root with a temporary target path to the target request, and resolves the script path below it with `getTargetPath`. For the local target the upload root is the local folder itself, so local runs keep today's path. For WSL, the request does not copy volumes unless asked to, so the folder is expected to be reached through the distribution's mount of the Windows drives, as the language server reaches it; this is an assumption from 2026.1's classes, and task 3.3 records the resolved path.

Alternatives:
- `PythonModuleExecution` of `robotcode.cli`: needs robotcode installed in the distribution, in a version that may differ from the plugin's.
- Computing `/mnt/c/…` with the plugin's own mapper: bypasses the target's own mapping and would be wrong for a target that copies uploads.

### Paths on the command line through the target

Every argument that is a local path, the paths of a "Files and folders" target and any other option that takes a path, is passed as a target value resolved with `getTargetPath`, so the path inside the distribution reaches robotcode. The working directory already comes from the base class. Arguments that are not paths, such as test names, stay as they are.

### The debugger port as a target port binding

The run's port, the OS-assigned one that `freeDebugPort()` picks, becomes the target side of a `TargetPortBinding` that `buildPythonExecution` registers on the request. `createProcessHandler` reads the binding's resolved local endpoint from the `TargetEnvironment` and keeps host and port for the handshake, and `connectDebugger` connects to that host instead of `127.0.0.1`. For the local target the endpoint is `127.0.0.1:<port>`, the address runs use today. Inside the distribution the debugger keeps listening on `127.0.0.1`; PyCharm's forwarding reaches it there, in NAT and in mirrored networking mode.

Alternatives:
- `--bind 0.0.0.0` and a connection to the distribution's IP address: the port is then open beyond the loopback, it works only in NAT mode, and Windows may ask for a firewall rule.
- The debugger connects to the IDE: a connect-back mode that the debugger does not have.

### Path mappings for the debugger

For a WSL run, `attach` carries `pathMappings` built from the WSL language server change's path table: one pair per root, `localRoot` in the IDE's Windows form (for example `\\wsl.localhost\Ubuntu\` or `C:\`) and `remoteRoot` the distribution's path (`/`, `/mnt/c/`). The pairs are ordered by descending length of `remoteRoot`, because the debugger takes the first pair that contains a path, and `/` contains every path. The debugger then compares executing sources with the breakpoints' IDE paths, and maps frames and output sources to IDE paths. Local runs send no mappings, as today. `attach` precedes `configurationDone` in the handshake, so the mappings are in place before the first keyword runs. The planned attach configuration (`intellij-robot-remote-attach`) sends `attach` with path mappings as well; whichever of the two changes lands first gives the handshake a path-mappings parameter, and the other passes its own list.

### Robot event paths translated in the protocol client

For a WSL run, the state gives the protocol client the mapper's distribution-to-IDE direction, and the client translates the path fields of every Robot event before it fires the signal: `attributes.source` and the sources of failed keywords, the sources of log messages, and the output, log and report files of `robotExited`. The converter, and every later consumer such as failure links, the log tab or opening the report, then see IDE paths, and the location URLs match those of the run markers, which use the mapped discovery sources. Ids, also those of `robotEnqueued`, are not translated: the results tree compares them only with ids of the same run.

Navigation from the results tree goes through `RobotSMTestLocator`, which parses the location URL back into a path and a line and looks the path up with `LocalFileSystem`. So far it has only seen drive and POSIX paths; a UNC path such as `//wsl.localhost/Ubuntu/…` must keep its leading double slash through `newLocalFileUrl` and the parsing. The parsing becomes a pure function with tests for UNC, drive and POSIX paths, and is fixed if it loses the double slash.

Alternatives:
- Translating in each consumer: every consumer has to remember it.
- Letting the debugger translate its events with `pathMappings`: it changes the event fields for every client, and VS Code matches event ids against discovery ids built from debuggee paths.

### One process handler for local and WSL runs

`createProcessHandler` keeps returning the plugin's handler, also for the WSL target's process, so Stop goes through the debugger's `terminate` there as well and the output files are written. Its fallback destroys the target process; that the WSL agent then ends the process inside the distribution is an assumption that task 3.3 checks.

Alternative: PyCharm's own handler for target processes. Stop would then send no `terminate`, and a paused run would not end gracefully.

### Python debugging of WSL runs

With "Attach Python" (`intellij-debugger-attach-python`), a WSL run goes through `RobotCodePythonDebugRunner` as a local run does. Two things differ:

- **The connection back to the IDE:** pydevd in the distribution connects to the IDE's debug server socket through the local port binding that `PyDebugRunner` registers on the target request, the way PyCharm debugs its own Python runs on WSL. The plugin adds nothing for it. The Robot Framework connection keeps the target port binding of the decision above, in the other direction.
- **Paths:** for a WSL run, `RobotCodePythonSessionHandler` implements `PositionConverterProvider` and returns a `PyRemotePositionConverter` with `PathMappingSettings` built from the path table of the WSL language server change: one pair per root, the local root in the IDE's Windows form and the remote root the distribution's path, the longest remote root first, as for the robot debugger's `pathMappings`. Python breakpoints set on the IDE's files then reach pydevd with the distribution's paths, and Python frames open the IDE's files, for a project inside the distribution and for one on a Windows drive. For a local run the handler provides no converter, so `PyDebugProcess` keeps its local one.

Alternative: PyCharm's own handler for target processes, which brings a converter built from the target environment. It is `internal`, and the run keeps the plugin's handler for the graceful Stop (see "One process handler for local and WSL runs").

## Risks / Trade-offs

- [Experimental API: `TargetEnvironmentRequest` for upload roots and port bindings, `TargetEnvironment` for the resolved binding, `TargetEnvironmentFunctions.targetPath` behind `getTargetPath`, `PythonScriptExecution`] → Confined to `buildPythonExecution` and `createProcessHandler`, as on the run-configuration base; `verifyPlugin` reports changes on 261 and the newer configured versions.
- [The target port is chosen before the environment exists, without knowing whether it is free inside the distribution] → A taken port makes the debugger fail to listen, and the run ends with the "did not connect" message; ephemeral ports collide rarely.
- [Port forwarding and uploads run through the IDE's internal WSL agent] → Only public target API is used; the Windows check covers NAT and mirrored mode.
- [A fallback kill in `wsl.exe` mode may leave the robot process inside the distribution] → It runs only after a graceful stop failed; the Windows check looks for leftover processes after Stop and after Kill.
- [Translating the path fields of events misses a field that a later consumer reads] → All path fields are translated in one place, with a unit test per field.
- [pydevd's connection from the distribution to the IDE, Windows' firewall and WSL's mirrored networking mode are PyCharm's behavior] → The Windows check covers "Attach Python" in NAT and mirrored mode and notes any firewall prompt.
- [The Python session maps only the WSL roots of the path table] → Path mappings that users configure on the interpreter stay out of scope, as for the robot debugger.
- [The modified block of "Runs with remote interpreters" drifts from the main spec] → Copy it again if the main spec changes before this change is archived.

## Migration Plan

None. Stored configurations keep their values; a configuration with a WSL interpreter starts to run instead of failing.
