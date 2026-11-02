---
title: Getting to Know the Project
description: "Step 1 of the tutorial: find out with the agent which tests, tags and suites a project has, which tests cover a requirement, what a keyword takes, and how a large project is split, the way Robot Framework resolves it."
sidebar:
  label: 1. Getting to Know the Project
  order: 150.41
---

Before you change anything, find out what the project contains. An agent that reads the `.robot` files can only guess at that. With the RobotCode skill, it asks Robot Framework instead, through `robotcode discover` and `robotcode doc`, so its answer matches what a run would see.

## What you learn

- why the agent asks `robotcode discover` instead of reading the `.robot` files;
- how to find the tests of a tag, a suite or a requirement;
- how to look up what a keyword takes and does, in the versions installed in your project;
- how to ask about a large project without filling the chat.

## How to ask the agent

Ask in your own words, and name the scope when you have one: a tag, a suite, a requirement or a profile.

- *"What tests and tags exist?"*
- *"Which tests are tagged `<tag>`?"*
- *"Which tests cover requirement `<ID>`?"*, if your tests carry their requirement in a tag or in `[Metadata]`
- *"What arguments does our `<keyword>` keyword take?"*
- *"How many tests does this project have, and how are they split across `<teams, folders or tags>`?"*

The sessions below start with *"Which tests cover the cart requirements SHOP-201 to SHOP-203?"*, *"What arguments does our `Create Order` keyword take?"* and, in a generated project with 5,000 tests, *"How many tests does this project have, and how are they split across the teams?"*

## What the agent does

### It asks `robotcode discover`

Which files become suites, which tests a profile includes and which tags a test ends up with is decided when Robot Framework resolves the project: by its rules for suites and `__init__.robot` files, by the `paths`, variables and profiles in `robot.toml`, and by filters and pre-run modifiers. A search through the files sees none of that. The skill therefore tells the agent not to answer such questions by reading or searching the `.robot` files, but with `robotcode discover`, which resolves the project with its installed Robot Framework.

For the three cart requirements, the agent selected the tests by their metadata. From the session *Coverage*:

<!-- excerpt: coverage -->
```console
$ robotcode discover tests -btm "Requirement:SHOP-201 OR Requirement:SHOP-202 OR Requirement:SHOP-203"; echo ---; robotcode discover metadata --values --tests
# Tests

- **Tests.Cart.Add Item To Cart** (`tests/cart.robot:15`)
- **Tests.Cart.Remove Item From Cart** (`tests/cart.robot:22`)
- **Tests.Cart.Cart Total Adds Up** (`tests/cart.robot:29`)
…
```

Each test has its long name, such as `Tests.Cart.Add Item To Cart`: the names of its suites, then its own. `robotcode discover metadata --values --tests` lists every metadata value with the tests that carry it. To answer whether every requirement file in `requirements/` has a test, the agent then read the files and compared each acceptance criterion with these tests.

### It looks keywords up where they are installed

`robotcode doc` loads a library or a resource in the project's environment, with `robot.toml`, the profiles and the variables. So it shows the keywords of the versions you have installed, and also those of your own resources and Python libraries. The skill puts it first, before the existing tests and before external documentation. From the session *Keywords*:

<!-- excerpt: keywords -->
```console
$ robotcode doc keyword resources/orders.resource "Create Order"
### Keyword *Create Order*

#### Arguments: 

| | | | |
|:--|:--|:--|:--|
| `product`|   |  |  |
| `quantity`|   | = | `1` |
| `express`|   | = | `${False}` |
…
```

### It counts before it lists

In a project with thousands of tests, a list of every test would fill the chat and tell you little. The skill tells the agent to filter or aggregate before it lists. In the session *A large project*, it asked for the tags without their tests, for the suites and, for the last run, for statistics by tag:

<!-- excerpt: a-large-project -->
```console
…
## By Tag

| Name       | Total | Pass | Fail | Skip | Elapsed |
| ---------- | ----: | ---: | ---: | ---: | ------: |
| regression |  4500 | 4460 |   40 |    0 |  5.50 s |
| accounts   |  1000 |  992 |    8 |    0 |  1.19 s |
…
```

