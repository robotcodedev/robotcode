# vscode-project-detection Specification

## Purpose

Defines which workspace folders the VS Code extension treats as Robot Framework projects and takes up, so that a folder it has not taken up gets nothing that needs Python: no check of its environment, no polling, no environment message and no language server, also while RobotCode is active in the window.

## Requirements

### Requirement: Robot Framework projects are detected

The extension SHALL treat a workspace folder as a Robot Framework project when it has a `robot.toml` or `.robot.toml`, a `pyproject.toml` or `requirements.txt` that depends on Robot Framework or RobotCode, or a Robot Framework file outside the skipped folders. It SHALL decide this from the files alone, without starting Python. Skipped are files and folders whose names start with `.` or `_`, and folders named `CVS`, `node_modules`, `target`, `build`, `dist` or `venv`.

#### Scenario: TypeScript project

- **WHEN** a workspace folder contains only `package.json`, `README.md`, `.gitignore` and TypeScript files
- **THEN** it is no Robot Framework project

#### Scenario: Robot Framework file in an installed package

- **WHEN** the only Robot Framework file of a workspace folder is `node_modules/fake-pkg/fixtures/example.robot`
- **THEN** it is no Robot Framework project

#### Scenario: Robot Framework file in the folder

- **WHEN** a workspace folder contains `tests/example.robot`
- **THEN** it is a Robot Framework project

#### Scenario: Project declared by its configuration

- **WHEN** a workspace folder has no Robot Framework file, and has a `robot.toml`, a `pyproject.toml` that lists `robotframework>=7.0` as a dependency, or a `requirements.txt` that lists `robotcode`
- **THEN** it is a Robot Framework project

#### Scenario: Robot Framework installed for the folder's interpreter

- **WHEN** a workspace folder contains only `package.json`, `README.md` and TypeScript files, and its Python interpreter has Robot Framework installed
- **THEN** it is no Robot Framework project

### Requirement: RobotCode takes up Robot Framework folders

The extension SHALL take up a workspace folder that is a Robot Framework project when VS Code starts, when the folder is added, or when a file change makes it one, and a folder in which a Robot Framework document is opened, also from a skipped folder. Taking up a folder SHALL check its Python environment, show the environment message when it is unusable, and start its language server when it is usable. A folder that is switched off for RobotCode SHALL NOT be taken up.

#### Scenario: Robot Framework project at startup

- **WHEN** VS Code opens a workspace folder with `tests/example.robot` and a Python environment with Robot Framework
- **THEN** the folder's language server starts before any Robot Framework document is opened

#### Scenario: Robot Framework project without Robot Framework in its environment

- **WHEN** VS Code opens a workspace folder with `tests/example.robot`, and its Python environment has no Robot Framework
- **THEN** the environment message says that Robot Framework is missing, at the latest when the startup phase ends

#### Scenario: Large project

- **WHEN** the search for Robot Framework files in a workspace folder without a configuration file takes longer than five seconds, and finds `tests/example.robot`
- **THEN** the folder's language server starts when the search ends, without a Robot Framework document being opened

#### Scenario: Robot Framework document from a skipped folder

- **WHEN** `node_modules/fake-pkg/fixtures/example.robot` is opened in a workspace folder that is no Robot Framework project, and the folder's Python environment has Robot Framework
- **THEN** the folder's language server starts

### Requirement: Folders not taken up stay quiet

For a workspace folder that RobotCode has not taken up, the extension SHALL NOT check the Python environment, poll for Robot Framework, show the environment message or start a language server, also not after the folder's Python environment changes. A command that the user runs for the folder and that needs only its Python environment, such as the REPL, SHALL check the environment when it runs, without polling afterwards.

#### Scenario: RobotCode activated in a folder without Robot Framework

- **WHEN** RobotCode is activated in a workspace folder that is no Robot Framework project, because its `README.md` is opened or a debug session starts, and the folder's Python interpreter has no Robot Framework
- **THEN** no language server starts, RobotCode starts no Python process for the folder, and no RobotCode message appears, also minutes later

#### Scenario: Robot Framework installed later

- **WHEN** Robot Framework is then installed for the folder's interpreter, or an interpreter with Robot Framework is selected for the folder
- **THEN** no language server starts for the folder

#### Scenario: REPL in a folder without Robot Framework

- **WHEN** the user starts the Robot REPL for that folder while its interpreter has no Robot Framework
- **THEN** RobotCode says that Robot Framework is missing, and starts no Python process for the folder afterwards

### Requirement: File changes are noticed

When a `robot.toml`, `.robot.toml`, `pyproject.toml` or `requirements.txt` changes, or a Robot Framework file or a folder is created outside the skipped folders, in a workspace folder that is not a project RobotCode has taken up, the extension SHALL detect again whether it is a Robot Framework project, and take it up when it is. In a folder taken up, a change of `robot.toml`, `.robot.toml`, `pyproject.toml`, `robocop.toml`, `.gitignore` or `.robotignore` SHALL restart its language server.

#### Scenario: Changed .gitignore in a folder without Robot Framework

- **WHEN** RobotCode is active in a workspace folder that contains only `package.json`, `README.md`, `.gitignore` and TypeScript files, because `README.md` was opened, the folder's Python interpreter has no Robot Framework, and `.gitignore` is changed
- **THEN** no language server starts, RobotCode's output channel shows no check of the folder's Python environment, and no RobotCode message appears

#### Scenario: Changed .gitignore in a Robot Framework project

- **WHEN** `.gitignore` is changed in a workspace folder with suite files whose language server runs
- **THEN** the language server restarts and the tests are read again

#### Scenario: robot.toml created

- **WHEN** a `robot.toml` is created in the folder of the first scenario
- **THEN** the folder is taken up, and the environment message says that Robot Framework is missing

#### Scenario: Robot Framework dependency added

- **WHEN** a `requirements.txt` that lists `robotframework` is created in the folder of the first scenario
- **THEN** the folder is taken up, and the environment message says that Robot Framework is missing

#### Scenario: Robot Framework file created

- **WHEN** `tests/example.robot` is created in the folder of the first scenario, and nobody opens it
- **THEN** the folder is taken up, and the environment message says that Robot Framework is missing

#### Scenario: Files created in a skipped folder

- **WHEN** `npm install` creates files, among them `node_modules/fake-pkg/fixtures/example.robot`, in the folder of the first scenario
- **THEN** the folder is not taken up and no RobotCode message appears
