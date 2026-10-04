# Spec Delta

## ADDED Requirements

### Requirement: Debugging a run started elsewhere

Starting a "Robot Framework (Attach)" configuration with Debug SHALL connect the debugger to the `robotcode debug` server at the configured host and port and send the configured path mappings. The session SHALL then debug the run as it debugs runs the IDE started: it SHALL stop at the line breakpoints and exception breakpoints of the local files that the path mappings map to the files of the run, show frames with the local files, and show variables and evaluations. The session's console SHALL show the output the debugger sends. If nothing accepts the connection within 15 seconds, the session SHALL end with a message in its console.

#### Scenario: Run on the same machine

- **WHEN** a run was started in a terminal with `robotcode debug --tcp 6612 -- tests` in the project folder, and the user debugs an attach configuration with port 6612 and no path mappings while a breakpoint is set in `sample.robot`
- **THEN** the run stops at the breakpoint, and the session shows the frames and variables

#### Scenario: Files in another folder

- **WHEN** the run was started in a copy of the project in another folder, and the attach configuration maps the local project folder to that copy
- **THEN** a breakpoint set in the local `sample.robot` stops the run, and selecting the top frame opens the local `sample.robot`

#### Scenario: Nothing listens

- **WHEN** the user debugs an attach configuration whose port has no `robotcode debug` server
- **THEN** after 15 seconds the session ends, and its console says that no connection could be made

### Requirement: Detaching from and terminating an attached run

Stopping an attach session SHALL detach the debugger: the run SHALL continue to its end without stopping at breakpoints and without waiting for the IDE. The attach session SHALL offer a "Terminate Run" action that ends the run gracefully, as Stop ends runs the IDE started. When the attached run ends, the session SHALL end.

#### Scenario: Detach

- **WHEN** the attached run is paused at a breakpoint and the user stops the session
- **THEN** the session ends, and the run finishes on its own without delays and writes its output files

#### Scenario: Terminate the run

- **WHEN** the attached run is paused at a breakpoint and the user chooses "Terminate Run"
- **THEN** the run ends gracefully with its report and log written, and the session ends

#### Scenario: The run ends

- **WHEN** the attached run reaches its end while the session is attached
- **THEN** the session ends
