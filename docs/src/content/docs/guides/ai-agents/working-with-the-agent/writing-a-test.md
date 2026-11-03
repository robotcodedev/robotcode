---
title: Writing a Test from a Requirement
description: "Step 2 of the tutorial: write a test with the agent, from learning the library in its installed version and trying keywords in the REPL to checking and running the test; a task is written the same way."
sidebar:
  label: 2. Writing a Test from a Requirement
  order: 150.42
---

Now that you know the project, write a test with the agent. It learns the library you want to use, tries keywords where it is unsure, writes the test, checks it and runs it. A task, the RPA counterpart of a test, is written the same way.

## What you learn

- how the agent learns a library in the version installed in your project;
- when to have it try keywords in the REPL first, and how to steer the REPL prompt by prompt;
- how the agent checks a new test with `robotcode analyze code` before it runs it;
- what is different for a task.

## How to ask the agent

- *"I want to test `<feature>` with `<library>`, but I've never used it. How do I `<…>`?"*
- *"Write a test for `<requirement, story or file>`."*
- *"Is there already a keyword for `<…>`?"*
- *"Open a REPL with `<resource>` and `<do something>`."*, to try keywords one by one before they go into a test
- *"Try `<flow>` against the real app, with a visible browser."*, which the agent does live in the REPL, without writing a test yet
- *"Write a task that `<…>`, then run it."*

The sessions below start with *"I want to test our web shop with the Browser library, but I've never used it. How do I open a page, type into a field and check a text?"*, *"Open a REPL with our orders resource and order two coffees."* and *"Write a task that orders every product in `data/restock.csv` and logs the order ids, then run it."*

## What the agent does

### It learns the library you have

The agent looks the keywords up with `robotcode doc` in the version installed in your project, instead of answering from what it remembers about the library. From the session *From a requirement*:

<!-- excerpt: from-a-requirement -->
```console
$ robotcode doc keywords Browser 2>&1 | head -20; robotcode doc keyword Browser "New Page" 2>&1 | head -40; robotcode doc keyword Browser "Fill Text" 2>&1 | head -40; robotcode doc keyword Browser "Get Text" 2>&1 | head -50
…
### Keyword *New Page*
…
#### Documentation:
Open a new Page.
…
```

### It tries in the REPL what it is unsure of

To try keywords and locators while no test is in play, the skill sends the agent to `robotcode repl`, an interactive shell in the project's configuration. What works there can be saved as a test with `.save`, while a test written too early can't be watched while it runs. In the session *From a requirement*, the agent tried the selectors on the running shop before it wrote anything:

<!-- excerpt: from-a-requirement -->
```console
$ robotcode session send repl-13d02ca5 'Get Text    css=#results .name    ==    coffee' 2>&1 | tail -8; echo "exit=${PIPESTATUS[0]}"
[ INFO ] Text: ['coffee']
=> 'coffee'
exit=0
```

In the session *Keywords in the REPL*, you steer the REPL prompt by prompt: the agent opens it once, keeps it running between your prompts, orders, shows the variables and reacts when an order fails:

<!-- excerpt: keywords-in-the-repl -->
```console
$ robotcode session send repl-f4e272c7 '${mug_order}=    Create Order    mug'; echo "exit=$?"
[ INFO ] Ordered 1 x mug (express: False)
[ FAIL ] mug is out of stock
exit=1
```

