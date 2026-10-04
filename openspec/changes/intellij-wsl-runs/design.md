# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach, checked on 2026-10-03 against the code on main, PyCharm 2026.1 (PY-261.22158.340, javap and decompiled classes from the Gradle cache) and the debugger package:

**Builds on planned changes.** None of them is implemented yet; this design relies on their planned designs. It needs the first three; the others only change details where they have landed first:
- `intellij-run-configuration-target`: `RobotCodeRunConfiguration` extends `AbstractPythonRunConfiguration`, and `RobotCodeRunProfileState` extends `PythonCommandLineState`. Its `buildPythonExecution(request)` gates on the environment state, refuses a remote interpreter (`PythonSdkUtil.isRemote`) with "not supported yet", picks the debug port and returns a `PythonScriptExecution` of the bundled robotcode's local path with `-u -X utf8` and `--no-pager -dp . debug [--no-debug] [--tcp <port>] [-- <robot arguments>]`. A "Files and folders" target puts its paths after `--`. `createProcessHandler(Process, String, TargetEnvironment, TargetedCommandLine)` creates the handler. Both runners call `state.execute(executor)` on a background thread.
- `intellij-wsl-language-server`: the WSL interpreter kind in the environment state, with its probe and results; the pure Kotlin path mapper with the roots of the distribution and of the Windows drives; the refusal of runs for the WSL kind.
- `intellij-async-run-and-debug`: a coroutine scope per run, bound to the process handler; the handshake runs in it, connects with a 15-second wait, and ends a run that does not connect with a console message.
- `intellij-debugger-breakpoints`: the handshake order `initialize`, `initialized`, configuration requests, `attach` (awaited), `configurationDone`.
- `intellij-run-stop`: an OS-assigned port for every run, always passed with `--tcp`; a process handler whose destroy path asks the debugger to end the run (DAP `terminate`) and falls back to the inherited kill. Its design leaves handlers of non-local targets out of scope.
- `intellij-test-result-events`: the converter passes Robot events to the platform's events processor, with the location URL built from the event's source as today.

**Plugin code on main:**
- The converter builds the location hint as `robotcode:///` plus `Urls.newLocalFileUrl(attributes.source)` plus `?line=` (`RobotOutputToGeneralTestEventsConverter.kt`); the run markers build the same URL from the discovered item's `source`, which the WSL language server change maps to the IDE path; `RobotSMTestLocator` resolves the URL's path with `LocalFileSystem`.
- Breakpoints send `file.toNioPath().toString()` as `source.path` (`RobotCodeDebugProcess.kt`); frames open `frame.source.path` with `VfsUtil.findFile` (`RobotCodeStackFrame.kt`); `attach` is sent with an empty map.
- The protocol client receives `robotStarted`, `robotEnded`, `robotSetFailed`, `robotLog`, `robotMessage` and `robotExited` and fires one signal per event (`RobotCodeDebugProtocolClient.kt`). Their arguments carry debuggee paths: the event `source`, `attributes.source`, the sources of `failedKeywords`, the sources of log messages, and the output, log and report files of `robotExited`.

**The debugger:**
- `robotcode debug --tcp <port>` listens on `127.0.0.1` unless `--bind` is given (`run.py`, `_debug_adapter_server_async`).
- `attach` accepts `pathMappings`, a list of `localRoot`/`remoteRoot` pairs (`server.py`). `map_path_to_client` maps a debuggee path with the first pair whose `remoteRoot` contains it, not the longest, and builds a Windows path when `localRoot` looks like one (`debugger.py`). It is applied to the sources of executing keywords before they are compared with the breakpoints, which the debugger keeps under the client's paths (a `PureWindowsPath`, case-insensitive, for a UNC or drive path), to stack frames and to the sources of output events.
- Robot events are not mapped: their ids (`<path>;<longname>[;<line>]`) and sources are debuggee paths (`listeners.py`).

