---
title: Finding Out Why a Test Failed
description: "Step 4 of the tutorial: let the agent read why a test failed from the results of the run, compare two runs, and stop in the debugger when the log is not enough."
sidebar:
  label: 4. Finding Out Why a Test Failed
  order: 150.44
---

When a test fails, the first question is why, not how to run it again. The agent answers it from the results of the run that failed: your last run, the `output.xml` of a CI run, or one that a colleague sends you.

## What you learn

- how the agent reads a failure from a finished run;
- how to point it to the results of another run;
- how to compare two runs;
- when the next step is the debugger.

## How to ask the agent

- *"Why did `<test>` fail in the last run?"*
- *"Why did `<test>` fail in `<path>/output.xml`?"*, for a run that isn't the project's last one
- *"Run all tests and tell me what changed compared with `<path>/output.xml`."*
- *"Show me in the debugger what `<keyword>` returns there."*, when the log is not enough

The sessions below start with *"Why did `Login Works` fail in last night's run?"* and *"Run all tests and tell me what changed compared with last night's run in `results/nightly`."*

## What the agent does

### It reads the results before it runs anything

For "why did this test fail?", the skill tells the agent to read the finished run first, without a new run. `robotcode results summary --failed` lists the failed tests with their messages, and `robotcode results log` shows the keywords of a test with their arguments and status. From the session *A failing test*:

<!-- excerpt: a-failing-test -->
```console
…
## Failures (1)

- ❌ **FAIL** Tests.Login.Login Works (`tests/login.robot:11`)
  > Welcome back, alice! != Welcome back, Alice!

# Log

### Test: Tests.Login.Login Works (`tests/login.robot:11`) ❌ **FAIL** _(22:37:01 · 1 ms)_
…
```

`robotcode results` reads the `output.xml` and returns only the part asked for. Without `-o` (`--output`), it takes the output file of the project's configuration.

### It compares two runs

`robotcode results diff` compares a baseline run with a newer one: new failures, which passed before, and new passes, which failed before. From the session *Comparing runs*, after the fix:

<!-- excerpt: comparing-runs -->
```console
$ robotcode results diff results/nightly/output.xml results/output.xml; echo "diff exit: $?"; robotcode results summary -o results/nightly/output.xml; robotcode results summary --failed; robotcode results stats --by suite -o results/nightly/output.xml; robotcode results stats --by suite; git status --short
# Diff — results/nightly/output.xml → results/output.xml

## New passes (1)

- Tests.Login.Login Works (`tests/login.robot:11`) — ❌ **FAIL** → ✅ **PASS**
…
```

### It goes into the debugger when the log isn't enough

Asked to show in the debugger what the shop returns, the agent started only that test as a debug session, stopped it at the keyword that asks the shop, stepped over the keyword and printed its result:

<!-- excerpt: a-failing-test -->
```console
$ robotcode session send debug-1aeb5b83 '.print ${greeting}'; echo "exit=$?"
${greeting} = 'Welcome back, alice!'
exit=0
```

With `--output NONE --log NONE --report NONE`, the debug run wrote no output files, so the recorded run stayed as it was. Which side to change, it left to you:

<!-- excerpt: a-failing-test -->
> Which fix is right still depends on what SHOP-101 specifies.

After your answer, it fixed the library and ran all tests again. [Step 5](/guides/ai-agents/working-with-the-agent/debugging-step-by-step/) shows the debugger in detail.

More on the commands: [Analyzing Results](/guides/cli/analyzing-results/).

## What to watch out for

- **Name the run if it isn't the last one.** Without a path, the agent reads the output of the project's configuration, and a new run replaces it.
- **Keep the run you investigate.** A new run, also one in the debugger, replaces the output files of the last one unless it writes elsewhere. In *A failing test*, the agent kept the run while it debugged, and told you that the run after the fix replaced it. Ask for another output directory if you still need the results.
- **Decide what is wrong.** The results show where the test and the system disagree, not which of them is right. When the agent asks, answer before it changes anything.

## The sessions

<!-- session: a-failing-test -->
<details class="rc-session-details">
<summary>A failing test <span>“Why did <code>Login Works</code> fail in last night's run?”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Why did `Login Works` fail in last night's run?

