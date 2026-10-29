# Proposal

## Why

With a WSL interpreter, RobotCode's editor features and run markers work in PyCharm on Windows, but Run and Debug still end with "not supported yet". Running and debugging the tests is the other half of what the reports in issue #433 ask for, and the run configurations are already PyCharm Python run configurations, whose base can run on PyCharm's WSL target.

## What Changes

- Run and Debug of Robot Framework run configurations work with a WSL interpreter. The robot process runs inside the interpreter's distribution, with the configuration's interpreter, interpreter options, working directory and environment, prepared the way PyCharm prepares its own Python runs on WSL.
- The run uses RobotCode's bundled robotcode through PyCharm's WSL support; nothing has to be installed in WSL besides Python and Robot Framework.
- Paths that a run passes to robotcode, such as the files and folders of a "Files and folders" target, are translated into the distribution's paths, for a project inside the distribution and for a project on a Windows drive.
- The debugger connection runs through PyCharm's port forwarding for WSL, so it needs no firewall rule and works in every networking mode of WSL.
- The debugger stops at the breakpoints set in the IDE, and its frames open the files the IDE shows. Stepping, Run to Cursor and evaluating work as with a local interpreter, and Stop ends the run gracefully with its output files written.
- With "Attach Python" of `intellij-debugger-attach-python` on, a Debug run with a WSL interpreter also debugs the Python code of libraries and keywords: Python breakpoints set in the IDE's files stop the run inside the distribution, the Python frames open the files the IDE shows, and Stop in either session ends the run gracefully.
- The results tree opens the right file and line for each test, the gutter shows the result states after a run, and every location that the run reports to the plugin, such as a log message's source or the output, log and report files, points to the file as the IDE shows it.
- The PyCharm guide describes runs, debugging and "Attach Python" with WSL interpreters.

Behaviour that users notice, for the release notes (not breaking): Robot Framework runs and debugging, also with "Attach Python", work with WSL interpreters. Docker, SSH and other remote interpreters are still refused with "not supported yet".

Not part of this change: Docker, SSH and other remote interpreters; a robotcode installed in the WSL environment instead of the bundled one; path mappings that users configure on the interpreter beyond the automatic WSL mapping; attaching to a robotcode debugger that runs outside the IDE.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `intellij-run-configurations`: runs with a WSL interpreter execute inside the distribution, with the bundled robotcode and translated paths, and the editor no longer flags WSL interpreters.
- `intellij-test-results`: the locations that a run inside WSL reports point to the files the IDE shows, for the results tree, the gutter states and every other use.
- `intellij-debugging`: debugging a run with a WSL interpreter, with breakpoints, frames, stepping and Stop as with a local interpreter, and with "Attach Python" the Python session too.
- `intellij-python-environment`: the requirement that refuses runs with a WSL interpreter goes away.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeRunProfileState.kt`: `interpreterRefusal`, which `buildPythonExecution` and `RobotCodeRunConfiguration.checkConfiguration` share, lets WSL interpreters through; the bundled robotcode as an upload root of the target request; translated path arguments; a target port binding for the debugger port, and the endpoint it resolves to for `connectDebugger`.
- The run's DAP handshake: `attach` with path mappings for WSL runs.
- `debugging/RobotCodeDebugProtocolClient.kt`: the path fields of Robot Framework events translated before any consumer sees them.
- `execution/RobotSMTestLocator.kt`: the parsing of location URLs, so that a path below `\\wsl.localhost\` opens from the results tree.
- The WSL support file of the WSL language server change: the debugger's path mappings and the Python session's path mapping from the same table.
- `RobotCodePythonSessionHandler` of `intellij-debugger-attach-python`: a position converter for the Python session of a WSL run.
- The PyCharm guide: `guides/pycharm/configuration.mdx`, `guides/pycharm/running-tests.mdx` and `guides/pycharm/debugging.mdx`.
- New unit tests under `intellij-client/src/test/kotlin/`, and one test under `tests/robotcode/debugger/` that pins how the debugger applies such path mappings.
- Depends on `intellij-wsl-language-server`, and for the Python debugging of WSL runs on `intellij-debugger-attach-python`; both must be implemented first.
- No change to the language server, discovery, the VS Code extension or `robot.toml`.
