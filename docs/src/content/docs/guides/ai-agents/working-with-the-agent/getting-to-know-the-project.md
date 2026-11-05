---
title: Getting to Know the Project
description: "Step 1 of the tutorial: ask an AI agent what a Robot Framework project tests, which tests cover a requirement and what a keyword takes, have it try the keyword, and get to know the commands behind the answers."
sidebar:
  label: 1. Getting to Know the Project
  order: 150.41
---

Before you change anything, you want to know what the project contains. You don't have to read its files for that. An agent with the RobotCode skill can ask Robot Framework instead of guessing from the files. So start with a broad question, go on with narrower ones, and on the way get to know the commands behind the answers.

To follow along, use the [example project](/guides/ai-agents/working-with-the-agent/#following-along).

## Ask what is there

<div class="rc-session">

<div class="rc-session-prompt">

**You:** What does this project test, and how are the tests organized?

</div>

<div class="rc-session-calls">

- [`robotcode discover info`](/guides/cli/discovering-tests/#info--environment-and-version)
- [`robotcode discover all`](/guides/cli/discovering-tests/#all--the-full-tree)
- [`robotcode discover suites`](/guides/cli/discovering-tests/#suites--flat-list-of-suites)
- [`robotcode discover tags --tests`](/guides/cli/discovering-tests/#tags--tag--tests-dictionary)
- [`robotcode profiles list`](/reference/cli/#profiles)
- [`robotcode config show`](/reference/cli/#config)
- [`robotcode discover files`](/guides/cli/discovering-tests/#files--flat-list-of-source-files)

</div>

<div class="rc-session-answer">

**Agent:** This project is a Robot Framework acceptance test suite for a small demo web shop, with 13 tests covering login, cart, orders and product search. … I only inspected the tests and didn't run them, so I can't say whether they pass.

…

| Suite | File | Owner | Tests | What it checks |
|---|---|---|---|---|
| `Tests.Login` | `tests/login.robot` | Team Accounts | 3 | Login greeting, logout, wrong password refused |
| `Tests.Cart` | `tests/cart.robot` | Team Checkout | 3 | Adding and removing items, cart total |
| `Tests.Orders` | `tests/orders.robot` | Team Checkout | 3 | Ordering coffee, express orders, sold-out products can't be ordered |
| `Tests.Search` | `tests/search.robot` | Team Catalog | 4 | Finding products by name: one match, several matches, no match |

…

- **Smoke tests:** four tests are tagged `smoke`: Login Works, Logout Works, Add Item To Cart and Order Coffee.
- **Requirements:** login, cart and orders tests each name a requirement, such as `SHOP-101`. Search tests don't, which is also expected.

…

</div>

</div>

This is a summary, and it shows you where to look next. In it, look for names and numbers you can check, and for what the agent says it didn't do: here, it didn't run the tests. A summary can also get a detail wrong, so before you rely on a detail, ask about that detail.

## Ask about what you need

Now name the scope of your question, such as a requirement, a tag, a suite or a team:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which tests cover the cart requirements SHOP-201 to SHOP-203?

</div>

<div class="rc-session-answer">

**Agent:** Each of the three requirements is covered by exactly one test, all in `tests/cart.robot`:

| Requirement | Test | Location | Tags | Risk |
|---|---|---|---|---|
| SHOP-201 | `Tests.Cart.Add Item To Cart` | `tests/cart.robot:15` | `cart`, `smoke` | Not set |
| SHOP-202 | `Tests.Cart.Remove Item From Cart` | `tests/cart.robot:22` | `cart` | Not set |
| SHOP-203 | `Tests.Cart.Cart Total Adds Up` | `tests/cart.robot:29` | `cart` | High |

This comes from the `robotcode discover all` output earlier, which shows each test's `Requirement` metadata. It shows only that the tests are linked to these requirements, not that they fully check them. …

</div>

</div>

The last sentence matters. A test that names a requirement doesn't have to check it, and whether it does is a question of its own.

You can also ask about what is missing, which a search through the files doesn't find:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which tests don't name a requirement?

</div>

<div class="rc-session-answer">

**Agent:** The four tests in the search suite are the only ones that don't name a requirement:

| Test | Location |
|---|---|
| `Tests.Search.Find Coffee` | `tests/search.robot:11` |
| `Tests.Search.Find Tea` | `tests/search.robot:12` |
| `Tests.Search.Find Several` | `tests/search.robot:13` |
| `Tests.Search.Find Nothing` | `tests/search.robot:14` |

…

</div>

</div>

## Ask about a keyword, and try it

<div class="rc-session">

<div class="rc-session-prompt">

**You:** What arguments does our `Create Order` keyword take?

</div>

<div class="rc-session-answer">

**Agent:** `Create Order` in `resources/orders.resource:8` takes three arguments, and only `product` is required:

| Argument | Required | Default | Meaning |
|---|---|---|---|
| `${product}` | Yes | None | The product to order |
| `${quantity}` | No | `1` | How many items to order |
| `${express}` | No | `${False}` | Whether it's an express order |

It returns the new order's id and fails if the product is out of stock.

…

</div>

</div>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Try it out: what happens with a product that is sold out?

</div>

<div class="rc-session-calls">

- [`robotcode session list`](/guides/cli/sessions/)
- [`robotcode session start repl`](/guides/cli/sessions/#starting-a-session)
- [`robotcode session send repl-60348d3a 'Resource    shop.resource'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send repl-60348d3a 'Resource    orders.resource'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send repl-60348d3a 'Open Shop As    alice'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send repl-60348d3a 'Create Order    mug'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send repl-60348d3a 'Create Order    coffee    quantity=101'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session send repl-60348d3a 'Create Order    coffee'`](/guides/cli/sessions/#sending-an-input)
- [`robotcode session stop repl-60348d3a`](/guides/cli/sessions/#ending-a-session)

</div>

<div class="rc-session-answer">

**Agent:** The order is refused: `Create Order` fails with `mug is out of stock` and returns no order id. …

I tried this in an interactive session, logged in as `alice`:

| Call | Result |
|---|---|
| `Create Order    mug` | Fails: `mug is out of stock` |
| `Create Order    coffee    quantity=101` | Fails: `coffee is out of stock` |
| `Create Order    coffee` | Passes and returns `order-4711` |

- …
- **Unknown products:** these should also say "out of stock", because the check treats a missing product as having 0 in stock. I saw this in the code but didn't run it.

… I've stopped the session and it left no changes in the project.

</div>

</div>

"Try it out" is all it takes. The agent runs the keyword without writing a test, and the project stays as it was. In the answer, look for what it really ran and what it only read about: here, the point on unknown products comes from the code, and it says so.

## See how it found out

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which `robotcode` commands did you use to find all that out? I want to try them myself.

</div>

<div class="rc-session-answer">

**Agent:** I ran these from the project root. Most of the answers came from `discover` and the interactive session; I didn't use `robotcode doc`, `analyze` or `robot` at all.

…

```sh wrap
robotcode discover info        # Robot Framework, RobotCode and Python versions
robotcode discover all         # all suites and tests, with tags and metadata
robotcode discover suites      # suites only
robotcode discover tags --tests   # each tag and the tests that carry it
robotcode discover files       # the Robot files that were found
robotcode profiles list        # the dev and ci profiles
robotcode config show          # robot.toml as written
```

…

I used `robotcode session` because my shell can't type into a running program. You can start the shell directly:

```sh wrap
robotcode repl
```

…

- **`Create Order` arguments:** I read them in `resources/orders.resource`. To get them through RobotCode, which I haven't run, try:
  ```sh wrap
  robotcode doc keyword orders.resource "Create Order"
  ```

…

</div>

</div>

Run them. You see what the agent saw, and from now on, you can look at a project without the agent too.

Each command has its own documentation: [`robotcode discover`](/guides/cli/discovering-tests/), [`robotcode profiles`](/reference/cli/#profiles), [`robotcode config`](/reference/cli/#config), [`robotcode session`](/guides/cli/sessions/), [`robotcode repl`](/guides/cli/repl/) and [`robotcode doc`](/guides/cli/browsing-documentation/). Your agent may name other commands, such as [`robotcode discover metadata`](/guides/cli/discovering-tests/#metadata--metadata-index), and it will also tell you what it read in the files instead.

## In a large project

With thousands of tests, a list of every test fills the conversation and tells you little. Ask for counts first, and go on from there:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** How many tests does this project have, and how are they split across the teams?

</div>

</div>

The example project is too small for this, so try it in your own. If a team could be a folder, a tag or metadata in your project, say which one you mean, or the agent picks one.

## In your own project

- Start with a broad question, then name the scope: a requirement, a tag, a suite or a team.
- Ask about what is missing too, not only about what is there.
- Say *"Try it out"* to see a keyword run without a test being written.
- With many tests, ask for counts before lists.
- Ask for the commands, and run them yourself.
- A test can only name a requirement with `[Metadata]` from Robot Framework 7.5. With an older version, mark what a test covers with a tag, and ask by tag.
