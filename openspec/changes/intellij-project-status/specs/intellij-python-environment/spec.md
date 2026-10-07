# Spec Delta

## Purpose

Defines which Python interpreter the IntelliJ plugin uses for RobotCode, which interpreters it accepts, how and when it checks them, and what it tells the user about an interpreter it cannot use.

## ADDED Requirements

### Requirement: The banner offers the next step

The banner that a Robot file shows for an interpreter RobotCode cannot use SHALL offer:

- "Configure Python Interpreter...", which opens the Python Interpreter settings, also in an IDE with a language pack;
- "Retry", which checks the interpreter again and starts RobotCode when it is usable now;
- "Disable RobotCode for This Project", which switches RobotCode off for the project.

#### Scenario: Configure the interpreter

- **WHEN** the banner says that Robot Framework is not installed and the user clicks "Configure Python Interpreter..."
- **THEN** the Python Interpreter settings of the project open

#### Scenario: Retry after installing

- **WHEN** the user installs Robot Framework with the pip command from the banner in a terminal and clicks "Retry"
- **THEN** the banner disappears and the language server starts

#### Scenario: Disable from the banner

- **WHEN** the user clicks "Disable RobotCode for This Project"
- **THEN** the setting "Enable RobotCode for this project" is off, and the banner, the run markers and the language server are gone

### Requirement: Hiding the banner

The banner for an interpreter RobotCode cannot use SHALL offer a close button, which hides the banner in this project until the IDE is restarted. While RobotCode is switched off for the project, no banner SHALL appear.

#### Scenario: Close the banner

- **WHEN** the user clicks the banner's close button
- **THEN** no Robot file of the project shows the banner again until the IDE is restarted

### Requirement: The banner shows how to install Robot Framework

When Robot Framework is missing or older than 5.0, the banner SHALL show the pip command that installs or upgrades it for the project's interpreter. The plugin SHALL NOT install packages itself.

#### Scenario: Old Robot Framework in the banner

- **WHEN** the project's interpreter has Robot Framework 4.1
- **THEN** the banner shows the pip command that upgrades Robot Framework for that interpreter
