---
title: Debugging Step by Step
description: "Step 5 of the tutorial: have an AI agent stop a real test in the debugger where it fails or at a line you name, ask what you want to know at the stop, and steer the paused run prompt by prompt."
sidebar:
  label: 5. Debugging Step by Step
  order: 150.45
---

The results of a run show what happened, but you can't ask them anything new. In the debugger, the test waits at a place you name, in its real context, and you can look around and try things there. You steer it prompt by prompt, and between your prompts the run stays where it stopped.

To follow along, use the [example project](/guides/ai-agents/working-with-the-agent/#following-along).

## Stop where it fails

`Express Order` fails only sometimes, with `placed != express`. The results can't tell you whether the shop would say something else a moment later, because in this example the shop only exists while the run lasts. So stop the test while it's still there:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** `Express Order` fails only sometimes. Run it in the debugger until it fails, and stop where it fails.

</div>

<div class="rc-session-calls">

- [`robotcode discover tests --search "Express Order"`](/guides/cli/discovering-tests/#tests--flat-list-of-tests)
- [`robotcode session list`](/guides/cli/sessions/)
- [`robotcode session start debug -bl "Tests.Orders.Express Order"`](/guides/cli/sessions/#starting-a-session)
- [`robotcode session restart debug-da913a68`](/guides/cli/sessions/#restarting-a-session)
- [`robotcode session status debug-da913a68`](/guides/cli/sessions/)
- [`robotcode session send debug-da913a68 '.where'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-da913a68 '.list'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-da913a68 '.vars --user'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-da913a68 '.print ${status}'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-da913a68 '.print ${expected}'`](/guides/cli/sessions/#sending-an-input)

</div>

<div class="rc-session-answer">

**Agent:** `Express Order` failed on the third run, and the debugger is paused right at the failure. Session `debug-da913a68` is still open and waiting, and I haven't changed anything.

**Where it stopped:** `resources/orders.resource:21`, before the failure unwinds:

```text wrap
* exception  BuiltIn.Should Be Equal — Keyword failed: placed != express

#0  BuiltIn.Should Be Equal        resources/orders.resource:21
#1  orders.Order Status Should Be  tests/orders.robot:25
#2  Express Order                  tests/orders.robot:21
```

…

**Likely cause:** this comes from reading the code, not from a test at this stop. …

The first status check on an express order returns `placed` about half the time, and every later check returns the true status. …

</div>

</div>

You don't need a breakpoint for this. A run in the debugger stops by itself at a failure that nothing catches, and "until it fails" tells the agent to start it again if it passes.

Look at two things in the answer. First, is the run still paused? That's what you want here. If your agent ended it after looking around, say at the start that you want it left paused. Second, where does the explanation come from? Here, it comes from reading the code, and the answer says so. A paused run can test it.

## Ask what you want to know

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Where are we? What does the variable with the status hold?

</div>

<div class="rc-session-calls">

- [`robotcode session status debug-da913a68`](/guides/cli/sessions/)
- [`robotcode session send debug-da913a68 '.where'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-da913a68 '.print ${status}'`](/guides/cli/sessions/#sending-an-input)

</div>

<div class="rc-session-answer">

**Agent:** We're still paused at the failure, at `resources/orders.resource:21`. That line is the `Should Be Equal    ${status}    ${expected}` call inside `Order Status Should Be`, which `Express Order` calls from `tests/orders.robot:25`.

`${status}` holds `'placed'`, but the test expected `'express'`, which is why this check failed.

</div>

</div>

Now ask the question that only a paused run can answer:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Ask the shop for the status of this order again. Is the answer the same?

</div>

<div class="rc-session-calls">

- [`robotcode session send debug-da913a68 'Order Status    ${order}'`](/guides/cli/sessions/#sending-an-input)

</div>

<div class="rc-session-answer">

**Agent:** No, the answer changed. The shop now returns `'express'` for `order-4711`, while the first check returned `'placed'`.

This confirms the cause: the order really is an express order, and only the first status check can return `placed`. The test fails because it checks once, too early, so the problem is the test's timing and not the order itself.

The run is still paused at the same spot, and `${status}` still holds `'placed'` because I didn't assign this new answer to it.

</div>

</div>

At the stop, the agent can call keywords in the context of the test. So a theory from reading the code becomes something you have seen happen. What to do about it is the same as in [step 4](/guides/ai-agents/working-with-the-agent/finding-out-why-a-test-failed/#decide-what-is-right): decide what is right, then ask for the fix.

## Let it finish

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Let it run to the end.

</div>

<div class="rc-session-calls">

- [`robotcode session send debug-da913a68 '.continue'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session status debug-da913a68`](/guides/cli/sessions/)
- [`robotcode session result debug-da913a68`](/guides/cli/sessions/)

</div>

<div class="rc-session-answer">

**Agent:** The run has ended and `Express Order` is recorded as **FAIL** with `placed != express` (1 test, 0 passed, 1 failed, exit code 1). The extra status check at the prompt didn't rescue it, because the failed check had already happened and resuming doesn't re-run it.

The results are in `results/`, including `log.html` and `report.html`.

Session `debug-da913a68` is still open, so it can run the test again with `robotcode session restart debug-da913a68`. If you're finished with it, `robotcode session stop debug-da913a68` closes it.

…

</div>

</div>

A paused run stays open until you say otherwise, so say when you're done.

## See how it did that

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which `robotcode` commands did you use? I want to try this myself.

</div>

<div class="rc-session-answer">

**Agent:** Here are the commands in the order I ran them, using your session ID as an example. `session start` prints a new ID each time, so use yours in the later commands.

**1. Find the test's full name**
```bash wrap
robotcode discover tests --search "Express Order"
```
This gives you `Tests.Orders.Express Order`.

**2. Start the test in the debugger**
```bash wrap
robotcode session start debug -bl "Tests.Orders.Express Order"
```
It stops at the first uncaught failure by default, so no breakpoint is needed. My first run passed and went straight to the end.

…

**4. Look around at the stop**
```bash wrap
robotcode session status debug-da913a68                   # "waits" means paused at a stop
robotcode session send debug-da913a68 '.where'            # call stack
robotcode session send debug-da913a68 '.list'             # source around the stop
robotcode session send debug-da913a68 '.vars --user'      # variables, without Robot's internal ones
robotcode session send debug-da913a68 '.print ${status}'
robotcode session send debug-da913a68 '.print ${expected}'
```
…

**5. Run a keyword inside the paused test**
```bash wrap
robotcode session send debug-da913a68 'Order Status    ${order}'
```
Use single quotes so your shell doesn't expand `${order}`.

…

**Interactive version:** in your own terminal you don't need `session` at all. This command gives you an `(rdb)` prompt where you type the same inputs directly:
```bash wrap
robotcode robot-debug -bl "Tests.Orders.Express Order"
```
It runs the test once, so if it passes, just start it again.

Each debug run overwrites the files in `results/`. To keep the last run's results, add `--output NONE --log NONE --report NONE` to the start command.

</div>

</div>

Try [`robotcode robot-debug`](/guides/cli/robot-debug/) in your own terminal. It takes the same inputs that the agent sends one by one with [`robotcode session`](/guides/cli/sessions/). Your agent may name others, such as [`robotcode session restart`](/guides/cli/sessions/#restarting-a-session). The answer's last sentence also matters when you work with the agent: a run in the debugger replaces the results of the last run, so if you still need them, say so when you start it.

## Stop where you say

You can also name the place, and go on from one stop to the next:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Run the order tests in the debugger and stop at line 19 of `tests/orders.robot`.

</div>

<div class="rc-session-calls">

- [`robotcode discover suites`](/guides/cli/discovering-tests/#suites--flat-list-of-suites)
- [`robotcode discover tests`](/guides/cli/discovering-tests/#tests--flat-list-of-tests)
- [`robotcode session list`](/guides/cli/sessions/)
- [`robotcode discover info`](/guides/cli/discovering-tests/#info--environment-and-version)
- [`robotcode session start debug --break tests/orders.robot:19 --output NONE --log NONE --report NONE -bl "Tests.Orders"`](/guides/cli/sessions/#starting-a-session)
- [`robotcode session send debug-f5c8b2df '.where'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-f5c8b2df '.vars --user'`](/guides/cli/sessions/#sending-an-input)

</div>

<div class="rc-session-answer">

**Agent:** The debugger is stopped at line 19 of `tests/orders.robot`, in the first order test, **Order Coffee**. Line 19 hasn't run yet:

```robot wrap
Order Status Should Be    ${order}    placed
```

…

- **What runs:** I selected the whole suite (`-bl "Tests.Orders"`), so `Express Order` and `Sold Out Product Cannot Be Ordered` run after this test if you continue. The debugger will also stop at any uncaught failure.
- **Results:** I turned off output files for this run, so your last results in `results/` are still there. Nothing from this debug run will be saved.

…

</div>

</div>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Show me all variables I set myself.

</div>

<div class="rc-session-calls">

- [`robotcode session send debug-f5c8b2df '.vars --user'`](/guides/cli/sessions/#sending-an-input)

</div>

<div class="rc-session-answer">

**Agent:** These are the variables set by you or your project, with Robot Framework's built-in ones left out, at the current stop (`tests/orders.robot:19`):

| Scope | Variable | Value | Set by |
| --- | --- | --- | --- |
| Test | `${order}` | `'order-4711'` | `Create Order` on line 18 of `tests/orders.robot` |
| Global | `${BASE_URL}` | `'http://localhost:8080'` | `[variables]` in `robot.toml` |
| Global | `${BROWSER}` | `'chromium'` | `[variables]` in `robot.toml` |

There are no local or suite variables at this stop.

</div>

</div>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Set a second breakpoint at line 21 of `resources/orders.resource` and continue.

</div>

<div class="rc-session-calls">

- [`robotcode session send debug-f5c8b2df '.break resources/orders.resource:21'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-f5c8b2df '.continue'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-f5c8b2df '.where'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-f5c8b2df '.print ${status}'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-f5c8b2df '.print ${expected}'`](/guides/cli/sessions/#sending-an-input)

</div>

<div class="rc-session-answer">

**Agent:** I added breakpoint 2, and the run is now stopped at line 21 of `resources/orders.resource`, still in **Order Coffee**. Line 21 hasn't run yet:

```robot wrap
Should Be Equal    ${status}    ${expected}
```

- **Call stack:** `Should Be Equal` ← `Order Status Should Be` (called from `tests/orders.robot:19`) ← `Order Coffee` ← `Orders` ← `Tests`
- **Values:** `${status}` and `${expected}` are both `'placed'`, so this check should pass.

Both breakpoints stay active. Line 21 is inside `Order Status Should Be`, and `Express Order` calls that keyword too. If you continue, the next stops are therefore lines 19 and 21 again in that test, unless something fails first.

</div>

</div>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Let it run to the end, and close the debugger.

</div>

<div class="rc-session-calls">

- [`robotcode session send debug-f5c8b2df '.detach'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session stop debug-f5c8b2df`](/guides/cli/sessions/#ending-a-session)
- [`robotcode session list`](/guides/cli/sessions/)

</div>

<div class="rc-session-answer">

**Agent:** The run finished and the debugger is closed, but **one of the 3 order tests failed**.

| Test | Result |
| --- | --- |
| Order Coffee | Passed |
| Express Order | **Failed:** `placed != express` |
| Sold Out Product Cannot Be Ordered | Passed |

…

</div>

</div>

Each prompt goes on where the last one stopped. Because the agent selected the suite by its name and not by its file, the `__init__.robot` of the folder above it runs too, as in a real run. In your run, `Express Order` may pass.

## In your own project

- Say what you want to find out, and where to stop: at a failure, at a line, or at a keyword.
- Ask at the stop what a variable holds, and have the agent call a keyword there to try something.
- Check where an explanation comes from: from what the paused run showed, or from reading the code.
- Say when a run should stay paused and when you're done with it.
- If you still need the results of the last run, say so when you start.
- Ask for the commands, and try `robotcode robot-debug` in your own terminal.
