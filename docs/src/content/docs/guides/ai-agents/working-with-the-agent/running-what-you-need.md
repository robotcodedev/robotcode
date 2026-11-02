---
title: Running What You Need
description: "Step 3 of the tutorial: let the agent run exactly the tests you name, by tag, suite or long name and with a profile, and find out what a profile changes before you rely on it."
sidebar:
  label: 3. Running What You Need
  order: 150.43
---

Running every test is rarely what you want. The agent runs the part you name, with the profile you name, and reads the result with `robotcode results` instead of the console output.

## What you learn

- how to name what to run: a tag, a suite or one test;
- what a profile changes, and how to see it before a run;
- how the agent reads the result of a run.

## How to ask the agent

- *"Which tests are in our `<tag>` test?"*, before you run them
- *"Run the tests tagged `<tag>`."* or *"Run `<suite or test>`."*
- *"Run them with the `<profile>` profile."*, or in the words of the profile, such as *"against staging"*
- *"Run the web tests in `<browser>`."*
- *"Rerun just the tests that failed last time."*

The sessions below start with *"Which tests are in our smoke test?"* and *"Can the Browser library run our web tests in Firefox?"*

## What the agent does

### It looks at the profiles first

`robotcode profiles list` shows the project's profiles with their descriptions, and `robotcode -p <profile> discover tests` the tests a profile would run, without running them. From the session *Smoke tests on staging*:

<!-- excerpt: smoke-tests-on-staging -->
```console
$ robotcode profiles list; echo ---; robotcode discover tests -i smoke; echo --- ci; robotcode -p ci discover tests -i smoke
| Active | Selected | Enabled | Precedence | Name | Description           |
|:------:|:------:|:--------:|:-------:|:-----|:----------------------|
|        |          |         |         | ci   | Staging shop          |
|        |          |         |         | dev  | Local shop in Firefox |
…
```

A profile is a global option of `robotcode`. It goes before the subcommand, as in `robotcode -p ci robot -i smoke`; after `robot`, Robot Framework would take it for an option of its own.

### It selects what you name

Tags with `-i` and `-e`, suites with `-s`, and one test, task or suite with `-bl` and its long name. The skill tells the agent to select one test by its long name and not by its `.robot` file: a single file becomes the top suite, and the `__init__.robot` files of the folders above it, with their suite setup and variables, don't run.

### It checks what the run reached

After a run, Robot Framework's exit code is the number of failed tests, and the agent reads the failures with `robotcode results`. In the session, it also looked at what the `ci` profile changes:

<!-- excerpt: smoke-tests-on-staging -->
> **About staging:** I ran it with the `ci` profile (`robotcode -p ci robot -i smoke`), the same way CI does. But all the profile does is set `BASE_URL` to `https://staging.shop.example`, and these tests don't use that address. They use the keywords in `resources/`, which call `ShopLibrary`, and that runs the shop in memory. None of the suites load the Browser library, so this run tested the in-memory shop, not staging. The same is true of CI.

### It finds another browser in the profile

Asked whether the web tests can run in Firefox, the agent read the arguments of `New Browser` with `robotcode doc` and found that the `dev` profile already selects Firefox. It then ran the search suite with `robotcode -p dev robot -s Search`.

More on profiles: [Profiles](/guides/robot-toml/profiles/).

## What to watch out for

- **Check what a profile changes.** A profile named after a system doesn't make the tests reach it. Ask the agent what a profile changes, or look yourself with `robotcode -p <profile> config show`.
- **A run replaces the results of the last one.** As in [step 2](/guides/ai-agents/working-with-the-agent/writing-a-test/), ask for another output directory if you still need them.
- **Point the agent to `robotcode results` when it reads `output.xml`.** In the session *Another browser*, it searched `output.xml` with `grep` to see which browser ran, which the skill tells it not to do: an `output.xml` can be hundreds of megabytes, and `robotcode results log` shows the arguments of `New Browser` too.

## The sessions

