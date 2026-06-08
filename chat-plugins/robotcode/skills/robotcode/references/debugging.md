# Debugging a run — `robotcode robot-debug`

`robotcode robot-debug` (alias `run-debug`) is a `pdb`-style **command-line debugger** for Robot Framework. It runs a real `.robot` suite through the same runner as [`robotcode robot`](../SKILL.md) — honoring `robot.toml`, profiles, variables, and the project environment — but **pauses at breakpoints** and drops you into a `(rdb)` debug prompt with the live call stack, the variables in each frame, a source listing, and the ability to run any keyword in the paused context. It sees every keyword and control structure (`FOR` / `IF` / `TRY` / `WHILE` / …) start and end, on every supported Robot Framework version (5.0–7.x).

Reach for the debugger when a recorded log isn't enough and you need the **live** state at the moment a test goes wrong — the real call stack, a variable's value at a specific point, or the result of running a keyword against the paused context. It is the third failure-analysis tool, and the most expensive; pick deliberately:

- **[`results`](results.md)** reads a *finished* `output.xml` — no re-run. Try it **first** for "why did X fail?".
- **[REPL](repl.md)** builds state up from scratch to *explore* — no suite is running.
- **The debugger** re-runs the suite and stops it **mid-flight** to inspect the actual live state. Use it only when the recorded log doesn't answer the question.

Beyond post-mortem analysis, `robot-debug` also makes a tight **inner loop while you develop or fix a test**: run the test through it instead of a plain `robot` run, and break-on-failure (on by default) stops you at the failure in the live context — inspect, then prove a fix by running the corrected keyword right there. That trial is ephemeral, so once it works **write the fix back into the `.robot` / `.resource` file** and re-run to confirm — running a keyword at the prompt doesn't change the source; `.continue` only carries the current run on. A clean pass just runs to completion, so it doubles as a quick "does it run?" check.

**To debug why a test fails, debug *that* test — fast.** Find the test's **longname** (from [`results`](results.md) or `discover`), then:

- **Select it with `-bl "<longname>"`, not the `.robot` file.** Pointing `robot-debug` at a single file (just like `robotcode robot`) makes that file the top suite, so the parent suites' `__init__.robot` never loads — its **Suite Setup/Teardown**, suite variables, and the tags and timeouts it applies don't run, and the test can fail (or pass) for the wrong reason. A bare path also runs *every* test in the file and, with break-on-failure on by default, stops at the **first** failure, which may be a different test. Selecting by longname builds the full suite tree from the project root / `robot.toml` paths, runs that initialization exactly as in a real run, and lands the pause in the one test you picked.
- **Read the recorded error with [`results`](results.md) first.** It often already names the cause — a variable or value, not what poking the live system would suggest — so bring up the debugger for the live values only if you still need them.
- **Don't reconstruct or paste the test into a REPL.** That runs a *copy* in a different context, dropping the suite's setup/teardown, variables, and imports.
- **Don't detour into external tools or a separate exploration of the system under test first.** That debugs the wrong context and routinely chases the wrong cause — a symptom in the live system, when the real fault was a variable, value, or setup in the test.

## Contents

