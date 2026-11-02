---
title: Sessions in the Background with robotcode session
description: 'Run the REPL or a debug run in the background with robotcode session and give it one input after the other from separate commands, as an AI agent does: send, wait, interrupt, status, result, restart, list and stop.'
sidebar:
  label: Sessions
  order: 55
---

:::tip[Installation]
`robotcode session` comes with the optional **`repl`** package, like [`robotcode repl`](/guides/cli/repl/) and [`robotcode robot-debug`](/guides/cli/robot-debug/). If it isn't installed yet, add it:

```bash
pip install "robotcode[repl]"   # or: pip install "robotcode[all]"
```
:::

`robotcode session` runs [`robotcode repl`](/guides/cli/repl/) or [`robotcode robot-debug`](/guides/cli/robot-debug/) in the background and lets separate commands drive it. Each `robotcode session send` gives the session one input, prints what it printed and returns, while the session keeps its variables, its imports and its paused run for the next command.

It is made for AI agents: their tools run one command at a time and can't type into a program that keeps running, so they can't hold a REPL or a debugger open between your prompts on their own. With a session, every agent works the same way on Linux, macOS and Windows. You can drive a session from a script or a terminal just as well.

## Starting a session

```bash
robotcode session start repl [OPTIONS of robotcode repl]
robotcode session start debug [OPTIONS and arguments of robotcode robot-debug]
```

`start` prints the ID of the new session, `repl-` or `debug-` followed by eight hexadecimal characters, and the output of the session until it waits at its first prompt: for a REPL, that is mostly nothing; for a debug run, its output up to its first stop.

```text
$ robotcode session start repl
Started session repl-1506c2de.
```

```text
$ robotcode session start debug --break tests/orders.robot:19 -bl "Tests.Orders"
Started session debug-14dc7014.
==============================================================================
Tests :: Web shop acceptance tests
==============================================================================
Tests.Orders :: Placing orders.
==============================================================================
Order Coffee :: An order for a product in stock is placed.
* breakpoint  orders.Order Status Should Be  (tests/orders.robot:19)
```

