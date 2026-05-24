# Analyzing Run Results

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

The five subcommands all read the same result file and share the same filter, search, and output-format options — once you've learned one the others follow:

| Subcommand | Use it when you want to … |
|---|---|
| [`summary`](#summary-headline-numbers) | … see the headline counts and overall status |
| [`show`](#show-list-individual-tests) | … list individual tests (with sort, filter, search) |
| [`log`](#log-walk-the-execution-tree) | … inspect the per-test execution tree |
| [`stats`](#stats-aggregate-by-tag-suite-or-status) | … aggregate by tag, suite, or status |
| [`diff`](#diff-compare-two-runs) | … compare two runs and find new failures |

This guide is split in two:

1. **[Part 1 — Using the commands](#quick-start)** walks through every subcommand from the terminal perspective: what each one does, what shows up on the screen, and what filters and flags are available.
2. **[Part 2 — JSON reference](#json-reference)** documents the structured output for scripts, CI pipelines and AI workflows — the JSON schema of every subcommand plus jq-based recipes.

For the exhaustive option list see the auto-generated [CLI reference](cli.md#results).

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
   - If `PATH` is a directory, the newest `output.xml` or `output.json` inside is picked. Useful when CI writes timestamped output directories.
2. The output file resolved from your active `robot.toml` profile (`output_dir` / `output` settings).
3. The most recent `output.xml` / `output.json` in the working directory.

If none of those produce a file, the command exits with a clear error (`Result file not found …` or `No result file found in …`). If the file exists but cannot be parsed (corrupted XML, premature termination of the run), you get `failed to parse <path>: …` with the underlying parser error.

Both `output.xml` and `output.json` are supported; `robotcode results` picks the right parser automatically based on the file. (`output.json` is the RF 7.0+ opt-in format you get by passing `--output something.json` to `robotcode robot` or setting `output_format = "json"` in your profile.)

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

Use the positive forms (`--pager`, `--color`) to *force* either feature even when stdout isn't a TTY — handy when you want to pipe coloured output into `less -R` yourself.

## `summary` — headline numbers

```bash
robotcode results summary
```

Output is a short block with the overall status, the test counts, the wall-clock time, and (with `--failed`) the list of failed tests above it.

```text
Failures (2):
FAIL    MyProject.Login.Bad Password (tests/login/test_login.robot:42)
        AssertionError: Expected 'Login failed' but got 'Internal error'
FAIL    MyProject.Checkout.Empty Cart (tests/checkout/test_empty.robot:11)
        TimeoutError: keyword 'Open Cart' did not complete in 5s

Summary: results/output.xml
  - Status:   FAIL
  - Total:    42
  - Passed:   37
  - Failed:   2
  - Skipped:  3
  - Started:  2026-05-15 08:11:02
  - Ended:    2026-05-15 08:12:25
  - Elapsed:  1m 23s
  - Messages: 318 INFO, 7 WARN, 2 FAIL
```

### Useful flags

| Flag | Purpose |
|---|---|
| `--failed` | Append the list of failed tests, each with its message and source location |
| `--full-paths` | Show absolute source paths instead of paths relative to the working directory |

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
| `--tags` | Render the test's tags in the output, in normalised form (`Bug 1`, `bug_1` and `Bug1` all show as `bug1`). |
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

Tests with no value for the sort field (e.g. no recorded start time, no elapsed time) sort to the end regardless of `--reverse`.

### Recipes

```bash
# What broke that's tagged smoke, sorted by who took longest?
robotcode results show --include smoke --failed --sort elapsed

# 10 slowest tests overall
robotcode results show --sort elapsed --top 10

# Failing tests with full message (no truncation) and tags
robotcode results show --failed --message-chars 0 --tags

# Find tests by name match
robotcode results show --search "TimeoutError" --tags

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

### Flag reference

| Flag | Effect |
|---|---|
| `--level TRACE\|DEBUG\|INFO\|WARN\|ERROR\|FAIL` | Suppress messages below this severity. Default: `INFO`. |
| `--max-depth N` | Collapse keyword bodies deeper than `N` levels. Default: `0` (unlimited). |
| `--extract DIR` | Decode embedded `data:` URIs and copy externally-referenced files into `DIR`. |
| `--raw-html` | Keep the original HTML markup in log messages. No artefact decoding happens in this mode. |
| `--execution-messages` | Include parser/discovery errors that fired before the run (library import failures, syntax errors, …). |
| `--keyword-info` | Print each executed keyword's `[Documentation]`, `[Tags]` and `[Timeout]` under its header (and add them to the JSON entry). Off by default; see [`--keyword-info` and `--suite-info`](#--keyword-info-and---suite-info). |
| `--suite-info` | Group tests under suite headers showing the suite name, source, `Documentation` and `Metadata` (and add a `suites` array plus per-test `suite` ref to the JSON). Off by default. |
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
│   └── screenshot.png        # external <img src="screenshot.png">
├── MyProject.Checkout.Empty_Cart/
│   └── ...
```

Test names are sanitised to filesystem-safe directory names (spaces become underscores, path separators are removed). External file references are resolved relative to the directory containing the result file; if the referenced file doesn't exist, the artefact is recorded as skipped with reason `missing-source` and nothing is copied. References that would escape the base directory via `..` are blocked — there is no way to overwrite files outside `DIR`.

### `--raw-html` vs default

By default, log messages tagged as HTML (Robot Framework's `Log    ...    HTML`) are converted to a plain-text approximation: `<img src="data:image/png;base64,…">` becomes a placeholder like `_(embedded image — see artefacts: no alt text)_` and the actual bytes are decoded and stored separately for `--extract`. `<a href="...">link</a>` becomes a markdown-style link.

With `--raw-html` the conversion is skipped — the original HTML markup is preserved verbatim and no artefacts are extracted. Use this when you want to feed the output into something that renders HTML itself.

### `--keyword-info` and `--suite-info`

Both flags add **structured metadata** to the log output and are independent — you can pass either or both. They default to off so the standard `log` view stays compact.

**`--keyword-info`** — for every executed `KEYWORD` / `SETUP` / `TEARDOWN`, the keyword's own `[Documentation]`, `[Tags]` and `[Timeout]` (taken from the keyword definition, not the call) are emitted. In TEXT the renderer prints them as indented `[Documentation] / [Tags] / [Timeout]` lines under the keyword header; in JSON they appear as `doc` / `tags` / `timeout` keys on the matching body-item entry. Fields whose underlying setting is empty are dropped, so `BuiltIn.Log` (which has a docstring but no tags) shows only `doc`.

**`--suite-info`** — tests get grouped under one `Suite:` header per parent suite. The header carries the suite's `fullName`, source path, executed status, plus the suite's `Documentation` (with `...` continuation lines for multi-line docs) and one `[Metadata]` line per key. In JSON, `LogResult.suites` is populated with one entry per surviving suite, and every test gains a `suite` field cross-referencing the parent suite by `fullName`.

Combine both for a maximal view that mirrors the structure of the original `.robot` files:

```bash
robotcode results log --suite-info --keyword-info
```

Example TEXT output:

```
Suite: MyProject.Login (tests/login.robot) PASS
  [Documentation] Exercises the login flow against the staging environment.
  [Metadata] OwnerTeam = identity-squad

  Test: MyProject.Login.Bad Password (tests/login.robot:42) FAIL
    [SETUP] Open Browser    PASS
      [Documentation] Launches a fresh Chromium with our shared profile.
      [Tags] browser    setup
      ...
```

### Recipes

```bash
# Drill into one failing test
robotcode results log -bl MyProject.Login.Bad_Password

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

Output:

```text
By Tag:
    NAME              TOTAL  PASS  FAIL  SKIP  ELAPSED
    regression          24    19     5     0    4m 12s
    smoke               18    18     0     0    47s
    slow                 7     5     1     1    2m 03s
    bug-1842            2      0     2     0    8s

By Suite:
    NAME                                  TOTAL  PASS  FAIL  SKIP  ELAPSED
    MyProject.Checkout                      14    10     4     0    3m 11s
    MyProject.Login                         12    12     0     0    1m 02s
    MyProject.Search                         8     7     0     1    52s
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
| `added` | exist only in current (added since baseline) |
| `removed` | exist only in baseline (deleted/renamed since baseline) |

Tests that have the same status in both runs are **not** reported — `diff` shows changes only.

### Flag reference

| Flag | Effect |
|---|---|
| `--only new-failures\|new-passes\|status-changes\|added\|removed` | Restrict output to these categories. Repeatable. |
| `--message-chars N` | Truncate the per-entry messages to `N` chars. Default: `120`. |
| `--full-paths` | Absolute source paths. |

The standard `--status / -i / -e / -s / -t / -bl / -ebl / --search / --search-regex` filters apply to **both** baseline and current before matching. This lets you scope the comparison to a tag, sub-suite, or pattern without re-running anything:

```bash
robotcode results diff baseline.xml --include smoke
robotcode results diff baseline.xml --suite "*.Checkout.*"
robotcode results diff baseline.xml --search Timeout
```

### Why `diff` always exits 0

`diff` exits 0 even when there are new failures, so it composes cleanly with other tools. For a regression gate, drive the exit code from the structured output — see [CI recipes](#ci-recipes) in the JSON reference.

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

## Filters

Every subcommand accepts the same filter set. Filters combine with **AND** — every test must satisfy every filter to make it through. Within a single repeatable flag (`--status`, `--include`, etc.) the matches combine with **OR** in the way Robot Framework normally treats those options.

| Flag | Behavior |
|---|---|
| `--status pass\|fail\|skip\|not-run` | Repeatable; tests whose status is in the chosen set. |
| `--failed` / `--passed` / `--skipped` | Shorthands for `--status fail` / `--status pass` / `--status skip`. Additive with `--status` and with each other (OR semantics). Available on `show`, `log`, `stats`. |
| `-i/--include TAG_PATTERN` | Robot tag-pattern syntax (see below). Repeatable. |
| `-e/--exclude TAG_PATTERN` | Same syntax, exclusion side. Repeatable. |
| `-s/--suite GLOB` | Match against the suite's full longname. Repeatable. |
| `-t/--test GLOB` | Match against the test's full longname. Aliased as `--task`. Repeatable. |
| `-bl/--by-longname NAME` | Exact longname match (no glob expansion). Repeatable. |
| `-ebl/--exclude-by-longname NAME` | Exclusion variant of `--by-longname`. Repeatable. |

### Tag-pattern syntax (`-i`/`-e`)

Tag patterns follow Robot Framework's own rules:

- A plain tag (`smoke`) matches tests carrying that tag.
- `AND` (uppercase) requires multiple tags: `smokeANDregression` matches only tests that have **both** tags.
- `NOT` excludes: `smokeNOTslow` matches `smoke` minus `slow`.
- Tags are matched case-insensitively, and whitespace and underscores are ignored — `smoke_test`, `Smoke Test` and `smoketest` all refer to the same tag. Other punctuation, including hyphens, is significant: `bug-123` and `bug123` are distinct.
- Glob characters `*` and `?` work inside a tag pattern: `bug-*` matches any tag starting with `bug-`.

You can repeat `-i` to OR multiple patterns: `-i smoke -i regression` selects tests that carry **either** `smoke` **or** `regression`.

### Suite / test globs

`-s` / `-t` accept shell-style glob patterns matched against the full longname:

- `*` matches any sequence of characters (including `.`, so `*.Login.*` matches at any depth).
- `?` matches a single character.
- Matching is case-insensitive and applied to the full longname (`MyProject.Login.Bad Password`).
- Repeat for OR: `-s "MyProject.Login.*" -s "MyProject.Checkout.*"`.

Quote globs in the shell — `--suite "*.Login.*"` and `--test "Test ?"` need quotes so the shell doesn't expand them against the local filesystem.

### `--by-longname` vs `--suite` / `--test`

- `-s` / `-t` are **glob** matches and accept patterns.
- `-bl` / `-ebl` are **exact** matches against the full longname — no glob expansion. They mirror `robotcode robot --by-longname` so you can hand the same names to `robot` and `results`.

Use `-bl` when you have a precise name to filter against (often pasted from the failure list); use `-s/-t` when you want pattern matching.

## Search

`--search` and `--search-regex` are **mutually exclusive** (passing both is a usage error). They apply across:

- the test's `name` and full longname
- the test's failure message
- the test's tags
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

When matching against **tags** specifically, both the pattern and each tag are normalised the way Robot Framework normalises tags (lowercase, whitespace and underscores ignored). So `--search "bug 1"` matches tests tagged `bug_1`, `Bug1`, or `BUG 1`. Other targets — name, message, keyword arguments, log text — are matched literally without normalisation.

```bash
robotcode results log --search "TimeoutError"
robotcode results log --search-regex 'AssertionError.*expected: \d+'
robotcode results log --search-regex '(?i)login'   # case-insensitive
```

### Anchors and alternation

The regex is matched against each target string individually, **not anchored** to the whole string — a pattern like `Login` matches any target that contains `Login` somewhere. Use `^` and `$` if you want anchored matches. Note that anchors apply per target string, so `^Login` matches a test whose full longname is `Login.Bad Password` but also a keyword named `Login With Token` somewhere inside the test body.

### Highlighting in the terminal

On `log` (and `show`), matches are highlighted inline in the TEXT output with a yellow background so you can scan visually. Structured output (JSON/TOML) is unchanged — searching only filters, it doesn't add markup.

### Search on `summary` and `stats`

`--search` works on these too, but its effect is subtle: the matching tests narrow the input set, and the counts / aggregations are computed against that narrowed set. So `robotcode results summary --search Login` is "how is the Login subset doing" and `robotcode results stats --by tag --search Login` is "which tags are involved in the Login subset".

### Invalid patterns

An unparseable regex (e.g. `[unclosed`) yields a usage error pinpointing where the pattern failed to compile. The command exits non-zero before reading the result file.

## Tips for terminal use

- **Quote your globs.** `--suite "*.Login.*"` and `--test "Test ?"` need quotes so the shell doesn't expand them against the local filesystem first.
- **Filters apply before aggregation.** `stats`, `summary` and `diff` all run the filter pipeline first, so `--search Login` followed by `--by tag` gives you tag stats over the Login subset, not all tags whose name happens to contain "Login".
- **`-bl` is for exact names, `-t` is for patterns.** When you copy a failing-test name out of the failure list, `-bl` is usually what you want — no need to escape glob characters.
- **Save your baselines.** Archive `output.xml` from your green main branch (or main-CI run) and feed it to `diff` from feature branches — that's the fastest way to catch regressions before review.
- **`diff` doesn't fail the build.** It always exits 0. If you want a regression gate, see the [CI recipes](#ci-recipes) in the JSON reference.

---

# JSON reference

When you set `-f json` (or `-f json_indent` for pretty-printed, or `-f toml`) between `robotcode` and the subcommand, every result command emits structured data instead of the terminal-formatted text. This is what CI pipelines, scripts and AI agents consume.

```bash
robotcode --format json results summary
robotcode --format json results show --failed --sort elapsed
robotcode --format json results log --failed
```

This part of the guide is the schema reference: what fields each subcommand emits, when they're present, and how to consume them safely.

## Schema rules

A few rules hold across every subcommand:

- **camelCase keys.** `fullName`, `elapsedSeconds`, `messagesCount`, etc.
- **ISO-8601 timestamps** with microsecond resolution.
- **Optional fields are omitted, not `null`.** A `null` literal never appears in the output. If a field has no value (e.g. `failed` without `--failed`, `tags` on an untagged test), the key is simply absent from the JSON object.
- **Scalar fields with a meaningful zero are always emitted.** `counts.failed = 0`, `truncated = 0`, `elapsedSeconds = 0.0` all stay in the object. Only optional fields disappear when unset.
- **Empty array ≠ missing field.** Sections that "exist but are empty" come through as `[]`; sections that were never requested (e.g. anything excluded by `diff --only`) are absent. The two are different and your queries should handle both, typically via `// []` in jq.
- **Stability.** Fields are appended over time, never renamed or removed in place. New fields are additive; existing consumers keep working.

## `summary` JSON

```json
{
  "file": {
    "source": "results/output.xml",
    "relSource": "results/output.xml"
  },
  "status": "FAIL",
  "counts": { "total": 42, "passed": 37, "failed": 2, "skipped": 3, "notRun": 0 },
  "elapsedSeconds": 83.4,
  "startTime": "2026-05-15T08:11:02",
  "endTime": "2026-05-15T08:12:25",
  "failed": [
    {
      "name": "Bad Password",
      "fullName": "MyProject.Login.Bad Password",
      "suite": "MyProject.Login",
      "status": "FAIL",
      "message": "AssertionError: Expected 'Login failed' but got 'Internal error'",
      "tags": ["smoke"],
      "elapsedSeconds": 0.234,
      "startTime": "2026-05-15T08:11:04",
      "source": "tests/login/test_login.robot",
      "relSource": "tests/login/test_login.robot",
      "lineno": 42
    }
  ],
  "messagesCount": { "INFO": 318, "WARN": 7, "FAIL": 2 }
}
```

Field notes:

- `failed` only appears when `--failed` was passed.
- `messagesCount` aggregates log messages by level (`TRACE` / `DEBUG` / `INFO` / `WARN` / `ERROR` / `FAIL`). Only levels with at least one message appear — empty buckets are omitted, not emitted as `0`.
- `executionMessagesCount` (parser / discovery errors that fired outside of test execution) appears **only** when there were any.
- `filtersApplied` (see [below](#filtersapplied)) appears when any filter was passed.

## `show` JSON

```json
{
  "file": { "source": "results/output.xml" },
  "counts": { "total": 42, "passed": 37, "failed": 2, "skipped": 3, "notRun": 0 },
  "tests": [
    {
      "name": "Bad Password",
      "fullName": "MyProject.Login.Bad Password",
      "suite": "MyProject.Login",
      "status": "FAIL",
      "message": "AssertionError: Expected 'Login failed' …",
      "tags": ["smoke", "regression"],
      "elapsedSeconds": 0.234,
      "startTime": "2026-05-15T08:11:04",
      "source": "tests/login/test_login.robot",
      "lineno": 42
    }
  ],
  "truncated": 0,
  "elapsedSeconds": 83.4,
  "startTime": "2026-05-15T08:11:02",
  "endTime": "2026-05-15T08:12:25"
}
```

Field notes:

- `tests[]` is always present, possibly empty.
- `tags` is always emitted for tests that have any (and absent for untagged tests), in normalised form (`Bug 1`, `bug_1`, `Bug1` all come through as `"bug1"`). The `--tags` flag in TEXT mode is render-only — it doesn't affect the JSON.
- `truncated` is the number of tests dropped by `--top N`; `0` when nothing was dropped.
- The order of `tests[]` reflects `--sort` and `--reverse`.

## `log` JSON

```json
{
  "file": { "source": "results/output.xml" },
  "tests": [
    {
      "fullName": "MyProject.Login.Bad Password",
      "status": "FAIL",
      "message": "AssertionError: Expected 'Login failed' …",
      "body": [ /* recursive tree of body items, see below */ ],
      "artifacts": [ /* aggregated artifact refs for the whole test */ ],
      "source": "tests/login/test_login.robot",
      "lineno": 42,
      "elapsedSeconds": 0.234,
      "startTime": "2026-05-15T08:11:04",
      "suite": "MyProject.Login"
    }
  ],
  "suites": [
    {
      "fullName": "MyProject.Login",
      "name": "Login",
      "status": "FAIL",
      "doc": "Exercises the login flow against staging.",
      "metadata": { "OwnerTeam": "identity-squad" },
      "source": "tests/login.robot",
      "elapsedSeconds": 12.7,
      "startTime": "2026-05-15T08:11:02"
    }
  ],
  "executionMessages": [ /* only with --execution-messages */ ],
  "extractDir": "./extracted",
  "extractedCount": 7
}
```

The `body` array of each test is a recursive tree of body items. Field notes:

- `extractDir` / `extractedCount` appear only with `--extract DIR`.
- `executionMessages` appears only with `--execution-messages`.
- `suites` and the per-test `suite` cross-reference appear only with `--suite-info`. One `suites` entry per parent suite that has at least one surviving test, in traversal order. Empty `metadata` / `doc` are dropped.
- Artefact entries carry `kind` (`"image"` | `"file"`), `src`, and — when extraction happened — `extractedTo` (absolute path of the written file). Failed extractions get a `skippedReason` instead (e.g. `"missing-source"`, `"target-traversal"`).

### Body-item types

Every body-item entry has a `type` field. The vocabulary tracks Robot Framework's own body-item taxonomy:

| `type` | What it represents | Notable fields |
|---|---|---|
| `KEYWORD` | A keyword call | `name`, `owner`, `args`, `assign`, `body` |
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

## `stats` JSON

```json
{
  "file": { "source": "results/output.xml" },
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

## `diff` JSON

```json
{
  "baseline": { "source": "baseline/output.xml" },
  "current": { "source": "current/output.xml" },
  "newFailures": [
    {
      "fullName": "MyProject.Login.Bad Password",
      "baselineStatus": "PASS",
      "currentStatus": "FAIL",
      "currentMessage": "AssertionError: Expected 'Login failed' …",
      "source": "tests/login/test_login.robot",
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

## `filtersApplied`

Every subcommand's JSON output includes a `filtersApplied` field when **any** filter was passed. It echoes back the filters the command actually saw:

```json
"filtersApplied": {
  "status": ["fail"],
  "include": ["bug1"],
  "exclude": ["smokeANDregression"],
  "suite": ["*.Login.*"]
}
```

Most filters come back verbatim. The two exceptions are `include` and `exclude`:

- A plain single-tag pattern is normalised the way Robot would (`BUG 1` → `bug1`, `Smoke_Test` → `smoketest`), so you see how the filter is actually being compared.
- A pattern containing an uppercase `AND` / `OR` / `NOT` operator is echoed verbatim, because each operand would need to be normalised individually and the surrounding structure carries deliberate meaning.

This is useful when piecing together a complex CI command — you can assert that the filter set ended up where you expected. When no filters were passed, the field is absent.

## CI recipes

A grab-bag of jq-based recipes. Pin `-f json` between `robotcode` and the subcommand to lock the format.

### Pass/fail the build

```bash
# Fail on any test failure
robotcode --format json results summary | jq -e '.counts.failed == 0'

# Fail only on new failures vs a checked-in baseline
robotcode --format json results diff baseline/output.xml \
  | jq -e '(.newFailures // []) | length == 0'

# Allow a fixed budget of failures
FAILED=$(robotcode --format json results summary | jq '.counts.failed')
test "$FAILED" -le 3
```

### Slow-test report

```bash
# Top 20 slowest tests, CSV
robotcode --format json results show --sort elapsed --top 20 \
  | jq -r '.tests[] | [.fullName, .elapsedSeconds] | @csv'

# Tag-level elapsed budget (minutes)
robotcode --format json results stats --by tag --sort elapsed \
  | jq -r '.sections[].groups[] | [.name, (.elapsedSeconds / 60)] | @csv'
```

### Notification payloads

```bash
# One-line Slack-style message
robotcode --format json results summary \
  | jq -r '"\(.status): \(.counts.passed)/\(.counts.total) passed in \(.elapsedSeconds / 60 | floor)m. \(.counts.failed) failed."'

# Diff summary against main
robotcode --format json results diff baseline.xml \
  | jq -r '"+ \((.added // []) | length) added · - \((.removed // []) | length) removed · \((.newFailures // []) | length) regressions · \((.newPasses // []) | length) fixes"'
```

### Artefact gathering

```bash
# After a failed CI run: pull screenshots out for upload
robotcode results log --failed --extract ./extracted

# Then: zip the lot
zip -r artefacts.zip ./extracted
```

### Flakiness signal

```bash
# Tests that flipped state between two runs (either direction)
robotcode --format json results diff run-1.xml run-2.xml \
  | jq '((.newFailures // []) + (.newPasses // [])) | map(.fullName)'
```

## Tips for scripting

- **Pin the output format.** Always say `-f json` (between `robotcode` and the subcommand). The TEXT format is meant for humans and may evolve.
- **Empty array ≠ missing field.** Sections that exist but are empty come through as `[]`. Sections excluded by `diff --only` are absent. Use `// []` in jq to handle both.
- **Optional fields are absent, never `null`.** Test for presence of the key rather than for a `null` value; in jq use `(.failed // empty)`.
- **Trust `filtersApplied`.** If you're not sure your filters are being honoured, the field echoes them back — tag patterns in their canonical (normalised) form, everything else verbatim.
- **For AI agents:** when feeding tool output into an LLM, prefer the narrowest subcommand call you can make (`summary` over `show`, `show --top 5` over a full listing, `log --failed --level FAIL` over an unfiltered log). Each layer of filtering saves tokens and reduces the amount of reasoning the model has to spend on parsing.
