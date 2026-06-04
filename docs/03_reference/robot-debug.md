# Command-line debugging with `robotcode robot-debug`

::: tip Installation
The `robotcode robot-debug` command (and the `robotcode repl` shell) come from the optional **`repl`** package. If it isn't installed yet, add it:

```bash
pip install robotcode[repl]   # or: pip install robotcode[all]
```
:::

`robotcode robot-debug` is a `pdb`-style **command-line debugger** for Robot Framework. It runs a real `.robot` suite through the same runner as [`robotcode robot`](cli.md#robot), but pauses at breakpoints — a `file:line`, a keyword name, an embedded `Breakpoint` keyword, or the first uncaught failure — and drops you into a debug prompt with the live call stack, per-frame variables, a source listing, and the ability to run any keyword in the paused context.

There are two ways in:

- **`robotcode robot-debug`** (alias `run-debug`) runs a real `.robot` suite through the normal runner with the debugger attached. It takes the same options and arguments as [`robotcode robot`](cli.md#robot) — paths, `--variable`, `--include`, profiles, … — plus the trigger flags below.
- **[`robotcode repl`](repl.md)** (the interactive shell) has the *same* debugger attached: a breakpoint that matches a keyword you run at the prompt drops you into the debug prompt too.

The debugger sees every keyword and control-structure (FOR / IF / TRY / WHILE / …) start and end, on every supported Robot Framework version (5.0 – 7.x). For graphical step-debugging inside the editor, use the VS Code extension instead — see [Relationship to the VS Code debugger](#relationship-to-the-vs-code-debugger).

**Who this is for:**

- **Developers debugging a failing test or suite** — pause exactly where it breaks and inspect the live call stack and per-frame variables, instead of sprinkling `Log` statements and re-running.
- **Anyone chasing an intermittent or hard-to-reproduce failure** — the first uncaught failure pauses the run out of the box, so you catch the state at the moment it actually goes wrong.
- **Terminal, SSH, container, and headless users** — full step-debugging where a graphical editor and a DAP client aren't available, driven entirely from the command line.
- **CI and scripted debugging** — feed the debug prompt a fixed sequence of commands from a pipe or file (`.where`, `.vars`, `.continue`) to capture state non-interactively, or reproduce a CI failure locally with the same breakpoints.
- **AI-driven debugging** — coding agents (Claude Code, Cursor, Copilot, …) can drive the debugger non-interactively: set a breakpoint, then pipe `.where` / `.vars` / `.print` to capture the paused call stack and variables and reason about a failure instead of guessing. Inside a recognised agent the prompt falls back to the plain backend automatically, so the captured output stays clean.

## Quick start

```bash
# A run pauses at the first uncaught failure out of the box
robotcode robot-debug tests/

# Pause at a specific line, then step and inspect
robotcode robot-debug --break login.robot:42 tests/

# Pause at the very first keyword of a run
robotcode robot-debug --stop-on-entry tests/login.robot

# Combine line + keyword breakpoints
robotcode robot-debug --break login.robot:42 --break "Submit Login" tests/
```

`robot-debug` accepts the full `robotcode robot` option set (see the [CLI reference](cli.md#robot)) plus the debugger triggers below. The prompt/backend flags (`--backend`, `--plain`, `--no-history`) work here too — see [Prompt features](repl.md#prompt-features). The interactive shell's setup flags (`-v`, `-P`, output flags, `--source`, …) live on [`robotcode repl`](repl.md), not here.

## Setting breakpoints

There are several ways to make a run pause; they combine freely.

| Trigger | How |
| --- | --- |
| **Line breakpoint** | `--break path/to/test.robot:42` — pause when execution reaches that line. Repeatable. |
| **Keyword breakpoint** | `--break "Open Browser"` — pause whenever a keyword with that name is about to run. Repeatable. |
| **Embedded `Breakpoint` keyword** | Add `Breakpoint` as a step in your `.robot` / `.resource` (after `Library    robotcode.repl.Repl`). It's a no-op when run normally and a hard breakpoint under the debugger — no flag needed. |
| **Stop on entry** | `--stop-on-entry` (`robot-debug` only) — pause at the very first keyword. |
| **Uncaught exception** | **On by default** — pause at an uncaught failing keyword (not caught by `TRY`/`EXCEPT` or `Run Keyword And …`), *before* the failure unwinds. Turn off with `--no-break-on-exception`. |
| **Every exception** | `--break-on-all-exceptions` — pause at *every* failing keyword, even ones caught by `TRY`/`EXCEPT` or `Run Keyword And …`. |
| **Failing test / suite** | `--break-on-failed-test` / `--break-on-failed-suite` — pause at the end of a failing test / suite. |

A **keyword breakpoint** matches by exact name — either the bare keyword name (`--break "Open Browser"`) or its fully-qualified `Library.Keyword` form (`--break "SeleniumLibrary.Open Browser"`, to disambiguate a name two libraries share). Unlike Robot's own keyword lookup, the match is case- and whitespace-sensitive, so spell it as it appears in the run.

The exception breakpoints are armed in both `repl` and `robot-debug` (the on-by-default `--break-on-exception` ↔ off-switch `--no-break-on-exception`); each is toggleable at runtime with `.catch` (see [Exception breakpoints](#exception-breakpoints) below).

```bash
# Triggers combine, and the default can be turned off:
# pause at the end of failing tests, but not on uncaught failures
robotcode robot-debug --break-on-failed-test --no-break-on-exception tests/
```

You can also add and remove breakpoints from the debug prompt at runtime with `.break` / `.tbreak` / `.delete` / `.disable` (see below).

### The embedded `Breakpoint` keyword

To pause at a fixed spot without passing `--break` on every run, put a `Breakpoint` step directly in your `.robot` or `.resource` file. Import the marker library once, then call `Breakpoint` wherever you want execution to stop:

```robot [login.robot]
*** Settings ***
Library    robotcode.repl.Repl

*** Test Cases ***
Login
    Open Browser    ${URL}
    Breakpoint                      # the run pauses here under the debugger
    Input Text    id=user    ${USER}
    Submit Login
```

`Breakpoint` is a **no-op in a normal `robot` run** — the suite executes straight through it — and a **hard breakpoint** whenever the debugger is attached, whether through `robotcode robot-debug` or a keyword you run at the `robotcode repl` prompt. You can leave it in the file while iterating; it only bites when you're actually debugging, and it needs no `--break` flag.

`Breakpoint` is the only keyword from `robotcode.repl.Repl` meant for your own suites — `Repl` and `Exit` are used internally and aren't called by hand.

> **Plain backend for non-interactive runs.** On an interactive terminal the debug prompt gives you completion, history, and highlighting at the stop. When you feed it from a pipe, a script, or CI, the default `auto` backend falls back automatically to a plain prompt (or pass `--plain` explicitly). See [Picking a specific input backend](repl.md#picking-a-specific-input-backend).

## At a stop

When the run pauses, the debugger prints a one-line banner and opens a prompt:

```
* breakpoint  Submit Login  (login.robot:42)
(rdb)
```

The banner is `* <reason>  <keyword>  (<file>:<line>)`, where reason is `breakpoint`, `step`, `entry`, `pause`, or `exception`. At the `(rdb)` prompt you have the full debug command set (below) **plus** every shell command (`.kw`, `.doc`, `.vars`, …), and you can run any keyword in the paused context — its result is echoed and any variable it assigns stays in scope, exactly like at the shell prompt.

`robot-debug` produces the **same console output as `robotcode robot`** — the run is fully visible, and continuing or stepping shows execution proceeding. The debug prompt is simply interleaved with Robot's live console at each stop; when a test happens to finish right at a prompt its `| PASS |` marker lands next to the prompt, which is cosmetic. (Use `.detach` at the prompt to let the rest of the run finish and print normally.)

## Debug commands

Each command has a canonical long name and, where it helps, a single-letter shortcut; long names also accept any unambiguous prefix (`.bre` → `.break`). At the *shell* prompt, where there is no active stop, the navigation/resume commands simply report `Not at a breakpoint.`

**Stepping and resuming**

| Command | Effect |
| --- | --- |
| `.continue` / `.c` | Resume until the next breakpoint, stop, or the end of the run. |
| `.step` / `.s` | Step into: stop at the next keyword, descending into calls. |
| `.next` / `.n` | Step over: stop at the next keyword in the current frame. |
| `.return` / `.r` | Continue until the current keyword returns, then stop. |
| `.until` | Continue until a *later* line in the current frame — past a loop's remaining iterations — or until the frame returns. |

**Stack and frames**

| Command | Effect |
| --- | --- |
| `.where` / `.w` | Show the call stack — innermost frame is `#0`, `>` marks the selected one. |
| `.up` / `.u` | Select the calling (outer) frame. |
| `.down` / `.d` | Select the called (inner) frame. |
| `.frame N` / `.f N` | Select frame number N directly (`#0` is the innermost). |

**Inspecting**

| Command | Effect |
| --- | --- |
| `.list` / `.l` | Show the source at the current stop. On prompt-toolkit: the whole file in the scrollable viewer, scrolled to the current line (marked `->`). On the plain backend: a ±5-line inline window. |
| `.source <kw>` | Show a keyword's source. On prompt-toolkit: the **whole file** in the scrollable viewer, opened at the definition line (marked `->`). On the plain backend: inline from the definition downward — 10 lines, or `.source <kw> <n>` for `n`. |
| `.print <expr>` / `.p` | Evaluate a variable or expression in the selected frame and print the result. |
| `.pprint <expr>` / `.pp` | Same, but pretty-printed — readable for nested dicts / lists. |
| `.whatis <expr>` | Print the Python type of a variable or expression. |
| `.vars` / `.v` | Show the variables in scope (Local / Test / Suite / Global), name + value. `--user` skips Robot internals. |
| `.set ${x} <value>` | Set a **scalar** variable in the selected frame's local scope (the value is variable-substituted, like `Set Variable`). List/dict variables (`@{…}`/`&{…}`) and item access (`${x}[0]`) aren't supported. |
| `.display <expr>` | Show `<expr>`'s value automatically at every following stop. Bare `.display` lists/shows the registered expressions. |
| `.undisplay <expr>` | Stop displaying `<expr>`; bare `.undisplay` clears the list. |

You can also just type a keyword at the `(rdb)` prompt to run it in the paused context, exactly like at the shell prompt.

`.source` resolves keywords from imported libraries and resources. A keyword defined directly in the suite file currently being run is *not* resolvable by name; when you're stopped inside one, use `.list` to see its source at the current line.

**Breakpoints**

| Command | Effect |
| --- | --- |
| `.break <loc>[, <cond>]` / `.b` | Add a breakpoint — `file:line` or a keyword name, optionally conditional (`.break Login, ${retries} > 3`). |
| `.tbreak <loc>[, <cond>]` | Same, but one-shot: removed after it first stops. |
| `.breakpoints` / `.bp` | List the breakpoints, numbered, with their attributes and the active exception filters. |
| `.condition <n> <expr>` | Set a condition on breakpoint `<n>` (bare `.condition <n>` clears it). |
| `.ignore <n> <count>` | Skip breakpoint `<n>`'s next `<count>` hits. |
| `.delete <n>` | Remove breakpoint `<n>`; bare `.delete` removes all. |
| `.disable <n>` / `.enable <n>` | Turn breakpoint `<n>` off / on; bare form applies to all. |
| `.commands <n>` | Attach debugger commands to breakpoint `<n>`, replayed at each hit (enter one per line, end with `end`; a leading `silent` suppresses the banner; a resuming command lets the run continue automatically). |

Breakpoints are referenced by the stable number shown in `.breakpoints`. A **condition** is evaluated in the stopped frame each time the breakpoint is reached; if the expression itself raises, the debugger stops anyway so the breakage is visible. `.ignore` skips the next *N* triggering hits.

**Logpoints — log and continue.** There's no dedicated logpoint command, but you get the "print a value on every hit, never stop" effect by attaching commands to a breakpoint: a leading `silent` suppresses the banner and a trailing resuming command (`.continue`) carries on without prompting.

```
(rdb) .break Process Item
Breakpoint 1 at keyword 'Process Item'
(rdb) .commands 1
Enter commands for breakpoint 1, one per line; `end` to finish:
(com) silent
(com) .print ${item}
(com) .continue
(com) end
Breakpoint 1: 3 command(s)
```

Now every hit on `Process Item` prints `${item}` and runs on without pausing. (Graphical gutter logpoints are a feature of the VS Code / DAP debugger; in the CLI, `.breakpoints` shows a `logpoint` flag for any breakpoint that carries one.)

**Exception breakpoints**

| Command | Effect |
| --- | --- |
| `.catch uncaught` | Pause at uncaught keyword failures (same as `--break-on-exception`). |
| `.catch all` | Pause at *every* keyword failure, even ones caught by `TRY`/`EXCEPT` or `Run Keyword And …`. |
| `.catch test` / `.catch suite` | Pause at a failing test end / suite end. |
| `.catch off` | Clear all exception breakpoints. Bare `.catch` shows what's armed. |

The CLI flags set the *initial* filters — `--break-on-exception` (on by default) ↔ `.catch uncaught`, `--break-on-all-exceptions` ↔ `.catch all`, `--break-on-failed-test` ↔ `.catch test`, `--break-on-failed-suite` ↔ `.catch suite` — and `.catch` adjusts them at runtime.

**Ending the session**

| Command | Effect |
| --- | --- |
| `.detach` | Stop debugging but let the run finish normally — clears all breakpoints and runs to the end. |
| `.abort` | Abort the run immediately and exit (no further keywords, no reports). |

At a stop, `.exit` / `.quit` (which leave the *shell*) would be ambiguous, so they point you at `.continue` / `.detach` / `.abort` instead of quitting.

`Ctrl-C` or `Ctrl-D` at the `(rdb)` prompt **resumes the run** — the same as `.continue`, not a kill — so use `.abort` when you actually want to stop it. Pressing Enter on an empty line does nothing and just re-prompts (unlike the shell's `>>>` prompt, where an empty line exits).

## A debug session, end to end

```
$ robotcode robot-debug --break "Greet" hello.robot

* breakpoint  Greet  (hello.robot:11)
(rdb) .list
      6      Log    hello
      7
      8  *** Test Cases ***
      9  T
     10      Log    start
->   11      Greet
     12      Log    end
(rdb) .where
> #0  Greet  hello.robot:11
  #1  T      hello.robot:9
  #2  Hello  hello.robot
(rdb) .print ${name}
${name} = 'world'
(rdb) Log    debugging ${name}
[ INFO ] debugging world
=> None
(rdb) .continue
```

Typing a keyword at the prompt runs it in the paused context: its log output appears (`[ INFO ] …`) and the `=> <value>` line echoes the keyword's return value (`None` for `Log`).

## Recipes

```bash
# Debug a failing suite: pauses at the first uncaught failure out of the box
robotcode robot-debug tests/login.robot
# … at (rdb): .where, .vars, .print ${response}, .up, .continue …

# Stop at a keyword, drive the debug prompt from a script (plain backend)
printf '.where\n.vars\n.continue\n' \
  | robotcode robot-debug --plain --break "Submit Login" tests/

# Same robot options as a normal run — variables, tag filters, … — plus debugging
robotcode robot-debug -v ENV:staging --include smoke tests/

# Set a conditional breakpoint interactively, then run
robotcode robot-debug --stop-on-entry tests/orders.robot
# … at (rdb): .break Process Item, ${index} == 7   then   .continue
```

## Relationship to the VS Code debugger

This is the **command-line** debugger. For graphical step-debugging inside the editor — breakpoints in the gutter, a Variables pane, the call-stack view — use the **RobotCode** VS Code extension's debugger, which speaks the Debug Adapter Protocol. Both pause Robot Framework runs; the CLI debugger is the terminal-native, scriptable counterpart.

The shared shell features — the prompt backends, history, tab completion, the doc viewer, and the dot-command set you also get at a stop — are documented on the [`robotcode repl`](repl.md) page. For the per-flag reference of the underlying `robot` options see the [CLI reference](cli.md#robot).
