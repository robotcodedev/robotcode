# Proposal

## Why

"Built-in preview" shows report and log in the platform's web preview. A preview of a file outside the project does not reload when a run writes the file again, and closing and reopening the preview on every run, which the plugin did to get the new content, moves the tab between editor splits and leaves the editor area in disorder (user report of 2026-10-14). VS Code shows the output in one panel that the next run reloads in place.

## What Changes

- "Built-in preview" opens the report and the log in a RobotCode preview tab of that file, with a browser that loads the file directly.
- When the preview tab of a file is open, the next run, "Open Report" and "Open Log" load the file's current content into that tab and bring it to the front in the editor split where it is; nothing is closed, and no second tab opens.
- This works the same for files inside and outside the project, and independently of the IDE's reload setting for its own preview.
- The preview tab has a small toolbar: Back and Forward through the pages it showed, such as from the report to the log, Reload of the shown page, Find in Page, and Open in Browser for the shown page.
- Without JCEF, the default browser is used, as before. The browsers keep getting a file of the project through the IDE's built-in web server.

Behaviour that users notice, for the release notes (not breaking): the preview of report and log stays where the user put it, shows the latest run, and has a toolbar to go back and forward, reload, find in the page and open the page in a browser.

Not part of this change: a tool window for the output; a match count for Find in Page, since the IDE's JCEF reports no find results.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-test-results`: the built-in preview of report and log as a RobotCode preview tab that later opens reload in place, with a toolbar.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeOutputFiles.kt`: the built-in preview opens or reloads the RobotCode preview tab instead of the platform's preview.
- A new file in `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/` with the preview tab's virtual file, editor and editor provider.
- `intellij-client/src/main/resources/META-INF/plugin.xml`: the editor provider.
- New tests under `intellij-client/src/test/kotlin/`.
- No change to robotcode, the language server, the VS Code extension or `robot.toml`.