</div>

*Loaded the skill `robotcode:robotcode`*

*…*

```console
$ robotcode results summary --failed; echo ---; robotcode --format json results summary | head -40; echo ---; robotcode results log -t "*Login Works*"; echo ---; robotcode results show --search "Login Works"; echo ---; ls -la; ls -la .github/workflows 2>/dev/null; find . -path ./.venv -prune -o \( -name 'output*.xml' -o -name 'output*.json' \) -print
# Summary — results/output.xml

- _Status:_ ❌ **FAIL**
- _Total:_ 13
- _Passed:_ 12
- _Failed:_ 1
- _Skipped:_ 0
- _Started:_ 2026-11-03 22:37:01
- _Ended:_ 2026-11-03 22:37:01
- _Elapsed:_ 68 ms
- _Messages:_ 3 FAIL

## Failures (1)

- ❌ **FAIL** Tests.Login.Login Works (`tests/login.robot:11`)
  > Welcome back, alice! != Welcome back, Alice!

---
…
---
# Log

### Test: Tests.Login.Login Works (`tests/login.robot:11`) ❌ **FAIL** _(22:37:01 · 1 ms)_

_Metadata:_ Requirement: SHOP-101

> Welcome back, alice! != Welcome back, Alice!

- **shop.Open Shop As** `alice` ✅ **PASS** _(22:37:01 · 0 ms)_
  - **ShopLibrary.Log In** `${user}` `${password}` ✅ **PASS** _(22:37:01 · 0 ms)_
  - **BuiltIn.Log** `Opened ${BASE_URL} as ${user}` ✅ **PASS** _(22:37:01 · 0 ms)_
    - `[INFO] Opened http://localhost:8080 as alice`
- **shop.Welcome Message Should Be** `Welcome back, Alice!` ❌ **FAIL** _(22:37:01 · 1 ms)_
  > Welcome back, alice! != Welcome back, Alice!
  - `${greeting}` = **ShopLibrary.Greeting** ✅ **PASS** _(22:37:01 · 0 ms)_
    - `[INFO] ${greeting} = Welcome back, alice!`
  - **BuiltIn.Should Be Equal** `${greeting}` `${expected}` ❌ **FAIL** _(22:37:01 · 0 ms)_
    > Welcome back, alice! != Welcome back, Alice!
    - `[FAIL] Welcome back, alice! != Welcome back, Alice!`

- _Elapsed:_ 1 ms

_Filters: test=\*Login Works\*_
…
```

*…*

<div class="rc-session-answer">

**Agent:** **`Login Works` failed because the greeting's capitalisation doesn't match what the test expects.** However, the only recorded run may not be last night's.

```
Welcome back, alice! != Welcome back, Alice!
```

**Cause**
- **The steps:** `Open Shop As    alice` passed, so the login itself works. The failure is in the next step, `Welcome Message Should Be`, which does an exact, case-sensitive comparison.
- **Expected value:** `tests/login.robot:16` expects `Welcome back, Alice!`.
- **Actual value:** `libraries/ShopLibrary.py:40` builds the greeting directly from the login name, `f"Welcome back, {self._user}!"`. The user is `alice` in lowercase, and the shop has no separate display name.

As the code stands, this test fails every time, so it's not flaky or caused by timing or the environment. It was also the only failure in that run: 12 of 13 tests passed.

**Is this last night's run?**
- **Timing:** the only output in the project is `results/output.xml`, and it started today (2026-11-03) at 22:37:01, not last night.
- **Environment:** that run used `http://localhost:8080`, so it's a local run with no `ci` profile. A CI run would use the staging URL.
- **Schedule:** `.github/workflows/tests.yml` only runs on push, so this workflow has no nightly job.

If last night's run happened somewhere else, send me its `output.xml` and I'll check it. The failure could be different there, especially against staging.

**Which side is wrong?**
I can't tell from the repo whether the shop or the test is wrong. The test's requirement, SHOP-101, isn't in `requirements/`, which only contains `SHOP-110.md`. The test's documentation only says "greeted by name".

- **If customers should see "Alice":** fix the shop, for example with a display name or by capitalising the name in `greeting`.
- **If the login name is meant to be shown as is:** change the expected text in the test to `Welcome back, alice!`.