<!-- session: smoke-tests-on-staging -->
<details class="rc-session-details">
<summary>Smoke tests on staging <span>“Which tests are in our smoke test?”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which tests are in our smoke test?

</div>

*Loaded the skill `robotcode:robotcode`*

```console
$ robotcode profiles list; echo ---; robotcode discover tests -i smoke; echo --- ci; robotcode -p ci discover tests -i smoke
| Active | Selected | Enabled | Precedence | Name | Description           |
|:------:|:------:|:--------:|:-------:|:-----|:----------------------|
|        |          |         |         | ci   | Staging shop          |
|        |          |         |         | dev  | Local shop in Firefox |

---
# Tests

- **Tests.Cart.Add Item To Cart** (`tests/cart.robot:15`)
- **Tests.Login.Login Works** (`tests/login.robot:11`)
- **Tests.Login.Logout Works** (`tests/login.robot:18`)
- **Tests.Orders.Order Coffee** (`tests/orders.robot:14`)

## Statistics

- _Suites:_ 4
- _Suites with tests:_ 3
- _Tests:_ 4

--- ci
# Tests

…
```

<div class="rc-session-answer">

**Agent:** Four tests are tagged `smoke`, so they make up the smoke test:

| Test | Location |
|---|---|
| Tests.Cart.Add Item To Cart | `tests/cart.robot:15` |
| Tests.Login.Login Works | `tests/login.robot:11` |
| Tests.Login.Logout Works | `tests/login.robot:18` |
| Tests.Orders.Order Coffee | `tests/orders.robot:14` |

You get the same four with the default settings and with the `ci` profile. The search suite has no smoke tests.

To run only the smoke test: `robotcode robot -i smoke`, or `robotcode -p ci robot -i smoke` against staging.

</div>

<div class="rc-session-prompt">

**You:** Run them against staging.

</div>

```console
$ robotcode -p ci robot -i smoke; echo "EXIT=$?"
==============================================================================
Tests :: Web shop acceptance tests                                            
==============================================================================
Tests.Cart :: Filling and emptying the cart.                                  
==============================================================================
Add Item To Cart :: A product added to the cart is in the cart.       | PASS |
------------------------------------------------------------------------------
Tests.Cart :: Filling and emptying the cart.                          | PASS |
1 test, 1 passed, 0 failed
==============================================================================
Tests.Login :: Logging in to the shop and out again.                          
==============================================================================
Login Works :: A user who logs in is greeted by name.                 | FAIL |
Welcome back, alice! != Welcome back, Alice!
------------------------------------------------------------------------------
Logout Works :: A user who logs out is no longer logged in.           | PASS |
------------------------------------------------------------------------------
Tests.Login :: Logging in to the shop and out again.                  | FAIL |
2 tests, 1 passed, 1 failed
==============================================================================
Tests.Orders :: Placing orders.                                               
==============================================================================
Order Coffee :: An order for a product in stock is placed.            | PASS |
------------------------------------------------------------------------------
Tests.Orders :: Placing orders.                                       | PASS |
1 test, 1 passed, 0 failed
…
Log:     ~/webshop/results/log.html
Report:  ~/webshop/results/report.html
EXIT=1
```

*…*

<div class="rc-session-answer">

**Agent:** Three of the four smoke tests passed and one failed. The run didn't actually reach staging, though.

**The failure:** `Tests.Login.Login Works` expected `Welcome back, Alice!` but got `Welcome back, alice!`. The greeting uses the username in lowercase instead of the capitalized name. I haven't checked whether the shop or the test is wrong.

**About staging:** I ran it with the `ci` profile (`robotcode -p ci robot -i smoke`), the same way CI does. But all the profile does is set `BASE_URL` to `https://staging.shop.example`, and these tests don't use that address. They use the keywords in `resources/`, which call `ShopLibrary`, and that runs the shop in memory. None of the suites load the Browser library, so this run tested the in-memory shop, not staging. The same is true of CI.

The log is at `results/log.html` and the report at `results/report.html`.

</div>

</div>

</details>
<!-- /session -->

