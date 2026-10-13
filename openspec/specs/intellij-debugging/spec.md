# Spec: intellij-debugging

## Purpose

Defines how the IntelliJ plugin starts debugging a Robot Framework run configuration and shows it in the Debug tool window, and how Run and Debug sessions of Robot Framework runs connect to the RobotCode debugger and are stopped, on every platform version it supports.

## Requirements

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

### Requirement: Line breakpoints take effect as shown

In a debug session, the RobotCode debugger SHALL stop only at Robot Framework line breakpoints that the IDE shows as enabled and that are not muted, at the line where the IDE shows them. Adding, removing, disabling, enabling, muting, unmuting and moving a breakpoint, by dragging it or by editing the lines above it, SHALL take effect at once, also for the last breakpoint of a file and also while the run is paused.

#### Scenario: Disable the only breakpoint of a file while paused

- **WHEN** the run is paused at the only breakpoint of a file, inside a loop that reaches that line again, and the user disables the breakpoint and resumes
- **THEN** the run does not stop at that line again

#### Scenario: Remove all breakpoints while paused

- **WHEN** the run is paused at a breakpoint, the user removes every Robot Framework breakpoint and resumes
- **THEN** the run does not stop at any of the removed lines

#### Scenario: Mute breakpoints

- **WHEN** the user mutes breakpoints while the run is paused in a loop and resumes
- **THEN** the run does not stop at any line breakpoint until breakpoints are unmuted

#### Scenario: Move a breakpoint

- **WHEN** the user drags a breakpoint to another line, or inserts a line above it, and the run reaches the old line and then the new one
- **THEN** the run stops only at the line where the IDE now shows the breakpoint

### Requirement: Force actions ignore breakpoints

Force Step Over and Force Run to Cursor SHALL ignore all breakpoints until they have reached their target.

#### Scenario: Force Step Over

- **WHEN** the run is paused on a line that calls a keyword whose body has a breakpoint and the user chooses Force Step Over
- **THEN** the run stops at the next line of the current body, not at the breakpoint inside the keyword

### Requirement: Run to Cursor always continues to the target line

Run to Cursor SHALL continue the paused run and stop it at the target line, whether or not that line has a breakpoint. The temporary stop SHALL not remain in effect after the session has shown a stop again, at the target line or anywhere else. A failure that an exception breakpoint passes over without pausing SHALL not end Run to Cursor.

#### Scenario: Target line with a breakpoint

- **WHEN** the run is paused and the user runs to the cursor on a later line that has a breakpoint
- **THEN** the run continues and stops at that line, and the session shows it as paused there

#### Scenario: Temporary stop does not remain

- **WHEN** the user runs to the cursor on a line without a breakpoint, the run stops there, and the run reaches that line again after resuming
- **THEN** the run does not stop at that line again

#### Scenario: Failure passed over on the way

- **WHEN** "Failed Keywords" is enabled with the suspend policy None and the user runs to the cursor on a line behind a failing keyword
- **THEN** the run passes the failure and stops at the target line

### Requirement: Breakpoints are in effect from the first keyword

The line breakpoints and exception breakpoints that exist when a debug session starts SHALL be in effect before Robot Framework runs its first keyword, and a stop at the first keyword SHALL pause the run.

#### Scenario: Breakpoint on the first keyword

- **WHEN** a breakpoint is set on the first keyword call of the first test and the test is started with Debug ten times in a row
- **THEN** every run stops at that breakpoint

### Requirement: Exception breakpoints per kind of failure

The IDE SHALL show the Robot Framework exception breakpoints as one group in the Breakpoints dialog. The group SHALL always hold "Uncaught Failed Keywords", enabled by default, which SHALL keep the enabled state and settings stored for the exception breakpoint of earlier plugin versions. The user SHALL be able to add "Failed Keywords", "Failed Tests" and "Failed Suites" to the group, each at most once and with settings of its own, and to remove them again.

#### Scenario: Setting stored by an earlier version

