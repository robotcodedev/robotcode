# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach, checked against the code on main, PyCharm 2026.1 and LSP4IJ 0.21.0 (bytecode):

- **The check:** `RobotCodeHelpers.checkPythonAndRobotVersion` resolves the interpreter as the SDK of the first module that has a Python SDK, requires its home path to exist as a regular file, and runs two processes through `ExecUtil.execAndGetOutput` with a 5-second timeout each: a version probe and the bundled `check_robot_version.py`. Everything runs in `executeOnPooledThread { }.get()`. Any non-zero result, including a timeout, becomes `INVALID_PYTHON_VERSION` or `INVALID_ROBOT` and is cached in project user data; the log lines contain neither the command nor the output.
- **Who blocks on it:** LSP4IJ's `isEnabled` through `tryConfigureProject`, the status bar widget's `isAvailable`, the editor banner's `collectNotificationData`, and `buildRobotCodeCommandLine`, which the language server, both discovery calls and runs use. A failed check throws `InvalidPythonOrRobotVersionException`, a plain `Exception`.
- **Runs start on the EDT:** both runners call `state.execute` synchronously inside `AsyncProgramRunner.execute`, and `startProcess` builds the command line there. Today the IDE shows "Error running" with the generic text "PythonSDK is not defined or robot version is not valid for project …" (runtime check Q18/Q31 in the analysis notes).
- **Startup and SDK events:** `RobotCodePostStartupActivity` calls `restartAll(reset = true, debounced = false)` for every project and restarts on every `SdkEntity` or `ModuleEntity` change in `workspaceModel.eventLog`. In 2026.1 the project SDK lives in `ProjectSettingsEntity`, and a module that inherits it keeps an unchanged dependency, so a project SDK change is missed (analysis notes, `invoke-project-sdk-change`). PyCharm's interpreter widget sets the module SDK, which is a `ModuleEntity` change.
- **LSP4IJ:** it consults the factory's `isEnabled` before it starts the server, and `LanguageServerManager.start` refuses a server that is not enabled unless `willEnable` is set.
- **Remote interpreters:** `PythonSdkUtil.isRemote(sdk)` is true when the SDK's additional data implements `PyRemoteSdkAdditionalDataMarker`. Target-based SDKs (`PyTargetAwareAdditionalData`), which PyCharm uses for WSL, Docker and SSH, implement it. Today the check probes such an SDK's home path on the local machine.
- **Bundled paths:** derived from `PathManager.getPluginsDir()/robotcode4ij/data`.
- **Planned change this builds on:** `intellij-language-server-connection` is planned, not implemented. This design assumes its planned design: Restart calls `restartAll(reset = true)` on the restart manager's coroutine scope, the interpreter texts live in the message bundle, and the probe requires Python 3.10.

## Goals / Non-Goals

**Goals:**

- One owner of the environment state, which every consumer reads without blocking.
- Results that tell users what to fix.
- Restarts only when the interpreter RobotCode uses has changed.
- A state model that a WSL interpreter kind can join later without reworking it.

**Non-Goals:**

- Choosing the interpreter differently: it stays the SDK of the first module that has a Python SDK.
- Banner actions beyond the existing link, a per-project switch, and the meaning of LSP4IJ's server toggle.
- The status widget beyond not blocking in `isAvailable`.
- Running anything on a remote interpreter.

## Decisions

### A project service owns the state, per interpreter

A new project service holds one state per interpreter:
- **Unknown:** not checked yet.
- **Checking:** a check is running.
- **Checked:** with a result, usable or one of the problems in the spec.
- **Failed:** the check itself failed; this is not a result about the interpreter.

An interpreter is identified by its kind, the SDK name and its home path. The service runs at most one check per interpreter at a time, on the coroutine scope the platform injects into the service, with `Dispatchers.IO`. It publishes every state change on a project topic.

Consumers read the state and never wait for it. When they find **Unknown**, they request a check. LSP4IJ's `isEnabled` returns whether the project interpreter is usable, `buildRobotCodeCommandLine` throws `CantRunException` with the message of the result, and the widget's `isAvailable` reads the state.

Alternatives:
- Keeping the user data cache and the blocking call: this is the status quo.
- One slot for the project interpreter only: runs that choose their own interpreter, which the planned run-configuration rework brings, and the validation before a run need the state of other interpreters too. The order of those changes relative to this one is open, so the state is per interpreter from the start.

### Classify before probing, with room for WSL

The service classifies the SDK before it runs anything:
1. No SDK gives the result "no interpreter".
2. `PythonSdkUtil.isRemote(sdk)` gives "remote, not supported yet" without starting a process.
3. A local SDK whose home path does not exist gives "path does not exist".
4. Any other local SDK is probed.

The kind is part of the interpreter's identity. The planned WSL support adds a WSL kind that is classified before the generic remote kind and brings its own probe, which runs the same snippet inside WSL and returns the same result model. The topic, the consumers and the results stay unchanged.

Alternatives:
- Probing the home path of every SDK locally: this is today's behaviour, and it runs the wrong interpreter when a remote path also exists locally.
- Keeping the `isRegularFile` test for local paths: a file that exists but cannot run is reported by the probe, as a failed check. The analysis notes an unverified risk that the JDK reports Windows app execution aliases, for example the Microsoft Store Python, as not regular files.

