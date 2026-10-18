---
title: Configure Your Project
description: 'Create a robot.toml for your Robot Framework project: a first configuration, running the tests with it, a profile for another environment and personal settings.'
sidebar:
  label: Configuration
  order: 90
---

RobotCode reads the configuration of a Robot Framework project from a `robot.toml` file in the project folder. It holds the options you would otherwise pass to `robot` on the command line or in argument files, such as the paths of the tests, the Python path and variables, and profiles for different environments. The editors and the `robotcode` commands use it alike, so the tests run the same way everywhere. This page creates a first `robot.toml`; [Configuring Projects with robot.toml](/guides/robot-toml/) explains all that it can do.

## A first `robot.toml`

Create a file named `robot.toml` in the root folder of your project, and commit it:

```toml title="robot.toml"
paths = ["tests"]
python-path = ["libraries", "resources"]
output-dir = "results"

[variables]
BROWSER = "chrome"
BASE_URL = "http://localhost:8080"
```

- **`paths`**: the folders or files with your tests.
- **`python-path`**: folders in which Robot Framework looks for your libraries and resource files.
- **`output-dir`**: the folder for `output.xml`, the log and the report.
- **`[variables]`**: variables for all tests, as `--variable` sets them on the command line.

Each setting is a command line option of Robot Framework, written with its long name in words separated by hyphens: `--outputdir` becomes `output-dir`, and `--pythonpath` becomes `python-path`. Relative paths count from the project folder.

In VS Code, the extension Even Better TOML completes the settings and shows their documentation, see [Editing `robot.toml`](/guides/vscode/configuration/#editing-robottoml).

## Running the tests

VS Code, PyCharm and IntelliJ IDEA use the configuration for the analysis, the test discovery and runs, and pick up a change of `robot.toml` at once.

On the command line, run the tests with `robotcode run`; Robot Framework's own `robot` command does not read `robot.toml`. `robotcode run` needs RobotCode's runner in the environment of your project:

```bash
pip install "robotcode[runner]"
```

```bash
# run the tests in paths
robotcode run

# options and paths on the command line come on top
robotcode run -i smoke
robotcode run tests/login.robot
```

An option with a single value on the command line, such as `-d`, replaces the one in `robot.toml`; a repeated option such as `-i` adds to its list, and paths on the command line replace `paths`.

## A profile for another environment

A profile holds the settings for another environment. Add one to `robot.toml`:

```toml title="robot.toml"
[profiles.staging]
description = "Staging server"
extend-variables = { BASE_URL = "https://staging.example.com" }
```

`robotcode -p staging run` runs with it. `extend-variables` adds to the variables outside of the profile, here changing `BASE_URL` and keeping `BROWSER`; `variables` would replace them all. In VS Code, **RobotCode: Select Configuration Profiles** selects the profiles, and in PyCharm **Tools | RobotCode | Select Configuration Profiles...**.

## Personal settings

Settings that only you need go into a file named `.robot.toml` next to `robot.toml`. Add it to `.gitignore`:

```toml title=".robot.toml"
[extend-variables]
BROWSER = "firefox"
```

RobotCode reads `.robot.toml` after `robot.toml`. Its settings replace those of `robot.toml`, and with `extend-` they add to them: `[variables]` here would drop `BASE_URL`.

## Checking the configuration

`robotcode profiles show` prints the settings that a run gets, and `robotcode -p staging profiles show` those with the profile `staging`. `robotcode config files` lists the files that RobotCode reads.

## Next steps

- [Configuring Projects with robot.toml](/guides/robot-toml/) explains all files, profiles in detail, expressions and the project root.
- The [`robot.toml` reference](/reference/config/) lists every setting.
- RobotCode's other settings are explained for [VS Code](/guides/vscode/configuration/) and [PyCharm](/guides/pycharm/configuration/).
