# Spec Delta

## Purpose

Defines how the IntelliJ plugin runs the RobotCode language server: when it starts, how it is connected, stopped and restarted, what it receives at start, where its output goes, and how users control and observe it.

## ADDED Requirements

### Requirement: RobotCode can be switched off per project

The "Robot Framework" settings page SHALL offer "Enable RobotCode for this project", on by default and stored for the current user only, not in the project's shared settings. Turning the setting on SHALL start RobotCode as at project opening.

#### Scenario: After an IDE restart

- **WHEN** the IDE is restarted after RobotCode was switched off for the project
- **THEN** no robotcode process starts for the project, the project's `.idea/workspace.xml` holds the setting, and `.idea/robotcodeSettings.xml` does not

#### Scenario: Switching RobotCode on

- **WHEN** RobotCode is switched off for the project and the user checks "Enable RobotCode for this project" and applies
- **THEN** RobotCode starts as it does when the project is opened

### Requirement: A project with RobotCode switched off

While the setting "Enable RobotCode for this project" is off, the project SHALL get no language server, no test discovery, no run markers, no run configurations from the editor or the Project view context, and no banner on Robot files, and the Language Servers tool window SHALL show the RobotCode server as disabled.

#### Scenario: Switching RobotCode off

- **WHEN** the user unchecks "Enable RobotCode for this project" and applies
- **THEN** the language server stops, the run markers and the banner disappear, and the Language Servers tool window shows the server as disabled

### Requirement: RobotCode in the Language Servers tool window

Enabling the RobotCode server in the Language Servers tool window SHALL turn the setting "Enable RobotCode for this project" on. Disabling it there, and LSP4IJ's own disable after repeated failed starts, SHALL keep the server off until RobotCode is restarted or the project is opened again, without changing the setting. The plugin's own stops and restarts SHALL NOT change whether the server is enabled.

#### Scenario: Enabling in the Language Servers tool window

- **WHEN** RobotCode is switched off and the user enables the RobotCode server in the Language Servers tool window
- **THEN** the setting is on again and the language server starts

#### Scenario: Repeated failed starts

- **WHEN** LSP4IJ disables the server after repeated failed starts
- **THEN** the plugin does not enable it again on its own, the setting stays on, and Restart RobotCode Language Server starts the server again

### Requirement: Status bar widget

In a project that uses Robot Framework, the status bar SHALL show a RobotCode widget. While the language server runs, its text SHALL name the Robot Framework version and the selected configuration profiles, for example "RF 7.5 · dev", and its tooltip SHALL list the RobotCode, Robot Framework, Robocop and Python versions, the interpreter, and the profiles, or that the `default-profiles` of robot.toml apply.

#### Scenario: Running project with a profile

- **WHEN** the language server runs with Robot Framework 7.5 and the profile `dev` is selected
- **THEN** the widget shows "RF 7.5 · dev", and its tooltip lists the RobotCode, Robot Framework, Robocop and Python versions and the interpreter

#### Scenario: Project without Robot Framework files

- **WHEN** a project without Robot Framework files is open
- **THEN** the status bar shows no RobotCode widget

### Requirement: States of the status bar widget

While the interpreter is not usable, the RobotCode widget SHALL show an error state whose tooltip gives the message of the environment check; while RobotCode is switched off for the project, it SHALL say so.

#### Scenario: Unusable interpreter

- **WHEN** the project's interpreter has no Robot Framework
- **THEN** the widget shows an error state whose tooltip says that Robot Framework is not installed

### Requirement: Actions of the status bar widget

A click on the RobotCode widget SHALL open the RobotCode actions: Select Configuration Profiles..., Configure Python Interpreter..., Restart RobotCode Language Server, Clear Cache and Restart RobotCode Language Server and Show Language Server Log, and, while RobotCode is switched off, an action that enables it for the project. Configure Python Interpreter... and Show Language Server Log SHALL also be available under Tools | RobotCode.

#### Scenario: Actions of the widget

- **WHEN** the user clicks the widget and chooses each action in turn
- **THEN** each action runs: the profile list opens, the Python Interpreter settings open, the server restarts, the cache is cleared and the server restarts, and the Language Servers tool window opens

### Requirement: The status bar widget does not make the IDE wait

The RobotCode widget SHALL take its versions from the running language server in the background and SHALL NOT make the IDE wait.

#### Scenario: Language server busy

- **WHEN** the language server does not answer the request for its versions at once
- **THEN** the IDE does not wait for it, and the widget shows the versions once they arrive

### Requirement: Code actions finish without error notifications

Every RobotCode code action that IntelliJ offers SHALL complete without an error notification. When a code action asks the editor to show a range after its edit, the plugin SHALL open the file that contains the range, select the range, and start renaming at it when the code action asks for that, after the edit has been applied.

#### Scenario: Create Keyword

- **WHEN** the user applies the quick fix "Create Keyword" to a call of an unknown keyword
- **THEN** the new keyword is added, its text is selected in the file that received it, and no error notification appears

#### Scenario: Extract keyword

- **WHEN** the user selects keyword calls and applies "Extract keyword"
- **THEN** the calls are replaced by a call of the new keyword, and the rename of the new keyword's name starts

#### Scenario: Documentation actions

- **WHEN** the user opens the intention list on a keyword call or a library import
- **THEN** it offers no documentation action that the plugin cannot carry out, such as "Open Documentation"
