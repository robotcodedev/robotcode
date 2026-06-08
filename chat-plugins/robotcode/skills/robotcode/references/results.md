# Interpreting test results — the `robotcode results` subcommands

`robotcode results` inspects a finished Robot Framework run — the `output.xml` / `output.json` it wrote — from the terminal. It reads the file **server-side** and returns only the slice you ask for: headline counts, per-test listings, the execution tree, aggregates, or a run-to-run diff. The output file is auto-discovered from the active profile (override with `-o`), so it works the same on your own run, a CI artifact, or a colleague's — without ever loading the raw file into context.

Reach for it whenever a run has finished and the question is "did it pass, what failed, why, or what changed?" — five subcommands (`summary`, `show`, `log`, `stats`, `diff`) cover those, detailed below. Parsing `output.xml` directly is almost always the wrong move (see §1 for why); let `results` filter server-side instead.

> **Note**: RobotCode auto-detects non-interactive use and disables paging/colors automatically — no extra flags needed. (If a wrapper ever forces a pager, `--no-pager --no-color` before the subcommand makes it explicit.)

## Contents

1. The shared option surface across all five subcommands
2. `summary` — the headline
3. `show` — list individual tests
4. `log` — the report.html in plain text
5. `stats` — aggregate by tag / suite / status
6. `diff` — compare two runs
7. Auto-discovery and `-o` overrides
8. For custom analysis: `robot.api.ExecutionResult`
9. JSON output during the run (RF 7+) and xUnit XML
10. Reporting back to the user

## 1. The shared option surface

Five subcommands share a consistent option surface — auto-discovering the output file from the active profile, accepting:

- Standard Robot filters: `-i <tag>` / `-e <tag>` / `-s <suite>` / `-t <test>` / `--status pass|fail|skip|not-run` (with `--failed` / `--passed` / `--skipped` as shortcuts on `show` / `log` / `stats`)
- Longname-exact filters: `-bl <longname>` / `-ebl <longname>` — use these when you already have the test's full name (e.g. copied from a previous `show` output); no glob ambiguity. Available on all five subcommands
- Full-text search: `--search TEXT` / `--search-regex PATTERN` — searches across names, messages, tags, documentation, metadata, and keyword names/args/docs/messages
- Output-file override: `-o PATH` (file or directory)

`--format json` / `--format text` is a **global** flag — put it *before* the subcommand (`robotcode --format json results summary`), not after it, the same as for `analyze` / `discover`.

All five emit text or JSON:

- **`summary`** — headline counts; add `--failed` to list failing tests above the counts
- **`show`** — one line per test (status, name, source, first failure-message line)
- **`log`** — full execution tree for matching tests (keywords, control flow, messages)
- **`stats`** — aggregate by `tag` / `suite` / `status`
- **`diff`** — compare two output files (status changes, added/removed tests)

Reaching for `xmllint`, `grep` on `output.xml`, opening the file with a generic read tool, or writing a custom parser is almost always wrong — the CLI covers every common case, and the rare ones map to the Python API (section 8). **`output.xml` for a non-trivial run is routinely tens to hundreds of megabytes**; pulling it into your context burns tokens for no benefit since `robotcode results` already filters server-side. Override the auto-discovered file with `-o PATH` / `--output PATH` on any subcommand (same flag name as `robot --output`).

## 2. `robotcode results summary` — the headline

```bash
robotcode results summary                                       # auto-discover the output file
robotcode results summary --failed                              # list every failing test above the totals
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
robotcode results show --tags                         # append the tag list after each test
robotcode results show --search AssertionError        # full-text search across all fields
robotcode results show --sort elapsed --top 10        # sort by duration (longest first), cap to 10
robotcode results show --sort status                  # FAIL → SKIP → PASS → NOT RUN
robotcode results show -bl "MyProject.Login.Login Works"  # exact-match by full longname
```

One line per test: status badge, full name, `(path:line)`, plus the first line of any failure/skip message. Reach for `show` over `summary --failed` when you need finer filters (combined status + tag + suite + search), a cap, tag info (`--tags`), or a specific sort order (`--sort name|suite|status|elapsed|start`). `--failed` / `--passed` / `--skipped` are additive shortcuts for `--status fail|pass|skip`.

## 4. `robotcode results log` — the report.html in plain text

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
robotcode results log --execution-messages                       # also include parser/discovery `<errors>` section
```

Renders the per-test execution tree — keyword calls, control structures (`FOR` / `WHILE` / `IF` / `TRY` / `VAR` / `RETURN`), log messages — same content `report.html` shows but in plain text an agent can read directly. Use this when you need to *understand why* a test failed, not just *that* it failed. `--max-depth N` is your friend on deeply nested suites: it collapses everything below level `N` to a child-count summary. For deeper inspection add `--keyword-info` (each keyword's `[Documentation]`/`[Tags]`/`[Timeout]`) or `--suite-info` (suite-level metadata). For HTML-rich messages, `pip install robotcode-runner[html]` improves conversion quality.

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

## 7. Auto-discovery and `-o` overrides

Auto-discovery (when `-o` is omitted) picks the active profile's configured output file, with timestamp-glob fallback, then `./output.xml` as last resort. `-o PATH` (file or directory) works the same way on all five subcommands and points at any XML / JSON — useful for inspecting an older run, a colleague's run, or a CI artefact downloaded locally.

## 8. For custom analysis: `robot.api.ExecutionResult`

**Only when `robotcode results` genuinely doesn't have a slice you need.** Most "I want a custom view" cases are already covered by `summary --failed`, `show --failed`/`--top`/`--sort`, `log --failed`/`--search`/`--max-depth`, `stats --by tag`, `diff`, or `--format json` piped through `jq` — try those first. For genuine raw access, use the Python API the `results` command uses internally:

```python
from robot.api import ExecutionResult

# Path comes from the active profile's output-dir; the run prints it on finish.
r = ExecutionResult(result_file_path)
for t in r.suite.all_tests:
    if t.message and "DeprecationWarning" in t.message:
        print(t.full_name, t.elapsed_time)
```

`r.suite.statistics`, iterable `r.suite.all_tests`, `test.full_name`, `test.message`, `test.status`, `test.elapsed_time`, etc. — no ElementTree, no XPath. Run it via the project's runtime so the same Robot Framework version reads what wrote.

## 9. JSON output during the run (RF 7+) and xUnit XML

`robotcode results` reads both XML and JSON outputs, so there's rarely a reason to switch formats. The exceptions — both for downstream tooling, not for agent consumption:

```bash
robotcode robot --output output.json ...           # RF 7+: smaller file / external JSON consumer
robotcode robot --xunit xunit.xml ...              # xUnit-format XML for CI dashboards (Jenkins, GitLab, GitHub)
```

## 10. Reporting back to the user

Lead with the headline (`X passed, Y failed, Z skipped`), then a short list of failed tests with a one-line reason each. Mention the paths to `log.html` / `report.html` so the user can open them; don't parse them. Don't dump JSON or XML in the response.
