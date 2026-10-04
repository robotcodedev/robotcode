# Spec Delta

## Purpose

Defines how the IntelliJ plugin runs the RobotCode language server: when it starts, how it is connected, stopped and restarted, what it receives at start, where its output goes, and how users control and observe it.

## ADDED Requirements

### Requirement: Local connection to the language server

The plugin SHALL accept the language server's connection only on the loopback address 127.0.0.1, and SHALL stop listening as soon as the server has connected. While the server runs, the plugin SHALL NOT keep a listening port open for it.

#### Scenario: Listening address during the start

- **WHEN** the language server starts
- **THEN** the port on which the plugin waits for the server is bound to 127.0.0.1, not to all network interfaces

#### Scenario: No listener while the server runs

- **WHEN** the language server has started and connected
- **THEN** the plugin no longer listens on a port for it

### Requirement: Failed starts end with an error

When the language server process exits before it connects, the start SHALL fail with an error that names the process's exit code. When the process neither connects nor exits within 60 seconds, the plugin SHALL end the process and fail the start with an error that says that the server did not connect in time. A failed start SHALL leave no thread waiting for the connection, and stopping or restarting the server afterwards SHALL NOT raise an error.

#### Scenario: Server exits before it connects

- **WHEN** the language server process exits with code 3 before it connects
- **THEN** the start of the RobotCode language server fails with an error that names exit code 3, and no thread stays blocked waiting for the connection

#### Scenario: Server never connects

- **WHEN** the language server process keeps running without connecting for 60 seconds
- **THEN** the plugin ends the process and the start fails with an error that says that the server did not connect in time

#### Scenario: Restarting after a failed start

- **WHEN** the start failed because the server exited before it connected, and the user then restarts the server three times
- **THEN** no NullPointerException or other error is logged, and no listening port or waiting thread is left behind

### Requirement: Language server output goes to the Language Servers console

Everything the language server writes to stderr or stdout SHALL appear in the logs of the RobotCode entry in the Language Servers tool window. It SHALL NOT be reported as an IDE error. Output on stdout SHALL NOT stall the language server, however much of it there is.

#### Scenario: Error output of the server

- **WHEN** robot.toml sets `default-profiles = "doesnotexist"` and the language server starts
- **THEN** the server's message about the missing profile appears in the logs of the RobotCode language server in the Language Servers tool window, and no "IDE error occurred" notification and no SEVERE entry in idea.log is raised for it

#### Scenario: Large output on stdout

- **WHEN** the language server process writes 200 KB to stdout, for example from a library that prints while it is imported for a suite
- **THEN** the output appears in the logs of the RobotCode language server, and the server keeps answering requests, for example completion in that suite

### Requirement: Clean stop and restart

When the plugin stops or restarts the language server, it SHALL give the server a bounded time to receive the exit notification and end on its own, and only then close the connection and end a process that is still running. Stopping the server SHALL NOT produce a connection error.

#### Scenario: Restart

- **WHEN** the user restarts the language server
- **THEN** the old server process ends by itself after the exit notification, and no connection error such as "Socket closed" is reported for the server

#### Scenario: Server that ignores the exit notification

- **WHEN** the server process is still running after the bounded wait
- **THEN** the plugin ends the process and the stop completes

### Requirement: Restart and Clear Cache actions

Tools | RobotCode | Restart RobotCode Language Server SHALL check the Python environment again before it starts the server, so that a problem fixed outside the IDE, such as installing Robot Framework, takes effect, and SHALL then run test discovery again. Tools | RobotCode | Clear Cache and Restart RobotCode Language Server SHALL clear the analysis cache of a running server and then restart as Restart does; when no server runs, it SHALL restart without clearing and without an error. Neither action SHALL block the IDE while it checks, clears or restarts. Both actions SHALL be disabled when no project is open.

#### Scenario: Restart after installing Robot Framework

- **WHEN** Robot Framework was missing in the project's interpreter, the user installs it from a terminal and then chooses Restart RobotCode Language Server
- **THEN** the language server starts, and the run markers of the tests appear in Robot files after discovery

#### Scenario: Clear Cache while the server is stopped

- **WHEN** the language server is stopped because the interpreter is not usable, and the user chooses Clear Cache and Restart RobotCode Language Server
- **THEN** no error is logged, and the plugin checks the environment again and starts the server if the environment is usable now

#### Scenario: Clear Cache with a running server

- **WHEN** the language server is running and the user chooses Clear Cache and Restart RobotCode Language Server
- **THEN** the server's analysis cache is cleared, the server restarts, and the IDE stays responsive meanwhile

#### Scenario: No project

- **WHEN** no project is open
- **THEN** both actions are disabled

### Requirement: No restart after the project is closed

A restart that was scheduled for a project, for example after a change to robot.toml, SHALL NOT run once the project is closing or closed, nor after the plugin has been unloaded.

#### Scenario: Project closed right after a robot.toml change

- **WHEN** robot.toml is saved and the project is closed within half a second
- **THEN** no environment check, server start or discovery runs for the closed project, and no error is logged
