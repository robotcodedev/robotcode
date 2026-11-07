---
title: Analyzing Run Results
description: Summarize, list, walk, aggregate, diff and compare Robot Framework run results with robotcode results in the terminal or CI, using filters, search and JSON output.
sidebar:
  label: Analyzing Results
  order: 30
---

:::tip[Installation]
The `robotcode results` command comes from the optional **`runner`** package. If it isn't installed yet, add it:

```bash
pip install "robotcode[runner]"   # or: pip install "robotcode[all]"
```
:::

Every Robot Framework run leaves a result file behind that captures everything the run did — counts, statuses, messages, the per-test keyword tree, timing. `report.html` and `log.html` are the visual face of that data; **`robotcode results`** is the scriptable one. Same data, on the terminal or in a pipeline, without leaving the shell.

**Who this is for:**

- **Developers** triaging failures from the terminal — no need to open `report.html` in a browser every time something turns red.
- **CI/CD pipelines** that need machine-readable status, regression gates, or per-suite/tag dashboards. The structured output is stable enough to script against.
- **Teams** comparing runs across branches, builds or test agents — what got better, what got worse, what's new.
- **AI-driven workflows** — coding agents (Claude Code, Cursor, Copilot, …), failure-analysis assistants, statistics interpretation, automated triage and reporting. Feeding raw `output.xml` into the agent's context is wasteful in any of these — multi-megabyte input the agent then has to figure out how to parse. `robotcode results` returns just the slice the workflow asked for (counts, failing tests, messages above a level).

Typical things you can do with it:

- check the headline status of the last run in one command
- list just the failing tests, sorted by who took longest
- walk a single test's execution log, with timestamps and extracted screenshots
- aggregate results by tag or suite for reporting or dashboards
- diff two runs and find regressions
- put a series of runs side by side: flaky tests, shared failures, slower tests

The six subcommands share the same filter, search, and output-format options — once you've learned one the others follow. `diff` and `compare` read two or more result files, the others one:

