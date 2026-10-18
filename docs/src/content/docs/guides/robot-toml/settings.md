---
title: Settings
description: 'How the settings of robot.toml map to the options of Robot Framework, the forms their values take, the settings only RobotCode has, paths, variables and environment variables, expressions, and moving over from argument files.'
sidebar:
  label: Settings
  order: 100.2
---

A setting in `robot.toml` is a command line option of Robot Framework, written with its long name in words separated by hyphens: `--outputdir` is `output-dir`, `--pythonpath` is `python-path`, `--loglevel` is `log-level`. Many options that can be given several times take a plural name, such as `includes` for `--include` and `variable-files` for `--variablefile`; the table below and the [reference](/reference/config/) give the exact names.

## Values

The value of a setting takes the form that fits the option.

**Text**, for an option with one value:

```toml
output-dir = "results"
log-level = "DEBUG"
console = "dotted"
```

**Numbers**, for the few options that count something:

```toml
console-width = 120
max-error-lines = 20
```

**Lists**, for an option that can be given several times:

```toml
python-path = ["libraries", "resources"]
includes = ["smoke", "api"]
variable-files = ["config/common.py", "config/staging.yaml"]
```

**Tables**, for an option whose values have a name and a value, such as variables and metadata:

```toml
[variables]
BROWSER = "chromium"
RETRIES = "3"

[metadata]
Version = "1.2"
Team = "Shop"
```

The values of variables and metadata are text, numbers too: `RETRIES = "3"` sets `${RETRIES}` as `--variable RETRIES:3` does, and Robot Framework converts it where a number is needed. Listeners, pre-run modifiers and parsers take a table, too, with the name or path as key and a list of arguments as value:

```toml
[listeners]
"listeners/Timing.py" = ["slow=5"]
AnotherListener = []
```

**Switches**, for an option without a value, take `true` or `false`:

```toml
dry-run = true
exit-on-failure = true
```

`false` passes the opposite option to Robot Framework, `dry-run = false` for example `--nodryrun`. So a profile can switch off what the settings outside of it switch on.

## From the command line to `robot.toml`

| On the command line | In `robot.toml` |
| --- | --- |
| `--outputdir results` | `output-dir = "results"` |
| `--loglevel DEBUG` | `log-level = "DEBUG"` |
| `--pythonpath libs --pythonpath resources` | `python-path = ["libs", "resources"]` |
| `--include smoke --include api` | `includes = ["smoke", "api"]` |
| `--exclude wip` | `excludes = ["wip"]` |
| `--test "Login*"` | `tests = ["Login*"]` |
| `--suite Orders` | `suites = ["Orders"]` |
| `--variable BROWSER:chromium` | `BROWSER = "chromium"` in the table `[variables]` |
| `--variablefile vars.py:staging` | `variable-files = ["vars.py:staging"]` |
| `--metadata Version:1.2` | `Version = "1.2"` in the table `[metadata]` |
| `--listener Timing.py:slow=5` | `"Timing.py" = ["slow=5"]` in the table `[listeners]` |
| `--language de` | `languages = ["de"]` |
| `--dryrun` | `dry-run = true` |
| `--exitonfailure` | `exit-on-failure = true` |
| The paths of the tests | `paths = ["tests"]` |

To find a setting:

