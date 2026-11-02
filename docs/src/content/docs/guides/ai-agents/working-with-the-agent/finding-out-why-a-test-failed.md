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

### Test: Tests.Login.Login Works (`tests/login.robot:11`) ❌ **FAIL** _(19:15:43 · 1 ms)_
…
```

`robotcode results` reads the `output.xml` and returns only the part asked for. Without `-o` (`--output`), it takes the output file of the project's configuration.

### It compares two runs

`robotcode results diff` compares a baseline run with a newer one: new failures, which passed before, and new passes, which failed before. From the session *Comparing runs*, after the fix:

<!-- excerpt: comparing-runs -->
```console
$ robotcode results diff results/nightly/output.xml results/output.xml; echo ---; robotcode results summary -o results/nightly/output.xml --failed
# Diff — results/nightly/output.xml → results/output.xml

## New passes (1)

- Tests.Login.Login Works (`tests/login.robot:11`) — ❌ **FAIL** → ✅ **PASS**
…
```

### It goes into the debugger when the log isn't enough

Asked to show in the debugger what the shop returns, the agent ran only that test with `robotcode robot-debug`, stopped at the failure and called the shop's keywords in the paused test. It wrote the results of the debug run to a folder of its own, so the recorded run stayed as it was. Which side to change, it left to you:

<!-- excerpt: a-failing-test -->
> This matches the recorded run, so the failure reproduces every time. Whether the shop or the test should change is still your call, as before.

After your answer, it fixed the library and ran all tests again. [Step 5](/guides/ai-agents/working-with-the-agent/debugging-step-by-step/) shows the debugger in detail.

More on the commands: [Analyzing Results](/guides/cli/analyzing-results/).

## What to watch out for

- **Name the run if it isn't the last one.** Without a path, the agent reads the output of the project's configuration, and a new run replaces it.
- **Keep the run you investigate.** A new run, also one in the debugger, writes to the same output directory unless the agent writes elsewhere. Ask for that, as the agent did by itself in *A failing test*.
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
$ robotcode results summary --failed; robotcode results log -t "Login Works"; ls -la; find . -name "output*.xml" -not -path "./.venv/*"
# Summary — results/output.xml

- _Status:_ ❌ **FAIL**
- _Total:_ 13
- _Passed:_ 12
- _Failed:_ 1
- _Skipped:_ 0
- _Started:_ 2026-10-29 19:15:43
- _Ended:_ 2026-10-29 19:15:43
- _Elapsed:_ 49 ms
- _Messages:_ 3 FAIL

## Failures (1)

- ❌ **FAIL** Tests.Login.Login Works (`tests/login.robot:11`)
  > Welcome back, alice! != Welcome back, Alice!

# Log

### Test: Tests.Login.Login Works (`tests/login.robot:11`) ❌ **FAIL** _(19:15:43 · 1 ms)_

_Metadata:_ Requirement: SHOP-101

> Welcome back, alice! != Welcome back, Alice!

- **shop.Open Shop As** `alice` ✅ **PASS** _(19:15:43 · 0 ms)_
  - **ShopLibrary.Log In** `${user}` `${password}` ✅ **PASS** _(19:15:43 · 0 ms)_
  - **BuiltIn.Log** `Opened ${BASE_URL} as ${user}` ✅ **PASS** _(19:15:43 · 0 ms)_
    - `[INFO] Opened http://localhost:8080 as alice`
- **shop.Welcome Message Should Be** `Welcome back, Alice!` ❌ **FAIL** _(19:15:43 · 0 ms)_
  > Welcome back, alice! != Welcome back, Alice!
  - `${greeting}` = **ShopLibrary.Greeting** ✅ **PASS** _(19:15:43 · 0 ms)_
    - `[INFO] ${greeting} = Welcome back, alice!`
  - **BuiltIn.Should Be Equal** `${greeting}` `${expected}` ❌ **FAIL** _(19:15:43 · 0 ms)_
    > Welcome back, alice! != Welcome back, Alice!
    - `[FAIL] Welcome back, alice! != Welcome back, Alice!`

- _Elapsed:_ 1 ms

_Filters: test=Login Works_

