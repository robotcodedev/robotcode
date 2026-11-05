---
title: Running What You Need
description: "Step 3 of the tutorial: tell an AI agent what to run in your own words, by tag, suite, test or profile, check what the run really reached, and keep the results you still need."
sidebar:
  label: 3. Running What You Need
  order: 150.43
---

Running every test is rarely what you want. Say what you want to run, in your own words, and the agent works out how to select it. Then check that the run did what you meant, because the agent runs what the project's settings say, and that can differ from what the name of a setting promises.

To follow along, use the [example project](/guides/ai-agents/working-with-the-agent/#following-along).

## Say what you want to run

If you aren't sure what a word like "smoke test" means in a project, ask first. Nothing runs for that:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which tests are in our smoke test?

</div>

<div class="rc-session-calls">

- [`robotcode discover tags --tests`](/guides/cli/discovering-tests/#tags--tag--tests-dictionary)
- [`robotcode discover tests -i smoke`](/guides/cli/discovering-tests/#tests--flat-list-of-tests)

</div>

<div class="rc-session-answer">

**Agent:** The smoke test is the set of tests tagged `smoke`. There are 4 of them, out of 13 tests in the project:

| Test | Location |
| --- | --- |
| Tests.Cart.Add Item To Cart | `tests/cart.robot:15` |
| Tests.Login.Login Works | `tests/login.robot:11` |
| Tests.Login.Logout Works | `tests/login.robot:18` |
| Tests.Orders.Order Coffee | `tests/orders.robot:14` |

I found them with `robotcode discover tests -i smoke`. To run just those, use `robotcode robot -i smoke`.

</div>

</div>

Both commands have their own documentation: [`robotcode discover tests`](/guides/cli/discovering-tests/#tests--flat-list-of-tests) and [`robotcode robot`](/reference/cli/#robot). Now run them. "Staging" isn't a setting of the project, it's your word for it:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Run them against staging.

</div>

<div class="rc-session-calls">

- [`robotcode profiles list`](/reference/cli/#profiles)
- [`robotcode -p staging profiles show`](/reference/cli/#profiles)
- [`robotcode -p ci profiles show`](/reference/cli/#profiles)
- [`robotcode -p ci robot -i smoke`](/reference/cli/#robot)

</div>

<div class="rc-session-answer">

**Agent:** I ran the 4 smoke tests against staging with the `ci` profile. 3 passed and 1 failed.

| Test | Result |
| --- | --- |
| Add Item To Cart | PASS |
| Login Works | **FAIL** |
| Logout Works | PASS |
| Order Coffee | PASS |

**Login Works** failed with `Welcome back, alice! != Welcome back, Alice!`. The greeting shows the username in lowercase, but the test expects it capitalized. I haven't looked into the cause. Either staging doesn't capitalize the name, or the test's expected value is wrong.

…

</div>

</div>

## Check what the run reached

The agent says that the tests ran against staging. Before you rely on that, ask:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Did those tests really talk to the staging shop? What does the `ci` profile change?

</div>

<div class="rc-session-calls">

- [`robotcode config show`](/reference/cli/#config)
- [`robotcode -p dev profiles show`](/reference/cli/#profiles)
- [`robotcode results log --search staging.shop.example`](/guides/cli/analyzing-results/#log--walk-the-execution-tree)

</div>

<div class="rc-session-answer">

**Agent:** **No. The tests never talked to the staging shop.** The `ci` profile only changed a variable, and nothing in the project uses it to connect anywhere.

**What `ci` changes.** It overrides one setting, `BASE_URL`. The default is `http://localhost:8080`, and `ci` sets it to `https://staging.shop.example`. `BROWSER` stays `chromium`. The `dev` profile is the other one, and it only switches `BROWSER` to `firefox`.

**Why no traffic went to staging:**
- `ShopLibrary` is an in-memory fake. Its docstring says "The shop runs in memory, so the suites need no server." It makes no HTTP calls and never reads `BASE_URL`.
- `BASE_URL` is only used in two places:
  - `Open Shop As` in `resources/shop.resource` logs it: `Opened https://staging.shop.example as alice`.
  - `tests/__init__.robot` records it as suite metadata (`Shop URL`).
- The log line is the only evidence of "staging", and it just prints the variable. The same tests would behave identically with the `dev` profile or no profile.

…

</div>

</div>

A profile sets values, and only what uses those values changes. Here, the suites run the shop in memory, so a green test says nothing about the staging shop, whatever the profile is called. In your own project the reason may be another one, but the question stays the same: did the run reach what its name promises? [Profiles](/guides/robot-toml/profiles/) explains what a profile can set.

## Run one test, or only the failures

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Run only `Login Works`.

</div>

<div class="rc-session-calls">

- [`robotcode discover tests --search "Login Works"`](/guides/cli/discovering-tests/#tests--flat-list-of-tests)
- [`robotcode robot -bl "Tests.Login.Login Works"`](/reference/cli/#robot)

</div>

<div class="rc-session-answer">

**Agent:** I ran only `Login Works` (`Tests.Login.Login Works`, `tests/login.robot:11`). It failed: 1 test, 0 passed, 1 failed.

…

</div>

</div>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Run all tests, then rerun just the ones that failed.

</div>

<div class="rc-session-calls">

- [`robotcode robot`](/reference/cli/#robot)
- [`robotcode robot --rerunfailed results/first-run.xml`](/reference/cli/#robot)

</div>

<div class="rc-session-answer">

**Agent:** Full run: 13 tests, 12 passed, 1 failed. The rerun of the failed test failed again, with the same message.

…

I copied the first run's output to `results/first-run.xml` before rerunning, because the rerun overwrites `results/output.xml`. That file now holds only the rerun result. …

</div>

</div>

Your run may also show `Express Order` failing, which only happens sometimes. [Step 4](/guides/ai-agents/working-with-the-agent/finding-out-why-a-test-failed/) is about that.

## Keep the results you still need

A run replaces the results of the last one. If you still need them, say so:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Run the cart tests, and keep the results of the last run. I still need them.

</div>

<div class="rc-session-calls">

- [`robotcode robot -d results-cart -bl "Tests.Cart"`](/reference/cli/#robot)

</div>

<div class="rc-session-answer">

**Agent:** All 3 cart tests passed: Add Item To Cart, Remove Item From Cart and Cart Total Adds Up.

I wrote this run to a separate directory, `results-cart/`, so the previous results in `results/` are untouched. …

</div>

</div>

## See how it did that

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which `robotcode` commands did you use for that? I want to run them myself.

</div>

<div class="rc-session-answer">

**Agent:** Here are the commands in the order I ran them. Run them from the project directory.

**1. Find the test and run only `Login Works`**
```bash wrap
robotcode discover tests --search "Login Works"
robotcode robot -bl "Tests.Login.Login Works"
```

**2. Run all tests, keep the output, then rerun only the failures**
```bash wrap
robotcode robot
cp results/output.xml results/first-run.xml
robotcode robot --rerunfailed results/first-run.xml
```
I copied the output because the rerun overwrites `results/output.xml`.

**3. Run the cart tests without touching `results/`**
```bash wrap
robotcode robot -d results-cart -bl "Tests.Cart"
```
`-d results-cart` sends the output, log and report to a separate directory. `-bl` selects by longname, as with `Login Works`.

To look at a finished run without rerunning it, use `robotcode results summary` (add `--failed` for the failing tests). …

</div>

</div>

Run them. To pick one test, the agent looks up its long name, the names of its suites and then its own, and selects by that. A profile comes before the command, as in `robotcode -p ci robot`.

The commands are documented at [`robotcode discover tests`](/guides/cli/discovering-tests/#tests--flat-list-of-tests), [`robotcode robot`](/reference/cli/#robot) and [`robotcode results summary`](/guides/cli/analyzing-results/#summary--headline-numbers). Your agent may name others, such as [`robotcode profiles show`](/reference/cli/#profiles).

## In your own project

- Say what you want to run in your own words: a tag, a suite, a test, a system.
- Ask what a word means in the project before you run it.
- Before you rely on a run against another system, ask what the profile changes and whether the run reached that system.
- If you still need the results of the last run, say so.
- Ask for the commands, and run them yourself.