### One probe process with both versions

The probe runs `<python> -u -X utf8 -c <snippet>`. The snippet prints one JSON line with the Python version and the Robot Framework version, or the error that importing Robot Framework raised. It imports no RobotCode code, so it also runs on old Pythons and reports their version. Kotlin maps the JSON to a result with the minimums 3.10 and 5.0. The probe has a time limit of 30 seconds. A start failure, a non-zero exit code, output that is not the expected JSON, or the time limit gives **Failed**, and the service logs the command line, the exit code, stdout and stderr as a warning.

Alternatives:
- Keeping the version probe plus `check_robot_version.py`: that means two processes, no Robot Framework version for the message, and the script imports bundled RobotCode packages that need Python 3.10.
- Changing the output of `check_robot_version.py`: VS Code parses its `True`/`False`.

### What starts a check, and what a result changes

A check starts:
- when a consumer finds **Unknown**;
- on Restart, as a reset;
- when the identity of the project interpreter changes;
- when the SDK of an interpreter that is not usable changes;
- when a run starts and finds **Unknown** or **Failed**.

A consumer that finds **Failed** does not request a check, so a failing check is not repeated on its own.

A change of the project interpreter between usable and not usable acts as follows:
- To usable, it starts the language server, if needed, and a full discovery, but only in a project that uses Robot Framework: the startup lookup found Robot Framework files, or a Robot Framework file has been opened.
- From usable, it stops the server.
- Every change refreshes the banners through `EditorNotifications.updateAllNotifications()`.

A result that stays usable changes nothing; the restart path restarts by itself after its own check.

### Runs wait for a missing result

Before it builds the command line, the run path gets the result for the interpreter it runs with. On **Unknown** or **Failed**, it checks under `runWithModalProgressBlocking`, which shows a cancellable progress dialog, when it runs on the EDT as runs do today, or under `runBlockingCancellable` on a background thread. A result that is not usable, or a cancelled wait, ends in `CantRunException` with the message, so the IDE shows its usual run error.

Alternatives:
- Failing with "still checking": this gives spurious failures right after a project opens.
- Waiting on the EDT without progress: the UI freezes for up to 30 seconds.
- `ProgressManager.runProcessWithProgressSynchronously`: it is marked `@ApiStatus.Obsolete` in 2026.1.

### Reacting to SDK and module changes by identity

The existing `workspaceModel.eventLog` subscription moves into the service and also watches `ProjectSettingsEntity`. On each change, the service resolves the project interpreter again and compares its identity with the last one. A different identity starts a check and, if the server runs, a restart through the restart path. The same identity starts nothing, unless an `SdkEntity` change concerns the SDK in use and its result is not usable; then it starts a check.

Alternatives:
- `ModuleRootListener.TOPIC`: it also fires for root changes and needs the same comparison.
- Reacting to every change: this is today's behaviour, with the extra restart 42 seconds after opening a project that the analysis observed.

### Activation by index lookup

The startup activity returns at once for the default project and for LightEdit (`LightEdit.owns`). Otherwise it runs a `smartReadAction` off the EDT that asks two indexes:
- `FileTypeIndex.containsFileOfType` for the suite and resource file types;
- `FilenameIndex.getVirtualFilesByName` for `robot.toml` and `.robot.toml` in the project scope, using the non-deprecated overload without a project parameter.

A hit marks the project as a Robot Framework project and requests the check. Without a hit nothing starts. Opening a Robot Framework file marks the project too: if the result is already usable, the first discovery runs then, and LSP4IJ starts the server for the file as usual; otherwise the check is requested.

Alternative: relying on LSP4IJ's lazy start alone would leave Robot Framework projects without discovery, and so without Run in the Project view, until a file is opened.

### Bundled paths from the plugin descriptor

The base path becomes `PluginManagerCore.getPlugin(PluginId.getId("dev.robotcode.robotcode4ij"))?.pluginPath` plus `data`. Both calls carry no status annotation in 2026.1.

## Risks / Trade-offs

- [The first server start in a Robot Framework project now waits for the index lookup in smart mode] → The lookup is a cheap index query. During a long indexing, opening a Robot Framework file still requests the check and starts the server.
- [The probe repeats the Robot Framework minimum that VS Code reads from `check_robot_version.py`] → Both minimums sit next to the message texts that name them. VS Code is unchanged.
- [A remote SDK whose path also exists locally stops working] → It only worked by running the local interpreter by accident. The message says that remote interpreters are not supported yet.
- [A cancellable modal progress during a run start] → It appears only when no result exists yet, and for at most 30 seconds.
- [Installing packages from a terminal may not change the SDK in the workspace model] → This is not verified. Restart checks again in any case.
- [The run-configuration rework lands before this change] → The run path asks for the state of the interpreter it runs with, so the order does not matter.

## Migration Plan

None. Nothing that is stored changes.

## Open Questions

- Does `pip install` from a terminal lead to an `SdkEntity` change of the SDK in use? If not, users choose Restart after installing; the specs, the approach and the tasks stay the same either way.
