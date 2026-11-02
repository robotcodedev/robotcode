# Debugging a run — `robotcode robot-debug`

`robotcode robot-debug` (alias `run-debug`) is a `pdb`-style **command-line debugger** for Robot Framework. It runs a real `.robot` suite through the same runner as [`robotcode robot`](../SKILL.md) — honoring `robot.toml`, profiles, variables, and the project environment — but **pauses at breakpoints** and drops you into a `(rdb)` debug prompt with the live call stack, the variables in each frame, a source listing, and the ability to run any keyword in the paused context.

Reach for the debugger when a recorded log isn't enough and you need the **live** state at the moment a test goes wrong — the real call stack, a variable's value at a specific point, or the result of running a keyword against the paused context. It is the third failure-analysis tool, and the most expensive; pick deliberately:

- **[`results`](results.md)** reads a *finished* `output.xml` — no re-run. Try it **first** for "why did X fail?".
- **[REPL](repl.md)** builds state up from scratch to *explore* — no suite is running.
- **The debugger** re-runs the suite and stops it **mid-flight** to inspect the actual live state. Use it only when the recorded log doesn't answer the question.

Beyond post-mortem analysis, `robot-debug` also makes a tight **inner loop while you develop or fix a test**: run the test through it instead of a plain `robot` run, and break-on-failure (on by default) stops you at the failure in the live context — inspect, then prove a fix by running the corrected keyword right there. That trial is ephemeral, so once it works **write the fix back into the `.robot` / `.resource` file** and re-run to confirm — running a keyword at the prompt doesn't change the source; `.continue` only carries the current run on. A clean pass just runs to completion, so it doubles as a quick "does it run?" check.

**To debug why a test fails, debug *that* test.** Find its longname (from [`results`](results.md) or `discover`), then:

- **Select it [by longname](../SKILL.md#selecting-one-test-or-suite), not the `.robot` file.** A bare path also stops at the **first** failure in the file, which may be a different test.
- **Read the recorded error with [`results`](results.md) first.** It often already names the cause — a variable or value, not what poking the live system would suggest — so bring up the debugger for the live values only if you still need them.
- **Don't detour into external tools or a separate exploration of the system under test first.** That debugs the wrong context and routinely chases the wrong cause.

## Contents

- **[Start or reuse a debug session](#start-or-reuse-a-debug-session)** — how to run it, step by step
- **[Two ways in](#two-ways-in)** — `robot-debug` (a real run, scoped to the tests you select) vs. `repl` (keywords typed at the prompt)
- **[How a debug session works](#how-a-debug-session-works)** — the pause → inspect → resume loop
- **[Setting breakpoints](#setting-breakpoints)** — line, keyword, location vs. run scope, embedded `Breakpoint`, stop-on-entry, exceptions
- **[At a stop: inspecting state](#at-a-stop-inspecting-state)** — stack & frames, variables, source, what's loaded (keywords / libraries / resources)
- **[Stepping & resuming](#stepping--resuming)**
- **[Managing breakpoints at runtime](#managing-breakpoints-at-runtime)** — conditions, ignore counts, logpoints
- **[Exception breakpoints](#exception-breakpoints)** — `.catch`
- **[Ending a session](#ending-a-session)** — `.detach` / `.abort`

## Start or reuse a debug session

If a debug session of this project is already open (`robotcode session list`), reuse it: `robotcode session restart <ID>` runs it again.

The debugger is an **interactive** program: it stops at a breakpoint, prints the `(rdb)` prompt, and waits. Drive it step by step: at each stop you read `.where` / `.vars` / `.print ${x}` and pick the next command from what you just saw, stepping with `.step` / `.next` / `.continue` exactly as the [session loop](#how-a-debug-session-works) describes. You don't decide the commands up front — choosing each step from the live state *is* debugging, and it's the reason you stopped the run instead of reading the recorded log.

**Can your shell tool keep a command running and write to its input?** Tools such as `write_stdin` or `send_to_terminal` do that; a background process that you feed through a file or a FIFO doesn't count.

- **Yes:** start `robotcode robot-debug` with its options there and work at its prompt: write one command, wait until the output ends with the prompt `(rdb) `, read the answer, then choose the next command from what you saw.
- **No:** run it as a **session**:

```bash
robotcode session start debug --break tests/login.robot:42 -bl "Project.Login"   # runs to the first stop; prints the ID and the output up to there
robotcode session send debug-7b2d9e04 '.vars --user'
robotcode session send debug-7b2d9e04 '.break resources/login.resource:17'
robotcode session send debug-7b2d9e04 '.continue'                                # returns at the next stop, or at the end of the run
```

- `start debug` takes the full `robotcode robot-debug` option set; options of `robotcode` itself (`-p …`) go before `session`. A run that ends before it stops anywhere prints its whole output with `start`.
- **One `send` per command or keyword**, in single quotes, and read its answer before the next step: no two steps in one shell command, no shell loop over inputs. A dot command goes in a `send` of its own, so `.break …` and `.continue` are two `send`s; a keyword block with its `END` is one `send`.
- **Exit code of `send`:** `0` / `1` the command or keyword passed / failed, `124` the run still goes after `--timeout` (default 60 s; `robotcode session wait <ID>` waits for the next stop or the end), `252` an error of robotcode itself. When the run ends, the answer ends with `The run has ended with exit code N.` (N counts the failed tests); then `robotcode session status <ID>` prints `ended`, and `robotcode session result <ID>` prints N.
- `robotcode session interrupt <ID>` pauses a running run at the next keyword, as `Ctrl-C` does.
- The session **stays open after the run**, as a debugger does: `robotcode session restart <ID>` runs it again in a new process — with the breakpoints as they are, and with Python libraries you changed since — and `robotcode session stop <ID>` ends it, mid-run too (as `.abort`). Stop it when you are done.

If a `session` command fails in a sandbox, your agent runs each command in a sandbox of its own, and a session can't outlive that command. Don't try to leave the sandbox. See [repl.md](repl.md#start-or-reuse-a-repl) for what the messages are and what works.

## Two ways in

- **`robotcode robot-debug`** (alias `run-debug`) — debug a run, scoped however you need: narrow it to a single test with `-t`/`-bl` (the usual case when debugging one failure), to a suite or tag, or run the lot. Takes the **full [`robotcode robot`](../SKILL.md) option set** (paths, `-v`, `-i`/`-e`/`-s`/`-t`, `--profile`, …) plus the trigger flags below.
- **`robotcode repl`** — the *same* debugger in the [REPL](repl.md), but it **starts detached**: attach it with `.debug on` or `--debugger-attached` (or `--break …`), and a keyword that reaches a breakpoint drops you into the same `(rdb)` prompt — see [repl.md](repl.md#debugging-from-the-repl).

## How a debug session works

1. **Start the run with a breakpoint armed** — a `file:line`, a keyword name, an embedded `Breakpoint`, or (by default) the first uncaught failure.
2. **Execution pauses** at the first match. A one-line banner prints and the `(rdb)` prompt opens:
   ```
   * breakpoint  Submit Login  (login.robot:42)
   (rdb)
   ```
3. **Inspect and act** — walk the stack, print variables, step, add breakpoints, or **type a keyword to run it in the paused context** (its result is echoed as `=> <value>` and any variable it assigns stays in scope, exactly like at the REPL prompt).
4. **Resume** with `.continue` (or a step command), or end the session with `.detach` / `.abort`.

## Setting breakpoints

Triggers combine freely. Pass them to `robot-debug` (most also work on `repl`):

| Trigger | How |
| --- | --- |
| **Line** | `--break path/to/test.robot:42` — pause when execution reaches that line. Repeatable. |
| **Keyword** | `--break "Open Browser"` — pause whenever that keyword is about to run. Repeatable. |
| **Embedded `Breakpoint`** | A `Breakpoint` step in a `.robot` / `.resource` — see below. No flag needed. |
| **Stop on entry** | `--stop-on-entry` (`robot-debug` only) — pause at the very first step of the run. |
| **Uncaught failure** | **On by default** — pause at the first failing keyword not caught by `TRY`/`EXCEPT` or `Run Keyword And …`, *before* it unwinds. Turn off with `--no-break-on-exception`. |
| **Other failures** | `--break-on-all-exceptions`, `--break-on-failed-test`, `--break-on-failed-suite`: see [Exception breakpoints](#exception-breakpoints). |

A **keyword breakpoint** matches keyword names the way Robot Framework does: case, spaces and underscores don't matter (`--break "open browser"` stops at `Open Browser`), the `Library.Keyword` form (`--break "SeleniumLibrary.Open Browser"`) picks one of two keywords that share a name, and glob patterns work as in Robot Framework's `--removekeywords name:` (`--break "BuiltIn.*"`, `--break "*Login*"`; a literal `[` is `[[]`). For a keyword with embedded arguments, the definition name (`.break Select ${animal} From List`) or a pattern (`.break Select * From List`) stops at every call, while the name of one call (`.break Select dog From List`) stops only at the calls written that way — argument values aren't compared, so to stop for certain values use a line breakpoint with a condition on the keyword's first body line.

### Breakpoint location vs. run scope

A `file:line` or keyword breakpoint says *where* to stop; the `robotcode robot` selectors say *what runs*. When you already know which test you're debugging, set the breakpoint where you need it **and** narrow the run to that one test:

```bash
robotcode robot-debug -bl "MyProject.Login.Login Works"                  # only this test runs; pause at its failure
robotcode robot-debug --break login.robot:42 -t "Login Works"            # break at the line, but only run that test
```

### The embedded `Breakpoint` keyword

To pause at a fixed spot without passing `--break` every time, put a `Breakpoint` step directly in the file after importing the marker library:

```robot
*** Settings ***
Library    robotcode.repl.Repl

*** Test Cases ***
Login
    Open Browser    ${URL}
    Breakpoint                  # pauses here under the debugger
    Input Text    id=user    ${USER}
```

`Breakpoint` is a **no-op in a normal `robot` run** and a **hard breakpoint** whenever the debugger is attached (under `robot-debug`, or in `repl` once you've attached with `.debug on`). (`Breakpoint` is the only keyword from `robotcode.repl.Repl` meant for your own suites; `Repl` and `Exit` are internal.)

## At a stop: inspecting state

At the `(rdb)` prompt you have the full debug command set, every shell dot-command (`.kw`, `.doc`, …), and keyword execution in context. Each command has a long name and often a one- or two-letter shortcut; long names accept any unambiguous prefix (`.cond` → `.condition`), except `.abort`, which must be typed in full.

**Stack & frames.** Execution is a stack of keyword frames — `#0` is the innermost (where you stopped), higher numbers are its callers. Variable lookups and expressions are evaluated **in the selected frame**, so moving frames changes what `.print` sees:

| Command | Effect |
| --- | --- |
| `.where` / `.w` | Show the call stack — `#0` innermost, `>` marks the selected frame. |
| `.up` / `.u` · `.down` / `.d` | Select the calling (outer) / called (inner) frame. |
| `.frame N` / `.f N` | Select frame number N directly. |

**Variables & expressions:**

| Command | Effect |
| --- | --- |
| `.vars` / `.v` | Variables in scope (Local / Test / Suite / Global), name + value; `--user` skips Robot internals. |
| `.print <expr>` / `.p` | Evaluate a variable or expression in the selected frame. |
| `.pprint <expr>` / `.pp` | Same, pretty-printed — readable for nested dicts / lists. |
| `.whatis <expr>` | Print the Python type of a variable or expression. |
| `.set ${x} <value>` | Change an existing **scalar** local variable in the selected frame; the value is variable-substituted and stored as a string. To create a variable or set another type, assign it at the prompt (`${x}=    Evaluate    [1, 2]`). Lists/dicts (`@{…}`/`&{…}`) and item access aren't supported. |
| `.display <expr>` / `.undisplay <expr>` | Show `<expr>`'s value automatically at every following stop / stop showing it. |

**Source:**

| Command | Effect |
| --- | --- |
| `.list` / `.l` | Show the source at the current stop, current line marked `->`. |
| `.source <kw>` | Show a keyword's source. Resolves imported library/resource keywords; a keyword defined in the *running suite file* isn't resolvable by name — use `.list` at the stop instead. |

**What's loaded and available:** `.imports`, `.kw`, `.kw <name>` and `.doc <name>` work at the stop too, against the paused run's namespace; see [repl.md](repl.md#dot-commands).

## Stepping & resuming

| Command | Effect |
| --- | --- |
| `.continue` / `.c` | Resume until the next breakpoint, stop, or the end of the run. |
| `.step` / `.s` | Step **into**: stop at the next keyword, descending into calls. |
| `.next` / `.n` | Step **over**: stop at the next keyword in the current frame. |
| `.return` / `.r` | Continue until the current keyword returns, then stop. |
| `.until` | Continue until a *later* line in the current frame (past a loop's remaining iterations) or until the frame returns. |

## Managing breakpoints at runtime

Add, remove, and refine breakpoints from the prompt — each is referenced by the stable number shown in `.breakpoints`:

| Command | Effect |
| --- | --- |
| `.break <loc>[, <cond>]` / `.b` | Add a breakpoint — `file:line` or a keyword name, optionally conditional (`.break Login, ${retries} > 3`). |
| `.tbreak <loc>[, <cond>]` | Same, but one-shot: removed after it first stops. |
| `.breakpoints` / `.bp` | List breakpoints, numbered, with their attributes and the active exception filters. |
| `.condition <n> <expr>` | Set a condition on breakpoint `<n>` (bare `.condition <n>` clears it). |
| `.ignore <n> <count>` | Skip breakpoint `<n>`'s next `<count>` hits. |
| `.delete <n>` · `.disable <n>` / `.enable <n>` | Remove / turn off / on breakpoint `<n>`; bare form applies to all. |
| `.commands <n>` | Attach debugger commands replayed at each hit (see logpoints). |

A **condition** is evaluated in the stopped frame each time the breakpoint is reached; if the expression itself raises, the debugger stops anyway, even past `.ignore` or with `silent` commands, and appends the error to the stop line (`— condition error: Variable '${item_id}' not found.`). A keyword breakpoint stops at the call, before the keyword's arguments are bound, so its condition sees the caller's variables; to test an argument, put a line breakpoint on the keyword's first body line instead. `.ignore` skips the next *N* triggering hits.

**Logpoints (log and continue).** There's no dedicated command; you get the "print on every hit, never stop" effect by attaching commands to a breakpoint — a leading `silent` suppresses the banner and a trailing resuming command carries on:

```
(rdb) .commands 1
Enter commands for breakpoint 1, one per line; `end` to finish:
(com) silent
(com) .print ${item}
(com) .continue
(com) end
```

Now every hit prints `${item}` and runs on without pausing.

## Exception breakpoints

Pause on *failures* rather than locations. The CLI flags set the initial filters; `.catch` adjusts them at runtime:

| Command | Flag equivalent | Effect |
| --- | --- | --- |
| `.catch uncaught` | `--break-on-exception` (default on) | Pause at uncaught keyword failures. |
| `.catch all` | `--break-on-all-exceptions` | Pause at *every* keyword failure, even ones caught by `TRY`/`EXCEPT` or `Run Keyword And …`. |
| `.catch test` / `.catch suite` | `--break-on-failed-test` / `--break-on-failed-suite` | Pause at a failing test / suite end. |
| `.catch off` | — | Clear all exception breakpoints. Bare `.catch` shows what's armed. |

`uncaught` stops *before* the failure unwinds, so the state that caused it is still on the stack — this is what makes the default `robotcode robot-debug tests/` useful for chasing an intermittent or hard-to-reproduce failure.

## Ending a session

| Command | Effect |
| --- | --- |
| `.detach` | Detach the debugger and let the run **finish normally** — no more stops. Your breakpoints/filters are kept (re-arm with `.debug on`). |
| `.abort` | Abort the run **immediately** — no further keywords, no reports. |
