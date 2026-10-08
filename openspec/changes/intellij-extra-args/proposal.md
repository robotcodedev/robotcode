# Proposal

## Why

VS Code users pass extra arguments to the `robotcode` processes the extension starts, for example `--log --log-level DEBUG` to find out why discovery or the language server misbehaves, or `--config` for an additional configuration file. PyCharm and IntelliJ IDEA offer no way to do this. The plugin's command-line builder already has a parameter for extra arguments, but nothing passes it. Where it would put them, after the plugin's own global options, a `--format` among them would override the `--format json` that test discovery relies on.

## What Changes

- Add a "General" page below the "Robot Framework" settings node, for VS Code's "General" category, with "Extra args", VS Code's `robotcode.extraArgs`. The plugin passes them as global options to every `robotcode` command it runs in the background for the project, such as test discovery. It does not pass them to the language server or to test runs, as in VS Code, where they reach the debug launcher but not the test process. Applying a change runs discovery again, without restarting the language server.
- Add a "Language Server" page below the "Robot Framework" settings node with "Extra args", VS Code's `robotcode.languageServer.extraArgs`. The plugin passes them as global options before `language-server`, which is where VS Code puts them too, although VS Code's description says otherwise. Applying a change restarts the language server. Output that such options produce, such as a debug log, appears in the RobotCode entry of the Language Servers tool window.
- Put extra arguments before the plugin's own global options in every `robotcode` command line, as VS Code does, so that the plugin's options win: a `--format`, `--color` or `--pager` among the extra arguments does not change what the plugin reads.
- Store both values for the current user only, in the project's workspace file, because they are mostly debugging aids. They are not shared through version control.

Behaviour that users notice, for the release notes (not breaking): none beyond the new settings.

Not part of this change: robotcode arguments for test runs; a toggle for the language server's debug log; settings for new projects.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-settings`: the General page and the Language Server page with their "Extra args", and the personal storage of both.
- `intellij-language-server`: the extra arguments on the language server's command line.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/RobotCodeHelpers.kt`: the argument order of `buildRobotCodeCommandLine`, extracted into a pure function.
- A new personal state component in `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/configuration/`, stored in `.idea/workspace.xml`.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/RobotCodeLanguageServer.kt` and `testing/RobotCodeTestManager.kt`: pass the extra arguments.
- New General and Language Server pages in `configuration/`, registered in `plugin.xml`, with texts in `messages/RobotCode.properties`.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the VS Code extension or `robot.toml`.