…
```

*…*

<div class="rc-session-answer">

**Agent:** `Login Works` fails on a capitalisation mismatch in the greeting. The test expects `Welcome back, Alice!` but the shop returns `Welcome back, alice!`.

**Which run this is:** the only result on disk is `results/output.xml`, timestamped today (2026-10-29) at 19:15, not last night. That run had 13 tests: 12 passed and only `Tests.Login.Login Works` failed. If last night's run was in CI, its output isn't here. Download that artifact and I can check whether it failed the same way.

**What happened** (`tests/login.robot:11`):
1. `Open Shop As    alice` passed and logged in as `alice`.
2. `Welcome Message Should Be    Welcome back, Alice!` called `Greeting`, which returned `Welcome back, alice!`. `Should Be Equal` then failed with `Welcome back, alice! != Welcome back, Alice!`.

**Cause:** `greeting` in `libraries/ShopLibrary.py` builds the text from the login name exactly as it was typed:
```python
return f"Welcome back, {self._user}!"
```

The user is `alice` in lowercase (`USERS = {"alice": ..., "bob": ...}`), so the greeting is lowercase too.

**Is it the test or the shop?** I can't tell from the repo. The test is linked to requirement `SHOP-101`, but `requirements/` only contains `SHOP-110.md`, so there's nothing to say how the name should be shown. Two possible fixes:
- If the shop should capitalise names, change the library to use `self._user.capitalize()`, or give each user a display name.
- If lowercase is correct, change the expected text in the test to `Welcome back, alice!`.

I haven't changed anything. Tell me which behaviour is intended and I'll make the fix and re-run the test.

</div>

<div class="rc-session-prompt">

**You:** Show me in the debugger what the shop returns there.

</div>

*…*

<div class="rc-session-answer">

**Agent:** Before starting, I'll check where a run writes its output. Starting the debugger would otherwise overwrite `results/output.xml`, which holds the only recorded run.

</div>

*…*

```console
$ D=/tmp/dbg; rm -rf $D; mkdir -p $D; mkfifo $D/in
nohup sleep 600 > $D/in 2>/dev/null &
nohup robotcode robot-debug --outputdir $D/out -bl "Tests.Login.Login Works" < $D/in > $D/log 2>&1 &
for i in $(seq 1 30); do grep -q "(rdb)" $D/log && break; sleep 1; done; cat $D/log
==============================================================================
Tests :: Web shop acceptance tests                                            
==============================================================================
Tests.Login :: Logging in to the shop and out again.                          
==============================================================================
Login Works :: A user who logs in is greeted by name.                 
* exception  BuiltIn.Should Be Equal  (resources/shop.resource:19)  — Keyword failed: Welcome back, alice! != Welcome back, Alice!
(rdb)
```

```console
$ D=/tmp/dbg
for c in '.where' '.list' '.print ${greeting}' '.print ${expected}' 'Greeting' 'Current User'; do echo "$c" > $D/in; sleep 1; done; cat $D/log | sed -n '/(rdb)/,$p'
(rdb) > #0  BuiltIn.Should Be Equal         resources/shop.resource:19
  #1  shop.Welcome Message Should Be  tests/login.robot:16
  #2  Login Works                     tests/login.robot:11
  #3  Login                           tests/login.robot
  #4  Tests                           tests
(rdb)      14  
     15  Welcome Message Should Be
     16      [Documentation]    Checks the greeting the shop shows the user who is logged in.
     17      [Arguments]    ${expected}
     18      ${greeting}=    Greeting
->   19      Should Be Equal    ${greeting}    ${expected}
     20  
     21  User Should Be Logged Out
     22      [Documentation]    Checks that nobody is logged in.
     23      ${user}=    Current User
     24      Should Be Equal    ${user}    ${None}
(rdb) ${greeting} = 'Welcome back, alice!'
(rdb) ${expected} = 'Welcome back, Alice!'
(rdb) => 'Welcome back, alice!'
(rdb) => 'alice'
(rdb)
```

<div class="rc-session-answer">

**Agent:** Now I'll end the session so the run finishes, and clean up.

</div>

```console
$ D=/tmp/dbg
echo '.detach' > $D/in; sleep 3; tail -8 $D/log; pkill -f "sleep 600" ; pgrep -fa robot-debug || echo "debugger exited"; ls -la results/output.xml
Exit code 144
1 test, 0 passed, 1 failed
==============================================================================
Tests :: Web shop acceptance tests                                    | FAIL |
1 test, 0 passed, 1 failed
==============================================================================
Output:  /tmp/dbg/out/output.xml
Log:     /tmp/dbg/out/log.html
Report:  /tmp/dbg/out/report.html
```

*…*

<div class="rc-session-answer">

**Agent:** In a live run the shop returns `'Welcome back, alice!'`, with a lowercase "a". The test expects `'Welcome back, Alice!'`.

I ran only `Tests.Login.Login Works` under `robotcode robot-debug`. It stopped at the failing `Should Be Equal` in `resources/shop.resource:19`:

```
* exception  BuiltIn.Should Be Equal  (resources/shop.resource:19)  — Keyword failed: Welcome back, alice! != Welcome back, Alice!

(rdb) .where
> #0  BuiltIn.Should Be Equal         resources/shop.resource:19
  #1  shop.Welcome Message Should Be  tests/login.robot:16
  #2  Login Works                     tests/login.robot:11

(rdb) .list
     18      ${greeting}=    Greeting
->   19      Should Be Equal    ${greeting}    ${expected}

