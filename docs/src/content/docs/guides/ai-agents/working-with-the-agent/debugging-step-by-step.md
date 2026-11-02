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

In the session, the agent started the order suite by its long name with a breakpoint, `robotcode robot-debug --break tests/orders.robot:19 -bl "Tests.Orders"`, and the run stopped there:

<!-- excerpt: debugging-step-by-step -->
```console
…
Order Coffee :: An order for a product in stock is placed.
* breakpoint  orders.Order Status Should Be  (tests/orders.robot:19)
…
```

### It answers with debugger commands

At the `(rdb)` prompt, `.where` shows the call stack, `.vars --user` the variables without those Robot Framework sets itself, and `.print` a variable or an expression. `.break` adds a breakpoint, and `.continue` runs on to the next one. Keywords can be called there too, in the context of the paused test. From the session, after *"Show me all variables I set myself."*:

<!-- excerpt: debugging-step-by-step -->
```console
…
Test:
    ${order} = 'order-4711'
…
```

The debugger waits at `(rdb)` between your prompts, so each prompt goes on where the last one stopped.

:::note[Driving the debugger]
GitHub Copilot in VS Code can type into a terminal and read it back, and Codex can write to a running command, so they can send each debugger command when you ask for it. Claude Code has no tool for that. In the session, it starts the debugger in the background with its input from a named pipe, writes the commands of each prompt into the pipe and reads the output from a file. Without either, the skill's fallback is a fixed list of commands sent at once, and you can no longer steer the run from prompt to prompt.
:::

More on the debugger: [robot-debug](/guides/cli/robot-debug/).

## What to watch out for

- **Name the test or the suite.** The agent selects it by its long name, so the `__init__.robot` files of the folders above it run as in a real run.
- **A debug run writes results too.** In the session, it replaced `results/output.xml`. Ask for another output directory if you still need the results of the last run.
- **End the debugger.** Say *"let it run to the end"* or *"stop the debugger"*; the agent ends it with `.continue`, `.detach` or `.abort`. Breakpoints set at the prompt last only for that run.

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
$ cd "$PWD"; D=$(mktemp -d); mkfifo $D/in; echo $D > /tmp/rdb_dir; (tail -f $D/in | robotcode robot-debug --break tests/orders.robot:19 -bl "Tests.Orders" > $D/out 2>&1; echo "EXIT $?" >> $D/out) & sleep 0; for i in $(seq 1 60); do grep -q "(rdb)" $D/out 2>/dev/null && break; sleep 1; done; cat $D/out; echo "DIR=$D"
==============================================================================
Tests :: Web shop acceptance tests                                            
==============================================================================
Tests.Orders :: Placing orders.                                               
==============================================================================
Order Coffee :: An order for a product in stock is placed.            
* breakpoint  orders.Order Status Should Be  (tests/orders.robot:19)
(rdb) DIR=/tmp/tmp.frPFLuGNrz
```

<div class="rc-session-answer">

**Agent:** Stopped at the breakpoint. Let me inspect the state there.

</div>

```console
$ D=/tmp/tmp.frPFLuGNrz; printf '.list\n.where\n.print ${order}\n' > $D/in; sleep 3; cat $D/out | sed -n '/(rdb)/,$p'
(rdb)      14  Order Coffee
     15      [Documentation]    An order for a product in stock is placed.
     16      [Metadata]    Requirement    SHOP-301
     17      [Tags]    smoke
     18      ${order}=    Create Order    coffee    quantity=2
->   19      Order Status Should Be    ${order}    placed
     20  
     21  Express Order
     22      [Documentation]    An express order is marked as such.
     23      [Metadata]    Requirement    SHOP-302
     24      ${order}=    Create Order    beans    express=${True}
(rdb) > #0  orders.Order Status Should Be  tests/orders.robot:19
  #1  Order Coffee                   tests/orders.robot:14
  #2  Orders                         tests/orders.robot
  #3  Tests                          tests
(rdb) ${order} = 'order-4711'
(rdb)
```

<div class="rc-session-answer">

**Agent:** The debugger is paused at `tests/orders.robot:19` in **Order Coffee**, just before `Order Status Should Be    ${order}    placed` runs.

- **How it was started:** `robotcode robot-debug --break tests/orders.robot:19 -bl "Tests.Orders"`. I picked the suite by its longname so that the parent `tests` suite's setup still runs.
- **Call stack:** `Order Status Should Be` (#0) ← `Order Coffee` ← `Tests.Orders` ← `Tests`
- **State:** `${order}` is `'order-4711'`. It was set by line 18, `Create Order    coffee    quantity=2`.

The session is still waiting at the `(rdb)` prompt, and I send it commands through a pipe in `/tmp/tmp.frPFLuGNrz`. What next?
- **Step over** the status check (`.next`) and see whether it passes.
- **Run a keyword here,** for example `Order Status Should Be    ${order}    placed`, or something else against the live shop state.
- **Look at variables** (`.vars --user`).
- **Let it finish:** `.continue` runs the other two order tests, and stops again if one of them fails.
- **Stop the run** (`.abort`).

</div>

<div class="rc-session-prompt">

**You:** Show me all variables I set myself.

</div>

```console
$ D=/tmp/tmp.frPFLuGNrz; : > /dev/null; L=$(wc -l < $D/out); printf '.vars --user\n' > $D/in; sleep 3; tail -n +$((L+1)) $D/out; tail -c 200 $D/out | tail -1
(rdb) Local:
    (none)
Test:
    ${order} = 'order-4711'
Suite:
    (none)
Global:
    ${BASE_URL} = 'http://localhost:8080'
    ${BROWSER} = 'chromium'
