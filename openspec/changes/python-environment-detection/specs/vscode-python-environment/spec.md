# Spec Delta

## Purpose

Defines how RobotCode's VS Code extension resolves the Python environment of a workspace folder, decides whether it can run Robot Framework in it, notices when the environment changes or becomes usable, and tells the user what is missing and what to do.

## ADDED Requirements

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

- **WHEN** the Python side reports no interpreter for the folder
- **THEN** the folder's problem is "no interpreter selected" and no Python process is started

#### Scenario: Python too old

- **WHEN** the Python side reports Python 3.9 for the folder
- **THEN** the folder's problem is "Python older than 3.10" and no Python process is started

#### Scenario: Interpreter missing

- **WHEN** the selected interpreter no longer exists on disk
- **THEN** the folder's problem is "interpreter missing"

### Requirement: Robot Framework is checked once per environment

For an interpreter that exists and is new enough, the extension SHALL check Robot Framework by looking for the package's metadata in the environment and confirming it with its check script, which also requires Robot Framework 5.0 or newer. The result SHALL be kept until the environment changes or a trigger of this capability asks for a new check.

#### Scenario: Robot Framework installed

- **WHEN** the environment has `robotframework` 7.5 installed
- **THEN** the folder is usable and the language server starts

#### Scenario: Robot Framework missing

- **WHEN** the environment has no `robotframework`
- **THEN** the folder's problem is "Robot Framework missing" and the language server does not start

### Requirement: A new virtual environment is picked up

When a `pyvenv.cfg` appears in a workspace folder, the extension SHALL ask the Python side to refresh its environments and resolve the folder's environment again. With the Python Environments extension, the environment it selects after the refresh SHALL be used. Without it, a virtual environment of the folder that is known but not selected SHALL be offered with the action **Use .venv**, which selects it on the Python side.

#### Scenario: uv venv with the Python Environments extension

- **WHEN** the folder has Robot Framework files and a `.venv` with `robotframework` is created with `uv sync` while VS Code is open
- **THEN** within a few seconds the folder uses `.venv`, the language server starts and the notification about the missing Robot Framework is no longer needed

#### Scenario: uv venv without the Python Environments extension

- **WHEN** the same happens with `python.useEnvironmentsExtension` set to `false`
- **THEN** the notification offers **Use .venv**, and choosing it selects the environment for the folder on the Python side, after which the language server starts

### Requirement: A later Robot Framework install is noticed

While a folder's problem is "Robot Framework missing", the extension SHALL look every few seconds whether Robot Framework has appeared in the environment and SHALL run the check again when it has, so the language server starts without the user doing anything. It SHALL also check again on the environment events of both APIs.

#### Scenario: pip or uv install in a terminal

- **WHEN** the user runs `uv pip install robotframework` or `pip install robotframework` into the selected environment
- **THEN** within a few seconds the folder becomes usable and the language server starts

#### Scenario: Package events

- **WHEN** the Python Environments extension reports a package change for the folder's environment
- **THEN** the extension checks Robot Framework again

### Requirement: A notification instead of a dialog

For a folder with a problem, the extension SHALL show one non-modal notification per folder and problem that names the folder and the problem, with the actions that fit it. It SHALL NOT show a quick pick, SHALL NOT repeat the notification for the same problem, and nothing SHALL wait for an answer: discovery, the language status and the Test Explorer show the state on their own.

#### Scenario: Robot Framework missing

- **WHEN** the folder `shop` has Robot Framework files and its environment has no Robot Framework
- **THEN** a notification says that RobotCode found Robot Framework files in `shop` but no Robot Framework in the selected Python environment, with **Install Robot Framework**, **Select Environment** and **Create Environment**, and the Testing view and the language status show the missing environment meanwhile

#### Scenario: Environment becomes usable

- **WHEN** the environment becomes usable after the notification was shown
- **THEN** the language server starts, the language status and the Testing view update, and no further notification for that problem appears

#### Scenario: Dismissed

- **WHEN** the user dismisses the notification
- **THEN** nothing else changes: the problem stays visible in the language status and the Testing view, and the next check still runs on the triggers of this capability

### Requirement: Select and Create use the Python side

**Select Environment** and **Create Environment** SHALL be offered for every problem. **Select Environment**, also behind **RobotCode: Select Python Environment** and the Python item of the language status, SHALL open the environment picker of the Python Environments extension for the folder when its API exists, and the Python extension's interpreter picker otherwise. **Create Environment** SHALL open the Python extension's create flow.

#### Scenario: Select Environment

- **WHEN** the user chooses **Select Environment**, or runs **RobotCode: Select Python Environment**
- **THEN** the environment picker of the Python side opens for the folder, and a selection made there is used by RobotCode

### Requirement: Install Robot Framework uses the Python side's tooling

**Install Robot Framework** SHALL be offered only when Robot Framework is the folder's only problem. It SHALL install `robotframework` with the Python Environments extension's package API when it exists, and otherwise in a terminal with uv for a uv-made environment and with pip for any other.

#### Scenario: Install with the Python Environments extension

- **WHEN** the user chooses **Install Robot Framework** and the Python Environments API exists
- **THEN** the package is installed into the folder's environment through that API, and the folder becomes usable afterwards without further action

#### Scenario: Install without the Python Environments extension

- **WHEN** the user chooses **Install Robot Framework** for a uv-made `.venv` without the Python Environments API
- **THEN** a terminal runs `uv pip install --python <interpreter> robotframework`, and the folder becomes usable when the install is done
