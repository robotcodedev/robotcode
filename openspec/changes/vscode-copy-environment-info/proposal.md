# Proposal

## Why

A report about RobotCode, Robot Framework or Robocop needs the versions in use: VS Code, RobotCode, the operating system, Python, Robot Framework and Robocop. Today users collect them from several places. The language status shows most of them, but its text can't be selected or copied (#260). **Report Issue** fills in some of them, but only for an issue on GitHub through VS Code's issue reporter; for a forum post, a chat or an issue of another project, nothing copies them.

## What Changes

- A new command **RobotCode: Copy Environment Info** copies the versions of a workspace folder to the clipboard. The lines of the list are named like the fields of RobotCode's bug report template: VS Code Version, RobotCode Version, OS, Python Version, RobotFramework Version and Additional tools.
- Lines that matter only in some setups appear only there:
  - the editor, when it isn't VS Code, for example Cursor or VSCodium;
  - the remote, for example WSL or SSH;
  - the language server's RobotCode version, when it differs from the extension's.
- The list names no paths, neither the interpreter's nor the project's, because they often contain user names. The Python line names the version and the kind of environment.
- The command is in the Command Palette and in the RobotCode menu next to **Report Issue**. The menu opens from the RobotCode item of the language status, so the versions are two clicks away from there.
- From the Command Palette, the command also works when the folder's language server isn't running, for example because its environment is broken. A version that is missing reads "unknown" or "not installed".
- A short message confirms that the list was copied.
- The troubleshooting page of the VS Code guide explains the command, and its screenshot of the menu shows the new entry.
- Robotidy, which #260 asks for, isn't part of the list: RobotCode no longer supports it, and Robocop formats.

## Capabilities

### New Capabilities
- `vscode-environment-info`: copying the versions of a workspace folder in VS Code for a report.

### Modified Capabilities
- `vscode-user-guide`: the troubleshooting page explains how to copy the versions.

## Impact

- **Code:** a new module that builds the list in `vscode-client/extension/`; the command and the menu entry in `vscode-client/extension/languageToolsManager.ts`; the command in `package.json`.
- **Tests:** unit tests of the list in `vscode-client/test/`.
- **Docs:** `docs/src/content/docs/guides/vscode/troubleshooting.mdx` and the screenshots `troubleshooting-tool-menu-light.png` and `troubleshooting-tool-menu-dark.png`.
- **Unchanged:** **Report Issue**, the language status items and the language server.
- **PyCharm:** not part of this change; a similar action there would be a change of its own.
