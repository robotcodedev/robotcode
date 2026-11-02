# cli-sessions Specification

## Purpose

REPL and debug sessions that run in the background and that separate `robotcode session` commands start, send inputs to, wait for, interrupt, restart, list and end, so that an AI agent without a tool for running processes can work turn by turn on Linux, macOS and Windows.

## Requirements

### Requirement: Starting a session

`robotcode session start repl` and `robotcode session start debug` SHALL start a REPL or a debug run in the background, with the options of `robotcode repl` or `robotcode robot-debug`, wait until it is ready and print the session's ID and its output so far. A debug session is ready at its first stop or at the end of its run. `start` SHALL return only once the session can take commands, and SHALL end a session that isn't ready within 60 seconds, or within `--timeout` when that is longer.

#### Scenario: Start a REPL
- **WHEN** `robotcode session start repl` runs
- **THEN** it prints the ID of a new session, such as `repl-3f9a2c1e`
- **AND** it returns while the session keeps running

#### Scenario: Start a debug run
- **WHEN** `robotcode session start debug --break tests/orders.robot:19 -bl "Tests.Orders"` runs
- **THEN** it prints the run's output up to the stop at line 19 and the session's ID

#### Scenario: A debug run that ends before a stop
- **WHEN** `robotcode session start debug -bl "Tests.Orders"` runs a suite in which nothing stops the run
- **THEN** it prints the session's ID, the run's output and that the run has ended with its exit code, and exits with 0
- **AND** the session stays open

#### Scenario: A session that is slow to start
- **WHEN** the process of a session takes longer to start than the `--timeout` of `session start`
- **THEN** `start` returns once the session can take commands, with the ID and exit code 124
- **AND** `robotcode session wait` with that ID reaches the session

#### Scenario: A session that doesn't get ready
- **WHEN** a session isn't ready within 60 seconds, or within `--timeout` when that is longer
- **THEN** `start` ends its process, prints what it wrote and exits with code 252

### Requirement: Session IDs

A session's ID SHALL be its kind, `repl` or `debug`, a hyphen and eight random hexadecimal characters, such as `repl-3f9a2c1e`, and it SHALL differ from the ID of every open session. The `robotcode session` commands SHALL address a session by its ID; a session SHALL have no other name.

#### Scenario: Form of the ID
- **WHEN** `robotcode session start debug -bl "Tests.Orders"` runs
- **THEN** the ID it prints starts with `debug-`, followed by eight hexadecimal characters

#### Scenario: A new session gets a new ID
- **WHEN** the session `repl-3f9a2c1e` has been stopped and `robotcode session start repl` runs again
- **THEN** the new session gets another ID
- **AND** `robotcode session send repl-3f9a2c1e "Log    hi"` says that no such session is open

### Requirement: Sending an input

`robotcode session send <id> "<input>"` SHALL give the input to the session's prompt, print the output it causes until the session waits at its next prompt, and exit with 0 when the statement passed and 1 when it failed. The input MAY be a block of several lines, and dot commands such as `.vars` SHALL work as at the prompt. The session SHALL keep its state, such as variables and imports, from one `send` to the next.

#### Scenario: Statement
- **WHEN** `robotcode session send repl-3f9a2c1e "Evaluate    1 + 1"` runs
- **THEN** `=> 2` is printed and the command exits with 0

#### Scenario: Failing statement
- **WHEN** `robotcode session send repl-3f9a2c1e "Should Be Equal    1    2"` runs
- **THEN** the failure is printed and the command exits with 1

#### Scenario: State between calls
- **WHEN** one `send` runs `${order}=    Create Order    coffee` and a later `send` runs `Log    ${order}`
- **THEN** the second shows the order id the first one set

#### Scenario: Debugger command
- **WHEN** `send` gives `.vars --user` to a debug session paused at a stop
- **THEN** the variables are printed and the run stays paused

#### Scenario: Pass Execution or Skip at a stop
- **WHEN** `send` gives `Pass Execution    done` or `Skip    later` to a debug session paused at a stop
- **THEN** the command exits with 0, as at the prompt of a REPL session, and the run stays paused

### Requirement: A whole input per send

Each `robotcode session send` SHALL give the session a whole input, which MAY be a text of several lines, such as a `FOR` loop with its `END`, at the `>>>` prompt and at a debug stop alike. A block that the input leaves unfinished SHALL fail with the error of Robot Framework, and the next `send` SHALL start a new input. A dot-command SHALL be an input of its own: a `send` that gives one with more lines SHALL fail without running anything.

#### Scenario: A block in one send
- **WHEN** `send` gives `FOR    ${i}    IN    a    b`, `    Log To Console    round ${i}` and `END` as one text of three lines
- **THEN** both rounds are printed and the command exits with 0

