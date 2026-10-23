## ADDED Requirements

### Requirement: The menu of a run marker offers what Robot Framework runs support

The menu of the run marker of a Robot Framework test, task or suite SHALL offer Run, Debug, Run with Profile..., Debug with Profile... and Modify Run Configuration…. It SHALL NOT offer PyCharm's Profile or Concurrency Diagram, or another executor besides Run and Debug.

#### Scenario: Menu in PyCharm Professional

- **WHEN** the user clicks the run marker of the test "Order Coffee" in PyCharm Professional
- **THEN** the menu shows Run, Debug, Run with Profile..., Debug with Profile... and Modify Run Configuration…, and neither Profile nor Concurrency Diagram

#### Scenario: Menu of a suite

- **WHEN** the user clicks the run marker on line 1 of a suite file in PyCharm Professional
- **THEN** the menu shows the same entries as the run marker of a test

## MODIFIED Requirements

### Requirement: Run and Debug stay with RobotCode

Run SHALL show a Robot Framework run configuration in a Run tool window tab with the test tree and the console, and Debug SHALL start a session of the RobotCode debugger, whichever Python plugins are installed. "Run with Coverage" SHALL NOT be offered for Robot Framework run configurations. "Profile" SHALL end with a message that Robot Framework runs cannot be profiled, and "Concurrency Diagram" with a message that they have no concurrency diagram, both without starting a process.

#### Scenario: Run

- **WHEN** the user runs a Robot Framework run configuration with Run
- **THEN** the Run tool window shows the test tree with the results and the console output

#### Scenario: Debug

- **WHEN** the user starts a Robot Framework run configuration with Debug while a Robot Framework breakpoint is set in a test it runs
- **THEN** the RobotCode debugger stops at the breakpoint, and PyCharm's Python debugger does not start

#### Scenario: Profile in PyCharm Professional

- **WHEN** the user chooses "Profile" for a Robot Framework run configuration in PyCharm Professional
- **THEN** no process starts, the IDE shows the message that Robot Framework runs cannot be profiled, and no "IDE error occurred" notification appears

#### Scenario: Concurrency Diagram in PyCharm Professional

- **WHEN** the user chooses "Concurrency Diagram" for a Robot Framework run configuration in PyCharm Professional, for example under "More Run/Debug" in the editor's context menu
- **THEN** no process starts, the IDE shows the message that Robot Framework runs have no concurrency diagram, and no "IDE error occurred" notification appears