**PyCharm 2026.1:**
- `PythonCommandLineState.getTargetPath(TargetEnvironmentRequest, Path)` (protected, unannotated) resolves a local path through the SDK's path mappings, or else through the request's upload roots with `TargetEnvironmentFunctions.targetPath` (`@Experimental`).
- `TargetEnvironment.UploadRoot`, `TargetEnvironment.TargetPath.Temporary`, `TargetEnvironment.TargetPortBinding(Integer local, int target)`, `ResolvedPortBinding` and `HostPort` are unannotated; `TargetEnvironmentRequest`, `TargetEnvironment`, `PythonExecution` and `PythonScriptExecution` are `@Experimental`.
- `LocalTargetEnvironment` resolves a target port binding to `127.0.0.1:<port>`.
- In 2026.1 the WSL target environment hands uploads and port bindings to the IDE's WSL agent (an internal Eel environment); its request does not copy volumes unless asked to.

## Goals / Non-Goals

**Goals:**

- WSL runs on the planned run-configuration base, through PyCharm's target API instead of a second process launcher.
- One path table for the language server, the debugger's path mappings and the plugin's own event locations.
- Local runs keep their command line, connection address, handler and events exactly.

**Non-Goals:**

- Docker, SSH and other targets.
- A robotcode installed in the WSL environment.
- Path mappings that users configure on the interpreter, beyond the automatic WSL mapping.
- Debugging Python code of keywords in the same run, and attaching to a debugger started outside the IDE.

## Decisions

### WSL interpreters pass the run gate

`buildPythonExecution` refuses only remote interpreters that are not of the WSL kind. A WSL interpreter goes through the environment state as every interpreter does: a usable result starts the run, any other result fails it with its message. The run-configuration base refuses every remote interpreter, and the WSL language server change gives that refusal its WSL message; for WSL interpreters the refusal goes away.

### Validation before a run accepts WSL interpreters

The validation before a run that `intellij-python-interpreter` plans reports remote interpreters as unsupported, WSL included. Where it exists, it uses the same test as `buildPythonExecution`, so that only remote interpreters other than the WSL kind get that error; problems of a WSL interpreter, such as a distribution that is not installed, come from its environment result like those of every interpreter. The spec modifies that planned requirement as copied on 2026-10-03; if this change is archived before `intellij-python-interpreter`, the block moves into that change instead.

### The bundled robotcode as an upload root

`buildPythonExecution` adds the bundled folder (`bundled`, which holds `tool` and `libs`, whose relative layout the entry script relies on) as an upload root with a temporary target path to the target request, and resolves the script path below it with `getTargetPath`. For the local target the upload root is the local folder itself, so local runs keep today's path. For WSL, the request does not copy volumes unless asked to, so the folder is expected to be reached through the distribution's mount of the Windows drives, as the language server reaches it; this is an assumption from the bytecode, and task 3.3 records the resolved path.

Alternatives:
- `PythonModuleExecution` of `robotcode.cli`: needs robotcode installed in the distribution, in a version that may differ from the plugin's.
- Computing `/mnt/c/…` with the plugin's own mapper: bypasses the target's own mapping and would be wrong for a target that copies uploads.

### Paths on the command line through the target

Every argument that is a local path, the paths of a "Files and folders" target and any other option that takes a path, is passed as a target value resolved with `getTargetPath`, so the path inside the distribution reaches robotcode. The working directory already comes from the base class. Arguments that are not paths, such as test names, stay as they are.

### The debugger port as a target port binding

The port that the run picks, an OS-assigned one once `intellij-run-stop` has landed and today's choice before, becomes the target side of a `TargetPortBinding` that `buildPythonExecution` registers on the request. `createProcessHandler` reads the binding's resolved local endpoint from the `TargetEnvironment` and keeps host and port for the handshake, which connects there. For the local target the endpoint is `127.0.0.1:<port>`, the address runs use today. Inside the distribution the debugger keeps listening on `127.0.0.1`; PyCharm's forwarding reaches it there, in NAT and in mirrored networking mode.