| Subcommand | Use it when you want to … |
|---|---|
| [`summary`](#summary--headline-numbers) | … see the headline counts and overall status |
| [`show`](#show--list-individual-tests) | … list individual tests (with sort, filter, search) |
| [`log`](#log--walk-the-execution-tree) | … inspect the per-test execution tree |
| [`stats`](#stats--aggregate-by-tag-suite-or-status) | … aggregate by tag, suite, or status |
| [`diff`](#diff--compare-two-runs) | … compare two runs and find new failures |
| [`compare`](#compare--runs-side-by-side) | … put two or more runs side by side |

This guide is split in two:

1. **[Part 1 — Using the commands](#quick-start)** walks through every subcommand from the terminal perspective: what each one does, what shows up on the screen, and what filters and flags are available.
2. **[Part 2 — JSON reference](#json-reference)** documents the structured output for scripts, CI pipelines and AI workflows — the JSON schema of every subcommand plus jq-based recipes.

For the exhaustive option list see the auto-generated [CLI reference](/reference/cli/#results).

## Quick start

```bash
# Headline status of the latest run
robotcode results summary

# Headline status + the list of failing tests with their messages
robotcode results summary --failed

# Just the failing tests, sorted by who took longest
robotcode results show --failed --sort elapsed

# Full execution trace of every test that touches "Login"
robotcode results log --search Login

# Statistics grouped by tag (most failing tag first)
robotcode results stats --by tag

# What's broken now that wasn't broken before?
robotcode results diff baseline/output.xml
```

If you never pass `--output`, the result file is **auto-discovered** from the active `robot.toml` profile — the same logic `robotcode robot` uses to decide where to write it.

## How the result file is located

In order, `robotcode results` looks for:

1. An explicit `-o/--output PATH` argument.
   - If `PATH` is a regular file, it's used directly.
   - If `PATH` is a directory, steps 2 and 3 search inside that directory instead of the project root. Useful when CI writes timestamped output directories.
2. The output file resolved from your active `robot.toml` profile (`output-dir` / `output` settings): first exactly that file (`output.xml` by default); only if it doesn't exist, the newest timestamped variant of it (`output-*.xml` for the default name, as `--timestampoutputs` writes them), then `output.json` and the newest `output-*.json` in the same directory.
3. `output.xml`, then `output.json` in the project root.

If none of those produce a file, the command exits with an error that lists every path it tried (`No result file found. Searched: …`); an explicit `PATH` that doesn't exist gives `Result file not found: …`. If the file exists but cannot be parsed (corrupted XML, premature termination of the run), you get `failed to parse <path>: …` with the underlying parser error.

Every error that stops a `robotcode results` command exits with code `128`: these, a usage error such as an invalid option value, an invalid `robot.toml`, and an unexpected crash. So a script can tell an error apart from what a command found.

Both `output.xml` and `output.json` are supported; `robotcode results` picks the right parser automatically based on the file. (`output.json` is the RF 7.0+ opt-in format: Robot Framework writes JSON when the output file name ends in `.json`, so you get it by passing `--output output.json` to `robotcode robot` or setting `output = "output.json"` in your profile.)

:::caution[Result files with test metadata need Robot Framework 7.5 to read]
`robotcode results` reads result files with the Robot Framework version installed in your environment. A result file written by Robot Framework 7.5 or newer that contains test-level `[Metadata]` cannot be read by Robot Framework 7.4 or older — neither by `robotcode results` nor by `rebot`. The command then fails with `failed to parse <path>: … Incompatible child element 'meta' for 'test'.` — for an `output.json` read with Robot Framework 7.2–7.4 the underlying error is `… 'robot.result.TestCase' object does not have attribute 'metadata'` instead. In both cases `robotcode results` adds a hint that names the cause:

```text
The file was written by Robot Framework 7.5 or newer and contains test metadata; reading it requires Robot Framework 7.5+.
```

Analyze such files in an environment with Robot Framework 7.5 or newer.
:::

## Output formats

The default TEXT output is meant for humans reading in a terminal — colourised, paginated, with timestamps. For pipelines, scripts and AI agents the global `-f/--format` flag — set **before** the subcommand — switches to a stable structured format:

```bash
robotcode results summary                       # default: human-readable TEXT
robotcode --format json results summary         # compact JSON, one line
robotcode --format json_indent results summary  # pretty-printed JSON
robotcode --format toml results summary         # TOML
```

If you only ever look at terminal output, the following sections cover everything you need. For the JSON shape of any subcommand, jump to the [JSON reference](#json-reference).

### Pager and colour in the terminal

When the TEXT output is longer than your terminal height, `robotcode` auto-pages it through the system pager — the program named in the `PAGER` environment variable, falling back to `less` on Unix and `more` on Windows. That spares you from scrolling a multi-screen `log` listing through your shell's scrollback. Quit the pager with `q`.

Both colour and the pager auto-detect the situation:

- **Interactive shell:** colour is on, and the pager kicks in once output exceeds the terminal height.
- **Output redirected to a file or piped into another command:** both are off automatically; you get plain text on stdout.

You can override the auto-detection explicitly with the global `--pager` / `--no-pager` and `--color` / `--no-color` flags:

```bash
# Disable the pager — output streams directly to stdout
robotcode --no-pager results log

# Disable colour (the NO_COLOR=1 environment variable does the same)
robotcode --no-color results show

# Both at once — typical for CI logs
robotcode --no-color --no-pager results summary
```

The positive forms (`--pager`, `--color`) don't force either feature into a pipe: when stdout isn't a TTY, `--pager` starts no pager, and `--color` renders the TEXT output as formatted text instead of raw markdown but adds no colour codes (JSON and TOML output stays unchanged). To pipe coloured output into `less -R` yourself, set the `FORCE_COLOR=1` environment variable instead — it adds colour codes to TEXT, JSON and TOML output alike, so JSON written that way no longer parses with `jq`. On a stream whose encoding isn't UTF-8, `--color` writes the raw markdown instead.

### Characters and encodings

`robotcode` writes its own text, the headings, tables, status words and help, in plain ASCII, so the output works on any terminal or pipe. That includes a pipe on Windows, where Python writes in the ANSI code page, such as cp1252. Statuses are bold words (`**FAIL**`), arrows are `->` and omissions are `...`.

Names, messages, metadata and documentation from your project are written as they are. When they contain a character that the code page of the stream lacks, Python stops with a `UnicodeEncodeError`. Set `PYTHONUTF8=1` to write UTF-8 instead; from Python 3.15 on, that is the default.

## `summary` — headline numbers

```bash
robotcode results summary
```

Output is a short block with the overall status, the test counts, the wall-clock time, and (with `--failed`) the list of failed tests below it.

```markdown
# Summary: results/output.xml

- _Status:_ **FAIL**
- _Total:_ 42
- _Passed:_ 37
- _Failed:_ 2
- _Skipped:_ 3
- _Started:_ 2026-10-05 23:50:52
- _Ended:_ 2026-10-05 23:52:16
- _Elapsed:_ 1 min 23.4 s
- _Messages:_ 2 FAIL, 4 WARN
- _Execution messages:_ 1 WARN

## Failures (2)

- **FAIL** MyProject.Login.Bad Password (`tests/login/test_login.robot:42`)
  > AssertionError: Expected 'Login failed' but got 'Internal error'
- **FAIL** MyProject.Checkout.Empty Cart (`tests/checkout/test_empty.robot:11`)
  > TimeoutError: keyword 'Open Cart' did not complete in 5s
```

### Useful flags

| Flag | Purpose |
|---|---|
| `--failed` | Append the list of failed tests, each with its message and source location |
| `--full-paths` | Show absolute source paths instead of paths relative to the project root |

Filter flags (`--status`, `-i`, `-e`, `-s`, `-t`, `-bl`, `-ebl`) and `--search` work here too and narrow the underlying test set **before** the counts are computed. See [Filters](#filters) and [Search](#search).

## `show` — list individual tests

`show` prints one row per test with status, source location, and (for failures) the truncated failure message. Use it to scan or to pull a specific subset.

```bash
robotcode results show            # all tests, execution order
robotcode results show --top 10   # only the first 10
robotcode results show --failed   # only failures (shorthand for --status fail)
```

### Flag reference

| Flag | Effect |
|---|---|
| `--sort name\|status\|elapsed\|start\|suite` | Reorder before output. Default: execution order from the output file. |
| `--reverse` | Reverse whatever `--sort` produced. |
| `--top N` | Keep only the first `N` after sorting. The dropped count is reported as a footer line. |
| `--message-chars N` | Truncate failure messages to `N` characters (default `120`). Use `0` to disable truncation. |
| `--show-tags` | Render the test's tags in the output, in normalised form (`Bug 1`, `bug_1` and `Bug1` all show as `bug1`). |
| `--show-metadata` | Render the test's `[Metadata]` (Robot Framework 7.5+) in the output, as one `Metadata:` line (`name: value, …`) under the test. Names keep the spelling from the source file; the lines of a multi-line value are joined with a space. With an older Robot Framework version installed, `--help` does not list the flag and passing it has no effect. |
| `--timing / --no-timing` | Show / hide start time and elapsed. Default: shown. |
| `--full-paths` | Absolute source paths instead of relative. |

### Sort semantics

Each `--sort` key has a *natural* direction — the one you almost always want. `--reverse` flips it.

| Key | Natural order |
|---|---|
| `name` | Lexicographic, ascending, case-insensitive, on the full longname (`Suite.SubSuite.Test`) |
| `suite` | Lexicographic, ascending, case-insensitive, on the parent-suite longname; tests within a suite keep their original order |
| `status` | `FAIL` → `SKIP` → `PASS` → `NOT RUN` (stable within a status group) |
| `elapsed` | Longest first |
| `start` | Earliest first |

Tests with no value for the sort field (e.g. no recorded start time, no elapsed time) sort first for `start` and last for `elapsed`; `--reverse` puts them at the other end.

### Recipes

```bash
# What broke that's tagged smoke, sorted by who took longest?
robotcode results show --include smoke --failed --sort elapsed

# 10 slowest tests overall
robotcode results show --sort elapsed --top 10

# Failing tests with full message (no truncation) and tags
robotcode results show --failed --message-chars 0 --show-tags

# Find tests by name match
robotcode results show --search "TimeoutError" --show-tags

# All tests of one specific suite, in name order
robotcode results show --suite "MyProject.Login" --sort name
```

## `log` — walk the execution tree

`log` prints, for every selected test, the full execution body — keyword calls with arguments and assignments, control-flow blocks (FOR, WHILE, IF, TRY, …) with their children, iterations, individual log messages with their levels, and any artefacts (screenshots, embedded images, external file references) the run produced.

```bash
robotcode results log                      # every test, every body item
robotcode results log --failed             # only failed tests (shorthand for --status fail)
robotcode results log --search "Timeout"   # only tests matching the search
```

A test's `[Metadata]` (Robot Framework 7.5+) is printed directly under its header whenever present, as one `Metadata:` line (`name: value, …`) like `show --show-metadata` prints it — `log` needs no flag for it.

### Flag reference

| Flag | Effect |
|---|---|
| `--level TRACE\|DEBUG\|INFO\|WARN\|ERROR\|FAIL` | Suppress messages below this severity. Default: `INFO`. |
| `--max-depth N` | Collapse keyword bodies deeper than `N` levels. Default: `0` (unlimited). |
| `--extract DIR` | Decode embedded `data:` URIs and copy externally-referenced files into `DIR`. |
| `--raw-html` | Keep the original HTML markup in log messages. No artefact decoding happens in this mode. |
| `--execution-messages` | Include the messages Robot Framework reports outside the tests (library import failures, syntax errors, …). |
| `--keyword-info` | Print each executed keyword's `[Documentation]`, `[Tags]` and `[Timeout]` under its header (and add them to the JSON entry). Off by default; see [`--keyword-info` and `--suite-info`](#--keyword-info-and---suite-info). |
| `--suite-info` | Group tests under suite headers showing the suite name, source, `Documentation` and `Metadata`, with the suites above them first (and add a `suites` array plus per-test `suite` ref to the JSON). Off by default. |
| `--timestamps` | Show per-message timestamps. |
| `--timing / --no-timing` | Show / hide start times and elapsed totals. |
| `--full-paths` | Absolute source paths. |

### `--extract` directory layout

`--extract DIR` creates `DIR` if needed, then writes one subdirectory per test:

```
DIR/
├── MyProject.Login.Bad_Password/
│   ├── embedded-0.png        # first data:image/png base64 blob in the test
│   ├── embedded-1.png        # second one
│   ├── report.json           # embedded <a href="data:…" download="report.json">
│   └── screenshot.png        # external <img src="screenshot.png">
├── MyProject.Checkout.Empty_Cart/
│   └── ...
```

Test names are sanitised to filesystem-safe directory names (every run of characters other than letters, digits, `_`, `.` and `-` becomes one underscore, and leading and trailing underscores are dropped). An embedded file whose link has a `download` attribute keeps that file name, sanitised the same way and with a leading `_` when Windows reserves the name for a device (such as `con.txt`); other embedded files, and those whose name leaves nothing usable, are numbered `embedded-N`. External file references, including the files of `<video>` and `<audio>` elements such as the videos Browser records, are resolved relative to the directory containing the result file, with percent escapes such as `%20` decoded; if the referenced file doesn't exist, the artefact is recorded as skipped with reason `missing-source` and nothing is copied. A file that a test references several times is copied once, and every reference to it points to the copy, or gives the reason it was skipped. `file:` links, which OperatingSystem logs for the files it touches, count only when they point into that directory; other `file:` links, and links to folders, stay plain links in the message. References that would escape the base directory via `..` are blocked — there is no way to overwrite files outside `DIR`.

### `--raw-html` vs default

By default, log messages tagged as HTML (Robot Framework's `Log    ...    HTML`) are converted to a plain-text approximation: `<img src="data:image/png;base64,…">` becomes a placeholder like `_(embedded image — see artefacts: no alt text)_` and the actual bytes are decoded and stored separately for `--extract`. `<a href="...">link</a>` becomes a markdown-style link.

With `--raw-html` the conversion is skipped — the original HTML markup is preserved verbatim and no artefacts are extracted. Use this when you want to feed the output into something that renders HTML itself.

### `--keyword-info` and `--suite-info`

Both flags add **structured metadata** to the log output and are independent — you can pass either or both. They default to off so the standard `log` view stays compact.

**`--keyword-info`** — for every executed `KEYWORD` / `SETUP` / `TEARDOWN`, the keyword's own `[Documentation]`, `[Tags]` and `[Timeout]` (taken from the keyword definition, not the call) are emitted. In TEXT the renderer prints them as nested `_[Documentation]_` / `_[Tags]_` / `_[Timeout]_` bullets under the keyword's bullet; in JSON they appear as `doc` / `tags` / `timeout` keys on the matching body-item entry. Fields whose underlying setting is empty are dropped, so `BuiltIn.Log` (which has a docstring but no tags) shows only `doc`.

**`--suite-info`** — tests get grouped under one `## Suite:` header per parent suite, and the suites above it get a header of their own first, starting with the top suite, as in `log.html`. The header carries the suite's `fullName`, source path and executed status; below it follow the suite's `Documentation` as a `>` quote (one `>` line per line of the documentation) and one `- _Name:_ value` bullet per `Metadata` key. In JSON, `LogResult.suites` is populated with one entry per surviving suite, and every test gains a `suite` field cross-referencing the parent suite by `fullName`.

Combine both for a maximal view that mirrors the structure of the original `.robot` files:

```bash
robotcode results log --suite-info --keyword-info
```

Example TEXT output:

```markdown
# Log

## Suite: MyProject (`tests`) **FAIL**

- _Environment:_ staging

## Suite: MyProject.Login (`tests/login/test_login.robot`) **FAIL**
> Exercises the login flow against the staging environment.

- _OwnerTeam:_ identity-squad

…

### Test: MyProject.Login.Bad Password (`tests/login/test_login.robot:42`) **FAIL** _(23:51:01, 1 ms)_

_Metadata:_ Issue: 4409

> AssertionError: Expected 'Login failed' but got 'Internal error'

- **[SETUP]** **Open Browser** **PASS** _(23:51:01, 0 ms)_
  - _[Documentation]_ Launches a fresh Chromium with our shared profile.
  - _[Tags]_ `browser` `setup`
…
```

### Recipes

```bash
# Drill into one failing test
robotcode results log -bl "MyProject.Login.Bad Password"

# Walk only the FAIL-level messages of every failed test
robotcode results log --failed --level FAIL

# Top-level keyword calls only, with everything nested collapsed
robotcode results log --max-depth 1

# Pull screenshots out of a failed run
robotcode results log --failed --extract ./extracted

# Diagnose suites that broke before they even ran
robotcode results log --execution-messages --level WARN

# Full structured view — suite headers + per-keyword doc/tags/timeout
robotcode results log --suite-info --keyword-info
```

## `stats` — aggregate by tag, suite, or status

`stats` answers questions like "which tag has the worst pass rate" or "which suite is consuming most of my CI time". You pick one or more aggregation dimensions and `stats` emits one table per dimension.

```bash
robotcode results stats                          # default: by status
robotcode results stats --by tag
robotcode results stats --by suite
robotcode results stats --by tag --by suite      # two sections, in the requested order
```

Output (`--by tag --by suite`):

```markdown
# Stats

## By Tag

| Name       | Total | Pass | Fail | Skip |      Elapsed |
| ---------- | ----: | ---: | ---: | ---: | -----------: |
| regression |    34 |   29 |    2 |    3 |  1 min 9.3 s |
| bug-1842   |     2 |    0 |    2 |    0 |         1 ms |
| smoke      |    10 |    9 |    1 |    0 |      14.01 s |
| slow       |     8 |    8 |    0 |    0 | 1 min 23.3 s |

## By Suite

| Name               | Total | Pass | Fail | Skip | Elapsed |
| ------------------ | ----: | ---: | ---: | ---: | ------: |
| MyProject.Login    |    12 |   11 |    1 |    0 | 16.01 s |
| MyProject.Checkout |    14 |   12 |    1 |    1 | 34.01 s |
| MyProject.Search   |    16 |   14 |    0 |    2 | 33.32 s |
```

### Flag reference

| Flag | Effect |
|---|---|
| `--by tag\|suite\|status` | Aggregation dimension. Repeatable for multiple sections. Default: `--by status`. |
| `--sort name\|total\|failed\|elapsed` | Order groups within each section. Default: `failed` descending — most painful first. |
| `--top N` | Keep at most `N` groups per section. The dropped count is reported as a footer line. |

### Aggregation rules

- **`--by tag`**: a test with N tags counts in N buckets. Tags that differ only in case, whitespace or underscores (`Bug 1`, `bug_1`, `Bug1`) are treated as the same tag and merge into one bucket, displayed in normalised form. Tests without tags drop out — there is **no** "(untagged)" bucket. The elapsed time per group is the **sum** across all matching tests (not the average).
- **`--by suite`**: groups are keyed by the test's parent suite **full longname**, not the leaf name. `MyProject.Login` and `MyProject.Checkout.Login` are distinct groups.
- **`--by status`**: groups are the literal status strings `PASS`, `FAIL`, `SKIP`, `NOT RUN`. Empty buckets are omitted.

Filters and `--search` are applied **before** aggregation. That makes questions like "for the smoke subset, which suite has the most failures?" a single command:

```bash
robotcode results stats --include smoke --by suite --sort failed
```

### Recipes

```bash
# Worst tags by failure count (default sort)
robotcode results stats --by tag

# Five worst tags only
robotcode results stats --by tag --top 5

# Where is the CI time going?
robotcode results stats --by suite --sort elapsed

# Status breakdown for one specific tag
robotcode results stats --include flaky --by status
```

## `diff` — compare two runs

`diff` matches tests across two result files by **full longname** and classifies the differences. Use it for regression triage, to spot flaky tests, or to confirm that a fix has actually landed.

```bash
robotcode results diff baseline/output.xml                    # current is auto-discovered
robotcode results diff baseline/output.xml current/output.xml # explicit pair
```

### Output sections

| Section | Tests that … |
|---|---|
| `new failures` | passed in baseline, fail in current — regressions |
| `new passes` | failed or skipped in baseline, pass in current — fixes |
| `status changes` | otherwise changed status (e.g. `SKIP → FAIL`, `FAIL → SKIP`) |
| `added in current` | exist only in current (added since baseline) |
| `removed from current` | exist only in baseline (deleted/renamed since baseline) |

Tests that have the same status in both runs are **not** reported — `diff` shows changes only.

### Flag reference

| Flag | Effect |
|---|---|
| `--only new-failures\|new-passes\|status-changes\|added\|removed` | Restrict output to these categories. Repeatable. |
| `--message-chars N` | Truncate the per-entry messages to `N` chars. Default: `120`. |
| `--full-paths` | Absolute source paths. |
| `--exit-code` | Exit with a code that tells which categories have entries. See [Exit codes](#exit-codes). |
| `--exit-code-mask CATEGORY` | Keep these categories in the output but out of the exit code. Repeatable and comma-separated; `all` for every category. Turns on `--exit-code`. |

The standard `--status / -i / -e / -s / -t / -bl / -ebl / --search / --search-regex` filters apply to **both** baseline and current before matching. This lets you scope the comparison to a tag, sub-suite, or pattern without re-running anything:

```bash
robotcode results diff baseline.xml --include smoke
robotcode results diff baseline.xml --suite "*.Checkout"
robotcode results diff baseline.xml --search Timeout
```

### Exit codes

Without `--exit-code`, `diff` exits 0 whatever it found, so a script that only shows the diff isn't stopped by it. With `--exit-code`, the exit code is `0` for an empty diff and otherwise the sum of the categories that have entries:

| Value | Category |
|---|---|
| `0` | the diff is empty |
| `1` | new failures |
| `2` | new passes |
| `4` | status changes |
| `8` | added tests |
| `16` | removed tests |

New failures and removed tests, for example, give `1 + 16 = 17`. An error that stops the command exits with `128`, with or without `--exit-code`, so it can't be mistaken for a diff.

What the diff shows is what counts: `--only` and the filters narrow both the output and the exit code. For a regression gate that only fails on new failures:

```bash
robotcode results diff baseline.xml --only new-failures --exit-code
```

To see the whole diff but keep some categories out of the exit code, use `--exit-code-mask`. It turns on `--exit-code` by itself:

```bash
# Show everything, fail only on new failures, status changes and removed tests
robotcode results diff baseline.xml --exit-code-mask new-passes,added
```

To branch on a single category in bash, test its bit:

```bash
robotcode results diff baseline.xml --exit-code
rc=$?
if [ "$rc" -ge 128 ]; then echo "diff failed"; exit "$rc"; fi
if [ $((rc & 16)) -ne 0 ]; then echo "tests were removed"; fi
```

### When tests have been renamed

`diff` matches on `fullName`. A rename therefore looks like one `removed` entry plus one `added` entry — even if the test bodies are identical. There is currently no fuzzy-match mode; if rename detection is important to you, keep test names stable or post-process the JSON.

### Recipes

```bash
# Regression triage: every new failure, full message, with sources
robotcode results diff baseline.xml --only new-failures --message-chars 0 --full-paths

# Diff only the smoke subset
robotcode results diff baseline.xml --include smoke

# Compare two CI runs (e.g. main vs feature branch)
robotcode results diff main/output.xml branch/output.xml
```

## `compare` — runs side by side

`compare` puts two or more result files side by side. `diff` compares exactly two runs, from a baseline to the current one; `compare` takes any number of runs and treats them alike. So it answers questions about a series of runs: how the counts developed, which tests are flaky, since when a test fails, which failure hits many tests, which tests got slower, and what differs between platforms.

```bash
robotcode results compare run1/output.xml run2/output.xml run3/output.xml
robotcode results compare results/output-*.xml          # e.g. the files of --timestampoutputs
```

Tests are matched by their full name, as in `diff`. The top suite is part of that name, so give every run the same top suite — the same `paths`, or the same `--name` — or no test of one run matches a test of another.

### The overview

The output always starts with one row per run. It numbers the runs `#1`, `#2`, …, and the other tables of `compare` use these numbers as their column heads:

```
# Compare: 3 runs

## Runs

|   # | Run             | Started             | Tests | Pass | Fail | Skip | Elapsed |
| --: | --------------- | ------------------- | ----: | ---: | ---: | ---: | ------: |
|  #1 | run1/output.xml | 2026-11-06 23:14:36 |     4 |    4 |    0 |    0 |  177 ms |
|  #2 | run2/output.xml | 2026-11-06 23:14:37 |     4 |    2 |    2 |    0 |   71 ms |
|  #3 | run3/output.xml | 2026-11-06 23:14:38 |     4 |    2 |    2 |    0 |  124 ms |
```

Without further options the overview is all `compare` shows.

### Naming runs

Give a run a name with `NAME=PATH`. The name then stands in the overview and replaces the number in the column heads:

```bash
robotcode results compare linux=out/linux/output.xml windows=out/windows/output.xml
```

An argument that names an existing file is always a path, even if the file name contains `=`.

### Order of the runs

The runs are in the order of the arguments. A shell glob such as `results/output-*.xml` expands sorted by name, which for the timestamped files of `--timestampoutputs` is their order in time. `--run-order start-time` sorts by the start time of each run's top suite instead, with two limits:

- Robot Framework writes local times without a time zone, so runs from machines in different time zones can land in the wrong order.
- A file that `rebot` merged from several outputs has no start time of its own; `compare` takes the earliest start of the suites in it.

`--last N` keeps only the last N runs. The runs keep their numbers, so `--last 3` of five runs shows `#3`, `#4` and `#5`.

### Counts per tag or suite

`--by tag` and `--by suite` add the counts of [`stats`](#stats--aggregate-by-tag-suite-or-status) with one column per run. Each cell is the number of failed out of all tests of that group in that run, `-` when the run has no such group. Repeat `--by` for both tables:

```bash
robotcode results compare run1/output.xml run2/output.xml run3/output.xml --by tag --by suite
```

```
## By Tag

| Name  |  #1 |  #2 |  #3 |
| ----- | --: | --: | --: |
| smoke | 0/2 | 1/2 | 0/2 |

## By Suite

| Name          |  #1 |  #2 |  #3 |
| ------------- | --: | --: | --: |
| Shop.Checkout | 0/2 | 1/2 | 1/2 |
| Shop.Login    | 0/2 | 1/2 | 1/2 |
```

`--sort name|total|failed|elapsed` sorts the rows by that value in the last run, the most failed first by default. `--top N` keeps the first N rows of each table. Tags are merged as in `stats`.

### Views

`--show` adds a view below the overview and the `--by` tables. Repeat it for several views; they follow in the order given.

| View | Shows … |
|---|---|
| [`tests`](#status-of-each-test) | the status of each test that failed in a run, flaky tests, failing since |
| [`failures`](#the-same-failure-over-tests-and-runs) | the same failure message over tests and runs |
| [`elapsed`](#growth-of-elapsed-times) | tests and suites that got slower in the last run |
| [`messages`](#messages-of-the-runs) | the errors and warnings of the runs, new and gone ones |
| [`environment`](#environment-of-the-runs) | Robot Framework, Python, platform and metadata of each run |

#### Status of each test

`--show tests` lists every test that failed in at least one run, with its status in each run as one character: `P` passed, `F` failed, `S` skipped, `N` not run, and `-` for a run that doesn't have the test, such as one from before the test was written.

```bash
robotcode results compare run*/output.xml --show tests
```

```
## Tests

| Test                         | Status  | Failed | Flaky | Failing since |
| ---------------------------- | ------- | -----: | ----- | ------------- |
| Shop.Login.Bad Password      | `PFFFF` |    4/5 |       | #2            |
| Shop.Checkout.Pay By Card    | `PFPFP` |    2/5 | yes   |               |
| Shop.Checkout.Pay By Invoice | `PPFPF` |    2/5 | yes   | #5            |
```

- **Failed** counts only the runs that had the test: a test written before run 5 of ten that failed once shows `1/6`. The tests are sorted by it, the most failed first.
- **Flaky** means the status changed between passed and failed at least twice. A single change is a new failure (`PPPFF`) or a fix (`FFPPP`) and not flakiness; skipped runs and runs without the test don't count as a change.
- **Failing since** names the run where the uninterrupted failures up to the last run began, for a test that failed in the last run that had it. A run without the test doesn't interrupt the series.

#### The same failure over tests and runs

`--show failures` groups the failure messages of all runs. The same message in many tests or runs often has one cause, such as a service that was down; the run it first appears in points to the change that caused it.

```bash
robotcode results compare run*/output.xml --show failures
```

```
## Failures

| Message                                          | Tests | First |  #1 |  #2 |  #3 |  #4 |  #5 |
| ------------------------------------------------ | ----: | ----- | --: | --: | --: | --: | --: |
| 500 Server Error for url: http://shop/order/4711 |     2 | #2    |   0 |   1 |   2 |   1 |   2 |
| Timeout after 5000 ms waiting for #pay           |     1 | #2    |   0 |   1 |   0 |   1 |   0 |
```

Two messages count as the same when they are equal after every number is replaced by `#` and runs of whitespace are collapsed, so IDs, times and counters don't split a group: the first row holds `…/order/4711` of one test and `…/order/4712` of another. The table shows the first message of each group, cut to `--message-chars` (default `120`); **Tests** is the number of different tests with it, and the run columns count the tests per run.

Ignoring numbers has two limits:

- Different assertions that differ only in numbers, such as `Expected 3 but got 5` and `Expected 1 but got 2`, land in one group.
- Multi-line messages whose lines change, such as the call log of the Browser library, stay apart.

#### Growth of elapsed times

`--show elapsed` lists the suites and tests whose elapsed time in the last run is longer than the median of the runs before it. The median keeps a single slow run, such as one with a cold cache, from hiding or faking a trend. There is no threshold: the lists are sorted by the growth in seconds, so the items that cost the most time come first, and `--top N` keeps the first N of each.

```bash
robotcode results compare run1/output.xml run4/output.xml slow/output.xml --show elapsed
```

```
## Elapsed

### Suites

| Name          | Median before |   Last |  Growth | Growth % |
| ------------- | ------------: | -----: | ------: | -------: |
| Shop.Checkout |        104 ms | 654 ms | +550 ms |   +530 % |
| Shop          |        125 ms | 673 ms | +548 ms |   +439 % |

### Tests

| Name                      | Median before |   Last |  Growth | Growth % |
| ------------------------- | ------------: | -----: | ------: | -------: |
| Shop.Checkout.Pay By Card |         51 ms | 601 ms | +550 ms |  +1069 % |
```

Only the runs that had the test or suite count, and one that is in fewer than two runs isn't listed. A failed test usually ends early, so a test that failed in the runs before can look slower when it passes again.

#### Messages of the runs

`--show messages` compares the errors and warnings of the runs, the messages `log.html` shows under "Test Execution Errors": import errors, invalid settings, deprecation warnings, and the warnings and errors logged in tests. A first table counts them per level and run; the second groups the messages as `--show failures` does, with the first and the last run each one appears in. A message only in the last run is **new**, one that is missing from the last run is **gone**; new ones come first.

```bash
robotcode results compare nightly/*/output.xml --show messages
```

```
## Messages

| Level |  #1 |  #2 |  #3 |
| ----- | --: | --: | --: |
| ERROR |   1 |   1 |   0 |
| WARN  |   0 |   0 |   1 |

| Level | Message                                                                                                                   | First | Last | Change |  #1 |  #2 |  #3 |
| ----- | ------------------------------------------------------------------------------------------------------------------------- | ----- | ---- | ------ | --: | --: | --: |
| WARN  | Keyword 'Open Old Browser' is deprecated since 7.1.                                                                       | #3    | #3   | new    |   0 |   0 |   1 |
| ERROR | Error in file '/home/me/shop/msgtests/shop.robot' on line 2: Importing library 'Screenshots' failed: ModuleNotFoundError… | #1    | #2   | gone   |   1 |   1 |   0 |
```

The messages are read before the filters, so a filter narrows the tests of the other views but not the messages.

#### Environment of the runs

`--show environment` shows what each result file records about where it was written: the tool and its Robot Framework version, the Python version and the operating system as Python names it (`linux`, `win32`, `darwin`), and one column per metadata name of the top suites.

```bash
robotcode results compare env/chrome/output.xml env/firefox/output.xml env/merged/output.xml --show environment
```

```
## Environment

| Run | Written by | Python | OS    | Browser | Build |
| --- | ---------- | ------ | ----- | ------- | ----- |
| #1  | Robot 7.5  | 3.14.9 | linux | chrome  | 1234  |
| #2  | Robot 7.5  | 3.14.9 | linux | firefox | 1234  |
| #3  | Rebot 7.5  | 3.14.9 | linux |         |       |
```

A result file records no more than that: no library versions, host names or environment variables. Add what you need as metadata when the tests run, and `compare` shows it, here with:

```bash
robotcode robot --metadata Browser:chrome --metadata Build:1234 tests
```

Three things to know:

- A file written by `rebot` records `Rebot` and the version of `rebot`, not the version the tests ran with.
- When `rebot` merges several outputs, the metadata stays with the merged suites, so the new top suite has none, as in row `#3`.
- With Robot Framework 7.0 or 7.1 installed, an `output.json` stays empty here: those versions read only the JSON their `rebot` writes, and it records none of these fields.

### Groups of runs

Runs of several platforms, browsers or environments are compared within their own kind: a test that fails only on Windows matters, and the Linux runs say nothing about whether it got slower on Windows. `--group-by-metadata NAME` groups the runs by the value of that metadata of their top suite, set with `--metadata` when the tests run:

```bash
robotcode robot --metadata Platform:linux tests
robotcode results compare plat/*/output.xml --group-by-metadata Platform --show tests
```

```
## Runs

|   # | Group       | Run                       | Started             | Tests | Pass | Fail | Skip | Elapsed |
| --: | ----------- | ------------------------- | ------------------- | ----: | ---: | ---: | ---: | ------: |
|  #1 | linux       | plat/1-linux/output.xml   | 2026-11-06 23:28:27 |     4 |    4 |    0 |    0 |  173 ms |
|  #2 | linux       | plat/2-linux/output.xml   | 2026-11-06 23:28:28 |     4 |    4 |    0 |    0 |  173 ms |
|  #3 | linux       | plat/3-linux/output.xml   | 2026-11-06 23:28:30 |     4 |    4 |    0 |    0 |  176 ms |
|     | **linux**   | _total_                   |                     |    12 |   12 |    0 |    0 |  522 ms |
|  #4 | windows     | plat/1-windows/output.xml | 2026-11-06 23:28:27 |     4 |    2 |    2 |    0 |   73 ms |
|  #5 | windows     | plat/2-windows/output.xml | 2026-11-06 23:28:28 |     4 |    4 |    0 |    0 |  175 ms |
|  #6 | windows     | plat/3-windows/output.xml | 2026-11-06 23:28:30 |     4 |    2 |    2 |    0 |   83 ms |
|     | **windows** | _total_                   |                     |    12 |    8 |    4 |    0 |  331 ms |

## Tests

_Groups: linux, windows_

| Test                      | Status    |    Failed | Flaky   | Failing since |
| ------------------------- | --------- | --------: | ------- | ------------- |
| Shop.Checkout.Pay By Card | `PPP FPF` | 0/3, 2/3 | -, yes | -, #6        |
| Shop.Login.Bad Password   | `PPP FPF` | 0/3, 2/3 | -, yes | -, #6        |
```

- The runs of a group stand together, in their order, and the groups in the order of their first run. The overview adds a sum row per group. Runs without the metadata form a group of their own, shown as `(none)`.
- Everything that depends on the order of the runs is computed within each group and shown per group, separated by `, ` in the order of the `_Groups:_` line: the failed count, flaky and failing since in `tests`, the first run in `failures`, the growth in `elapsed` (with a **Group** column), and new and gone in `messages`.
- The status of a test has a space between the groups. The other tables keep one column per run.
- `--last N` keeps the last N runs of each group.
- The groups need the metadata in the top suite. A file that `rebot` merged from several outputs has none there (see [Environment of the runs](#environment-of-the-runs)) unless `rebot --metadata Platform:linux …` sets it.

### Flag reference

| Flag | Effect |
|---|---|
| `NAME=PATH` | Name a run. |
| `--message-chars N` | Cut messages and metadata values to N characters (0 = no cut). Default: `120`. |
| `--show tests\|failures\|elapsed\|messages\|environment` | Add a view; see [Views](#views). Repeatable. |
| `--by tag\|suite` | Add the counts per tag or suite, one column per run. Repeatable. |
| `--sort name\|total\|failed\|elapsed` | Sort the rows of `--by` by this value in the last run. Default: `failed`. |
| `--top N` | At most N rows per table (0 = all). |
| `--run-order arguments\|start-time` | Order the runs as the arguments are (default) or by the start time of their top suite. |
| `--last N` | Compare only the last N runs, of each group with `--group-by-metadata`. |
| `--group-by-metadata NAME` | Group the runs by the value of this metadata of their top suite. |
| `--full-paths` | Absolute paths in the overview. |

The filters of `diff` (`--status / -i / -e / -s / -t / -bl / -ebl / -btm / -ebtm / --search / --search-regex`) apply to every run before the runs are compared.

### Exit code

`compare` exits with 0 whatever the runs show, as `stats` does, and with 128 for an error that stops it, as every `results` command does. For a build that fails on new failures between two runs, use [`diff --exit-code`](#exit-codes).

## Filters

Every subcommand accepts the same filter set. Filters combine with **AND** — every test must satisfy every filter to make it through. Within a single repeatable flag (`--status`, `--include`, etc.) the matches combine with **OR** in the way Robot Framework normally treats those options.

| Flag | Behavior |
|---|---|
| `--status pass\|fail\|skip\|not-run` | Repeatable; tests whose status is in the chosen set. |
| `--failed` / `--passed` / `--skipped` | Shorthands for `--status fail` / `--status pass` / `--status skip`. Additive with `--status` and with each other (OR semantics). Available on `show`, `log`, `stats`. |
| `-i/--include TAG_PATTERN` | Robot tag-pattern syntax (see below). Repeatable. |
| `-e/--exclude TAG_PATTERN` | Same syntax, exclusion side. Repeatable. |
| `-s/--suite GLOB` | Match against the suite's name or full longname. Repeatable. |
| `-t/--test GLOB` | Match against the test's name or full longname. Aliased as `--task`. Repeatable. |
| `-bl/--by-longname NAME` | Exact longname match (no glob expansion). Repeatable. |
| `-ebl/--exclude-by-longname NAME` | Exclusion variant of `--by-longname`. Repeatable. |
| `-btm/--by-test-metadata PATTERN` | Tests whose `[Metadata]` matches the pattern (Robot Framework 7.5+, see [below](#test-metadata--btm-ebtm)). Repeatable. |
| `-ebtm/--exclude-by-test-metadata PATTERN` | Exclusion variant of `--by-test-metadata` (Robot Framework 7.5+). Repeatable. |

### Tag-pattern syntax (`-i`/`-e`)

Tag patterns follow Robot Framework's own rules:

- A plain tag (`smoke`) matches tests carrying that tag.
- `AND` (uppercase) requires multiple tags: `smokeANDregression` matches only tests that have **both** tags.
- `NOT` excludes: `smokeNOTslow` matches `smoke` minus `slow`.
- Tags are matched case-insensitively, and whitespace and underscores are ignored — `smoke_test`, `Smoke Test` and `smoketest` all refer to the same tag. Other punctuation, including hyphens, is significant: `bug-123` and `bug123` are distinct.
- Glob characters `*` and `?` work inside a tag pattern: `bug-*` matches any tag starting with `bug-`.

You can repeat `-i` to OR multiple patterns: `-i smoke -i regression` selects tests that carry **either** `smoke` **or** `regression`.

### Suite / test globs

`-s` / `-t` accept shell-style glob patterns matched against the name or the full longname:

- `*` matches any sequence of characters (including `.`, so `*.Login` matches at any depth).
- `?` matches a single character.
- Matching is case-insensitive and ignores whitespace and underscores; a pattern matches if it fits either the name (`Bad Password`) or the full longname (`MyProject.Login.Bad Password`).
- Repeat for OR: `-s "MyProject.Login" -s "MyProject.Checkout"`.

Quote globs in the shell — `--suite "*.Login"` and `--test "Test ?"` need quotes so the shell doesn't expand them against the local filesystem.

### `--by-longname` vs `--suite` / `--test`

- `-s` / `-t` are **glob** matches and accept patterns.
- `-bl` / `-ebl` are **exact** matches against the full longname — no glob expansion. They mirror `robotcode robot --by-longname` so you can hand the same names to `robot` and `results`.

Use `-bl` when you have a precise name to filter against (often pasted from the failure list); use `-s/-t` when you want pattern matching.

### Test metadata (`-btm`/`-ebtm`)

`-btm`/`-ebtm` (Robot Framework 7.5+) select by the test's `[Metadata]`, with the same pattern rules as `robotcode robot` and `discover`, described in [Selecting by test metadata](/guides/cli/discovering-tests/#selecting-by-test-metadata):

```bash
robotcode results show -btm Issue:4409                        # the results of every test for issue 4409
robotcode results summary -btm "Author:Hans* OR Reviewer:Hans*"
robotcode results stats --by tag -ebtm "Owner:*"              # tag statistics of the tests without an owner
```

A result file holds the values the run used: variables in a value are already replaced. `Build:42` matches a test with `[Metadata]    Build    ${BUILD}` that ran with `BUILD` set to 42, while `robot` and `discover` see `${BUILD}`. The patterns are echoed in [`filtersApplied`](#filtersapplied) as given, under `by-test-metadata` and `exclude-by-test-metadata`.

:::note[Robot Framework 7.5+]
Test metadata exists since Robot Framework 7.5. With an older version installed, `--help` does not list `--by-test-metadata` and `--exclude-by-test-metadata`; they are still accepted, but `--by-test-metadata` selects nothing and `--exclude-by-test-metadata` removes nothing.
:::

## Search

`--search` and `--search-regex` are **mutually exclusive** (passing both is a usage error). They apply across:

- the test's `name` and full longname
- the test's failure message
- the test's tags
- the test's `[Metadata]` names and values (Robot Framework 7.5+)
- the test's `[Documentation]`, `[Template]` and `[Timeout]`
- every keyword call's name, arguments and assignments within the test body
- every executed keyword's `[Documentation]`, `[Tags]` and `[Timeout]` (taken from the keyword definition; result-tree only)
- every log message's text
- any **ancestor suite**'s `Documentation` or `Metadata` (a hit on a suite-level field keeps every test underneath it)

A test matches if **any** of those targets matches. Once `log` decides a test matches, all of its body items are emitted as usual — the search is a test-level filter, not a per-message filter.

| Flag | Semantics |
|---|---|
| `--search TEXT` | Case-insensitive substring match. No metacharacters; `[` and `*` are literal. |
| `--search-regex PATTERN` | Regular expression, **case-sensitive** by default. Use `(?i)` at the start of the pattern for case-insensitive matching. |

When matching against **tags** specifically, each tag is normalised the way Robot Framework normalises tags (lowercase, whitespace and underscores ignored), and so is a `--search` pattern. So `--search "bug 1"` matches tests tagged `bug_1`, `Bug1`, or `BUG 1`. A `--search-regex` pattern is used as written against the normalised tag: `bug1` matches those tests, `Bug 1` doesn't. Other targets — name, message, keyword arguments, log text — are matched literally without normalisation.

```bash
robotcode results log --search "TimeoutError"
robotcode results log --search-regex 'AssertionError.*expected: \d+'
robotcode results log --search-regex '(?i)login'   # case-insensitive
```

### Anchors and alternation

The regex is matched against each target string individually, **not anchored** to the whole string — a pattern like `Login` matches any target that contains `Login` somewhere. Use `^` and `$` if you want anchored matches. Note that anchors apply per target string, so `^Login` matches a test whose full longname is `Login.Bad Password` but also a keyword named `Login With Token` somewhere inside the test body.

### Highlighting in the terminal

On `log` (and `show`), matches are marked as inline code in the TEXT output so you can scan visually. Structured output (JSON/TOML) is unchanged — searching only filters, it doesn't add markup.

### Search on `summary` and `stats`

`--search` works on these too, but its effect is subtle: the matching tests narrow the input set, and the counts / aggregations are computed against that narrowed set. So `robotcode results summary --search Login` is "how is the Login subset doing" and `robotcode results stats --by tag --search Login` is "which tags are involved in the Login subset".

### Invalid patterns

An unparseable regex (e.g. `[unclosed`) yields a usage error pinpointing where the pattern failed to compile. The command exits non-zero before reading the result file.

## Tips for terminal use

- **TEXT output is markdown.** On a coloured TTY the markdown is rendered to themed ANSI via `rich` (and paged if longer than your terminal); on pipes or with `--no-color` the raw markdown goes through verbatim — paste it into a PR description, a Slack message, or feed it straight to an LLM.
- **Quote your globs.** `--suite "*.Login"` and `--test "Test ?"` need quotes so the shell doesn't expand them against the local filesystem first.
- **Filters apply before aggregation.** `stats`, `summary` and `diff` all run the filter pipeline first, so `--search Login` followed by `--by tag` gives you tag stats over the Login subset, not all tags whose name happens to contain "Login".
- **`-bl` is for exact names, `-t` is for patterns.** When you copy a failing-test name out of the failure list, `-bl` is usually what you want — no need to escape glob characters.
- **Save your baselines.** Archive `output.xml` from your green main branch (or main-CI run) and feed it to `diff` from feature branches — that's the fastest way to catch regressions before review.
- **`diff` doesn't fail the build by default.** It exits 0 unless you pass `--exit-code`. For a regression gate, see [Exit codes](#exit-codes).

---

## JSON reference

When you set `-f json` (or `-f json_indent` for pretty-printed, or `-f toml`) between `robotcode` and the subcommand, every result command emits structured data instead of the terminal-formatted text. This is what CI pipelines, scripts and AI agents consume.

```bash
robotcode --format json results summary
robotcode --format json results show --failed --sort elapsed
robotcode --format json results log --failed
```

This part of the guide is the schema reference: what fields each subcommand emits, when they're present, and how to consume them safely.

### Schema rules

A few rules hold across every subcommand:

- **camelCase keys.** `fullName`, `elapsedSeconds`, `messagesCount`, etc.
- **ISO-8601 timestamps** with microsecond resolution.
- **Optional fields are omitted, not `null`.** If a field has no value (e.g. `failed` without `--failed`, `tags` on an untagged test), the key is simply absent from the JSON object. A `null` appears only in the per-run lists of `compare`, for a run that doesn't have the item.
- **Scalar fields with a meaningful zero are emitted in JSON.** `counts.failed = 0`, `truncated = 0`, `elapsedSeconds = 0.0` all stay in the object; the exception is a `stats` group's `elapsedSeconds`, which is left out when it is `0.0`. Only optional fields disappear when unset. TOML output also leaves out counters that are `0` (`counts.*`, `truncated`, `extractedCount`) and flags that are `false`.
- **Empty array ≠ missing field.** Sections that "exist but are empty" come through as `[]`; sections that were never requested (e.g. anything excluded by `diff --only`) are absent. The two are different and your queries should handle both, typically via `// []` in jq.
- **ASCII only.** Characters outside ASCII in names, messages and paths come as `\u` escapes (`"Gr\u00fc\u00dfe"` for `Grüße`), so the JSON works on any terminal or pipe. Every JSON parser, `jq` included, reads them back as the original characters.
- **Stability.** Fields are appended over time, never renamed or removed in place. New fields are additive; existing consumers keep working.

### `summary` JSON

```json
{
  "file": {
    "source": "/abs/path/results/output.xml",
    "relSource": "results/output.xml"
  },
  "status": "FAIL",
  "counts": { "total": 42, "passed": 37, "failed": 2, "skipped": 3, "notRun": 0 },
  "elapsedSeconds": 83.4,
  "startTime": "2026-05-15T08:11:02.183025",
  "endTime": "2026-05-15T08:12:25.583025",
  "failed": [
    {
      "name": "Bad Password",
      "fullName": "MyProject.Login.Bad Password",
      "suite": "MyProject.Login",
      "status": "FAIL",
      "message": "AssertionError: Expected 'Login failed' but got 'Internal error'",
      "tags": ["smoke"],
      "metadata": { "Issue": "4409" },
      "elapsedSeconds": 0.234,
      "startTime": "2026-05-15T08:11:04.906118",
      "source": "/abs/path/tests/login/test_login.robot",
      "relSource": "tests/login/test_login.robot",
      "lineno": 42
    }
  ],
  "messagesCount": { "WARN": 4, "FAIL": 2 },
  "executionMessagesCount": { "WARN": 1 }
}
```

Field notes:

- `failed` only appears when `--failed` was passed and at least one test failed. Its entries have the same shape as the `tests[]` entries of [`show`](#show-json), including `metadata`.
- `messagesCount` counts the `WARN`, `ERROR` and `FAIL` messages by level, each message once: those logged in tests and keywords plus the execution messages; other levels are not counted. Only levels with at least one message appear — empty buckets are omitted, not emitted as `0`.
- `executionMessagesCount` counts the messages of the `<errors>` section that come from outside the tests, such as parsing and import errors. Robot Framework also copies the warnings and errors logged in tests into `<errors>`; those copies are not counted here. It appears **only** when there were any.
- `filtersApplied` (see [below](#filtersapplied)) appears when any filter was passed.

### `show` JSON

```json
{
  "file": { "source": "/abs/path/results/output.xml" },
  "counts": { "total": 42, "passed": 37, "failed": 2, "skipped": 3, "notRun": 0 },
  "tests": [
    {
      "name": "Bad Password",
      "fullName": "MyProject.Login.Bad Password",
      "suite": "MyProject.Login",
      "status": "FAIL",
      "message": "AssertionError: Expected 'Login failed' …",
      "tags": ["smoke", "regression"],
      "metadata": { "Issue": "4409", "Owner Team": "core" },
      "elapsedSeconds": 0.234,
      "startTime": "2026-05-15T08:11:04.906118",
      "source": "/abs/path/tests/login/test_login.robot",
      "lineno": 42
    }
  ],
  "truncated": 0,
  "elapsedSeconds": 83.4,
  "startTime": "2026-05-15T08:11:02.183025",
  "endTime": "2026-05-15T08:12:25.583025"
}
```

Field notes:

- `tests[]` is always present, possibly empty.
- `tags` is always emitted for tests that have any (and absent for untagged tests), in normalised form (`Bug 1`, `bug_1`, `Bug1` all come through as `"bug1"`). The `--show-tags` flag in TEXT mode is render-only — it doesn't affect the JSON.
- `metadata` is the test's `[Metadata]` as a name → value object. Names keep the spelling from the source file and values come through as recorded in the result file, the lines of a multi-line value joined with `\n`. An entry without a name — a `[Metadata]` setting with nothing after it, which Robot Framework writes to `output.json` but not to `output.xml` — is left out. The key is absent for tests without metadata; only result files written by Robot Framework 7.5 or newer contain test metadata. Like `--show-tags`, the `--show-metadata` flag is render-only.
- `truncated` is the number of tests dropped by `--top N`; `0` when nothing was dropped.
- The order of `tests[]` reflects `--sort` and `--reverse`.

### `log` JSON

```json
{
  "file": { "source": "/abs/path/results/output.xml" },
  "tests": [
    {
      "fullName": "MyProject.Login.Bad Password",
      "status": "FAIL",
      "message": "AssertionError: Expected 'Login failed' …",
      "body": [ /* recursive tree of body items, see below */ ],
      "artifacts": [ /* aggregated artifact refs for the whole test */ ],
      "source": "/abs/path/tests/login/test_login.robot",
      "lineno": 42,
      "elapsedSeconds": 0.234,
      "startTime": "2026-05-15T08:11:04.906118",
      "suite": "MyProject.Login",
      "metadata": { "Issue": "4409", "Owner Team": "core" }
    }
  ],
  "suites": [
    {
      "fullName": "MyProject.Login",
      "name": "Login",
      "status": "FAIL",
      "doc": "Exercises the login flow against staging.",
      "metadata": { "OwnerTeam": "identity-squad" },
      "source": "/abs/path/tests/login.robot",
      "elapsedSeconds": 12.7,
      "startTime": "2026-05-15T08:11:02.190455"
    }
  ],
  "executionMessages": [ /* only with --execution-messages */ ],
  "extractDir": "/abs/path/extracted",
  "extractedCount": 7
}
```

The `body` array of each test is a recursive tree of body items. Field notes:

- `extractDir` appears only with `--extract DIR`; `extractedCount` is always present (`0` without `--extract`).
- `executionMessages` appears only with `--execution-messages`.
- The per-test `metadata` is the test's `[Metadata]` (Robot Framework 7.5+) in the same shape as in [`show`](#show-json) and as the suite-level `metadata` below; absent for tests without metadata. It does not depend on any flag.
- `suites` and the per-test `suite` cross-reference appear only with `--suite-info`. One `suites` entry per suite that contains at least one surviving test — directly or in a child suite — in traversal order. Empty `metadata` / `doc` are dropped.
- Artefact entries carry `kind` (`"image"` | `"file"`), `src`, and — when extraction happened — `extractedTo` (absolute path of the written file). Failed extractions get a `skippedReason` instead (e.g. `"missing-source"`, `"target-traversal"`).

#### Body-item types

Every body-item entry has a `type` field. The vocabulary tracks Robot Framework's own body-item taxonomy:

| `type` | What it represents | Notable fields |
|---|---|---|
| `KEYWORD` | A keyword call | `name` (owner included, e.g. `BuiltIn.Log`), `args`, `assign`, `body` |
| `SETUP` / `TEARDOWN` | Suite/test setup or teardown keyword | same as `KEYWORD` |
| `FOR` | `FOR` loop | `flavor` (`IN`/`IN RANGE`/`IN ENUMERATE`/`IN ZIP`), `body` (iterations) |
| `ITERATION` | One iteration of a `FOR` / `WHILE` loop | `assign` (the loop variable values), `body` |
| `WHILE` | `WHILE` loop | `condition`, `body` |
| `IF` / `ELSE IF` / `ELSE` | Conditional branches | `condition` (on `IF` / `ELSE IF`), `body` |
| `TRY` / `EXCEPT` / `FINALLY` | Exception handling | `patterns`, `patternType` (on `EXCEPT`) |
| `VAR` | `VAR` assignment statement | `assign` (variable name), `args` (value), `scope` |
| `RETURN` / `BREAK` / `CONTINUE` | Control-flow exits | `args` (values for `RETURN`) |
| `GROUP` | `GROUP` block | `name`, `body` |
| `ERROR` | Recorded execution error | `args` |
| `MESSAGE` | A log message | `level`, `text`, `timestamp`, `isHtml`, `artifacts` |

Every entry carries `status`, `elapsedSeconds` and `startTime` where applicable. The recursive `body` field is what makes the tree walkable — you can drill into a `FOR` loop's `ITERATION` and then into the `KEYWORD` calls inside each iteration.

With **`--keyword-info`**, every `KEYWORD` / `SETUP` / `TEARDOWN` entry additionally carries the keyword's own definition metadata:

| Field | When it appears |
|---|---|
| `doc` | Keyword has a `[Documentation]` setting (library keywords always do; user keywords only when written). |
| `tags` | Keyword has at least one `[Tags]` entry. |
| `timeout` | Keyword has a `[Timeout]` setting. |

Empty entries are dropped — a user keyword without `[Tags]` will not have a `tags` key.

### `stats` JSON

```json
{
  "file": { "source": "/abs/path/results/output.xml" },
  "sections": [
    {
      "dimension": "tag",
      "groups": [
        {
          "name": "regression",
          "counts": { "total": 24, "passed": 19, "failed": 5, "skipped": 0, "notRun": 0 },
          "elapsedSeconds": 252.1
        }
      ],
      "truncated": 0
    }
  ]
}
```

Field notes:

- `sections[]` has one entry per `--by` dimension, in the order they appeared on the command line.
- `dimension` is `"tag"` | `"suite"` | `"status"`.
- `groups[]` is sorted by `--sort` (default: `failed` descending) and capped by `--top N`.
- `elapsedSeconds` per group is the **sum** of test elapsed times in that group.
- `truncated` is the number of groups dropped by `--top N`.

### `diff` JSON

```json
{
  "baseline": { "source": "/abs/path/baseline/output.xml" },
  "current": { "source": "/abs/path/current/output.xml" },
  "newFailures": [
    {
      "fullName": "MyProject.Login.Bad Password",
      "baselineStatus": "PASS",
      "currentStatus": "FAIL",
      "currentMessage": "AssertionError: Expected 'Login failed' …",
      "source": "/abs/path/tests/login/test_login.robot",
      "relSource": "tests/login/test_login.robot",
      "lineno": 42
    }
  ],
  "newPasses": [],
  "statusChanges": [],
  "added": [],
  "removed": []
}
```

Field notes:

- Without `--only`, all five section arrays (`newFailures`, `newPasses`, `statusChanges`, `added`, `removed`) are always present — empty `[]` when nothing matched.
- With `--only`, sections you didn't list are **omitted entirely** from the JSON. Use `// []` in jq when accessing fields that may be missing.
- Each entry carries `fullName`, the relevant status fields, and (when they exist) the relevant messages. `baselineMessage` / `currentMessage` are omitted when the corresponding run had no failure message.

### `compare` JSON

```json
{
  "runs": [
    {
      "number": 1,
      "file": {
        "source": "/abs/path/run1/output.xml",
        "relSource": "run1/output.xml",
        "generator": "Robot 7.5 (Python 3.14.9 on linux)",
        "generationTime": "2026-11-06T23:14:36.133699"
      },
      "status": "PASS",
      "counts": { "total": 4, "passed": 4, "failed": 0, "skipped": 0, "notRun": 0 },
      "startTime": "2026-11-06T23:14:36.134241",
      "elapsedSeconds": 0.17724
    }
  ]
}
```

Field notes:

- `runs` is in the order of the overview, after `--run-order` and `--last`. `name` is present for a run given as `NAME=PATH`; `startTime` is missing for a file that `rebot` merged from several outputs.
- With `--group-by-metadata`, `groupByMetadata` names the metadata, each run has its `group` (missing for a run without the metadata), and `groups` lists the groups in order with the numbers of their `runs`, their summed `counts` and `elapsedSeconds`. A group of runs without the metadata has no `name`.
- Every list of per-run values elsewhere in the `compare` JSON follows the order of `runs`, with `null` for a run that doesn't have the item.
- `sections` holds one entry per `--by` dimension, in the order given. Each group has one entry per run in `runs`: `{ "counts": …, "elapsedSeconds": … }`, or `null` when the run has no test in that group. `truncated` is the number of groups dropped by `--top`.

  ```json
  "sections": [
    {
      "dimension": "tag",
      "groups": [
        {
          "name": "smoke",
          "runs": [
            { "counts": { "total": 2, "passed": 2, "failed": 0, "skipped": 0, "notRun": 0 }, "elapsedSeconds": 0.102033 },
            { "counts": { "total": 2, "passed": 1, "failed": 1, "skipped": 0, "notRun": 0 }, "elapsedSeconds": 0.001616 }
          ]
        }
      ],
      "truncated": 0
    }
  ]
  ```
- `tests` is present with `--show tests`. Each test has its `statuses`, one per run in `runs` with Robot Framework's status names and `null` for a run without the test, and `perGroup` with the counts that depend on the order of the runs: `failed` out of `runs`, `flaky`, and `failingSince` as a run number when the test fails in the last run that had it.

  ```json
  "tests": {
    "tests": [
      {
        "fullName": "Shop.Login.Bad Password",
        "statuses": ["PASS", "FAIL", "FAIL", "FAIL", "FAIL"],
        "perGroup": [{ "group": null, "failed": 4, "runs": 5, "flaky": false, "failingSince": 2 }],
        "source": "/abs/path/tests/login.robot",
        "relSource": "tests/login.robot",
        "lineno": 5
      }
    ],
    "truncated": 0
  }
  ```

  Without `--group-by-metadata`, `perGroup` has a single entry whose `group` is `null`; with it, one entry per group in the order of `groups`.
- `failures` is present with `--show failures`: per group of messages the shown `message`, the full names of its `tests`, the number of tests per run in `runs`, and `perGroup` with the `firstRun` it appears in.

  ```json
  "failures": {
    "failures": [
      {
        "message": "500 Server Error for url: http://shop/order/4711",
        "tests": ["Shop.Login.Bad Password", "Shop.Checkout.Pay By Invoice"],
        "runs": [0, 1, 2, 1, 2],
        "perGroup": [{ "group": null, "firstRun": 2 }]
      }
    ],
    "truncated": 0
  }
  ```
- `elapsed` is present with `--show elapsed`: `suites` and `tests`, each entry with `medianSeconds` of the runs before the last one that had it, `lastSeconds`, `growthSeconds` and `growthPercent` (missing when the median is `0`), and its `group`. `suitesTruncated` and `testsTruncated` count what `--top` dropped.

  ```json
  "elapsed": {
    "suites": [
      { "fullName": "Shop.Checkout", "group": null, "medianSeconds": 0.1037, "lastSeconds": 0.6536, "growthSeconds": 0.5499, "growthPercent": 530.3 }
    ],
    "tests": [
      { "fullName": "Shop.Checkout.Pay By Card", "group": null, "medianSeconds": 0.0514, "lastSeconds": 0.6014, "growthSeconds": 0.55, "growthPercent": 1069.1 }
    ],
    "suitesTruncated": 0,
    "testsTruncated": 0
  }
  ```
- `messages` is present with `--show messages`: `counts` per level with one number per run, and `messages`, each with its `level`, the shown `message`, the number per run in `runs`, and `perGroup` with `firstRun`, `lastRun`, `new` and `gone`.

  ```json
  "messages": {
    "counts": [
      { "level": "ERROR", "runs": [1, 1, 0] },
      { "level": "WARN", "runs": [0, 0, 1] }
    ],
    "messages": [
      {
        "level": "WARN",
        "message": "Keyword 'Open Old Browser' is deprecated since 7.1.",
        "runs": [0, 0, 1],
        "perGroup": [{ "group": null, "firstRun": 3, "lastRun": 3, "new": true, "gone": false }]
      }
    ],
    "truncated": 0
  }
  ```
- `environment` is present with `--show environment`: one entry per run with its `run` number, the `generator` text as the file records it, its parts `tool`, `version`, `python` and `platform`, and the `metadata` of the top suite. Fields the file doesn't record are missing.

  ```json
  "environment": [
    {
      "run": 1,
      "generator": "Robot 7.5 (Python 3.14.9 on linux)",
      "tool": "Robot",
      "version": "7.5",
      "python": "3.14.9",
      "platform": "linux",
      "metadata": { "Browser": "chrome", "Build": "1234" }
    }
  ]
  ```

### `filtersApplied`

Every subcommand's JSON output includes a `filtersApplied` field when **any** filter was passed. It echoes back the filters the command actually saw:

```json
"filtersApplied": {
  "status": ["fail"],
  "include": ["bug1"],
  "exclude": ["smokeANDregression"],
  "suite": ["*.Login"]
}
```

Most filters come back verbatim. The two exceptions are `include` and `exclude`:

- A plain single-tag pattern is normalised the way Robot would (`BUG 1` → `bug1`, `Smoke_Test` → `smoketest`), so you see how the filter is actually being compared.
- A pattern containing an uppercase `AND` / `OR` / `NOT` operator is echoed verbatim, because each operand would need to be normalised individually and the surrounding structure carries deliberate meaning.

This is useful when piecing together a complex CI command — you can assert that the filter set ended up where you expected. When no filters were passed, the field is absent.

### CI recipes

A grab-bag of jq-based recipes. Pin `-f json` between `robotcode` and the subcommand to lock the format.

#### Pass/fail the build

```bash
# Fail on any test failure
robotcode --format json results summary | jq -e '.counts.failed == 0'

# Fail only on new failures vs a checked-in baseline
robotcode results diff baseline/output.xml --only new-failures --exit-code

# Allow a fixed budget of failures
FAILED=$(robotcode --format json results summary | jq '.counts.failed')
test "$FAILED" -le 3
```

#### Slow-test report

```bash
# Top 20 slowest tests, CSV
robotcode --format json results show --sort elapsed --top 20 \
  | jq -r '.tests[] | [.fullName, .elapsedSeconds] | @csv'

# Tag-level elapsed budget (minutes)
robotcode --format json results stats --by tag --sort elapsed \
  | jq -r '.sections[].groups[] | [.name, (.elapsedSeconds / 60)] | @csv'

# Tests that got slower in the last of ten runs, with the growth in seconds
robotcode --format json results compare results/output-*.xml --last 10 --show elapsed \
  | jq -r '.elapsed.tests[] | [.fullName, .growthSeconds] | @csv'
```

#### Notification payloads

```bash
# One-line Slack-style message
robotcode --format json results summary \
  | jq -r '"\(.status): \(.counts.passed)/\(.counts.total) passed in \(.elapsedSeconds / 60 | floor)m. \(.counts.failed) failed."'

# Diff summary against main
robotcode --format json results diff baseline.xml \
  | jq -r '"+ \((.added // []) | length) added · - \((.removed // []) | length) removed · \((.newFailures // []) | length) regressions · \((.newPasses // []) | length) fixes"'
```

#### Artefact gathering

```bash
# After a failed CI run: pull screenshots out for upload
robotcode results log --failed --extract ./extracted

# Then: zip the lot
zip -r artefacts.zip ./extracted
```

#### Flakiness signal

```bash
# Flaky tests over the last ten runs
robotcode --format json results compare results/output-*.xml --last 10 --show tests \
  | jq '[.tests.tests[] | select(any(.perGroup[]; .flaky)) | .fullName]'
```

### Tips for scripting

- **Pin the output format.** Always say `-f json` (between `robotcode` and the subcommand). The TEXT format is meant for humans and may evolve.
- **Empty array ≠ missing field.** Sections that exist but are empty come through as `[]`. Sections excluded by `diff --only` are absent. Use `// []` in jq to handle both.
- **Optional fields are absent, never `null`.** Test for presence of the key rather than for a `null` value; in jq use `(.failed // empty)`.
- **Trust `filtersApplied`.** If you're not sure your filters are being honoured, the field echoes them back — tag patterns in their canonical (normalised) form, everything else verbatim.
- **For AI agents:** when feeding tool output into an LLM, prefer the narrowest subcommand call you can make (`summary` over `show`, `show --top 5` over a full listing, `log --failed --level FAIL` over an unfiltered log). Each layer of filtering saves tokens and reduces the amount of reasoning the model has to spend on parsing.