The other commands take this ID. A session runs in the folder `start` was called in, with the project's `robot.toml`, and with the options of `robotcode` itself that `start` got, such as `-p` for a profile: `robotcode -p dev session start repl`. A debug run that ends before it stops anywhere leaves its session open, as every end does; `start` then prints the run's output and its exit code, see [The end of a REPL or a run](#the-end-of-a-repl-or-a-run).

`start` returns once the session takes commands, so that `wait` and the other commands always reach it. Its `--timeout` is for the first prompt: when the process takes longer to start, `start` returns as soon as the session takes commands, with exit code `124`, and `wait` prints the rest. A session that isn't ready within 60 seconds, or within `--timeout` when that is longer, is ended, and `start` exits with code `252`.

## Sending an input

```bash
robotcode session send ID 'INPUT'
```

`send` gives the input to the prompt the session waits at and prints the output up to the next prompt. That output is the standard output and the standard error of the session together, in the order in which both were written. Put the input in single quotes, in bash and zsh as in PowerShell, so that the shell leaves `${…}` alone. An agent that tries out the keywords of a resource file for you works like this, one command per turn:

```text
$ robotcode session send repl-1506c2de 'Import Resource    ${CURDIR}/resources/orders.resource'
$ robotcode session send repl-1506c2de '${order}=    Create Order    coffee    quantity=2'
[ INFO ] Ordered 2 x coffee (express: False)
[ INFO ] ${id} = order-4711
[ INFO ] ${order} = order-4711
$ robotcode session send repl-1506c2de 'Create Order    mug'
[ INFO ] Ordered 1 x mug (express: False)
[ FAIL ] mug is out of stock
```

Each `send` is a whole input, which the session runs as `robotcode repl` runs a script file. A `FOR` loop or an `IF` goes in one `send`, as a text of several lines, also at a debug stop; a block the text leaves unfinished fails with the error of Robot Framework, such as `FOR loop must have closing END.`, and the next `send` starts a new input. In bash and zsh, the line breaks go inside the single quotes; in PowerShell, a here-string takes them:

```bash
robotcode session send repl-1506c2de 'FOR    ${i}    IN    a    b
    Log To Console    round ${i}
END'
```

```powershell
robotcode session send repl-1506c2de @'
FOR    ${i}    IN    a    b
    Log To Console    round ${i}
END
'@
```

Dot-commands work as at the prompt: `.vars`, `.kw` or `.doc` in a REPL, and in a debug session also `.continue`, `.step` or `.where`. Each is an input of its own, so `.break …` and `.continue` go in two `send`s:

```text
$ robotcode session send debug-14dc7014 '.vars --user'
Local:
    (none)
Test:
    ${order} = 'order-4711'
Suite:
    (none)
Global:
    ${BASE_URL} = 'http://localhost:8080'
    ${BROWSER} = 'chromium'
```

When `.continue` lets a debug run go on to its end, `send` prints the rest of the run's output and the run's exit code, and the session stays open, see [The end of a REPL or a run](#the-end-of-a-repl-or-a-run).

## Exit codes

The exit code of `send` says how the input went, so a script or an agent doesn't have to read it from the output:

| Exit code | Meaning |
| --- | --- |
| `0` | The statement passed. |
| `1` | The statement failed. |
| `124` | It still runs after `--timeout`; `session wait` prints the rest. |
| `252` | An error of robotcode itself, such as an ID without an open session, or a `send` after the end of the REPL or the run. |

`session wait`, `session start` and `session restart` exit the same way. The exit code of the REPL or the run is never the exit code of a `session` command, as Robot Framework gives exit codes a meaning of its own, the number of failed tests: the commands print it, and `session result` prints it on its own, see [The end of a REPL or a run](#the-end-of-a-repl-or-a-run).

## Statements that run long

`send` waits at most 60 seconds for its answer, or as many as `--timeout` says. After that it prints the output so far and exits with `124`, while the statement goes on in the session. `session wait ID` waits until the session is at its prompt again, or its REPL or run has ended, prints the rest and exits with the code `send` would have had:

```text
$ robotcode session send --timeout 1 repl-1506c2de 'Sleep    3s'
It still runs; `robotcode session wait repl-1506c2de` prints the rest.
$ robotcode session wait repl-1506c2de
[ INFO ] Slept 3 seconds.
```

`wait` and `start` take `--timeout` too. Without the limit, the tool of an agent would cut the command off after its own timeout, without the agent knowing that the statement still runs.

`session interrupt ID` acts on the session as `Ctrl-C` does at its terminal. In a REPL, the statement that runs fails with `Execution interrupted`. In a debug session, the run pauses at the next keyword, and `session wait` shows the stop; a second `interrupt` interrupts the keyword that runs, as a second `Ctrl-C` does.

## The end of a REPL or a run

When the REPL exits with `.exit` or the debug run ends, the session stays open, as a debugger stays open after its program has ended. The command that waits for the end, or else the next `wait`, prints the rest of the output and, on standard error, the exit code of the REPL or the run:

```text
$ robotcode session send debug-14dc7014 '.continue'
| PASS |
------------------------------------------------------------------------------
Express Order :: An express order is marked as such.                  | PASS |
------------------------------------------------------------------------------
Sold Out Product Cannot Be Ordered :: The shop refuses an order fo... | PASS |
------------------------------------------------------------------------------
Tests.Orders :: Placing orders.                                       | PASS |
3 tests, 3 passed, 0 failed
==============================================================================
Tests :: Web shop acceptance tests                                    | PASS |
3 tests, 3 passed, 0 failed
==============================================================================
Output:  /home/user/webshop/results/output.xml
Log:     /home/user/webshop/results/log.html
Report:  /home/user/webshop/results/report.html
The run has ended with exit code 0.
```

Whether a command waited at the end doesn't matter: after a `send` that returned with `124`, the next `wait` gets the rest. From then on:

- `robotcode session status ID` prints `ended`. Before, it prints `runs` while the session runs and `waits` while it waits at its prompt. `status` takes none of the output, which `wait` prints, so a script can call `wait` in a loop until `status` says `ended`.
- `robotcode session result ID` prints the exit code of the REPL or the run, such as `2` for a run in which two tests failed, and exits with `0`. Before the end, it says that the REPL or the run hasn't ended and exits with `252`.
- `send` and `interrupt` fail with `252` and name `restart`.

```text
$ robotcode session status debug-14dc7014
ended
$ robotcode session result debug-14dc7014
0
```

## Restarting a session

`robotcode session restart ID` starts the REPL or the debug run of a session again, in a new process under the same ID. A REPL or a run that hasn't ended is ended first, as `stop` does. The new process starts with the options of `session start`, so that a debug run starts from its beginning, and it gets the breakpoints as they are: also those that `.break` set during the session, without those that `.delete` removed, also from the command line, and with the conditions of `.condition`. As a new process, it uses Python libraries as they are now, also when you have changed them since the start. `restart` prints the output since the last command, and then the new output as `start` does:

```text
$ robotcode session restart debug-14dc7014
Restarted session debug-14dc7014.
==============================================================================
Tests :: Web shop acceptance tests
==============================================================================
Tests.Orders :: Placing orders.
==============================================================================
Order Coffee :: An order for a product in stock is placed.
* breakpoint  orders.Order Status Should Be  (tests/orders.robot:19)
```

A restarted REPL session starts without the variables and imports of before. When the new process doesn't get ready, `restart` prints what it wrote and exits with `252`, and the session stays as it was.

## Ending a session

A session ends:

- with `robotcode session stop ID`, which prints the output since the last command. A debug run that hasn't ended is aborted as with `.abort`, without reports; with the debugger detached, it ends as on `Ctrl-C`;
- with `robotcode session stop --project`, together with the other sessions of the project the current folder belongs to, the folder RobotCode finds for its `robot.toml`. A session belongs to the project of the folder `session start` ran in, also when a debug run's suite lies elsewhere;
- with `robotcode session stop --all`, together with all your other sessions;
- when it has waited for 15 minutes without a request, at its prompt or after the end of its REPL or run, so that a forgotten session doesn't keep a browser open. `--idle-timeout MINUTES` at the start changes the time; a statement that runs doesn't count as waiting;
- when its process gets SIGTERM from another process, as at a shutdown on Linux or macOS, together with its REPL or run.

`robotcode session list` shows the open sessions, whether they run, wait at their prompt or their REPL or run has ended, and how long they wait until they end:

```text
$ robotcode session list
ID              PROJECT             STATE  IDLE TIME LEFT
repl-1506c2de   /home/user/webshop  waits  14:32
debug-14dc7014  /home/user/webshop  runs   -
```

## Structured output

With the option `--format json` of `robotcode`, `send` and `wait` print one object with the output and the status (`passed`, `failed` or `running`), and, once the REPL or the run has ended, its exit code as `exit_code`. `status` and `result` print an object with the `state` or the `exit_code`, and `list` prints a list of the sessions:

```text
$ robotcode --format json session send repl-1506c2de 'Evaluate    1 + 1'
{"output":"=> 2\n","status":"passed"}
$ robotcode --format json session wait debug-14dc7014
{"output":"","status":"passed","exit_code":0}
```

## Where a session keeps its files

Each open session has a file in a folder only you can open: `$XDG_RUNTIME_DIR/robotcode/sessions` on Linux, `~/Library/Caches/TemporaryItems/robotcode/sessions` on macOS and `%LOCALAPPDATA%\Temp\robotcode\sessions` on Windows. The `session` commands find a session by its ID there and talk to it over a local channel, a Unix socket on Linux and macOS and a named pipe on Windows, which takes only requests that bring the session's key from that file. The output of a session stays in its memory until a `session` command gets it; no file holds it. A session whose process has gone, after a crash for example, is removed by the next `session` command that finds its file.

## Where sessions can't run

A session has to write that folder, open its channel and keep running after the command that started it has returned. Whether it can depends on what the sandbox of an AI agent covers:

- **A sandbox around the whole agent**, such as a container, a dev container or a virtual machine: sessions work there without any setting, and nothing outside that sandbox sees them. An agent's own sandbox for each command has to be off in there; Codex's is on by default (`--sandbox danger-full-access`).
- **A sandbox for each command**, which Codex uses by default and Claude Code and GitHub Copilot CLI offer: a session can't outlive the command that started it. `session start` says what it can't do and exits with code `252`. An agent with a tool that writes to a running command, as Codex has, can drive [`robotcode repl`](/guides/cli/repl/) or [`robotcode robot-debug`](/guides/cli/robot-debug/) in its own terminal instead. Claude Code and Copilot CLI have no such tool and have to find another way.

This was checked on Linux and on Windows, where Claude Code has no such sandbox; the way through the terminal only on Linux. macOS is not checked.
