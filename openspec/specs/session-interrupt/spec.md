# session-interrupt Specification

## Purpose

Defines what Ctrl-C does in `robotcode repl` and `robotcode robot-debug`:

- at the `>>>` shell prompt, the `(rdb)` debugger prompt and the `(com)` prompt for breakpoint commands, with either backend;
- while a statement or a run executes.

## Requirements

### Requirement: Ctrl-C at the shell prompt discards the input

When the user presses Ctrl-C at the `>>>` prompt or while continuing an unfinished block, the REPL SHALL discard the input typed so far without running it. It SHALL print `KeyboardInterrupt` on a line of its own and SHALL show the `>>>` prompt again, and the session SHALL go on. This SHALL hold for the plain and for the prompt-toolkit backend.

#### Scenario: Unfinished block discarded

- **WHEN** the user types `FOR    ${i}    IN    a    b` and Enter, then `Log    ${i}` and Enter, and presses Ctrl-C before the block is finished
- **THEN** `KeyboardInterrupt` is printed, nothing is logged, and the `>>>` prompt appears again

#### Scenario: Ctrl-C at an empty prompt

- **WHEN** the user presses Ctrl-C at an empty `>>>` prompt
- **THEN** `KeyboardInterrupt` is printed and the `>>>` prompt appears again

#### Scenario: Ctrl-D still ends the session

- **WHEN** the user presses Ctrl-C and then Ctrl-D at the `>>>` prompt
- **THEN** the session ends as with `.exit`

### Requirement: Ctrl-C at the debugger prompt keeps the run paused

When the user presses Ctrl-C at the `(rdb)` prompt, the debugger SHALL discard the typed input and SHALL print `KeyboardInterrupt` on a line of its own. It SHALL keep the run paused and SHALL show `(rdb)` again, with either backend. Ctrl-D at `(rdb)` SHALL resume the run as `.continue` does.

#### Scenario: Ctrl-C at a stop

- **WHEN** `robotcode robot-debug --stop-on-entry` stops at the first keyword and the user presses Ctrl-C at `(rdb)`
- **THEN** `KeyboardInterrupt` is printed and `(rdb)` appears again, and the keyword has not run yet
- **AND** `.continue` then runs the suite to its end

#### Scenario: Partly typed command discarded

- **WHEN** the user types `.print ${` at `(rdb)` and presses Ctrl-C
- **THEN** nothing but `KeyboardInterrupt` is printed, and `(rdb)` appears again

#### Scenario: Ctrl-D still resumes the run

- **WHEN** the user presses Ctrl-D at `(rdb)`
- **THEN** the run goes on as after `.continue`

### Requirement: Ctrl-C aborts the entry of breakpoint commands

When the user presses Ctrl-C at the `(com)` prompt of `.commands`, the debugger SHALL abort the entry and SHALL keep the commands the breakpoint had before. It SHALL print `KeyboardInterrupt` and that the commands are unchanged, and SHALL return to the prompt the entry was started from. `end` and Ctrl-D SHALL store the commands entered.

#### Scenario: Previous commands kept

- **WHEN** breakpoint 1 has the command `.print ${i}`, the user enters `.commands 1`, types `.continue` at `(com)` and presses Ctrl-C
- **THEN** breakpoint 1 still has only the command `.print ${i}`, and the prompt the entry was started from appears again

#### Scenario: Ctrl-D stores the commands

- **WHEN** the user enters `.commands 1`, types `.print ${i}` at `(com)` and presses Ctrl-D
- **THEN** breakpoint 1 has the command `.print ${i}`

### Requirement: Ctrl-C pauses a run with the debugger attached

Ctrl-C SHALL NOT interrupt the keyword that runs while all of these hold: a `robotcode robot-debug` run or a statement of `robotcode repl` executes, the debugger is attached, and no stop is active. The debugger SHALL print right away that it pauses, and SHALL stop with the reason `pause` when the next keyword starts. A stop for another reason before that SHALL take its place. A REPL statement that ends before another keyword starts SHALL end without the stop.

#### Scenario: Pause during a robot-debug run

- **WHEN** `robotcode robot-debug` runs a test with `Sleep    3` and then `Log To Console    next`, and the user presses Ctrl-C while `Sleep` runs
- **THEN** a message says that the run pauses at the next keyword, `Sleep` passes, and the run stops with `* pause` at `Log To Console`
- **AND** `.continue` runs the test to its end, and the test passes

#### Scenario: Pause during a REPL statement

- **WHEN** `robotcode repl --debugger-attached` runs a `FOR` loop that calls `Sleep    2` for two items, and the user presses Ctrl-C during the first `Sleep`
- **THEN** the first `Sleep` passes, and the debugger stops with `* pause` before the second `Sleep` runs

#### Scenario: Statement ends first

- **WHEN** `robotcode repl --debugger-attached` runs `Sleep    3` and the user presses Ctrl-C while it runs
- **THEN** `Sleep` passes, the `>>>` prompt appears again, and the next statement runs without a stop

#### Scenario: Debugger detached

- **WHEN** `robotcode repl` runs `Sleep    30` with the debugger detached and the user presses Ctrl-C
- **THEN** `Sleep` fails with `Execution interrupted`, and the `>>>` prompt appears again

#### Scenario: Keyword typed at a stop

- **WHEN** the run is paused at `(rdb)`, the user runs `Sleep    5` there and presses Ctrl-C while it runs
- **THEN** `Sleep` fails with `Execution interrupted`, the run stays paused, and `(rdb)` appears again

### Requirement: A second Ctrl-C interrupts the keyword that runs

When the user presses Ctrl-C again before the requested pause is reached, the keyword that runs SHALL be interrupted and SHALL fail with `Execution interrupted`. The debugger SHALL then stop at that failure if an exception breakpoint applies to it. Otherwise it SHALL stop at the next keyword that starts.

#### Scenario: Hanging keyword

- **WHEN** `robotcode robot-debug` runs `Sleep    30` with the default exception breakpoints, and the user presses Ctrl-C twice while it runs
- **THEN** `Sleep` fails with `Execution interrupted` well before 30 seconds, and the run stops with `* exception` at `Sleep`

#### Scenario: Caught failure

- **WHEN** `robotcode robot-debug` runs `Run Keyword And Ignore Error    Sleep    30` and then `Log To Console    next`, and the user presses Ctrl-C twice while `Sleep` runs
- **THEN** the run stops with `* pause` at `Log To Console`

### Requirement: Ctrl-C ends a robot-debug run without the debugger

When `robotcode robot-debug` runs with the debugger detached, by `--no-debugger-attached` or after `.detach`, Ctrl-C SHALL end the run as Robot Framework ends a run on Ctrl-C. The test that runs SHALL fail with `Execution terminated by signal`, the remaining tests SHALL NOT run, and the output files SHALL be written. A second Ctrl-C before the run has ended SHALL end the process at once with exit code 253.

#### Scenario: Run without the debugger

- **WHEN** `robotcode robot-debug --no-debugger-attached -o output.xml` runs the first of two tests and the user presses Ctrl-C while a keyword of it runs
- **THEN** the first test fails with `Execution terminated by signal`
- **AND** the second test isn't executed
- **AND** `output.xml` is written

#### Scenario: After .detach

- **WHEN** the user enters `.detach` at a stop in the first of two tests and presses Ctrl-C while a keyword of that test runs
- **THEN** the first test fails with `Execution terminated by signal`, and the second test isn't executed

#### Scenario: Second Ctrl-C

- **WHEN** a run without the debugger gets Ctrl-C, and a second Ctrl-C while the teardown of the test still runs
- **THEN** the process ends at once with exit code 253
