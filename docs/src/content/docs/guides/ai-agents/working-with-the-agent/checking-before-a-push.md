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
Files: 8, Errors: 1, Warnings: 2, Infos: 0, Hints: 0 (in 0.03s)
exit=3
…
```

The exit code is a bitmask: 1 for errors, 2 for warnings, 4 for infos and 8 for hints, so `3` means errors and warnings. The exit code of a test run means something else, the number of failed tests.

### It checks with the CI profile too

A profile can set other variables or paths, and so change what a keyword or a variable resolves to. The agent ran the analysis once more with `-p ci`. Then it ran the tests and read the result with `robotcode results`.

### It sorts what it found and asks

The agent changed nothing. It sorted what it found by what blocks the push:

<!-- excerpt: before-a-push -->
> **I wouldn't push yet.** The CI would go red because `Login Works` fails, and two other problems also need fixing first. I didn't change any files; the only thing overwritten is the ignored `results/` folder.
> …
> **Fix before pushing**
> …
> **Worth fixing soon**

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
$ robotcode analyze code; echo "exit=$?"; robotcode -p ci analyze code; echo "ci exit=$?"; robotcode profiles list; robotcode discover all; robotcode discover tags --tests; robotcode discover metadata --values --tests;robotcode discover metadata --values --suites; find . -path ./.venv -prune -o -path ./.git -prune -o -type f -print
resources/orders.resource:31:5: [ERROR] KeywordNotFound: No keyword with name 'Submit Ordr' found.
Files: 8, Errors: 1, Warnings: 0, Infos: 0, Hints: 0 (in 1.96s)
exit=1
resources/orders.resource:31:5: [ERROR] KeywordNotFound: No keyword with name 'Submit Ordr' found.
Files: 8, Errors: 1, Warnings: 0, Infos: 0, Hints: 0 (in 0.03s)
ci exit=1
…
```

*…*

```console
$ robotcode analyze code --collect-unused; echo "exit=$?"; robotcode robot; echo "robot exit=$?"; robotcode results summary --failed; robotcode results show --failed; git status --short
resources/orders.resource:23:1: [WARNING] KeywordNotUsed: Keyword 'Submit Order' is not used.
resources/orders.resource:28:1: [WARNING] KeywordNotUsed: Keyword 'Checkout' is not used.
resources/orders.resource:31:5: [ERROR] KeywordNotFound: No keyword with name 'Submit Ordr' found.
Files: 8, Errors: 1, Warnings: 2, Infos: 0, Hints: 0 (in 0.03s)
exit=3
…
# Show — results/output.xml

- ❌ **FAIL** Tests.Login.Login Works (`tests/login.robot:11`) _(22:41:12 · 1 ms)_
  > Welcome back, alice! != Welcome back, Alice!

## Statistics

- _Total:_ 1
- _Passed:_ 0
- _Failed:_ 1
- _Skipped:_ 0
- _Started:_ 2026-11-03 22:41:12
- _Ended:_ 2026-11-03 22:41:12
- _Elapsed:_ 38 ms

_Filters: status=fail_
```

*…*

<div class="rc-session-answer">

**Agent:** **I wouldn't push yet.** The CI would go red because `Login Works` fails, and two other problems also need fixing first. I didn't change any files; the only thing overwritten is the ignored `results/` folder.

**Fix before pushing**
1. **Failing test:** `Tests.Login.Login Works` fails with `Welcome back, alice! != Welcome back, Alice!`. `greeting` uses the raw username (`libraries/ShopLibrary.py:39`), while the test expects it capitalized (`tests/login.robot:16`). The fix probably belongs in the library, but SHOP-101 isn't in `requirements/`, so I can't confirm which side is right.
…
3. **Keyword typo:** `resources/orders.resource:31` calls `Submit Ordr` instead of `Submit Order`. This is the only error from static analysis. No test calls `Checkout`, so the test runs miss it, and the CI doesn't run `analyze`.

**Worth fixing soon**
- **Search ignores the requirement:** SHOP-110 says search ignores case, but `search_products` doesn't: `COFF` finds nothing, while `coff` finds `coffee` (`ShopLibrary.py:90`). The web page handles case correctly, but no test covers case-insensitive search.
- **Web page is untested:** no suite imports the Browser library, so nothing tests `webshop/index.html`, including SHOP-110's "No products found" message.
- **Missing requirements:** all 9 requirements the tests name (SHOP-101–103, 201–203, 301–303) have no file in `requirements/`. The only file there is SHOP-110, and no test names it.
- **CI never touches staging:** `-p ci` only changes `BASE_URL`, which is just logged and shown as metadata, so a green run says nothing about staging. Likewise, `-p dev` doesn't actually run anything in Firefox. The README promises both.
- **CI setup:** it installs unpinned packages with `pip`, ignoring `uv.lock`, and doesn't run `robotcode analyze code`. Adding that step would have caught the typo.

**Minor**
- **Unused code:** the keywords `Submit Order` and `Checkout` are unused, and so is the library keyword `Price Of`.
- **Login state:** `greeting` returns `Welcome back, None!` when nobody is logged in. From reading the code, a failed login also leaves the previous user logged in.
- **Sold-out items:** `put_in_cart` doesn't check stock, so a sold-out `mug` can be added to the cart. `Cart Total Adds Up` relies on this.

**What checked out**
| Check | Result |
|---|---|
| Default profile | 12 of 13 passed |
| `ci` profile | 12 of 13 passed |
| Clean install using the CI's `pip` packages (Python 3.13) | 12 of 13 passed |
| Random test order, 3 seeds | 12 of 13 passed each time |
| `analyze code`, default and `ci` profiles | only the typo above |
| Project conventions (`Owner`, area tags, `Requirement` and `Risk` metadata) | followed |
| Git | working tree clean, no generated files tracked |

Only the default run showed by name that `Login Works` was the failure; the other runs matched on counts.

**Next step**
I can fix the three blockers and add the `analyze` step to the CI. For that, I need two decisions from you:
- **Greeting:** should it say `Alice`? I'd assume yes and change the library.
…

</div>

</div>

</details>
<!-- /session -->
