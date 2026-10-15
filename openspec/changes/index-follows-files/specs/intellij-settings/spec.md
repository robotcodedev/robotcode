# Spec Delta

## MODIFIED Requirements

### Requirement: Analysis page

The Robot Framework settings node SHALL have an "Analysis" sub-page with these settings, and the language server SHALL use their values after the user applies them:

- diagnostic mode: "Open files only", the default, or "Workspace";
- progress mode: "Off", the default, "Simple" or "Detailed";
- find unused references, off by default;
- references code lens, off by default;
- file check interval in minutes: a whole number from 1 to 1440, 5 by default.

#### Scenario: References code lens

- **WHEN** the user switches the references code lens on and applies
- **THEN** keyword definitions in Robot Framework files show the number of references, such as "2 references", above the definition

#### Scenario: Unused references

- **WHEN** the user switches find unused references on and applies, and a suite file defines a keyword that nothing calls
- **THEN** the editor marks that keyword with the message "Keyword '<name>' is not used."

#### Scenario: Workspace diagnostic mode

- **WHEN** the diagnostic mode is "Workspace" and a Robot Framework file that is not open in an editor contains an error
- **THEN** the server reports the problems of that file, and IntelliJ marks the file as a problem file

#### Scenario: File check interval

- **WHEN** the user sets the file check interval to 2 and applies
- **THEN** the server receives `robotcode.analysis.fileCheckInterval` with the value 2 and checks the workspace files every 2 minutes

### Requirement: Values of the Analysis page

An empty load library timeout SHALL NOT be sent to the server. The "Analysis" sub-page SHALL reject a timeout outside 1 to 3600 and a file check interval outside 1 to 1440, and SHALL NOT send list entries that are blank.

#### Scenario: Empty load library timeout

- **WHEN** the load library timeout is empty
- **THEN** the settings tree contains no `loadLibraryTimeout`, and the timeout from `robot.toml` or the server's default applies

#### Scenario: Invalid load library timeout

- **WHEN** the user enters `0` as load library timeout
- **THEN** the page shows an error and the value is not stored

#### Scenario: Blank entry in a modifier list

- **WHEN** the user adds a blank entry to the ignore list and applies
- **THEN** the server receives the ignore list without the blank entry

#### Scenario: Invalid file check interval

- **WHEN** the user enters `0` as file check interval
- **THEN** the page shows an error and the value is not stored