:::note[Driving the REPL]
How the agent keeps the REPL running between your prompts depends on its tools. GitHub Copilot in VS Code can type into a terminal and read it back, and Codex can write to a running command, so they can work at the REPL's prompt. Claude Code and GitHub Copilot CLI have no tool for that, so they run the REPL with [`robotcode session`](/guides/cli/sessions/), as in these sessions: `session start repl` starts it and prints an ID, each `session send` runs one input and returns with its output and an exit code, and `session stop` ends it. A session has to keep running after the command that started it, which not every sandbox allows; see [Where sessions can't run](/guides/cli/sessions/#where-sessions-cant-run).
:::

### It checks before it runs

`robotcode analyze code` finds unknown keywords, wrong arguments and unresolved variables without running anything. In the session *From a requirement*, it found a line in a new keyword that Robot Framework doesn't accept, before the first run:

<!-- excerpt: from-a-requirement -->
```console
…
resources/orders.resource:31:5: [ERROR] KeywordNotFound: No keyword with name 'Submit Ordr' found.
resources/shop.resource:63:9: [ERROR] ModelError: Invalid variable name '${listed}[${name}]'.
Files: 8, Errors: 2, Warnings: 0, Infos: 0, Hints: 0 (in 2.44s)
…
```

The agent changed that line, and the run that followed passed. The other error was in the project before. It left that one as it was and reported it in its answer.

### It runs what it wrote, by name

To run only the new tests, the agent selects their suite by its long name, as in `robotcode robot -s Tests.Search`. In the session *From a requirement*, it ran the suite in Chromium and, with the `dev` profile, in Firefox. It also ran the new tests against a broken copy of the page, to see that they can fail:

<!-- excerpt: from-a-requirement -->
```console
…
Search Field Has Its Label :: The start page has a search field la... | FAIL |
TimeoutError: locator.waitFor: Timeout 10000ms exceeded.
Search Lists Matching Products With Prices :: Text and Enter list ... | FAIL |
…
```

### A task works the same way

A task is what Robot Framework runs from a `*** Tasks ***` section. The agent writes and checks it like a test, runs it with `robotcode robot` and lists it with `robotcode discover tasks`. Robot Framework doesn't run tests and tasks together, so in the session the agent put the task into a folder of its own, `tasks/`. Since `robot.toml` only includes `tests/`, a plain `robotcode discover tasks` finds nothing there, so the agent named the folder:

<!-- excerpt: a-task -->
```console
$ robotcode discover tasks tasks/
# Tasks

- **Tasks.Restock.Order Restock List** (`tasks/restock.robot:18`)
…
```

More on the commands: [REPL](/guides/cli/repl/) and [Analyzing Code](/guides/cli/analyzing-code/).

## What to watch out for

- **Let the agent see the application.** Without the page running, it can't know your markup. In the session *From a requirement*, the page was running, and the agent used it:

  <!-- excerpt: from-a-requirement -->
  > The shop page answers on port 8080, so I can try this against the real page instead of guessing at selectors.
- **Read what else it changed.** A new test can need more than a new file. In the session, the agent also changed the CI workflow and said so:

  <!-- excerpt: from-a-requirement -->
  > - **CI workflow:** I also changed `.github/workflows/tests.yml`, which you didn't ask for. It now installs `robotframework-browser` and runs `rfbrowser init --with-deps chromium`, because the tests can't run in CI without them. I haven't run this workflow, or the tests against staging, so check both on the first push.
- **A run replaces the last results.** It writes to the output directory of `robot.toml`, so the `output.xml`, `log.html` and `report.html` of the run before are gone. If you still need them, ask for another directory, such as `-d results/<name>`.
- **Decide where tasks live.** A folder outside the `paths` of `robot.toml` is not part of a plain run. Name the folder, as the agent does in *A task*, or add a profile for the tasks.

## The sessions

<!-- session: from-a-requirement -->
<details class="rc-session-details">
<summary>From a requirement <span>“I want to test our web shop with the Browser library, but I've never used it. How do I open a page, type into a field and check a text?”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** I want to test our web shop with the Browser library, but I've never used it. How do I open a page, type into a field and check a text?

</div>

*Loaded the skill `robotcode:robotcode`*

*…*

````console
$ robotcode doc keywords Browser 2>&1 | head -20; robotcode doc keyword Browser "New Page" 2>&1 | head -40; robotcode doc keyword Browser "Fill Text" 2>&1 | head -40; robotcode doc keyword Browser "Get Text" 2>&1 | head -50
# Library *Browser*

…
### Keyword *New Page*

#### Arguments: 

| | | | | |
|:--|:--|:--|:--|:--|
| `url`| : `str` \| `None` | = | `${None}` | Optional URL to navigate the page to. The url should include the protocol, for example `https://`. |
| `wait_until`| : `PageLoadStates` | = | `load` | When to consider operation succeeded, defaults to load. Events can be either: `domcontentloaded` - consider operation to be finished when the DOMContentLoaded event is fired. `load` - consider operation to be finished when the load event is fired. `networkidle` - consider operation to be finished when there are no network connections for at least 500 ms. `commit` - consider operation to be finished when network response is received and the document started loading. |

**Return Type**: `NewPageDetails`


**Tags**: 
- BrowserControl
- Setter

#### Documentation:
Open a new Page.
…
````

*…*

<div class="rc-session-answer">

**Agent:** The shop page answers on port 8080, so I can try this against the real page instead of guessing at selectors.

</div>

*…*

```console
$ robotcode session start repl 2>&1
Started session repl-13d02ca5.
```

```console
$ robotcode session send repl-13d02ca5 'Import Library    Browser' 2>&1; echo "exit=$?"
exit=0
```

```console
$ robotcode session send repl-13d02ca5 'New Page    ${BASE_URL}' 2>&1 | tail -25; echo "exit=${PIPESTATUS[0]}"
[ INFO ] Starting Browser process ~/webshop/.venv/lib/python3.13/site-packages/Browser/wrapper/index.js using at 127.0.0.1:45183
[ INFO ] Successfully initialized new page object and opened url: http://localhost:8080
[ INFO ] No browser and context was open. New browser and context was automatically opened when page is created.
=> {'page_id': 'page=cf4092ff-f80f-472a-94c5-98d2857a4657', 'video_path': ''}
exit=0
```

```console
$ robotcode session send repl-13d02ca5 'Get Title    ==    Demo Web Shop' 2>&1 | tail -8; echo "exit=${PIPESTATUS[0]}"
[ INFO ] Title: 'Demo Web Shop'
=> 'Demo Web Shop'
exit=0
```

```console
$ robotcode session send repl-13d02ca5 'Fill Text    input[type=search]    coffee' 2>&1 | tail -8; echo "exit=${PIPESTATUS[0]}"
[ INFO ] Fills the text 'coffee' in the given field.
exit=0
```

```console
$ robotcode session send repl-13d02ca5 'Keyboard Key    press    Enter' 2>&1 | tail -8; echo "exit=${PIPESTATUS[0]}"
exit=0
```

```console
$ robotcode session send repl-13d02ca5 'Get Text    css=#results .name    ==    coffee' 2>&1 | tail -8; echo "exit=${PIPESTATUS[0]}"
[ INFO ] Text: ['coffee']
=> 'coffee'
exit=0
```

```console
$ robotcode session send repl-13d02ca5 'Get Text    css=#results .price    ==    9.99 €' 2>&1 | tail -12; echo "exit=${PIPESTATUS[0]}"
[ INFO ] *HTML*</td></tr><tr><td colspan="3"><a href="browser/screenshot/fail-screenshot-1.png" target="_blank"><img src="browser/screenshot/fail-screenshot-1.png" style="max-width:800px;max-height:800px;"/></a>
[ INFO ] See also file://~/webshop/results/playwright-log.txt for additional details.
[ FAIL ] Text '4.50 €' (str) should be '9.99 €' (str)
exit=1
```

```console
$ robotcode session stop repl-13d02ca5 2>&1; d=$(mktemp -d); cat > $d/first_browser_test.robot <<'EOF'
*** Settings ***
Library    Browser


*** Test Cases ***
Search Finds Coffee
    New Browser    ${BROWSER}    headless=True
    New Page    ${BASE_URL}
    Fill Text    input[type=search]    coffee
    Keyboard Key    press    Enter
    Get Text    css=#results .name    ==    coffee
    Get Text    css=#results .price    ==    4.50 €
EOF
robotcode analyze code $d/first_browser_test.robot 2>&1 | tail -5; robotcode robot --output NONE --log NONE --report NONE -d $d/out $d/first_browser_test.robot 2>&1 | tail -12; echo "exit=${PIPESTATUS[0]}"; rm -rf $d; git status --short; sed -n 1,40p tests/search.robot
Files: 0, Errors: 0, Warnings: 0, Infos: 0, Hints: 0 (in 0.01s)
==============================================================================
First Browser Test                                                            
==============================================================================
Search Finds Coffee                                                   | PASS |
------------------------------------------------------------------------------
First Browser Test                                                    | PASS |
1 test, 1 passed, 0 failed
==============================================================================
Output:  NONE
exit=0
*** Settings ***
Documentation    Finding products by their name.
Metadata         Owner    Team Catalog

Resource         ../resources/shop.resource

Test Template    Search Should Find


*** Test Cases ***    TEXT    PRODUCTS
Find Coffee           coff    coffee
Find Tea              tea     tea
Find Several          e       beans    coffee    tea
Find Nothing          xyz
```

<div class="rc-session-answer">

**Agent:** You need four keywords: `New Page` opens the page, `Fill Text` types into a field, `Keyboard Key` presses Enter, and `Get Text` checks a text. I ran this test against your shop at `http://localhost:8080` in headless Chromium, and it passed:

```robotframework
*** Settings ***
Library    Browser


*** Test Cases ***
Search Finds Coffee
    New Browser    ${BROWSER}    headless=True
    New Page    ${BASE_URL}
    Fill Text    input[type=search]    coffee
    Keyboard Key    press    Enter
    Get Text    css=#results .name    ==    coffee
    Get Text    css=#results .price    ==    4.50 €
```

`${BROWSER}` and `${BASE_URL}` come from `robot.toml`, so the same test also works with the `dev` and `ci` profiles. I only ran it with the default settings, not with those profiles.

**What each step does**
| Step | Keyword | Notes |
|---|---|---|
| Start the browser | `New Browser` | Use `headless=False` to watch it run. |
| Open a page | `New Page    <url>` | If no browser is open, it starts one with default settings. |
| Type into a field | `Fill Text    <selector>    <text>` | Clears the field, then inserts the text. To simulate typing character by character, use `Type Text`. |
| Press a key | `Keyboard Key    press    Enter` | The shop's search only reacts to Enter and has no button. |
| Check a text | `Get Text    <selector>    ==    <expected>` | Fails the test if the text differs. |

**How the text check behaves**
`Get Text` is both the getter and the check. Without `==` it just returns the text, and a wrong value fails with a clear message. I tried a wrong price on purpose:

```
Text '4.50 €' (str) should be '9.99 €' (str)
```

The Browser library also retries these checks until its timeout, so you usually don't need `Sleep` for results that appear a moment later.

**Common pitfalls**
- **Selectors starting with `#`:** write `css=#results`, because Robot Framework treats a bare `#results` at the start of a cell as a comment.
- **Selectors matching several elements:** `Get Text` and `Fill Text` use strict mode, so they fail if the selector matches more than one element. For example, `.name` alone would fail when searching for `e`, which finds three products.
- **After installing or updating the library:** run `rfbrowser init` again. It's already set up in your `.venv`.

</div>

*…*

<div class="rc-session-answer">

**Your repo**
I ran the test from a temporary folder and deleted it, so nothing in the repo changed. The wrong-price check did leave a failure screenshot under `results/`, which git ignores.

If you want this as a real test, `tests/search.robot` is the natural place. Its tests currently go through `ShopLibrary` using a test template, so I'd put the browser steps in a keyword in `resources/shop.resource`. Should I add it there?

</div>

<div class="rc-session-prompt">

**You:** Great. Then write a test for `requirements/SHOP-110.md`.

</div>

*…*

```console
$ robotcode doc keywords Browser "Get Element" 2>&1 | cut -c1-200; robotcode doc keyword Browser "Get Element States" 2>&1 | sed -n 1,25p | cut -c1-220; robotcode doc keyword Browser "Get Element By Role" 2>&1 | sed -n 1,22p | cut -c1-200; robotcode doc keyword Browser "Get Element Count" 2>&1 | sed -n 1,14p | cut -c1-200; rfbrowser init --help 2>&1 | cut -c1-160; robotcode session start repl 2>&1
# Library *Browser*

- **Get Element** `(selector: str)` — Returns a selector string that points to the element found by `selector`.
…
Started session repl-d12621c6.
```

*…*

```console
$ S=repl-d12621c6; robotcode session send $S '${field}=    Get Element By Role    searchbox    name=Search products    exact=True' 2>&1 | tail -4; echo "exit=${PIPESTATUS[0]}"
[ INFO ] Locator found successfully.
[ INFO ] ${field} = internal:role=searchbox[name="Search products"s]
exit=0
```

```console
$ S=repl-d12621c6; robotcode session send $S 'Get Element States    ${field}    contains    visible' 2>&1 | tail -4; echo "exit=${PIPESTATUS[0]}"
[ INFO ] States are: ['attached', 'visible', 'enabled', 'editable', 'defocused']
=> ['attached', 'visible', 'enabled', 'editable', 'defocused']
exit=0
```

<div class="rc-session-answer">

**Agent:** Next, the hidden message. It's in the HTML from the start, so a plain text check might pass even when the shop isn't showing it.

</div>

```console
$ S=repl-d12621c6; robotcode session send $S 'Get Text    id=message    ==    No products found' 2>&1 | tail -4 | cut -c1-200; echo "exit=${PIPESTATUS[0]}"
[ INFO ] Text: ['No products found']
=> 'No products found'
exit=0
```

```console
$ S=repl-d12621c6; robotcode session send $S 'Get Element States    id=message' 2>&1 | tail -3 | cut -c1-200; echo "exit=${PIPESTATUS[0]}"
[ INFO ] States are: ['attached', 'hidden', 'enabled', 'defocused']
=> ['attached', 'hidden', 'enabled', 'defocused']
exit=0
```

<div class="rc-session-answer">

**Agent:** That confirms it: `Get Text` passes while the message is still hidden, so the test also has to check that it's visible. Next, reading several results.

</div>

*…*

```console
$ S=repl-d12621c6; robotcode session send $S 'Get Text    css=#results .product    text_type=allInnerTexts' 2>&1 | tail -3 | cut -c1-300; echo "exit=${PIPESTATUS[0]}"
[ INFO ] Text: ['beans\n9.90 €', 'coffee\n4.50 €', 'tea\n3.20 €']
=> ['beans\n9.90 €', 'coffee\n4.50 €', 'tea\n3.20 €']
exit=0
```

*…*

```console
$ robotcode session stop repl-d12621c6 2>&1
cat >> tests/search.robot <<'EOF'

Search Field Has Its Label
    [Documentation]    The start page has a search field labelled "Search products".
    [Metadata]    Requirement    SHOP-110
    [Setup]    Open Shop Page
    [Template]    Search Field Should Be Labelled
    Search products

Search Lists Matching Products With Prices
    [Documentation]    Text and Enter list every product whose name contains the text, with its price.
    [Metadata]    Requirement    SHOP-110
    [Setup]    Open Shop Page
    [Template]    Shop Page Search Should List
    coffee    coffee=4.50 €
    ug        mug=12.00 €
    e         beans=9.90 €    coffee=4.50 €    tea=3.20 €

Search Ignores Upper And Lower Case
    [Documentation]    The search finds a product however its name is capitalized.
    [Metadata]    Requirement    SHOP-110
    [Setup]    Open Shop Page
    [Template]    Shop Page Search Should List
    COFFEE    coffee=4.50 €
    CoFfEe    coffee=4.50 €

Search Without A Match Shows A Message
    [Documentation]    When no product matches, the shop shows "No products found".
    [Metadata]    Requirement    SHOP-110
    [Setup]    Open Shop Page
    [Template]    Shop Page Search Should Find Nothing
    xyz
EOF
…
git diff --stat; robotcode analyze code 2>&1 | tail -15; echo "analyze exit=${PIPESTATUS[0]}"; robotcode discover tests --search SHOP-110 2>&1 | tail -12
 resources/shop.resource | 46 ++++++++++++++++++++++++++++++++++++++++++++++
 tests/search.robot      | 31 +++++++++++++++++++++++++++++++
 2 files changed, 77 insertions(+)
resources/orders.resource:31:5: [ERROR] KeywordNotFound: No keyword with name 'Submit Ordr' found.
resources/shop.resource:63:9: [ERROR] ModelError: Invalid variable name '${listed}[${name}]'.
Files: 8, Errors: 2, Warnings: 0, Infos: 0, Hints: 0 (in 2.44s)
analyze exit=1
- **Tests.Search.Search Lists Matching Products With Prices** (`tests/search.robot:23`)
- **Tests.Search.Search Ignores Upper And Lower Case** (`tests/search.robot:32`)
- **Tests.Search.Search Without A Match Shows A Message** (`tests/search.robot:40`)

## Statistics

- _Suites:_ 2
- _Suites with tests:_ 1
- _Tests:_ 4

_Filters: search=SHOP-110_
```

```console
$ sed -i 's/^        VAR    \${listed}\[\${name}\]    \${price}$/        Set To Dictionary    ${listed}    ${name}=${price}/' resources/shop.resource; sed -n 60,66p resources/shop.resource; robotcode analyze code 2>&1 | tail -4; robotcode robot -s Tests.Search 2>&1 | tail -30; echo "exit=${PIPESTATUS[0]}"
    ${prices}=    Get Text    css=#results .price    text_type=allInnerTexts
    VAR    &{listed}
    FOR    ${name}    ${price}    IN ZIP    ${names}    ${prices}
        Set To Dictionary    ${listed}    ${name}=${price}
    END
    Dictionaries Should Be Equal    ${listed}    ${expected}
    Get Element States    id=message    contains    hidden
resources/orders.resource:31:5: [ERROR] KeywordNotFound: No keyword with name 'Submit Ordr' found.
Files: 8, Errors: 1, Warnings: 0, Infos: 0, Hints: 0 (in 0.04s)
…
==============================================================================
Tests :: Web shop acceptance tests                                    | PASS |
8 tests, 8 passed, 0 failed
==============================================================================
Output:  ~/webshop/results/output.xml
Log:     ~/webshop/results/log.html
Report:  ~/webshop/results/report.html
exit=0
```

```console
$ d=$(mktemp -d); curl -s http://localhost:8080 > $d/index.html
python - "$d/index.html" <<'EOF'
import sys
p=sys.argv[1]; s=open(p,encoding='utf-8').read()
n=s
n=n.replace('aria-label="Search products" placeholder="Search products"','aria-label="Find" placeholder="Find"')
n=n.replace('search.value.toLowerCase()','search.value')
n=n.replace('coffee: 4.5','coffee: 4.6')
n=n.replace('document.getElementById("message").hidden = found.length > 0;','')
assert n.count('Find')>=2 and 'toLowerCase' not in n and '4.6' in n and '.hidden =' not in n
open(p,'w',encoding='utf-8').write(n)
EOF
python -m http.server 8099 --directory $d >/dev/null 2>&1 & srv=$!; sleep 1
robotcode robot -v BASE_URL:http://localhost:8099 --output NONE --log NONE --report NONE -d $d/out -s Tests.Search 2>&1 | grep -E "PASS|FAIL|tests,|should|Expected|^[A-Z].*contains|[Ee]rror" | cut -c1-170
kill $srv; rm -rf $d
echo ===== dev firefox; robotcode -p dev robot --output NONE --log NONE --report NONE -d /tmp/ffout -s Tests.Search 2>&1 | grep -E "\| (PASS|FAIL)|tests,|rror" | cut -c1-150; rm -rf /tmp/ffout
echo ===== full; robotcode robot 2>&1 | grep -E "^Tests.* \| |tests,|FAIL|rror" | cut -c1-150; echo "exit=${PIPESTATUS[0]}"; git status --short
Find Coffee                                                           | PASS |
Find Tea                                                              | PASS |
Find Several                                                          | PASS |
Find Nothing                                                          | PASS |
Search Field Has Its Label :: The start page has a search field la... | FAIL |
TimeoutError: locator.waitFor: Timeout 10000ms exceeded.
Search Lists Matching Products With Prices :: Text and Enter list ... | FAIL |
Search Ignores Upper And Lower Case :: The search finds a product ... | FAIL |
1) Element count for selector `css=#results .product` is '0' (int) should be '1' (int)
2) Element count for selector `css=#results .product` is '0' (int) should be '1' (int)
Search Without A Match Shows A Message :: When no product matches,... | FAIL |
Elements states '['attached', 'defocused', 'enabled', 'hidden']' (list) should contain '['visible']' (list)
Tests.Search :: Finding products by their name.                       | FAIL |
8 tests, 4 passed, 4 failed
Tests :: Web shop acceptance tests                                    | FAIL |
8 tests, 4 passed, 4 failed
…
17 tests, 16 passed, 1 failed
exit=1
 M resources/shop.resource
 M tests/search.robot