More on the commands: [Discovering Tests](/guides/cli/discovering-tests/) and [Browsing Documentation](/guides/cli/browsing-documentation/).

## What to watch out for

- **Name the profile when it matters.** A profile can change the `paths`, the variables or the pre-run modifiers, and so which tests there are. Say *"with the `ci` profile"*, and the agent asks `robotcode -p ci discover`.
- **Use the long name for one test or suite.** It is what `robotcode` selects by, and the agent finds it with `discover`.
- **Selecting tests by `[Metadata]` needs Robot Framework 7.5 or newer.** With an older version, tags are the way to mark what a test covers.

## The sessions

<!-- session: coverage -->
<details class="rc-session-details">
<summary>Coverage <span>“Which tests cover the cart requirements SHOP-201 to SHOP-203?”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which tests cover the cart requirements SHOP-201 to SHOP-203?

</div>

*Loaded the skill `robotcode:robotcode`*

```console
$ robotcode discover tests -btm "Requirement:SHOP-201 OR Requirement:SHOP-202 OR Requirement:SHOP-203"; echo ---; robotcode discover metadata --values --tests
# Tests

- **Tests.Cart.Add Item To Cart** (`tests/cart.robot:15`)
- **Tests.Cart.Remove Item From Cart** (`tests/cart.robot:22`)
- **Tests.Cart.Cart Total Adds Up** (`tests/cart.robot:29`)

## Statistics

- _Suites:_ 2
- _Suites with tests:_ 1
- _Tests:_ 3

---
# Metadata
…
```

<div class="rc-session-answer">

**Agent:** Each of the three cart requirements is covered by exactly one test, all in `tests/cart.robot`:

| Requirement | Test | Location |
|---|---|---|
| SHOP-201 | Tests.Cart.Add Item To Cart | `tests/cart.robot:15` |
| SHOP-202 | Tests.Cart.Remove Item From Cart | `tests/cart.robot:22` |
| SHOP-203 | Tests.Cart.Cart Total Adds Up (also tagged `Risk high`) | `tests/cart.robot:29` |

I found these by searching the tests' `[Metadata]    Requirement` values with `robotcode discover`. No other test names any of these three requirements.

To run just these three:
```bash
robotcode robot -btm "Requirement:SHOP-201 OR Requirement:SHOP-202 OR Requirement:SHOP-203"
```

</div>

<div class="rc-session-prompt">

**You:** Does every requirement in `requirements/` have a test?

</div>

*…*

```console
$ cat requirements/SHOP-110.md; echo ---; robotcode discover tests -s "Tests.Search"; echo ---; robotcode discover tests --search SHOP-110
# SHOP-110: Search products

As a customer, I want to search the products of the shop by their name, so that I quickly find what I want to buy.

## Acceptance criteria

1. The start page has a search field labelled "Search products".
2. When I type a text and press Enter, the shop lists every product whose name contains the text, with its price.
3. The search ignores upper and lower case.
4. When no product matches, the shop shows "No products found".
---
# Tests

- **Tests.Search.Find Coffee** (`tests/search.robot:11`)
- **Tests.Search.Find Tea** (`tests/search.robot:12`)
- **Tests.Search.Find Several** (`tests/search.robot:13`)
- **Tests.Search.Find Nothing** (`tests/search.robot:14`)

## Statistics

- _Suites:_ 2
- _Suites with tests:_ 1
- _Tests:_ 4

---
# Tests
…

## Statistics

- _Suites:_ 1

_Filters: search=SHOP-110_
```

*…*

<div class="rc-session-answer">

**Agent:** No. `requirements/` holds just one file, **SHOP-110 (Search products)**, and no test names it. Every test that names a requirement points to one with no file in `requirements/`.

**SHOP-110 has no linked test.** No test has `Requirement    SHOP-110` in its metadata, and the text "SHOP-110" appears nowhere in the tests. The search suite `tests/search.robot` tests this feature, but its four tests have no `Requirement` metadata. Your conventions only require it for login, cart and orders, so that's allowed, but it leaves SHOP-110 unlinked. The search tests also only partly cover its four acceptance criteria:

