# vscode-update-notification Specification

## Purpose

Defines when the VS Code extension tells the user that it was updated and offers to show what's new, so that users learn about new releases without being interrupted by every dev build.

## Requirements

### Requirement: The extension announces a new release version

When the extension runs a release version other than the one it noted last, it SHALL note the version and show a notification that names it and offers to open the news about the latest release, as soon as a workspace folder is a Robot Framework project or has an open Robot Framework document, at startup or later in the session. With the setting `robotcode.showWhatsNewOnUpdate` off, it SHALL note the version without a notification.

#### Scenario: Update to a release

- **WHEN** VS Code updated the extension from 2.7.0 to 2.8.0, and a workspace folder with Robot Framework files opens
- **THEN** a notification says that RobotCode has been updated to v2.8.0, and its button "What's New?" opens the news about the latest release

#### Scenario: Notification switched off

- **WHEN** the setting `robotcode.showWhatsNewOnUpdate` is off, VS Code updated the extension to a new release, a workspace folder with Robot Framework files opens, and the setting is turned on afterwards
- **THEN** no notification for that release appears

#### Scenario: Folder without Robot Framework

- **WHEN** VS Code updated the extension to 2.8.0, and RobotCode is activated in a workspace folder that is no Robot Framework project because its `README.md` is opened
- **THEN** no notification appears

#### Scenario: Robot Framework document opened later

- **WHEN** a Robot Framework file is then created in that folder and opened
- **THEN** the notification for v2.8.0 appears

#### Scenario: Next window with a Robot Framework project

- **WHEN** the window of "Folder without Robot Framework" is closed without a Robot Framework document being opened, and VS Code later opens a workspace folder with Robot Framework files
- **THEN** the notification for v2.8.0 appears

### Requirement: Dev builds aren't announced

When the extension starts in a dev build, a version whose patch number is 100000 or more, it SHALL NOT show the notification. It SHALL still note that version when it starts, also in a window without a Robot Framework project.

#### Scenario: Update between dev builds

- **WHEN** VS Code updated the extension from 2.7.100498 to 2.7.100499, and the extension starts
- **THEN** no notification appears

#### Scenario: Update from a release to a dev build

- **WHEN** VS Code updated the extension from 2.7.0 to 2.7.100499, and the extension starts
- **THEN** no notification appears

#### Scenario: Update from a dev build to a release

- **WHEN** VS Code updated the extension from 2.7.100499 to 2.8.0, and a workspace folder with Robot Framework files opens
- **THEN** the notification for v2.8.0 appears