#### Scenario: Unfinished block
- **WHEN** `send` gives `FOR    ${i}    IN    a    b` and `    Log To Console    round ${i}` without `END`
- **THEN** it prints `FOR loop must have closing END.`, no round, and exits with 1
- **AND** the next `send` starts a new input

#### Scenario: A block at a stop
- **WHEN** `send` gives a `FOR` loop with its `END` to a debug session paused at a stop
- **THEN** the loop runs in the paused context, and the run stays paused

#### Scenario: Two dot-commands in one send
- **WHEN** `send` gives `.vars --user` and `.vars` as one text of two lines
- **THEN** it reports as `[ ERROR ]` that dot-commands can only be sent on their own, and exits with 1

### Requirement: Waiting with a timeout

`robotcode session send` SHALL wait at most the time given with `--timeout`, 60 seconds without it. When the statement runs longer, `send` SHALL print the output so far and exit with code 124 while the statement goes on, and `robotcode session wait <id>` SHALL print the rest once the session waits at its prompt again or its REPL or run has ended, with the exit code `send` would have had.

#### Scenario: Statement longer than the timeout
- **WHEN** `robotcode session send repl-3f9a2c1e --timeout 2 "Sleep    5s"` runs
- **THEN** it returns after about 2 seconds with exit code 124
- **AND** `robotcode session wait repl-3f9a2c1e` returns when `Sleep` has ended, with exit code 0

### Requirement: Interrupting a session

`robotcode session interrupt <id>` SHALL act on the session as Ctrl-C does at the terminal of `robotcode repl` or `robotcode robot-debug`.

#### Scenario: Statement in a REPL session
- **WHEN** `Sleep    60s` runs in a REPL session with the debugger detached and `robotcode session interrupt repl-3f9a2c1e` runs
- **THEN** `Sleep` fails with `Execution interrupted`, and the session waits at its prompt again

#### Scenario: Running debug session
- **WHEN** a debug session runs after `.continue` and `robotcode session interrupt debug-7b2d9e04` runs
- **THEN** the run pauses at the next keyword, and `robotcode session wait debug-7b2d9e04` shows the stop

### Requirement: Ending a session

A session SHALL end with `robotcode session stop <id>`, also while a statement or its run is busy, when it has waited for 15 minutes without a request, at its prompt or after its REPL or run has ended, and with a SIGTERM from outside; `--idle-timeout` at the start SHALL change that time. A statement that runs SHALL NOT count as waiting. Ending a debug session before its run ends SHALL stop the run as `.abort` does.

#### Scenario: Stop
- **WHEN** `robotcode session stop repl-3f9a2c1e` runs
- **THEN** the session's process ends, and `robotcode session list` no longer shows it

#### Scenario: Idle session
- **WHEN** a session started with `--idle-timeout 1` waits at its prompt for a minute without a request
- **THEN** the session ends

#### Scenario: Idle after the end
- **WHEN** the run of a debug session started with `--idle-timeout 1` has ended and a minute passes without a request
- **THEN** the session ends

#### Scenario: SIGTERM from outside
- **WHEN** the process of a session gets SIGTERM from another process, as at a shutdown
- **THEN** the REPL or the run ends, and the session ends with it

### Requirement: The end of a REPL or a run

When the REPL of a session exits or its run ends, the session SHALL stay open. The command that waits, or else the next `wait`, SHALL print the rest of the output and that the REPL or the run has ended with its exit code, and exit as for its input. The exit code of the REPL or the run SHALL NOT be the exit code of a `session` command. A `send` or an `interrupt` after the end SHALL fail with exit code 252.

#### Scenario: End of a debug run
- **WHEN** `send` gives `.continue` to a debug session and the run, in which two tests fail, reaches its end
- **THEN** `send` prints the rest of the run's output and `The run has ended with exit code 2.`, and exits with 0
- **AND** the session stays open

#### Scenario: The end while no command waits
- **WHEN** `send --timeout 1` gives `.continue` to a debug session and exits with 124, and the run ends before the next command
- **THEN** `robotcode session wait` prints the rest of the run's output and that the run has ended with its exit code, and exits with 0

#### Scenario: `.exit` in a REPL session
- **WHEN** `send` gives `.exit` to a REPL session in which a statement failed
- **THEN** it prints `The REPL has ended with exit code 1.` and exits with 0
- **AND** the session stays open

#### Scenario: A send after the end
- **WHEN** `send` gives `Log    hello` to a session whose run has ended
- **THEN** it says that the run has ended and that `robotcode session restart` starts it again, and exits with 252