- **WHEN** a project's workspace stores the former "Any Exception" breakpoint as disabled
- **THEN** "Uncaught Failed Keywords" is shown disabled, and the debugger does not stop at uncaught keyword failures

#### Scenario: One group

- **WHEN** the user opens the Breakpoints dialog in a project that has stored no Robot Framework exception breakpoints
- **THEN** the dialog shows one "Robot Framework Exception Breakpoints" group, which holds "Uncaught Failed Keywords", enabled, and offers no way to remove it

#### Scenario: Add a kind

- **WHEN** the user adds "Failed Tests" with the dialog's add button
- **THEN** the group holds "Failed Tests" as an enabled breakpoint of its own, and the add button then offers only "Failed Keywords" and "Failed Suites"

#### Scenario: Remove an added kind

- **WHEN** the user removes "Failed Tests" from the group and starts a failing test with Debug
- **THEN** the run does not stop when the test fails, and the add button offers "Failed Tests" again

#### Scenario: Added kinds survive a restart

- **WHEN** the user has added "Failed Tests" with the suspend policy None and restarts the IDE
- **THEN** the group still holds "Failed Tests" with the suspend policy None

### Requirement: What each exception breakpoint stops at

"Uncaught Failed Keywords" SHALL stop at keyword failures that are not handled by `TRY/EXCEPT` or by BuiltIn's error-handling keywords, "Failed Keywords" at every keyword failure, "Failed Tests" when a test fails, and "Failed Suites" when a suite fails. The debugger SHALL stop at a failure only while the matching exception breakpoint is enabled and breakpoints are not muted.

#### Scenario: All exception breakpoints disabled

- **WHEN** all Robot Framework exception breakpoints are disabled and a failing test is started with Debug
- **THEN** the test fails without the run stopping, and the run ends normally

#### Scenario: Failed keywords

- **WHEN** "Failed Keywords" is enabled and a test runs `Fail    expected` inside `TRY/EXCEPT`
- **THEN** the run stops after that keyword and shows the failure message `expected`

#### Scenario: Caught failure with uncaught failed keywords

- **WHEN** only "Uncaught Failed Keywords" is enabled and a test runs `Fail    expected` inside `TRY/EXCEPT` and inside `Run Keyword And Ignore Error`
- **THEN** the run does not stop at these failures

#### Scenario: Failed tests

- **WHEN** only "Failed Tests" is enabled and a test fails with the message `intentional failure`
- **THEN** the run stops when that test ends and shows the message `intentional failure`

#### Scenario: Failed suites

- **WHEN** only "Failed Suites" is enabled and a test of a suite file fails
- **THEN** the run stops when that suite ends and shows the suite's failure message

### Requirement: Stops at exception breakpoints

A stop at an exception breakpoint SHALL apply that breakpoint's suspend policy and show the failure message. A failure stop that matches no enabled exception breakpoint SHALL be shown as paused instead of leaving the run waiting unseen.

#### Scenario: Suspend policy None

- **WHEN** "Uncaught Failed Keywords" is enabled with the suspend policy None and a failing test is started with Debug
- **THEN** the run finishes without a visible stop and the IDE logs no error

### Requirement: Robot Framework line breakpoints only in Robot Framework files

The plugin SHALL offer Robot Framework line breakpoints only in Robot Framework suite and resource files. In all other files, toggling a breakpoint SHALL create the breakpoint type that the IDE would create without the plugin, or none.

#### Scenario: Python file

- **WHEN** the user clicks the gutter of a line in a Python file
- **THEN** a Python line breakpoint is created, not a Robot Framework breakpoint

#### Scenario: Plain text file

- **WHEN** the user clicks the gutter of a line in a `.txt` or `.toml` file
- **THEN** no Robot Framework breakpoint is created

### Requirement: Scopes in the Variables view

While a run is paused, the Variables view SHALL show the Local scope of the selected frame inline and the frame's other scopes (Test, Suite, Global) as groups whose variables are loaded when a group is expanded. A frame without scopes SHALL show no variables and no error.

