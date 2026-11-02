---
title: Checking Before a Push
description: "Step 6 of the tutorial: let the agent check the code without running it, with and without the CI profile, find unused code, run the tests and sort what it finds before you push."
sidebar:
  label: 6. Checking Before a Push
  order: 150.46
---

Before you push, the agent checks the code without running it, then runs the tests. Unknown keywords, wrong arguments, unresolved variables and unused code show up before a CI run does.

## What you learn

- what `robotcode analyze code` finds without running anything;
- why the profile matters for the check;
- how the agent reports what it found and leaves the fixes to you.

## How to ask the agent

- *"Check the project for problems before I push."*
- *"Lint only the files I changed today."*
- *"Are there unused keywords or variables?"*
- *"Check it with the `<profile>` profile too."*

The session below starts with *"Check the project for problems before I push."*

## What the agent does

### It analyzes the code

`robotcode analyze code` checks the project statically, without running a test: undefined keywords, unresolved variables, wrong argument counts, failing imports and, with `--collect-unused`, unused keywords and variables. Each finding is one line with the file, the line and the column. From the session *Before a push*:

<!-- excerpt: before-a-push -->
```console
…
resources/orders.resource:23:1: [WARNING] KeywordNotUsed: Keyword 'Submit Order' is not used.
resources/orders.resource:28:1: [WARNING] KeywordNotUsed: Keyword 'Checkout' is not used.
resources/orders.resource:31:5: [ERROR] KeywordNotFound: No keyword with name 'Submit Ordr' found.
Files: 8, Errors: 1, Warnings: 2, Infos: 0, Hints: 0 (in 1.65s)
exit=3
…
```

The exit code is a bitmask: 1 for errors, 2 for warnings, 4 for infos and 8 for hints, so `3` means errors and warnings. The exit code of a test run means something else, the number of failed tests.

### It checks with the CI profile too

A profile can set other variables or paths, and so change what a keyword or a variable resolves to. The agent ran the analysis once more with `-p ci`, and `robotcode discover --diagnostics` for the errors and warnings Robot Framework itself reports when it parses the files. Then it ran the tests and read the result with `robotcode results`.

### It sorts what it found and asks

The agent changed nothing. It sorted what it found by what blocks the push:

<!-- excerpt: before-a-push -->
> I checked the project. It has **one static error, one failing test, and a CI workflow that won't work as written.** I haven't changed anything.
> …
> **Blocking**
> …
> **Worth a look**

More on the analysis: [Analyzing Code](/guides/cli/analyzing-code/).

## What to watch out for

- **Errors first.** A keyword that doesn't exist, like `Submit Ordr`, fails the test that reaches it. An unused keyword is a warning to look at, not necessarily a mistake.
- **Suppress on purpose.** If a finding is intended, mark it with `# robotcode: ignore[<code>]` in the file, so that every later check knows.
- **Check with the profile CI uses.** Say which profile that is, and the agent checks with it too.

## The sessions

<!-- session: before-a-push -->
<details class="rc-session-details">
<summary>Before a push <span>“Check the project for problems before I push.”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Check the project for problems before I push.

</div>

*Loaded the skill `robotcode:robotcode`*

*…*

```console
$ cd ~/webshop; robotcode analyze code --collect-unused; echo "exit=$?"; robotcode -p ci analyze code; echo "ci exit=$?"; robotcode discover --diagnostics all; robotcode discover metadata --values --tests; robotcode discover tags --tests
resources/orders.resource:23:1: [WARNING] KeywordNotUsed: Keyword 'Submit Order' is not used.
resources/orders.resource:28:1: [WARNING] KeywordNotUsed: Keyword 'Checkout' is not used.
resources/orders.resource:31:5: [ERROR] KeywordNotFound: No keyword with name 'Submit Ordr' found.
Files: 8, Errors: 1, Warnings: 2, Infos: 0, Hints: 0 (in 1.65s)
exit=3
resources/orders.resource:31:5: [ERROR] KeywordNotFound: No keyword with name 'Submit Ordr' found.
Files: 8, Errors: 1, Warnings: 0, Infos: 0, Hints: 0 (in 0.02s)
ci exit=1
# All

- **Tests** (`tests`)
  - **Tests.Cart** (`tests/cart.robot`)
    - **Tests.Cart.Add Item To Cart** (`tests/cart.robot:15`)
      - _Tags:_ `cart`, `smoke`
      - _Metadata:_ Requirement: SHOP-201
    - **Tests.Cart.Remove Item From Cart** (`tests/cart.robot:22`)
      - _Tags:_ `cart`
      - _Metadata:_ Requirement: SHOP-202
    - **Tests.Cart.Cart Total Adds Up** (`tests/cart.robot:29`)
      - _Tags:_ `cart`
…

## Statistics

- _Suites:_ 5
- _Suites with tests:_ 4
- _Tests:_ 13
```