(rdb) .print ${greeting}
${greeting} = 'Welcome back, alice!'
(rdb) .print ${expected}
${expected} = 'Welcome back, Alice!'
(rdb) Greeting
=> 'Welcome back, alice!'
(rdb) Current User
=> 'alice'
```

At the prompt I also called the shop's keywords directly in the paused test. `Greeting` gave the same text again, and `Current User` returned `'alice'`. So the shop puts the login name into the greeting exactly as it's stored, lowercase.

This matches the recorded run, so the failure reproduces every time. Whether the shop or the test should change is still your call, as before.

I let the run finish without further stops. Its output went to a scratch directory, so `results/output.xml` from the earlier run is unchanged.

</div>

<div class="rc-session-prompt">

**You:** The test is right, Alice is the display name. Fix the shop.

</div>

*…*

```console
$ python - <<'EOF'
p='libraries/ShopLibrary.py'
s=open(p).read()
s=s.replace('USERS = {"alice": "secret", "bob": "secret"}\n','USERS = {"alice": "secret", "bob": "secret"}\nDISPLAY_NAMES = {"alice": "Alice", "bob": "Bob"}\n')
s=s.replace('        return f"Welcome back, {self._user}!"','        return f"Welcome back, {DISPLAY_NAMES[self._user]}!"')
s=s.replace('"""Returns the greeting the shop shows the user who is logged in."""','"""Returns the greeting the shop shows the user who is logged in, with their display name."""')
open(p,'w').write(s)
EOF
grep -n "DISPLAY_NAMES\|display name" libraries/ShopLibrary.py
7:DISPLAY_NAMES = {"alice": "Alice", "bob": "Bob"}
39:        """Returns the greeting the shop shows the user who is logged in, with their display name."""
40:        return f"Welcome back, {DISPLAY_NAMES[self._user]}!"
```

<div class="rc-session-answer">

**Agent:** Now I'll re-run the full suite to confirm the fix (this writes a new `results/`, as AGENTS.md specifies).

</div>

```console
$ robotcode robot 2>&1 | tail -6; robotcode results summary --failed | head -12
Tests :: Web shop acceptance tests                                    | PASS |
13 tests, 13 passed, 0 failed
==============================================================================
Output:  ~/webshop/results/output.xml
Log:     ~/webshop/results/log.html
Report:  ~/webshop/results/report.html
# Summary — results/output.xml

…
```

<div class="rc-session-answer">

**Agent:** I fixed the shop, and `Login Works` now passes. The full run passed all 13 tests.

The change is in `libraries/ShopLibrary.py`:
- I added a display name for each test user, next to `USERS`: `DISPLAY_NAMES = {"alice": "Alice", "bob": "Bob"}`.
- `Greeting` now uses that display name instead of the login name, so the shop says `Welcome back, Alice!`. I also updated its docstring to say so.

Login itself still uses the lowercase names `alice` and `bob`, so no tests or resources needed changing.

Running the suite again replaced the result files in `results/`, so the old failed run is no longer there.

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
$ robotcode robot 2>&1 | tail -30; echo EXIT=$?
Tests.Orders :: Placing orders.                                               
==============================================================================
Order Coffee :: An order for a product in stock is placed.            | PASS |
------------------------------------------------------------------------------
…
==============================================================================
Tests :: Web shop acceptance tests                                    | PASS |
13 tests, 13 passed, 0 failed
==============================================================================
Output:  ~/webshop/results/output.xml
Log:     ~/webshop/results/log.html
Report:  ~/webshop/results/report.html
EXIT=0
```

```console
$ robotcode results diff results/nightly/output.xml results/output.xml; echo ---; robotcode results summary -o results/nightly/output.xml --failed
# Diff — results/nightly/output.xml → results/output.xml

## New passes (1)

- Tests.Login.Login Works (`tests/login.robot:11`) — ❌ **FAIL** → ✅ **PASS**
  > Welcome back, alice! != Welcome back, Alice!

_Summary:_ 1 new passes.

---
# Summary — results/nightly/output.xml

- _Status:_ ❌ **FAIL**
- _Total:_ 13
- _Passed:_ 12
- _Failed:_ 1
- _Skipped:_ 0
- _Started:_ 2026-10-29 19:15:43
- _Ended:_ 2026-10-29 19:15:43
- _Elapsed:_ 49 ms
- _Messages:_ 3 FAIL

## Failures (1)

- ❌ **FAIL** Tests.Login.Login Works (`tests/login.robot:11`)
  > Welcome back, alice! != Welcome back, Alice!
```

*…*

<div class="rc-session-answer">

**Agent:** I ran all 13 tests with the default config, then compared the results with `results/nightly/output.xml`. Everything passed this time: 13 passed, 0 failed. Last night's run had 13 passed except one failure.

**What changed since the nightly run:**

- **`Tests.Login.Login Works` (`tests/login.robot:11`) went from failing to passing.** Last night it failed with `Welcome back, alice! != Welcome back, Alice!`. In other words, the shop greeted the user by their lowercase login name instead of their display name.
- No test failed that had passed before, and no tests were added or removed. The other 12 tests passed in both runs.

The fix is probably in `libraries/ShopLibrary.py`. The welcome message is now built from `DISPLAY_NAMES` (line 40), and the file was last modified after the nightly run's results. There's no git history here, so I can't confirm exactly what was changed.

One caveat: I don't know which profile the nightly run used. The CI uses `-p ci`. That shouldn't matter for this comparison, because the suites run the shop in memory through `ShopLibrary`.

This run overwrote the previous results in `results/`: `output.xml`, `log.html` and `report.html`. The nightly files are unchanged.

</div>

</div>

</details>
<!-- /session -->
