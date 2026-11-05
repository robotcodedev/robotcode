---
title: A Profile for the CI Server
description: "Step 7 of the tutorial: tell an AI agent what the CI server needs, look at the profile it writes in robot.toml, check what a run with it gets without running the tests, and ask what the profile replaces."
sidebar:
  label: 7. A Profile for the CI Server
  order: 150.47
---

A CI server runs your tests with other settings than you do: another system, a browser without a window, another folder for the results. A profile in `robot.toml` holds those settings. Tell the agent what the server needs, in your own words. You don't have to know the settings. Then have it show you the result, and check it before the first CI run.

To follow along, use the [example project](/guides/ai-agents/working-with-the-agent/#following-along).

## Say what the server needs

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Add a profile for our CI server: the staging shop, a browser without a window, and the results in `results/ci`.

</div>

<div class="rc-session-calls">

- [`robotcode profiles list`](/reference/cli/#profiles)
- [`robotcode config info desc output-dir`](/reference/cli/#desc)
- [`robotcode -p ci profiles show`](/reference/cli/#profiles)

</div>

<div class="rc-session-answer">

**Agent:** I updated the existing `ci` profile in `robot.toml`. `robotcode -p ci profiles show` loads it without errors. I haven't run any tests with it.

- **Staging shop:** `BASE_URL` was already set to `https://staging.shop.example`, so I left it.
- **Results:** `output-dir = "results/ci"`.
- **Windowless browser:** I added `HEADLESS = "True"` to the profile's variables. The value is quoted because `robot.toml` only accepts strings for variables.

Nothing reads `HEADLESS` yet. No test or resource in the project opens a browser. When one does, it has to pass `headless=${HEADLESS}` to `New Browser`. Without that, the CI browser will still open a window.

…

</div>

</div>

You asked for a new profile, and the agent extended the one that exists, because the project's CI workflow already runs it. That's the right call here, and it's the kind of decision you want to see in the answer. Check as well whether it changed anything besides `robot.toml`.

## Look at the result

Don't stop at a description of the change. Have the agent show you the profile, and what a run gets from it:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Show me the profile, and what a run with it gets, without running the tests.

</div>

<div class="rc-session-calls">

- [`robotcode -p ci profiles show`](/reference/cli/#profiles)
- [`robotcode -p ci discover tests`](/guides/cli/discovering-tests/#tests--flat-list-of-tests)

</div>

<div class="rc-session-answer">

**Agent:** **The profile** (`robot.toml`):

```toml wrap
[profiles.ci]
description = "Staging shop, headless browser, results in results/ci"
output-dir = "results/ci"

[profiles.ci.extend-variables]
BASE_URL = "https://staging.shop.example"
HEADLESS = "True"
```

**What a run gets** (`robotcode -p ci profiles show`):

- `output-dir = "results/ci"`
- `python-path = ["libraries", "resources"]`
- `paths = ["tests"]`
- Variables:
  - `BASE_URL = "https://staging.shop.example"`
  - `BROWSER = "chromium"`
  - `HEADLESS = "True"`

**Tests it would run** (`robotcode -p ci discover tests`): 13 tests in 4 suites, Cart (3), Login (3), Orders (3) and Search (4). I didn't filter by tag.

…

</div>

</div>

These commands are documented at [`robotcode profiles show`](/reference/cli/#profiles) and [`robotcode discover tests`](/guides/cli/discovering-tests/#tests--flat-list-of-tests). "Without running the tests" matters here: you learn what the profile does before anything runs.

## Ask what it replaces

A plain setting in a profile replaces the one outside of it, and one with `extend-` before its name adds to it. A profile that replaces too much can lose settings without any error, so ask:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which of these settings replace those in `robot.toml`, and which add to them?

</div>

<div class="rc-session-answer">

**Agent:** In a profile, a plain key replaces the base value, and an `extend-` key merges into it.

| Setting in `ci` | Effect |
| --- | --- |
| `output-dir = "results/ci"` | **Replaces** the base `output-dir = "results"`. |
| `extend-variables.BASE_URL` | **Adds to** the base `[variables]`. This key already exists there, so the profile's value wins: `https://staging.shop.example` instead of `http://localhost:8080`. |
| `extend-variables.HEADLESS` | **Adds to** the base `[variables]`. It's a new key. |
| `description` | Only describes the profile. |

The settings the profile doesn't mention come through unchanged: `paths`, `python-path` and `BROWSER = "chromium"`. The `profiles show` output above confirms this.

If I had written `[profiles.ci.variables]` instead of `extend-variables`, the profile's table would have replaced the whole base `[variables]`. `BROWSER` would then have been lost. That's why the profile uses `extend-variables`.

</div>

</div>

[Profiles](/guides/robot-toml/profiles/) explains this and what else a profile can do.

## Ask whether anything uses it

A setting only counts if something uses it, and the agent has already said that this one has no effect yet. If it hadn't, you would want to ask:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Does anything use the setting for the browser without a window yet?

</div>

<div class="rc-session-answer">

**Agent:** No, nothing uses it. A search of the project (excluding `.venv`, `.git` and `uv.lock`) finds `HEADLESS` only in `robot.toml`.

The search also finds no `New Browser`, `New Context` or `New Page` call anywhere, so no test or resource opens a browser. …

When you add the first keyword that opens a browser, it has to pass the setting itself, for example `New Browser    ${BROWSER}    headless=${HEADLESS}`. The profile already supplies the value, but the keyword has to use it.

</div>

</div>

## See how it checked

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which `robotcode` commands did you use to check the profile? I want to run them myself.

</div>

<div class="rc-session-answer">

**Agent:** Run these from the project root:

```bash wrap
robotcode profiles list            # the profiles that exist
robotcode -p ci profiles show      # what is in effect with ci applied
robotcode -p ci discover tests     # which tests a ci run would pick up
robotcode config info desc output-dir   # docs for a setting
```

Put `-p ci` before the subcommand, as in `robotcode -p ci profiles show`. It's a global option. `profiles list` and `config info desc` need no profile.

- `profiles show` is the one that confirmed the merge. It prints the result after the `extend-` keys are applied, so you see `output-dir`, the variables and the paths as a run would.
- `robotcode config show` prints the config as written, with the files merged but no profile applied. Compare it with `profiles show` to see what `ci` changes.
- The first `profiles show` failed with an error: `HEADLESS = true` had to be a string. That's the validation you get for free.

…

</div>

</div>

Run them. Besides the commands above, [`robotcode config info desc`](/reference/cli/#desc) and [`robotcode config show`](/reference/cli/#config) are in the reference, and the [`robot.toml` reference](/reference/config/) lists every setting. Your agent may name other commands, such as [`robotcode config info list`](/reference/cli/#info).

## In your own project

- Say what the server needs in your own words, and let the agent find the settings.
- Look at the resulting profile and at what a run gets from it, before the first CI run.
- Ask what the profile replaces and what it adds to.
- Ask whether anything uses a new setting.
- Ask for the commands, and run them yourself.
