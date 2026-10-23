---
title: Profiles
description: 'Profiles in robot.toml: defining and selecting them, default profiles, inheritance, their order and precedence, hiding and enabling them, detached profiles, and changing profiles in a later file.'
sidebar:
  label: Profiles
  order: 100.3
---

A profile is a named set of settings that applies on top of the settings outside of profiles when you select it. Profiles let one project run in different ways without copies of the configuration:

- against different environments, such as a local server, a staging server and production;
- with different browsers or devices;
- as different kinds of runs, such as a quick smoke test or a dry run;
- with the settings of a particular machine, such as the CI server.

You can select several profiles at once, for example an environment and a browser, so each profile only needs to hold what makes it different.

## Defining a profile

A profile is a table `[profiles.<name>]`. It takes the same settings as the top of the file, plus a few of its own:

```toml title="robot.toml"
[variables]
BROWSER = "chromium"
BASE_URL = "http://localhost:8080"

[profiles.staging]
description = "Staging shop"
output-dir = "results/staging"

[profiles.staging.extend-variables]
BASE_URL = "https://staging.shop.example"
```

The settings of a profile replace those outside of it, and with `extend-` before the name they add to them: `extend-variables` changes `BASE_URL` and keeps `BROWSER`, while `variables` would leave only `BASE_URL`.