| # | Criterion | Covered? |
|---|---|---|
| 1 | Start page has a search field labelled "Search products" | No. The tests call `Search Products` in the in-memory `ShopLibrary` and never open the web page. |
| 2 | Lists every product whose name contains the text, **with its price** | Partly. `Search Should Find` checks that exactly the expected products come back, but not their prices. |
| 3 | Search ignores upper and lower case | No. Every search text is lowercase (`coff`, `tea`, `e`, `xyz`). |
| 4 | No match shows "No products found" | Partly. `Find Nothing` checks the result is empty, but not the message. |

**The other direction doesn't line up either.** The tests name nine requirements: SHOP-101–103 for login, SHOP-201–203 for cart and SHOP-301–303 for orders. None of them has a file in `requirements/`. Those files are either missing or kept somewhere else.

Possible next steps, if you want them:
- Add `[Metadata]    Requirement    SHOP-110` to the search tests. The suite uses a test template, so it could go on each test.
- Add tests for criterion 3 (for example, searching `COFF` should find coffee) and for the price and the "No products found" message. Criterion 1 needs a Browser-library test against `BASE_URL`.
- Check where the requirement files for SHOP-101 to SHOP-303 are.

</div>

</div>

</details>
<!-- /session -->

<!-- session: keywords -->
<details class="rc-session-details">
<summary>Keywords <span>“What arguments does our <code>Create Order</code> keyword take?”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** What arguments does our `Create Order` keyword take?

</div>

*Loaded the skill `robotcode:robotcode`*

```console
$ ls resources libraries; for f in resources/*.resource ShopLibrary; do t=$f; [ "$f" = ShopLibrary ] && t=libraries/ShopLibrary.py; echo "== $t"; robotcode doc keywords "$t" "create order" 2>&1; done
libraries:
ShopLibrary.py

resources:
cart.resource
orders.resource
shop.resource
== resources/cart.resource
# Resource *cart*

_(no keyword matches)_
== resources/orders.resource
…
```

```console
$ robotcode doc keyword resources/orders.resource "Create Order"
### Keyword *Create Order*

#### Arguments: 

| | | | |
|:--|:--|:--|:--|
| `product`|   |  |  |
| `quantity`|   | = | `1` |
| `express`|   | = | `${False}` |

#### Documentation:
Creates an order for `quantity` items of `product` and returns its id.


Fails if the product is out of stock.
```

<div class="rc-session-answer">

**Agent:** `Create Order` is in `resources/orders.resource` and takes three arguments:

| Argument | Default | Meaning |
|---|---|---|
| `product` | required | The product to order |
| `quantity` | `1` | How many items to order |
| `express` | `${False}` | Whether the order is an express order |

It returns the new order's id, and it fails if the product is out of stock.

Example:
```robotframework
${order_id}=    Create Order    Coffee Mug    quantity=3    express=${True}
```

The product name in the example is made up. The real products are defined in `libraries/ShopLibrary.py`.

</div>

<div class="rc-session-prompt">

**You:** And what does it do to place the order?

</div>

```console
$ cat resources/orders.resource
*** Settings ***
Documentation    Ordering from the demo shop.

Library          ShopLibrary


*** Keywords ***
Create Order
    [Documentation]    Creates an order for ``quantity`` items of ``product`` and returns its id.
    ...
    ...    Fails if the product is out of stock.
    [Arguments]    ${product}    ${quantity}=1    ${express}=${False}
    Log    Ordered ${quantity} x ${product} (express: ${express})
    ${id}=    Place Order    ${product}    ${quantity}    ${express}
…
```

```console
$ robotcode doc keyword libraries/ShopLibrary.py "Place Order"; grep -n "def place_order" -A30 libraries/ShopLibrary.py
### Keyword *Place Order*

#### Arguments: 

| | | | |
|:--|:--|:--|:--|
| `product`| : `str` |  |  |
| `quantity`| : `int` | = | `${1}` |
| `express`| : `bool` | = | `${False}` |

**Return Type**: `str`


#### Documentation:
…
```

