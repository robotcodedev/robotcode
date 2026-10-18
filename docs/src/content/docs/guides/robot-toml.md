---
title: Configuring Projects with robot.toml
description: 'All that robot.toml can do: settings and how they map to Robot Framework options, paths, variables and environment variables, profiles with inheritance, precedence and conditions, expressions, the files RobotCode reads, the project root and checking the configuration.'
sidebar:
  label: robot.toml
  order: 100
---

`robot.toml` holds the configuration of a Robot Framework project: the options you would otherwise pass to `robot` on the command line or in argument files, and profiles for different environments. RobotCode reads it everywhere it runs: the `robotcode` commands such as `robotcode run`, `discover`, `analyze code` and `repl` read it, and so does RobotCode's language server in VS Code, PyCharm, IntelliJ IDEA and other editors, for the analysis, the test discovery and runs. A run in the editor and a run in CI therefore get the same options.

Robot Framework's own `robot` command does not read `robot.toml`. Run your tests with `robotcode run`, or `robotcode robot`, which is the same command; it passes the configuration on to Robot Framework. On the command line, it needs RobotCode's runner in the environment of your project, for example installed with `pip install "robotcode[runner]"`.

This guide explains all that the file can do. To create a first `robot.toml`, see [Configure Your Project](/getting-started/configuration/); the [`robot.toml` reference](/reference/config/) lists every setting.

## Settings