```

*…*

<div class="rc-session-answer">

**Agent:** I added four browser tests for SHOP-110 to `tests/search.robot`, one per acceptance criterion, and they pass in both Chromium and Firefox. In the full Chromium run, 16 of 17 tests pass. The one failure is `Login Works`, which also fails on a clean `main`. Nothing is committed yet.

| Criterion | Test | What it checks |
|---|---|---|
| 1. Labelled field | `Search Field Has Its Label` | A visible search field with the exact label "Search products" |
| 2. Lists matches with prices | `Search Lists Matching Products With Prices` | `coffee`, `ug` and `e`, each with exactly the expected products and prices |
| 3. Ignores case | `Search Ignores Upper And Lower Case` | `COFFEE` and `CoFfEe` |
| 4. No match | `Search Without A Match Shows A Message` | `xyz` lists nothing and shows the message |

The tests carry `[Metadata]    Requirement    SHOP-110`. I didn't tag them `smoke` or mark them high risk, because the requirement doesn't call for either. Their keywords are in `resources/shop.resource`.

**How I checked them**
- **Can they fail?** Against a broken copy of the page with one bug per criterion, all four failed, and the three I checked closely failed for the right reason, e.g. `Key coffee: 4.60 € != 4.50 €`. The label test timed out looking for the field.
- **The hidden message:** "No products found" is always in the page, just hidden, and `Get Text` still reads it. The test therefore also checks that the message is visible.

**Changes that affect other tests**
- **CI workflow:** I also changed `.github/workflows/tests.yml`, which you didn't ask for. It now installs `robotframework-browser` and runs `rfbrowser init --with-deps chromium`, because the tests can't run in CI without them. I haven't run this workflow, or the tests against staging, so check both on the first push.
- **Shared resource:** `shop.resource` now imports Browser, and every suite uses that file. A missing Browser install would therefore cause import errors in all suites, not just search.
- **Local server:** these four tests need the shop page running at `BASE_URL`. `AGENTS.md` still says the suites need no server, so that line needs updating.

**Problems I found but didn't change**
1. **`Login Works` fails:** it gets `Welcome back, alice!` but expects `Welcome back, Alice!`. Either the test or `greeting` in `ShopLibrary` is wrong, so your CI should already be red because of it.
2. **The in-memory search is case-sensitive:** `search_products` in `ShopLibrary` doesn't meet criterion 3, while the web page does. The older `Find ...` tests don't try uppercase, so they don't notice.
3. **Typo in `resources/orders.resource:31`:** `Submit Ordr` should be `Submit Order`. No test reaches it yet, but static analysis reports it as an error, and `Checkout` will fail when it's called.

Do you want me to fix any of these, or commit the tests? For `Login Works` I'd need to know which greeting is correct, though "Alice" looks like the intended one.

</div>

<div class="rc-session-prompt">

**You:** Add one of them to the smoke tests.

</div>

```console
$ python - <<'EOF'
p='tests/search.robot'
s=open(p,encoding='utf-8').read()
old="""    [Documentation]    Text and Enter list every product whose name contains the text, with its price.
    [Metadata]    Requirement    SHOP-110
"""
assert s.count(old)==1
open(p,'w',encoding='utf-8').write(s.replace(old,old+"    [Tags]    smoke\n"))
EOF
robotcode discover tests -i smoke 2>&1 | grep -E '^- |Tests:' ; robotcode analyze code tests/search.robot 2>&1 | tail -1; robotcode robot -i smoke 2>&1 | grep -E "\| (PASS|FAIL)|tests,|!" | cut -c1-120; git status --short
- **Tests.Cart.Add Item To Cart** (`tests/cart.robot:15`)
- **Tests.Login.Login Works** (`tests/login.robot:11`)
- **Tests.Login.Logout Works** (`tests/login.robot:18`)
- **Tests.Orders.Order Coffee** (`tests/orders.robot:14`)
- **Tests.Search.Search Lists Matching Products With Prices** (`tests/search.robot:23`)
- _Suites:_ 5
- _Suites with tests:_ 4
- _Tests:_ 5
Files: 1, Errors: 0, Warnings: 0, Infos: 0, Hints: 0 (in 0.03s)
Add Item To Cart :: A product added to the cart is in the cart.       | PASS |
Tests.Cart :: Filling and emptying the cart.                          | PASS |
Login Works :: A user who logs in is greeted by name.                 | FAIL |
Welcome back, alice! != Welcome back, Alice!
Logout Works :: A user who logs out is no longer logged in.           | PASS |
Tests.Login :: Logging in to the shop and out again.                  | FAIL |
2 tests, 1 passed, 1 failed
Order Coffee :: An order for a product in stock is placed.            | PASS |
Tests.Orders :: Placing orders.                                       | PASS |
Search Lists Matching Products With Prices :: Text and Enter list ... | PASS |
Tests.Search :: Finding products by their name.                       | PASS |
Tests :: Web shop acceptance tests                                    | FAIL |
5 tests, 4 passed, 1 failed
 M .github/workflows/tests.yml
 M resources/shop.resource
 M tests/search.robot
