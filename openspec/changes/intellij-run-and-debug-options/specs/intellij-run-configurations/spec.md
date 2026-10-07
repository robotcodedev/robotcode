# Spec Delta

## Purpose

Defines what a Robot Framework run configuration of the IntelliJ plugin runs, how it is stored, edited, shared and reused, and which arguments its runs pass to `robotcode` and Robot Framework.

## ADDED Requirements

### Requirement: Run & Debug options per configuration

A Robot Framework run configuration SHALL offer, behind "Modify options" in a "Run & Debug" group:

- the wrapper: "Project default", "Profile's wrapper", a custom command, or "None";
- Robot Framework messages, log messages and timestamps, each "Project default", on or off;
- what to open after a run: "Project default", "Nothing", "Report" or "Log".

#### Scenario: Value set in the configuration

- **WHEN** the project default for log messages is on and a configuration switches log messages off
- **THEN** runs of that configuration send no log messages, and runs of other configurations still do

### Requirement: Run & Debug options without a project default

The "Run & Debug" group of a Robot Framework run configuration SHALL also offer, without a project default: `robotcode` arguments, stop on entry (off unless switched on), the connection timeout in seconds (when empty, the debugger's default of 15 seconds) and extra debugger arguments.

#### Scenario: New configuration

- **WHEN** the user creates a Robot Framework run configuration and opens "Modify options"
- **THEN** the "Run & Debug" group offers `robotcode` arguments, stop on entry, which is off, the connection timeout and extra debugger arguments

### Requirement: Configurations follow the project defaults

New configurations SHALL use "Project default" for every value that has one. At the start of each run, a value set to "Project default" SHALL take the project default that is current at that moment.

#### Scenario: Changed project default reaches an existing configuration

- **WHEN** a saved configuration uses "Project default" for the wrapper, and the user sets the launch wrapper on the Run & Debug page to `xvfb-run -a` and runs the configuration without editing it
- **THEN** the run uses the wrapper `xvfb-run -a`

### Requirement: Run & Debug options on the command line

A run SHALL pass the effective values as `robotcode` options:

- before `debug`: `--wrapper` with the command as one argument for a custom command or a non-empty project default, `--no-wrapper` for "None", and nothing for "Profile's wrapper" or an empty project default; then the `robotcode` arguments, split like a command line.

A wrapper command SHALL reach `robotcode` with the same words the user typed, also when they contain spaces in quotes or Windows paths with backslashes.

#### Scenario: Project wrapper on a gutter run

- **WHEN** the launch wrapper on the Run & Debug page is `xvfb-run -a` and the user runs a test from the gutter
- **THEN** the command line passes `--wrapper` with the value `xvfb-run -a` before `debug`, and the test runs under `xvfb-run`

#### Scenario: No wrapper

- **WHEN** a configuration sets the wrapper to "None" while its `robot.toml` profile defines a wrapper
- **THEN** the run passes `--no-wrapper` and runs without the wrapper

### Requirement: Debugger options on the command line

A run SHALL pass the effective debugger values as `robotcode` options after `debug` and before `--`: `--output-messages` when messages are on; `--no-output-log` only when log messages are off; `--output-timestamps` when timestamps are on; `--stop-on-entry` when stop on entry is on and the run was started with Debug; `--wait-for-client-timeout` with the connection timeout when it differs from 15 seconds; then the extra debugger arguments, split like a command line.

#### Scenario: Default debugger output

- **WHEN** a configuration uses the project defaults and the project keeps VS Code's defaults
- **THEN** the run passes none of `--output-messages`, `--no-output-log`, `--output-timestamps` and `--wait-for-client-timeout`

#### Scenario: Stop on entry with Run

- **WHEN** stop on entry is on and the user starts the configuration with Run
- **THEN** the run passes no `--stop-on-entry`