#### Scenario: Frame without scopes

- **WHEN** the user selects a frame for which the debugger reports no scopes
- **THEN** the Variables view is empty and the IDE logs no error

### Requirement: Variables expand into their items

A list variable SHALL expand into its length and its items, shown in pages of 100 items with an entry that loads the next page. A dictionary variable SHALL expand into its length and its entries. Each variable SHALL show the name of its Python type, such as `str`, `list` or `DotDict`. The same SHALL apply to a value that an evaluation returns, such as a watch.

#### Scenario: Expand a list

- **WHEN** the run is paused after `@{items}=    Create List    a    b    c` and the user expands `@{items}`
- **THEN** the items `a`, `b` and `c` are shown with their indexes, and the type column shows `list`

#### Scenario: Large list

- **WHEN** a paused test has a list variable with 300 items and the user expands it
- **THEN** the first 100 items are shown with an entry for the remaining 200, and choosing that entry shows the next 100

#### Scenario: Expand a dictionary

- **WHEN** the run is paused after `&{options}=    Create Dictionary    a=1    b=2` and the user expands `&{options}`
- **THEN** the entries `'a'` and `'b'` are shown with their values

#### Scenario: Expand a list in a watch

- **WHEN** the run is paused after `@{items}=    Create List    a    b    c`, the user adds `@{items}` as a watch and expands it
- **THEN** the items `a`, `b` and `c` are shown with their indexes

### Requirement: Set Value for variables of the paused keyword or test

While a run is paused, Set Value SHALL be offered for the variables of the Local scope of the innermost frame. Set Value SHALL NOT be offered for variables of outer frames, for the Test, Suite and Global groups, or for items of lists and dictionaries.

#### Scenario: Not offered for suite variables

- **WHEN** the user opens the context menu of a variable in the Suite group
- **THEN** Set Value is not available

### Requirement: Set Value evaluates the new value

A value entered with Set Value SHALL be evaluated as the debugger evaluates it: as a Python expression in which Robot Framework variables are replaced. After a successful change, the Variables view and the rest of the run SHALL use the new value. A value the debugger rejects SHALL show the debugger's error message and leave the variable unchanged.

#### Scenario: Change a variable

- **WHEN** the run is paused before `Log    ${x}`, the user sets `${x}` to `'changed'` and resumes
- **THEN** the Variables view shows `'changed'` for `${x}` before the resume, and `Log    ${x}` logs `changed`

#### Scenario: Invalid value

- **WHEN** the user sets `${x}` to the bare word `changed`
- **THEN** the IDE shows the debugger's error message and `${x}` keeps its value

### Requirement: Frames show their keyword, test or suite

The Frames view SHALL show each frame with the name of its keyword, test or suite, followed by its file name and line in a secondary color. Frames without a source file SHALL be shown dimmed. Selecting a frame SHALL show its source at the frame's line and column.

#### Scenario: Paused inside a keyword

- **WHEN** the run is paused inside a user keyword called from a test
- **THEN** the top frame shows the keyword's name with its file and line, the frames below show the test and the suites, and a directory suite without a source file is dimmed

### Requirement: Expanded variables stay expanded across steps

After a step or a resume to the next stop, the Variables view SHALL restore the groups and values the user had expanded, as long as the selected frame belongs to the same keyword, test or suite at the same depth of the stack.

#### Scenario: Step over in a test

- **WHEN** the user expands the Suite and Global groups and a dictionary variable inside the Suite group, and then steps over a keyword call in the same test
- **THEN** the Suite and Global groups and the dictionary are still expanded at the next stop

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

Robot Framework line breakpoints SHALL offer a condition, a log message ("Evaluate and log") and a hit count, and the project SHALL keep them with its breakpoints. The condition SHALL be a Python expression in which Robot Framework variables are replaced, and the run SHALL stop only when it is true. The hit count SHALL take the forms the RobotCode debugger accepts, such as `3` for the third hit, `>= 3` or `% 3`, counting only the times the condition was true.

