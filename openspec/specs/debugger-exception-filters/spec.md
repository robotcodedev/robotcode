# debugger-exception-filters Specification

## Purpose

Defines the exception filters the RobotCode debugger offers a debug client, such as VS Code or the IntelliJ plugin, for stopping a run at failures: which filters there are and how they are named and described.

## Requirements

### Requirement: Names of the exception filters

The debugger SHALL offer the exception filters `failed_keyword`, `uncaught_failed_keyword`, `failed_test` and `failed_suite`, named in the plural after the failures each one stops at: "Failed Keywords", "Uncaught Failed Keywords", "Failed Tests" and "Failed Suites". Their descriptions SHALL be "Breaks on failed keywords", "Breaks on uncaught failed keywords", "Breaks on failed tests" and "Breaks on failed suites".

#### Scenario: Advertised filters

- **WHEN** a debug client asks the debugger for its capabilities
- **THEN** the filter `failed_test` is named "Failed Tests" and described as "Breaks on failed tests", and the filter `failed_suite` is named "Failed Suites" and described as "Breaks on failed suites"

#### Scenario: VS Code's Breakpoints view

- **WHEN** a RobotCode debug session starts in VS Code
- **THEN** the Breakpoints view lists "Failed Keywords", "Uncaught Failed Keywords", switched on, "Failed Tests" and "Failed Suites"

#### Scenario: Same names as in PyCharm

- **WHEN** the user compares VS Code's Breakpoints view with the Robot Framework exception breakpoints of the IntelliJ plugin
- **THEN** both name the kinds of failure "Uncaught Failed Keywords", "Failed Keywords", "Failed Tests" and "Failed Suites"

#### Scenario: Same filter under the new name

- **WHEN** a debug client enables the filter `failed_test` and a test fails
- **THEN** the run stops when that test ends, as it did when the filter was named "Failed Test"