- **[Two ways in](#two-ways-in)** — `robot-debug` (a real run, scoped to the tests you select) vs. `repl` (keywords typed at the prompt)
- **[How a debug session works](#how-a-debug-session-works)** — the pause → inspect → resume loop
- **[Setting breakpoints](#setting-breakpoints)** — line, keyword, location vs. run scope, embedded `Breakpoint`, stop-on-entry, exceptions
- **[At a stop: inspecting state](#at-a-stop-inspecting-state)** — stack & frames, variables, source, what's loaded (keywords / libraries / resources)
- **[Stepping & resuming](#stepping--resuming)**
- **[Managing breakpoints at runtime](#managing-breakpoints-at-runtime)** — conditions, ignore counts, logpoints
- **[Exception breakpoints](#exception-breakpoints)** — `.catch`
- **[Ending a session](#ending-a-session)** — `.continue` / `.detach` / `.abort`
- **[Driving the session from an agent](#driving-the-session-from-an-agent)** — step through it interactively (the normal way)
- **[A session, end to end](#a-session-end-to-end)**
- **[Relationship to the VS Code debugger](#relationship-to-the-vs-code-debugger)**

## Two ways in

- **`robotcode robot-debug`** (alias `run-debug`) — debug a run, scoped however you need: narrow it to a single test with `-t`/`-bl` (the usual case when debugging one failure), to a suite or tag, or run the lot. Takes the **full [`robotcode robot`](../SKILL.md) option set** (paths, `-v`, `-i`/`-e`/`-s`/`-t`, `--profile`, …) plus the trigger flags below.
- **`robotcode repl`** — the *same* debugger is available in the [REPL](repl.md), but it **starts detached**: attach it with `.debug on` or `--debugger-attached` (passing `--break …` attaches too). Arm a breakpoint up front with `--break …`, or interactively at the prompt with `.break` (a keyword name *or* a `file:line`, no restart); running a keyword that reaches it drops you into the same `(rdb)` prompt. Use it to debug a keyword while you build it up — see [repl.md](repl.md#debugging-from-the-repl).

Both come from the optional **`repl`** extra. `Error: No such command 'robot-debug'` means it's missing — see [install.md](install.md) (`pip install robotcode[repl]`, or `[all]`).

## How a debug session works

1. **Start the run with a breakpoint armed** — a `file:line`, a keyword name, an embedded `Breakpoint`, or (by default) the first uncaught failure.
2. **Execution pauses** at the first match. A one-line banner prints and the `(rdb)` prompt opens:
   ```
   * breakpoint  Submit Login  (login.robot:42)
   (rdb)
   ```
   The banner is `* <reason>  <keyword>  (<file>:<line>)`, where reason is `breakpoint`, `step`, `entry`, `pause`, or `exception`.
3. **Inspect and act** — walk the stack, print variables, step, add breakpoints, or **type a keyword to run it in the paused context** (its result is echoed as `=> <value>` and any variable it assigns stays in scope, exactly like at the REPL prompt).
4. **Resume** with `.continue` (or a step command), or end the session with `.detach` / `.abort`.

The run's normal console output (`| PASS |` / `| FAIL |`, log messages) stays fully visible and interleaves with the prompt — `robot-debug` produces the **same console output as `robotcode robot`**, just paused at each stop.

## Setting breakpoints

Triggers combine freely. Pass them to `robot-debug` (most also work on `repl`):

| Trigger | How |
| --- | --- |
| **Line** | `--break path/to/test.robot:42` — pause when execution reaches that line. Repeatable. |
| **Keyword** | `--break "Open Browser"` — pause whenever that keyword is about to run. Repeatable. |
| **Embedded `Breakpoint`** | A `Breakpoint` step in a `.robot` / `.resource` — see below. No flag needed. |
| **Stop on entry** | `--stop-on-entry` (`robot-debug` only) — pause at the very first keyword of the run. |
| **Uncaught failure** | **On by default** — pause at the first failing keyword not caught by `TRY`/`EXCEPT` or `Run Keyword And …`, *before* it unwinds. Turn off with `--no-break-on-exception`. |
| **Every failure** | `--break-on-all-exceptions` — pause at *every* failing keyword, even caught ones. |
| **Failing test / suite** | `--break-on-failed-test` / `--break-on-failed-suite` — pause at the end of a failing test / suite. |

A **keyword breakpoint** matches by exact name — the bare name (`--break "Open Browser"`) or the fully-qualified `Library.Keyword` form (`--break "SeleniumLibrary.Open Browser"`) to disambiguate a name two libraries share. Unlike Robot's own lookup the match is **case- and whitespace-sensitive**, so spell it as it appears in the run. Because *uncaught failure* is armed by default, `robotcode robot-debug tests/` with no flags already drops you at the first real failure with its state intact — that whole-suite form is for *finding* an unknown failure.

### Breakpoint location vs. run scope

A `file:line` or keyword breakpoint says *where* to stop; the `robotcode robot` selectors say *what runs*. When you already know which test you're debugging, set the breakpoint where you need it **and** narrow the run to that one test:

```bash
robotcode robot-debug -bl "MyProject.Login.Login Works"                  # only this test runs; pause at its failure
robotcode robot-debug --break login.robot:42 -t "Login Works"            # break at the line, but only run that test
```

Handing over a bare **file** path (`tests/login.robot`) instead runs *every* test in the file — so, with break-on-failure on, it can stop on a *different* test first — **and** skips the parent suites' `__init__.robot` (the setup/variables loss described above). Select a test, task, or single suite by longname; the one path form that's fine is a whole **directory** (`tests/` loads its `__init__.robot`), never a single file.

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

`Breakpoint` is a **no-op in a normal `robot` run** and a **hard breakpoint** whenever the debugger is attached (under `robot-debug`, or in `repl` once you've attached with `.debug on`). Leave it in while iterating — it only bites when you're actually debugging, and needs no flag. (`Breakpoint` is the only keyword from `robotcode.repl.Repl` meant for your own suites; `Repl` and `Exit` are internal.)

## At a stop: inspecting state

At the `(rdb)` prompt you have the full debug command set, every shell dot-command (`.kw`, `.doc`, …), and keyword execution in context. Each command has a long name and often a one-letter shortcut; long names accept any unambiguous prefix (`.bre` → `.break`).

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
| `.set ${x} <value>` | Set a **scalar** local variable in the selected frame (value is variable-substituted, like `Set Variable`). Lists/dicts (`@{…}`/`&{…}`) and item access aren't supported. |
| `.display <expr>` / `.undisplay <expr>` | Show `<expr>`'s value automatically at every following stop / stop showing it. |

**Source:**

| Command | Effect |
| --- | --- |
| `.list` / `.l` | Show the source at the current stop, current line marked `->`. |
| `.source <kw>` | Show a keyword's source. Resolves imported library/resource keywords; a keyword defined in the *running suite file* isn't resolvable by name — use `.list` at the stop instead. |

**What's loaded and available.** The shell introspection commands work at the stop too, against the **paused run's** namespace and scope — so you can see what you have to work with before running a keyword in context, and pull its docs or source without leaving the prompt:

| Command | Effect |
| --- | --- |
| `.imports` | The libraries and resources the paused run has loaded — each with its keyword count and source path. |
| `.kw` | List every available keyword, grouped by library/resource; `.kw <text>` searches by partial name. |
| `.kw <name>` | Full keyword documentation — signature, argument types, defaults, tags, docstring; disambiguate with `Owner.Keyword` (e.g. `.kw BuiltIn.Log`). |
| `.doc <name>` | Documentation for a loaded library or resource, by its namespace name (or its alias if imported `AS`). |

So at any stop you can answer "what keywords and variables are in scope, which libraries and resources are loaded, and what do they do / where are they defined" — `.kw` / `.doc` for the docs, `.source` for a keyword's body, `.vars` for the variables. These are the same commands documented for the `>>>` prompt — see [repl.md](repl.md#dot-commands).

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

A **condition** is evaluated in the stopped frame each time the breakpoint is reached; if the expression itself raises, the debugger stops anyway so the breakage is visible. `.ignore` skips the next *N* triggering hits.

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
| `.continue` / `.c` | Run on to the next stop or the end. |
| `.detach` | Detach the debugger and let the run **finish normally** — no more stops. Your breakpoints/filters are kept (re-arm with `.debug on`); like `.debug off` then `.continue`. |
| `.abort` | Abort the run **immediately** — no further keywords, no reports. |

Two things that surprise people:

- At the `(rdb)` prompt, **`Ctrl-C` / `Ctrl-D` resume the run** (like `.continue`) — they do **not** kill it. Use `.abort` to actually stop. (This is the opposite of the shell `>>>` prompt.)
- `.exit` / `.quit` are refused at a stop as ambiguous — use `.continue` / `.detach` / `.abort`.

## Driving the session from an agent

The debugger is an **interactive** program: it stops at a breakpoint, prints the `(rdb)` prompt, and waits. **Drive it interactively — that's the normal way.** It stops, you read `.where` / `.vars` / `.print ${x}`, and you pick the next command from what you just saw, stepping with `.step` / `.next` / `.continue` exactly as the [session loop](#how-a-debug-session-works) describes. You don't decide the commands up front — choosing each step from the live state *is* debugging, and it's the reason you stopped the run instead of reading the recorded log. Leave every session with a resuming command (`.continue` / `.detach` / `.abort`).

The one thing never to do is start `robot-debug` and then **block on its exit code** — with no input it sits at the prompt forever.

The core pattern: **arm a breakpoint → inspect the live state → resume**, instead of guessing from a static log. No agent flags are required — RobotCode auto-detects the agent session and uses the capture-safe **plain backend** (`--plain` forces it explicitly); same detection/overrides as the REPL (see [repl.md](repl.md)). The full `robotcode robot` option set still applies, so scope the debugged run like any other (`-bl "<longname>"`, `-i <tag>`, `-v …`, `--profile …`).

> **Fallback only if your agent can't drive a terminal.** When you can only run a command to completion, pipe a *predetermined* command sequence that ends in a resuming command — e.g. `printf '.where\n.vars --user\n.continue\n' | robotcode robot-debug -t "Login Works"`. This gives up the back-and-forth, so prefer interactive whenever you can.

## A session, end to end

```
$ robotcode robot-debug --break "Greet" hello.robot

* breakpoint  Greet  (hello.robot:11)
(rdb) .list
     10      Log    start
->   11      Greet
     12      Log    end
(rdb) .where
> #0  Greet  hello.robot:11
  #1  T      hello.robot:9
(rdb) .print ${name}
${name} = 'world'
(rdb) Log    debugging ${name}
[ INFO ] debugging world
=> None
(rdb) .continue
```

`.list` shows the source at the stop, `.where` the stack, `.print` reads a variable in the selected frame, and typing `Log …` runs the keyword in the paused context — its `[ INFO ]` output appears and `=> None` echoes the return value.

## Relationship to the VS Code debugger

This is the **command-line** debugger. For graphical step-debugging inside the editor — breakpoints in the gutter, a Variables pane, the call-stack view — use the **RobotCode VS Code extension**, which speaks the Debug Adapter Protocol. Both pause Robot Framework runs; the CLI debugger is the terminal-native, scriptable counterpart. The shared shell features — prompt backends, history, tab completion, the doc viewer, and the dot-command set you also get at a stop — are documented in [repl.md](repl.md).
