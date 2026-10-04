# Design

## Context

See proposal.md for the motivation. The state that shapes the approach, checked against the code on main, the language server and LSP4IJ 0.21.0 (bytecode):

- **Enablement:** `RobotCodeLanguageServerFactory` implements LSP4IJ's `LanguageServerEnablementSupport`. `setEnabled` stores an unpersisted user-data flag, and `isEnabled` runs `tryConfigureProject()` whenever the flag is not `true`, which switches the server back on. LSP4IJ calls `setEnabled(false)` in three cases:
  - when the server is disabled in the Language Servers tool window, through a stop with `willDisable`;
  - from its own guard after more than 19 failed restart attempts (`LanguageServerWrapper.start`);
  - for every stop with the default `StopOptions`, whose `willDisable` is `true`, which is what `RobotCodeLanguageServerManager.stop()` uses today.

  It calls `setEnabled(true)` for a start with `willEnable`.
- **The banner:** `editor/EditorNotificationProvider` shows the check's message with one link that opens the settings by the display name "Python Interpreter"; its close action only writes a log line.
- **The widget:** `editor/RobotCodeStatusBarWidgetFactory` shows a static icon with the tooltip "RobotFramework" and no click action. Its `getId()` returns "RobotCodeStatusBarWidget", while `plugin.xml` registers it as `dev.robotcode.robotcode4ij.editor.RobotCodeStatusBarWidget`; the platform requires both to match.
- **Project information:** `robot/projectInfo` returns `robotVersionString`, `robocopVersionString` (absent without Robocop), `pythonVersionString` (`sys.version`), `pythonExecutable` and `robotCodeVersionString` (`project_info.py`). `RobotCodeServerApi` declares only `robot/cache/clear`.
- **The client command:** quick fixes and refactorings end with the command `_robotcode.codeActionShowDocumentSelectAndRename` and the arguments `[uri, range, rename]`. "Create Keyword", "Create local variable", "Create suite variable", "Add argument", the "Surround with TRY" actions and "Assign keyword result to variable" pass `rename = false`; "Extract keyword" passes no third argument, which VS Code reads as `true` (`vscode-client/extension/index.ts`). The target file can differ from the edited one: "Create Keyword" may add the keyword to a resource file.
- **How LSP4IJ runs it:** no action with that id exists. LSP4IJ tries the server, then an action with the command's id, then a workspace edit built from the arguments, and then shows an error notification (analysis notes, `invoke-client-commands`). Code action intentions run in a write action, and the command runs right after the edit is applied, so a rename cannot start synchronously.
- **Documentation actions:** since commit b60a48bb (2026-10-03), the server offers "Show in Documentation Viewer", "Show in New Documentation Viewer" and "Open Documentation (deprecated)" only for code action requests whose `only` contains `source`. LSP4IJ 0.21.0 requests intentions without `only` and quick fixes with `only = ["quickfix"]`, and sends no other code action request.
- **The Python Interpreter page** has the configurable id `com.jetbrains.python.configuration.PyActiveSdkModuleConfigurable` in PyCharm and in the Python plugin for IntelliJ IDEA.
- **Planned changes this builds on, not implemented yet:**
  - `intellij-environment-check`: the state service with its topic, the per-result texts, a reset that checks again, the banner refresh on every state change, and the mark of a project that uses Robot Framework.
  - `intellij-profiles`: the personal state component `RobotCodePersonalConfiguration` in `workspace.xml`, the "General" group on the "Robot Framework" page, which leaves out personal rows for the default project, and the Select Configuration Profiles action.
  - `intellij-language-server-connection`: Restart and Clear Cache in the background, with `update()`.

## Goals / Non-Goals

**Goals:**

- One switch per project that the server, discovery, markers, producers and the banner all respect, and that LSP4IJ's toggle shows.
- A status entry that answers "which versions, which profiles, is RobotCode working" and leads to the actions.
- No error notification after a RobotCode code action.

**Non-Goals:**

- Installing packages; quick toggles; "Report Issue"; a switch for discovery alone.
- A documentation viewer or a handler for documentation commands.

## Decisions

### The switch is personal, and LSP4IJ's disable lasts for the session

`RobotCodePersonalConfiguration` gets `enabled`, which defaults to `true`, and the "General" group of the "Robot Framework" page gets the checkbox; like the other personal rows, it is left out for the default project. The factory's `isEnabled` becomes "switch on, not disabled for this session, and interpreter usable", and it changes no state. The factory's `setEnabled`:
- `true` turns the switch on and clears the session flag;
- `false` sets an in-memory session flag only.

Restart, Clear Cache and Restart, and the banner's Retry clear the session flag. The plugin's own stops pass `StopOptions().setWillDisable(false)`, so they no longer go through `setEnabled`.

Alternatives:
- Storing `setEnabled(false)` in the switch: LSP4IJ uses the same call for its guard against repeated failed starts, so a crash loop would switch RobotCode off for good.
- Ignoring `setEnabled`, as today: the toggle in the Language Servers tool window keeps not sticking.

### What "off" does

A change of the switch acts at once, without waiting for another change:
- **Off** stops the server, cancels discovery, empties the model so that markers and producers find nothing, restarts the daemon so that markers disappear, and refreshes the banners and the widget.
- **On** requests the environment state and starts as at project opening.

