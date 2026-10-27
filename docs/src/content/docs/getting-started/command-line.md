---
title: Get Started on the Command Line
description: 'Install the robotcode commands into the Python environment of your project with pip or uv, choose the packages for your tasks, then list and run a first test.'
sidebar:
  label: Command Line
  order: 25
---

The `robotcode` command works with your Robot Framework project in the terminal, in CI pipelines and in scripts: it runs the tests, lists what a run would pick up, checks the code and shows the results of a run. It reads the same `robot.toml` as RobotCode in VS Code and PyCharm. This page installs it into your project and runs a first test with it. Editors other than VS Code and PyCharm use RobotCode's language server; see [Neovim](/getting-started/neovim/).

## Choosing the packages

RobotCode comes as the package `robotcode` with extras, one for each group of commands. Install the extras for the commands you need:

| Package | Commands | For |
| --- | --- | --- |
| `robotcode` | `config`, `profiles` | Showing the configuration and the profiles of the project; every extra includes it |
| `robotcode[runner]` | `robot` (or `run`), `rebot`, `libdoc`, `testdoc`, `discover`, `results` | Running tests, listing them and reading the results of a run, for example in a CI pipeline |
| `robotcode[analyze]` | `analyze` | Checking the code for problems |
| `robotcode[repl]` | `repl`, `robot-debug`, `doc`, and the commands of `runner` | Trying keywords, debugging in the terminal and reading the documentation of libraries |
| `robotcode[debugger]` | `debug`, and the commands of `runner` | Debugging from a client of the Debug Adapter Protocol, such as an editor |
| `robotcode[languageserver]` | `language-server`, and `analyze` | Editors that connect to RobotCode's language server |
| `robotcode[all]` | All of them, with Robocop and the optional packages PyYAML and docutils | Everything |

The VS Code extension and the PyCharm plugin bring their own copy of these packages; you install them for the command line, for CI pipelines and for other editors.

## Installing RobotCode

Install the packages into the Python environment of your project, the one with Robot Framework and your libraries: the commands run Robot Framework from that environment. RobotCode needs Python 3.10 or newer with Robot Framework 5.0 or newer.

With pip, in the activated environment:

```bash
pip install "robotcode[runner]"
```

With uv, add it to a project that uv manages, or install it into an environment with uv's pip interface:

```bash
uv add "robotcode[runner]"          # in a project that uv manages
uv pip install "robotcode[runner]"  # in an environment
```

To install several extras, separate them with commas, for example `"robotcode[runner,analyze]"`. In a project that uv manages, `uv run` runs a command in the project's environment, for example `uv run robotcode --version`.

Check the installation:

```bash
robotcode --version
```

It prints the installed version, for example `robotcode, version 2.8.0`. `robotcode --help` lists the commands of the installed packages.

## Listing your tests

Create a folder `tests` in your project with a file `first.robot`:

```robot title="tests/first.robot"
*** Test Cases ***
First Test Case
    Log    Hello world
```

`robotcode discover all` lists the suites and tests that Robot Framework would run, without running them:

```bash
robotcode discover all tests
```

```text
# All

- **Tests** (`tests`)
  - **Tests.First** (`tests/first.robot`)
    - **Tests.First.First Test Case** (`tests/first.robot:2`)

## Statistics

- _Suites:_ 2
- _Suites with tests:_ 1
- _Tests:_ 1
```

## Running your first test

```bash
robotcode run tests
```

`robotcode run` is short for `robotcode robot`. It runs Robot Framework with the configuration of your project; the options of Robot Framework go after `run`, as they would after `robot`. Robot Framework writes `output.xml`, `log.html` and `report.html` to the folder `results`, the output folder that RobotCode's [user configuration](/guides/robot-toml/files/#the-user-configuration) sets by default for projects without one of their own.

`robotcode results` reads the results of the last run without running the tests again:

```bash
robotcode results summary
```

```text
# Summary — results/output.xml

- _Status:_ ✅ **PASS**
- _Total:_ 1
- _Passed:_ 1
- _Failed:_ 0
- _Skipped:_ 0
- _Started:_ 2026-10-27 18:42:29
- _Ended:_ 2026-10-27 18:42:29
- _Elapsed:_ 12 ms
```

`robotcode results show` lists the tests of the run, with the failure message of each test that failed.

## Next steps

- A `robot.toml` with the paths of your tests lets you leave out `tests` in these commands; see [Configure Your Project](/getting-started/configuration/).
- [Working on the Command Line](/guides/cli/) shows which command answers which task, with a guide for each.
- The [CLI reference](/reference/cli/) lists every command and option.
