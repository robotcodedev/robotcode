---
title: A Profile for the CI Server
description: "Step 7 of the tutorial: let the agent write a CI profile in robot.toml from the documentation of each setting, and check it with config show, a dry run and discover."
sidebar:
  label: 7. A Profile for the CI Server
  order: 150.47
---

Finally, set up how CI runs the tests: a profile in `robot.toml` with the system to test, a browser without a window and a folder for the results. The agent writes it from the documentation of each setting and checks the result before CI runs it.

## What you learn

- how the agent finds out what a setting does and how it is written;
- how a profile adds to the settings of `robot.toml`;
- how to check a profile without running the tests.

## How to ask the agent

- *"Add a profile for our CI server: `<system>`, `<browser settings>`, and the results in `<folder>`."*
- *"Show me what a run with that profile gets."*
- *"What does the setting `<key>` do?"*
- *"What's my effective configuration with the `<profile>` profile?"*

The session below starts with *"Add a profile for our CI server: the staging shop, a browser without a window, and the results in `results/ci`."*

## What the agent does

### It reads the setting's documentation

`robotcode config info desc <key>` prints a setting's type, its description and a TOML example. The skill tells the agent to read it before it writes a setting, instead of guessing. From the session *A profile for the CI server*:

<!-- excerpt: a-profile-for-the-ci-server -->
```console
$ robotcode config info desc output-dir | head -20
# robot.toml configuration settings

## output-dir

Type: `str | StringExpression | None`
…
```

### It extends what is there

The project already had a `ci` profile, so the agent extended it instead of adding a second one. A profile in `[profiles.<name>]` adds to the top-level settings of `robot.toml` when you select it.

### It checks the result without running the tests

`robotcode -p ci profiles show` shows the configuration with the profile, a dry run with `--dry` the options and arguments `robot` would get, and `robotcode -p ci discover tests` the tests the profile includes. From the session:

<!-- excerpt: a-profile-for-the-ci-server -->
```console
$ robotcode -p ci --dry robot 2>&1; echo ---; robotcode -p ci discover tests
Dry run, not executing any commands. Would execute robot with the following options and arguments:
variable = ['BASE_URL:https://staging.shop.example', 'BROWSER:chromium', 'HEADLESS:true']
outputdir = 'results/ci'
pythonpath = ['libraries']
tests
…
```

More on profiles: [Profiles](/guides/robot-toml/profiles/) and the [`robot.toml` reference](/reference/config/).

## What to watch out for

- **Settings come from several places.** A `robot.toml` for your user, the project's `robot.toml` and the selected profiles add up. `robotcode config show -s` shows where each value comes from.
- **The profile goes before the subcommand.** In the CI workflow, it is `robotcode -p ci robot`, not `robotcode robot -p ci`.

## The sessions

<!-- session: a-profile-for-the-ci-server -->
<details class="rc-session-details">
<summary>A profile for the CI server <span>“Add a profile for our CI server: the staging shop, a browser without a window, and the results in <code>results/ci</code>.”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Add a profile for our CI server: the staging shop, a browser without a window, and the results in `results/ci`.

</div>

*Loaded the skill `robotcode:robotcode`*

*…*

````console
$ robotcode config info desc output-dir | head -20
# robot.toml configuration settings

## output-dir

Type: `str | StringExpression | None`

Where to create output files. The default is the
directory where tests are run from and the given path
is considered relative to that unless it is absolute.

…
````

```console
$ python - <<'EOF'
p='robot.toml'
s=open(p).read()
s=s.replace('BROWSER = "chromium"\n','BROWSER = "chromium"\nHEADLESS = "false"\n')
s=s.replace('[profiles.ci]\ndescription = "Staging shop"\n','[profiles.ci]\ndescription = "CI server: staging shop, headless browser"\noutput-dir = "results/ci"\n')
s=s.replace('BASE_URL = "https://staging.shop.example"\n','BASE_URL = "https://staging.shop.example"\nHEADLESS = "true"\n')
open(p,'w').write(s)
EOF
cat robot.toml; robotcode -p ci config show; robotcode -p ci discover suites | tail -5; robotcode -p dev config show | grep -A4 variables
paths = ["tests"]
python-path = ["libraries"]
output-dir = "results"

[variables]
BASE_URL = "http://localhost:8080"
BROWSER = "chromium"
HEADLESS = "false"

[profiles.dev]
description = "Local shop in Firefox"
extend-variables = { BROWSER = "firefox" }

[profiles.ci]
description = "CI server: staging shop, headless browser"
output-dir = "results/ci"

[profiles.ci.extend-variables]
BASE_URL = "https://staging.shop.example"
HEADLESS = "true"


…
```

