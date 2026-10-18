---
title: Configuration Files and the Project Root
description: 'The files RobotCode reads, robot.toml, .robot.toml, pyproject.toml and the user configuration, what each one is for, their order, and how RobotCode finds the project root.'
sidebar:
  label: Files and Project Root
  order: 100.1
---

RobotCode reads the configuration from up to four files. Each has its own purpose:

| File | Where | What it is for |
| --- | --- | --- |
| `robot.toml` | The project root | The configuration of the project, the same for everyone. Commit it. |
| `.robot.toml` | The project root | Your personal settings. Add it to `.gitignore`. |
| `pyproject.toml` | The project root | The standard project file of Python. Its table `[tool.robot]` can hold the configuration instead of `robot.toml`, but `robot.toml` is recommended, so that the Python and the Robot Framework world stay apart. |
| The user configuration | Your configuration folder | Your defaults for all projects. |

## The order

RobotCode reads the files in this order:

1. the user configuration,
2. `pyproject.toml`,
3. `robot.toml`,
4. `.robot.toml`.

A setting in a later file replaces the one of an earlier file, and with `extend-` before its name it adds to it. A `python-path` in `robot.toml` therefore replaces the one of the user configuration, while an `extend-python-path` in `.robot.toml` adds to the one of `robot.toml`. [How Settings Combine](/guides/robot-toml/combining/) explains the rules.

## Personal settings in `.robot.toml`

`.robot.toml` holds what only you need, without changing the project's `robot.toml` for everyone else. RobotCode reads it after `robot.toml`, so its settings win. Some uses:

```toml title=".robot.toml"
# Run in another browser, with a window
[extend-variables]
BROWSER = "firefox"
HEADLESS = "false"
```

```toml title=".robot.toml"
# Test against a shop that runs on another port on your machine
[extend-variables]
BASE_URL = "http://localhost:9000"
```

```toml title=".robot.toml"
# Your own profile when you don't select one
default-profiles = ["staging"]
```

```toml title=".robot.toml"
# A library you work on in a checkout next to the project
extend-python-path = ["../shop-library/src"]
```

```toml title=".robot.toml"
# Credentials that must not be committed, read in the tests with %{SHOP_PASSWORD}
[extend-env]
SHOP_USER = "jane"
SHOP_PASSWORD = "secret"
```

Use the `extend-` form of a setting in `.robot.toml` when you want to add to the project's values: `[variables]` here would replace all variables of `robot.toml`, `[extend-variables]` changes only those it names. The same goes for profiles: `[profiles.local]` in `.robot.toml` replaces all profiles of `robot.toml`, while `[extend-profiles.local]` adds one; see [Changing profiles in a later file](/guides/robot-toml/profiles/#changing-profiles-in-a-later-file).

## `pyproject.toml`

`pyproject.toml` is the standard project file of Python, and RobotCode supports it. A project that wants to stick to this standard can keep its configuration there instead of in `robot.toml`. The recommendation, however, is to keep the Python world and the Robot Framework world apart: `pyproject.toml` for the Python side of the project, `robot.toml` for its tests and tasks.

In `pyproject.toml`, the settings go into the table `[tool.robot]` and its sub-tables:

```toml title="pyproject.toml"
[tool.robot]
paths = ["tests"]
python-path = ["libraries", "resources"]

[tool.robot.variables]
BROWSER = "chromium"

[tool.robot.profiles.ci]
output-dir = "results/ci"
```

The settings of RobotCode's analysis go into the table `[tool.robotcode-analyze]`, as in `robot.toml`. If a project has both files, `robot.toml` wins.

## The user configuration

The user configuration is a `robot.toml` in your configuration folder:

- Linux: `~/.config/robotcode/robot.toml`, or `$XDG_CONFIG_HOME/robotcode/robot.toml`
- macOS: `~/Library/Application Support/robotcode/robot.toml`
- Windows: `%LOCALAPPDATA%\robotcode\robot.toml`

Its settings apply to every project you open, before those of the project. If the file does not exist, RobotCode creates it with these defaults:

```toml
output-dir = "results"
python-path = ["./lib", "./resources"]
```

A project that sets `output-dir` or `python-path` replaces these values, it does not add to them. Change the file or empty it to change the defaults. Keep in mind that the settings in this file apply to all projects, also to projects of other people that you open: a setting that a project needs belongs in its `robot.toml`.

## Other files with `--config`

`--config` (`-c`) before the command reads the given files instead of those of the project, after the user configuration, for example a configuration for a special run:

```bash
robotcode -c release.toml run
```

The environment variable `ROBOTCODE_CONFIG_FILES` does the same.

## The project root

The project root is the folder of the configuration. Relative paths in the configuration count from there, wherever you start a command, because RobotCode runs Robot Framework in that folder; only paths of tests that you give on the command line count from the current folder.

RobotCode looks for the root from the paths of the tests on the command line, or else from the current folder; in the editors, from the workspace folder in VS Code and from the project folder in PyCharm. It goes up folder by folder and stops at the first one that contains a `.robot.toml`, `robot.toml` or `pyproject.toml`, or else a `.git` or `.hg`. If it finds none, the commands use the current folder as the root, and `robotcode config root` reports that it found no root.

- `robotcode config root` shows the root and what it was found by.
- `--root` (`-r`) before the command sets the root, and `--no-vcs` ignores `.git` and `.hg`.

### Several projects in one repository

In a repository with several projects, give each project folder its own `robot.toml`:

```text
shop-tests/
├── .git/
├── web/
│   ├── robot.toml
│   └── tests/
└── api/
    ├── robot.toml
    └── tests/
```

`robotcode run` in `web`, or `robotcode run web/tests` in `shop-tests`, uses `web/robot.toml`. `robotcode run` in `shop-tests` itself finds no `robot.toml` on its way up and stops at `.git`, so it uses neither. In VS Code, add `web` and `api` as folders of a workspace, so that each gets its own language server with its own configuration; see [Several workspace folders](/guides/vscode/configuration/#several-workspace-folders).
