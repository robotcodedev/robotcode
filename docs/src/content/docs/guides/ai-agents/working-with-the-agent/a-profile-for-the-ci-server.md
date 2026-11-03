---
title: A Profile for the CI Server
description: "Step 7 of the tutorial: let the agent write a CI profile in robot.toml, and check it with profiles show, a dry run and discover."
sidebar:
  label: 7. A Profile for the CI Server
  order: 150.47
---

Finally, set up how CI runs the tests: a profile in `robot.toml` with the system to test, a browser without a window and a folder for the results. The agent finds out how the settings work, writes the profile and checks the result before CI runs it.

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

`robotcode config info desc <key>` prints a setting's type, its description and a TOML example. The skill tells the agent to read it before it writes a setting, instead of guessing. In the session *A profile for the CI server*, the agent didn't call it: it read the skill's reference on configuration, and `output-dir` and the variables were already in `robot.toml`. Ask for it when you want to know what a setting does.

### It extends what is there

The project already had a `ci` profile, so the agent extended it instead of adding a second one:

<!-- excerpt: a-profile-for-the-ci-server -->
> The `ci` profile is already there, and it's the one the CI server runs (`robotcode -p ci robot`). I'll extend it, because a second profile wouldn't be picked up by the workflow.

A profile in `[profiles.<name>]` adds to the top-level settings of `robot.toml` when you select it.

### It checks the result without running the tests

`robotcode -p ci profiles show` shows the configuration with the profile, a dry run with `--dry` the options and arguments `robot` would get, and `robotcode -p ci discover tests` the tests the profile includes. From the session:

<!-- excerpt: a-profile-for-the-ci-server -->
```console
$ robotcode -p ci profiles show; echo "--- dry"; robotcode -p ci --dry robot; echo "exit=$?"; echo "--- discover"; robotcode -p ci discover info 2>&1 | head -20; robotcode -p ci discover tests 2>&1 | tail -5
…
--- dry
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
- **A setting only counts if something uses it.** In the session, the agent pointed out that the new setting has no effect yet:

  <!-- excerpt: a-profile-for-the-ci-server -->
  > The CI profile now has all three settings, but the headless setting does nothing yet because no test opens a browser. The change is in `robot.toml` and isn't committed.

## The sessions

<!-- session: a-profile-for-the-ci-server -->
<details class="rc-session-details">
<summary>A profile for the CI server <span>“Add a profile for our CI server: the staging shop, a browser without a window, and the results in <code>results/ci</code>.”</span></summary>

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Add a profile for our CI server: the staging shop, a browser without a window, and the results in `results/ci`.

</div>

*Loaded the skill `robotcode:robotcode`*

```console
$ cat robot.toml; echo ---; cat .github/workflows/tests.yml; echo ---; ls -a; git log --stat | head -40; grep -rn "BASE_URL\|HEADLESS\|BROWSER\|headless" --include=* -r . --exclude-dir=.venv --exclude-dir=.git --exclude=uv.lock | head -40
paths = ["tests"]
python-path = ["libraries"]
output-dir = "results"

[variables]
BASE_URL = "http://localhost:8080"
BROWSER = "chromium"

[profiles.dev]
description = "Local shop in Firefox"
extend-variables = { BROWSER = "firefox" }

[profiles.ci]
description = "Staging shop"

[profiles.ci.extend-variables]
BASE_URL = "https://staging.shop.example"


---
name: Tests
on: push
jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.13"
      - run: pip install robotframework robotcode[runner]
…
```

<div class="rc-session-answer">

**Agent:** A `ci` profile already exists, so I'm checking how the headless setting would actually reach the browser.

</div>

*…*

<div class="rc-session-answer">

**Agent:** The `ci` profile is already there, and it's the one the CI server runs (`robotcode -p ci robot`). I'll extend it, because a second profile wouldn't be picked up by the workflow.

</div>

```console
$ python - <<'EOF'
import re
s=open('robot.toml').read()
old='''description = "Staging shop"

[profiles.ci.extend-variables]
BASE_URL = "https://staging.shop.example"
'''
new='''description = "Staging shop, browser without a window, results in results/ci"
output-dir = "results/ci"

[profiles.ci.extend-variables]
BASE_URL = "https://staging.shop.example"
HEADLESS = "true"
'''
assert old in s
open('robot.toml','w').write(s.replace(old,new))
EOF
git diff; robotcode -p ci profiles show; echo "--- default"; robotcode profiles show; echo "--- dev"; robotcode -p dev profiles show; echo "--- run"; robotcode -p ci robot; echo "exit=$?"; ls results results/ci; robotcode results summary results/ci/output.xml 2>&1 | head; git status --short
diff --git a/robot.toml b/robot.toml
index d09d302..d4df59b 100644
--- a/robot.toml
+++ b/robot.toml
@@ -11,9 +11,11 @@ description = "Local shop in Firefox"
 extend-variables = { BROWSER = "firefox" }
 
 [profiles.ci]
-description = "Staging shop"
+description = "Staging shop, browser without a window, results in results/ci"
+output-dir = "results/ci"
 
 [profiles.ci.extend-variables]
 BASE_URL = "https://staging.shop.example"
