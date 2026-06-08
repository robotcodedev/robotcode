# Configuration: `robot.toml` and profiles

`robot.toml` centralizes a Robot Framework project's settings — paths, variables, output options, and environment-specific **profiles** — so they live in version control instead of scattered argument files or CLI flags. `robotcode` honors it for every command (`robot`, `discover`, `robot-debug`, …).

## Contents

- What goes in it
- Computed values (`expr` / `if`)
- Where config lives, and the loading order
- Profiles
- Common patterns
- Gotchas

## What goes in it

Every `robot` / `rebot` command-line option is a key (multi-word options use hyphens: `--outputdir` → `output-dir`), plus RobotCode-specific settings:

```toml
output-dir = "results"
log-level = "INFO"
languages = ["en", "fi"]
paths = ["tests"]            # so `robotcode robot` needs no path argument

[variables]
BROWSER = "Chrome"
LOGIN_URL = "https://example.com/login"
```

Don't memorize or guess keys — the catalog is the tool:

- `robotcode config info list` — every settable key (including `[profile].*` and the `extend-*` twins).
- `robotcode config info desc <key>` — type, description, and a TOML example. Wildcards work: `config info desc "*tag*"`, `config info desc "rebot.*"`.
- `robot --help` — the underlying Robot Framework options these keys mirror.

`config info desc <key>` is the authoritative source whether you're **explaining** a setting (its meaning and accepted type) or **editing** one. When editing, the reliable loop is **look up (`config info desc`) → write the TOML → verify (`config show`)** — don't hand-write keys from memory. When explaining a setting's *value*, note that `config show` reports what is actually in effect and a profile can override the top-level value, so use `robotcode --profile <name> config show` (or `config show -s` to attribute each setting to its file/profile) to report the value under the active profile rather than just the default.

## Computed values: `expr` and `if`

A value doesn't have to be a literal. Wherever a setting is a string (its type from `config info desc` contains `StringExpression`), a list item, a dict value, or a `[variables]` entry, you can supply an **expression** instead — an inline table `{ expr = "<python expression>" }` that RobotCode evaluates once when it resolves the config:

```toml
output-dir = { expr = "f'results/{date.today()}'" }

[variables]
BUILD = { expr = "environ.get('BUILD_ID', 'local')" }
```

Profiles add a **condition**: `enabled` and `hidden` take `{ if = "<python expression>" }` (or the dotted form `enabled.if = "..."`), evaluated as a boolean — this is how a profile switches itself on only on CI, on a given OS, and so on:

```toml
[profiles.ci]
enabled.if = "environ.get('CI') == 'true'"
```

These are **not** arbitrary Python. The string must be a single *expression* (no statements, assignments, imports, or semicolons), and only two groups of names are in scope:

- the config globals — `environ`, `re`, `platform`, `datetime`, `date`, `time`, `timedelta`, `timezone`, `Path` (so the typical uses are environment- and platform-driven config); and
- standard safe built-ins — type constructors (`str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, `bytes`) and common functions (`len`, `min`, `max`, `sum`, `sorted`, `reversed`, `range`, `enumerate`, `zip`, `map`, `filter`, `abs`, `round`, `format`, `ord`, `chr`, …).

Attribute and method calls on those objects are fine (`environ.get('CI')`, `platform.system()`, `Path.cwd() / 'app'`). Any other name — `os`, `open`, `__import__`, a module you weren't given a global for — is rejected when the value is evaluated, with `Name access to '<name>' is not allowed`; that error almost always means the expression reached for something outside this safe set.

When explaining such a setting, `config info desc` tells you whether it accepts an expression (the `StringExpression` in its type), and `config show` reports the **evaluated** result that is actually in effect — not the `{ expr = … }` source.

## Where config lives, and the loading order

RobotCode merges several files; a later one overrides settings from the earlier ones. Each layer has a deliberate purpose:

1. **Global user config** — a user-level `robot.toml` *outside* the repo (run `robotcode config files` for the exact path). Your machine-wide defaults across every Robot project; never committed anywhere.
2. **`pyproject.toml`** — project root, under `[tool.robot]`. Robot settings here only if you deliberately keep a single config file (see split-by-concern below).
3. **`robot.toml`** — project root; the **shared, committed** project configuration — the team's single source of truth and what makes runs reproducible. Everything the team needs to run the suite the same way belongs here, in version control.
4. **`.robot.toml`** — project root; **personal, per-developer overrides**, deliberately **git-ignored**. For local-only tweaks that must not affect teammates — a local library/browser path, an extra `python-path`, a personal `default-profiles`, a temporary `log-level`. Nothing the team relies on goes here.

**Why it is split this way.** The three layers divide responsibility on purpose. The committed `robot.toml` is the team's shared baseline — it is what makes runs reproducible, so anything the whole team needs to run the suite identically lives there, in version control. `.robot.toml` (git-ignored) and the global user config are the *personal* layers: they stay out of the repo and **can** differ from machine to machine, so a developer **can** adjust things locally — a local library/browser path, an extra `python-path`, a personal `default-profiles` — without changing what everyone else runs. They are optional; their point is to *allow* per-developer overrides, not to require them. The committed `robot.toml` stays the common baseline, and any per-machine difference comes only from these optional layers. The same split tells you where a new setting belongs: if a correct, identical run depends on it, it goes in the committed `robot.toml`; if it is a machine- or person-specific convenience, it goes in `.robot.toml` or the user-global file.

**`robot.toml` vs. `pyproject.toml` — split by concern.** Keep *Python*-project configuration (build, dependencies, and Python tools like ruff/mypy/pytest) in `pyproject.toml`, and *Robot Framework* configuration (paths, variables, profiles, RF/rebot options, RobotCode settings) in **`robot.toml`** — even when the project already has a `pyproject.toml`. RobotCode *can* read Robot settings from a `[tool.robot]` section in `pyproject.toml` (it loads before `robot.toml`, so `robot.toml` wins on conflict), but the clean practice is to keep the two apart. `robot.toml` also keeps its keys at the top level (`output-dir = "results"`, `[profiles.dev]`), so it stays flat and readable instead of nesting everything under `[tool.robot]` / `[tool.robot.profiles.<name>]`.

Inspect what is actually in play instead of guessing:

- `robotcode config files` — which config files were found and their roles/precedence.
- `robotcode config root` — the detected project root, and how it was discovered.
- `robotcode config show` — the merged, effective configuration. `--format json` for machine output; `-s` / `--single` to see each file's own contribution.

## Profiles

A profile is a named settings block (`[profiles.<name>]`) layered on top of the top-level (default) settings:

```toml
output-dir = "results"          # default — applies unless a profile overrides it

[profiles.dev]
output-dir = "results/dev"
variables = { ENVIRONMENT = "development", API_URL = "http://dev-api.example.com" }

[profiles.prod]
output-dir = "results/prod"
variables = { ENVIRONMENT = "production", API_URL = "https://api.example.com" }
```

- **`inherits`** — pull in other profiles by name: `inherits = ["base"]` (string or list).
- **`hidden` / `enabled`** — `hidden = true` keeps a profile out of listings; `enabled.if = "<python expression>"` (e.g. `enabled.if = "platform.system() == 'Windows'"`) switches it on conditionally.
- **`precedence`** — a number (default `0`); when several profiles merge, the higher-precedence one wins a conflicting scalar key.
- **`extend-` prefix** — within a merge a plain key **replaces** the accumulated value, while its `extend-` twin **appends** to it. Supported on `variables`, `include` / `exclude`, `python-path`, `metadata`, and more (check `config info`).
- **`default-profiles`** — which profile(s) apply when no `--profile` is given.

### Selecting and inspecting profiles

```bash
robotcode --profile dev robot tests/          # one profile
robotcode -p base -p "win*" robot tests/      # repeatable; each value is a glob; all matches merge
robotcode profiles list                        # defined profiles
robotcode --profile dev profiles show          # a single profile's own definition
robotcode -p base -p win config show           # the merged, effective config for a selection
```

Merge order: default (top-level) settings first → profiles by ascending `precedence` → for equal precedence, the order given on the command line.

### See a profile's effect on a run — without running

`discover` applies the resolved configuration too, so it previews exactly what a profile changes: which tests/suites are selected, and how their longnames and tags come out after the profile's `paths`, `include` / `exclude`, and name transforms.

```bash
robotcode --profile ci discover tests          # the tests this profile would run
robotcode --profile ci discover suites          # the resulting suite tree
robotcode --profile ci discover tags            # the resolved tags
robotcode discover tests                         # …compare against no profile (or `-p a` vs `-p b`)
```

The longnames it prints are exactly what you pass to `robotcode robot -bl "<longname>"` / `robotcode robot-debug -bl "<longname>"` to run or debug one test in that same resolved context.

## Common patterns

```toml
# A base profile others inherit, plus environment profiles
[profiles.base]
log-level = "INFO"
variables = { TIMEOUT = "20s" }

[profiles.dev]
inherits = ["base"]
extend-variables = { ENVIRONMENT = "development" }   # adds to base, doesn't replace

[profiles.ci]
inherits = ["base"]
extend-variables = { ENVIRONMENT = "ci" }
extend-include = ["smoke"]                            # adds to any inherited includes

# Platform-conditional profile
[profiles.windows]
enabled.if = "platform.system() == 'Windows'"
variables = { DRIVER_PATH = "C:\\drivers" }
```

## Gotchas

- **`extend-` vs. plain replaces silently.** A profile's plain `variables = { … }` *replaces* the inherited/default variables (the others are dropped); use `extend-variables` to add. Same for `include`, `python-path`, `metadata`, etc.
- **Config changes longnames.** `paths` and name-transform settings change suite/test *names* from what the files literally say — so select a single test by its `discover` / `results` **longname** (`-bl`), never by its file path. See [debugging.md](debugging.md).
- **CLI overrides config.** Flags on the command line win over `robot.toml`; use them to narrow a one-off run, not as a substitute for the config.
- **`config show` is the merged result, so it includes the user-global defaults.** A setting that isn't in the project's `robot.toml` / `pyproject.toml` is usually one of those user-level defaults (source #1 above) rather than something the project sets. `config show -s` (each file's own contribution) and `config files` show which file each setting comes from, which attributes any setting to its layer.
- **Verify, don't guess.** Confirm keys/types with `config info desc` and the merged result with `config show` — and preview a profile's selection with `discover` — before trusting an edit.