Alternatives:
- `--bind 0.0.0.0` and a connection to the distribution's IP address: the port is then open beyond the loopback, it works only in NAT mode, and Windows may ask for a firewall rule.
- The debugger connects to the IDE: a connect-back mode that the debugger does not have.

### Path mappings for the debugger

For a WSL run, `attach` carries `pathMappings` built from the WSL language server change's path table: one pair per root, `localRoot` in the IDE's Windows form (for example `\\wsl.localhost\Ubuntu\` or `C:\`) and `remoteRoot` the distribution's path (`/`, `/mnt/c/`). The pairs are ordered by descending length of `remoteRoot`, because the debugger takes the first pair that contains a path, and `/` contains every path. The debugger then compares executing sources with the breakpoints' IDE paths, and maps frames and output sources to IDE paths. Local runs send no mappings, as today. `attach` precedes `configurationDone` in the planned handshake, so the mappings are in place before the first keyword runs. The planned attach configuration (`intellij-robot-remote-attach`) sends `attach` with path mappings as well; whichever of the two changes lands first gives the handshake a path-mappings parameter, and the other passes its own list.

### Robot event paths translated in the protocol client

For a WSL run, the state gives the protocol client the mapper's distribution-to-IDE direction, and the client translates the path fields of every Robot event before it fires the signal: the event `source`, `attributes.source`, the sources of failed keywords and log messages, and the output, log and report files of `robotExited`. The converter, and every later consumer such as failure links, the log tab or opening the report, then see IDE paths, and the location URLs match those of the run markers, which use the mapped discovery sources. Event ids are not translated: the results tree compares them only with ids of the same run.

Navigation from the results tree goes through `RobotSMTestLocator`, which parses the location URL back into a path and a line and looks the path up with `LocalFileSystem`. So far it has only seen drive and POSIX paths; a UNC path such as `//wsl.localhost/Ubuntu/…` must keep its leading double slash through `newLocalFileUrl` and the parsing. The parsing becomes a pure function with tests for UNC, drive and POSIX paths, and is fixed if it loses the double slash.

Alternatives:
- Translating in each consumer: every consumer has to remember it.
- Letting the debugger translate its events with `pathMappings`: it changes the event fields for every client, and VS Code matches event ids against discovery ids built from debuggee paths.

### One process handler for local and WSL runs

`createProcessHandler` keeps returning the plugin's handler, also for the WSL target's process, so Stop goes through the debugger's `terminate` there as well and the output files are written. Its fallback destroys the target process; that the WSL agent then ends the process inside the distribution is an assumption that task 3.3 checks.

Alternative: PyCharm's own handler for target processes. Stop would then send no `terminate`, and a paused run would not end gracefully.

## Risks / Trade-offs

- [Experimental API: `TargetEnvironmentRequest` for upload roots and port bindings, `TargetEnvironment` for the resolved binding, `TargetEnvironmentFunctions.targetPath` behind `getTargetPath`, `PythonScriptExecution`] → Confined to `buildPythonExecution` and `createProcessHandler`, as in the run-configuration base; `verifyPlugin` reports changes on 261 and the newer configured versions.
- [The target port is chosen before the environment exists, without knowing whether it is free inside the distribution] → A taken port makes the debugger fail to listen, and the run ends with the planned "did not connect" message; ephemeral ports collide rarely.
- [Port forwarding and uploads run through the IDE's internal WSL agent] → Only public target API is used; the manual check covers NAT and mirrored mode.
- [A fallback kill in `wsl.exe` mode may leave the robot process inside the distribution] → It runs only after a graceful stop failed; the manual check looks for leftover processes after Stop and after Kill.
- [Translating the path fields of events misses a field that a later consumer reads] → All path fields are translated in one place, with a unit test per field.
- [The copied requirement blocks drift from `intellij-run-configuration-target` and `intellij-python-interpreter`] → Copy them again if those plans change before this change is archived.

## Migration Plan

None. Stored configurations keep their values; a configuration with a WSL interpreter starts to run instead of failing.