Do you know which SHOP-101 specifies? I haven't changed anything, and once you tell me I can make the fix. `Login Works` is tagged `smoke`, so the smoke test stays red until then.

The full log is in `results/log.html`.

</div>

<div class="rc-session-prompt">

**You:** Show me in the debugger what the shop returns there.

</div>

*…*

```console
$ robotcode session start debug --output NONE --log NONE --report NONE --break "ShopLibrary.Greeting" -bl "Tests.Login.Login Works"; echo "exit=$?"
Started session debug-1aeb5b83.
==============================================================================
Tests :: Web shop acceptance tests                                            
==============================================================================
Tests.Login :: Logging in to the shop and out again.                          
==============================================================================
Login Works :: A user who logs in is greeted by name.                 
* breakpoint  ShopLibrary.Greeting  (resources/shop.resource:18)
exit=0
```

```console
$ robotcode session send debug-1aeb5b83 '.where'; echo "exit=$?"
> #0  ShopLibrary.Greeting            resources/shop.resource:18
  #1  shop.Welcome Message Should Be  tests/login.robot:16
  #2  Login Works                     tests/login.robot:11
  #3  Login                           tests/login.robot
  #4  Tests                           tests
exit=0
```

```console
$ robotcode session send debug-1aeb5b83 '.list'; echo "exit=$?"
     13      Log    Opened ${BASE_URL} as ${user}
     14  
     15  Welcome Message Should Be
     16      [Documentation]    Checks the greeting the shop shows the user who is logged in.
     17      [Arguments]    ${expected}
->   18      ${greeting}=    Greeting
     19      Should Be Equal    ${greeting}    ${expected}
     20  
     21  User Should Be Logged Out
     22      [Documentation]    Checks that nobody is logged in.
     23      ${user}=    Current User
exit=0
```

<div class="rc-session-answer">

**Agent:** Stopped just before the keyword runs. Next I'll step over it to see what comes back.

</div>

```console
$ robotcode session send debug-1aeb5b83 '.next'; echo "exit=$?"
* step  BuiltIn.Should Be Equal  (resources/shop.resource:19)
exit=0
```

```console
$ robotcode session send debug-1aeb5b83 '.print ${greeting}'; echo "exit=$?"
${greeting} = 'Welcome back, alice!'
exit=0
```

```console
$ robotcode session send debug-1aeb5b83 '.print ${expected}'; echo "exit=$?"
${expected} = 'Welcome back, Alice!'
exit=0
```

```console
$ robotcode session send debug-1aeb5b83 '.whatis ${greeting}'; echo "exit=$?"
${greeting}: str
exit=0
```

```console
$ robotcode session send debug-1aeb5b83 'Current User'; echo "exit=$?"
=> 'alice'
exit=0
```

```console
$ robotcode session stop debug-1aeb5b83; echo "exit=$?"; robotcode session list; ls -l --time-style=long-iso results/; git status --short
aborting the run
Second signal will force exit.
| FAIL |
Execution terminated by signal
------------------------------------------------------------------------------
Tests.Login :: Logging in to the shop and out again.                  | FAIL |
1 test, 0 passed, 1 failed
==============================================================================
Tests :: Web shop acceptance tests                                    | FAIL |
1 test, 0 passed, 1 failed
==============================================================================
Output:  NONE
exit=0
No session is open.
…
```

<div class="rc-session-answer">

**Agent:** The debugger confirms it: **the shop returns `'Welcome back, alice!'`**, with a lowercase `a`. I paused the real test at `resources/shop.resource:18` and stepped over the `Greeting` call, which stopped on the comparison at line 19.

```
* breakpoint  ShopLibrary.Greeting  (resources/shop.resource:18)
(rdb) .next
* step  BuiltIn.Should Be Equal  (resources/shop.resource:19)
(rdb) .print ${greeting}
${greeting} = 'Welcome back, alice!'
(rdb) .print ${expected}
${expected} = 'Welcome back, Alice!'
(rdb) .whatis ${greeting}
${greeting}: str
(rdb) Current User
=> 'alice'
```

