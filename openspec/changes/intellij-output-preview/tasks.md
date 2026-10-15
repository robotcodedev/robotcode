# Tasks

## 1. Preview tab

- [x] 1.1 Add the preview tab: a `LightVirtualFile` for one output file, equal for the same path and named "Preview of" and the file's name; an editor that shows a `JBCefBrowser` for the file's `file://` URL, can load it again with a query parameter that changes on every load, and disposes the browser; and a dumb-aware editor provider that accepts only these files and hides the default editor, registered as `fileEditorProvider` in `plugin.xml`. Verify with a light platform test: the provider accepts the preview file and refuses another file, and two preview files of one path are equal.
- [x] 1.2 Let `openOutputFile` open the built-in preview through it: load the file into the open editors of the preview file and select the tab with `setSelectedComposite(file, false)` in each editor split that has it open, or open it with `navigate(true)`; remove the platform preview and the uncommitted close-and-reopen fix. Verify in task 2.2.

- [x] 1.3 Add the toolbar to the preview editor: Back and Forward through the page's history (`history.back()` and `history.forward()`), enabled from a `CefLoadHandler` registered with `JBCefClient.addLoadHandler`; Reload with `reloadIgnoreCache()`; Find in Page with a search field below the toolbar, also on the IDE's Find shortcut, `find` on typing and on Enter and Shift+Enter, `stopFinding` on Escape or close; and Open in Browser for the file of the shown page through the path of the target "Default browser". Replace the changing query of a later open with `reloadIgnoreCache()` when the tab shows its own file, and load the file otherwise. Texts in `messages/RobotCode.properties`. Verify the function that turns a page URL into its file with a JUnit test (query, fragment, another scheme) and the rest in task 2.4.

## 2. Verification

- [x] 2.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [x] 2.2 Check in the headless PyCharm harness:
  - a run with "Open output after run" set to "Report" opens the preview tab of `report.html`, which shows that run's report;
  - with the tab moved to a right split and the test changed in the left split, three more runs leave one preview tab, in the right split, showing each run's report, also when another file was in front of it there, and the left split shows only the test and stays the current split;
  - with the output directory outside the project, the second run's report appears in the open tab;
  - "Open Log" opens the preview tab of `log.html`, and a link from the report to the log works in the report's tab;
  - with "Default browser", the recording `BrowserLauncher` still receives the http URL of the built-in web server;
  - `idea.log` gets no new SEVERE entries from RobotCode.
- [x] 2.3 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` again and verify that all three pass without new deprecation or internal-API findings.
- [x] 2.4 Check the toolbar in the headless PyCharm harness:
  - the tab shows Back, Forward, Reload, Find in Page and Open in Browser, with Back and Forward disabled after it opened;
  - after a click on a log link, Back shows the report and enables Forward, and Forward shows the log again;
  - after another run with "Open output after run" set to "Report" and without a link followed, Back stays disabled;
  - after a run with "Nothing", Reload shows that run's report;
  - Find in Page with a test name selects a match, and Escape hides the search field;
  - Open in Browser on the log makes the recording `BrowserLauncher` receive the http URL of `log.html`;
  - `idea.log` gets no new SEVERE entries from RobotCode.
