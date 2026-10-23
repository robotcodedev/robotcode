# Design

## Context

The versions that the list needs are in the extension already (`vscode-client/extension/`):

- **RobotCode:** the extension's version is `extension.packageJSON.version`; the language status shows it as its RobotCode item, whose command opens the RobotCode menu (`robotcode.showToolMenu`) for the folder of the active editor.
- **Language server:** `LanguageClientsManager.getProjectInfo(folder)` asks the folder's language server with `robot/projectInfo` for the versions of Robot Framework and Robocop and for its own RobotCode version (`robotCodeVersionString`, the `__version__` of the `robotcode` it runs). Without a client for the folder it returns `undefined`; a client that is still starting delays the answer.
- **Environment check:** `LanguageClientsManager.getRobotEnvironmentState(folder)` holds what the check of the folder's environment found, also without a language server: usable, or the problem (no interpreter, interpreter missing, Python too old, Robot Framework missing or too old), and the Robot Framework version it saw.
- **Python:** `PythonManager.getPythonInfo(folder)` returns version, name, path and the kind of environment (`type`: the environment manager of the Python Environments extension, or the tool of the older Python extension API).
- **Language status texts:** `LanguageToolsManager.updateItems` builds the texts of the Robot Framework and Python items from these values, with "not installed", "unknown", "no interpreter selected" and "(not supported)".
- **VS Code and OS:** `vscode.version`, `vscode.env.appName` and `vscode.env.remoteName`; Node's `os.type()`, `os.arch()` and `os.release()`. VS Code's own system information, which its issue reporter and `code --status` show as "OS Version", joins these three the same way (`mainImpl.js` of VS Code 1.142).
- **RobotCode menu:** the menu (`toolMenu` in `languageToolsManager.ts`) has the section Developer Tools, which ends with Report Issue. It opens only for a folder whose language server runs.
- **Report Issue** passes Python, Robot Framework and Robocop versions to VS Code's issue reporter, which adds VS Code, the OS and the extension's version itself.
- **Bug template:** `.github/ISSUE_TEMPLATE/bug_report.md` asks for VS Code Version, RobotCode Version, OS, Python Version, RobotFramework Version and "Additional tools like robocop".

## Goals / Non-Goals

**Goals:**
- One function builds the text of the list, and unit tests check it without a VS Code window.
- The list says about Robot Framework and Python what the language status says.

**Non-Goals:**
- No change to the data of Report Issue, to the language status items or to the language server.
- No copying from the other language status items; the RobotCode menu is the way from the language status.

## Decisions

### D1: A function builds the text, the command gathers the values

A new module `vscode-client/extension/environmentInfo.ts` exports a function that takes the values (the versions, the kind of environment, the application name, the remote name and the parts of the OS) and returns the Markdown list. The command gathers the values and copies the text with `vscode.env.clipboard.writeText`.

- **Alternative: build the text in the command handler.** It could only be tested through the UI.

### D2: Robot Framework and Python as the language status shows them

The text of the Robot Framework version moves from `updateItems` into a function of the new module, which the language status and the list both use: the language server's version, else the version the environment check saw, `<version> (not supported)` when it is older than 5.0, "not installed" when it is missing, and "unknown" otherwise. A problem in the startup phase of a folder counts as unknown, as in the language status, which keeps its icon and its details.

For Python, the list follows the cases of the Python item: "no interpreter selected" when no interpreter is selected, "unknown" when the Python side reports nothing, and else the version. Where the item adds the name of the environment, the list adds the kind in parentheses (D5).

- **Alternative: a second copy of the Robot Framework rules for the list.** The two would drift apart, and a report would say something else than the language status.

### D3: The folder

The command takes the folder it is given, which the RobotCode menu passes, else the folder of the active editor, else the only folder of the workspace, else the folder the user picks with `showWorkspaceFolderPick`; when the user cancels the pick, nothing is copied. Unlike the menu, the command doesn't require a running language server. Without any workspace folder it copies the lines that need no folder and "unknown" for the others.

- **Alternative: refuse without a language server, as the menu does.** A broken environment is when a report is needed most.

### D4: The lines

The six lines keep the order and the names of the bug template. A line for a particular setup follows the line it belongs to:

```
- VS Code Version: 1.142.0
- Editor: Cursor                              only when it isn't VS Code
- RobotCode Version: 2.8.0
- RobotCode Language Server Version: 2.7.0   only when it differs
- OS: Linux x64 6.8.0
- Remote: wsl                                 only on a remote
- Python Version: 3.13.12 (venv)
- RobotFramework Version: 7.5
- Additional tools: robotframework-robocop==6.2.0
```

- **Editor:** `vscode.env.appName` when it doesn't start with "Visual Studio Code", so that Insiders counts as VS Code.
- **RobotCode Language Server Version:** `robotCodeVersionString` of the project info when it differs from the extension's version.
- **OS:** `` `${os.type()} ${os.arch()} ${os.release()}` ``, as in VS Code's own system information. The extension runs where the workspace is, so on a remote the line names the remote's system.
- **Remote:** `vscode.env.remoteName` as VS Code names it, for example `wsl`, `ssh-remote` or `dev-container`.
- **Additional tools:** Robocop as `robotframework-robocop==<version>`, as Report Issue fills in the same field; "none" when the language server reports no Robocop; "unknown" without an answer of the language server.

### D5: No paths, no names

The Python line has the version and the kind of environment, not the interpreter's path and not the environment's name, which can be a folder or a user-chosen name. Nothing else in the list comes from a path.

### D6: The project info waits a few seconds at most

The command asks the language server for the project info only when the folder has a client, and cancels the request after five seconds; then the language server's values read "unknown". A language server that is starting thus doesn't hold up the copy.

- **Alternative: wait for the answer.** The command would hang while a language server starts or hangs, which is again a case for a report.

### D7: The confirmation

After copying, `showInformationMessage` says "Copied the environment info of <folder> to the clipboard." The clipboard shows nothing by itself.

- **Alternative: a message in the status bar.** It disappears after a few seconds and is easy to miss.

### D8: Command and menu entry

`package.json` contributes the command `robotcode.copyEnvironmentInfo` with the title "Copy Environment Info" in the category "RobotCode". The RobotCode menu gets the entry "Copy Environment Info" in Developer Tools, before Report Issue; it runs the command with the menu's folder.

## Risks / Trade-offs

- [The kind of environment reads differently with the Python Environments extension and with the older API, for example `venv` and `Venv`.] → The list shows it as the Python side reports it; a reader understands both.
- [`os.release()` gives the kernel version, for example 25.0.0 on macOS instead of 26, and 10.0.26200 on Windows 11.] → VS Code's own system information shows the same, and maintainers know it from VS Code's issue reporter.
- [Moving the texts of the language status into shared functions touches code that shows the environment problems.] → The functions keep the rules as they are, and their unit tests cover each case of D2.
