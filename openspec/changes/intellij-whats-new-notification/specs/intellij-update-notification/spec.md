# Spec Delta

## Purpose

Defines when the IntelliJ plugin tells the user that RobotCode was updated and offers to show what's new, and how the user opens the news at any time, so that users of PyCharm and IntelliJ IDEA learn about new releases as VS Code users do, without being interrupted by every dev build.

## ADDED Requirements

### Requirement: The plugin announces a new release version

When a project becomes a Robot Framework project, because it contains Robot Framework files or a `robot.toml` or because one is opened, and the plugin runs a release version other than the one it noted last, also when it noted none yet, the plugin SHALL note the version and show a notification that names it, unless "Show whats new on update" is off. The notification's action "What's New?" SHALL open the news about the latest release in the IDE's web browser.

#### Scenario: Update to a release

- **WHEN** the IDE updated RobotCode from 2.7.0 to 2.8.0, and a project with Robot Framework files opens
- **THEN** a notification says that RobotCode has been updated to v2.8.0, and its action "What's New?" opens `https://robotcode.io/news/latest/` in the web browser

#### Scenario: First start after the installation

- **WHEN** RobotCode 2.8.0 was installed in an IDE that never ran RobotCode, and a project with Robot Framework files opens
- **THEN** the notification for v2.8.0 appears

#### Scenario: Update without restarting the IDE

- **WHEN** the IDE updates RobotCode to 2.8.0 without a restart while a project with Robot Framework files is open
- **THEN** the notification for v2.8.0 appears

#### Scenario: Project without Robot Framework files

- **WHEN** the IDE updated RobotCode to 2.8.0, and a project without Robot Framework files and without a `robot.toml` opens
- **THEN** no notification appears, and the notification for v2.8.0 appears in the next project that becomes a Robot Framework project

#### Scenario: Notification switched off

- **WHEN** "Show whats new on update" is off, the IDE updated RobotCode to 2.8.0, a project with Robot Framework files opens, and the user turns the setting on afterwards
- **THEN** no notification for v2.8.0 appears

### Requirement: One notification per version

The plugin SHALL show the notification for a version at most once per IDE installation, whatever the number of open projects, and SHALL note the version for the IDE installation, not for a project.

#### Scenario: Several projects

- **WHEN** the IDE updated RobotCode to 2.8.0 and opens two projects with Robot Framework files
- **THEN** exactly one notification for v2.8.0 appears

#### Scenario: Restart after the notification

- **WHEN** the notification for v2.8.0 appeared, and the IDE restarts with the same projects
- **THEN** no notification appears

### Requirement: Dev builds aren't announced

When the plugin runs a dev build, a version with a pre-release part such as `2.8.0-dev.508`, it SHALL NOT show the notification. It SHALL still note that version as the one it noted last.

#### Scenario: Update between dev builds

- **WHEN** the IDE updated RobotCode from 2.8.0-dev.483 to 2.8.0-dev.508, and a project with Robot Framework files opens
- **THEN** no notification appears

#### Scenario: Update from a release to a dev build

- **WHEN** the IDE updated RobotCode from 2.7.0 to 2.8.0-dev.508, and a project with Robot Framework files opens
- **THEN** no notification appears

#### Scenario: Update from a dev build to a release

- **WHEN** the IDE updated RobotCode from 2.8.0-dev.508 to 2.8.0, and a project with Robot Framework files opens
- **THEN** the notification for v2.8.0 appears

### Requirement: Show What's New action

The menu Tools | RobotCode and the menu of the RobotCode status bar widget SHALL offer the action "Show What's New", which opens the news about the latest release in the IDE's web browser, as the notification's action does. The action SHALL be available in every project, also while RobotCode is switched off for it.

#### Scenario: Action in the Tools menu

- **WHEN** the user chooses Tools | RobotCode | Show What's New
- **THEN** the web browser opens `https://robotcode.io/news/latest/`

#### Scenario: Action in the status bar widget's menu

- **WHEN** the user opens the menu of the RobotCode status bar widget
- **THEN** it offers "Show What's New"

#### Scenario: RobotCode switched off

- **WHEN** "Disable extension" is on for the project, and the user chooses Tools | RobotCode | Show What's New
- **THEN** the web browser opens `https://robotcode.io/news/latest/`
