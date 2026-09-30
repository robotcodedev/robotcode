# Spec Delta

## Purpose

Defines how the IntelliJ plugin starts debugging a Robot Framework run configuration and shows it in the Debug tool window, on every platform version it supports.

## ADDED Requirements

### Requirement: Debugging a Robot Framework run configuration

When a Robot Framework run configuration is started with the Debug executor, the plugin SHALL save all documents, start the run under the RobotCode debugger and show it as a session in the Debug tool window. The session tab SHALL show the run's console, stop at enabled breakpoints and end when the run ends or is stopped. A rerun from the session tab SHALL reuse that tab.

#### Scenario: Stop at a breakpoint
- **WHEN** a line breakpoint is set on a keyword call in a test and the test is started with Debug
- **THEN** a session tab for the run configuration opens in the Debug tool window with the run's console output
- **AND** the run stops at the breakpoint with the call stack and variables shown

#### Scenario: Step and resume
- **WHEN** the run is stopped at a breakpoint and the user steps over and then resumes
- **THEN** execution moves to the next step and then runs to the end, and the session ends

#### Scenario: Rerun reuses the tab
- **WHEN** the user reruns the finished session from its tab
- **THEN** the new run is shown in the same tab instead of a new one

#### Scenario: Stop the session
- **WHEN** the user stops a running debug session
- **THEN** the Robot Framework process ends and the session is shown as terminated

### Requirement: No deprecated debugger API of the supported platforms

The plugin SHALL start debug sessions only through debugger API that is not deprecated in its minimum supported platform version. It SHALL use the replacement API where the minimum version already provides one, including API that version still marks as experimental.

#### Scenario: Plugin verification
- **WHEN** `verifyPlugin` checks the plugin against the minimum supported IDE version and the newer versions it is configured for
- **THEN** the report lists no deprecated debugger API usage for any of them

#### Scenario: Compiler warnings
- **WHEN** the plugin is compiled against the minimum supported platform version
- **THEN** the compiler reports no deprecation warning for the debug runner
