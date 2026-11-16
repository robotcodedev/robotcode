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
- [`robotcode session start debug --output NONE --log NONE --report NONE -bl "Tests.Orders.Express Order"`](/guides/cli/sessions/#starting-a-session)
- [`robotcode session send debug-0b7316eb '.where'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-0b7316eb '.list'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-0b7316eb '.vars --user'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-0b7316eb '.up'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-0b7316eb 'Order Status    ${order}'`](/guides/cli/sessions/#sending-an-input)
- …

</div>

<div class="rc-session-answer">

**Agent:** It failed on the first attempt, so no retries were needed. The debugger is paused right at the failure, and the session is still open as `debug-0b7316eb`.

**Where it stopped:** `Should Be Equal` at `resources/orders.resource:21`, inside `Order Status Should Be`, which is called from `Express Order` (`tests/orders.robot:25`).

- Error: `placed != express`
- Values at the stop: `${order}='order-4711'`, `${status}='placed'`, `${expected}='express'`

**Main clue:** I ran `Order Status    ${order}` three more times at the stop, on the same order, and it returned `'express'` every time. So the order really is express. The status lookup just returned `placed` when it ran right after `Create Order`. …

…

</div>

</div>

You don't need a breakpoint for this. A run in the debugger stops by itself at a failure that nothing catches, and "until it fails" tells the agent to start it again if it passes.

Look at two things in the answer. First, is the run still paused? That's what you want here. If your agent ended it after looking around, say at the start that you want it left paused. Second, where does the explanation come from? Here, the agent called a keyword of the shop at the stop and got another answer, so the explanation rests on something it saw, not only on reading the code.

## Ask what you want to know

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Where are we? What does the variable with the status hold?

</div>

<div class="rc-session-calls">

- [`robotcode session status debug-0b7316eb`](/guides/cli/sessions/)
- [`robotcode session send debug-0b7316eb '.where'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-0b7316eb '.print ${status}'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-0b7316eb '.frame 1'`](/guides/cli/sessions/#sending-an-input)

</div>

<div class="rc-session-answer">

**Agent:** We're still paused at the failure. Execution is stopped in `BuiltIn.Should Be Equal` at `resources/orders.resource:21`, which `Order Status Should Be` calls from the `Express Order` test (`tests/orders.robot:25`).

**`${status}` holds `'placed'`.** The check compares it to `${expected}` = `'express'`, which is why it fails.

When I first asked for `${status}`, I got "not found". That was because I had left the debugger looking at the test's own level, two frames up, where the variable doesn't exist. I switched it to `Order Status Should Be`, the level where `${status}` is set, and read it there.

…

</div>

</div>

A variable belongs to the keyword that sets it. At a stop, the debugger looks at one level of the call stack, and the agent can switch to another one to read its variables.

What the shop says now is the question that only a paused run can answer. The agent above asked it on its own; if yours explains the failure from the code alone, ask for it:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Ask the shop for the status of this order again. Is the answer the same?

</div>

<div class="rc-session-calls">

- [`robotcode session send debug-0b7316eb 'Order Status    ${order}'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-0b7316eb '.print ${order}'`](/guides/cli/sessions/#sending-an-input)

</div>

<div class="rc-session-answer">

**Agent:** No, the answer is different. The shop now says order `order-4711` has status **`'express'`**. The failed check had read **`'placed'`**, which is still what `${status}` holds.

That's the fourth time `express` has come back since the stop, so the order really is express. The `placed` reading came from checking right after the order was created, before the express flag had taken effect. That timing is why the test only fails sometimes.

The run is still paused at the failure.

</div>

</div>

At the stop, the agent can call keywords in the context of the test. So a theory from reading the code becomes something you have seen happen. What to do about it is the same as in [step 4](/guides/ai-agents/working-with-the-agent/finding-out-why-a-test-failed/#decide-what-is-right): decide what is right, then ask for the fix.

## Let it finish

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Let it run to the end.

</div>

<div class="rc-session-calls">

- [`robotcode session send debug-0b7316eb '.continue'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session stop debug-0b7316eb`](/guides/cli/sessions/#ending-a-session)

</div>

<div class="rc-session-answer">

**Agent:** The run has finished: **`Express Order` failed** with `placed != express`, 1 test and 1 failure. Re-checking the status at the stop only read it again; the failure itself was already recorded. I've closed the debug session.

No output, log or report files were written, so your last results files are unchanged.

…

</div>

</div>

After the end of the run, this agent closed the session by itself. Another may leave it open until you say you're done, so say what you want.

## See how it did that

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which `robotcode` commands did you use? I want to try this myself.

</div>

<div class="rc-session-answer">

**Agent:** Here are the commands in the order I ran them. I used a **session** because my shell can't type into a running program. In your own terminal, the simpler route is below.

**1. Find the test's full name**
```bash wrap
robotcode discover tests --search "Express Order"
```
This gives `Tests.Orders.Express Order`.

**2. Start the debug run, which stops at the first failure by default**
```bash wrap
robotcode session start debug --output NONE --log NONE --report NONE -bl "Tests.Orders.Express Order"
```
This prints `Started session debug-…` and then runs until it stops. `--output NONE --log NONE --report NONE` keeps your last results files from being overwritten.

**3. Inspect the stop** (one `send` per command)
```bash wrap
robotcode session send <ID> '.where'            # call stack
robotcode session send <ID> '.list'             # source around the stop
robotcode session send <ID> '.vars --user'      # variables in the selected frame
robotcode session send <ID> '.up'               # go one frame outward
robotcode session send <ID> '.frame 1'          # jump to frame #1 (Order Status Should Be)
robotcode session send <ID> '.print ${status}'  # print a variable in that frame
robotcode session send <ID> '.print ${order}'
```

…

**Simpler in your own terminal:** run the debugger directly and type the same commands at its `(rdb)` prompt, without `session send`:
```bash wrap
robotcode robot-debug --output NONE --log NONE --report NONE -bl "Tests.Orders.Express Order"
```
At the `(rdb)` prompt, type `.where`, `.frame 1`, `.print ${status}`, `Order Status    ${order}` and `.continue`.

The failure only happens sometimes, so the test may pass on a given run. In that case it just runs to the end without stopping. Run it again until it stops at the failure.

</div>

</div>

Try [`robotcode robot-debug`](/guides/cli/robot-debug/) in your own terminal. It takes the same inputs that the agent sends one by one with [`robotcode session`](/guides/cli/sessions/). The answer also says what `--output NONE --log NONE --report NONE` is for, which matters when you work with the agent: a run in the debugger replaces the results of the last run, so if you still need them, say so when you start it.

## Stop where you say

You can also name the place, and go on from one stop to the next:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Run the order tests in the debugger and stop at line 19 of `tests/orders.robot`.

</div>

<div class="rc-session-calls">

- [`robotcode discover suites`](/guides/cli/discovering-tests/#suites--flat-list-of-suites)
- [`robotcode session start debug --break tests/orders.robot:19 -bl "Tests.Orders"`](/guides/cli/sessions/#starting-a-session)
- [`robotcode session send debug-b0b6c650 '.where'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-b0b6c650 '.vars --user'`](/guides/cli/sessions/#sending-an-input)

</div>

<div class="rc-session-answer">

**Agent:** The debugger is paused at line 19 of `tests/orders.robot`, in the test **Order Coffee**. That line, `Order Status Should Be    ${order}    placed`, hasn't run yet.

I ran the whole `Tests.Orders` suite, selected by longname so the parent suite's setup also runs. The command was `robotcode session start debug --break tests/orders.robot:19 -bl "Tests.Orders"`.

…

This debug run will overwrite the output files from the last run in `results/`.

</div>

</div>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Show me all variables I set myself.

</div>

<div class="rc-session-answer">

**Agent:** These are the user variables at the current stop on line 19 of `tests/orders.robot`. The session is still paused there, so nothing has changed since I listed them with `.vars --user`:

| Scope | Variable | Value | Set by |
|---|---|---|---|
| Test | `${order}` | `'order-4711'` | `Create Order` on line 18 |
| Global | `${BASE_URL}` | `'http://localhost:8080'` | `[variables]` in `robot.toml` |
| Global | `${BROWSER}` | `'chromium'` | `[variables]` in `robot.toml` |

The local and suite scopes are empty. Robot Framework's built-in variables, such as `${TEST NAME}` and `${OUTPUT DIR}`, are left out. …

</div>

</div>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Set a second breakpoint at line 21 of `resources/orders.resource` and continue.

</div>

<div class="rc-session-calls">

- [`robotcode session send debug-b0b6c650 '.break resources/orders.resource:21'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-b0b6c650 '.continue'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-b0b6c650 '.where'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-b0b6c650 '.vars --user'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-b0b6c650 '.print ${status}'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-b0b6c650 '.print ${expected}'`](/guides/cli/sessions/#sending-an-input)

</div>

<div class="rc-session-answer">

**Agent:** I added breakpoint 2 at `resources/orders.resource:21` and continued. The run is now paused there, still in **Order Coffee**. The step about to run is `Should Be Equal    ${status}    ${expected}`, inside `Order Status Should Be`, which was called from `tests/orders.robot:19`.

**Values being compared:**
- `${status}` is `'placed'`, from `Order Status` on line 20.
- `${expected}` is `'placed'`, passed in from the test.

The two values match, so this assertion should pass.

…

Both breakpoints stay active for the rest of the session. The next `.continue` will also stop at line 21 for **Express Order**, which calls the same keyword, though not at line 19, because that test's status check is on line 25.

</div>

</div>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Let it run to the end, and close the debugger.

</div>

<div class="rc-session-calls">

- [`robotcode session send debug-b0b6c650 '.disable'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send debug-b0b6c650 '.continue'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session stop debug-b0b6c650`](/guides/cli/sessions/#ending-a-session)

</div>

<div class="rc-session-answer">

**Agent:** The Orders suite ran to the end and the debugger is closed. **2 of 3 tests passed and 1 failed.**

| Test | Result |
|---|---|
| Order Coffee | PASS |
| Express Order | **FAIL**: `placed != express` |
| Sold Out Product Cannot Be Ordered | PASS |

I disabled both breakpoints before continuing. The run still paused once, because the debugger stops at an uncaught failure by default; I continued past it.

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
