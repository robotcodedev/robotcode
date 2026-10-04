# Proposal

## Why

PyCharm on Windows lets a project use a Python interpreter inside WSL, and many Robot Framework projects live in WSL for exactly that reason. RobotCode does not work with such an interpreter: the plugin starts every robotcode process as a local Windows process and probes the interpreter as a local file, so the language server, test discovery and runs stay off, and the editor calls the interpreter invalid, or "not supported yet" once the background environment check exists. Issue #433 collects reports from version 1.0.3 to 2.5.1, and a community fix shows that users patch the plugin themselves to get there. The maintainer decided that remote interpreters are a goal, starting with WSL; this change brings the editor features, the next one brings runs.

## What Changes

- With a WSL interpreter, the RobotCode language server runs inside the interpreter's WSL distribution. Completion, diagnostics, hover, inlay hints, Go to Definition, Find Usages, rename and quick fixes work in Robot files of the project, both for a project inside the distribution (opened as `\\wsl.localhost\<distro>\...` or `\\wsl$\<distro>\...`) and for a project on a Windows drive that uses a WSL interpreter.
- Test discovery runs inside WSL as well, so run markers appear in the gutter. Every other robotcode process the plugin starts for the project, such as the profile list where it exists, runs there too.
- The environment check runs the interpreter inside WSL and reports the same results as for a local interpreter, for example a Python older than 3.10 or a missing Robot Framework. Three new messages name what is wrong with the WSL setup itself: the interpreter's distribution is not installed, RobotCode's bundled files cannot be reached from WSL, or the project folder cannot be reached from the interpreter's distribution.
- RobotCode uses its bundled robotcode from the plugin folder through the distribution's mount of the Windows drives. The interpreter needs only Python 3.10 or newer with Robot Framework 5.0 or newer; nothing else has to be installed in WSL.
- The plugin talks to a server in WSL over the process's standard input and output, so no network port is opened and WSL's network mode does not matter. The server's messages appear in the Language Servers tool window, as for a local interpreter.
- The language server and discovery accept and report file locations in the form the IDE uses for WSL files, through an internal option that only the IntelliJ plugin passes. VS Code and the command line behave as before.
- In standard-input/output mode, the language server keeps its standard output for protocol messages, so a library that prints while it is loaded cannot break the connection, and it ends when its standard input closes. This applies to every client that starts the server in this mode.
- Run and Debug with a WSL interpreter are not part of this change. They end with the IDE's "Error running" message saying that Robot Framework runs with a WSL interpreter are not supported yet, instead of failing in an unclear way.

Behaviour that users notice, for the release notes (not breaking): RobotCode's editor features and run markers work in projects with a WSL interpreter. Docker, SSH and other remote interpreters keep the "not supported yet" message.

Not part of this change: running and debugging tests with a WSL interpreter; Docker, SSH and other remote interpreters; installing or copying robotcode into WSL, or using a robotcode installed there; translating absolute paths that users type into settings.

## Capabilities

### New Capabilities

- `intellij-python-environment`: WSL interpreters are recognized and checked inside their distribution, with their own results; every robotcode process of such a project runs there; runs with a WSL interpreter are refused for now.
- `intellij-language-server`: the language server runs inside the interpreter's distribution, over standard input and output, and file locations reach the server and come back in the form each side uses.
- `intellij-test-discovery`: discovery runs inside the interpreter's distribution and marks the tests of a WSL project in the gutter.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/`:
  - a new WSL support file: recognizing a WSL interpreter, its distribution and its interpreter path, and the path mapping between the IDE's and the distribution's view of files;
  - `RobotCodeHelpers.kt`: the command builder starts robotcode inside the distribution for a WSL interpreter;
  - the environment state service of the background environment check: the WSL kind, its probe and its results;
  - `lsp/RobotCodeLanguageServer.kt`: standard input and output for a server in WSL; `lsp/RobotCodeLanguageServerFactory.kt`: no IDE process id in `initialize` for such a server;
  - `testing/RobotCodeTestManager.kt`: the discovered sources in the IDE's form;
  - the run path: the "not supported yet" error for WSL interpreters.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the WSL messages; `intellij-client/README.md`: one line on WSL interpreters under Requirements.
- `packages/core/src/robotcode/core/uri.py`: the mapping between client URIs and local paths; `src/robotcode/cli/__init__.py`: the hidden global option that sets it; `packages/jsonrpc2/src/robotcode/jsonrpc2/server.py`: standard output and end of input in stdio mode.
- New tests under `intellij-client/src/test/kotlin/`, `tests/robotcode/core/`, `tests/robotcode/runner/cli/discover/` and `tests/robotcode/jsonrpc/`.
- No change to the VS Code extension or to `robot.toml`.
