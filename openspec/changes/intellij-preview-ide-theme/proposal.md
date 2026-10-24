# Proposal: intellij-preview-ide-theme

## Why

A report or a log of Robot Framework 7.0 or later in the built-in preview does not take the IDE's theme (J7 of the PyCharm findings): in the light theme it can show dark, in the dark theme light. Checked in the UI-test PyCharm 2026.1 with Robot Framework 7.5: the page takes its theme from a `?theme=` parameter of its URL, otherwise from a choice it keeps in the browser's local storage, otherwise from `prefers-color-scheme`. The preview's browser reported `prefers-color-scheme: dark` with the light and the dark IDE theme alike, so without a kept choice the report showed dark in the light theme.

## What Changes

- The preview gives its browser the IDE's theme, light or dark, as `prefers-color-scheme`: before it loads the page, and again when the IDE's theme changes. Reports and logs of Robot Framework 7.0 and later follow it, an open tab without being loaded again.
- The theme switch of the report and the log keeps working. Robot Framework keeps a choice made with it until the IDE's theme changes.
- The PyCharm guide's page on running tests says that the preview shows the report and the log in the IDE's theme.
- Not part of it: Robot Framework 5.0 to 6.1, whose report and log have one look only; "Open in Browser" and the other targets of "Open output target", whose browsers keep their own theme; VS Code's preview of the report and the log.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-test-results`: new requirements that the built-in preview shows reports and logs in the IDE's theme and follows a change of it, and that it keeps a choice made with the page's own theme switch until the IDE's theme changes.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeOutputPreview.kt`: the preview's browser gets the IDE's color scheme over JCEF's DevTools client before it loads the page, and again on a theme change.
- A unit test of the color scheme parameters in `RobotCodeOutputPreviewTest`; the behavior is checked in the UI-test PyCharm, since the platform tests have no browser.
- Docs: `guides/pycharm/running-tests.mdx`.
- The plugin's users: the preview matches the IDE's theme. Who switched a report's theme with its own switch keeps that choice until the IDE's theme changes.
