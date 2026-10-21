# Tasks: vscode-language-status-severity

## 1. Language status

- [x] 1.1 In `updateItems` of `vscode-client/extension/languageToolsManager.ts`, show the Python item as an error only when `pythonProblem` is set (design D1). Verify with `npm run compile` and `npm run lint`.

## 2. Verification

- [x] 2.1 Check in the isolated VS Code harness with the real Python extensions: a `.venv` without Robot Framework shows only the Robot Framework item as an error, in both API modes; `robotcode.python` set to an interpreter that does not exist shows the Python item as an error; a usable `.venv` shows neither. Verify by recording the results in design.md.

## 3. Review corrections

- [x] 3.1 Show the Python item as an error also when the Python side reports no interpreter (design D1). Verify with `npm run compile` and `npm run lint`.
- [x] 3.2 Give the Robot Framework item the version of the environment check when the folder is usable, "unknown" while Robot Framework cannot be checked, and an error only for a missing or too old Robot Framework (design D2). Verify with `npm run compile` and `npm run lint`.
- [x] 3.3 Check in the harness the four cases of 2.1 again, with the Robot Framework item "unknown" and without an error when `robotcode.python` names an interpreter that does not exist, and a usable folder whose language server has not answered yet, whose Robot Framework item shows the version without an error. Verify by recording the results in design.md.
