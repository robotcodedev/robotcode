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

For the three cart requirements, the agent asked for the metadata of the tests. From the session *Coverage*:

<!-- excerpt: coverage -->
```console
$ robotcode discover metadata --values --tests --search-regex 'SHOP-20[0-9]' ; echo "---exit $?"; robotcode discover metadata --values --tests; echo "---"; ls requirements/
# Metadata

## Tests and Tasks

- **Requirement**
  - `SHOP-201`
    - **Tests.Cart.Add Item To Cart** (`tests/cart.robot:15`)
  - `SHOP-202`
    - **Tests.Cart.Remove Item From Cart** (`tests/cart.robot:22`)
  - `SHOP-203`
    - **Tests.Cart.Cart Total Adds Up** (`tests/cart.robot:29`)
…
```

`robotcode discover metadata --values --tests` lists every metadata value with the tests that carry it. Each test has its long name, such as `Tests.Cart.Add Item To Cart`: the names of its suites, then its own. Asked which tests name no requirement, the agent compared this list with all tests from `robotcode discover tests` and found the four tests of the search suite.

### It looks keywords up where they are installed

`robotcode doc` loads a library or a resource in the project's environment, with `robot.toml`, the profiles and the variables. So it shows the keywords of the versions you have installed, and also those of your own resources and Python libraries. The skill puts it first, before the existing tests and before external documentation. From the session *Keywords*:

<!-- excerpt: keywords -->
```console
$ robotcode doc keyword resources/orders.resource "Create Order" 2>&1; echo ------; cat resources/orders.resource
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

In a project with thousands of tests, a list of every test would fill the chat and tell you little. The skill tells the agent to filter or aggregate before it lists. In the session *A large project*, it asked for the suites and the tags without listing their tests, counted the tests of each team's tag and, for the last run, asked for statistics by tag:

<!-- excerpt: a-large-project -->
```console
…
## By Tag

| Name       | Total | Pass | Fail | Skip | Elapsed |
| ---------- | ----: | ---: | ---: | ---: | ------: |
| regression |  4500 | 4460 |   40 |    0 |  5.62 s |
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
$ robotcode discover metadata --values --tests --search-regex 'SHOP-20[0-9]' ; echo "---exit $?"; robotcode discover metadata --values --tests; echo "---"; ls requirements/
# Metadata

## Tests and Tasks

- **Requirement**
  - `SHOP-201`
    - **Tests.Cart.Add Item To Cart** (`tests/cart.robot:15`)
  - `SHOP-202`
    - **Tests.Cart.Remove Item From Cart** (`tests/cart.robot:22`)
  - `SHOP-203`
    - **Tests.Cart.Cart Total Adds Up** (`tests/cart.robot:29`)
- **Risk**
  - high
    - **Tests.Cart.Cart Total Adds Up** (`tests/cart.robot:29`)

## Suites

- **Application**
  - Demo web shop
- **Browser**
  - ${BROWSER}
- **Owner**
  - Team Checkout
- **Shop URL**
  - ${BASE_URL}

## Statistics

- _Suites:_ 2
- _Suites with tests:_ 1
- _Tests:_ 3

_Filters: search-regex=SHOP-20\[0-9\]_
…
---
SHOP-110.md
```

<div class="rc-session-answer">

**Agent:** Each cart requirement is covered by exactly one test, all in `tests/cart.robot`:

| Requirement | Test | Location | Risk |
|---|---|---|---|
| SHOP-201 | Add Item To Cart | `tests/cart.robot:15` | not set |
| SHOP-202 | Remove Item From Cart | `tests/cart.robot:22` | not set |
| SHOP-203 | Cart Total Adds Up | `tests/cart.robot:29` | high |

This comes from each test's `[Metadata]    Requirement` tag, as resolved by `robotcode discover`. It shows which test claims which requirement, but I didn't check that the test steps actually verify it. I also didn't run the tests.

`requirements/` contains only `SHOP-110.md`, so these three requirements have no files there to compare the tests against. No test claims SHOP-110 either.

</div>

<div class="rc-session-prompt">

**You:** Which tests don't name a requirement?

</div>

```console
$ robotcode discover tests; echo "---"; robotcode discover suites
# Tests

