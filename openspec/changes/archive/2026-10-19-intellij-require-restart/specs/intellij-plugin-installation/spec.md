# Spec Delta

## Purpose

Defines how installing, updating and uninstalling the IntelliJ plugin take effect, so that users know when RobotCode is active and the IDE never runs with a half-unloaded RobotCode.

## ADDED Requirements

### Requirement: Installing, updating and uninstalling take effect after a restart

The plugin SHALL declare that installing, updating and uninstalling it needs a restart of the IDE, so that the IDE never loads or unloads RobotCode while it runs. A new installation SHALL be active after the restart, an update SHALL keep the installed version working until the restart, and an uninstalled RobotCode SHALL keep working until the restart.

#### Scenario: Installation from the Marketplace

- **WHEN** the user installs RobotCode under Settings | Plugins
- **THEN** the IDE offers to restart, and RobotCode's settings pages, actions and run markers appear after the restart

#### Scenario: Update to a new version

- **WHEN** the IDE downloads a new version of RobotCode while a project with Robot Framework files is open
- **THEN** it asks for a restart, the installed version keeps working until then, and the new version runs after the restart

#### Scenario: Uninstallation

- **WHEN** the user uninstalls RobotCode
- **THEN** the IDE asks for a restart, and the Robot Framework files keep their highlighting and run markers until the restart
