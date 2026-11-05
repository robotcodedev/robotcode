---
title: Finding Out Why a Test Failed
description: "Step 4 of the tutorial: ask an AI agent what happened in a run and whether a failure is flaky, decide what is right, and only then ask for a fix and for the proof that it works."
sidebar:
  label: 4. Finding Out Why a Test Failed
  order: 150.44
---

A test failed. Before anything changes, you want to know what happened, whether it happens every time, and which side is wrong. An agent can find out the first two for you. The third is your decision. Only then do you ask for a fix. On the way, you get to know the `robotcode` commands that read the results of a run.

To follow along, use the [example project](/guides/ai-agents/working-with-the-agent/#following-along).

## Ask what happened

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Run all tests and give me a summary of the run: what failed and why?

</div>

<div class="rc-session-calls">

- [`robotcode robot`](/reference/cli/#robot)
- [`robotcode results log --failed`](/guides/cli/analyzing-results/#log--walk-the-execution-tree)

</div>

<div class="rc-session-answer">

**Agent:** **Run summary:** 13 tests, 11 passed, 2 failed (exit code 2).

| Suite | Result |
|---|---|
| Cart | 3/3 passed |
| Login | 2/3 passed |
| Orders | 2/3 passed |
| Search | 4/4 passed |

**Failures**

1. **Login Works** (`tests/login.robot:11`, requirement SHOP-101)
   - The error is `Welcome back, alice! != Welcome back, Alice!`.
   - The shop's `Greeting` returns the username as given (`alice`), but the test expects it capitalized (`Alice`).
   - Either the library should capitalize the name or the test's expected string is wrong. I haven't checked which of the two is the intended behaviour.

2. **Express Order** (`tests/orders.robot:21`, requirement SHOP-302)
   - The error is `placed != express`.
   - `Create Order beans express=${True}` passes the express flag through to `ShopLibrary.Place Order`, which returns `order-4712`. `Order Status` for that order then returns `placed` instead of `express`.
   - This looks like a real bug in the shop library, which ignores or doesn't record the express flag. A wrong expectation in the test is less likely. I haven't read the library code to confirm.

…

</div>

</div>

A question gets you an answer: the agent looks and reports, and it leaves the files alone. If you have already run the tests, ask about that run instead, and the agent reads its results:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Check the last run. Why did it fail?

</div>

</div>

In the answer, look for three things:

- **The failure as the run reported it**, not a guess.
- **What the agent only assumes.** Here, it thinks that `Express Order` is a bug in the shop, and it says that it hasn't checked.
- **What it can't tell.** Here, nothing says which greeting is right.

Your first run may show only `Login Works` failing. The next sections explain why.

## See how it found out

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which `robotcode` commands did you use to find that out? I want to run them myself.

</div>

<div class="rc-session-answer">

**Agent:** I used two commands, both from the project root:

1. **Run the tests:**
   ```bash wrap
   robotcode robot
   ```
   It takes the paths and output settings from `robot.toml`. The exit code is the number of failed tests, which was 2 here.

2. **Read the failure details from the finished run, without re-running:**
   ```bash wrap
   robotcode results log --failed
   ```
   This printed the execution tree for the two failed tests. It showed each keyword's result and the `[INFO]` lines, such as `${greeting} = Welcome back, alice!` and `${status} = placed`.

Other `robotcode results` subcommands show the same run in different forms. I didn't use them, but they're the usual next steps:

```bash wrap
robotcode results summary --failed   # headline counts plus the failing tests
robotcode results show               # one line per test, with filters
robotcode results stats              # aggregate by suite, tag or status
```

…

</div>

</div>

Run them. You see what the agent saw, and from now on, you can look at a run without the agent too.

Each command has its own documentation: [`robotcode robot`](/reference/cli/#robot), [`robotcode results log`](/guides/cli/analyzing-results/#log--walk-the-execution-tree), [`robotcode results summary`](/guides/cli/analyzing-results/#summary--headline-numbers), [`robotcode results show`](/guides/cli/analyzing-results/#show--list-individual-tests) and [`robotcode results stats`](/guides/cli/analyzing-results/#stats--aggregate-by-tag-suite-or-status). Your agent may name others, such as [`robotcode results diff`](/guides/cli/analyzing-results/#diff--compare-two-runs).

## Check whether it fails every time

One failed run doesn't tell you whether the failure is real or only happens sometimes. So ask:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Run all tests a few more times and compare the runs. Is any test flaky?

</div>

<div class="rc-session-calls">

- [`robotcode robot --output run$i.xml --log NONE --report NONE`](/reference/cli/#robot)
- …
- [`robotcode results show --failed -o results/run$i.xml`](/guides/cli/analyzing-results/#show--list-individual-tests)
- [`robotcode results diff results/output.xml results/run$i.xml`](/guides/cli/analyzing-results/#diff--compare-two-runs)
- [`robotcode results log -bl "Tests.Orders.Express Order" -o results/run$i.xml`](/guides/cli/analyzing-results/#log--walk-the-execution-tree)

</div>

<div class="rc-session-answer">

**Agent:** **Yes, one test is flaky: `Tests.Orders.Express Order` (`tests/orders.robot:21`).** I ran the suite four more times, for five runs in total.

| Run | Exit code | Login Works | Express Order |
|---|---|---|---|
| 0 (first run) | 2 | FAIL | FAIL |
| 1 | 1 | FAIL | PASS |
| 2 | 2 | FAIL | FAIL |
| 3 | 2 | FAIL | FAIL |
| 4 | 1 | FAIL | PASS |

- **Express Order:** It failed in 3 of 5 runs and passed in 2. The other 11 tests gave the same result every time.
- **Login Works:** It failed in all five runs with the same message, so it isn't flaky. The failure is deterministic, as I described earlier.
- …
- **Correction to my earlier explanation:** I said the library probably ignored the express flag. That was wrong. `place_order` stores `express` correctly, and the test only fails when the status is read before the simulated confirmation.

…

</div>

</div>

These are two different problems. `Login Works` fails every time, so the test and the shop really disagree. `Express Order` only fails sometimes, so running it again would hide the problem, not solve it. A few runs can't prove that a test is stable, but they show the ones that aren't.

Look at the correction too. What the agent had only assumed after one run turned out to be wrong, and a fix based on it would have gone after the wrong thing.

Ask for the reason:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Why does `Express Order` fail only sometimes?

</div>

<div class="rc-session-answer">

**Agent:** The failure depends on a coin flip inside `ShopLibrary.order_status` (`libraries/ShopLibrary.py:86-93`):

```python wrap
# The warehouse confirms an express order a moment later.
if self._orders[order] == "express" and order not in self._confirmed:
    self._confirmed.add(order)
    if random.random() < 0.5:
        return "placed"
return self._orders[order]
```

1. `place_order` correctly stores the order as `express`.
2. The first time `order_status` is called for an express order, the order isn't in `_confirmed` yet. The library adds it, then returns `placed` with 50% probability. This simulates the warehouse not having confirmed the order yet.
3. Every later call for that order returns `express`.

`Express Order` calls `Order Status Should Be` exactly once, so it only ever sees that first call. It fails when the coin flip lands on `placed`, which is about half the time. …

</div>

</div>

## Decide what is right

The results show where the test and the shop disagree, not which of them is right. An agent can't know that unless something in the project says so. So this part is yours: look at the requirement, or ask whoever knows. If the requirement lives somewhere the agent can read, tell it where.

For this example, take `Login Works` as right. The shop may take a moment to confirm an order, so `Express Order` has to wait for it.

## Ask for the fix and for the proof

<div class="rc-session">

<div class="rc-session-prompt">

**You:** `Login Works` is right: the shop should greet users with a capital letter. `Express Order` should wait until the order is confirmed. Fix the failing tests, run all tests a few times and tell me whether anything still fails.

</div>

<div class="rc-session-calls">

- [`robotcode analyze code`](/guides/cli/analyzing-code/)
- [`robotcode robot --output fix$i.xml --log NONE --report NONE`](/reference/cli/#robot)
- [`robotcode results summary -o results/fix$i.xml`](/guides/cli/analyzing-results/#summary--headline-numbers)

</div>

<div class="rc-session-answer">

**Agent:** Nothing fails any more. I ran all 13 tests 10 times and every run had 13 passed, 0 failed, with exit code 0 each time.

**Changes**
- **`Login Works`:** `libraries/ShopLibrary.py` now capitalizes the user name in `greeting`, so `alice` is greeted as `Welcome back, Alice!`. I fixed it in the library rather than the test, as you said the shop should greet with a capital letter. If nobody is logged in, it still returns `Welcome back, None!` as before.
- **`Express Order`:** `tests/orders.robot` now retries the status check for up to 5 attempts, 200 ms apart, until the order shows `express`:
  ```robot wrap
  Wait Until Keyword Succeeds    5x    200ms
  ...    Order Status Should Be    ${order}    express
  ```
  The simulated confirmation only delays the first status check, so the second attempt always sees `express`. The test can't fail from that delay any more.

Ten passes is good evidence, but not proof. Before the fix this test failed about half the time, so ten clean runs by chance would be roughly a 1-in-1000 event.

…

</div>

</div>

Now "fix" is the right word, because the agent no longer has to guess. If you only say "Fix the failing test", it picks a side by itself: sometimes it changes the library, sometimes the test, and the test passes either way.

"A few times" is your proof. After a flaky test, one passing run shows nothing.

## Look at the change

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Show me what you changed.

</div>

<div class="rc-session-answer">

**Agent:** That's the whole diff: two files, 4 lines added and 2 removed. Nothing is committed.

- **`libraries/ShopLibrary.py`:** `greeting` now capitalizes the user name, so the login test gets `Welcome back, Alice!`.
- **`tests/orders.robot`:** `Express Order` now retries `Order Status Should Be` up to 5 times, 200 ms apart, until the status is `express`.

…

</div>

</div>

Passing tests show that the tests pass, not that the change is good. Check that the agent changed what you asked for and nothing else, and look for what no test covers. The new greeting, for example, isn't always the same: depending on how the agent wrote it, it raises an error when nobody is logged in, or it says `Welcome back, None!`. So ask:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** What does the greeting do when nobody is logged in?

</div>

<div class="rc-session-answer">

**Agent:** It returns `Welcome back, None!`, the same as before my change.

When nobody is logged in, `self._user` is `None`. The conditional in my change then leaves `name` as `None`, and the f-string prints it as the text `None`. I read this from the code and didn't run it.

That output is a quirk of the original code, not something I introduced. I kept the behaviour the same because you only asked for the capitalization fix. A shop greeting that says "None" is probably not what you want, though.

…

</div>

</div>

## In your own project

- Ask what happened before you ask for a fix: *"Check the last run. Why did it fail?"*
- Ask for the commands, and run them yourself.
- Before you look for a cause, find out whether the failure happens every time.
- Take what the agent only assumes as an assumption, until something confirms it.
- Decide what is right. Don't leave that to the agent.
- Then ask for the fix: say which side is right, and how you want it proven.
- Ask to see the change, also when all tests pass.