```

<div class="rc-session-answer">

**Agent:** I tagged `Search Lists Matching Products With Prices` as `smoke` (`tests/search.robot:23`) and it passes. I took "one of them" to mean one of the four new tests, and chose this one because it covers the main path: type a text, press Enter, get products with prices.

The smoke set now has 5 tests, and 4 pass. The failure is `Login Works`, the same `alice`/`Alice` problem as before, so the smoke run stays red until that's fixed.

This is also the first smoke test that needs a browser and the shop page running at `BASE_URL`. The other four run in memory, so smoke runs now depend on that page being up.

Nothing is committed yet.

</div>

</div>

</details>
<!-- /session -->

<!-- session: keywords-in-the-repl -->
<details class="rc-session-details">
<summary>Keywords in the REPL <span>“Open a REPL with our orders resource and order two coffees.”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Open a REPL with our orders resource and order two coffees.

</div>

*Loaded the skill `robotcode:robotcode`*

*…*

```console
$ robotcode session start repl
Started session repl-f4e272c7.
```

```console
$ robotcode session send repl-f4e272c7 'Import Resource    ${CURDIR}/resources/orders.resource'
(Bash completed with no output)
```

```console
$ robotcode session send repl-f4e272c7 '${order}=    Create Order    coffee    quantity=2'; echo "exit=$?"
[ INFO ] Ordered 2 x coffee (express: False)
[ INFO ] ${id} = order-4711
[ INFO ] ${order} = order-4711
exit=0
```

```console
$ robotcode session send repl-f4e272c7 'Order Status Should Be    ${order}    placed'; echo "exit=$?"
[ INFO ] ${status} = placed
exit=0
```

<div class="rc-session-answer">

**Agent:** The order for two coffees went through as `order-4711`, and `Order Status Should Be` confirms its status is `placed`.

```robotframework
Import Resource    ${CURDIR}/resources/orders.resource
${order}=    Create Order    coffee    quantity=2
Order Status Should Be    ${order}    placed
```

- **Shop state:** the order only exists in the in-memory shop from `ShopLibrary`, so nothing real was ordered. I didn't log in, because `Create Order` worked without it; the tests in `tests/orders.robot` log in as `alice` first.
- **Not submitted:** I only created the order. `Submit Order` wasn't part of your request, so I didn't run it.
- **Bug in `Checkout`:** this keyword in `resources/orders.resource` calls `Submit Ordr` instead of `Submit Order`, so it will fail with a "no keyword found" error when called. I didn't run it or change it, but I can fix it if you like.

The REPL is still open as session `repl-f4e272c7`, with `${order}` available, and it closes by itself after 15 idle minutes. To send more to it or close it:

```bash
robotcode session send repl-f4e272c7 '<keyword call>'
robotcode session stop repl-f4e272c7
```

</div>

<div class="rc-session-prompt">

**You:** Which variables are there now?

</div>

```console
$ robotcode session send repl-f4e272c7 '.vars --user'; echo "exit=$?"
  ${BASE_URL}  'http://localhost:8080'
  ${BROWSER}   'chromium'
  ${order}     'order-4711'
