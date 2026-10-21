# Tasks: vscode-language-status-severity

## 1. Language status

- [ ] 1.1 In `updateItems` of `vscode-client/extension/languageToolsManager.ts`, show the Python item as an error only when `pythonProblem` is set (design D1). Verify with `npm run compile` and `npm run lint`.

## 2. Verification

- [ ] 2.1 Check in the isolated VS Code harness with the real Python extensions: a `.venv` without Robot Framework shows only the Robot Framework item as an error, in both API modes; `robotcode.python` set to an interpreter that does not exist shows the Python item as an error; a usable `.venv` shows neither. Verify by recording the results in design.md.
