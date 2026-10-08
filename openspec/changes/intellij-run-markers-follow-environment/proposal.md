# Proposal

## Why

Since the environment check runs in the background, test discovery skips its refresh while the project's interpreter is not usable, and so it no longer clears its test list. The run markers of the last successful discovery then stay in the editor, although every click on them ends with "Error running": they offer runs that cannot start. Before, a discovery that failed because of the interpreter cleared the list, so the markers disappeared.

## What Changes

- When the result of the environment check for the project's interpreter becomes not usable, a problem such as a missing Robot Framework or a check that failed, the plugin removes the run markers of the project's tests. The banner on Robot Framework files names the reason, as before.
- When the interpreter becomes usable again, the full discovery that already runs then brings the markers back.
- While a check is running, the markers stay as they are, so that switching between two usable interpreters does not make them disappear and reappear.

Behaviour that users notice, for the release notes (not breaking): run markers disappear while the project has no usable Python interpreter.

Not part of this change: markers for files that discovery reports problems in; the behaviour of runs, which already fail with the result's text.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-python-environment`: run markers are shown only while the project's interpreter is usable.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/testing/RobotCodeTestManager.kt`: a way to clear the test list and redraw the markers.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/RobotCodeLanguageServerManager.kt` or a listener next to it: clears the test list when the result becomes not usable.
- New light platform tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the VS Code extension, runs or discovery's command lines.