exit=0
```

<div class="rc-session-answer">

**Agent:** Three variables are set in the session, not counting Robot Framework's built-ins:

| Variable | Value | Comes from |
| --- | --- | --- |
| `${BASE_URL}` | `http://localhost:8080` | `robot.toml` |
| `${BROWSER}` | `chromium` | `robot.toml` |
| `${order}` | `order-4711` | the `Create Order` call |

`${BROWSER}` is `chromium` because I started the session without a profile. The `dev` profile would make it `firefox`.

</div>

<div class="rc-session-prompt">

**You:** Now order a mug.

</div>

```console
$ robotcode session send repl-f4e272c7 '${mug_order}=    Create Order    mug'; echo "exit=$?"
[ INFO ] Ordered 1 x mug (express: False)
[ FAIL ] mug is out of stock
exit=1
```

<div class="rc-session-answer">

**Agent:** The mug order failed with `mug is out of stock`, so no order was created and `${mug_order}` wasn't set.

This is expected: mugs start with a stock of 0 in `ShopLibrary`, and the `Sold Out Product Cannot Be Ordered` test checks for this exact error. The `Ordered 1 x mug` line above the failure doesn't mean it worked, because `Create Order` logs that before it places the order.

The session is still open and `${order}` still holds your coffee order. The failed call does mark the session as failed, so `robotcode session result` will report `1`.

