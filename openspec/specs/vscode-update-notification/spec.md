# vscode-update-notification Specification

## Purpose

Defines when the VS Code extension tells the user that it was updated and offers to show what's new, so that users learn about new releases without being interrupted by every dev build.

## Requirements

### Requirement: The extension announces a new release version

When the extension starts in a release version other than the one it last started in, it SHALL show a notification that names the new version and offers to open the news about the latest release, unless the setting `robotcode.showWhatsNewOnUpdate` is off.

#### Scenario: Update to a release

- **WHEN** VS Code updated the extension from 2.7.0 to 2.8.0, and the extension starts
- **THEN** a notification says that RobotCode has been updated to v2.8.0, and its button "What's New?" opens the news about the latest release

#### Scenario: Notification switched off

- **WHEN** the setting `robotcode.showWhatsNewOnUpdate` is off, and VS Code updated the extension to a new release
- **THEN** no notification appears

### Requirement: Dev builds aren't announced

When the extension starts in a dev build, a version whose patch number is 100000 or more, it SHALL NOT show the notification. It SHALL still remember that version as the one it last started in.

#### Scenario: Update between dev builds

- **WHEN** VS Code updated the extension from 2.7.100498 to 2.7.100499, and the extension starts
- **THEN** no notification appears

#### Scenario: Update from a release to a dev build

- **WHEN** VS Code updated the extension from 2.7.0 to 2.7.100499, and the extension starts
- **THEN** no notification appears

#### Scenario: Update from a dev build to a release

- **WHEN** VS Code updated the extension from 2.7.100499 to 2.8.0, and the extension starts
- **THEN** the notification for v2.8.0 appears