- **The mismatch:** the two strings differ only in the capital `A`. The value is a plain string, so there's no type mismatch involved.
- **Where the lowercase comes from:** `Current User` also returns `'alice'` in the paused test, so the greeting simply repeats the stored login name unchanged.

I stopped the session at that point, so `Should Be Equal` never ran and the test shows as failed because I aborted it. The run wrote no output files, so `results/` still holds the earlier run, and nothing in the repo changed.

Which fix is right still depends on what SHOP-101 specifies.

</div>

<div class="rc-session-prompt">

**You:** The test is right, Alice is the display name. Fix the shop.

</div>

```console
$ grep -n -i -E "welcome|alice|bob|display|greet" webshop/index.html; echo ---; grep -rn -E "alice|bob|Current User" tests resources; python - <<'E'
import re
p='libraries/ShopLibrary.py'
s=open(p).read()
s=s.replace('''USERS = {"alice": "secret", "bob": "secret"}
''','''USERS = {"alice": "secret", "bob": "secret"}
DISPLAY_NAMES = {"alice": "Alice", "bob": "Bob"}
''')
s=s.replace('''return f"Welcome back, {self._user}!"''','''return f"Welcome back, {DISPLAY_NAMES[self._user]}!"''')
open(p,'w').write(s)
E
git diff; robotcode analyze code; echo "analyze exit=$?"; robotcode robot -bl "Tests.Login.Login Works"; echo "login exit=$?"; robotcode robot; echo "all exit=$?"; robotcode results summary --failed; git status --short
12:    .product { display: flex; justify-content: space-between; padding: .6rem .8rem; margin-top: .5rem; background: #fff; border-radius: .5rem; }
---
tests/orders.robot:8:Test Setup       Open Shop As    alice
tests/cart.robot:8:Test Setup       Open Shop As    alice
tests/login.robot:15:    Open Shop As    alice
tests/login.robot:22:    Open Shop As    bob
tests/login.robot:30:    Run Keyword And Expect Error    Wrong password for alice    Open Shop As    alice    password=guess
resources/shop.resource:23:    ${user}=    Current User
diff --git a/libraries/ShopLibrary.py b/libraries/ShopLibrary.py
index f74a7f4..0c33fc0 100644
--- a/libraries/ShopLibrary.py
+++ b/libraries/ShopLibrary.py
@@ -4,6 +4,7 @@ from robot.api import logger
 from robot.api.deco import keyword, library
 
 USERS = {"alice": "secret", "bob": "secret"}
+DISPLAY_NAMES = {"alice": "Alice", "bob": "Bob"}
 PRICES = {"coffee": 4.50, "tea": 3.20, "beans": 9.90, "mug": 12.00}
 
 
@@ -36,7 +37,7 @@ class ShopLibrary:
     @keyword
     def greeting(self) -> str:
         """Returns the greeting the shop shows the user who is logged in."""
-        return f"Welcome back, {self._user}!"
+        return f"Welcome back, {DISPLAY_NAMES[self._user]}!"
 
     @keyword
     def current_user(self) -> str | None:
…
Log:     ~/webshop/results/log.html
Report:  ~/webshop/results/report.html
all exit=0
# Summary — results/output.xml

- _Status:_ ✅ **PASS**
- _Total:_ 13
- _Passed:_ 13
- _Failed:_ 0
- _Skipped:_ 0
- _Started:_ 2026-11-03 22:38:07
- _Ended:_ 2026-11-03 22:38:07
- _Elapsed:_ 44 ms
- _Messages:_ 2 FAIL

 M libraries/ShopLibrary.py
```

*…*

<div class="rc-session-answer">

**Agent:** I've fixed the shop, and `Login Works` now passes. A full run of the default local profile passes all 13 tests. The change isn't committed yet.

**The fix**
In `libraries/ShopLibrary.py`, the shop now keeps display names separately from login names, and the greeting uses the display name:

```diff
 USERS = {"alice": "secret", "bob": "secret"}
+DISPLAY_NAMES = {"alice": "Alice", "bob": "Bob"}
...
-        return f"Welcome back, {self._user}!"
+        return f"Welcome back, {DISPLAY_NAMES[self._user]}!"
```