<div class="rc-session-answer">

**Agent:** `Create Order` (`resources/orders.resource:8`) is a thin wrapper. It logs a line like `Ordered 3 x Coffee Mug (express: False)`, then passes its three arguments unchanged to the `Place Order` keyword from `ShopLibrary` and returns the id it gets back.

The work happens in `place_order` in `libraries/ShopLibrary.py:73`, against the shop's in-memory data:

1. **Checks stock:** if the shop has fewer than `quantity` of `product` in stock, it fails with `<product> is out of stock`. A product the shop doesn't know counts as 0 in stock, so it fails the same way.
2. **Reduces stock:** it subtracts `quantity` from that product's stock.
3. **Creates the id:** ids are numbered `order-4711`, `order-4712`, and so on, by how many orders exist so far.
4. **Sets the status:** the order gets the status `express` if `express` is true, otherwise `placed`. You can check it with `Order Status Should Be`.
5. **Returns the id.**

There's no server or browser involved, and nothing is submitted for delivery. `Submit Order` is a separate step, and it only logs a message.

While reading the file I noticed a bug nearby: `Checkout` (`resources/orders.resource:31`) calls `Submit Ordr`, a misspelling of `Submit Order`. Any test that uses `Checkout` will fail with "No keyword with name 'Submit Ordr' found." I can fix it if you want.

</div>

<div class="rc-session-prompt">

**You:** Try it out — what happens with a product that is sold out?

</div>

*…*

<div class="rc-session-answer">

**Agent:** `mug` is the sold-out product (stock 0). I'll try it in the REPL, with an in-stock order for comparison:

</div>

```console
$ printf '%s\n' 'Import Resource    ${CURDIR}/resources/orders.resource' '${id}=    Create Order    mug' '${id}=    Create Order    coffee    quantity=2' 'Order Status Should Be    ${id}    placed' '${err}=    Run Keyword And Expect Error    *    Create Order    beans    quantity=21' 'Log To Console    ${err}' | timeout 120 robotcode repl 2>&1 | tail -40; echo "exit: ${PIPESTATUS[1]}"
[ INFO ] Ordered 1 x mug (express: False)
[ FAIL ] mug is out of stock
[ INFO ] Ordered 2 x coffee (express: False)
[ INFO ] ${id} = order-4711
[ INFO ] ${id} = order-4711
[ INFO ] ${status} = placed
[ INFO ] Ordered 21 x beans (express: False)
[ FAIL ] beans is out of stock
[ INFO ] ${err} = beans is out of stock
beans is out of stock
exit: 1
```

<div class="rc-session-answer">

**Agent:** Ordering a sold-out product fails right away, with a clear message:

```
[ INFO ] Ordered 1 x mug (express: False)
[ FAIL ] mug is out of stock
```

What I saw in the REPL:

- **`Create Order    mug` fails with `mug is out of stock`.** The log line comes first because `Create Order` logs before it calls `Place Order`. So a log can show "Ordered 1 x mug" even though no order exists.
- **A failed order leaves nothing behind.** The coffee order right after it got `order-4711`, the first id, so the mug attempt used no id and changed no stock.
- **Asking for more than is in stock fails the same way.** `beans` has 20 in stock, and ordering 21 gives `beans is out of stock`. The message says "out of stock" even though the product isn't sold out, which could confuse someone reading a failed test.
- **The in-stock order works:** coffee × 2 returned `order-4711` with status `placed`.

The REPL exited with code 1 because the mug statement failed, which was the point of the test. The other statements ran normally.

To test this in a suite, catch the failure like this:

```robotframework
Run Keyword And Expect Error    mug is out of stock    Create Order    mug
```

</div>

</div>

</details>
<!-- /session -->

<!-- session: a-large-project -->
<details class="rc-session-details">
<summary>A large project <span>“How many tests does this project have, and how are they split across the teams?”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** How many tests does this project have, and how are they split across the teams?

</div>

*Loaded the skill `robotcode:robotcode`*