<!-- session: another-browser -->
<details class="rc-session-details">
<summary>Another browser <span>“Can the Browser library run our web tests in Firefox?”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Can the Browser library run our web tests in Firefox?

</div>

*Loaded the skill `robotcode:robotcode`*

```console
$ cat robot.toml; robotcode doc keyword Browser "New Browser" 2>&1 | head -60
paths = ["tests"]
python-path = ["libraries"]
output-dir = "results"

[variables]
BASE_URL = "http://localhost:8080"
BROWSER = "chromium"

[profiles.dev]
description = "Local shop in Firefox"
extend-variables = { BROWSER = "firefox" }

[profiles.ci]
description = "Staging shop"
…
```

*…*

<div class="rc-session-answer">

**Agent:** Yes. Firefox is supported, the project is already set up for it, and the Firefox browser has been downloaded.

- **The library supports it.** Per `robotcode doc`, the `browser` argument of `New Browser` accepts `chromium`, `firefox` or `webkit`. Playwright ships its own browsers, so you don't need geckodriver.
- **Firefox is installed.** The Browser library's Playwright folder in `.venv` contains `firefox-1543` next to Chromium, so `rfbrowser init` already fetched it.
- **The tests are set up to switch.** `resources/search.resource:14` calls `New Browser    ${BROWSER}`. In `robot.toml`, the default is `BROWSER = "chromium"` and the `dev` profile changes it to `firefox`.

To run the web tests (the search suite) in Firefox:

```bash
robotcode -p dev robot -s Search
```

Or use any profile and set the variable yourself: `robotcode robot -v BROWSER:firefox -s Search`.

The CI runs `robotcode -p ci robot`, and the `ci` profile only changes `BASE_URL`. So CI still tests in Chromium. If you want Firefox there too, add `BROWSER = "firefox"` to `[profiles.ci.extend-variables]`.

I haven't run the suite. That needs the shop page running at `http://localhost:8080`. If it's up, I can run the search tests in Firefox now to confirm.

</div>

<div class="rc-session-prompt">

**You:** The shop is running. Then run the web tests in Firefox.

</div>

```console
$ robotcode -p dev robot -s Search 2>&1 | tail -30; echo "exit=$?"
==============================================================================
Tests :: Web shop acceptance tests                                            
==============================================================================
Tests.Search :: Finding products by their name.                               
==============================================================================
Find Coffee                                                           | PASS |
------------------------------------------------------------------------------
Find Tea                                                              | PASS |
------------------------------------------------------------------------------
Find Several                                                          | PASS |
…
Log:     ~/webshop/results/log.html
Report:  ~/webshop/results/report.html
exit=0
```

```console
$ robotcode results log --suite-info --max-depth 1 2>&1 | head -20; grep -o 'firefox[^<]\{0,60\}' results/output.xml | sort | uniq -c | head
# Log

## Suite: Tests.Search (`tests/search.robot`) ✅ **PASS**
> Finding products by their name.

- _Owner:_ Team Catalog

### Test: Tests.Search.Find Coffee (`tests/search.robot:12`) ✅ **PASS** _(19:08:55 · 1 ms)_
…
      1 firefox
      3 firefox.
      3 firefox", "headless": true, "chromiumSandbox": false, "devtools": f
      3 firefox","headless":true,"chromiumSandbox":false,"devtools":false,"
```

<div class="rc-session-answer">

**Agent:** All 7 tests in the search suite passed with the `dev` profile, which runs them in Firefox.

I checked the run's output to be sure it used Firefox. All three `New Browser` calls opened `firefox` in headless mode.

Only three of the seven tests use the browser:
- Search Page Lists Matching Products With Prices
- Search Page Ignores Case
- Search Page Without Match Shows Message

The other four (Find Coffee, Find Tea, Find Several, Find Nothing) use `ShopLibrary` in memory, so the browser setting doesn't affect them.

Files are in `results/`:
- Report: `results/report.html`
- Log: `results/log.html`

</div>

</div>

</details>
<!-- /session -->
