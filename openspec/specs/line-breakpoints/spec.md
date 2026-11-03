# line-breakpoints Specification

## Purpose

Defines how line breakpoints of the command-line debugger (`.break`, `.tbreak` and `robotcode robot-debug --break`) match the place a keyword runs at, and what the debugger says about a breakpoint that no keyword reached.

## Requirements

### Requirement: A line breakpoint matches by file name

A line breakpoint given with a relative path SHALL stop in every file whose path ends with that path, as in gdb, wherever the run was started. A breakpoint given with an absolute path SHALL stop only in that file.

#### Scenario: A file name alone
- **WHEN** `robotcode robot-debug --break login.robot:25` runs a suite with `tests/login.robot`, which has a keyword call at line 25
- **THEN** the run stops at line 25 of `tests/login.robot`

#### Scenario: Part of the path
- **WHEN** `robotcode robot-debug --break tests/login.robot:25` runs in a project with `tests/login.robot` and `other/login.robot`, each with a keyword call at line 25
- **THEN** the run stops in `tests/login.robot` and not in `other/login.robot`

#### Scenario: Several files with that name
- **WHEN** `robotcode robot-debug --break login.robot:25` runs that project over both folders
- **THEN** the run stops in both files

#### Scenario: An absolute path
- **WHEN** `.break` gets the absolute path of `tests/login.robot` and a line
- **THEN** the run stops in that file only

### Requirement: The list shows a line breakpoint as it was given

`.breakpoints` SHALL show the location of a line breakpoint as it was given, so that a breakpoint with a mistyped path can be told from a right one.

#### Scenario: Two forms
- **WHEN** `--break login.robot:25` and `--break tests/orders.robot:10` are set and `.breakpoints` runs
- **THEN** it lists `login.robot:25` and `tests/orders.robot:10`

### Requirement: A breakpoint that no keyword reached

When a `robotcode robot-debug` run has ended by itself, the debugger SHALL warn about each enabled breakpoint whose location no keyword reached during the run, and name it as it was given. A breakpoint that was reached but whose condition was false SHALL NOT count as unreached. The warning SHALL NOT change the exit code.

#### Scenario: A file that isn't in the run
- **WHEN** `robotcode robot-debug --break nosuch.robot:5` runs a suite to its end
- **THEN** the output warns that `nosuch.robot:5` was never reached
- **AND** the exit code is that of the run

#### Scenario: A line without a keyword call
- **WHEN** `--break tests/login.robot:19` names the line of the test's name and the run ends
- **THEN** the output warns that `tests/login.robot:19` was never reached

#### Scenario: A false condition
- **WHEN** a breakpoint with a condition that stays false is at a line a keyword runs at
- **THEN** the run doesn't stop there, and no warning names it

#### Scenario: A keyword breakpoint
- **WHEN** `--break "No Such Keyword"` is set and the run ends
- **THEN** the output warns that it was never reached

#### Scenario: A run that was ended
- **WHEN** a run with an unreached breakpoint ends through `.abort` or `.detach`
- **THEN** no warning names it
