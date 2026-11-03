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

### It looks at what a profile includes

`robotcode profiles list` shows the project's profiles with their descriptions, and `robotcode -p <profile> discover tests` the tests a profile would run, without running them. From the session *Smoke tests on staging*:

<!-- excerpt: smoke-tests-on-staging -->
```console
$ command -v robotcode; robotcode discover tests -i smoke; echo "--- ci profile"; robotcode -p ci discover tests -i smoke; echo "--- tags"; robotcode discover tags --tests; echo "--- robot.toml"; cat robot.toml
…
--- ci profile
# Tests

- **Tests.Cart.Add Item To Cart** (`tests/cart.robot:15`)
…
```

A profile is a global option of `robotcode`. It goes before the subcommand, as in `robotcode -p ci robot -i smoke`; after `robot`, Robot Framework would take it for an option of its own.

### It selects what you name

Tags with `-i` and `-e`, suites with `-s`, and one test, task or suite with `-bl` and its long name. The skill tells the agent to select one test by its long name and not by its `.robot` file: a single file becomes the top suite, and the `__init__.robot` files of the folders above it, with their suite setup and variables, don't run.

### It checks what the run reached

After a run, Robot Framework's exit code is the number of failed tests, and the agent reads the failures with `robotcode results`. In the session, it also looked at what the `ci` profile changes:

<!-- excerpt: smoke-tests-on-staging -->
> **The smoke tests ran with the staging profile, but they never reached the staging shop.** The result says nothing about staging. 3 of the 4 tests passed and 1 failed.

### It finds another browser in the profile

Asked whether the web tests that [*From a requirement*](/guides/ai-agents/working-with-the-agent/writing-a-test/) added can run in Firefox, the agent read the arguments of `New Browser` with `robotcode doc` and found that the `dev` profile already selects Firefox. It then ran the search suite with `robotcode -p dev robot -d "$OUT" -bl "Tests.Search"`, with its results in a temporary folder, so that `results/` stayed as it was. Asked whether that run really used Firefox, it searched the results of the run with `robotcode results show --search-regex`:

<!-- excerpt: another-browser -->
```console
…
=== browser option = firefox
- ✅ **PASS** Tests.Search.Search Field Has Its Label (`tests/search.robot:16`) _(22:32:41 · 1.23 s)_
- _Total:_ 1
=== browser option = chromium
=== browser option = webkit
…
```

More on profiles: [Profiles](/guides/robot-toml/profiles/).

## What to watch out for

- **Check what a profile changes.** A profile named after a system doesn't make the tests reach it. Ask the agent what a profile changes, or look yourself with `robotcode -p <profile> profiles show`.
- **A run replaces the results of the last one.** As in [step 2](/guides/ai-agents/working-with-the-agent/writing-a-test/), ask for another output directory if you still need them.
- **Point the agent to `robotcode results` when it reads `output.xml` itself.** An `output.xml` can be hundreds of megabytes, and `robotcode results` returns only the part asked for, which is why the skill tells the agent not to read the file. In the session *Another browser*, the agent kept to that. For the metadata of the top suite, which it didn't find there, it used Robot Framework's Python API, as the skill allows when `robotcode results` lacks a part.

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
$ command -v robotcode; robotcode discover tests -i smoke; echo "--- ci profile"; robotcode -p ci discover tests -i smoke; echo "--- tags"; robotcode discover tags --tests; echo "--- robot.toml"; cat robot.toml
~/webshop/.venv/bin/robotcode
# Tests

- **Tests.Cart.Add Item To Cart** (`tests/cart.robot:15`)
- **Tests.Login.Login Works** (`tests/login.robot:11`)
- **Tests.Login.Logout Works** (`tests/login.robot:18`)
- **Tests.Orders.Order Coffee** (`tests/orders.robot:14`)

## Statistics

- _Suites:_ 4
- _Suites with tests:_ 3
- _Tests:_ 4

--- ci profile
# Tests

- **Tests.Cart.Add Item To Cart** (`tests/cart.robot:15`)
- **Tests.Login.Login Works** (`tests/login.robot:11`)
- **Tests.Login.Logout Works** (`tests/login.robot:18`)
- **Tests.Orders.Order Coffee** (`tests/orders.robot:14`)

