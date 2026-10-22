# vscode-python-environment Specification

## Purpose

Defines how RobotCode's VS Code extension resolves the Python environment of a workspace folder, decides whether it can run Robot Framework in it, notices when the environment changes or becomes usable, and tells the user what is missing and what to do.

## Requirements

### Requirement: The environment comes from the Python side

For each workspace folder, the extension SHALL use the interpreter that the Python Environments extension reports for the folder when that extension offers its API, and the interpreter of the Python extension's API otherwise. The setting `robotcode.python` SHALL override both when it is set.

#### Scenario: Environment selected by the Python Environments extension

- **WHEN** the Python Environments extension has selected `.venv` of the folder, while the Python extension's old API still reports the system Python
- **THEN** RobotCode runs the language server, discovery and runs with `.venv`

#### Scenario: Python Environments extension switched off

- **WHEN** `python.useEnvironmentsExtension` is `false` and the Python extension's API reports a selected interpreter
- **THEN** RobotCode uses that interpreter

#### Scenario: Override setting

- **WHEN** `robotcode.python` names an interpreter for the folder
- **THEN** RobotCode uses it, whatever the Python side reports

### Requirement: Usability is decided from the API's data

The extension SHALL decide whether a folder has an interpreter and whether it is Python 3.10 or newer from the data the Python side reports, without starting Python; only when that data has no version SHALL it ask the interpreter once. The problems it SHALL tell apart are: no interpreter selected, the interpreter does not exist, Python older than 3.10, Robot Framework missing or older than 5.0.

#### Scenario: Nothing selected

- **WHEN** the Python side reports no interpreter for the folder, and with the Python extension's API its default `python` resolves to nothing
- **THEN** the folder's problem is "no interpreter selected" and no Python process is started

#### Scenario: Python too old

- **WHEN** the Python side reports Python 3.9 for the folder
- **THEN** the folder's problem is "Python older than 3.10" and no Python process is started

#### Scenario: Interpreter missing

- **WHEN** the selected interpreter no longer exists on disk
- **THEN** the folder's problem is "interpreter missing"

### Requirement: Robot Framework is checked once per environment

For an interpreter that exists and is new enough, the extension SHALL check Robot Framework with its check script, which imports the package as Python itself finds it and requires Robot Framework 5.0 or newer. The result SHALL be kept until the environment changes or a trigger of this capability asks for a new check.

#### Scenario: Robot Framework installed

- **WHEN** the environment has `robotframework` 7.5 installed
- **THEN** the folder is usable and the language server starts

#### Scenario: Robot Framework missing

- **WHEN** the environment has no `robotframework`
- **THEN** the folder's problem is "Robot Framework missing" and the language server does not start

### Requirement: A new virtual environment is picked up

When a `pyvenv.cfg` appears in a workspace folder, the extension SHALL ask the Python side to refresh its environments and resolve the folder's environment again. With the Python Environments extension, the environment it selects after the refresh SHALL be used. Without it, a virtual environment of the folder that is known or lies in the folder as `.venv` or `venv` but is not selected SHALL be offered with the action **Use .venv**, which selects it on the Python side.

#### Scenario: uv venv with the Python Environments extension

- **WHEN** the folder has Robot Framework files and a `.venv` with `robotframework` is created with `uv sync` while VS Code is open
- **THEN** within a few seconds the folder uses `.venv`, the language server starts and the notification about the missing Robot Framework is no longer needed

#### Scenario: uv venv without the Python Environments extension

- **WHEN** the same happens with `python.useEnvironmentsExtension` set to `false`
- **THEN** the notification offers **Use .venv**, and choosing it selects the environment for the folder on the Python side, after which the language server starts

### Requirement: A later Robot Framework install is noticed

While a folder's problem is a missing or too old Robot Framework, the extension SHALL run its check script every few seconds, more slowly after a while, so that a Robot Framework installed in the meantime, wherever Python finds it, starts the language server without the user doing anything. It SHALL also check again on the environment events of both APIs.

#### Scenario: pip or uv install in a terminal

- **WHEN** the user runs `uv pip install robotframework`, `pip install robotframework` or `pip install --user robotframework` for the selected interpreter, or points `PYTHONPATH` at an install
- **THEN** within a few seconds the folder becomes usable and the language server starts

#### Scenario: Package events

- **WHEN** the Python Environments extension reports a package change for the folder's environment
- **THEN** the extension checks Robot Framework again

### Requirement: One message per folder instead of a dialog

For a folder with a problem, the extension SHALL show one message per folder that stays on screen, names the folder and the problem, and offers **Select Environment**, **Create Environment**, **Retry** and, without the Python Environments extension, **Use .venv** as links, plus **Cancel**. It SHALL replace the text when the problem changes, close the message when the folder becomes usable and confirm that in a short information message, SHALL NOT show a quick pick, and nothing SHALL wait for it.

#### Scenario: Robot Framework missing

- **WHEN** the folder `shop` has Robot Framework files and its environment has no Robot Framework
- **THEN** the message says that RobotCode found a Robot Framework project in `shop` but the selected Python environment has no Robot Framework and that it has to be installed into that environment, with the links **Select Environment**, **Create Environment** and **Retry** and the button **Cancel**; the Testing view and the language status show the missing environment meanwhile

#### Scenario: Environment becomes usable

- **WHEN** the environment becomes usable while the message is shown
- **THEN** the message closes by itself, a short information message says that an environment was found, names it with its Python and Robot Framework versions and says that RobotCode is ready, the language server starts, and the language status and the Testing view update

#### Scenario: The problem changes

