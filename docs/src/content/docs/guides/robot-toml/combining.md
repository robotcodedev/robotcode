---
title: How Settings Combine
description: 'The rules by which RobotCode combines the configuration files, the selected profiles and the command line into the options of a run: replacing and extending, order, inheritance and detached profiles.'
sidebar:
  label: How Settings Combine
  order: 100.4
---

The options of a run come from several places: the configuration files, the selected profiles and the command line. This page collects the rules by which RobotCode combines them.

## The steps

1. **The files.** RobotCode reads the user configuration, `pyproject.toml`, `robot.toml` and `.robot.toml`, in this order, and combines them into one configuration; see [The order](/guides/robot-toml/files/#the-order).
2. **The settings outside of profiles** of this configuration are the start.
3. **The selected profiles** apply one after the other: those of `-p`, of `ROBOTCODE_PROFILES` or of the editor, or else the [default profiles](/guides/robot-toml/profiles/#default-profiles). Each profile comes after the profiles it inherits from. Profiles with a lower `precedence` come first; with the same precedence, the order of the selection counts. Disabled profiles are skipped.
4. **The command line** comes last: `robotcode run` passes its options and paths to Robot Framework after those of the configuration.

`robotcode profiles show` prints the result of the first three steps, and `robotcode -v run` the options that Robot Framework gets.

## Replacing and extending

In every step, the same two rules apply:

- **A setting replaces** the value before it.
- **A setting with `extend-` before its name adds** to the value before it. Lists get the new entries at the end; tables get the new keys, and a key that exists already gets the new value.

```toml title="robot.toml"
python-path = ["libraries"]
includes = ["smoke"]

[variables]
BROWSER = "chromium"
TIMEOUT = "10s"

[profiles.replace]
python-path = ["other"]

[profiles.replace.variables]
BROWSER = "firefox"

[profiles.extend]
extend-python-path = ["other"]
extend-includes = ["api"]

[profiles.extend.extend-variables]
BROWSER = "firefox"
```

| Setting | `-p replace` | `-p extend` |
| --- | --- | --- |
| `python-path` | `["other"]` | `["libraries", "other"]` |
| `includes` | `["smoke"]` | `["smoke", "api"]` |
| `variables` | `BROWSER = "firefox"` | `BROWSER = "firefox"`, `TIMEOUT = "10s"` |

`extend-` exists for the settings that take a list or a table. A setting with a single value, such as `output-dir`, can only be replaced.

### A setting and its `extend-` setting in the same place

A profile, or the settings outside of profiles in one file, can have both forms of a setting. Then the setting applies first and its `extend-` setting adds to it:

```toml title="robot.toml"
[variables]
BROWSER = "chromium"

[profiles.dev.variables]
BASE_URL = "http://localhost:8080"

[profiles.dev.extend-variables]
HEADLESS = "false"
```

With `-p dev`, the variables are `BASE_URL` and `HEADLESS`: `variables` replaces `BROWSER`, and `extend-variables` adds `HEADLESS`.

## Between the files

The rules above also apply between the files: a setting in `.robot.toml` replaces the one of `robot.toml`, and an `extend-` setting adds to it. For profiles, this means:

- `[profiles.<name>]` in a later file replaces all profiles of the earlier files.
- `[extend-profiles.<name>]` adds a profile, or changes the profile of that name: a setting replaces the one of the profile, and an `extend-` setting adds to it.

See [Changing profiles in a later file](/guides/robot-toml/profiles/#changing-profiles-in-a-later-file).

## Inheritance and detached profiles

- A profile that **inherits** from others applies after them, unless one of them has a higher `precedence`, so its settings replace or extend theirs; see [Inheritance](/guides/robot-toml/profiles/#inheritance).
- A **detached** profile throws away everything before it: the settings outside of profiles, from all files, and the profiles applied before it, including those it inherits from; only environment variables that an `env` before it has set stay set. Only the profiles after it add to it; see [Detached profiles](/guides/robot-toml/profiles/#detached-profiles).

## The command line

`robotcode run` passes the options of the configuration to Robot Framework first and the options of the command line after them, so Robot Framework treats them as one command line:

- **An option with a single value**, such as `-d` or `-L`, replaces the one of the configuration: `robotcode run -d out` writes the results to `out`.
- **An option that can be given several times**, such as `-i` or `-e`, adds to the configuration: with `includes = ["smoke"]`, `robotcode run -i api` runs the tests tagged `smoke` or `api`.
- **A variable** given with `-v` replaces one of the same name: `robotcode run -v BROWSER:firefox` runs in Firefox.
- **Paths** on the command line replace `paths`: `robotcode run tests/login.robot` runs only that file.

## Expressions and environment variables

RobotCode computes [expressions](/guides/robot-toml/settings/#expressions) after combining the settings, and sets the environment variables of `env` before, so an expression can read them with `environ`. Conditions in `enabled` are computed when a profile is about to apply.

## An example, step by step

With the files of the [example project](/guides/robot-toml/#an-example-project), `robotcode -p ci run` on a developer machine combines the settings like this:

| Step | `output-dir` | `BROWSER` | `HEADLESS` | `BASE_URL` |
| --- | --- | --- | --- | --- |
| User configuration | `results` | | | |
| `robot.toml` | `results` | `chromium` | `false` | `http://localhost:8080` |
| `.robot.toml` | `results` | `firefox` | `false` | `http://localhost:8080` |
| Profile `staging`, inherited by `ci` | `results` | `firefox` | `false` | `https://staging.shop.example` |
| Profile `ci` | `results/ci` | `firefox` | `true` | `https://staging.shop.example` |
