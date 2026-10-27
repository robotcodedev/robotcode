---
title: robot.toml on the Command Line
description: 'Running tests with robot.toml on the command line: where the options go, commands for everyday tasks, environment variables for CI servers, and checking what a run gets.'
sidebar:
  label: On the Command Line
  order: 100.5
---

On the command line, `robotcode run` runs the tests with the configuration of `robot.toml`. It needs RobotCode's runner in the environment of your project, for example installed with `pip install "robotcode[runner]"`.

## Where the options go

```text
robotcode [options of robotcode] run [options of Robot Framework] [paths]
```

- **Before `run`** come the options of `robotcode` itself: `-p` selects profiles, `-c` other configuration files, `-r` the project root, and `-v` makes RobotCode tell what it does.
- **After `run`** come the options of Robot Framework, as you would give them to `robot`, and the paths of the tests.

The place matters: `robotcode -v run` makes RobotCode verbose, `robotcode run -v BROWSER:firefox` sets a variable. `robotcode run -- --help` shows the options of Robot Framework, and `robotcode --help` and `robotcode run --help` those of RobotCode.

## Everyday tasks

| Task | Command |
| --- | --- |
| Run the tests of `paths` | `robotcode run` |
| Run with a profile | `robotcode -p staging run` |
| Run with several profiles | `robotcode -p staging -p firefox run` |
| Run with all profiles whose names match a pattern | `robotcode -p "browser-*" run` |
| Run only the tests with a tag | `robotcode run -i smoke` |
| Leave out the tests with a tag | `robotcode run -e slow` |
| Run one file or folder | `robotcode run tests/orders.robot` |
| Run one test | `robotcode run -t "Order Coffee"` |
| Run with another value of a variable | `robotcode run -v BROWSER:firefox` |
| Write the results somewhere else | `robotcode run -d results/try` |
| Check the tests without running them | `robotcode run --dryrun` |
| List the tests that a run would run | `robotcode -p staging discover tests` |
| Show the settings a run gets | `robotcode -p staging profiles show` |
| Show the options passed to Robot Framework | `robotcode -v -p staging run` |
| Use another configuration file | `robotcode -c release.toml run` |
| Run a project from outside its folder | `robotcode run web/tests`, or `robotcode -r web run` |

Options on the command line come on top of the configuration: one with a single value, such as `-d`, replaces the configured one, and one that can be given several times, such as `-i`, adds to the configured ones. Paths on the command line replace `paths`. See [The command line](/guides/robot-toml/combining/#the-command-line).

`robotcode robot` is the same command as `robotcode run`. Other commands read the configuration the same way, for example `robotcode -p staging discover tests`, `robotcode -p staging analyze code` or `robotcode -p staging repl`.

## On a CI server

On a CI server, select the profile on the command line, or with the environment variable `ROBOTCODE_PROFILES`, which the CI configuration can set for all steps:

```bash
robotcode -p ci run
```

```bash
export ROBOTCODE_PROFILES="ci"
robotcode run
```

The other options of `robotcode` have environment variables too: `ROBOTCODE_CONFIG_FILES` for `-c` and `ROBOTCODE_ROOT` for `-r`. With conditions on environment variables that the CI server sets, a profile can also switch itself on, without any option; see [The same command locally and on the CI server](/guides/robot-toml/recipes/#the-same-command-locally-and-on-the-ci-server).

## Checking what a run gets

| Command | What it shows |
| --- | --- |
| `robotcode -p ci profiles show` | The settings that a run gets with the selected profiles, with the expressions computed. `-n` shows the expressions instead. |
| `robotcode profiles list` | The profiles, with their descriptions, which of them are selected and, of these, which are enabled. `-h` includes hidden profiles. |
| `robotcode config show` | The settings of all files together, before any profile applies. `-s` shows each file on its own. |
| `robotcode config files` | The configuration files that RobotCode reads, in order. |
| `robotcode config root` | The project root and what it was found by. |
| `robotcode -v -p ci run` | Which files RobotCode reads, which profiles it uses or skips, and the options it passes to Robot Framework. |

[Troubleshooting](/guides/robot-toml/troubleshooting/) explains what to look for when a setting does not do what you expect.