- **Tests.Cart.Add Item To Cart** (`tests/cart.robot:15`)
- **Tests.Cart.Remove Item From Cart** (`tests/cart.robot:22`)
- **Tests.Cart.Cart Total Adds Up** (`tests/cart.robot:29`)
- **Tests.Login.Login Works** (`tests/login.robot:11`)
- **Tests.Login.Logout Works** (`tests/login.robot:18`)
- **Tests.Login.Login With A Wrong Password Fails** (`tests/login.robot:26`)
- **Tests.Orders.Order Coffee** (`tests/orders.robot:14`)
- **Tests.Orders.Express Order** (`tests/orders.robot:21`)
- **Tests.Orders.Sold Out Product Cannot Be Ordered** (`tests/orders.robot:27`)
- **Tests.Search.Find Coffee** (`tests/search.robot:11`)
- **Tests.Search.Find Tea** (`tests/search.robot:12`)
- **Tests.Search.Find Several** (`tests/search.robot:13`)
- **Tests.Search.Find Nothing** (`tests/search.robot:14`)

## Statistics

- _Suites:_ 5
- _Suites with tests:_ 4
- _Tests:_ 13

…
```

<div class="rc-session-answer">

**Agent:** The four tests in the search suite don't name a requirement:

| Test | Location |
|---|---|
| Find Coffee | `tests/search.robot:11` |
| Find Tea | `tests/search.robot:12` |
| Find Several | `tests/search.robot:13` |
| Find Nothing | `tests/search.robot:14` |

The other nine of the 13 tests each name one requirement. This matches `AGENTS.md`, which only asks the login, cart and orders tests to name a requirement, so these four don't break the convention.

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
$ ls resources libraries; for t in resources/*.resource libraries/ShopLibrary.py; do echo "== $t"; robotcode doc keywords "$t" "Create Order" 2>&1 | head -30; done
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
# Resource *orders*

- **Create Order** `(product, quantity = 1, express = ${False})` — Creates an order for `quantity` items of `product` and returns its id.
== resources/shop.resource
# Resource *shop*

_(no keyword matches)_
== libraries/ShopLibrary.py
# Library *ShopLibrary*

_(no keyword matches)_
```

<div class="rc-session-answer">

**Agent:** `Create Order` is defined in `resources/orders.resource` and takes three arguments:

| Argument | Default | Required |
|---|---|---|
| `product` | none | yes |
| `quantity` | `1` | no |
| `express` | `${False}` | no |

It creates an order for `quantity` items of `product` and returns the order's id.

</div>

<div class="rc-session-prompt">

**You:** And what does it do to place the order?

</div>

```console
$ robotcode doc keyword resources/orders.resource "Create Order" 2>&1; echo ------; cat resources/orders.resource
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
------
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
    RETURN    ${id}

Order Status Should Be
    [Documentation]    Checks the status of ``order``: ``placed`` or ``express``.
    [Arguments]    ${order}    ${expected}
    ${status}=    Order Status    ${order}
    Should Be Equal    ${status}    ${expected}

Submit Order
    [Documentation]    Submits ``order`` for delivery.
    [Arguments]    ${order}
    Log    Submitted ${order}

Checkout
    [Documentation]    Checks ``order`` out and submits it.
    [Arguments]    ${order}
    Submit Ordr    ${order}
```

