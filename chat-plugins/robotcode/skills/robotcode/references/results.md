# Interpreting test results — the `robotcode results` subcommands

`robotcode results` inspects a finished Robot Framework run — the `output.xml` / `output.json` it wrote — from the terminal. It reads the file **server-side** and returns only the slice you ask for: headline counts, per-test listings, the execution tree, aggregates, a run-to-run diff, or several runs side by side. The output file is auto-discovered from the active profile (override with `-o`), so it works the same on your own run, a CI artifact, or a colleague's — without ever loading the raw file into context.

Reach for it whenever a run has finished and the question is "did it pass, what failed, why, what changed, or how do the last runs compare?" — six subcommands (`summary`, `show`, `log`, `stats`, `diff`, `compare`) cover those, detailed below.

## Contents

1. The shared option surface across all six subcommands
2. `summary` — the headline
3. `show` — list individual tests
4. `log` — the log.html in plain text
5. `stats` — aggregate by tag / suite / status
6. `diff` — compare two runs
7. `compare` — several runs side by side
8. Auto-discovery and `-o` overrides
9. For custom analysis: `robot.api.ExecutionResult`

## 1. The shared option surface

The six subcommands share a consistent option surface:

- Standard Robot filters: `-i <tag>` / `-e <tag>` / `-s <suite>` / `-t <test>` / `--status pass|fail|skip|not-run` (with `--failed` / `--passed` / `--skipped` as shortcuts on `show` / `log` / `stats`)
- Longname-exact filters: `-bl <longname>` / `-ebl <longname>` — use these when you already have the test's full name (e.g. copied from a previous `show` output). Available on all six subcommands
- Test-metadata filters (RF 7.5+): `-btm <pattern>` / `-ebtm <pattern>` — select by the test's own `[Metadata]` with the same patterns as `robotcode robot` and `discover`: terms `NAME:VALUE` with `*` / `?`, combined with `AND` / `OR` / `NOT` as separate upper-case words (`-btm Issue:4409` → the results of every test for issue 4409, `"Author:Hans* NOT Reviewer:*"`). Every line of a multi-line value is a value of its own. A result file holds the values the run used, so variables in a value are already replaced there. Available on all six subcommands
- Full-text search: `--search TEXT` / `--search-regex PATTERN` — searches across names, messages, tags, documentation, metadata, and keyword names/args/docs/messages
- Output-file override: `-o PATH` (file or directory), except on `diff` and `compare`, which take their result files as arguments

## 2. `robotcode results summary` — the headline

```bash
robotcode results summary                                       # auto-discover the output file
robotcode results summary --failed                              # list every failing test below the totals
robotcode results summary -i smoke --status fail                # combine tag + status filters
robotcode results summary --search TimeoutError                 # full-text search across name/message/keywords/logs
robotcode results summary -bl "MyProject.Login.Login Works"     # exact-match by full longname
robotcode --format json results summary                         # structured payload (counts, status, elapsed, ...)
robotcode results summary -o results/old-run.xml                # specific output file (XML or JSON)
robotcode results summary -o /tmp/ci-results/                   # directory — auto-discovery runs inside it
```

This is the right starting point for any "did the run pass?" / "what failed?" question. The `--failed` listing shows each failing test with full name, `(path:line)` link, and the first line of the error message — exactly what you'd report to the user.

## 3. `robotcode results show` — list individual tests

```bash
robotcode results show                                # every test, one line each
robotcode results show --failed                       # only failures (shorthand for --status fail)
robotcode results show --failed --skipped             # multiple statuses (OR)
robotcode results show -i smoke -e wipANDnotready     # tag filters
robotcode results show -s "MyProject.Login.*"         # suite glob
robotcode results show --top 20                       # cap output
robotcode results show --show-tags                    # append the tag list after each test
robotcode results show --search AssertionError        # full-text search across all fields
robotcode results show --sort elapsed --top 10        # sort by duration (longest first), cap to 10
robotcode results show --sort status                  # FAIL → SKIP → PASS → NOT RUN
robotcode results show -bl "MyProject.Login.Login Works"  # exact-match by full longname
```

One line per test: status badge, full name, `(path:line)`, plus the first line of any failure/skip message. Reach for `show` over `summary --failed` when you need finer filters (combined status + tag + suite + search), a cap, tag info (`--show-tags`), or a specific sort order (`--sort name|suite|status|elapsed|start`).

## 4. `robotcode results log` — the log.html in plain text

```bash
robotcode results log                                            # full trace, all tests
robotcode results log --failed                                   # only failing tests' trees (shorthand for --status fail)
robotcode results log -t "*Login*"                               # by test-name glob
robotcode results log -bl "MyProject.Login.Login Works"          # exact-match by full longname — best for one specific test
robotcode results log --search TimeoutError                      # only tests where the substring appears (name/message/keywords/logs)
robotcode results log --level WARN                               # raise the message-level threshold (default INFO)
robotcode results log --max-depth 2                              # show keyword levels 1-2; deeper calls collapsed to a child-count summary
robotcode results log --failed --keyword-info                    # add each keyword's [Documentation]/[Tags]/[Timeout]
robotcode results log --suite-info                               # add suite-level metadata to the tree
robotcode results log --failed --extract /tmp/artefacts          # write referenced screenshots / base64 blobs out
robotcode results log --execution-messages                       # also the `<errors>` messages from outside the tests (imports, parsing)
```

Renders the per-test execution tree — keyword calls, control structures (`FOR` / `WHILE` / `IF` / `TRY` / `VAR` / `RETURN`), log messages — same content `log.html` shows but in plain text an agent can read directly. Use this when you need to *understand why* a test failed, not just *that* it failed.