| Setting of a profile | What it does |
| --- | --- |
| `description` | A text that `robotcode profiles list` and the profile lists of VS Code and PyCharm show; the Test Explorer names its run profiles after it. |
| `inherits` | Profiles that are selected along with this one, see [Inheritance](#inheritance). |
| `precedence` | The order in which the profile applies, see [Order and precedence](#order-and-precedence). |
| `hidden` | Hides the profile from the lists, see [Hiding profiles](#hiding-profiles). |
| `enabled` | Switches the profile on or off, see [Enabling profiles](#enabling-profiles). |
| `detached` | Starts the profile from scratch, see [Detached profiles](#detached-profiles). |

## Selecting profiles

- **On the command line**, `-p` (`--profile`) before the command selects a profile:

  ```bash
  robotcode -p staging run
  robotcode -p staging -p firefox run
  robotcode -p "browser-*" run
  ```

  Give `-p` several times for several profiles. A name can be a pattern with `*` and `?`: `-p "browser-*"` selects all profiles whose names start with `browser-`.
- **The environment variable** `ROBOTCODE_PROFILES` selects profiles as well, separated by spaces, for example on a CI server: `ROBOTCODE_PROFILES="ci firefox"`.
- **In VS Code**, **RobotCode: Select Configuration Profiles** selects the profiles of a workspace folder, and the Test Explorer offers a run profile for each profile; see [Configuration profiles](/guides/vscode/configuration/#configuration-profiles).
- **In PyCharm**, **Tools | RobotCode | Select Configuration Profiles...** selects them, and **Run with Profile...** runs once with another profile; see [Configuration profiles](/guides/pycharm/configuration/#configuration-profiles).

`robotcode profiles list` lists the profiles with their descriptions and shows which of them are selected and, of these, which are enabled.

## Default profiles

`default-profiles` names the profiles that apply when none is selected:

```toml title="robot.toml"
default-profiles = ["local"]

[profiles.local]
description = "Local shop"

[profiles.local.extend-variables]
BASE_URL = "http://localhost:8080"

[profiles.ci]
description = "CI server"

[profiles.ci.extend-variables]
BASE_URL = "https://staging.shop.example"
HEADLESS = "true"
```

`robotcode run` and a run in the editor without a selection use `local`. A selection replaces the default profiles completely: `robotcode -p ci run` uses only `ci`, not `local` and `ci`.

Default profiles help when every run needs one of several profiles, such as an environment, and they save typing `-p` for the profile that most runs use. Like `-p`, `default-profiles` takes patterns such as `"os-*"`. Each developer can set a default of their own in their [`.robot.toml`](/guides/robot-toml/files/#personal-settings-in-robottoml), which replaces the one of `robot.toml`:

```toml title=".robot.toml"
default-profiles = ["staging"]
```

With conditions, the same default profiles can do different things on different machines; see [The same command locally and on the CI server](/guides/robot-toml/recipes/#the-same-command-locally-and-on-the-ci-server).

## Inheritance

A profile can build on others with `inherits`. Selecting it selects the profiles it inherits from as well, and they apply before it, so it only needs to hold what is different:

```toml title="robot.toml"
[variables]
BROWSER = "chromium"
HEADLESS = "false"
BASE_URL = "http://localhost:8080"

[profiles.staging]
description = "Staging shop"

[profiles.staging.extend-variables]
BASE_URL = "https://staging.shop.example"

[profiles.headless.extend-variables]
HEADLESS = "true"

[profiles.ci]
description = "CI server"
inherits = ["staging", "headless"]
output-dir = "results/ci"
```

`robotcode -p ci run` applies `staging`, then `headless`, then `ci`: the tests run against the staging shop, without a window, and write their results to `results/ci`. Changes to `staging` reach `ci` without copying them.

How inheritance works in detail:

- **Inheritance selects, it does not copy.** `inherits` selects the other profiles along with this one; the settings apply one after the other, as if you had selected all of them. A setting in the inheriting profile replaces what its parents set, and `extend-` adds to it:

  ```toml title="robot.toml"
  [profiles.base.variables]
  BROWSER = "chromium"
  TIMEOUT = "10s"

  [profiles.slow]
  inherits = ["base"]

  [profiles.slow.extend-variables]
  TIMEOUT = "60s"
  ```

  With `-p slow`, `BROWSER` is `chromium` and `TIMEOUT` is `60s`. With `variables` instead of `extend-variables` in `slow`, only `TIMEOUT` would be left.
- **Several parents** apply in the order of the list. If two of them set the same variable, the later one wins: with `inherits = ["staging", "firefox"]`, a `BROWSER` from `firefox` wins over one from `staging`.
- **Several levels** work as well: if `ci` inherits from `staging` and `staging` from `base`, `-p ci` applies `base`, `staging` and `ci`, in this order.
- **A single parent** can also be given as text: `inherits = "staging"`.
- **A profile selected twice**, once directly and once through inheritance, applies once.
- **A disabled profile** brings no parents along, at any level: if `ci` is [disabled](#enabling-profiles), selecting it applies neither `ci` nor `staging` and `headless`, which it inherits from, nor the profiles they inherit from. A disabled parent is left out with its own parents, and the profile that inherits from it applies without them. A parent that another profile in use also inherits from still applies.
- **`precedence`** comes before inheritance: a parent with a higher precedence than the inheriting profile applies after it, and wins where both set the same setting.
- **`detached`** in the inheriting profile also drops its parents, because they apply before it; see [Detached profiles](#detached-profiles).

Profiles that only exist to be inherited from, such as `headless` above, are best [hidden](#hiding-profiles), so that nobody selects them by mistake.

## Order and precedence

When you select several profiles, the order decides which one wins where they set the same setting. Without `precedence`, the profiles apply in the order in which you selected them, each after the profiles it inherits from:

```toml title="robot.toml"
[profiles.ci]
log-level = "INFO"

[profiles.debug]
log-level = "TRACE"
```

`robotcode -p ci -p debug run` logs with `TRACE`, but `robotcode -p debug -p ci run` logs with `INFO`, because `ci` applies last. `precedence` fixes the order regardless of the selection:

```toml title="robot.toml"
[profiles.debug]
precedence = 100
log-level = "TRACE"
```

Profiles with a lower precedence apply first, and a profile without a precedence counts as 0. Now `debug` applies after `ci` in both commands and always logs with `TRACE`. Profiles with the same precedence keep the order of the selection. Give a profile a high precedence when it should win over the others, as `debug` here, and a negative one when it should only fill in what the others leave open.

`robotcode profiles list -sp` lists the profiles sorted by precedence.

## Hiding profiles

Some profiles are not meant to be selected on their own: base profiles that others inherit from, or technical profiles that only make sense together with others. Hidden profiles do not appear in `robotcode profiles list` and in the profile lists of VS Code and PyCharm, which keeps these lists short:

```toml title="robot.toml"
[profiles.headless]
hidden = true

[profiles.headless.extend-variables]
HEADLESS = "true"

[profiles._browser-defaults.variables]
BROWSER = "chromium"
TIMEOUT = "10s"
```

- `hidden = true` hides a profile, and so does a name that starts with `_`, such as `_browser-defaults`.
- A condition hides a profile only sometimes, for example on the CI server: `hidden = { if = "environ.get('CI') == 'true'" }`.
- A hidden profile can still be selected by name, with `-p headless`, and inherited from.
- `robotcode profiles list -h` lists the hidden profiles as well.

## Enabling profiles

`enabled` switches a profile on or off. A disabled profile is skipped, even when it is selected, through `-p`, a pattern, `default-profiles` or inheritance:

```toml title="robot.toml"
# switched off for now
[profiles.payment]
enabled = false

[profiles.windows]
enabled = { if = "platform.system() == 'Windows'" }

[profiles.windows.extend-variables]
DRIVER_PATH = "C:\\drivers"

[profiles.linux]
enabled = { if = "platform.system() == 'Linux'" }

[profiles.linux.extend-variables]
DRIVER_PATH = "/usr/local/bin"
```

With a condition in a table with `if`, a [Python expression](/guides/robot-toml/settings/#expressions) decides. Select `windows` and `linux` together, or put both into `default-profiles`, and only the one for the current system applies. `robotcode -v profiles show` shows which profiles RobotCode uses and which it skips.

## Detached profiles

A profile with `detached = true` starts from scratch: the settings outside of profiles, from all configuration files including the user configuration, and the profiles applied before it do not count. Only environment variables that an `env` before it has set stay set. That suits a run that has nothing in common with the others, for example the performance tests of the project:

```toml title="robot.toml"
paths = ["tests"]
python-path = ["libraries", "resources"]

[variables]
BROWSER = "chromium"

[profiles.performance]
detached = true
paths = ["performance"]
python-path = ["performance/libraries"]
output-dir = "results/performance"
```

`robotcode -p performance run` runs only the tests in `performance`, without the variables and the Python path of the other tests. Profiles that `performance` inherits from are dropped as well, because they apply before it.

## Changing profiles in a later file

A later configuration file, such as [`.robot.toml`](/guides/robot-toml/files/#personal-settings-in-robottoml), can add profiles and change those of `robot.toml`:

- `[profiles.<name>]` in a later file replaces **all** profiles of the earlier files.
- `[extend-profiles.<name>]` adds the profile, or, if an earlier file has a profile of that name, changes it: a setting replaces the one of the profile, and an `extend-` setting adds to it.

```toml title=".robot.toml"
[extend-profiles.local]
description = "My local settings"

[extend-profiles.local.extend-variables]
BASE_URL = "http://localhost:9000"

[extend-profiles.ci]
output-dir = "results/my-ci"

[extend-profiles.ci.extend-variables]
BROWSER = "firefox"
```

Here `local` is a new profile, and `ci` from the `robot.toml` of the [example project](/guides/robot-toml/#an-example-project) writes its results to `results/my-ci` and runs in Firefox, with its other settings as before.

Profiles change the tables `[rebot]`, `[libdoc]` and `[testdoc]` the same way: a `[profiles.ci.rebot]` replaces the whole `[rebot]` while `ci` applies, and a `[profiles.ci.extend-rebot]` changes it. In `.robot.toml`, `[extend-profiles.ci.extend-rebot]` adds to what `ci` sets for `rebot`.

```toml title="robot.toml"
[rebot]
merge = true

[profiles.ci.extend-rebot]
report-title = "CI run"
```

`robotcode -p ci rebot results/output.xml` merges and gets the report title `CI run`.

`extend-profiles` and `inherits` do different things: `extend-profiles` changes how a profile is defined, `inherits` selects other profiles along with it when it is used.