`robot.toml` is a [TOML](https://toml.io/en/) file. Each setting is a command line option of Robot Framework, written with its long name in words separated by hyphens, and its value takes the form that fits the option:

| On the command line | In `robot.toml` |
| --- | --- |
| `--outputdir results` | `output-dir = "results"` |
| `--loglevel DEBUG` | `log-level = "DEBUG"` |
| `--pythonpath lib --pythonpath resources` | `python-path = ["lib", "resources"]` |
| `--include smoke --include api` | `includes = ["smoke", "api"]` |
| `--exclude wip` | `excludes = ["wip"]` |
| `--variable BROWSER:chrome` | `BROWSER = "chrome"` in the table `[variables]` |
| `--variablefile vars.py:staging` | `variable-files = ["vars.py:staging"]` |
| `--metadata Version:1.2` | `Version = "1.2"` in the table `[metadata]` |
| `--listener Listener.py:arg` | `"Listener.py" = ["arg"]` in the table `[listeners]` |
| `--dryrun` | `dry-run = true` |
| The paths of the tests | `paths = ["tests"]` |

An option that can be given several times takes a list, an option with a name and a value takes a table, and an option without a value takes `true` or `false`. The values of variables and metadata are strings, numbers too: `RETRIES = "3"` in `[variables]` sets `${RETRIES}` as `--variable RETRIES:3` does.

`robotcode config info list` lists all settings, and `robotcode config info desc <setting>` describes one. `args` passes further arguments to Robot Framework as they are, for example an argument file whose options you have not moved into `robot.toml` yet:

```toml
args = ["--argumentfile", "old.args"]
```

## Paths, variables and environment variables

```toml title="robot.toml"
paths = ["tests"]
python-path = ["libraries", "resources"]
variable-files = ["config/staging.py"]

[variables]
BROWSER = "chrome"

[env]
SHOP_USER = "tester"
```

- **`paths`** lists the files and folders with the tests. A run without paths on the command line runs them; paths on the command line replace them.
- **`python-path`** adds folders in which Robot Framework looks for libraries, and for resource and variable files that it does not find next to the file that imports them.
- **`variables`** and **`variable-files`** set variables, as `--variable` and `--variablefile` do.
- **`env`** sets environment variables before Robot Framework starts, here for `%{SHOP_USER}` in the tests. The language server sets them when it starts, too.

Relative paths count from the [project root](#the-project-root), wherever you start a command: RobotCode runs Robot Framework in that folder. Only paths of tests that you give on the command line count from the current folder.

In the editors, the analysis takes `python-path`, `variables`, `variable-files`, `env` and `languages` from the configuration, so that imports and variables resolve as they do in a run. The test discovery uses the settings of a run, such as `paths`, `includes` and `excludes`.

## Profiles

A profile is a set of settings that applies on top of the settings outside of profiles when you select it. Profiles let one project run against different environments:

```toml title="robot.toml"
paths = ["tests"]

[variables]
BROWSER = "chrome"
BASE_URL = "http://localhost:8080"

[profiles.staging]
description = "Staging server"
extend-variables = { BASE_URL = "https://staging.example.com" }

[profiles.ci]
description = "CI server"
inherits = ["staging"]
output-dir = "results/ci"
extend-variables = { BROWSER = "headlesschrome" }
```

### Selecting profiles

- **On the command line**, `-p` (`--profile`) before the command selects a profile; give it several times for several profiles: `robotcode -p ci run` or `robotcode -p staging -p firefox run`. A name can be a pattern with `*` and `?`: `-p "ci-*"` selects all profiles whose names start with `ci-`.
- **The environment variable** `ROBOTCODE_PROFILES` selects profiles as well, separated by spaces, for example on a CI server: `ROBOTCODE_PROFILES="ci"`.
- **Without a selection**, the profiles in `default-profiles` apply, for example `default-profiles = ["staging"]`.
- **In VS Code**, **RobotCode: Select Configuration Profiles** selects the profiles of a workspace folder, and the Test Explorer offers each profile as a run profile; see [Configuration profiles](/guides/vscode/configuration/#configuration-profiles).
- **In PyCharm and IntelliJ IDEA**, **Tools | RobotCode | Select Configuration Profiles...** selects them, and **Run with Profile...** runs once with another profile; see [Configuration profiles](/guides/pycharm/configuration/#configuration-profiles).

`robotcode profiles list` lists the profiles with their descriptions and shows which of them are selected and enabled.

### How the settings combine

When you select profiles, RobotCode starts with the settings outside of profiles and applies the profiles one after the other:

- **A setting in a profile replaces** the one before it. With `extend-` before its name, it **adds** to a list or a table instead: `extend-variables` in `staging` above changes `BASE_URL` and keeps `BROWSER`, while `variables` would leave only the variables of the profile. A profile with both applies `variables` first and adds `extend-variables` to it.
- **`inherits`** selects the profiles it names along with this one and applies them before it: selecting `ci` applies `staging`, then `ci`.
- **`precedence`** sets the order: profiles with a lower precedence apply first. A profile without a precedence counts as 0, and profiles with the same precedence apply in the order in which you selected them.
- **`detached = true`** starts a profile from scratch: the settings outside of profiles, from all configuration files, and the profiles applied before it do not count.

With `robotcode -p ci run`, the tests run against `https://staging.example.com` in `headlesschrome` and write their results to `results/ci`.

### Enabling and hiding profiles

```toml title="robot.toml"
[profiles.windows]
enabled = { if = "platform.system() == 'Windows'" }
extend-variables = { DRIVER_PATH = "C:\\drivers" }

[profiles.linux]
enabled = { if = "platform.system() == 'Linux'" }
extend-variables = { DRIVER_PATH = "/usr/local/bin" }
```

- **`enabled = false`**, or a condition as above, switches a profile off: RobotCode skips it even when it is selected. Select both profiles above, and only the one for the current system applies.
- **`hidden = true`** hides a profile from `robotcode profiles list` and from the profile lists of VS Code and PyCharm; profiles whose names start with `_` are hidden too. A hidden profile can still be selected by name, and serve as a base for others in `inherits`. `robotcode profiles list -h` lists hidden profiles as well.

## Expressions

A setting whose type in the [reference](/reference/config/) includes `StringExpression` also takes a table with `expr`, which computes the value with a Python expression when RobotCode uses the configuration:

```toml title="robot.toml"
output-dir = { expr = "f'results/{date.today():%Y-%m-%d}'" }

[variables]
BROWSER = { expr = "environ.get('BROWSER', 'chrome')" }
```

The conditions in `enabled` and `hidden` use the same kind of expression. Besides basic built-in functions of Python such as `str`, `int` and `len`, an expression can use these names: `environ` for the environment variables, `platform`, `re`, `datetime`, `date`, `time`, `timedelta`, `timezone` and `Path`. `robotcode profiles show -n` shows the expressions without computing them.

## The files

RobotCode reads these files, in this order; a later file wins:

1. **The user configuration**, a `robot.toml` with defaults of your own for all projects. It is in your configuration folder:
   - Linux: `~/.config/robotcode/robot.toml`, or `$XDG_CONFIG_HOME/robotcode/robot.toml`
   - macOS: `~/Library/Application Support/robotcode/robot.toml`
   - Windows: `%LOCALAPPDATA%\robotcode\robot.toml`

   If the file does not exist, RobotCode creates it with `output-dir = "results"` and `python-path = ["./lib", "./resources"]`; change it to change these defaults.
2. **`pyproject.toml`** in the project root, with the settings in the table `[tool.robot]`.
3. **`robot.toml`** in the project root: the configuration of the project. Commit it.
4. **`.robot.toml`** in the project root: personal settings, for example another browser. Add it to `.gitignore`.

With `--config` (`-c`) before the command, RobotCode reads the given files instead of those of the project, after the user configuration.

### Replacing and extending

Between the files, the same rule applies as between profiles: a setting in a later file replaces the one in an earlier file, and `extend-` adds to it. A `.robot.toml` that adds to `robot.toml`:

```toml title="robot.toml"
python-path = ["libraries"]

[variables]
BROWSER = "chrome"
BASE_URL = "http://localhost:8080"
```

```toml title=".robot.toml"
extend-python-path = ["my-libraries"]

[extend-variables]
BROWSER = "firefox"
```

With both files, the Python path is `libraries` and `my-libraries`, `BROWSER` is `firefox` and `BASE_URL` stays. With `[variables]` instead of `[extend-variables]` in `.robot.toml`, only `BROWSER` would be left.

This applies to profiles too: `[profiles.local]` in `.robot.toml` replaces all profiles of `robot.toml`. `[extend-profiles.local]` adds the profile `local` instead, or, if `robot.toml` has a profile of that name, changes it: a setting replaces the one of the profile, and an `extend-` setting adds to it.

```toml title=".robot.toml"
[extend-profiles.local]
description = "My local settings"
extend-variables = { BASE_URL = "http://localhost:9000" }

[extend-profiles.ci]
output-dir = "results/my-ci"
extend-variables = { BROWSER = "firefox" }
```

Here `local` is a new profile, and `ci` from the [example above](#profiles) writes its results to `results/my-ci` and runs in `firefox`, with its other settings as before.

### `pyproject.toml`

A project that keeps its configuration in `pyproject.toml` puts the settings into the table `[tool.robot]`:

```toml title="pyproject.toml"
[tool.robot]
paths = ["tests"]
python-path = ["libraries"]

[tool.robot.variables]
BROWSER = "chrome"

[tool.robot.profiles.ci]
output-dir = "results/ci"
```

The settings of RobotCode's analysis go into the table `[tool.robotcode-analyze]`, as in `robot.toml`. If a project has both files, `robot.toml` wins.

## The project root

The project root is the folder of the configuration. RobotCode looks for it from the paths of the tests on the command line, or else from the current folder; in the editors, from the workspace folder in VS Code and from the project folder in PyCharm. It goes up folder by folder and stops at the first one that contains a `.robot.toml`, `robot.toml` or `pyproject.toml`, or else a `.git` or `.hg`. If it finds none, the current folder is the root.

- `robotcode config root` shows the root and what it was found by.
- `--root` before the command sets the root, and `--no-vcs` ignores `.git` and `.hg`.

## Settings of other commands

- **`[rebot]`, `[libdoc]` and `[testdoc]`** hold the options of `robotcode rebot`, `robotcode libdoc` and `robotcode testdoc`. These commands also use the settings outside of these tables that they share with `robot`, for example `python-path`, or `output-dir` for `rebot`.

  ```toml title="robot.toml"
  [rebot]
  merge = true
  report-title = "Nightly run"
  ```

- **`[tool.robotcode-analyze]`** configures the analysis in the editors and in `robotcode analyze code`, for example the severity of diagnostics and the cache; see [Analyzing Code](/guides/analyzing-code/) and [Configuration via `robot.toml`](/reference/diagnostics-modifiers/#configuration-via-robottoml).
- **`wrapper`** runs the tests through a command, for example one that starts the services they need; see [Running Tests Through a Wrapper](/guides/wrapper/).

## Checking the configuration

| Command | What it shows |
| --- | --- |
| `robotcode config root` | The project root and what it was found by. |
| `robotcode config files` | The configuration files that RobotCode reads, in order. |
| `robotcode config show` | The settings of all files together, before any profile applies. `-s` shows each file on its own. |
| `robotcode profiles list` | The profiles, with their descriptions, and which of them are selected and enabled. `-h` includes hidden profiles. |
| `robotcode -p ci profiles show` | The settings that a run gets with the selected profiles, with the expressions computed. `-n` shows the expressions instead. |

`-v` (`--verbose`) before a command shows which files RobotCode reads, which profiles it uses or skips, and the options it passes to Robot Framework, for example `robotcode -v -p ci run`. A setting with a wrong value stops the command with a message that names the file and the setting.

## Editing `robot.toml`

In VS Code, the extension Even Better TOML completes the settings of `robot.toml` and `.robot.toml` and shows their documentation, from RobotCode's JSON schema; see [Editing `robot.toml`](/guides/vscode/configuration/#editing-robottoml). Other editors with a TOML language server can use the schema at `https://www.robotcode.io/schemas/robot.toml.json`.

The editors restart RobotCode's language server when you create, change or delete `robot.toml`, `.robot.toml` or `pyproject.toml`, so a change applies at once.