#### Scenario: Condition

- **WHEN** a breakpoint inside a `FOR` loop over the numbers 0 to 7 has the condition `${i} == 3`
- **THEN** the run stops once, with `${i}` being 3

#### Scenario: Hit count

- **WHEN** a breakpoint inside that loop has the hit count `2`
- **THEN** the run stops once, in the second iteration

#### Scenario: Hit count with an operator

- **WHEN** a breakpoint inside that loop has the hit count `% 3`
- **THEN** the run stops twice, with `${i}` being 2 and 5

#### Scenario: Settings survive a restart

- **WHEN** the user sets a condition, a log message and a hit count on a breakpoint and restarts the IDE
- **THEN** the breakpoint still has all three

### Requirement: Log messages of breakpoints

With the suspend policy None, the log message of a breakpoint SHALL be a Robot Framework template, such as `value is ${i}`, that the debugger writes to the run's output each time the line is reached, without stopping. With a suspending policy, the log message SHALL be evaluated like a watch when the run stops at the breakpoint, and its result SHALL be logged.

#### Scenario: Log message without stopping

- **WHEN** a breakpoint inside a `FOR` loop over the numbers 0 to 7 has the suspend policy None and the log message `value is ${i}`
- **THEN** the output shows `value is 0` to `value is 7`, one line per iteration, and the run does not stop

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

### Requirement: Stop ends a Robot Framework run gracefully

When the user stops a Robot Framework run that the IDE started, in a Run or a Debug session, or reruns it while it is still running, the plugin SHALL ask the RobotCode debugger to end the run, so that Robot Framework stops gracefully: the running test fails, the remaining tests are not run, teardowns run, and the output files are written. This SHALL work whether the run is paused in the debugger or running.

#### Scenario: Stop while paused at a breakpoint

- **WHEN** a debug session is paused at a breakpoint in a test and the user presses Stop once
- **THEN** the run ends without a further Stop, Robot Framework reports a single stop signal ("Second signal will force exit.") and no forced exit ("Execution forcefully stopped."), the stopped test fails, and `output.xml`, `log.html` and `report.html` are written
- **AND** the Debug tool window no longer shows the run as paused while it ends

#### Scenario: Stop a running test

- **WHEN** a test that runs `Sleep    30s` is started with Run and the user presses Stop once
- **THEN** the run ends within a few seconds, the test fails with "Execution terminated by signal", and `output.xml`, `log.html` and `report.html` are written

#### Scenario: Rerun a paused debug session

- **WHEN** a debug session is paused at a breakpoint and the user reruns it
- **THEN** the paused run ends gracefully and the new run starts without the user killing the old process

### Requirement: While a stopped run is ending

While the debugger handles the request to end a stopped run, the plugin SHALL NOT send a signal to the process. If the debugger is not connected, or does not confirm the request within five seconds, the plugin SHALL interrupt the process instead. A second Stop while the run is ending SHALL kill the process. Once a paused run continues towards its end, the debug session SHALL no longer show it as paused.

#### Scenario: Debugger does not confirm

- **WHEN** the user stops a run whose debugger connection is not established, or whose debugger does not confirm the stop request within five seconds
- **THEN** the plugin interrupts the process, as Stop did before this change

#### Scenario: Kill a run that is ending

- **WHEN** the user presses Stop again while a stopped run is still executing its teardowns
- **THEN** the process is killed

### Requirement: Concurrent Robot Framework runs use separate debugger ports

Every Robot Framework Run and Debug session SHALL connect to its RobotCode debugger through a port of its own, chosen when the run starts instead of a fixed preferred port, and SHALL pass that port to robotcode explicitly. Runs started at the same time SHALL NOT connect to each other's debugger.

#### Scenario: Compound configuration

- **WHEN** a compound run configuration starts two Robot Framework configurations at the same time
- **THEN** the two runs use different debugger ports, and each run's test results are complete

