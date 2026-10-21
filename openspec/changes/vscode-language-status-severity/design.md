# Design: vscode-language-status-severity

## Context

See proposal.md for the problem. The facts below were read from the code on 2026-10-21 and seen in the isolated VS Code harness the same day.

- `updateItems` in `languageToolsManager.ts` fills the items of the language status from the project info of the running language server and from `getRobotEnvironmentState(folder)`.
- `pythonProblem` is the folder's problem when it is not one of Robot Framework: `noInterpreter`, `interpreterMissing` or `pythonTooOld` (`languageToolsManager.ts:665-666`). The detail of the Python item names exactly these problems.
- The Python item is `Information` only when the project info exists or the state is `usable` without a Python problem (`:692-696`). Without Robot Framework no language server runs and the state is `unusable`, so the item is an `Error`, although `pythonProblem` is not set and its detail says only "Python Version".
- A check that runs keeps the problem it started with (`{ ...previous, state: "checking" }`), so `pythonProblem` stays set until the check has a result.
- Harness, real ms-python.python 2026.10.0 and ms-python.vscode-python-envs 1.40.0, `.venv` with Python 3.14.8 and no Robot Framework: both items show the error icon, with the Python Environments API ("3.14.8 .venv") and with the Python extension's API ("3.14.8 .venv (venv)"). After Robot Framework was installed, neither did.

## Goals / Non-Goals

**Goals:**
- The Python item is an error exactly when its detail names a problem.

**Non-Goals:**
- No change to the Robot Framework item, the texts of the items, the environment message or the PyCharm plugin, which has no language status.

## Decisions

### D1: The severity of the Python item comes from `pythonProblem`

The Python item is an `Error` when `pythonProblem` is set, and `Information` otherwise. While the first check of a folder runs, RobotCode knows no problem, so the item shows the interpreter the Python side reports without an error, as its text and detail already do.

Alternative considered:
- **Keep the rule and also accept Robot Framework problems** (`projectInfo`, or `usable`, or a Robot Framework problem). The Python item would still be an error while the first check runs, without naming a problem.

## Risks / Trade-offs

- [The language status has no JavaScript tests.] → It is checked in the isolated VS Code harness with the real Python extensions.

## Migration Plan

Nothing for users to do. Rollback is a revert.