### Requirement: The state of a session

`robotcode session status <id>` SHALL print at once whether the session runs, waits at its prompt or its REPL or run has ended, as `runs`, `waits` or `ended`, and exit with 0. It SHALL take none of the session's output.

#### Scenario: A debug run at a stop
- **WHEN** a debug session has stopped at a breakpoint
- **THEN** `robotcode session status debug-7b2d9e04` prints `waits`

#### Scenario: The output stays for wait
- **WHEN** `send --timeout 1` has returned with 124 while its statement writes to the console, and `status` runs
- **THEN** it prints `runs`, and the next `wait` prints all the output of the statement

#### Scenario: After the end
- **WHEN** the run of a debug session has ended
- **THEN** `status` prints `ended`

### Requirement: The result of a REPL or a run

`robotcode session result <id>` SHALL print the exit code of the session's REPL or run once it has ended, and exit with 0. Before the end, it SHALL say that the REPL or the run hasn't ended and exit with code 252.

#### Scenario: A run with two failed tests
- **WHEN** the run of a debug session in which two tests failed has ended
- **THEN** `robotcode session result debug-7b2d9e04` prints `2` and exits with 0

#### Scenario: Before the end
- **WHEN** the run of a debug session waits at a stop
- **THEN** `result` says that the run hasn't ended and exits with code 252

### Requirement: Restarting a session

`robotcode session restart <id>` SHALL end the REPL or the run of the session as `stop` does, but not the session, and start it again in a new process under the same ID, with the options of `session start` and the breakpoints as they are at the restart. It SHALL print the output since the last command and then answer as `session start` does. When the new process doesn't get ready, the session SHALL stay open, and `restart` SHALL exit with code 252.

#### Scenario: A restart at a stop
- **WHEN** `robotcode session restart debug-7b2d9e04` runs while the run waits at a stop
- **THEN** the run starts again from its beginning in a new process under the ID `debug-7b2d9e04`, and `restart` prints its output up to its first stop

#### Scenario: Breakpoints as they are
- **WHEN** at a stop `.break` has added a breakpoint, `.delete` has removed one given with `--break`, and `restart` runs
- **THEN** the new run stops at the added breakpoint and not at the removed one

#### Scenario: A changed Python library
- **WHEN** a Python library of the suite has been changed since the start and `restart` runs
- **THEN** the new run uses the changed library

#### Scenario: A REPL session
- **WHEN** `restart` runs for a REPL session in which `${order}` was set
- **THEN** `${order}` isn't set in the new REPL

#### Scenario: A restart that fails
- **WHEN** the new process ends before it is ready
- **THEN** `restart` prints what it wrote and exits with code 252
- **AND** the session stays open, and `status` prints `ended`

### Requirement: Stopping several sessions

`robotcode session stop --project` SHALL end every open session of the project the current folder belongs to, the folder RobotCode finds for its `robot.toml`, and `robotcode session stop --all` every open session of the user. A session SHALL belong to the project of the folder `session start` ran in.

#### Scenario: The sessions of the project
- **WHEN** sessions are open in two projects and `robotcode session stop --project` runs in one of them
- **THEN** the sessions of that project end, and those of the other stay open

#### Scenario: A debug run of a suite of another project
- **WHEN** `robotcode session start debug ../other/tests` ran in a project
- **THEN** `robotcode session stop --project` in that project ends the session

#### Scenario: All sessions
- **WHEN** sessions are open in two projects and `robotcode session stop --all` runs
- **THEN** all of them end

### Requirement: Listing sessions

`robotcode session list` SHALL show each open session of the user with its ID, its project folder, whether it runs, waits or its REPL or run has ended, and the time left until it ends for being idle.

#### Scenario: Two sessions
- **WHEN** a REPL session and a debug session are open
- **THEN** `robotcode session list` shows both, each with its ID, project folder, state and the time left

### Requirement: Structured output

With the global option `--format json`, `robotcode session send` and `robotcode session wait` SHALL print one object with the output, the status (`passed`, `failed` or `running`) and, once the REPL or the run has ended, its exit code as `exit_code`. `robotcode session status` and `robotcode session result` SHALL print an object with the state or the exit code.

#### Scenario: Result as JSON
- **WHEN** `robotcode --format json session send repl-3f9a2c1e "Evaluate    1 + 1"` runs
- **THEN** it prints an object whose output contains `=> 2` and whose status is `passed`

#### Scenario: The end as JSON
- **WHEN** `robotcode --format json session send debug-7b2d9e04 .continue` runs, and the run, in which two tests fail, ends
- **THEN** it prints an object whose status is `passed` and whose `exit_code` is 2

### Requirement: Unknown session

