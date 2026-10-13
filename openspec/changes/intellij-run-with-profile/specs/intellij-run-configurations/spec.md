# Spec Delta

## ADDED Requirements

### Requirement: The configuration profiles option

The editor of a Robot Framework run configuration SHALL offer "Configuration profiles" under "Modify options", in its Robot Framework section, with the choices "Project selection", "Default profiles of robot.toml" and "Custom". For "Custom", the editor SHALL show the chosen profile names and a "Select..." button that opens the profile list of the General page with the configuration's names as the selection; confirming the list SHALL put the checked names into the editor.

#### Scenario: Custom profiles survive a restart

- **WHEN** the user shows "Configuration profiles" through "Modify options", chooses "Custom", checks `ci` in the list, applies and restarts the IDE
- **THEN** the editor shows "Custom" with `ci`, and a run of the configuration contains `-p ci`

### Requirement: Configuration profiles of earlier and shared configurations

A configuration stored before "Configuration profiles" existed SHALL open with "Project selection". A configuration stored as a project file SHALL hold a choice other than "Project selection" together with its profile names.

#### Scenario: Stored as a project file

- **WHEN** a configuration with the choice "Custom" and `ci` is stored as a project file
- **THEN** the file under `.run/` holds the choice and `ci`

#### Scenario: Configuration of an earlier version

- **WHEN** a configuration saved before this option existed is opened
- **THEN** its choice is "Project selection"