The producer and the banner provider also check the switch, so that nothing appears in the moment before the model is empty. The handler calls the language server manager and the test manager directly, so it works whether or not the planned settings topic of the discovery change exists; when that topic exists, the switch publishes it as well.

### The banner's actions

The banner gets four things:
- "Configure Python Interpreter...", which calls `ShowSettingsUtil.showSettingsDialog(project, predicate, null)` with a predicate on the configurable id;
- "Retry", which resets the environment state and restarts through the restart path, as Restart does;
- "Disable RobotCode for This Project", which turns the switch off;
- a close action, which adds the project to an in-memory set of dismissed projects and refreshes the banners.

For a missing or old Robot Framework, the text adds `"<interpreter>" -m pip install robotframework`, or `-U robotframework` for an upgrade, with the interpreter path from the environment state.

Alternatives:
- Installing through PyCharm's `PythonPackageManager`: its install API is `@ApiStatus.Experimental` or `@Internal`.
- Opening the settings by display name, as today: this breaks with language packs.

### One widget with an action popup

The factory's `getId()` returns the id from `plugin.xml`. The widget implements `StatusBarWidget.MultipleTextValuesPresentation`: `getSelectedValue()` gives the text, and `getPopup()` returns `JBPopupFactory.createActionGroupPopup` over the RobotCode action group.

Texts:
- **running:** "RF 7.5", plus " · " and the selected profiles, joined with commas;
- **interpreter not usable:** "RobotCode" with an error icon;
- **switched off:** "RobotCode off".

The tooltip lists the versions, the first word of `pythonVersionString`, the interpreter and the profiles, or the message of the environment state.

The factory's `isAvailable` returns whether the project uses Robot Framework, read from the environment service. When that mark changes, the plugin calls `StatusBarWidgetsManager.updateWidget(factory)`. When the state, the project information, the profile selection or the switch changes, it calls `StatusBar.updateWidget(id)`.

Alternative: several widgets that mirror VS Code's language status items. The analysis decided on one widget and leaves the Python entry to PyCharm's interpreter widget.

### Project information from the server

`RobotCodeServerApi` declares `@JsonRequest("robot/projectInfo")`. When `RobotCodeLanguageClient.handleServerStatusChanged` sees `started`, a coroutine on a project service's injected scope sends the request and keeps the answer, which is cleared when the server stops, and the widget refreshes. Nothing waits for it on the EDT.

### The RobotCode action group serves the menu and the popup

The group under Tools | RobotCode gets these new actions:
- "Configure Python Interpreter...", the same action the banner uses;
- "Show Language Server Log", which activates LSP4IJ's "Language Servers" tool window through `ToolWindowManager`;
- "Enable RobotCode for This Project", which is visible only while the switch is off.

The popup shows the whole group, including Select Configuration Profiles..., Restart and Clear Cache and Restart from the planned changes.

### The client command as an LSP4IJ command action

`plugin.xml` registers an `LSPCommandAction` subclass under the id `_robotcode.codeActionShowDocumentSelectAndRename`, outside every group. `commandPerformed` reads the URI, the range (an LSP4J `Range`) and the optional `rename` flag, which defaults to `true`. It then defers the rest with `invokeLater`, after the write action of the intention:
1. commit the documents;
2. find the file by its URL and open it with `FileEditorManager.openTextEditor`;
3. select the range from its end to its start, as VS Code does;
4. when `rename` is set, start the platform's Rename action on that editor through `ActionManager.tryToExecute`, so that LSP4IJ's rename handler, registered with `order="first"`, takes over.

Alternative: `ActionUtil.invokeAction`. It is deprecated, and `ActionUtil` is `@ApiStatus.Internal` in 2026.1.

### Documentation actions: neither a handler nor a filter

The analysis left open whether to filter "Open Documentation" or to add a minimal handler for `robotcode.showDocumentation`. Neither is needed. The server offers its three documentation actions only to requests that ask for `source` actions, and LSP4IJ 0.21.0 never sends such a request, so IntelliJ users never see them, and no error notification can come from them.

Against the alternatives:
- A handler would serve a command the server marks as deprecated.
- The two other commands need the Documentation Viewer, which is not part of the IntelliJ plugin.
- LSP4IJ offers no public way to filter single code actions; `LSPCodeActionFeature` can only switch intentions off as a whole.

A harness check confirms that the intention list offers no documentation action.

## Risks / Trade-offs

- [A later LSP4IJ version asks for `source` actions, and the three documentation actions appear without a handler] → The harness check catches this when the LSP4IJ version is raised. The server then needs a client option to leave them out, as it already decides about documentation links by an initialization option. A handler for the deprecated command alone would leave the other two failing.
- [`StatusBarWidgetsManager` lives in an `impl` package] → It is public and carries no status annotation in 2026.1. It is used only to re-evaluate availability; `verifyPlugin` reports changes.
- [Disabling the server in the Language Servers tool window lasts only for the session] → The setting on the "Robot Framework" page is the lasting switch, and the page says so.
- [The rename after "Extract keyword" depends on LSP4IJ's rename handler] → The harness checks it. Without the rename, the new name is still selected.

## Migration Plan

None. The switch defaults to on, and nothing that is stored changes for existing projects.