(rdb) (rdb)
```

<div class="rc-session-answer">

**Agent:** These are the variables you set yourself, with Robot Framework's built-in ones left out:

| Scope | Variable | Value |
|---|---|---|
| Test | `${order}` | `'order-4711'` (set on line 18 by `Create Order`) |
| Global | `${BASE_URL}` | `'http://localhost:8080'` |
| Global | `${BROWSER}` | `'chromium'` |

There are no local or suite variables yet. The two global ones come from `robot.toml`. I started the debugger without a profile, so `${BROWSER}` is the default `chromium`. With `-p dev` it would be Firefox. That makes no difference to these order tests, which use the in-memory `ShopLibrary` rather than a browser.

The debugger is still paused at line 19. Do you want to step over the status check, run a keyword here, or let it continue?

</div>

<div class="rc-session-prompt">

**You:** Set a second breakpoint at line 21 of `resources/orders.resource` and continue.

</div>

*…*

```console
$ D=/tmp/tmp.frPFLuGNrz; L=$(wc -l < $D/out); printf '.break resources/orders.resource:21\n.continue\n' > $D/in; sleep 4; tail -n +$((L+1)) $D/out
(rdb) breakpoint 2 at resources/orders.resource:21
(rdb) 
* breakpoint  BuiltIn.Should Be Equal  (resources/orders.resource:21)
(rdb)
```

```console
$ D=/tmp/tmp.frPFLuGNrz; L=$(wc -l < $D/out); printf '.where\n.print ${status}\n.print ${expected}\n' > $D/in; sleep 3; tail -n +$((L+1)) $D/out
(rdb) > #0  BuiltIn.Should Be Equal        resources/orders.resource:21
  #1  orders.Order Status Should Be  tests/orders.robot:19
  #2  Order Coffee                   tests/orders.robot:14
  #3  Orders                         tests/orders.robot
  #4  Tests                          tests
(rdb) ${status} = 'placed'
(rdb) ${expected} = 'placed'
(rdb)
```

<div class="rc-session-answer">

**Agent:** I set breakpoint 2 at `resources/orders.resource:21` and continued. The debugger is now paused on that line, still inside **Order Coffee**, just before `Should Be Equal    ${status}    ${expected}` runs.

- **Call stack:** `Should Be Equal` (#0) ← `Order Status Should Be` (`tests/orders.robot:19`) ← `Order Coffee` ← `Tests.Orders` ← `Tests`
- **Values being compared:** `${status}` is `'placed'` and `${expected}` is `'placed'`, so this check will pass.

Both breakpoints are still set. If you `.continue`, the run will stop again at line 21 when **Express Order** checks its status, so you can compare `'express'` there. **Sold Out Product Cannot Be Ordered** doesn't call `Order Status Should Be`, so it won't stop at either breakpoint.

</div>

<div class="rc-session-prompt">

**You:** Continue to the next breakpoint.

</div>

```console
$ D=/tmp/tmp.frPFLuGNrz; L=$(wc -l < $D/out); printf '.continue\n' > $D/in; sleep 4; tail -n +$((L+1)) $D/out
(rdb) | PASS |
------------------------------------------------------------------------------
Express Order :: An express order is marked as such.                  
* breakpoint  BuiltIn.Should Be Equal  (resources/orders.resource:21)
(rdb)
```

```console
$ D=/tmp/tmp.frPFLuGNrz; L=$(wc -l < $D/out); printf '.where\n.print ${status}\n.print ${expected}\n' > $D/in; sleep 3; tail -n +$((L+1)) $D/out
(rdb) > #0  BuiltIn.Should Be Equal        resources/orders.resource:21
  #1  orders.Order Status Should Be  tests/orders.robot:25
  #2  Express Order                  tests/orders.robot:21
  #3  Orders                         tests/orders.robot
  #4  Tests                          tests
(rdb) ${status} = 'express'
(rdb) ${expected} = 'express'
(rdb)
```

<div class="rc-session-answer">

**Agent:** **Order Coffee** passed. The debugger is paused again at `resources/orders.resource:21`, this time in **Express Order**.

- **Call stack:** `Should Be Equal` (#0) ← `Order Status Should Be` (`tests/orders.robot:25`) ← `Express Order` ← `Tests.Orders` ← `Tests`
- **Values being compared:** `${status}` is `'express'` and `${expected}` is `'express'`, so this test will pass too.

Neither breakpoint is left on the run's path: line 19 belongs to Order Coffee, and **Sold Out Product Cannot Be Ordered** doesn't call `Order Status Should Be`. If you `.continue`, the run will finish without stopping, unless that last test fails in a way its `Run Keyword And Expect Error` doesn't catch.

</div>

<div class="rc-session-prompt">

**You:** Let it run to the end.

</div>

```console
$ D=/tmp/tmp.frPFLuGNrz; L=$(wc -l < $D/out); printf '.continue\n' > $D/in; for i in $(seq 1 60); do grep -q "^EXIT" $D/out && break; sleep 1; done; tail -n +$((L+1)) $D/out
(rdb) | PASS |
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
EXIT 0
```

*…*

<div class="rc-session-answer">

**Agent:** The run finished and all 3 order tests passed (exit code 0). The debugger didn't stop again.

| Test | Result |
|---|---|
| Order Coffee | PASS |
| Express Order | PASS |
| Sold Out Product Cannot Be Ordered | PASS |

The results are in `results/`: `log.html`, `report.html` and `output.xml`. This run replaced the previous `output.xml`. Both breakpoints only existed in this session, and I've removed the temporary pipe I used to send commands to the debugger.

</div>

</div>

</details>
<!-- /session -->
