# Discovering Tests, Tasks and Suites

Before you can run, filter, or report on a Robot Framework project you usually want to know what's actually *in* it: which suites live in which directories, what tags each test carries, which `.robot` files Robot would even pick up. **`robotcode discover`** answers those questions without executing a single test.

It applies the same configuration and profile pipeline that `robotcode robot` would use to *run* the project — so what `discover` reports is exactly what `robot` would see — and surfaces the result either as a human-readable tree on the terminal or as structured data for scripts, CI pipelines, and editors.

**Who this is for:**

- **Developers** opening an unfamiliar project who want a one-shot overview before drilling in.
- **CI/CD pipelines** that need a stable inventory of tests / tags / files for sharding, reporting dashboards, or build-time validation.
- **Editor and IDE integrations** — the JSON output is what the **RobotCode** VS Code extension consumes to build its Test Explorer view.
- **AI-driven workflows** — coding agents (Claude Code, Cursor, Copilot, …), inventory analyses, test-selection assistants. Letting the agent grep through a tree of `.robot` files is wasteful; `discover` returns just the slice the agent asked for (a tag list, a file list, the test tree under one path).
- **Test-selection scripts** that build `-bl/--by-longname` lists for `robotcode robot` — pre-filtering tests for sharded CI matrices, regression sets, or scheduled smoke runs.

Typical things you can do with it:

- get a tree view of every suite, sub-suite, test and task the active profile would discover
- list just the tests (or just the tasks) one per line, with source paths and tags
- list every distinct tag in the project with the tests it tags
- list the source files Robot Framework would even consider parsing
- check the Robot Framework version, Python version and environment the tooling is running under

The seven subcommands share the same configuration, search, and output-format pipeline — once you've learned one the others follow:

| Subcommand | Use it when you want to … |
|---|---|
| [`all`](#all-the-full-tree) | … see the whole tree (workspace → suite → sub-suite → test/task) |
| [`tests`](#tests-flat-list-of-tests) | … list tests one per line (typed `test`) |
| [`tasks`](#tasks-flat-list-of-tasks) | … list tasks one per line (typed `task`, RPA mode) |
| [`suites`](#suites-flat-list-of-suites) | … list suites only — no per-test rows |
| [`tags`](#tags-tag--tests-dictionary) | … build a `tag → [tests]` index for triage or dashboards |
| [`files`](#files-source-files-robot-would-parse) | … list every `.robot` / `.resource` file Robot would even consider |
| [`info`](#info-environment-and-version) | … check the active Robot / Python / RobotCode versions and environment |

This guide is split in two:

1. **[Part 1 — Using the commands](#quick-start)** walks through every subcommand from the terminal perspective: what it does, what shows up on the screen, and what filters and flags are available.
2. **[Part 2 — JSON reference](#json-reference)** documents the structured output for scripts, CI pipelines, and editor integrations — the JSON schema of every subcommand plus jq-based recipes.

For the exhaustive option list see the auto-generated [CLI reference](cli.md#discover).

## Quick start

```bash
# Workspace tree — every suite, every test, with tags
robotcode discover all

# Flat list of tests, one per line
robotcode discover tests

# Just the test names matching "Login", in the current profile's scope
robotcode discover tests --search Login

# A tag → tests dictionary
robotcode discover tags

# Which source files would Robot even parse?
robotcode discover files

# Active Robot / Python / RobotCode versions + environment
robotcode discover info
```

If you don't pass paths or filters, `discover` falls back to the **default paths from your active `robot.toml` profile** — the same logic `robotcode robot` uses.

## How `discover` finds your project

`discover` runs the same configuration pipeline as `robotcode robot`:

1. **Profile resolution.** `robot.toml` is loaded and combined with any `--profile` selectors. The resulting profile contributes the default paths (`paths = [...]`), variables, library paths, and any other Robot Framework settings.
2. **Argument layering.** Positional `ROBOT_OPTIONS_AND_ARGS` you pass on the command line are appended *after* the profile's settings — Robot's normal precedence rules apply. So `robotcode discover tests --include smoke ./tests/login` picks up the profile's `paths` *unless* you give explicit paths (then those win), and adds `--include smoke` on top of any profile-level includes.
3. **Static parsing only.** `discover` never executes a keyword. It walks the suite tree the same way Robot's `--dryrun` would but stops earlier — at parse time. Library imports, variable files, listeners, and pre-run modifiers are loaded only as far as needed to resolve the tree.

If you want to discover something *outside* your profile (a one-off file, a specific directory), pass it as a positional argument:

```bash
robotcode discover tests path/to/suite.robot
robotcode discover all path/to/dir/ path/to/other/
```

You can also pass any standard `robot` argument through — `--include`, `--exclude`, `--suite`, `--test`, `--variable`, `--pythonpath`, … See [Robot-native filters](#robot-native-filters) below.

## Output formats

The default TEXT output is meant for humans reading in a terminal — colourised, paginated. For pipelines, scripts, editor integrations, and AI agents, the global `-f/--format` flag — set **before** the subcommand — switches to a stable structured format:

```bash
robotcode discover all                       # default: human-readable TEXT
robotcode --format json discover all         # compact JSON, one line
robotcode --format json_indent discover all  # pretty-printed JSON
robotcode --format toml discover all         # TOML
```

If you only ever look at terminal output, the following sections cover everything you need. For the JSON shape of any subcommand, jump to the [JSON reference](#json-reference).

Pager and colour handling is identical to `results` — see [Pager and colour](analyzing-results.md#pager-and-colour-in-the-terminal) for the details.

## `all` — the full tree

`all` prints the complete hierarchy the active profile resolves to: the workspace root, every suite and sub-suite below it, and every test or task inside those suites. It's the closest thing to "show me what's in this project".

```bash
robotcode discover all
robotcode discover all ./tests/login        # restrict to a path
robotcode discover all --include smoke      # restrict to a tag
```

Sample output:

```
Suite: MyProject (tests/)
    Suite: MyProject.Login (tests/login/)
        Test: MyProject.Login.Bad Password (tests/login/test_login.robot:14)
            Tags: regression, smoke
        Test: MyProject.Login.Good Password (tests/login/test_login.robot:22)
            Tags: smoke

Statistics:
  - Suites: 4
  - Suites with tests: 3
  - Tests: 18
```

### Flag reference

| Flag | Effect |
|---|---|
| `--tags / --no-tags` | Show or hide the `Tags:` line under each test/task. **Default: on.** |
| `--full-paths / --no-full-paths` | Absolute source paths. Default: relative to cwd. |
| `--search TEXT` / `--search-regex PATTERN` | Prune the tree to tests matching the pattern; surviving tests keep their full ancestor chain. See [Search](#search). |
| `-bl NAME` / `-ebl NAME` | Include/exclude tests, tasks or suites by exact long name. See [Robot-native filters](#robot-native-filters). |
| *any standard `robot` flag* | `--include`, `--exclude`, `--suite`, `--test`, `--variable`, `--pythonpath`, … passed through to the discovery pipeline. |

A diagnostics footer is added to TEXT output when parsing emits warnings or errors (deprecated section headers, duplicate test names, unparseable files). In JSON they land in the `diagnostics` field — see [diagnostics](#diagnostics).

## `tests` — flat list of tests

`tests` collapses the hierarchy: one row per test, with full long name and source location. The natural input for scripts that need a list of test identifiers.

```bash
robotcode discover tests
robotcode discover tests --tags                 # add a `Tags: ...` line per test
robotcode discover tests --include smoke        # filter by tag
robotcode discover tests --search "Login"       # substring search
robotcode discover tests path/to/suite.robot    # one suite only
```

Sample output:

```
Test: MyProject.Login.Bad Password (tests/login/test_login.robot:14)
Test: MyProject.Login.Good Password (tests/login/test_login.robot:22)
Test: MyProject.Checkout.Empty Cart (tests/checkout/test_checkout.robot:8)
```

### Flag reference

| Flag | Effect |
|---|---|
| `--tags / --no-tags` | Include a `Tags:` line per test. **Default: off** (tests are always one-line in TEXT). |
| `--full-paths / --no-full-paths` | Absolute source paths. |
| `--search TEXT` / `--search-regex PATTERN` | Filter by name/source/body/tags. |
| `-bl NAME` / `-ebl NAME` | Long-name include/exclude. |
| *any standard `robot` flag* | Pass-through. |

Tasks defined with `*** Tasks ***` are intentionally **not** in this list — use [`tasks`](#tasks-flat-list-of-tasks) for those.

## `tasks` — flat list of tasks

`tasks` is the RPA twin of `tests`: one row per task. The TEXT output and flag set mirror `tests`; only the row label differs (`Task: …`).

```bash
robotcode discover tasks
robotcode discover tasks --tags
```

In a mixed-mode suite (rare — Robot doesn't recommend it), `tests` shows the `*** Test Cases ***` half and `tasks` shows the `*** Tasks ***` half. A project where the active `robot.toml` profile sets `rpa = true` puts everything under `tasks`.

## `suites` — flat list of suites

`suites` lists every suite the active profile resolves, one per line, no per-test detail. Useful when you want to know *which suites exist* without scrolling past hundreds of tests, or to build a suite-by-suite shard plan for CI.

```bash
robotcode discover suites
robotcode discover suites --include smoke    # only suites with a smoke test
```

Sample output:

```
MyProject (tests/)
MyProject.Login (tests/login/)
MyProject.Checkout (tests/checkout/)
```

A suite with no surviving tests after filtering disappears from the list — `--include smoke` against a suite where nothing is tagged `smoke` will drop that suite.

## `tags` — tag → tests dictionary

`tags` builds an index of every distinct tag in the discovered suite tree. The default TEXT output is the tag list alone; `--tests` and `--tasks` expand each tag with the tests / tasks it covers.

```bash
robotcode discover tags                     # just the tags
robotcode discover tags --tests             # tag → tests, indented
robotcode discover tags -i smoke            # tags appearing in the smoke subset
robotcode discover tags --not-normalized    # keep the original tag spelling
```

Sample output (`--tests`):

```
smoke
    Test: MyProject.Login.Good Password (tests/login/test_login.robot:22)
    Test: MyProject.Login.Bad Password (tests/login/test_login.robot:14)
regression
    Test: MyProject.Login.Bad Password (tests/login/test_login.robot:14)
```

### Flag reference

| Flag | Effect |
|---|---|
| `--normalized / --not-normalized` | Whether tag keys are normalised (lowercase, no whitespace, no underscore). **Default: on.** `Bug 1` / `bug_1` / `BUG1` collapse to a single `bug1` entry; with `--not-normalized` the three variants stay separate. |
| `--tests / --no-tests` | Add the tests carrying each tag. Default: off. |
| `--tasks / --no-tasks` | Add the tasks carrying each tag. Default: off. |
| `--full-paths` | Absolute source paths in the expanded child rows. |
| `--search TEXT` / `--search-regex PATTERN` | Filter the underlying test set first; only tags surviving on at least one matching test appear. |
| `-bl` / `-ebl` / *any `robot` flag* | Pass-through. |

### Normalisation in practice

The `--normalized` default matches Robot Framework's own tag-matching semantics: `--include "bug 1"` matches tests tagged `bug_1` or `BUG1`. Disable it (`--not-normalized`) when you want to **audit tag hygiene** — three distinct dict keys for `Bug 1` / `bug_1` / `BUG1` make accidental variants pop.

## `files` — source files Robot would parse

`files` lists every `.robot` and `.resource` file Robot Framework would even consider loading from the given paths (or the profile's default paths), honouring `.gitignore` / `.robotignore`.

```bash
robotcode discover files                          # respects profile paths
robotcode discover files ./tests ./resources      # explicit directories
robotcode discover files --search "checkout"      # filename substring filter
```

Sample output:

```
tests/login/test_login.robot
tests/login/resources/login_keywords.resource
tests/checkout/test_checkout.robot
```

Files under directories ignored by `.gitignore` / `.robotignore` are excluded automatically. Use this when you need to feed a list of files into another tool (linter, formatter, custom pre-commit hook) and want exactly the set Robot would walk.

### Flag reference

| Flag | Effect |
|---|---|
| `--full-paths / --no-full-paths` | Absolute paths. Default: relative to cwd. |
| `--search TEXT` / `--search-regex PATTERN` | Filter by path/filename substring or regex. |

## `info` — environment and version

`info` reports the versions and platform `robotcode` is running under — useful for bug reports, CI metadata, and "does this build have the right Robot version" checks.

```bash
robotcode discover info
robotcode --format json discover info
```

TEXT output:

```
robot_version_string: 7.4.2
robotcode_version_string: 1.6.0
python_version_string: 3.13.2
executable: .venv/bin/python
platform: linux
system: Linux
…
```

Set `ROBOT_OPTIONS`, `ROBOT_SYSLOG_FILE`, `ROBOT_SYSLOG_LEVEL` or `ROBOT_INTERNAL_TRACES` and they're echoed back under `robot_env`, so you can verify the run environment matches expectations.

> **Note:** `info` is the only `discover` subcommand whose JSON keys use `snake_case` (e.g. `robot_version_string`) rather than the `camelCase` used everywhere else. This matches the underlying `platform` / `sys` field names and is intentional.

## Robot-native filters

Every `discover` subcommand (except `info` and `files`) passes through to Robot Framework's own filtering machinery. Anything you'd write on a `robot` command line works here:

| Flag | Effect |
|---|---|
| `-i / --include TAG_PATTERN` | Include tests with a matching tag. Supports Robot's `AND`/`OR`/`NOT` syntax and globs (`*`, `?`). |
| `-e / --exclude TAG_PATTERN` | Exclude tests with a matching tag. |
| `-s / --suite NAME` | Limit to suites whose name matches the glob. |
| `-t / --test NAME` | Limit to tests whose name matches the glob (`--task` is the RPA alias). |
| `-bl / --by-longname NAME` | Exact long-name include — no glob expansion. |
| `-ebl / --exclude-by-longname NAME` | Exact long-name exclude. |
| `--variable NAME:VALUE`, `--pythonpath PATH`, … | Anything else Robot accepts. |

Filters compose — `--include smoke --exclude wip` means "smoke and not wip".

### `--by-longname` vs `--suite` / `--test`

- `-s` / `-t` are **glob** matches.
- `-bl` / `-ebl` are **exact** matches against the full long name. They mirror `robotcode robot --by-longname` so you can hand the same names to `robot` and `discover`.

Use `-bl` when you have a precise name (often pasted from a failure list or a build log); use `-s/-t` when you want pattern matching.

## Search

`--search` and `--search-regex` are **mutually exclusive** (passing both is a usage error). They prune the discovered tree to tests matching the pattern; surviving tests keep their full ancestor chain so `discover all --search Login` still shows `MyProject → MyProject.Login → Login.Bad Password` with sibling suites pruned.

The search applies across:

- the test's `name` and full long name
- the test's `source` path
- the test's `[Documentation]`, `[Template]` and `[Timeout]`
- the test's tags (Robot's normalisation rules apply)
- every keyword call's name, arguments and assigned variables inside the test body
- FOR/WHILE/IF conditions, VAR/RETURN values, EXCEPT patterns, GROUP names
- any ancestor suite's `Documentation` or `Metadata` — a hit on a suite-level field keeps every test underneath it

| Flag | Semantics |
|---|---|
| `--search TEXT` | Case-insensitive substring match. No metacharacters; `[` and `*` are literal. |
| `--search-regex PATTERN` | Python regex, **case-sensitive** by default. Prefix with `(?i)` for case-insensitive matching. |

Tag targets are matched with normalisation (lowercase, whitespace and underscores ignored), so `--search "bug 1"` matches tests tagged `bug_1`, `Bug1`, or `BUG 1`. All other targets are matched literally.

```bash
robotcode discover tests --search "Login"
robotcode discover all --search-regex 'Login.*(Bad|Good)'
robotcode discover tests --search-regex '(?i)checkout'
robotcode discover tags --search smoke
robotcode discover files --search "_keywords"
```

### Highlighting in the terminal

Matches are highlighted inline in the TEXT output with a yellow background so they're easy to scan. Structured output (JSON/TOML) is unchanged — searching only filters, it doesn't add markup.

### Search on `tags` and `files`

`--search` works on these too:

- **`tags`** filters the underlying tests first; tag keys whose tests are all dropped disappear from the dictionary. So `discover tags --search Login` is "what tags are involved in the Login subset".
- **`files`** matches the filename / path itself — no body inspection. So `discover files --search "_keywords"` is "every file whose path contains `_keywords`".

### Invalid patterns

An unparseable regex (e.g. `[unclosed`) yields a usage error pinpointing where the pattern failed to compile. The command exits non-zero before parsing any suite.

## Tips for terminal use

- **Quote your globs.** `--suite "*.Login.*"` and `--test "Test ?"` need quotes so the shell doesn't expand them against the local filesystem first.
- **`-bl` is for exact names, `-t` is for patterns.** When you copy a test long-name out of another tool's output, `-bl` is usually what you want — no need to escape glob characters.
- **Pre-filter before piping into `robot`.** `robotcode discover tests --include smoke -f json | jq -r '.items[].longname'` gives you a stable list of long names you can hand back to `robotcode robot -bl ...` for sharded CI runs.
- **Parse errors don't stop discovery.** Files with syntax errors still appear in the tree; their problems land in the [`diagnostics`](#diagnostics) field. Pipe through `--format json` and check `.diagnostics` for build-time gating.

---

# JSON reference

When you set `-f json` (or `-f json_indent` for pretty-printed, or `-f toml`) between `robotcode` and the subcommand, every `discover` command emits structured data instead of the terminal-formatted text. This is what CI pipelines, scripts, editor integrations, and AI agents consume.

```bash
robotcode --format json discover all
robotcode --format json discover tests --include smoke
robotcode --format json discover tags --tests
```

## Schema rules

A few rules hold across every subcommand (with one exception called out below):

- **camelCase keys.** `fullName`, `relSource`, `needsParseInclude`, etc. *Exception:* `info` uses `snake_case` to match the underlying `platform` / `sys` field names.
- **Optional fields are omitted, not `null`.** A `null` literal never appears. If a field has no value (a test with no tags, a suite with no children), the key is simply absent.
- **Empty array ≠ missing field.** A field listed in the schema may be `[]` if the section "exists but is empty"; a field absent entirely means the section wasn't computed for this run. `// []` in jq smooths over the difference.
- **Stability.** Fields are appended over time, never renamed or removed in place. Existing consumers keep working.

## `TestItem` — the common shape

Every subcommand that returns tests/tasks/suites uses the same `TestItem` schema:

```json
{
  "type": "test",
  "id": "/abs/path/test_login.robot;MyProject.Login.Bad Password;42",
  "name": "Bad Password",
  "longname": "MyProject.Login.Bad Password",
  "lineno": 42,
  "uri": "file:///abs/path/test_login.robot",
  "relSource": "tests/login/test_login.robot",
  "source": "/abs/path/test_login.robot",
  "needsParseInclude": true,
  "tags": ["smoke", "regression"],
  "range": {
    "start": { "line": 41, "character": 0 },
    "end":   { "line": 41, "character": 0 }
  },
  "children": [ /* nested TestItems for type=suite/workspace */ ],
  "description": "Test docstring (when set)",
  "error": "Parse error message (when this item failed to parse)",
  "rpa": false
}
```

Field notes:

- `type` is one of `"workspace"`, `"suite"`, `"test"`, `"task"`. `workspace` is the synthetic root that wraps the actual project directory.
- `id` is a stable identifier (`source;longname;lineno` for tests/tasks; `source;longname` for suites). Editor integrations use this to track which `TestItem` corresponds to which on-disk artefact across reloads.
- `lineno` is 1-based; `range.start.line` / `range.end.line` are 0-based (LSP convention). Both refer to the same line of source.
- `uri` is a `file://` URI of the source file — same format the Language Server Protocol uses.
- `needsParseInclude` is true when re-parsing this item requires re-running Robot 6.1+'s include-resolution pass (resource-file `Library` imports with arguments).
- `tags` are normalised (`Bug 1`, `bug_1`, `Bug1` all come through as `"bug1"`) and only present when the item has at least one tag.
- `children` is the nested-tree field — present on `workspace` and `suite` items, absent on `test` / `task`.
- `range` follows the LSP `Range` shape so editors can highlight the source span.

## `all` / `tests` / `tasks` / `suites` JSON

All four subcommands wrap their items in a `ResultItem`:

```json
{
  "items": [ /* TestItem(s) */ ],
  "diagnostics": { /* see below */ },
  "filtersApplied": { "search": "Login" }
}
```

Per subcommand:

- **`all`** — `items` has exactly one entry: the `workspace` root, whose `children` is the suite tree.
- **`tests`** / **`tasks`** — `items` is a flat list of `test` / `task` entries respectively.
- **`suites`** — `items` is a flat list of `suite` entries (no children — drill into the source files separately if you want per-suite tests).

`diagnostics` and `filtersApplied` are both optional and absent when empty / unused.

## `tags` JSON

```json
{
  "tags": {
    "bug1": [ /* TestItems carrying this tag */ ],
    "smoke": [ /* … */ ]
  },
  "filtersApplied": { "include": ["smoke"] }
}
```

Field notes:

- `tags` is always an object — possibly empty `{}` if no tag survived the filter chain.
- Keys are tag names; normalised by default, original spellings preserved with `--not-normalized`.
- Each value is an array of `TestItem` objects (the tests / tasks carrying that tag).
- A test with `n` tags appears in `n` entries.

## `files` JSON

```json
[
  "tests/login/test_login.robot",
  "tests/login/resources/login_keywords.resource",
  "tests/checkout/test_checkout.robot"
]
```

`files` is a plain JSON array of path strings — relative to cwd by default, absolute with `--full-paths`. No wrapper object, no per-file metadata. If you need richer info, use `discover all` and walk the tree.

## `info` JSON

```json
{
  "robot_version_string": "7.4.2",
  "robot_env": {
    "ROBOT_OPTIONS": "--include smoke"
  },
  "robotcode_version_string": "1.6.0",
  "python_version_string": "3.13.2",
  "executable": ".venv/bin/python",
  "machine": "x86_64",
  "processor": "x86_64",
  "platform": "linux",
  "system": "Linux",
  "system_version": "#1 SMP …"
}
```

Field notes:

- **Snake-case keys**, deliberately — see the schema note above.
- `robot_env` echoes back any of `ROBOT_OPTIONS`, `ROBOT_SYSLOG_FILE`, `ROBOT_SYSLOG_LEVEL`, `ROBOT_INTERNAL_TRACES` that were set, and is absent (or `{}`) when none of them are.

## `diagnostics`

When parsing a file produces a warning or error (deprecated syntax, duplicate test names, unparseable file …), `discover all/tests/tasks/suites` reports it as an LSP-style diagnostic keyed by the source's `file://` URI:

```json
"diagnostics": {
  "file:///abs/path/parse_error.robot": [
    {
      "range": { "start": { "line": 13, "character": 0 },
                 "end":   { "line": 13, "character": 0 } },
      "message": "Singular section headers like '*** Keyword ***' are deprecated. Use plural format like '*** Keywords ***' instead.",
      "severity": 2,
      "code": "discover",
      "source": "robotcode.discover"
    }
  ]
}
```

Field notes:

- `severity` follows LSP's enum: `1` = Error, `2` = Warning, `3` = Information, `4` = Hint.
- A file whose parser failed entirely still contributes whatever tests Robot could recover; the unrecoverable parts come through here.
- `diagnostics` is omitted when nothing fired.

## `filtersApplied`

Every subcommand that accepts search flags includes a `filtersApplied` field when one was set:

```json
"filtersApplied": {
  "search": "Login"
}
```

```json
"filtersApplied": {
  "search-regex": "(?i)login"
}
```

The Robot-native filters (`--include`, `--exclude`, `--suite`, `--test`, `-bl`, `-ebl`) are **not** echoed here — they're handed straight to Robot Framework's filter pipeline and the effect is visible in the surviving `items` set.

## CI recipes

A grab-bag of jq-based recipes. Pin `-f json` between `robotcode` and the subcommand to lock the format.

### Build a shard plan

```bash
# List of suite long names → fed into a CI matrix
robotcode --format json discover suites \
  | jq -r '.items[].longname'

# Long names of every smoke test
robotcode --format json discover tests --include smoke \
  | jq -r '.items[].longname'
```

### Fail the build on parse errors

```bash
robotcode --format json discover all \
  | jq -e '(.diagnostics // {}) | map(.[] | select(.severity == 1)) | length == 0'
```

### List every file the test pipeline would touch

```bash
robotcode --format json discover files | jq -r '.[]'
```

### Build a tag report

```bash
# tag → count of tests carrying it
robotcode --format json discover tags \
  | jq '.tags | map_values(length)'

# Tags with fewer than 3 tests (candidates for cleanup)
robotcode --format json discover tags \
  | jq '.tags | to_entries | map(select(.value | length < 3)) | from_entries'
```

### Check the Robot version in CI

```bash
robotcode --format json discover info | jq -r .robot_version_string
```

### Find tests touched by a specific keyword

```bash
# Every test whose body calls `Open Browser`
robotcode --format json discover tests --search "Open Browser" \
  | jq -r '.items[].longname'
```

---

For the per-flag reference, see the auto-generated [CLI reference](cli.md#discover).
