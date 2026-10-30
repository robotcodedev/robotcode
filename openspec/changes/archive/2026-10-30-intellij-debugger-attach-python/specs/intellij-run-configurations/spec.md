# Spec Delta

## MODIFIED Requirements

### Requirement: Run and Debug stay with RobotCode

Run SHALL show a Robot Framework run configuration in a Run tool window tab with the test tree and the console, and Debug SHALL start a session of the RobotCode debugger, whichever Python plugins are installed. "Run with Coverage" SHALL NOT be offered for Robot Framework run configurations. "Profile" SHALL end with a message that Robot Framework runs cannot be profiled, and "Concurrency Diagram" with a message that they have no concurrency diagram, both without starting a process.

#### Scenario: Run

- **WHEN** the user runs a Robot Framework run configuration with Run
- **THEN** the Run tool window shows the test tree with the results and the console output

#### Scenario: Debug

- **WHEN** the user starts a Robot Framework run configuration whose effective "Attach Python" is off with Debug while a Robot Framework breakpoint is set in a test it runs
- **THEN** the RobotCode debugger stops at the breakpoint, and PyCharm's Python debugger does not start

#### Scenario: Profile in PyCharm Professional

- **WHEN** the user chooses "Profile" for a Robot Framework run configuration in PyCharm Professional
- **THEN** no process starts, the IDE shows the message that Robot Framework runs cannot be profiled, and no "IDE error occurred" notification appears

#### Scenario: Concurrency Diagram in PyCharm Professional

- **WHEN** the user chooses "Concurrency Diagram" for a Robot Framework run configuration in PyCharm Professional, for example under "More Run/Debug" in the editor's context menu
- **THEN** no process starts, the IDE shows the message that Robot Framework runs have no concurrency diagram, and no "IDE error occurred" notification appears

#### Scenario: Debug with Attach Python

- **WHEN** the user starts a Robot Framework run configuration whose effective "Attach Python" is on with Debug
- **THEN** the RobotCode debugger session starts, and a session of PyCharm's Python debugger starts beside it

### Requirement: Run & Debug options per configuration

A Robot Framework run configuration SHALL offer, behind "Modify options" in a "Run & Debug" group, with the labels of the "Run" and "Debug" settings pages:

- "Launch wrapper": "Project default", "Profile's wrapper", a custom command, or "None";
- "Output messages", "Output log" and "Output timestamps", each "Project default", on or off;
- "Attach Python": "Project default", on or off;
- "Open output after run": "Project default", "Nothing", "Report" or "Log".

#### Scenario: Value set in the configuration

- **WHEN** the project default for "Output log" is on and a configuration switches "Output log" off
- **THEN** runs of that configuration send no log messages, and runs of other configurations still do

#### Scenario: Attach Python set in the configuration

- **WHEN** the project default for "Attach Python" is off and a configuration switches "Attach Python" on
- **THEN** Debug runs of that configuration also start PyCharm's Python debugger, and Debug runs of other configurations do not

#### Scenario: Attach Python with Run

- **WHEN** a configuration's effective "Attach Python" is on and the user starts it with Run
- **THEN** the run starts as it does with "Attach Python" off, without PyCharm's Python debugger