- `robotcode config info list` lists all settings, and `robotcode config info desc <setting>` describes one, for example `robotcode config info desc output-dir`.
- In VS Code, completion in `robot.toml` offers the settings and their values; see [In the editors](/guides/robot-toml/#in-the-editors).
- The [`robot.toml` reference](/reference/config/) lists every setting with its type and examples.

## Settings that only RobotCode has

| Setting | What it does |
| --- | --- |
| `paths` | The files and folders with the tests, which Robot Framework takes as arguments. Paths on the command line replace them. |
| `env` | Environment variables that are set before Robot Framework starts. |
| `args` | Further arguments that are passed to Robot Framework as they are. |
| `wrapper` | A command that the run goes through, see [Running Tests Through a Wrapper](/guides/wrapper/). |
| `profiles`, `extend-profiles`, `default-profiles` | Profiles, see [Profiles](/guides/robot-toml/profiles/). |
| `[rebot]`, `[libdoc]`, `[testdoc]`, and `[extend-rebot]`, `[extend-libdoc]`, `[extend-testdoc]` | The options of other commands, and changes to them, see [below](#settings-of-other-commands). |
| `[tool.robotcode-analyze]` | The settings of RobotCode's analysis, see [below](#settings-of-other-commands). |

## Paths, variables and environment variables

```toml title="robot.toml"
paths = ["tests"]
python-path = ["libraries", "resources"]
variable-files = ["config/staging.py"]

[variables]
BROWSER = "chromium"

[env]
SHOP_USER = "tester"
```

- **`paths`** lists the files and folders with the tests. A run without paths on the command line runs them.
- **`python-path`** adds folders in which Robot Framework looks for libraries, and for resource and variable files that it does not find next to the file that imports them.
- **`variables`** and **`variable-files`** set variables, as `--variable` and `--variablefile` do.
- **`env`** sets environment variables before Robot Framework starts, here for `%{SHOP_USER}` in the tests. The language server sets them when it starts, too, so that the editor knows them.

Relative paths count from the [project root](/guides/robot-toml/files/#the-project-root), wherever you start a command.

Passwords and other secrets do not belong in a committed `robot.toml`. Keep them in your [`.robot.toml`](/guides/robot-toml/files/#personal-settings-in-robottoml), or let the CI server set them as environment variables and read them in the tests with `%{NAME}`.

## Expressions

A setting whose type in the [reference](/reference/config/) includes `StringExpression` also takes a table with `expr`, which computes the value with a Python expression when RobotCode uses the configuration:

```toml title="robot.toml"
# A results folder for each day
output-dir = { expr = "f'results/{date.today():%Y-%m-%d}'" }

[variables]
# The browser from the environment variable BROWSER, Chromium without it
BROWSER = { expr = "environ.get('BROWSER', 'chromium')" }
```

Besides basic built-in functions of Python such as `str`, `int` and `len`, an expression can use these names:

| Name | What it is |
| --- | --- |
| `environ` | The environment variables, as `os.environ` |
| `platform` | Python's module `platform`, for example `platform.system()` |
| `re` | Python's module `re` for regular expressions |
| `datetime`, `date`, `time`, `timedelta`, `timezone` | The classes of Python's module `datetime` |
| `Path` | `pathlib.Path` |

The conditions in `enabled` and `hidden` of a profile use the same kind of expression, in a table with `if`; see [Enabling profiles](/guides/robot-toml/profiles/#enabling-profiles). `robotcode profiles show -n` shows the expressions without computing them.

## Settings of other commands

- **`[rebot]`, `[libdoc]` and `[testdoc]`** hold the options of `robotcode rebot`, `robotcode libdoc` and `robotcode testdoc`. A setting in the table wins over the same setting outside of it, and an `extend-` setting in the table adds to it. Of the settings outside of the tables, each command takes only some:
  - **`rebot`** takes the ones that Robot Framework itself passes from `robot` to `rebot` after a run, such as `output-dir`, `python-path`, `log-title` and `report-title`. It does not take `includes`, `excludes`, `tests`, `suites`, `parse-include`, `name`, `doc`, `metadata`, `set-tag`, `output`, `log-level`, `timestamp-outputs`, `console` and `quiet`; put them into `[rebot]` when `rebot` needs them. As in Robot Framework, `run-empty-suite` becomes `process-empty-suite` for `rebot`.
  - **`libdoc`** takes only `python-path`. Outside of the table, `name` and `quiet` are options of `robot`.
  - **`testdoc`** takes the settings it shares with `robot`: `name`, `doc`, `metadata`, `set-tag`, `tests`, `suites`, `includes` and `excludes`.

  ```toml title="robot.toml"
  output-dir = "results"

  [rebot]
  merge = true
  output-dir = "merged"
  report-title = "Nightly run"
  ```

  Here the runs write their results to `results`, and `robotcode rebot` writes the merged results to `merged`.

  A `[rebot]` in a profile or in a later file, such as `.robot.toml`, replaces the whole `[rebot]` before it. **`[extend-rebot]`** changes it instead: a setting in it replaces the one of `[rebot]`, and an `extend-` setting adds to it. `[extend-libdoc]` and `[extend-testdoc]` do the same for their tables:

  ```toml title=".robot.toml"
  [extend-rebot]
  report-title = "My nightly run"
  ```

  With the `robot.toml` above, `robotcode rebot` still merges the results into `merged`, with your own report title.

- **`[tool.robotcode-analyze]`** configures the analysis in the editors and in `robotcode analyze code`, for example the severity of diagnostics and the cache; see [Analyzing Code](/guides/analyzing-code/) and [Configuration via `robot.toml`](/reference/diagnostics-modifiers/#configuration-via-robottoml).

## Moving over from argument files

A project that runs its tests with an argument file and a script per environment:

```text title="arguments.txt"
--outputdir results
--pythonpath libraries
--pythonpath resources
--variable BROWSER:chromium
--variable BASE_URL:http://localhost:8080
--exclude wip
tests
```

```bash title="run-staging.sh"
robot --argumentfile arguments.txt --variable BASE_URL:https://staging.shop.example "$@"
```

The same as `robot.toml`, with the script as a profile:

```toml title="robot.toml"
paths = ["tests"]
output-dir = "results"
python-path = ["libraries", "resources"]
excludes = ["wip"]

[variables]
BROWSER = "chromium"
BASE_URL = "http://localhost:8080"

[profiles.staging.extend-variables]
BASE_URL = "https://staging.shop.example"
```

`robotcode run` replaces `robot --argumentfile arguments.txt`, and `robotcode -p staging run` replaces the script. Until all options have moved, `args` can pass the argument file on:

```toml title="robot.toml"
args = ["--argumentfile", "arguments.txt"]
```