- **WHEN** at startup the Python side selects the folder's `.venv` shortly after RobotCode's first check found the global interpreter without Robot Framework
- **THEN** one message is shown, with the text for `.venv`, and no second one

#### Scenario: Retry

- **WHEN** the user chooses **Retry**
- **THEN** RobotCode asks the Python side to look for environments again, checks the folder again, and the message shows the time of that check when the problem remains

### Requirement: Cancel asks whether to switch RobotCode off

After **Cancel** the extension SHALL ask whether to switch RobotCode off for the folder: for this session, which ends with the window or **RobotCode: Restart Language Servers**, or for this project, which sets `robotcode.disableExtension` in the folder settings. A folder that is switched off SHALL get no language server, no discovery, no checks and no message, and the Testing view SHALL show its switched-off hint.

#### Scenario: Cancel without an answer

- **WHEN** the user chooses **Cancel** and closes the question
- **THEN** the message stays closed for this problem, the problem stays visible in the language status and the Testing view, the checks keep running, and the message comes back for a new problem

#### Scenario: Off for this session

- **WHEN** the user answers **For this session**
- **THEN** the folder gets no language server, discovery or message until the window is reloaded or **RobotCode: Restart Language Servers** runs, its run profiles disappear, and the Testing view shows the switched-off hint

#### Scenario: Off for this project

- **WHEN** the user answers **For this project**
- **THEN** `robotcode.disableExtension` is set to `true` in the folder's settings and the folder stays switched off in later sessions

### Requirement: Select and Create use the Python side

**Select Environment** and **Create Environment** SHALL be offered for every problem, unless the setting `robotcode.python` names the interpreter: then the message offers **Open Settings** instead. **Select Environment**, also behind **RobotCode: Select Python Environment** and the language status, SHALL open the Python Environments extension's picker for the folder when its API exists, else the Python extension's picker. **Create Environment** SHALL open the Python extension's create flow.

#### Scenario: Interpreter from the setting

- **WHEN** `robotcode.python` names an interpreter without Robot Framework for the folder
- **THEN** the message says that the Python environment of the setting robotcode.python has no Robot Framework, with the links **Open Settings** and **Retry**

#### Scenario: Select Environment

- **WHEN** the user chooses **Select Environment**, or runs **RobotCode: Select Python Environment**
- **THEN** the environment picker of the Python side opens for the folder, and a selection made there is used by RobotCode

### Requirement: No install action

The extension SHALL NOT offer to install Robot Framework itself, and SHALL NOT suggest a way to do it: which tool and which version a project wants, `uv sync` or `uv add`, pip, poetry, conda, a pin in `pyproject.toml` or a lock file, is the project's decision. For a missing or too old Robot Framework the message SHALL say only that it has to be installed or updated in the selected environment.

#### Scenario: The user installs with the project's tooling

- **WHEN** the notification about the missing Robot Framework is shown and the user runs `uv sync` in a terminal, which installs the pinned `robotframework` of the project into `.venv`
- **THEN** within a few seconds the folder becomes usable with that version and the language server starts, without any action in the notification

### Requirement: The language status marks the item with the problem

The Python item of RobotCode's language status SHALL be shown as an error exactly when the folder's interpreter has a problem: none is selected, it no longer exists or cannot be started, or it is older than Python 3.10. The Robot Framework item SHALL be shown as an error exactly when Robot Framework is missing or older than 5.0.

#### Scenario: Robot Framework missing

- **WHEN** the selected Python environment of the folder has Python 3.14 and no Robot Framework, and a Robot Framework file of the folder is open
- **THEN** the language status shows the Robot Framework item as an error and the Python item without one

#### Scenario: Interpreter missing

- **WHEN** the setting `robotcode.python` names an interpreter that does not exist
- **THEN** the language status shows the Python item as an error and the Robot Framework item without one

### Requirement: The Robot Framework item shows what the check knows

The Robot Framework item of the language status SHALL show the version that RobotCode's check of the environment found, also before the language server answers. While RobotCode cannot check Robot Framework, because the interpreter has a problem or the first check runs, the item SHALL show the version as unknown.

#### Scenario: Language server still starting

- **WHEN** the environment of the folder is usable with Robot Framework 7.5 and its language server has not answered yet
- **THEN** the Robot Framework item shows 7.5 without an error

#### Scenario: Interpreter missing

- **WHEN** the setting `robotcode.python` names an interpreter that does not exist
- **THEN** the Robot Framework item shows the version as unknown

### Requirement: Problems in the startup phase are provisional

For the first 15 seconds after RobotCode first looks at a workspace folder, when VS Code starts or the folder is added, a problem of its Python environment SHALL count as provisional. A provisional problem SHALL get no environment message, the Testing view SHALL keep its loading state, and the language status SHALL show its items as busy, without an error. A problem that remains after the startup phase SHALL be shown at once.

#### Scenario: Environment selected late

- **WHEN** at startup RobotCode's first check finds the global interpreter without Robot Framework, and the Python side selects the folder's `.venv` with Robot Framework 8 seconds later
- **THEN** no environment message appears, the Testing view shows no hint about the environment, the language status shows no error, and the language server starts with `.venv`

#### Scenario: Problem that lasts

- **WHEN** the selected environment of the folder still has no Robot Framework 15 seconds after VS Code started
- **THEN** the environment message, the Testing view's hint and the language status's error appear at once

#### Scenario: Problem after the startup phase

- **WHEN** VS Code has run for a minute and the user selects an environment without Robot Framework for the folder
- **THEN** the Testing view's hint and the language status's error appear at once, and the environment message a few seconds later, as before