A `robotcode session` command for an ID with no open session SHALL say that no such session is open and exit with code 252.

#### Scenario: Send to a session that isn't open
- **WHEN** `robotcode session send repl-0d1e2f3a "Log    hello"` runs and no session `repl-0d1e2f3a` is open
- **THEN** it says that no session `repl-0d1e2f3a` is open and exits with code 252

### Requirement: Platforms and access

Sessions SHALL work on Linux, macOS and Windows. A session SHALL accept requests only from processes of the user who started it.

#### Scenario: Windows
- **WHEN** a REPL session is started, driven with `send` and stopped in PowerShell on Windows
- **THEN** it behaves as on Linux

#### Scenario: Another user
- **WHEN** a process of another user connects to a session's channel
- **THEN** the session refuses the connection

#### Scenario: No runtime folder in the environment
- **WHEN** a `robotcode session` command runs on Linux without `$XDG_RUNTIME_DIR`, as in a container
- **THEN** it works in the folder that platformdirs falls back to and prints no warning about it

### Requirement: Output in memory

A session SHALL keep its output, the standard output and standard error of its process and of the processes it starts, in memory until a `session` command gets it, and SHALL write it to no file. Output a command has got SHALL be dropped; output written after an answer SHALL come with the next answer.

#### Scenario: No output on disk
- **WHEN** a REPL session has answered a `send` whose statement wrote to the console
- **THEN** no file in the folder of the sessions holds that output

#### Scenario: Output after an answer
- **WHEN** a thread of a REPL session writes a line after the session has answered a `send`
- **THEN** the answer to the next `send` starts with that line

#### Scenario: Long output
- **WHEN** a statement writes 3 MB to the console
- **THEN** it runs to its end, and the answer carries all of it

### Requirement: Where sessions can't run

`robotcode session start` SHALL say why it can't start a session and exit with code 252 when it can't write the files of the session in the folder of the sessions or the session can't open its channel, as in the sandbox of an agent. The other `session` commands SHALL work where that folder can't be written.

#### Scenario: A folder that can't be written
- **WHEN** `robotcode session start repl` runs where the folder of the sessions can't be created or written
- **THEN** it names the folder and the reason, without a traceback, and exits with code 252
- **AND** `robotcode session list` runs there without an error

#### Scenario: A channel that can't be opened
- **WHEN** the session that `robotcode session start repl` starts can't open its channel
- **THEN** `start` prints the address of the channel and the reason, without a traceback, and exits with code 252

### Requirement: Ended sessions

A session SHALL count as ended when nothing listens on its channel any more, also when another process has its process ID, and the next `session` command that finds its file SHALL remove its files. A session whose channel a command can't reach for another reason, such as a sandbox that forbids it, SHALL keep its files, and so SHALL a session that restarts.

#### Scenario: A command during a restart
- **WHEN** a `session` command finds the channel of a session gone because the session has just restarted in a new process
- **THEN** it reaches the new process and doesn't remove the files of the session

#### Scenario: The process of a session has gone
- **WHEN** the process of a session has ended without removing its file, after a crash for example
- **THEN** the next `robotcode session list` doesn't show it and removes its files

#### Scenario: Another process ID in a sandbox
- **WHEN** a `session` command runs where the process ID of an open session belongs to no process, as in a sandbox with processes of its own
- **THEN** it reaches the session as it does elsewhere

#### Scenario: A channel the command may not reach
- **WHEN** `robotcode session send` can't connect to the channel of an open session, because a sandbox forbids it for example
- **THEN** it says that the session doesn't answer and exits with code 252
- **AND** the session keeps its files

### Requirement: Sandboxes in the guide on sessions

The guide on sessions SHALL say that sessions work without any setting when the whole agent runs in one sandbox, such as a container, a dev container or a virtual machine, and that nothing outside that sandbox sees them. It SHALL say that they don't work where each command of an agent has a sandbox of its own, and what an agent does there instead. It SHALL NOT describe settings or rules that lead out of a sandbox or open it.

#### Scenario: One sandbox around the whole agent
- **WHEN** a reader looks up whether sessions work in a container
- **THEN** the guide says that they work without any setting and that an agent's own sandbox for each command has to be off in there

#### Scenario: A sandbox for each command
- **WHEN** a reader looks up why `session start` exits with code 252 in the sandbox of an agent
- **THEN** the guide says that a session can't outlive the command that started it there, and that an agent with a tool that writes to a running command drives `robotcode repl` or `robotcode robot-debug` in its terminal

#### Scenario: What was checked
- **WHEN** a reader looks up on which systems this holds
- **THEN** the guide names Linux and Windows and says that macOS is not checked