+HEADLESS = "true"
 
 
output-dir = "results/ci"
python-path = [
    "libraries",
]
paths = [
    "tests",
]

[variables]
BASE_URL = "https://staging.shop.example"
BROWSER = "chromium"
HEADLESS = "true"
…
Tests :: Web shop acceptance tests                                    | FAIL |
13 tests, 12 passed, 1 failed
==============================================================================
Output:  ~/webshop/results/ci/output.xml
Log:     ~/webshop/results/ci/log.html
Report:  ~/webshop/results/ci/report.html
exit=1
results:
ci

results/ci:
log.html
output.xml
report.html
Usage: robotcode results summary [OPTIONS]
Try 'robotcode results summary --help' for help.

[ ERROR ] Got unexpected extra argument (results/ci/output.xml)
 M robot.toml
```

<div class="rc-session-answer">

**Agent:** One test failed, so I'm checking whether my change caused it by running it without the profile.

</div>

*…*

<div class="rc-session-answer">

**Agent:** The CI profile now has all three settings, but the headless setting does nothing yet because no test opens a browser. The change is in `robot.toml` and isn't committed.

I extended the existing `ci` profile rather than adding a new one, because `.github/workflows/tests.yml` already runs `robotcode -p ci robot`:

```toml
[profiles.ci]
description = "Staging shop, browser without a window, results in results/ci"
output-dir = "results/ci"

[profiles.ci.extend-variables]
BASE_URL = "https://staging.shop.example"
HEADLESS = "true"
```

`profiles show` confirms these values under `-p ci`, and the default and `dev` profiles are unchanged. A real run with `-p ci` wrote its output, log and report to `results/ci/`.

**Test run:** 12 of 13 tests passed. `Tests.Login.Login Works` fails with `Welcome back, alice! != Welcome back, Alice!`, and it fails the same way without the profile, so this change didn't cause it. The CI job will stay red until that's fixed; I left it alone since it's a separate question whether the shop or the test is wrong.

**Before this works in a real browser:**
- **Headless has no effect yet:** nothing in `tests/`, `resources/` or `libraries/` uses the Browser library, and the suites run against the in-memory `ShopLibrary`. For the same reason, they don't connect to the staging URL either, which only appears in a log message and the metadata. When browser tests arrive, they need to pass it on, e.g. `New Browser    ${BROWSER}    headless=${HEADLESS}`.
- **`HEADLESS` only exists under `ci`:** a keyword using it would fail with an undefined variable in other runs, so it will also need a default in the top-level `[variables]`.
- **The CI workflow is missing the Browser setup:** it installs only `robotframework robotcode[runner]`, with no Browser library and no `rfbrowser init`. Browser tests would fail there until that's added. It also uses `pip` rather than `uv sync`, so it doesn't use your locked versions.

</div>

<div class="rc-session-prompt">

**You:** Show me what a run with that profile gets.

</div>

```console
$ robotcode -p ci profiles show; echo "--- dry"; robotcode -p ci --dry robot; echo "exit=$?"; echo "--- discover"; robotcode -p ci discover info 2>&1 | head -20; robotcode -p ci discover tests 2>&1 | tail -5
output-dir = "results/ci"
python-path = [
    "libraries",
]
paths = [
    "tests",
]

[variables]
BASE_URL = "https://staging.shop.example"
BROWSER = "chromium"
HEADLESS = "true"

--- dry
Dry run, not executing any commands. Would execute robot with the following options and arguments:
variable = ['BASE_URL:https://staging.shop.example', 'BROWSER:chromium', 'HEADLESS:true']
outputdir = 'results/ci'
pythonpath = ['libraries']
tests
exit=251
--- discover
# Info

- _Robot Framework:_ 7.5.1
…
- _Python:_ 3.13.18
- _Executable:_ .venv/bin/python
- _Machine:_ x86_64
- _Platform:_ linux
- _System:_ Linux
- _System Version:_ #1 SMP PREEMPT_DYNAMIC Sat, 31 Oct 2026 06:43:52 +0000


- _Suites:_ 5
- _Suites with tests:_ 4
- _Tests:_ 13
```

<div class="rc-session-answer">

**Agent:** This is what `robotcode -p ci robot` passes to Robot Framework, from a dry run that executed nothing:

```
variable   = ['BASE_URL:https://staging.shop.example', 'BROWSER:chromium', 'HEADLESS:true']
outputdir  = 'results/ci'
pythonpath = ['libraries']
tests
```

| Setting | Value | Comes from |
|---|---|---|
| `BASE_URL` | `https://staging.shop.example` | `ci` profile, overrides `http://localhost:8080` |
| `HEADLESS` | `true` | `ci` profile, new |
| `BROWSER` | `chromium` | top-level `[variables]` |
| `output-dir` | `results/ci` | `ci` profile, overrides `results` |
| `python-path` | `libraries` | top-level |
| `paths` | `tests` | top-level |

The run selects all 13 tests in 4 suites, with no tag filters. These values match the earlier real run, which wrote to `results/ci/`.

The dry run's exit code of 251 comes from the dry run itself, not from a test result.

</div>

</div>

</details>
<!-- /session -->