## 5. `robotcode results stats` — aggregate by tag / suite / status

```bash
robotcode results stats                              # default: by status
robotcode results stats --by tag                     # how many pass/fail/skip per tag
robotcode results stats --by tag --by suite          # both sections in one call
robotcode results stats --by tag --sort elapsed --top 20   # 20 slowest tags
robotcode results stats --by suite --search Browser  # only suites touching the Browser keyword
robotcode results stats --by tag -bl "MyProject.Login.Login Works"   # stats limited to one specific test (rarely needed but possible)
robotcode --format json results stats --by tag       # structured for downstream tools
```

Each section is a table with pass/fail/skip counts and total elapsed per group. Sort orders: `name` (ascending) / `total` / `failed` / `elapsed` (descending). Reach for `stats` over `summary` when the user asks "which tags fail most", "which suite is slowest", "is failure clustered in one area", etc.

## 6. `robotcode results diff` — compare two runs

```bash
robotcode results diff baseline.xml                            # baseline vs auto-discovered current
robotcode results diff prev/output.xml curr/output.xml         # two explicit files
robotcode results diff baseline.xml --only new-failures        # restrict to regressions
robotcode results diff baseline.xml --only new-passes --only added  # combine categories
robotcode --format json results diff baseline.xml              # structured diff
```

`BASELINE` is required; `CURRENT` defaults to auto-discovery. Categories the `--only` filter takes: `new-failures` (regressions), `new-passes` (fixes), `status-changes` (any), `added` (test exists in current but not baseline), `removed`. The plain output is a structured table — perfect for "what changed since the last green run".

## 7. `robotcode results compare` — several runs side by side

```bash
robotcode results compare run1/output.xml run2/output.xml run3/output.xml   # one row per run: counts, start, elapsed
robotcode results compare results/output-*.xml --last 10 --show tests       # flaky tests and "failing since" over the last 10 runs
robotcode results compare a.xml b.xml c.xml --show failures                 # the same failure message over tests and runs
robotcode results compare a.xml b.xml c.xml --show elapsed                  # tests and suites slower in the last run than before
robotcode results compare a.xml b.xml --show messages                       # the runs' errors and warnings, new and gone ones
robotcode results compare linux=l.xml windows=w.xml --show environment      # RF, Python, OS and top-suite metadata per run
robotcode results compare nightly/*/output.xml --group-by-metadata Platform --show tests   # per platform
robotcode results compare a.xml b.xml --by tag                              # failed/total per tag, one column per run
robotcode --format json results compare a.xml b.xml c.xml --show tests      # structured
```

Reach for `compare` over `diff` when there are more than two runs or the question is about a series — "is this test flaky?", "since when does it fail?", "does it fail only on Windows?", "what got slower?". `diff` stays the tool for "what changed from the baseline to now" between two runs.

Every run is an argument — no auto-discovery — and `NAME=PATH` gives it a name. The runs are numbered `#1`, `#2`, … in argument order (`--run-order start-time` sorts by start), and the overview always comes first. Tests are matched by their full name, so the runs need the same top suite name. `--show` is repeatable and the views follow in the order given:

- `tests`: every test that failed in a run, with its status as one character per run (`P`, `F`, `S`, `N`, `-` for a run without the test), failed out of the runs that had it, **flaky** (at least two changes between pass and fail — one change is a new failure or a fix), and **failing since** (the run where its current series of failures began).
- `failures`: failure messages grouped over tests and runs, numbers ignored (`…/order/4711` and `…/order/4712` are one group), with the first run each appears in.
- `elapsed`: growth of the last run over the median of the runs before it, largest first, no threshold.
- `messages`: what `log.html` shows under "Test Execution Errors", per run, with new and gone ones.
- `environment`: what each file records — `Robot`/`Rebot` and its version, Python, OS, top-suite metadata. Nothing else is recorded; a file written by `rebot` shows rebot's version.

`--group-by-metadata NAME` groups the runs by a top-suite metadata value set with `--metadata` at run time. Everything that depends on the order of the runs is then computed per group and shown as `value · value` in group order; `--last N` keeps the last N runs of each group. `compare` exits with 0 whatever the runs show.

## 8. Auto-discovery and `-o` overrides

Auto-discovery (when `-o` is omitted) picks the active profile's configured output file, with timestamp-glob fallback, then `./output.xml` as last resort. `-o PATH` (file or directory) points at any XML / JSON — useful for inspecting an older run, a colleague's run, or a CI artefact downloaded locally.

## 9. For custom analysis: `robot.api.ExecutionResult`

**Only when `robotcode results` genuinely doesn't have a slice you need.** Most "I want a custom view" cases are already covered by `summary --failed`, `show --failed`/`--top`/`--sort`, `log --failed`/`--search`/`--max-depth`, `stats --by tag`, `diff`, `compare`, or `--format json` piped through `jq` — try those first. For genuine raw access, use the Python API the `results` command uses internally:

```python
from robot.api import ExecutionResult

# Path comes from the active profile's output-dir; the run prints it on finish.
r = ExecutionResult(result_file_path)
for t in r.suite.all_tests:
    if t.message and "DeprecationWarning" in t.message:
        print(t.full_name, t.elapsed_time)
```

`r.suite.statistics`, iterable `r.suite.all_tests`, `test.full_name`, `test.message`, `test.status`, `test.elapsed_time`, etc. (these names from RF 7.0) — no ElementTree, no XPath. Run it via the project's runtime so the same Robot Framework version reads what wrote.
