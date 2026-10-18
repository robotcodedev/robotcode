---
title: Recipes
description: 'Ready-made robot.toml configurations: the same command locally and on a CI server, browsers as profiles, smoke tests and dry runs, a results folder per run, secrets, settings per operating system, a debug profile and test files in another language.'
sidebar:
  label: Recipes
  order: 100.6
---

## The same command locally and on the CI server

Two profiles in `default-profiles`, each with a condition, let `robotcode run` do the right thing on a developer machine and on the CI server, without a `-p`. GitHub Actions and GitLab CI, for example, set the environment variable `CI`:

```toml title="robot.toml"
default-profiles = ["local", "ci"]

[profiles.local]
description = "Developer machine"
enabled = { if = "'CI' not in environ" }

[profiles.local.extend-variables]
BASE_URL = "http://localhost:8080"

[profiles.ci]
description = "CI server"
enabled = { if = "'CI' in environ" }
output-dir = "results/ci"

[profiles.ci.extend-variables]
BASE_URL = "https://staging.shop.example"
HEADLESS = "true"
```

On a developer machine, `ci` is disabled and only `local` applies; on the CI server, it is the other way round.

## Browsers as profiles

Profiles for the browsers combine with the profiles for the environments, so you don't need a profile for every pair:

```toml title="robot.toml"
[variables]
BROWSER = "chromium"

[profiles.staging.extend-variables]
BASE_URL = "https://staging.shop.example"

[profiles.firefox]
description = "Firefox"

[profiles.firefox.extend-variables]
BROWSER = "firefox"

[profiles.webkit]
description = "WebKit"

[profiles.webkit.extend-variables]
BROWSER = "webkit"
```

`robotcode -p staging -p firefox run` runs against the staging shop in Firefox. In VS Code and PyCharm, select both profiles in **Select Configuration Profiles**.

## Smoke tests and dry runs

```toml title="robot.toml"
[profiles.smoke]
description = "Only the smoke tests"
extend-includes = ["smoke"]

[profiles.check]
description = "Check the tests without running them"
dry-run = true
```

`robotcode -p smoke run` runs the tests tagged `smoke`, and `robotcode -p check run` checks all tests for syntax errors and missing keywords without running them. In the Test Explorer of VS Code, both are offered as run profiles, so a click runs the selected tests that way; in PyCharm, **Run with Profile...** does the same.

## A results folder per run

```toml title="robot.toml"
output-dir = { expr = "f'results/{datetime.now():%Y-%m-%d_%H-%M-%S}'" }
```

Each run writes its results to a folder of its own, such as `results/2026-10-18_14-30-05`, and the results of earlier runs stay.

## Secrets

Passwords and tokens do not belong in a committed `robot.toml`. On a developer machine, keep them in your `.robot.toml`, which is not committed:

```toml title=".robot.toml"
[extend-env]
SHOP_USER = "jane"
SHOP_PASSWORD = "secret"
```

On the CI server, let the CI system set them as environment variables. The tests read them with `%{SHOP_USER}` and `%{SHOP_PASSWORD}` in both cases.

## Settings per operating system

```toml title="robot.toml"
default-profiles = ["os-*"]

[profiles.os-windows]
enabled = { if = "platform.system() == 'Windows'" }
hidden = true

[profiles.os-windows.extend-variables]
DRIVER_PATH = "C:\\drivers"

[profiles.os-linux]
enabled = { if = "platform.system() == 'Linux'" }
hidden = true

[profiles.os-linux.extend-variables]
DRIVER_PATH = "/usr/local/bin"

[profiles.os-macos]
enabled = { if = "platform.system() == 'Darwin'" }
hidden = true

[profiles.os-macos.extend-variables]
DRIVER_PATH = "/opt/homebrew/bin"
```

`default-profiles` takes patterns, as `-p` does, so `os-*` selects all three profiles, and only the one of the current system applies. The profiles are hidden, because nobody needs to select them on their own. A selection with `-p` replaces the default profiles, so add the pattern when you select other profiles: `robotcode -p staging -p "os-*" run`.

## A profile for debugging

```toml title="robot.toml"
[profiles.debug]
description = "Detailed log"
precedence = 100
log-level = "TRACE"
console = "verbose"
```

`robotcode -p ci -p debug run` runs as on the CI server, but with a detailed log. The high precedence makes `debug` win, whatever order you select the profiles in.

## Test files in another language

```toml title="robot.toml"
languages = ["de"]
```

Robot Framework then reads section headers and settings in German, such as `*** Testfälle ***`, in all files, and RobotCode's analysis and completion do the same.
