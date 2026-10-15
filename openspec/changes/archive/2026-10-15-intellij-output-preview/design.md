# Design

## Context

See proposal.md for the motivation.

**Current code** (checked on 2026-10-14):

- `openOutputFile` in `RobotCodeOutputFiles.kt` opens the built-in preview as the platform's `WebPreviewVirtualFile` with the file's URL from the built-in web server (`getBuiltInServerUrls`), or its `file://` URL for a file outside the project, through `OpenFileDescriptor.navigate(true)`. An uncommitted fix closes an open preview of the same file before that, so that it loads the new content.

**Platform behaviour** (javap and the headless harness, PyCharm 2026.1):

- `WebPreviewFileEditor` reloads its page in `reloadPage`, which is Kotlin-`internal` in a class marked `@ApiStatus.Internal`; the platform calls it when it creates the editor.
- An open preview reloads in place only through the live reload of the built-in web server: a page served over http connects back through a web socket, and `WebServerPageConnectionService.reloadRelatedClients` reloads it when the file system reports a change of a file it served. A preview with a `file://` URL has no such connection; in the harness, it kept showing the first run's report after a second run.
- `OpenFileDescriptor.navigate` opens a file that is not open in the current editor window; closing the preview first therefore moves it into the split that has the focus. The menu's right split comes from `OpenInRightSplitAction`, which is internal API.
- JCEF loads `file://` URLs: the platform's preview showed a report from outside the project.
- Loading the same `file://` URL again does not reload a page whose fragment changed, as a click in a report or log changes it; `CefBrowser.reloadIgnoreCache()` reloads it and keeps the history (harness).
- `CefBrowser` offers `goBack`, `goForward`, `canGoBack`, `canGoForward`, `reloadIgnoreCache`, `find` and `stopFinding`; `JBCefClient.addLoadHandler` delivers `CefLoadHandler.onLoadingStateChange` with the back and forward state, on a thread of the browser. In the harness, `goBack()` did nothing although `canGoBack()` was true, while `history.back()` and `history.forward()` run through `executeJavaScript` moved the page's history; `find` with `stopFinding(false)` left the match selected. The IDE's JCEF has no `CefFindHandler`, so a search reports no match count. `ActionToolbar.updateActionsAsync()` is unannotated; `updateActionsImmediately()` is deprecated.
- In 2026.3, JCEF is the bundled plugin "Web Browser (JCEF)" (`com.intellij.modules.jcef`); the plugin verifier resolves its classes for 2026.3 and reports the plugin as compatible.
- `OpenFileDescriptor.navigate(false)` on an open tab in another split makes that split the current editor window, in which files open next (harness). `EditorWindow.setSelectedComposite(VirtualFile, Boolean)` selects a tab in its window; it and `FileEditorManagerEx.getWindows()` are unannotated in 2026.1 and 2026.3.
- Public and unannotated in 2026.1 and 2026.3: `JBCefBrowser.createBuilder()`, `JBCefBrowserBuilder.setUrl` and `build`, `JBCefBrowserBase.loadURL`, the `fileEditorProvider` extension point with `FileEditorProvider`, `FileEditorManager.getEditorList(VirtualFile)`, `OpenFileDescriptor(Project, VirtualFile)` with `navigate(Boolean)`, and `LightVirtualFile`.

## Goals / Non-Goals

**Goals:**

- One preview tab per output file that stays where the user put it and shows the latest run, for files inside and outside the project.

**Non-Goals:**

- A tool window for the output, and a match count for Find in Page.
- A change to how the browsers open report and log.

## Decisions

### A RobotCode preview tab

A `LightVirtualFile` of its own stands for the preview of one output file; two of them are equal when they stand for the same path, so the editor manager finds an open tab again. Its name is "Preview of" and the file's name, as the platform names its preview tab. An editor provider, registered through the `fileEditorProvider` extension point, accepts only these files, is dumb aware, and hides the default editor. Its editor shows a `JBCefBrowser` and disposes it with itself.

### The file's own URL

The preview loads the file's `file://` URL, also for a file of the project. The plugin reloads the tab itself, so it needs neither the built-in web server nor its live reload, and relative links from the report to the log work in the folder of the files. When the tab shows its own file, a later open reloads it with `reloadIgnoreCache()`, which also works after a click changed the fragment and adds nothing to the history; when the tab shows another page, such as the log after a link, it loads the tab's file.

### Reuse before opening

`openOutputFile` looks for open editors of the preview file with `getEditorList`. When there are any, it loads the file into their browsers again and selects the tab with `setSelectedComposite(file, false)` in each editor split that has it open, which leaves the current split and the focus where they are; `navigate(false)` would make the tab's split the current one. Otherwise it opens the tab with `navigate(true)`. The uncommitted fix that closes and reopens the platform's preview goes away.

Alternatives:
- The platform's preview, closed and reopened on every open: it moves the tab between splits (the user report).
- The platform's preview, only brought to the front: a file outside the project keeps its old content, and its reload is internal API.
- A tool window for report and log: a larger change of the user interface, and unlike VS Code, which reloads its panel in place.
- `HTMLEditorProvider.openEditor`: it lives in an implementation package, opens a new tab on every call, and offers no reload.

### A toolbar above the page

The editor's component holds a horizontal action toolbar above the browser:
- **Back** and **Forward** run `history.back()` and `history.forward()` in the page; they are enabled from the state that a load handler receives in `onLoadingStateChange`, which also asks the toolbar to update, on the user interface thread.
- **Reload** calls `reloadIgnoreCache()` for the shown page.
- **Find in Page** shows a search field below the toolbar, also through the IDE's Find shortcut in the tab: typing starts a search with `find`, Enter and Shift+Enter move to the next and previous match, and Escape or the close button ends it with `stopFinding` and hides the field.
- **Open in Browser** opens the file of the shown page in the default browser, through the same path as the target "Default browser", so a file of the project gets the built-in web server's URL.

Alternative: a query parameter that changes on every load, which the first version used to reload a page whose fragment changed. Every run would add a history entry, so Back would go through old copies of the same report.

## Risks / Trade-offs

- [Two runs write their output to different folders] → Each file gets a tab of its own, since the tab stands for a path.
- [The IDE has no JCEF] → The effective target is the default browser, as before, so no preview tab opens.
- [JCEF stops loading `file://` URLs in a later version] → The harness check opens a report from outside the project.
- [JCEF is a plugin of its own from 2026.3 on] → `verifyPlugin` checks 2026.3; if the IDE ships without it, `JBCefApp.isSupported()` is false and the target falls back to the default browser.

## Migration Plan

None. Nothing is stored.
