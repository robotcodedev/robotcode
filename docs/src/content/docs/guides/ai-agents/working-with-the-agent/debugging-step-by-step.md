---
title: Debugging Step by Step
description: "Step 5 of the tutorial: let the agent run a real test in the debugger, stop at a line, show the call stack and the variables, and continue prompt by prompt."
sidebar:
  label: 5. Debugging Step by Step
  order: 150.45
---

When the results of a run don't explain a failure, the agent runs the real test in the debugger and stops where you say. You steer the paused run prompt by prompt: look at the call stack and the variables, set another breakpoint, continue.

## What you learn

- why the agent debugs a real test with `robotcode robot-debug` and not in the REPL;
- how to stop at a line and look around;
- how to steer the paused run from one prompt to the next;
- how agents differ in driving the debugger.

## How to ask the agent

- *"Run `<test or suite>` in the debugger and stop at line `<n>` of `<file>`."*
- *"Where are we?"*, *"Show me all variables I set myself."* or *"What is `${<name>}` there?"*
- *"Set a breakpoint at line `<n>` of `<file>` and continue."*
- *"Continue to the next breakpoint."* or *"Let it run to the end."*

The session below starts with *"Run the order tests in the debugger and stop at line 19 of `tests/orders.robot`."*

## What the agent does

### It debugs the real test

The REPL runs only the keywords you type, without the suite's setup, its variables and its `__init__.robot`. The debugger runs the real test in its real context and pauses it. So as soon as a test is in play, the skill sends the agent to `robotcode robot-debug` and not to the REPL; see [How the Skill Works](/guides/ai-agents/how-the-skill-works/#from-request-to-command).

In the session, the agent started the order suite by its long name with a breakpoint, and the run stopped there:

<!-- excerpt: debugging-step-by-step -->
```console
$ robotcode session start debug --break tests/orders.robot:19 -bl "Tests.Orders"
Started session debug-499a3ee8.
…
Order Coffee :: An order for a product in stock is placed.
* breakpoint  orders.Order Status Should Be  (tests/orders.robot:19)
```

### It answers with debugger commands

At a stop, `.where` shows the call stack, `.vars --user` the variables without those Robot Framework sets itself, and `.print` a variable or an expression. `.break` adds a breakpoint, and `.continue` runs on to the next one. Keywords can be called there too, in the context of the paused test. From the session, after *"Show me all variables I set myself."*:

<!-- excerpt: debugging-step-by-step -->
```console
$ robotcode session send debug-499a3ee8 '.vars --user'
Local:
    (none)
Test:
    ${order} = 'order-4711'
…
```

The debugger waits at its stop between your prompts, so each prompt goes on where the last one stopped.

