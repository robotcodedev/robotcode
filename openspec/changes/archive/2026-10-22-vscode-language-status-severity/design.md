# Design: vscode-language-status-severity

## Context

See proposal.md for the problem. The facts below were read from the code on 2026-10-21 and seen in the isolated VS Code harness the same day.

- `updateItems` in `languageToolsManager.ts` fills the items of the language status from the project info of the running language server and from `getRobotEnvironmentState(folder)`.
- `pythonProblem` is the folder's problem when it is not one of Robot Framework: `noInterpreter`, `interpreterMissing` or `pythonTooOld` (`languageToolsManager.ts:665-666`). The detail of the Python item names exactly these problems. Its text is "not installed" when the Python side reports no interpreter (`getPythonInfo`, `pythonmanger.ts:653`).
- The Python item is `Information` only when the project info exists or the state is `usable` without a Python problem (`:692-696`). Without Robot Framework no language server runs and the state is `unusable`, so the item is an `Error`, although `pythonProblem` is not set and its detail says only "Python Version".
- The Robot Framework item takes its version only from the project info, else "not installed" or "<version> (not supported)", and is an `Error` whenever there is no project info (`:631-649`). So it says "not installed" as an error when the interpreter has the problem, and, read from the code, while the language server of a usable folder starts, although the check found the version (`RobotEnvironmentState.robotVersion`).
- A check that runs keeps the problem it started with (`{ ...previous, state: "checking" }`), so a known problem stays set until the check has a result.
- Harness, real ms-python.python 2026.10.0 and ms-python.vscode-python-envs 1.40.0, `.venv` with Python 3.14.8 and no Robot Framework: both items show the error icon, with the Python Environments API ("3.14.8 .venv") and with the Python extension's API ("3.14.8 .venv (venv)"). After Robot Framework was installed, neither did.

## Goals / Non-Goals

**Goals:**
- Each of the two items is an error exactly when its own part of the environment has a problem.
- The Robot Framework item shows what RobotCode knows about Robot Framework.

**Non-Goals:**
- No change to the environment message, the other items of the language status, or the PyCharm plugin, which has no language status.

## Decisions

### D1: The Python item is an error for a problem of the interpreter

The Python item is an `Error` when `pythonProblem` is set, or when the Python side reports no interpreter, which its text shows as "not installed". Otherwise it is `Information`, also while the first check of a folder runs.

Alternatives considered:
- **Keep the rule and also accept Robot Framework problems** (`projectInfo`, or `usable`, or a Robot Framework problem). The Python item would still be an error while the first check runs, without naming a problem.
- **Only `pythonProblem`.** This was the first plan. Before the first check's result, and in a switched-off folder, which gets no check, the item said "not installed" without an error (review).

### D2: The Robot Framework item follows the check

- **Text:** the version of the project info; else, when the folder is usable, the version the check found; else "not installed" for a missing Robot Framework and "<version> (not supported)" for one older than 5.0, as before; else "unknown", because the interpreter has a problem or the first check runs.
- **Severity:** `Error` exactly for a missing or too old Robot Framework, `Information` otherwise.
- The detail stays as it is: it names the two Robot Framework problems.

Alternative considered:
- **"not installed" while nothing is known.** It states something RobotCode has not checked.

## Risks / Trade-offs

- [The language status has no JavaScript tests.] → It is checked in the isolated VS Code harness with the real Python extensions.

## Migration Plan

Nothing for users to do. Rollback is a revert.

## Verification

First round, harness of 2026-10-21 (task 2.1, before the review corrections): isolated VS Code 1.142.0, the real ms-python.python 2026.10.0 and ms-python.vscode-python-envs 1.40.0, RobotCode from the working tree, the language status hover of an open Robot Framework file:
- **`.venv` without Robot Framework, Python extension's API** (`python.useEnvironmentsExtension: false`): "not installed – Robot Framework Version - not installed in the Python environment" with the error icon, "3.14.8 .venv (venv) – Python Version" without one.
- **The same with the Python Environments API:** the Robot Framework item with the error icon, "3.14.8 .venv – Python Version" without one.
- **`robotcode.python` set to `/opt/nowhere/bin/python`:** "unknown custom – Python Version - the interpreter no longer exists or cannot be started" with the error icon. The Robot Framework item keeps its error icon too, as before, since no language server runs (non-goal).
- **`.venv` with Robot Framework 7.5:** no item with the error icon.

After the review corrections (task 3.3), same harness:
- **`.venv` without Robot Framework**, with the Python extension's API and with the Python Environments API: the Robot Framework item "not installed" with the error icon, the Python item ("3.14.8 .venv (venv)" or "3.14.8 .venv") without one.
- **`robotcode.python` set to `/opt/nowhere/bin/python`:** the Python item "unknown custom – Python Version - the interpreter no longer exists or cannot be started" with the error icon, the Robot Framework item "unknown" without one.
- **Usable `.venv`:** no item with the error icon, the Robot Framework item "7.5".
- **Usable environment whose language server has not answered yet:** `robotcode.python` named a wrapper of the `.venv` interpreter that starts it after 10 s. Read right after the check found the folder usable, while the log said only "client … starting": the Robot Framework item "7.5" with the busy indicator and without the error icon, "3.14.8 custom" for Python.