```console
$ robotcode doc keyword libraries/ShopLibrary.py "Place Order" 2>&1; echo ------; grep -n "def place_order" -A25 libraries/ShopLibrary.py
### Keyword *Place Order*

#### Arguments: 

| | | | |
|:--|:--|:--|:--|
| `product`| : `str` |  |  |
| `quantity`| : `int` | = | `${1}` |
| `express`| : `bool` | = | `${False}` |

**Return Type**: `str`


#### Documentation:
Places an order and returns its id. Fails if `product` is out of stock.
…
73:    def place_order(self, product: str, quantity: int = 1, express: bool = False) -> str:
74-        """Places an order and returns its id. Fails if ``product`` is out of stock."""
75-        if self._stock.get(product, 0) < quantity:
76-            raise AssertionError(f"{product} is out of stock")
77-        self._stock[product] -= quantity
78-        order = f"order-{4711 + len(self._orders)}"
79-        self._orders[order] = "express" if express else "placed"
80-        return order
81-
82-    @keyword
83-    def order_status(self, order: str) -> str:
84-        """Returns the status of ``order``: ``placed`` or ``express``."""
85-        return self._orders[order]
86-
87-    @keyword
88-    def search_products(self, text: str) -> list[str]:
89-        """Returns the products whose name contains ``text``."""
90-        return sorted(product for product in PRICES if text in product)
```

<div class="rc-session-answer">

**Agent:** `Create Order` doesn't place the order itself. It logs the request and hands off to the `Place Order` keyword from `libraries/ShopLibrary.py`:

```robotframework
Log    Ordered ${quantity} x ${product} (express: ${express})
${id}=    Place Order    ${product}    ${quantity}    ${express}
RETURN    ${id}
```

`Place Order` (`libraries/ShopLibrary.py:73`) then does the following in the in-memory shop:

1. **Checks stock:** if there's less stock than `quantity`, it fails with `<product> is out of stock`. An unknown product counts as zero stock, so it fails the same way.
2. **Reduces stock:** it subtracts `quantity` from the product's stock.
3. **Creates the id:** the id is `order-<4711 + number of existing orders>`, so the first order is `order-4711`.
4. **Records the status:** the order's status is `express` if `express` is true, otherwise `placed`.
5. **Returns the id:** `Create Order` passes it back to the caller.

No payment or delivery step happens here, and the order is only marked `placed` or `express`.

While reading the same file, I noticed that `Checkout` in `resources/orders.resource` calls `Submit Ordr`, which looks like a typo for `Submit Order`. No keyword I saw in that file has that name, so `Checkout` would probably fail when run, though I haven't run it.

</div>

<div class="rc-session-prompt">

**You:** Try it out — what happens with a product that is sold out?

</div>

*…*

```console
$ robotcode session list; robotcode session start repl
No session is open.
Started session repl-4a611478.
```

```console
$ robotcode session send repl-4a611478 'Import Resource    ${CURDIR}/resources/orders.resource'; echo "exit=$?"
exit=0
```

```console
$ robotcode session send repl-4a611478 '${id}=    Create Order    mug'; echo "exit=$?"
[ INFO ] Ordered 1 x mug (express: False)
[ FAIL ] mug is out of stock
exit=1
```

```console
$ robotcode session send repl-4a611478 '.vars --user'; echo "exit=$?"
  ${BASE_URL}  'http://localhost:8080'
  ${BROWSER}   'chromium'
exit=0
```

```console
$ robotcode session stop repl-4a611478; echo "exit=$?"; git status --short
exit=0
```

<div class="rc-session-answer">

**Agent:** `Create Order` fails when the product is sold out. I tried it in a REPL session with `mug`, the only product with zero stock in `ShopLibrary`:

```
>>> ${id}=    Create Order    mug
[ INFO ] Ordered 1 x mug (express: False)
[ FAIL ] mug is out of stock
```

- **The failure:** the keyword fails with `mug is out of stock`, which would fail a test unless it's handled.
- **No order id:** `${id}` was never set, as it's missing from the session's variables afterwards.
- **Misleading log line:** `Ordered 1 x mug` still appears because `Create Order` logs it before calling `Place Order`. A log can therefore say "Ordered" for an order that was never placed.

To test this case on purpose, wrap the call so the failure is the expected result:

```robotframework
Run Keyword And Expect Error    mug is out of stock    Create Order    mug
```

I didn't run that line, and the session has been stopped. No project files changed.

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
$ command -v robotcode; robotcode profiles list 2>&1 | head -20; robotcode discover suites 2>&1 | tail -30; robotcode discover tags 2>&1 | tail -30; for t in accounts catalog checkout payments shipping smoke regression; do echo "== $t"; robotcode discover tests -i $t 2>&1 | tail -4; done
~/shop-platform/.venv/bin/robotcode
No profiles defined.
…
## Statistics