</div>

<div class="rc-session-prompt">

**You:** What's the status of the coffee order? Then close the REPL.

</div>

```console
$ robotcode session send repl-f4e272c7 'Order Status    ${order}'; echo "exit=$?"
=> 'placed'
exit=0
```

```console
$ robotcode session stop repl-f4e272c7; echo "exit=$?"
exit=0
```

<div class="rc-session-answer">

**Agent:** The coffee order `order-4711` still has the status `placed`, and the REPL is now closed.

Closing it also discarded the in-memory shop, so that order and the session's variables are gone. I didn't change any files in the project, and the `Submit Ordr` typo in `Checkout` is still there.

</div>

</div>

</details>
<!-- /session -->

<!-- session: a-task -->
<details class="rc-session-details">
<summary>A task <span>“Write a task that orders every product in <code>data/restock.csv</code> and logs the order ids, then run it.”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Write a task that orders every product in `data/restock.csv` and logs the order ids, then run it.

</div>

*Loaded the skill `robotcode:robotcode`*

*…*

```console
$ python - <<'EOF'
from pathlib import Path
p = Path("libraries/ShopLibrary.py")
s = p.read_text()
s = s.replace('''from robot.api import logger
''', '''import csv
from pathlib import Path

from robot.api import logger
''', 1)
s = s.replace('''    @keyword
    def order_status(self''', '''    @keyword
    def read_order_list(self, path: Path) -> list[dict[str, str]]:
        """Returns the rows of the CSV file ``path``, each as a dictionary by column name."""
        with path.open(newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))

    @keyword
    def order_status(self''', 1)
p.write_text(s)
EOF
mkdir -p tasks
cat > tasks/restock.robot <<'EOF'
*** Settings ***
Documentation    Orders the products on the restock list.
Metadata         Owner    Team Checkout

Resource         ../resources/shop.resource
Resource         ../resources/orders.resource

Task Setup       Open Shop As    alice

Task Tags        orders


*** Variables ***
${RESTOCK_FILE}    ${CURDIR}/../data/restock.csv


*** Tasks ***
Order Restock List
    [Documentation]    Orders every product in ${RESTOCK_FILE} and logs the order ids.
    ${rows}=    Read Order List    ${RESTOCK_FILE}
    Should Not Be Empty    ${rows}
    FOR    ${row}    IN    @{rows}
        ${order}=    Create Order    ${row}[product]    ${row}[quantity]
        Log    ${order}: ${row}[quantity] x ${row}[product]    console=True
    END
EOF
robotcode analyze code tasks/restock.robot libraries; echo "analyze exit $?"; robotcode discover tasks tasks/; robotcode robot tasks/; echo "robot exit $?"; robotcode results summary; robotcode discover tests | tail -6; git status --short
Files: 1, Errors: 0, Warnings: 0, Infos: 0, Hints: 0 (in 0.45s)
analyze exit 0
# Tasks

- **Tasks.Restock.Order Restock List** (`tasks/restock.robot:18`)

## Statistics

- _Suites:_ 2
- _Suites with tasks:_ 1
- _Tasks:_ 1

==============================================================================
Tasks                                                                         
==============================================================================
Tasks.Restock :: Orders the products on the restock list.                     
==============================================================================
Order Restock List :: Orders every product in /tmp/-ho... order-4711: 10 x coffee
order-4712: 5 x tea
order-4713: 3 x beans
| PASS |
------------------------------------------------------------------------------
Tasks.Restock :: Orders the products on the restock list.             | PASS |
1 task, 1 passed, 0 failed
==============================================================================
Tasks                                                                 | PASS |
1 task, 1 passed, 0 failed
==============================================================================
Output:  ~/webshop/results/output.xml
Log:     ~/webshop/results/log.html
Report:  ~/webshop/results/report.html
robot exit 0
…
 M libraries/ShopLibrary.py
?? data/
?? tasks/
```