## Statistics

- _Suites:_ 4
- _Suites with tests:_ 3
- _Tests:_ 4
…
```

<div class="rc-session-answer">

**Agent:** Your smoke test has four tests, all tagged `smoke`:

| Area | Test | Location |
| --- | --- | --- |
| Cart | Add Item To Cart | `tests/cart.robot:15` |
| Login | Login Works | `tests/login.robot:11` |
| Login | Logout Works | `tests/login.robot:18` |
| Orders | Order Coffee | `tests/orders.robot:14` |

The list is the same with the default configuration and the `ci` profile. The search suite has no smoke tests.

To run just these, use `robotcode robot -i smoke`.

</div>

<div class="rc-session-prompt">

**You:** Run them against staging.

</div>

```console
$ robotcode -p ci robot -i smoke; echo "exit code: $?"
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
==============================================================================
Tests :: Web shop acceptance tests                                    | FAIL |
4 tests, 3 passed, 1 failed
==============================================================================
Output:  ~/webshop/results/output.xml
Log:     ~/webshop/results/log.html
Report:  ~/webshop/results/report.html
exit code: 1
```

<div class="rc-session-answer">

**Agent:** The run has one failure. Before I report it, I'm checking the recorded error, and also whether these tests actually reach staging, since `AGENTS.md` says the suites run the shop in memory.

</div>

*…*

<div class="rc-session-answer">

**Agent:** **The smoke tests ran with the staging profile, but they never reached the staging shop.** The result says nothing about staging. 3 of the 4 tests passed and 1 failed.

| Test | Result |
| --- | --- |
| Add Item To Cart | Passed |
| Login Works | **Failed** |
| Logout Works | Passed |
| Order Coffee | Passed |

**Why staging wasn't tested**
The `ci` profile only changes `BASE_URL`, and nothing connects to that address:
- **Where `BASE_URL` is used:** `resources/shop.resource:13` writes it to the log, and `tests/__init__.robot:4` records it as metadata.
- **What the tests actually talk to:** every step goes through `libraries/ShopLibrary.py`, which runs the shop in memory.
- **Why the log is misleading:** it says `Opened https://staging.shop.example as alice`, but no connection is made. The whole run took about 50 ms.

The CI job, `robotcode -p ci robot`, uses the same profile, so it isn't testing staging either. A real staging check would need tests that use the Browser library or some other connection to the live shop.

**The failure**
`Login Works` (`tests/login.robot:11`) expects a capitalised name, but the shop greets the user with the name exactly as it was typed at login:

```
Welcome back, alice! != Welcome back, Alice!
```

The greeting comes from `f"Welcome back, {self._user}!"` at `libraries/ShopLibrary.py:39`, and the user is stored as `alice`. Because this all happens in memory, the mismatch is in the local code and isn't a staging bug.

I can't tell whether the test or the shop is wrong. The test's requirement, SHOP-101, has no file in `requirements/`; the only file there is `SHOP-110.md`. Someone who knows the intended greeting would have to decide. Changing `ShopLibrary.py` would only make the in-memory copy pass, and wouldn't show how the real shop behaves.

I haven't changed anything. The full log is in `results/log.html`, and the report is in `results/report.html`.

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
$ command -v robotcode; robotcode doc keyword Browser "New Browser" 2>&1 | head -80; echo ---; robotcode doc lib Browser 2>&1 | grep -n -i -E 'firefox' | head -20; echo ---; robotcode profiles list; robotcode -p dev profiles show; echo ---; cat robot.toml; grep -n -i -E 'browser|playwright' pyproject.toml; grep -rn -i -E 'firefox|chromium|webkit|New Browser|BROWSER' resources tests .github libraries | head -30; ls ~/.cache/ms-playwright 2>/dev/null; pip list 2>/dev/null | grep -i -E 'robotframework-browser'; uv pip list 2>/dev/null | grep -i browser
~/webshop/.venv/bin/robotcode
### Keyword *New Browser*

#### Arguments: 