```console
$ robotcode -p ci --dry robot 2>&1 | tail -5
Dry run, not executing any commands. Would execute robot with the following options and arguments:
variable = ['BASE_URL:https://staging.shop.example', 'BROWSER:chromium', 'HEADLESS:true']
outputdir = 'results/ci'
pythonpath = ['libraries']
tests
```

<div class="rc-session-answer">

**Agent:** There was already a `ci` profile pointing at the staging shop, so I extended it instead of adding a second one. Your CI server already runs `robotcode -p ci robot`, so it picks this up as is. I checked with a dry run of `robotcode -p ci robot`: it would use `BASE_URL:https://staging.shop.example`, `HEADLESS:true` and `outputdir = 'results/ci'`. I haven't run any tests with it.

Changes in `robot.toml`:

```toml
[variables]
...
HEADLESS = "false"

[profiles.ci]
description = "CI server: staging shop, headless browser"
output-dir = "results/ci"

[profiles.ci.extend-variables]
BASE_URL = "https://staging.shop.example"
HEADLESS = "true"
```

- **Headless:** the project had no way to set this yet, so I added a `HEADLESS` variable. It's `false` by default, so local and `dev` runs still open a window, and `true` under `ci`.
- **Results:** `ci` now writes to `results/ci`. Other runs still write to `results/`.

Two things you should know:

1. **Nothing uses `HEADLESS` yet.** No keyword in `resources/` opens a browser at the moment; the suites run against the in-memory `ShopLibrary`. When you add the Browser library steps, pass the variable through for headless mode to take effect: `New Browser    ${BROWSER}    headless=${HEADLESS}`.
2. **The CI workflow can't run browser tests as it stands.** `.github/workflows/tests.yml` only runs `pip install robotframework robotcode[runner]`. It doesn't install the Browser library or run `rfbrowser init`, and it doesn't use the project's uv environment. The current tests don't need any of that. Browser tests will, so I can update the workflow when you get there.

</div>

<div class="rc-session-prompt">

**You:** Show me what a run with that profile gets.

</div>

```console
$ robotcode -p ci --dry robot 2>&1; echo ---; robotcode -p ci discover tests
Dry run, not executing any commands. Would execute robot with the following options and arguments:
variable = ['BASE_URL:https://staging.shop.example', 'BROWSER:chromium', 'HEADLESS:true']
outputdir = 'results/ci'
pythonpath = ['libraries']
tests
---
# Tests

…
- _Suites:_ 5
- _Suites with tests:_ 4
- _Tests:_ 13
```

<div class="rc-session-answer">

**Agent:** With the `ci` profile, `robotcode -p ci robot` would hand Robot Framework these options. I got them from a dry run and a test discovery; I didn't run the tests.

| Setting | Value |
|---|---|
| `BASE_URL` | `https://staging.shop.example` (from `ci`) |
| `HEADLESS` | `true` (from `ci`) |
| `BROWSER` | `chromium` (default) |
| Output dir | `results/ci` (from `ci`) |
| Python path | `libraries` |
| Paths | `tests` |

The profile doesn't filter by tags, so it runs all **13 tests** in 4 suites:

- **Cart:** Add Item To Cart, Remove Item From Cart, Cart Total Adds Up
- **Login:** Login Works, Logout Works, Login With A Wrong Password Fails
- **Orders:** Order Coffee, Express Order, Sold Out Product Cannot Be Ordered
- **Search:** Find Coffee, Find Tea, Find Several, Find Nothing

Right now `BASE_URL` changes only the "Shop URL" metadata and a log message, because the tests run against the in-memory `ShopLibrary`. It will start to matter once Browser library tests use it. If CI should run only the smoke tests, I can add `includes = ["smoke"]` to the profile.

</div>

</div>

</details>
<!-- /session -->