Logging in still uses `alice`, and `Current User` still returns `alice`. "Bob" is my assumption, following the same pattern as "Alice".

**Things to check**
- **Greeting with nobody logged in:** `Greeting` now fails with `KeyError: None`, where it used to return `Welcome back, None!`. No test does this, and I think failing is better than a wrong greeting.
- **Earlier results replaced:** the new runs overwrote `results/`, so the failing run's `output.xml` and logs are gone. They weren't tracked by git, so they can't be restored, though re-running the old code would reproduce the failure.
- **Staging not covered:** I only ran this against the in-memory shop, not with the `ci` profile. The fix is in the test library, so if staging's real greeting is what failed, it still needs its own fix.

**A separate bug I didn't fix**
`robotcode analyze code` reports an error at `resources/orders.resource:31`:

```
KeywordNotFound: No keyword with name 'Submit Ordr' found.
```

It's a typo for `Submit Order` in the `Checkout` keyword. It doesn't show up in the runs because no test or resource calls `Checkout`, but any new test that does will fail. It was already there before my change, and I can fix it too if you like.

Do you want me to commit the shop fix?

</div>

</div>

</details>
<!-- /session -->

<!-- session: comparing-runs -->
<details class="rc-session-details">
<summary>Comparing runs <span>“Run all tests and tell me what changed compared with last night's run in <code>results/nightly</code>.”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Run all tests and tell me what changed compared with last night's run in `results/nightly`.

</div>

*Loaded the skill `robotcode:robotcode`*

*…*

```console
$ git ls-files results | head; git check-ignore results/output.xml; robotcode results summary -o results/output.xml; robotcode robot; echo "exit code: $?"
results/output.xml
# Summary — results/output.xml

…
==============================================================================
Tests :: Web shop acceptance tests                                    | PASS |
13 tests, 13 passed, 0 failed
==============================================================================
Output:  ~/webshop/results/output.xml
Log:     ~/webshop/results/log.html
Report:  ~/webshop/results/report.html
exit code: 0
```

```console
$ robotcode results diff results/nightly/output.xml results/output.xml; echo "diff exit: $?"; robotcode results summary -o results/nightly/output.xml; robotcode results summary --failed; robotcode results stats --by suite -o results/nightly/output.xml; robotcode results stats --by suite; git status --short
# Diff — results/nightly/output.xml → results/output.xml

## New passes (1)

- Tests.Login.Login Works (`tests/login.robot:11`) — ❌ **FAIL** → ✅ **PASS**
  > Welcome back, alice! != Welcome back, Alice!

_Summary:_ 1 new passes.

diff exit: 0
…
```

*…*

<div class="rc-session-answer">

**Agent:** All 13 tests pass now, and the only change from the nightly run is that `Tests.Login.Login Works` went from fail to pass. The nightly run had 12 passed and 1 failed.

| | Nightly | Now |
|---|---|---|
| **Passed** | 12 | 13 |
| **Failed** | 1 | 0 |
| **Skipped** | 0 | 0 |

No tests were added or removed, none newly fail, and all the other tests have the same status and tags.

**The fixed test:** the nightly run failed with `Welcome back, alice! != Welcome back, Alice!`. The greeting used the login name, but the test expects the capitalised name.

**Why it passes now:** the fix is your uncommitted change in `libraries/ShopLibrary.py`, which adds `DISPLAY_NAMES` and uses it in `greeting`. It's the only difference in the working tree, and the test itself didn't change. Until it's committed, tonight's nightly and CI will most likely fail the same way.

**How far the comparison goes:**
- **Profile:** I ran without a profile, so it used `http://localhost:8080`. The nightly's `Login Works` log shows the same URL, but CI runs with `-p ci` against staging, so this run doesn't confirm CI will pass.
- **Nightly date:** `results/nightly/output.xml` is stamped today at 22:37, under two minutes before this run at 22:38. If you expected a run from last night, check that this is the right file.
- **Overwritten results:** this run replaced the previous results directly in `results/`, which is ignored by git. That earlier run also had 13 of 13 passing, and `results/nightly` wasn't touched.

The details are in `results/log.html` and `results/report.html`.

</div>

</div>

</details>
<!-- /session -->