:::note[Driving the debugger]
GitHub Copilot in VS Code can type into a terminal and read it back, and Codex can write to a running command, so they can work at the debugger's `(rdb)` prompt. Claude Code and GitHub Copilot CLI have no tool for that, so they run the debugger with [`robotcode session`](/guides/cli/sessions/), as in this session: `session start debug` runs to the first stop and prints an ID, each `session send` sends one debugger command and returns with its answer, and `session stop` ends it. A session has to keep running after the command that started it, which not every sandbox allows; see [Where sessions can't run](/guides/cli/sessions/#where-sessions-cant-run).
:::

More on the debugger: [robot-debug](/guides/cli/robot-debug/).

## What to watch out for

- **Name the test or the suite.** The agent selects it by its long name, so the `__init__.robot` files of the folders above it run as in a real run.
- **A debug run writes results too.** It replaces the output files of the last run, as in this session. If you still need them, say so, and the agent adds `--output NONE --log NONE --report NONE`, as in [*A failing test*](/guides/ai-agents/working-with-the-agent/finding-out-why-a-test-failed/).
- **End the debugger.** Say *"let it run to the end"* or *"stop the debugger"*. The agent ends the run with `.continue`, `.detach` or `.abort`, and a session with `robotcode session stop`.

## The sessions

<!-- session: debugging-step-by-step -->
<details class="rc-session-details">
<summary>Debugging step by step <span>“Run the order tests in the debugger and stop at line 19 of <code>tests/orders.robot</code>.”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Run the order tests in the debugger and stop at line 19 of `tests/orders.robot`.

</div>

*Loaded the skill `robotcode:robotcode`*

*…*

```console
$ robotcode session start debug --break tests/orders.robot:19 -bl "Tests.Orders"
Started session debug-499a3ee8.
==============================================================================
Tests :: Web shop acceptance tests                                            
==============================================================================
Tests.Orders :: Placing orders.                                               
==============================================================================
Order Coffee :: An order for a product in stock is placed.            
* breakpoint  orders.Order Status Should Be  (tests/orders.robot:19)
```

```console
$ robotcode session send debug-499a3ee8 '.where'; robotcode session send debug-499a3ee8 '.vars --user'; robotcode session send debug-499a3ee8 '.print ${order}'
> #0  orders.Order Status Should Be  tests/orders.robot:19
  #1  Order Coffee                   tests/orders.robot:14
  #2  Orders                         tests/orders.robot
  #3  Tests                          tests
Local:
    (none)
Test:
    ${order} = 'order-4711'
Suite:
    (none)
Global:
    ${BASE_URL} = 'http://localhost:8080'
    ${BROWSER} = 'chromium'
${order} = 'order-4711'
```

<div class="rc-session-answer">

**Agent:** The debugger is stopped at line 19 of `tests/orders.robot`, in the test `Order Coffee`, and the session is still open. Line 19 hasn't run yet.

```
> #0  orders.Order Status Should Be  tests/orders.robot:19
  #1  Order Coffee                   tests/orders.robot:14
  #2  Orders                         tests/orders.robot
  #3  Tests                          tests
```

**Variables at the stop:**
- `${order}` = `'order-4711'`, set by `Create Order` on line 18
- `${BASE_URL}` = `'http://localhost:8080'`
- `${BROWSER}` = `'chromium'`

I selected the whole suite with `-bl "Tests.Orders"`, so `Express Order` and `Sold Out Product Cannot Be Ordered` will run after this test. The breakpoint only applies to line 19, so they won't pause there, though the debugger still stops on any uncaught failure.

You can tell me what to do next, or send commands yourself with `robotcode session send debug-499a3ee8 '<command>'`:
- **Step over line 19:** `.next`
- **Check the live status:** run a keyword at the stop, such as `Order Status Should Be    ${order}    placed`
- **Run the remaining tests:** `.continue`
- **Finish without further stops:** `.detach`
- **End the run:** `.abort`, then `robotcode session stop debug-499a3ee8` to close the session

</div>

<div class="rc-session-prompt">

**You:** Show me all variables I set myself.

</div>

```console
$ robotcode session send debug-499a3ee8 '.vars --user'
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

<div class="rc-session-answer">

**Agent:** These are the three variables you set yourself, as of the current stop at line 19:

| Variable | Value | Scope | Set by |
| --- | --- | --- | --- |
| `${order}` | `'order-4711'` | Test | `tests/orders.robot:18`, from `Create Order` |
| `${BASE_URL}` | `'http://localhost:8080'` | Global | `[variables]` in `robot.toml` |
| `${BROWSER}` | `'chromium'` | Global | `[variables]` in `robot.toml` |

There are no local or suite variables at this point. The output above excludes Robot Framework's built-in variables, such as `${TEST_NAME}` and `${OUTPUT_DIR}`.

</div>

<div class="rc-session-prompt">

**You:** Set a second breakpoint at line 21 of `resources/orders.resource` and continue.

</div>

```console
$ sed -n 1,40p resources/orders.resource | cat -n; robotcode session send debug-499a3ee8 '.break resources/orders.resource:21'; robotcode session send debug-499a3ee8 '.breakpoints'; robotcode session send debug-499a3ee8 '.continue'
…
breakpoint 2 at resources/orders.resource:21
  #1  line    tests/orders.robot:19
  #2  line    resources/orders.resource:21
  catch    uncaught_failed_keyword
* breakpoint  BuiltIn.Should Be Equal  (resources/orders.resource:21)
```

```console
$ robotcode session send debug-499a3ee8 '.where'; robotcode session send debug-499a3ee8 '.vars --user'
> #0  BuiltIn.Should Be Equal        resources/orders.resource:21
  #1  orders.Order Status Should Be  tests/orders.robot:19
  #2  Order Coffee                   tests/orders.robot:14
  #3  Orders                         tests/orders.robot
  #4  Tests                          tests
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

*…*

<div class="rc-session-answer">

**Agent:** The second breakpoint is set, and the run has stopped on it at line 21 of `resources/orders.resource`, still in the test `Order Coffee`. Line 21 hasn't run yet.

```
> #0  BuiltIn.Should Be Equal        resources/orders.resource:21
  #1  orders.Order Status Should Be  tests/orders.robot:19
  #2  Order Coffee                   tests/orders.robot:14
  #3  Orders                         tests/orders.robot
  #4  Tests                          tests
```

**Values line 21 will compare:**
- `${status}` = `'placed'`, set on line 20 by `Order Status`
- `${expected}` = `'placed'`, passed in from `tests/orders.robot:19`

Both values match, so `Should Be Equal` should pass.

**Breakpoints:**
1. `tests/orders.robot:19`
2. `resources/orders.resource:21`

The debugger also still stops on uncaught failures.

Breakpoint 2 is inside `Order Status Should Be`, which `Express Order` also calls (`tests/orders.robot:25`). The next `.continue` should therefore stop here again in that test. Line 19 won't stop again, because no other test reaches it.

`.vars --user` shows `Local: (none)` here because frame `#0` is the library keyword. To see the keyword's locals in that list, run `.up` first; `.print` finds them from any frame.

</div>

<div class="rc-session-prompt">

**You:** Continue to the next breakpoint.

</div>

```console
$ robotcode session send debug-499a3ee8 '.continue'
| PASS |
------------------------------------------------------------------------------
Express Order :: An express order is marked as such.                  
* breakpoint  BuiltIn.Should Be Equal  (resources/orders.resource:21)
```

```console
$ robotcode session send debug-499a3ee8 '.where'; robotcode session send debug-499a3ee8 '.print ${status}'; robotcode session send debug-499a3ee8 '.print ${expected}'; robotcode session send debug-499a3ee8 '.print ${order}'
> #0  BuiltIn.Should Be Equal        resources/orders.resource:21
  #1  orders.Order Status Should Be  tests/orders.robot:25
  #2  Express Order                  tests/orders.robot:21
  #3  Orders                         tests/orders.robot
  #4  Tests                          tests
${status} = 'express'
${expected} = 'express'
${order} = 'order-4712'
```

<div class="rc-session-answer">

**Agent:** `Order Coffee` passed, and the run has stopped at breakpoint 2 again, this time in `Express Order`. Line 21 of `resources/orders.resource` hasn't run yet.

```
> #0  BuiltIn.Should Be Equal        resources/orders.resource:21
  #1  orders.Order Status Should Be  tests/orders.robot:25
  #2  Express Order                  tests/orders.robot:21
  #3  Orders                         tests/orders.robot
  #4  Tests                          tests
```

**Values at this stop:**
- `${status}` = `'express'`
- `${expected}` = `'express'`
- `${order}` = `'order-4712'`

Both compared values match here too, so this check should pass.

`Sold Out Product Cannot Be Ordered` is the only test left. It doesn't call `Order Status Should Be`, so the next `.continue` shouldn't hit breakpoint 2 again. Its expected error is caught by `Run Keyword And Expect Error`, so the debugger's stop on uncaught failures shouldn't trigger either, and the run should finish.

</div>

<div class="rc-session-prompt">

**You:** Let it run to the end.

</div>

```console
$ robotcode session send debug-499a3ee8 '.detach'; echo "exit: $?"; robotcode session list; robotcode results summary; git status --short
debugger: detached
| PASS |
------------------------------------------------------------------------------
Sold Out Product Cannot Be Ordered :: The shop refuses an order fo... | PASS |
------------------------------------------------------------------------------
Tests.Orders :: Placing orders.                                       | PASS |
3 tests, 3 passed, 0 failed
==============================================================================
Tests :: Web shop acceptance tests                                    | PASS |
3 tests, 3 passed, 0 failed
==============================================================================
Output:  ~/webshop/results/output.xml
Log:     ~/webshop/results/log.html
Report:  ~/webshop/results/report.html
The run has ended with exit code 0.
exit: 0
ID              PROJECT                                                                                                                   STATE  IDLE TIME LEFT
debug-499a3ee8  ~/webshop  ended  15:00
# Summary — results/output.xml

- _Status:_ ✅ **PASS**
- _Total:_ 3
- _Passed:_ 3
- _Failed:_ 0
- _Skipped:_ 0
- _Started:_ 2026-11-03 22:39:31
- _Ended:_ 2026-11-03 22:40:29
- _Elapsed:_ 57.19 s
- _Messages:_ 1 FAIL
```

*…*

```console
$ robotcode results log --level FAIL -bl "Tests.Orders.Sold Out Product Cannot Be Ordered" 2>&1 | head -30; robotcode session stop debug-499a3ee8; git status --short; git check-ignore results
# Log

### Test: Tests.Orders.Sold Out Product Cannot Be Ordered (`tests/orders.robot:27`) ✅ **PASS** _(22:40:29 · 2 ms)_
…

results
```

<div class="rc-session-answer">

**Agent:** The run finished with exit code 0: all 3 order tests passed, with no further stops.

| Test | Result |
| --- | --- |
| `Order Coffee` | PASS |
| `Express Order` | PASS |
| `Sold Out Product Cannot Be Ordered` | PASS |

The summary lists `Messages: 1 FAIL`, but this isn't a problem. It's the `mug is out of stock` error from `Sold Out Product Cannot Be Ordered`, which that test expects and catches with `Run Keyword And Expect Error`.

The 57 seconds of elapsed time mostly comes from pausing at the breakpoints, so it doesn't reflect how fast the tests run.

I've closed the debug session. The `results/` folder is ignored by git, so the working tree is still clean.

**Files are in `results/`:**
- `log.html`
- `report.html`
- `output.xml`

</div>

</div>

</details>
<!-- /session -->
