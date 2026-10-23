# Tasks

## 1. The list (D1, D2, D4, D5)

- [ ] 1.1 Add `vscode-client/extension/environmentInfo.ts` with the function that builds the list from the gathered values (D1, D4, D5) and the function for the Robot Framework text (D2), and let `updateItems` in `languageToolsManager.ts` use the latter for the Robot Framework item. Unit tests in `vscode-client/test/environmentInfo.test.ts`:
  - the six lines of the plain setup, in the order and with the names of the bug template;
  - each extra line only with its setup: Editor for Cursor but not for "Visual Studio Code - Insiders", Remote, and the language server's RobotCode version only when it differs;
  - Additional tools with Robocop, with "none" and with "unknown";
  - Python with and without the kind of environment, with no interpreter and unknown;
  - the Robot Framework text for each case of D2, the startup phase included.

  Verify with `npm run lint` and `xvfb-run -d npm test`.

## 2. The command (D3, D6, D7, D8)

- [ ] 2.1 Register `robotcode.copyEnvironmentInfo` in `languageToolsManager.ts` and contribute it in `package.json` (D8): the folder as in D3, the values as in D4, the project info only from an existing client and for five seconds at most (D6), the copy with its confirmation (D7), and the entry "Copy Environment Info" before Report Issue in the RobotCode menu (D8). Verify with `npm run lint` and `xvfb-run -d npm test`.

## 3. Documentation

- [ ] 3.1 In `docs/src/content/docs/guides/vscode/troubleshooting.mdx`, explain "RobotCode: Copy Environment Info": that it copies the versions of the workspace folder as a list for an issue, a forum post or a chat, and that the RobotCode menu offers it too. Add the entry to the alt text of the menu screenshot, and take `troubleshooting-tool-menu-light.png` and `troubleshooting-tool-menu-dark.png` again with `playground/robotcode-demo/vscode/guide-troubleshooting.js` in the VS Code harness. Verify with `npm run docs:build` and by looking at both screenshots.

## 4. Integration

- [ ] 4.1 In the VS Code harness with the real Python extensions, read the clipboard after each step and check:
  - **Show Tool Menu** at the RobotCode item of the language status, then **Copy Environment Info**: the list of the active editor's folder, and the confirmation;
  - the command from the Command Palette in a workspace with two folders: the folder of the active editor; without an editor the pick, and nothing copied when the pick is cancelled;
  - a folder whose environment has no Robot Framework, so that its language server doesn't run: `not installed` and `unknown`;
  - no path in the list, with the environment in the harness's home directory;
  - the Robot Framework item of the language status shows the same texts as before: a version, and "not installed" for the folder without Robot Framework.

## Workflow follow-up

- Archive the change with its delta specs synced: the new main spec `vscode-environment-info` and the modified requirement in `vscode-user-guide`.
- On the maintainer's request, comment on and close #260 once the command is released.