- _Suites:_ 506
- _Suites with tests:_ 500
- _Tests:_ 5000

# Tags

- **accounts**
- **catalog**
- **checkout**
- **payments**
- **regression**
- **shipping**
- **smoke**

## Statistics

- _Suites:_ 506
- _Suites with tests:_ 500
- _Tests:_ 5000

== accounts
- _Suites:_ 102
- _Suites with tests:_ 100
- _Tests:_ 1000

== catalog
- _Suites:_ 102
- _Suites with tests:_ 100
- _Tests:_ 1000

== checkout
- _Suites:_ 102
- _Suites with tests:_ 100
- _Tests:_ 1000

== payments
- _Suites:_ 102
- _Suites with tests:_ 100
- _Tests:_ 1000

== shipping
- _Suites:_ 102
- _Suites with tests:_ 100
- _Tests:_ 1000

== smoke
- _Suites:_ 506
- _Suites with tests:_ 500
- _Tests:_ 500

== regression
- _Suites:_ 506
- _Suites with tests:_ 500
- _Tests:_ 4500
```

*…*

<div class="rc-session-answer">

**Agent:** The project has **5,000 tests** in 500 suites, split evenly across the five teams:

| Team | Tests | Suites |
|---|---:|---:|
| accounts | 1,000 | 100 |
| catalog | 1,000 | 100 |
| checkout | 1,000 | 100 |
| payments | 1,000 | 100 |
| shipping | 1,000 | 100 |

Across all teams, 500 tests are tagged `smoke` and 4,500 `regression`.

These counts come from `robotcode discover`, filtered by team tag, so nothing was run. I didn't separately compare the tags against the `tests/` folders. However, the five team counts add up to exactly 5,000, so no test can be missing a team tag or carrying two.

</div>

<div class="rc-session-prompt">

**You:** Which teams had failures in the last run, and how many?

</div>

*…*

```console
$ robotcode results summary 2>&1 | tail -20; echo ----; robotcode results stats --by tag --sort failed 2>&1 | tail -30
# Summary — results/output.xml

- _Status:_ ❌ **FAIL**
- _Total:_ 5000
- _Passed:_ 4960
- _Failed:_ 40
- _Skipped:_ 0
- _Started:_ 2026-11-03 22:26:12
- _Ended:_ 2026-11-03 22:26:19
- _Elapsed:_ 6.96 s
- _Messages:_ 40 FAIL

----
# Stats

## By Tag

| Name       | Total | Pass | Fail | Skip | Elapsed |
| ---------- | ----: | ---: | ---: | ---: | ------: |
| regression |  4500 | 4460 |   40 |    0 |  5.62 s |
| accounts   |  1000 |  992 |    8 |    0 |  1.19 s |
| catalog    |  1000 |  992 |    8 |    0 |  1.34 s |
| checkout   |  1000 |  992 |    8 |    0 |  1.21 s |
| payments   |  1000 |  992 |    8 |    0 |  1.18 s |
| shipping   |  1000 |  992 |    8 |    0 |  1.34 s |
| smoke      |   500 |  500 |    0 |    0 |  636 ms |
```

<div class="rc-session-answer">

**Agent:** All five teams had failures in the last run, with **8 failed tests each**. That's 40 failures out of 5,000 tests, and the other 4,960 passed.

| Team | Failed | Passed |
|---|---:|---:|
| accounts | 8 | 992 |
| catalog | 8 | 992 |
| checkout | 8 | 992 |
| payments | 8 | 992 |
| shipping | 8 | 992 |

All 40 failures are `regression` tests; all 500 `smoke` tests passed. The run started today at 22:26:12.

I haven't looked at why the tests failed. An identical count in every team could point to a shared cause, so I can check the failure messages next if you'd like.

The full report is in `results/report.html`, and the detailed log is in `results/log.html`.

</div>

</div>

</details>
<!-- /session -->