#### Scenario: Multiple instances

- **WHEN** a Robot Framework configuration with "Allow multiple instances" is started a second time while its first run is still running
- **THEN** both runs complete, each with its own results

### Requirement: Run and Debug do not block the user interface

Starting a Robot Framework Run or Debug session, and every debugger action, SHALL NOT block the IDE's user interface while the plugin waits for the process or the RobotCode debugger. Debugger actions are stepping, resuming, pausing, Run to Cursor, evaluating, computing frames and variables, loading the next items of a long list, changing a variable's value with Set Value, and adding, changing or removing breakpoints.

#### Scenario: Start a run

- **WHEN** the user starts a test from the gutter with Run or Debug
- **THEN** the IDE's user interface is not blocked while the plugin starts the process and connects to the debugger

#### Scenario: Change a breakpoint while paused

- **WHEN** the run is paused and the user disables or enables a breakpoint
- **THEN** the IDE's user interface is not blocked while the change is sent to the debugger

#### Scenario: Set Value while paused

- **WHEN** the run is paused and the user changes the value of a local variable with Set Value
- **THEN** the IDE's user interface is not blocked while the debugger sets and evaluates the new value

### Requirement: Waits for the debugger are bounded

Every wait for the debugger SHALL be bounded, with a bound longer than the debugger's own limit for a keyword evaluation, so that an evaluation the debugger is still working on is not abandoned by the plugin.

#### Scenario: Evaluate a slow keyword

- **WHEN** the run is paused and the user evaluates `Sleep    5s` in the Evaluate dialog
- **THEN** the IDE stays responsive during the five seconds, and the dialog shows the result afterwards

### Requirement: A debugger that does not connect is reported

If the RobotCode debugger of a run does not accept the connection within 15 seconds while the process is running, the plugin SHALL write a message to the run's console and end the process. If the process ends before the connection was made, the run SHALL end with the process's exit code. In both cases the run's test results SHALL end, and the plugin SHALL NOT report an IDE error.

#### Scenario: Process ends before the debugger listens

- **WHEN** the Robot Framework process of a Debug session is killed before its debugger accepts connections
- **THEN** the console shows the exit code, the test results do not stay at "Running tests…", and no "IDE error occurred" notification appears

#### Scenario: Debugger never accepts the connection

- **WHEN** the process of a run is alive but its debugger does not accept the connection within 15 seconds
- **THEN** the console says that the debugger did not accept the connection, the process is ended, and no "IDE error occurred" notification appears

### Requirement: Evaluation contexts and errors

Evaluations from the Evaluate dialog and the inline evaluation field SHALL use the debugger's REPL semantics: a single variable shows its value, anything else runs as a keyword call. Watches SHALL be evaluated as expressions, as in VS Code: a watch SHALL run a keyword only when it starts with `! `, and an unknown variable SHALL show `<undefined>`. When the debugger answers an evaluation with an error, the IDE SHALL show the debugger's message and SHALL NOT report an IDE error.

#### Scenario: Watches are expressions

- **WHEN** the watches `1 + 2`, `${UNKNOWN}` and `Log    watch-side-effect` exist and the run stops twice
- **THEN** the first watch shows `3`, the second shows `<undefined>`, the third shows the debugger's error message, and `watch-side-effect` is never logged

#### Scenario: Keyword call in a watch

- **WHEN** the run is paused and the watch `! Get Length    ${items}` exists, where `@{items}` has three items
- **THEN** the watch shows `3`

#### Scenario: Keyword call in the Evaluate dialog

- **WHEN** the run is paused and the user evaluates `Catenate    a    b` in the Evaluate dialog
- **THEN** the dialog shows `'a b'`

#### Scenario: Error message

- **WHEN** the run is paused and the user evaluates `1 + 2` in the Evaluate dialog
- **THEN** the dialog shows the debugger's message that no keyword with the name `1 + 2` was found, and no "IDE error occurred" notification appears
