# Proposal: completion-private-keywords

## Why

Keyword completion offers keywords tagged `robot:private` from every imported file. After the user picks one, RobotCode reports a `PrivateKeyword` warning for the call it just suggested. Projects that use private keywords to hide helpers also get longer completion lists. Users asked for this in #495, again in #567 (closed as a duplicate) and in #652.

Private library keywords have the same problem without the warning. Libdoc leaves them out of a library's documentation, but completion offers them, and no diagnostic reports a call.

## What Changes

- **Completion hides private keywords of other files.**
  - Every keyword list leaves out private keywords that are not defined in the file being edited: the list without a prefix, the list after `Library.` and the list after `resource.`.
  - Hidden are private keywords of resource files other than the current file and every private library keyword.
  - Private keywords of the current file are still offered everywhere in that file, also in test cases. Robot Framework warns when a test calls a private keyword of its own suite file; that is a Robot Framework bug (robotframework/robotframework#5807), and RobotCode does not follow it.
- **Setting `robotcode.completion.hidePrivateKeywords`**, on by default. When it is off, the private keywords of other files are offered again, marked as `private` and sorted after the other keywords of the same list.
- **`PrivateKeyword` also for library keywords.**
  - A call of a private library keyword is reported as `PrivateKeyword`, with the message "Keyword '…' is private and should not be called from Robot Framework files."
  - Resource keywords keep Robot Framework's message "Keyword '…' is private and should only be called by keywords in the same file."
  - Robot Framework itself does not warn for library keywords. RobotCode reports what Libdoc and the library author mark as private.
- **What counts as private** does not change. It is what `library-documentation-extraction` defines: `robot:private` in a keyword's tags, including tags declared in its documentation, on Robot Framework 6.0 and newer.

## Capabilities

### New Capabilities

- `private-keywords`: how completion and diagnostics treat keywords tagged `robot:private`: which ones completion offers, how the setting changes that, and when a call is reported.

### Modified Capabilities

_None._ `library-documentation-extraction` already defines which keywords are private, and it stays as it is.

## Impact

- **Code:**
  - `packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py`: filter, marking and sorting in the three keyword lists.
  - `packages/language_server/src/robotcode/language_server/robotframework/configuration.py`: the new completion setting.
  - `packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py` and `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/analyzer.py`: `PrivateKeyword` for library keywords in both analysis paths.
  - `package.json`: the setting for VS Code.
- **IntelliJ:** The plugin does not send completion settings to the server yet, so the server's default applies there: private keywords of other files are hidden. A switch in the settings comes with the planned change `intellij-settings-pages`, which covers every completion setting VS Code offers.
- **Users:**
  - Calls of private library keywords get a new warning, in the editor and in `robotcode analyze code`, where a warning sets the exit code. Diagnostic modifiers can lower or ignore `PrivateKeyword`, as for every other code.
  - None of Robot Framework's standard libraries has private keywords, on RF 6.0 or RF 7.5.
- **Tests:** completion and diagnostics for private keywords, on both analysis paths.