```console
$ sed -i 's|\[Documentation\]    Orders every product in ${RESTOCK_FILE} and logs the order ids.|[Documentation]    Orders every product in the restock list and logs the order ids.|' tasks/restock.robot
robotcode robot tasks/ | sed -n 5,10p; echo "task exit ${PIPESTATUS[0]}"
robotcode robot --output NONE --log NONE --report NONE | tail -4; echo "tests exit ${PIPESTATUS[0]}"
==============================================================================
Order Restock List :: Orders every product in the restock list and... order-4711: 10 x coffee
order-4712: 5 x tea
order-4713: 3 x beans
| PASS |
------------------------------------------------------------------------------
task exit 0
Tests :: Web shop acceptance tests                                    | FAIL |
13 tests, 12 passed, 1 failed
==============================================================================
Output:  NONE
tests exit 1
```

*…*

<div class="rc-session-answer">

**Agent:** I wrote the task and ran it, and it passed. All three products were ordered:

| Order id | Quantity | Product |
|---|---|---|
| `order-4711` | 10 | coffee |
| `order-4712` | 5 | tea |
| `order-4713` | 3 | beans |

**These aren't real orders.** `ShopLibrary` runs the shop in memory, so the orders disappeared when the run ended and nothing reached a real or staging shop. To place real orders, the library would need a connection to the actual shop.

