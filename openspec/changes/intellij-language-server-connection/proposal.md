# Proposal

## Why

In PyCharm and IntelliJ IDEA, the connection to the RobotCode language server breaks in ways users see every day. Every line the server writes to stderr, for example a robot.toml profile that no longer exists, becomes an "IDE error occurred" report that blames RobotCode, although the same line already appears in the Language Servers console. The plugin waits for the server on a port that is open on all network interfaces, for as long as the server runs, and it waits without a time limit. A server that exits before it connects blocks a thread forever, and stopping it then throws a NullPointerException (#630).

The Python check accepts Python 3.8 and 3.9, although every RobotCode package requires Python 3.10, and its message names 3.9 as the minimum. The VS Code extension has the same 3.8 check. When the check fails, Tools | RobotCode | Restart reuses the failed result, so installing Robot Framework does not bring the server back, and Clear Cache and Restart throws while the server is stopped.

## What Changes

- The plugin accepts the server's connection only on 127.0.0.1, and it stops listening once the server has connected.
- A server that exits before it connects fails the start with an error that names its exit code. A server that neither connects nor exits within 60 seconds is ended, and the start fails with an error that says so. No thread keeps waiting, and stopping or restarting afterwards no longer throws (#630).
- The server's stderr appears only in the RobotCode entry of the Language Servers tool window, as before, and no longer raises IDE errors. Output on stdout appears there too, instead of piling up unread where it can stall the server.
- Stopping and restarting give the server time to receive the exit notification and end on its own before the plugin ends the process, which removes the "Socket closed" error that every restart reported.
- RobotCode requires Python 3.10 or newer with Robot Framework 5.0 or newer, and every message about an unusable interpreter, including the error of a run, says so. The VS Code extension applies the same Python 3.10 minimum and names it, so both clients reject the same interpreters.
- Restart RobotCode Language Server checks the Python environment again, then restarts the server and runs discovery. Clear Cache and Restart clears the cache of a running server and then restarts the same way; without a running server it only restarts. Both run in the background and are disabled without a project.
- A restart that was scheduled just before a project closed no longer runs for the closed project.

The null-safe stop (#630) may land earlier as a plain fix. This change keeps the item.

Behaviour that users notice, for the release notes (not breaking): Python 3.8 and 3.9 interpreters are rejected up front with a message that names Python 3.10, in PyCharm and IntelliJ IDEA as well as in VS Code. They could not run RobotCode before either. Tools | RobotCode | Restart now picks up an interpreter that was fixed outside the IDE.

Not part of this change: checking the environment in the background with separate results for each problem and with timeouts; checking again when the interpreter changes; starting only in Robot Framework projects; which interpreter RobotCode uses; profiles and extra arguments on the server's command line; restarts triggered by settings and configuration files; transports other than the local socket, which remote interpreters would need.

## Capabilities

### New Capabilities

- `intellij-language-server`: how the IntelliJ plugin starts, connects to, stops and restarts the RobotCode language server, and where the server's output goes.
- `intellij-python-environment`: the Python and Robot Framework versions RobotCode needs in IntelliJ, and what the plugin tells the user about an interpreter that does not meet them.

### Modified Capabilities

- `vscode-extension-compatibility`: the VS Code extension accepts only Python 3.10 or newer and names that minimum.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/RobotCodeLanguageServer.kt`: loopback listener, connect step with liveness check and timeout, null-safe stop with a bounded wait, stdout forwarding, no own stderr handler, command line built only on start.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/RobotCodeHelpers.kt`: the Python 3.10 probe, the messages, and the restart manager on the coroutine scope the platform gives the service.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/RobotCodeLanguageServerManager.kt` and the two actions in `actions/`: background clearing and restarting, enablement.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the interpreter messages.
- `vscode-client/extension/pythonmanger.ts` and `vscode-client/extension/languageclientsmanger.ts`: the Python 3.10 probe and its message.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server or to `robot.toml`.
