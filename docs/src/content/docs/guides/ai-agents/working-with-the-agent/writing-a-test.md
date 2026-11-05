---
title: Writing a Test from a Requirement
description: "Step 2 of the tutorial: have an AI agent learn a library in its installed version, try selectors on the running page, write a test from a requirement, and show you that the test can fail; try keywords in a REPL and write a task the same way."
sidebar:
  label: 2. Writing a Test from a Requirement
  order: 150.42
---

You have a requirement and want a test for it. The agent can write one, and it will probably pass. Whether it's a good test is what you find out by asking: what did it try before it wrote the test, how do you know that the test can fail, and what else did it change?

To follow along, use the [example project](/guides/ai-agents/working-with-the-agent/#following-along), and run `rfbrowser init` as its README says, because this step uses the Browser library.

## Start with the library

If you don't know a library yet, ask about it before you ask for a test:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** I want to test our web shop with the Browser library, but I've never used it. How do I open a page, type into a field and check a text?

</div>

<div class="rc-session-calls">

- [`robotcode doc keywords Browser "New Page"`](/guides/cli/browsing-documentation/)
- [`robotcode doc keywords Browser "Fill Text"`](/guides/cli/browsing-documentation/)
- [`robotcode doc keywords Browser "Get Text"`](/guides/cli/browsing-documentation/)

</div>

<div class="rc-session-answer">

**Agent:** The Browser library is installed in your project. I checked the keyword signatures with `robotcode doc`. Here is a minimal suite:

```robot wrap
*** Settings ***
Library    Browser

*** Test Cases ***
Search Works
    New Browser    chromium    headless=False
    New Page       https://shop.example.com
    Fill Text      id=search    laptop
    Click          id=search-button
    Get Text       css=h1    ==    Search results
    [Teardown]    Close Browser
```

**The three things you asked about**
- **Open a page:** `New Browser` starts the browser. It is headless by default, so `headless=False` lets you watch it. `New Page    <url>` then opens the URL in a new tab. If you skip `New Browser`, `New Page` starts one for you.
- **Type into a field:** `Fill Text    <selector>    <text>` clears the field and types the text. `Type Text` types key by key, which you rarely need.
- **Check a text:** `Get Text    <selector>    ==    expected` reads the text and asserts it in one step. …

…

</div>

</div>

Look at where the answer comes from. Here, the agent looked the keywords up with [`robotcode doc`](/guides/cli/browsing-documentation/), so they fit the version installed in your project, and it isn't answering from what it remembers about the library.

## Let it try before it writes

An agent that can see the running page doesn't have to guess its selectors. So make sure the page is running, or have the agent start it:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Start the shop's web page and leave it running.

</div>

</div>

Then point it to the requirement, and say that you want the selectors tried first:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Write a test for `requirements/SHOP-110.md`. The shop's page is running. Try your selectors on it before you write the test.

</div>

<div class="rc-session-calls">

- …
- [`robotcode session start repl`](/guides/cli/sessions/#starting-a-session)
- [`robotcode session send $S 'Import Library    Browser'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send $S 'New Page    http://localhost:8080'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send $S 'Fill Text    role=searchbox[name="Search products"]    COFF'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send $S 'Keyboard Key    press    Enter'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send $S 'Get Element Count    css=.product    ==    1'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send $S 'Get Text    css=.product .name    ==    coffee'`](/guides/cli/sessions/#sending-an-input)
- …
- [`robotcode session stop $S`](/guides/cli/sessions/#ending-a-session)
- [`robotcode analyze code tests/search_web.robot resources/search.resource`](/guides/cli/analyzing-code/)
- [`robotcode robot -bl "Tests.Search Web"`](/reference/cli/#robot)

</div>

<div class="rc-session-answer">

**Agent:** I wrote the SHOP-110 test as a new suite. All 4 tests pass against the running shop, and `robotcode analyze code` reports no issues.

I tried the selectors in the REPL on the live page before writing anything. …

**Files**
- `tests/search_web.robot` has four tests, each tagged `[Metadata]    Requirement    SHOP-110`:
  - **Criterion 1:** the search field labelled "Search products" is visible.
  - **Criterion 2:** searching `e` lists beans, coffee and tea, each with its price.
  - **Criterion 3:** searching `COFF` finds coffee.
  - **Criterion 4:** searching `xyz` shows "No products found" and lists nothing.
- `resources/search.resource` holds the keywords and selectors. Per your conventions, keywords go in the resource file of their area.

…

**Things you may want to change**
- **Separate suite:** I didn't add these to `tests/search.robot`. That suite uses `Test Template` with the in-memory `ShopLibrary`, so web tests can't share it. If you'd rather have one suite, tell me.
- **No `smoke` or `Risk` tags:** the requirement doesn't say either, so I left them off.
- **Browser setting:** the tests use `${BROWSER}` from `robot.toml`, so the `dev` profile runs them in Firefox. I only ran them in the default chromium.
- **CI:** the `ci` profile points `BASE_URL` at staging, so these tests will run against staging there. I didn't check that the staging page has the same selectors.

…

</div>

</div>

In the answer, look for three things:

- **Whether each criterion of the requirement has a test.** That's the first thing to compare.
- **Whether it checked what it wrote.** [`robotcode analyze code`](/guides/cli/analyzing-code/) finds unknown keywords and wrong arguments without running anything, and then the tests have to pass.
- **What it decided for you.** Where the test went and what it left out differ from one run to the next. If that isn't what you want, say so. Rules that always apply belong in your [instructions for the agent](/guides/ai-agents/briefing/).

## Ask how you know that it works

The new test passes. That doesn't tell you much yet, because a test that can't fail always passes:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** How do I know that this test can fail? Show me.

</div>

<div class="rc-session-calls">

- [`robotcode robot -d /tmp/mut-out-$d -v BASE_URL:http://localhost:$p -bl "Tests.Search Web"`](/reference/cli/#robot)
- [`robotcode robot -bl "Tests.Search Web"`](/reference/cli/#robot)

</div>

<div class="rc-session-answer">

**Agent:** The tests can fail. I copied the shop page five times, put one bug in each copy, and served them on ports 8100–8104. Then I ran the suite against each copy with `-v BASE_URL:...`.

| Bug injected in the shop | Tests that failed |
|---|---|
| Search is case-sensitive (`toLowerCase()` removed) | `Search Ignores Case` |
| Matches only the start of a name (`startsWith`) | `Search Lists Matching Products With Price` |
| Message reads "Nothing here" instead of "No products found" | `Search Without Match Says So` |
| Coffee costs 5.50 € instead of 4.50 € | the price test and `Search Ignores Case` |
| Field label is "Find" instead of "Search products" | all four tests |

Each bug was caught, and the tests that failed were the ones for the broken criterion. …

…

I removed the mutant servers and temporary files afterwards. The real shop and test files are unchanged, and the real suite still passes 4 of 4.

</div>

</div>

This is the proof you asked for: each criterion has a test that fails when the page breaks it.

## Ask what else it changed

A new test can need more than a new file, so ask, even when all you wanted was a test:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** What else did you change besides the test?

</div>

<div class="rc-session-calls">

- [`robotcode session list`](/guides/cli/sessions/)

</div>

<div class="rc-session-answer">

**Agent:** Besides the two new files, I changed two other things:

- **`results/` directory:** I created it with `mkdir -p results` after the first REPL attempt failed. It now holds `log.html`, `output.xml`, `report.html` and `playwright-log.txt`. These come from my last real run of the new suite, `Tests.Search Web`. Any earlier run output there is overwritten.
- **Temporary mutant files:** the five broken shop copies, their servers and their output went to `/tmp`. All of it is deleted now.

…

Nothing else was touched. `git status` shows only the two new files and the `.claude/` directory that was already untracked before I started. I didn't edit `robot.toml`, the existing suites, the shop in `webshop/`, or any dependencies. No REPL sessions are left open.

</div>

</div>

## Try keywords one by one

Before there is a test, you may want to try keywords yourself and decide after each one what comes next. In a REPL, an interactive shell for Robot Framework, you can do that through the agent. It keeps the REPL running between your prompts:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Open a REPL with our orders resource and order two coffees.

</div>

<div class="rc-session-calls">

- [`robotcode doc keywords resources/orders.resource`](/guides/cli/browsing-documentation/)
- [`robotcode session start repl`](/guides/cli/sessions/#starting-a-session)
- [`robotcode session send repl-8e4fe8ff 'Import Resource    ${CURDIR}/resources/orders.resource'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send repl-8e4fe8ff '${id}=    Create Order    coffee    2'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send repl-8e4fe8ff 'Order Status Should Be    ${id}    placed'`](/guides/cli/sessions/#sending-an-input)

</div>

<div class="rc-session-answer">

**Agent:** I opened a REPL with `resources/orders.resource` loaded and ordered two coffees. `Create Order    coffee    2` returned the order id `order-4711`, and `Order Status Should Be` confirmed its status is `placed`.

The session is still open as `repl-8e4fe8ff`, with `${id}` set. I haven't stopped it, so you can keep sending keywords to it. When you're done, `robotcode session stop repl-8e4fe8ff` closes it.

…

</div>

</div>

Check how the agent understood you. "Two coffees" can also mean two orders, and then it's worth saying exactly what you want. [`robotcode session`](/guides/cli/sessions/) is how this agent keeps the REPL open. In your own terminal, you can use [`robotcode repl`](/guides/cli/repl/) directly.

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which variables are there now?

</div>

<div class="rc-session-calls">

- [`robotcode session send repl-8e4fe8ff '.vars --user'`](/guides/cli/sessions/#sending-an-input)

</div>

<div class="rc-session-answer">

**Agent:** The session currently has these user-defined variables:

| Variable | Value |
| --- | --- |
| `${BASE_URL}` | `'http://localhost:8080'` |
| `${BROWSER}` | `'chromium'` |
| `${id}` | `'order-4711'` |

…

</div>

</div>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Now order a mug.

</div>

<div class="rc-session-calls">

- [`robotcode session send repl-8e4fe8ff '${mug}=    Create Order    mug'`](/guides/cli/sessions/#sending-an-input)

</div>

<div class="rc-session-answer">

**Agent:** The mug order failed with `mug is out of stock`. The keyword logged `Ordered 1 x mug`, but `Place Order` then rejected it, so nothing was created and `${mug}` isn't set.

The session is still open and `${id}` (`order-4711`, the coffees) is unchanged. …

</div>

</div>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** What's the status of the coffee order? Then close the REPL.

</div>

<div class="rc-session-calls">

- [`robotcode session send repl-8e4fe8ff '${status}=    Order Status    ${id}'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send repl-8e4fe8ff 'Log    ${status}'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session stop repl-8e4fe8ff`](/guides/cli/sessions/#ending-a-session)

</div>

<div class="rc-session-answer">

**Agent:** The coffee order (`order-4711`, 2 x coffee) has the status `placed`.

…

</div>

</div>

A failure doesn't end the REPL, and what you set before it is still there. What you find out this way can go into a test afterwards.

## Write a task the same way

A task, the RPA counterpart of a test, is what Robot Framework runs from a `*** Tasks ***` section. You ask for it in the same way:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Write a task that orders every product in `data/restock.csv` and logs the order ids, then run it.

</div>

<div class="rc-session-calls">

- [`robotcode analyze code tasks`](/guides/cli/analyzing-code/)
- [`robotcode robot --rpa tasks`](/reference/cli/#robot)

</div>

<div class="rc-session-answer">

**Agent:** I added a task in `tasks/restock.robot` and ran it. It passed and ordered every product in `data/restock.csv`:

| Product | Quantity | Order id |
|---|---|---|
| coffee | 10 | order-4711 |
| tea | 5 | order-4712 |
| beans | 3 | order-4713 |

The task reads the CSV, skips the header row, and calls the existing `Create Order` keyword for each line. It writes each order id to the log and to the console. Static analysis reported no issues.

… To run it, use `robotcode robot --rpa tasks`. A plain `robotcode robot` still runs only `tests/`.

That run replaced the previous `results/` files (`output.xml`, `log.html`, `report.html`).

</div>

</div>

Look at where the task went, because that decides how it runs. Here it's in a folder that `robot.toml` doesn't include, so a plain run of [`robotcode robot`](/reference/cli/#robot) doesn't pick it up, and you have to name the folder.

## In your own project

- Ask about a library you don't know before you ask for a test, and check that the answer comes from the installed version.
- Point the agent to the requirement and to the running application, and say that it should try things first.
- Compare the tests with the requirement, and look at what the agent decided for you.
- Ask how you know that the test can fail, and to be shown.
- Ask what else it changed.
- To try keywords one by one, ask for a REPL, and steer it prompt by prompt.
