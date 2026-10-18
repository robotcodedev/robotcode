---
title: Troubleshooting robot.toml
description: 'What to check when a setting of robot.toml does not do what you expect: the commands that show the configuration, and the usual causes, from the wrong command to replaced settings.'
sidebar:
  label: Troubleshooting
  order: 100.7
---

When a setting does not do what you expect, the commands in [Checking what a run gets](/guides/robot-toml/command-line/#checking-what-a-run-gets) show where the configuration comes from and what a run gets. The sections below say which of them to use for which problem.

## The tests run without the configuration

Robot Framework's own `robot` command does not read `robot.toml`. Run the tests with `robotcode run`.

## A setting has no effect

Go through the steps in which RobotCode combines the settings:

1. **The right project?** `robotcode config root` shows which folder RobotCode takes as the project root. Started in a folder without a configuration further up, it may stop at the `.git` folder of the repository; see [The project root](/guides/robot-toml/files/#the-project-root).
2. **The right file?** `robotcode config files` lists the files RobotCode reads. A `robot.toml` in a subfolder of the project root is not read.
3. **The right profile?** `robotcode profiles list` shows which profiles are selected. Without `-p`, only the [default profiles](/guides/robot-toml/profiles/#default-profiles) apply. A profile with an `enabled` condition may be disabled on your machine: `robotcode -v -p <name> profiles show` says whether RobotCode uses it or skips it.
4. **Replaced later?** `robotcode -v profiles show` and `robotcode config show -s` show whether a later file or profile replaces the setting, for example a `.robot.toml` or a profile with a higher `precedence`.
5. **Replaced on the command line?** An option on the command line with a single value, such as `-d`, replaces the one of the configuration.

## Variables or profiles are gone

A setting without `extend-` replaces the value before it:

- `[variables]` in a profile or in `.robot.toml` leaves only its own variables. Use `[extend-variables]` to change single variables and keep the others.
- `[profiles.<name>]` in `.robot.toml` replaces all profiles of `robot.toml`. Use `[extend-profiles.<name>]`.
- `python-path` or `output-dir` in `robot.toml` replace the defaults of the user configuration, `./lib` and `./resources` or `results`.

See [Replacing and extending](/guides/robot-toml/combining/#replacing-and-extending).

## A profile is missing from the list

- **Hidden:** a profile with `hidden = true`, or with a name that starts with `_`, is left out of `robotcode profiles list` and of the profile lists of the editors. `robotcode profiles list -h` shows it, and `-p` selects it by name.
- **Replaced:** `[profiles.<name>]` in a later file replaces the profiles of the earlier files, see above.

## "Can't find any configuration profiles matching the pattern"

No profile has the name, or matches the pattern, that `-p`, `ROBOTCODE_PROFILES`, `default-profiles` or the editor selects. Check the spelling with `robotcode profiles list -h`.

## "Value '3' must be of type `str | StringExpression` but is `int`"

The values of variables, metadata and environment variables are text. Put numbers in quotes: `RETRIES = "3"`. The message names the file and the setting, such as `variables.RETRIES`.

## A path is not found

Relative paths in the configuration count from the project root, not from the folder in which you start the command, and not from the folder of the file that sets them; see [The project root](/guides/robot-toml/files/#the-project-root). `robotcode config root` shows the root.

## The editor does not pick up a change

The editors restart RobotCode's language server when `robot.toml`, `.robot.toml` or `pyproject.toml` change. In VS Code, each workspace folder has its own configuration: check that the file is in the folder of the files you work on. See also [Troubleshooting in VS Code](/guides/vscode/troubleshooting/) and [Troubleshooting in PyCharm](/guides/pycharm/troubleshooting/).
