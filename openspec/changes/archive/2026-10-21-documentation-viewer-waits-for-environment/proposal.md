# Proposal: documentation-viewer-waits-for-environment

## Why

After a restart of VS Code, a restored Documentation Viewer generates its page right away, with the interpreter the Python side reports at that moment. At startup that can be no interpreter or the wrong one, because the Python side selects the folder's environment only later, in large workspaces several seconds later. The generation then fails, and the viewer shows an error with a Retry button instead of its kept page, which it looks up with that interpreter. A few seconds later the environment is ready, but nothing makes the viewer try again.

## What Changes

- **Generation waits for the environment.** A viewer generates a page only when RobotCode's environment check finds the Python environment of its folder usable, the same check that the language server waits for, and it generates with the interpreter of that check.
- **Waiting instead of an error.** While the environment cannot run Robot Framework, the viewer says that it waits for the folder's Python environment, with its progress bar running. Only when the problem has lasted 30 seconds does it show it as an error, without a Retry button. A folder for which RobotCode is switched off gets that error at once. The refresh button checks the environment again.
- **The page loads by itself.** When the folder's environment becomes usable, a waiting viewer loads its page without any action. A viewer whose page came from another interpreter loads it again, so a viewer also follows when the user selects another environment for the folder.
- **The last page until the check is done.** Each history entry remembers the kept page it showed last. Until the environment of the folder is checked, the viewer shows that page, so a restored viewer shows its page at once again.
- **Generation errors stay as they are.** A generation that fails in a usable environment, for example because the import of a library fails, still shows the error, and the Retry button when no page is kept.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `vscode-documentation-viewer`: generation waits for a usable Python environment and starts by itself when the environment becomes usable; a viewer says that it waits, and shows the problem as an error only when it lasts; a viewer follows a change of its folder's interpreter; until the environment is checked, a history entry shows the page it showed last.

## Impact

- **Code:**
  - `vscode-client/extension/documentationViewer.ts`: waits for the environment check, says that it waits or shows the environment error, loads again on environment events, and reads the remembered page.
  - `vscode-client/extension/index.ts`: passes the `LanguageClientsManager` to the viewer manager.
  - `vscode-client/extension/pythonmanger.ts`: `executeRobotCode` takes the interpreter to run as an optional argument.
  - `vscode-client/documentationViewer/protocol.ts`, `app.tsx` and `viewer.css`: the remembered page in history entries, the waiting note, the environment error and the reload message.
- **Docs:** `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`, the paragraph on kept pages and failed generations.
- **Tests:** The VS Code viewer has no JavaScript tests. It is checked in the isolated VS Code harness with the real Python extensions, before and after the change.
- **Users:** No new settings. A viewer saved by an older version has no remembered page, so at the first restart after the update it shows the progress bar until the environment is checked.
