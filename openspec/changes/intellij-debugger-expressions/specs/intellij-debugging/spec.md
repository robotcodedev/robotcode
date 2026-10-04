# Spec Delta

## ADDED Requirements

### Requirement: Expression editors understand Robot Framework

The Evaluate dialog, watches, the condition and log fields of Robot Framework breakpoints, and the Robot debug console SHALL accept input without the IDE logging errors. While a run is paused, they SHALL offer completion of the keywords, libraries, resources and variables that the RobotCode debugger reports for the selected frame.

#### Scenario: Typing in the Evaluate dialog

- **WHEN** the run is paused and the user types an expression into the Evaluate dialog for a minute
- **THEN** `idea.log` gets no SEVERE entry and no "IDE error occurred" notification appears

#### Scenario: Complete a variable

- **WHEN** the run is paused and the user types `${` in the Evaluate dialog
- **THEN** the completion list offers the variables of the selected frame

#### Scenario: Complete a keyword

- **WHEN** the run is paused and the user types `Lo` in the Evaluate dialog
- **THEN** the completion list offers `Log` and other keywords whose names match

### Requirement: Hover shows variable values

While a run is paused, hovering a variable in a Robot Framework file SHALL show its value in the selected frame. The value SHALL be evaluated as an expression, without running keywords.

#### Scenario: Hover a variable

- **WHEN** the run is paused after `${message}=    Set Variable    Hello` and the user hovers `${message}` in the editor
- **THEN** a tooltip shows the value `'Hello'`

### Requirement: Robot debug console

A Robot Framework debug session SHALL have a "Robot Debug Console" tab. While the run is paused, a line entered there SHALL be evaluated in the selected frame with the debugger's REPL semantics, where a single variable shows its value and anything else runs as a keyword call, and the console SHALL print the result or the debugger's error message. Entered lines SHALL be kept in a history that can be recalled. While the run is not paused, the console SHALL say so instead of evaluating.

#### Scenario: Run a keyword

- **WHEN** the run is paused and the user enters `Log    hello` in the Robot Debug Console
- **THEN** the keyword runs in the paused test, its message `hello` appears in the run's output, and the console prints the result

#### Scenario: History

- **WHEN** the user has entered `Log    hello` and presses the history key in the empty input line
- **THEN** the input line shows `Log    hello` again

#### Scenario: Run not paused

- **WHEN** the run is not paused and the user enters a line in the Robot Debug Console
- **THEN** the console says that the run is not paused, and nothing is evaluated

### Requirement: Breakpoint conditions, log messages and hit counts

Robot Framework line breakpoints SHALL offer a condition, a log message ("Evaluate and log") and a hit count, and the project SHALL keep them with its breakpoints. The condition SHALL be a Python expression in which Robot Framework variables are replaced, and the run SHALL stop only when it is true. A hit count N SHALL stop the run only the N-th time it reaches the line, counting only the times the condition was true. With the suspend policy None, the log message SHALL be a Robot Framework template, such as `value is ${i}`, that the debugger writes to the run's output each time the line is reached, without stopping. With a suspending policy, the log message SHALL be evaluated like a watch when the run stops at the breakpoint, and its result SHALL be logged.

#### Scenario: Condition

- **WHEN** a breakpoint inside a `FOR` loop over the numbers 0 to 7 has the condition `${i} == 3`
- **THEN** the run stops once, with `${i}` being 3

#### Scenario: Log message without stopping

- **WHEN** a breakpoint inside that loop has the suspend policy None and the log message `value is ${i}`
- **THEN** the output shows `value is 0` to `value is 7`, one line per iteration, and the run does not stop

#### Scenario: Hit count

- **WHEN** a breakpoint inside that loop has the hit count 2
- **THEN** the run stops once, in the second iteration

#### Scenario: Settings survive a restart

- **WHEN** the user sets a condition, a log message and a hit count on a breakpoint and restarts the IDE
- **THEN** the breakpoint still has all three

### Requirement: Breakpoint actions apply at line breakpoints

When the run stops at a Robot Framework line breakpoint, the IDE SHALL apply that breakpoint's settings: its suspend policy, the "Breakpoint hit" message, the stack trace, "Remove once hit", and breakpoints that are disabled until this breakpoint is hit.

#### Scenario: Remove once hit

- **WHEN** a breakpoint inside a loop has "Remove once hit" set and the run reaches it
- **THEN** the run stops there once, the breakpoint is removed, and later iterations do not stop

#### Scenario: Suspend policy None with a hit message

- **WHEN** a breakpoint has the suspend policy None and the "Breakpoint hit" message enabled
- **THEN** the run does not visibly stop at it, and the console shows the hit message each time the line is reached

#### Scenario: Dependent breakpoint

- **WHEN** a breakpoint is set to stay disabled until another breakpoint is hit, and the run reaches it before and after that other breakpoint
- **THEN** the run stops at it only after the other breakpoint was hit

### Requirement: Exception breakpoint for failed tests

The IDE SHALL offer a "Failed Tests" Robot Framework exception breakpoint, disabled by default. While it is enabled and breakpoints are not muted, the run SHALL stop when a test fails, apply the breakpoint's suspend policy and show the test's failure message.

#### Scenario: Failed test

- **WHEN** only "Failed Tests" is enabled and a test fails with the message `intentional failure`
- **THEN** the run stops at the end of that test and shows the failure message