**What changed**
- **`tasks/restock.robot` (new):** logs in, reads the CSV, places one order per row with the existing `Create Order` keyword, and logs each id to the log and the console. It also fails if the list is empty.
- **`libraries/ShopLibrary.py`:** a new `Read Order List` keyword reads the CSV, because Robot Framework has no built-in CSV keyword and none is installed in the project.

The task is in `tasks/` rather than `tests/` because Robot can't mix tasks and tests in one run, so it would have broken the CI's `robotcode -p ci robot`. That also means a plain `robotcode robot` won't pick it up, so run it with:

```sh
robotcode robot tasks/
```

The results are in `results/` (`log.html`, `report.html`). Nothing is committed yet, and `data/` was already untracked.

**Choices to check**
- **User:** the orders are placed as `alice`, the same user the orders tests use, since you didn't name one.
- **Owner and tag:** I set the owner to `Team Checkout` and tagged the task `orders`, copied from the orders suite.
- **Requirement:** there's no `SHOP-<number>` on it, because that rule covers tests and I didn't want to make one up.
- **Failures:** if one order fails, the task stops and the remaining rows aren't ordered.

**Existing problems, not fixed**
- **Failing test:** `Login Works` fails with `Welcome back, alice! != Welcome back, Alice!`, leaving the test suite at 12 of 13 passed. It fails the same way without my library change.
- **Keyword typo:** `Checkout` in `resources/orders.resource:31` calls `Submit Ordr`, which doesn't exist, so it would fail if used. The new task doesn't call it.

</div>

<div class="rc-session-prompt">

**You:** Which tasks does the project have now?

</div>

```console
$ robotcode discover tasks tasks/
# Tasks

- **Tasks.Restock.Order Restock List** (`tasks/restock.robot:18`)

## Statistics

- _Suites:_ 2
- _Suites with tasks:_ 1
- _Tasks:_ 1
```

```console
$ robotcode discover tasks; grep -rl --include='*.robot' --include='*.resource' -i '^\*\*\* *tasks\? *\*\*\*' . --exclude-dir=.venv --exclude-dir=results
# Tasks

_(no tasks matched)_

## Statistics

- _Suites:_ 5
- _Suites with tests:_ 4
- _Tests:_ 13

./tasks/restock.robot
```

<div class="rc-session-answer">

**Agent:** The project has one task, the one I just added: **`Tasks.Restock.Order Restock List`** (`tasks/restock.robot:18`).

A plain `robotcode discover tasks` reports no tasks, because `robot.toml` only sets `paths = ["tests"]`. To see it, you have to name the folder: `robotcode discover tasks tasks/`. A search of the project's `.robot` and `.resource` files found no other task sections.

</div>

</div>

</details>
<!-- /session -->
