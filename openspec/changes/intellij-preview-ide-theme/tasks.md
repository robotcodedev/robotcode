# Tasks

## 1. Color scheme of the preview (design D1–D4)

- [ ] 1.1 In `RobotCodeOutputPreview.kt`, add the function that builds the parameters of `Emulation.setEmulatedMedia` for light and dark (D4); verify with a unit test in `RobotCodeOutputPreviewTest` that it gives `{"features":[{"name":"prefers-color-scheme","value":"light"}]}` and the same with `dark`.
- [ ] 1.2 Build the preview's browser without a URL. When JCEF reports it created, send the IDE's color scheme (`JBColor.isBright()`) over `CefBrowser.getDevToolsClient()` and load the file when the call has completed, also when it failed or there is no client. Send the new color scheme on each `LafManagerListener` notification, subscribed with the editor as parent disposable, and close the DevTools client when the editor is disposed (D2, D3). Verify that `./gradlew compileKotlin` succeeds and the tests in `RobotCodeOutputPreviewTest` pass.

## 2. Docs

- [ ] 2.1 In `docs/src/content/docs/guides/pycharm/running-tests.mdx`, after the description of the preview tab, say that with Robot Framework 7.0 or later the preview shows the report and the log in PyCharm's light or dark theme and follows a change of it, and that the page's own theme switch keeps working; verify the page in the docs dev server.

## 3. Verification

- [ ] 3.1 Run `(cd intellij-client && ./gradlew test)` and `./gradlew verifyPlugin`; verify both are green and that `verifyPlugin` reports no new experimental or internal API usages besides the known LSP4IJ ones, or note them for a decision.
- [ ] 3.2 Check in the UI-test PyCharm with Robot Framework 7.5, after removing the choice that the preview's browser kept from the guide's recordings:
  - "Open Report" shows the report light in Islands Light, "Open Log" the log dark in Islands Dark;
  - switching the IDE's theme with the report open switches the page without loading it again: Back stays as it was and the page keeps its position;
  - the link to the log in the report shows the IDE's theme;
  - the report's own switch to dark stays after another run, and the next change of the IDE's theme takes over again.

  Verify with screenshots, then restore the sandbox.

## Workflow follow-up

- Tick J7 in `playground/pycharm-befunde.md` after the commit.
- The guide's recording scripts keep a choice in the harness's browser with `?theme=` (`previewTheme` in `playground/robotcode-demo/pycharm/guide.js`); with this change, switching the IDE's theme is enough.
- Archive the change after review.