```console
$ robotcode discover tags --no-tests 2>&1 | tail -30; robotcode discover suites 2>&1 | tail -30
# Tags

- **accounts**
- **catalog**
- **checkout**
- **payments**
- **regression**
- **shipping**
- **smoke**

## Statistics

…

- _Suites:_ 506
- _Suites with tests:_ 500
- _Tests:_ 5000
```

<div class="rc-session-answer">

**Agent:** Now count per team via tag filters.

</div>

```console
$ for t in accounts catalog checkout payments shipping smoke regression; do echo -n "$t: "; robotcode discover tests -i $t 2>/dev/null | grep -oP '_Tests:_ \K\d+'; done; echo -n "untagged-team: "; robotcode discover tests -e accounts -e catalog -e checkout -e payments -e shipping 2>/dev/null | grep -oP '_Tests:_ \K\d+'
accounts: 1000
catalog: 1000
checkout: 1000
payments: 1000
shipping: 1000
smoke: 500
regression: 4500
untagged-team:
```

<div class="rc-session-answer">

**Agent:** The project has **5,000 tests** in 500 suite files. They are split evenly across the five teams, 1,000 tests each:

| Team | Tests |
|---|---|
| accounts | 1,000 |
| catalog | 1,000 |
| checkout | 1,000 |
| payments | 1,000 |
| shipping | 1,000 |

The team totals add up to 5,000, so every test carries exactly one team tag. By type, **500 are `smoke`** and **4,500 are `regression`**.

I got these numbers with `robotcode discover`, which applies the project's config the same way a real run does, so it counts what a run would actually see. Nothing was executed.

</div>

<div class="rc-session-prompt">

**You:** Which teams had failures in the last run, and how many?

</div>

*…*

```console
$ robotcode results summary 2>&1 | head -20; robotcode results stats --by tag 2>&1
# Summary — results/output.xml

- _Status:_ ❌ **FAIL**
- _Total:_ 5000
- _Passed:_ 4960
- _Failed:_ 40
- _Skipped:_ 0
- _Started:_ 2026-10-29 19:24:57
- _Ended:_ 2026-10-29 19:25:04
- _Elapsed:_ 6.79 s
- _Messages:_ 40 FAIL

# Stats

## By Tag

| Name       | Total | Pass | Fail | Skip | Elapsed |
| ---------- | ----: | ---: | ---: | ---: | ------: |
| regression |  4500 | 4460 |   40 |    0 |  5.50 s |
| accounts   |  1000 |  992 |    8 |    0 |  1.19 s |
| catalog    |  1000 |  992 |    8 |    0 |  1.26 s |
| checkout   |  1000 |  992 |    8 |    0 |  1.21 s |
| payments   |  1000 |  992 |    8 |    0 |  1.18 s |
| shipping   |  1000 |  992 |    8 |    0 |  1.29 s |
| smoke      |   500 |  500 |    0 |    0 |  629 ms |
```

```console
$ robotcode results show --failed 2>&1 | sed -E 's/.*\) *//' | sort | uniq -c | sort -rn | head
     40   > Status of the item is done, expected failed
     40 _
      5 
      1 - _Total:_ 40
      1 ## Statistics
      1 - _Started:_ 2026-10-29 19:24:57
      1 - _Skipped:_ 0
      1 # Show — results/output.xml
      1 - _Passed:_ 0
      1 _Filters: status=fail_
```

<div class="rc-session-answer">

**Agent:** All five teams had failures in the last run, 8 each. Of the 5,000 tests, **4,960 passed and 40 failed** (run of 2026-10-29 19:24, `results/output.xml`).

| Team | Failed / Total |
|---|---|
| accounts | 8 / 1,000 |
| catalog | 8 / 1,000 |
| checkout | 8 / 1,000 |
| payments | 8 / 1,000 |
| shipping | 8 / 1,000 |

- **Only `regression` tests failed** (40 of 4,500). All 500 `smoke` tests passed.
- **All 40 failures have the same error:** `Status of the item is done, expected failed`. One message, split evenly across every team, points to a single shared cause rather than separate team-level bugs. I haven't dug into it yet.

The full report is in `results/log.html` and `results/report.html`.

</div>

</div>

</details>
<!-- /session -->