*…*

```console
$ cd ~/webshop; robotcode robot > /tmp/run.txt 2>&1; echo "exit=$?"; robotcode results summary --failed; grep -n "Library\|Browser" -r tests resources | head; grep -n "def \|USERS\|PRICES\|STOCK\|=" libraries/ShopLibrary.py | head -50
exit=1
# Summary — results/output.xml

- _Status:_ ❌ **FAIL**
- _Total:_ 13
- _Passed:_ 12
- _Failed:_ 1
- _Skipped:_ 0
- _Started:_ 2026-10-29 19:37:00
- _Ended:_ 2026-10-29 19:37:00
- _Elapsed:_ 37 ms
- _Messages:_ 3 FAIL

## Failures (1)
…
79:        self._orders[order] = "express" if express else "placed"
83:    def order_status(self, order: str) -> str:
88:    def search_products(self, text: str) -> list[str]:
90:        return sorted(product for product in PRICES if text in product)
```

*…*

<div class="rc-session-answer">

**Agent:** I checked the project. It has **one static error, one failing test, and a CI workflow that won't work as written.** I haven't changed anything.

**Blocking**

1. **Misspelled keyword:** `resources/orders.resource:31`. `Checkout` calls `Submit Ordr`, but the keyword is `Submit Order`. This is the only error `robotcode analyze code` reports, with both the default and the `ci` profile. No test calls `Checkout` or `Submit Order`, so test runs don't catch it.

2. **Failing test:** `Tests.Login.Login Works`. Locally 12 of 13 tests pass. This one fails with `Welcome back, alice! != Welcome back, Alice!`. `greeting()` in `libraries/ShopLibrary.py:39` uses the login name as it is, but the test expects it capitalised. This is a smoke test, so the smoke run is red too. You need to decide which side is right; to fix the library, change it to `self._user.capitalize()`, or a display-name lookup.

3. **The CI workflow is out of step with the project:** `.github/workflows/tests.yml`.
   - It runs `pip install robotframework robotcode[runner]` instead of `uv sync`. That skips `uv.lock` and doesn't install the Browser library or run `rfbrowser init`. The suites don't use Browser yet, so this works for now, but it will break once they do.
   - `pyproject.toml` takes `robotcode` and its packages from `~/robotcode` (`[tool.uv.sources]`). Switching CI to `uv sync` would fail on that path, and anyone else cloning the repo can't run `uv sync` either. Decide whether those path sources should be pushed at all.

**Worth a look**

4. **Requirement files are missing.** The tests cite SHOP-101–103, 201–203 and 301–303, but `requirements/` only has `SHOP-110.md`, and no test cites that one.
5. **Search doesn't meet SHOP-110.** Criterion 3 says search ignores upper and lower case, but `search_products` compares case-sensitively (`text in product`). No test checks this, so a test like `Find Coffee    COFF    coffee` would catch it.
6. **Unused keywords:** `Submit Order` and `Checkout` in `orders.resource` aren't used anywhere. Once the typo is fixed, either write a test for them or remove them.

**Conventions are followed**
- Every suite has `Metadata    Owner`.
- The login, cart and orders suites have their area `Test Tags`.
- Every login, cart and orders test has a `Requirement`, and the three high-risk tests have `Risk    high`.
- There are four smoke tests.
- The profiles `dev` and `ci` resolve correctly, and results go to `results/`, which is in `.gitignore`.

The working tree is clean, so all of this is in commit `558e3cc`. Do you want me to fix 1 and 2 (and whichever of the others you choose) before you push?

</div>

</div>

</details>
<!-- /session -->