| | | | | |
|:--|:--|:--|:--|:--|
| `browser`| : `SupportedBrowsers` | = | `chromium` | Opens the specified [browser](#type-supportedbrowsers). Defaults to chromium. |
| `headless`| : `bool` | = | `${True}` | Set to False if you want a GUI. Defaults to True. |
…
[variables]
BASE_URL = "http://localhost:8080"
BROWSER = "firefox"

---
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

[profiles.ci.extend-variables]
BASE_URL = "https://staging.shop.example"


7:dependencies = ["robotframework>=7.5", "robotcode[all]>=2.7.0", "robotframework-browser>=20.6.0"]
resources/shop.resource:4:Library          Browser
resources/shop.resource:34:    [Documentation]    Opens the shop's web page at ${BASE_URL} in ${BROWSER}.
resources/shop.resource:35:    New Browser    ${BROWSER}
tests/__init__.robot:5:Metadata         Browser    ${BROWSER}
.github/workflows/tests.yml:11:      - run: pip install robotframework robotcode[runner] robotframework-browser
.github/workflows/tests.yml:12:      - run: rfbrowser init --with-deps chromium
b
robotframework-browser          21.0.0
```

<div class="rc-session-answer">

**Agent:** The library supports Firefox, and `dev` selects it. I'll check whether Firefox is installed here and actually starts.

</div>

```console
$ ls -la ~/.cache/ms-playwright 2>&1 | head; find .venv -type d -iname 'firefox*' 2>/dev/null | head; echo "--- env"; env | grep -i playwright; echo "--- session"; ID=$(robotcode -p dev session start repl 2>&1 | tail -1); echo "id=$ID"; robotcode session send "$ID" 'Import Library    Browser'; echo "rc=$?"; robotcode session send "$ID" 'New Browser    firefox    headless=True'; echo "rc=$?"; robotcode session send "$ID" 'Get Browser Catalog'; echo "rc=$?"; robotcode session send "$ID" 'Close Browser    ALL'; robotcode session stop "$ID"; echo "--- usage"; sed -n 30,45p resources/shop.resource; grep -rn -E 'Open Shop|Open .*Page|Browser' tests | head; git diff -- .github/workflows/tests.yml resources/shop.resource tests/search.robot | head -80
…
.venv/lib/python3.13/site-packages/Browser/wrapper/node_modules/playwright-core/.local-browsers/firefox-1555
.venv/lib/python3.13/site-packages/Browser/wrapper/node_modules/playwright-core/.local-browsers/firefox-1555/firefox
--- env
--- session
id=Started session repl-ade5c4b7.
[ ERROR ] No session 'Started session repl-ade5c4b7.' is open.
rc=252
[ ERROR ] No session 'Started session repl-ade5c4b7.' is open.
rc=252
[ ERROR ] No session 'Started session repl-ade5c4b7.' is open.
rc=252
[ ERROR ] No session 'Started session repl-ade5c4b7.' is open.
[ ERROR ] No session 'Started session repl-ade5c4b7.' is open.
--- usage
    ${found}=    Search Products    ${text}
    Lists Should Be Equal    ${found}    ${expected}
…
```

```console
$ ID=repl-ade5c4b7; robotcode session send $ID 'Import Library    Browser'; echo "rc=$?"; robotcode session send $ID 'New Browser    firefox    headless=True'; echo "rc=$?"; robotcode session send $ID 'New Page    about:blank'; echo "rc=$?"; robotcode session send $ID 'Evaluate JavaScript    ${None}    () => navigator.userAgent'; echo "rc=$?"; robotcode session send $ID 'Close Browser    ALL'; echo "rc=$?"; robotcode session stop $ID; echo "stop rc=$?"; echo "--- shop reachable?"; curl -s -o /dev/null -m 3 -w '%{http_code}\n' http://localhost:8080; echo "curl rc=$?"; git status --short
rc=0
[ INFO ] {"browser": "firefox", "headless": true, "chromiumSandbox": false, "devtools": false, "handleSIGHUP": true, "handleSIGINT": true, "handleSIGTERM": true, "slowMo": 0.0, "timeout": 30000.0, "tracesDir": "~/webshop/results/browser/traces/temp/e71684df-fc7d-41ab-b84a-ee69fca407e3"}
[ INFO ] Starting Browser process ~/webshop/.venv/lib/python3.13/site-packages/Browser/wrapper/index.js using at 127.0.0.1:39219
[ INFO ] Successfully created browser with options: {"browser":"firefox","headless":true,"chromiumSandbox":false,"devtools":false,"handleSIGHUP":true,"handleSIGINT":true,"handleSIGTERM":true,"slowMo":0,"timeout":30000,"tracesDir":"~/webshop/results/browser/traces/temp/e71684df-fc7d-41ab-b84a-ee69fca407e3"}
=> 'browser=343e6cac-351e-4f4e-868a-0185f4c5cbbc'
rc=0
[ INFO ] Successfully initialized new page object and opened url: about:blank
[ INFO ] No context was open. New context was automatically opened when this page is created.
=> {'page_id': 'page=f034942b-9c98-4c6b-a4eb-8d36646e6166', 'video_path': ''}
rc=0
[ INFO ] JavaScript executed successfully.
=> 'Mozilla/5.0 (X11; Linux x86_64; rv:157.0) Gecko/20100101 Firefox/157.0'
rc=0
[ INFO ] Closed all browsers
rc=0
stop rc=0
--- shop reachable?
200
curl rc=0
 M .github/workflows/tests.yml
 M resources/shop.resource
 M tests/search.robot
```

<div class="rc-session-answer">

**Agent:** Firefox starts, and the shop is responding on `localhost:8080`, so I can run the real web tests in it. The results go to a temp folder so your `results/` stays as it is.

</div>

```console
$ OUT=$(mktemp -d); robotcode -p dev robot -d "$OUT" -bl "Tests.Search" 2>&1 | tail -40; echo "rc=${PIPESTATUS[0]}"; echo "OUT=$OUT"; robotcode results -o "$OUT/output.xml" summary --failed 2>&1 | head -20; git status --short
…
Tests.Search :: Finding products by their name.                       | PASS |
8 tests, 8 passed, 0 failed
==============================================================================
Tests :: Web shop acceptance tests                                    | PASS |
8 tests, 8 passed, 0 failed
==============================================================================
Output:  /tmp/tmp.Ya9UZwoN4h/output.xml
Log:     /tmp/tmp.Ya9UZwoN4h/log.html
Report:  /tmp/tmp.Ya9UZwoN4h/report.html
rc=0
OUT=/tmp/tmp.Ya9UZwoN4h
Usage: robotcode results [OPTIONS] COMMAND [ARGS]...
Try 'robotcode results --help' for help.

[ ERROR ] No such option '-o'.
 M .github/workflows/tests.yml
 M resources/shop.resource
 M tests/search.robot
```

<div class="rc-session-answer">

**Agent:** **Yes, and it already works here.** I ran the `Tests.Search` suite with the `dev` profile, which runs in Firefox, against the shop on `localhost:8080`: **all 8 tests passed**. Four of those are the web tests that open the page in a browser; the other four go through `ShopLibrary` and don't use one.

- **Library support:** Browser supports `chromium`, `firefox` and `webkit`. You choose one with the first argument of `New Browser`, and `Open Shop Page` passes `${BROWSER}` there (`resources/shop.resource:35`).
- **Firefox on this machine:** `.venv` has Playwright's Firefox, and it started as Firefox 157 in a separate headless check. The test run didn't set `headless` either, so it was headless too (the library's default).

**To run them locally:**
```bash
robotcode -p dev robot -bl "Tests.Search"
```

I sent my run's output to a temp folder, so `results/` wasn't touched. The log is at `/tmp/tmp.Ya9UZwoN4h/log.html`.

**CI still uses Chromium:** the `ci` profile doesn't set `BROWSER`, so it stays on the `chromium` default from `robot.toml`. The uncommitted change in `.github/workflows/tests.yml` also installs only Chromium (`rfbrowser init --with-deps chromium`). So nothing has tested Firefox against staging yet.

To use Firefox in CI, you would need two changes:
- Add `BROWSER = "firefox"` under `[profiles.ci.extend-variables]` in `robot.toml`.
- Install it in the workflow with `rfbrowser init --with-deps firefox`, or list both browsers if you want to test in both.

Do you want me to make those changes?

</div>

<div class="rc-session-prompt">

**You:** Did that run really use Firefox? Show me in its results.

</div>

*…*

```console
$ O=/tmp/tmp.Ya9UZwoN4h/output.xml; robotcode results summary -o $O; echo "=== tests mentioning firefox"; robotcode results show -o $O --search firefox; echo "=== tests mentioning chromium"; robotcode results show -o $O --search chromium; echo "=== one web test"; robotcode results log -o $O --suite-info -bl "Tests.Search.Search Field Has Its Label" | cut -c1-400 | head -40
# Summary — /tmp/tmp.Ya9UZwoN4h/output.xml

- _Status:_ ✅ **PASS**
- _Total:_ 8
- _Passed:_ 8
- _Failed:_ 0
- _Skipped:_ 0
- _Started:_ 2026-11-03 22:32:41
- _Ended:_ 2026-11-03 22:32:44
- _Elapsed:_ 2.84 s

=== tests mentioning firefox
# Show — /tmp/tmp.Ya9UZwoN4h/output.xml

- ✅ **PASS** Tests.Search.Find Coffee (`tests/search.robot:11`) _(22:32:41 · 2 ms)_
- ✅ **PASS** Tests.Search.Find Tea (`tests/search.robot:12`) _(22:32:41 · 4 ms)_
- ✅ **PASS** Tests.Search.Find Several (`tests/search.robot:13`) _(22:32:41 · 3 ms)_
- ✅ **PASS** Tests.Search.Find Nothing (`tests/search.robot:14`) _(22:32:41 · 3 ms)_
- ✅ **PASS** Tests.Search.Search Field Has Its Label (`tests/search.robot:16`) _(22:32:41 · 1.23 s)_
- ✅ **PASS** Tests.Search.Search Lists Matching Products With Prices (`tests/search.robot:23`) _(22:32:42 · 483 ms)_
- ✅ **PASS** Tests.Search.Search Ignores Upper And Lower Case (`tests/search.robot:33`) _(22:32:43 · 377 ms)_
- ✅ **PASS** Tests.Search.Search Without A Match Shows A Message (`tests/search.robot:41`) _(22:32:43 · 312 ms)_
…
    - `[INFO] {"browser": "firefox", "headless": true, "chromiumSandbox": false, "devtools": false, "handleSIGHUP": true, "handleSIGINT": true, "handleSIGTERM": true, "slowMo": 0.0, "timeout": 30000.0, "tracesDir": "/tmp/tmp.Ya9UZwoN4h/browser/traces/temp/a3463713-d722-4c5b-b0cb-42676cfa9db1"}`
    - `[INFO] Successfully created browser with options: {"browser":"firefox","headless":true,"chromiumSandbox":false,"devtools":false,"handleSIGHUP":true,"handleSIGINT":true,"handleSIGTERM":true,"slowMo":0,"timeout":30000,"tracesDir":"/tmp/tmp.Ya9UZwoN4h/browser/traces/temp/a3463713-d722-4c5b-b0cb-42676cfa9db1"}`
  - **Browser.New Page** `${BASE_URL}` ✅ **PASS** _(22:32:41 · 709 ms)_
    - `[INFO] Successfully initialized new page object and opened url: http://localhost:8080`
    - `[INFO] No context was open. New context was automatically opened when this page is created.`
- **shop.Search Field Should Be Labelled** `Search products` ✅ **PASS** _(22:32:42 · 253 ms)_
  - `${field}` = **Browser.Get Element By Role** `searchbox` `name=${label}` `exact=True` ✅ **PASS** _(22:32:42 · 152 ms)_
    - `[INFO] Locator found successfully.`
    - `[INFO] ${field} = internal:role=searchbox[name="Search products"s]`
  - **Browser.Get Element States** `${field}` `contains` `visible` ✅ **PASS** _(22:32:42 · 100 ms)_
    - `[INFO] States are: ['attached', 'visible', 'enabled', 'editable', 'defocused']`
- `[INFO] Switching context to context=4c8afa59-f351-4cfb-a0d6-1830256c9ef8 in CURRENT`
- `[INFO] Successfully changed active context: context=4c8afa59-f351-4cfb-a0d6-1830256c9ef8`
- `[INFO] Successfully closed Context`

- _Started:_ 2026-11-03 22:32:41
- _Ended:_ 2026-11-03 22:32:44
- _Elapsed:_ 2.84 s

_Filters: by-longname=Tests.Search.Search Field Has Its Label_
```

<div class="rc-session-answer">

**Agent:** The `chromium` hit needs explaining, and so does `firefox` matching all 8 tests, including the ones with no browser. I'll narrow both searches to the recorded `browser` option.

</div>

```console
$ O=/tmp/tmp.Ya9UZwoN4h/output.xml; for b in firefox chromium webkit; do echo "=== browser option = $b"; robotcode results show -o $O --search-regex "\"browser\": ?\"$b\"" | grep -E 'PASS\*\*|FAIL\*\*|_Total'; done; echo "=== chromium in any form other than chromiumSandbox"; robotcode results show -o $O --search-regex '(?i)chromium(?!Sandbox)' | grep -E 'PASS\*\*|_Total'; echo "=== New Browser in each web test"; for t in "Search Lists Matching Products With Prices" "Search Ignores Upper And Lower Case" "Search Without A Match Shows A Message"; do echo "-- $t"; robotcode results log -o $O -bl "Tests.Search.$t" | grep -A2 'Browser.New Browser' | cut -c1-110; done; echo "=== top suite metadata"; robotcode results log -o $O --suite-info -bl "Tests.Search.Find Coffee" | head -14 | cut -c1-200
=== browser option = firefox
- ✅ **PASS** Tests.Search.Search Field Has Its Label (`tests/search.robot:16`) _(22:32:41 · 1.23 s)_
- _Total:_ 1
=== browser option = chromium
=== browser option = webkit
=== chromium in any form other than chromiumSandbox
=== New Browser in each web test
…
```

```console
$ python -c "
from robot.api import ExecutionResult
r = ExecutionResult('/tmp/tmp.Ya9UZwoN4h/output.xml')
print(r.suite.full_name, dict(r.suite.metadata))"
Tests {'Application': 'Demo web shop', 'Browser': 'firefox', 'Shop URL': 'http://localhost:8080'}
```

<div class="rc-session-answer">

**Agent:** **Yes, that run used Firefox.** The run started one browser, in the first web test, and the log records it as Firefox:

```
Test: Tests.Search.Search Field Has Its Label
  [SETUP] shop.Open Shop Page
    Browser.New Browser  ${BROWSER}  PASS (270 ms)
      [INFO] Successfully created browser with options: {"browser":"firefox","headless":true,"chromiumSandbox":false,...}
```

| Check in the results | Result |
|---|---|
| Tests where a browser was started with `"browser": "firefox"` | 1, the test above |
| Same search for `chromium` and `webkit` | 0 |
| Top suite metadata | `Browser: firefox`, `Shop URL: http://localhost:8080` |

**The other three web tests:** they don't start their own browser. `New Browser` takes 2 ms there and logs `Switching browser to browser=d13e3230-…`, because it reuses an open browser with the same arguments. All three reuse the same one, and it's the only browser started in the run.

**Two search hits that look odd but aren't a problem:**
- **`chromium` matches one test:** this is only the option name `chromiumSandbox`, which is listed even for Firefox. With that name excluded, there are no matches.
- **`firefox` matches all 8 tests:** the likely cause is the top suite's `Browser` metadata, which applies to every test. It doesn't mean all 8 opened a browser, since the first four never do.

**What the results can't show:** they record the browser Playwright was told to start, not what the running browser reported about itself. The `Firefox/157.0` version I gave earlier came from my separate check, not from this run. To have each run prove it, `Open Shop Page` could log `navigator.userAgent`.

To see it yourself, run this or open `/tmp/tmp.Ya9UZwoN4h/log.html`:
```bash
robotcode results log -o /tmp/tmp.Ya9UZwoN4h/output.xml -bl "Tests.Search.Search Field Has Its Label"
```

</div>

</div>

</details>
<!-- /session -->
