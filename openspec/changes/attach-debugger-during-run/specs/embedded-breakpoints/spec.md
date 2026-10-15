# Spec Delta

## Purpose

Defines what the `Breakpoint` keyword of `robotcode.repl.Repl` and Python's `breakpoint()` do in `robotcode robot-debug` and `robotcode repl`, also while the debugger is detached.

## ADDED Requirements

### Requirement: The Breakpoint keyword attaches the debugger and stops

When a `Breakpoint` keyword of `robotcode.repl.Repl` runs in a `robotcode robot-debug` run or in a `robotcode repl` session, the debugger SHALL be attached if it was detached, and the run SHALL stop at the keyword with the reason `breakpoint`. Breakpoints, steps and exception breakpoints SHALL then pause as with an attached debugger. In a run without RobotCode's debugger, the keyword SHALL do nothing.

#### Scenario: Run started without the debugger

- **WHEN** `robotcode robot-debug --no-debugger-attached` runs a test with `Log To Console    before`, `Breakpoint` and `Log To Console    after`
- **THEN** `before` is printed, and the run stops with `* breakpoint` at `Breakpoint`
- **AND** `.continue` runs the test to its end

#### Scenario: After .detach

- **WHEN** the user enters `.detach` at a stop, and a later `Breakpoint` keyword runs
- **THEN** the run stops there with `* breakpoint`

#### Scenario: REPL session

- **WHEN** `robotcode repl` runs a statement with `Breakpoint` while the debugger is detached, its default
- **THEN** the statement stops with `* breakpoint`
- **AND** `.debug` afterwards reports the debugger as attached

#### Scenario: Run without RobotCode's debugger

- **WHEN** `robotcode robot` runs the test
- **THEN** `Breakpoint` does nothing, and the test passes

### Requirement: breakpoint() pauses at the next keyword

When Python's `breakpoint()` is called while a `robotcode robot-debug` run or a statement of a `robotcode repl` session executes, for example by `Evaluate    breakpoint()`, the debugger SHALL be attached if it was detached. It SHALL stop with the reason `breakpoint` when the next keyword starts, and the keyword that called `breakpoint()` SHALL NOT fail. A REPL statement that ends before another keyword starts SHALL end without the stop.

#### Scenario: Evaluate in a run without the debugger

- **WHEN** `robotcode robot-debug --no-debugger-attached` runs `Evaluate    breakpoint()` and then `Log To Console    next`
- **THEN** `Evaluate` passes, and the run stops with `* breakpoint` at `Log To Console`

#### Scenario: Called from a library keyword

- **WHEN** a Python keyword calls `breakpoint()` during a `robot-debug` run
- **THEN** that keyword runs to its end, and the run stops with `* breakpoint` at the next keyword

#### Scenario: REPL statement

- **WHEN** `robotcode repl` runs a `FOR` loop over two items of `Evaluate    breakpoint()` and `Log    ${i}`
- **THEN** the debugger stops with `* breakpoint` before `Log` runs

#### Scenario: Last keyword of a REPL input

- **WHEN** `robotcode repl` runs `Evaluate    breakpoint()` as an input of its own
- **THEN** the input ends without a stop, and the next input runs without one
