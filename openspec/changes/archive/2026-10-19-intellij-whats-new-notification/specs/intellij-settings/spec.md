# Spec Delta

## ADDED Requirements

### Requirement: Show whats new on update on the General page

The General page SHALL show the checkbox "Show whats new on update", for VS Code's `robotcode.showWhatsNewOnUpdate`, on by default. Its text SHALL say that it shows a notification with a link to the news when RobotCode was updated, and that it applies to all projects of the IDE.

#### Scenario: Default

- **WHEN** the user opens the General page in an IDE in which the setting was never changed
- **THEN** "Show whats new on update" is checked

#### Scenario: Text of the setting

- **WHEN** the user opens the General page
- **THEN** the text of "Show whats new on update" says that it shows a notification with a link to the news after an update, and that it applies to all projects

### Requirement: Show whats new on update is stored for the IDE

"Show whats new on update" SHALL apply to all projects of the IDE and SHALL be stored in the IDE's configuration, only when it differs from its default. It SHALL NOT be written to `.idea/robotcodeSettings.xml` or `.idea/workspace.xml`.

#### Scenario: Turned off in one project

- **WHEN** the user turns off "Show whats new on update" on the General page of one project and applies
- **THEN** the General page of another project shows it turned off, and neither project's `.idea/robotcodeSettings.xml` nor `.idea/workspace.xml` holds it

#### Scenario: Value survives a restart

- **WHEN** the user turns the setting off, applies and restarts the IDE
- **THEN** the General page shows it turned off
