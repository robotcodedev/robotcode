# Design

## Context

See proposal.md for the motivation and specs/results-compare/spec.md for the behavior. The current state of the code:

- `results.py` holds every `results` command. `diff` loads two files with `_load_execution_result`, applies `_apply_tree_filters` to each and matches tests by `_get_full_name`. `stats` buckets tests per tag (normalized like Robot Framework does), suite or status in `_build_stats_section`, which also sorts and cuts with `--top`.
- `_models.py` holds the JSON shapes (`CamelSnakeMixin` dataclasses, append-only), `_render.py` the Markdown, written with `app.echo_as_markdown` through the pager.
- The `results` group is marked `errors_exit_with_128`, so every error of a new subcommand exits with 128 without any code in the command.
- Measured on Robot Framework 7.5:
  - The root element of `output.xml`, and the top-level keys of `output.json`, hold `generator="Robot 7.5 (Python 3.14.9 on linux)"` and `generated`.
  - After `rebot` the generator reads `Rebot 7.5 (…)` and `generated` is rebot's time. The top suite keeps its start time when `rebot` gets one file. When it merges several, the new top suite has no start time and no metadata; both stay on the suites below it.
  - The run's errors and warnings are the `<errors>` section; it also holds copies of the WARN and ERROR messages logged in tests, as `log.html` shows them under "Test Execution Errors".
- `Result.generator` exists from Robot Framework 7.2 on. 5.0 to 7.1 keep only `generated_by_robot`, read from the first word of the generator.

## Goals / Non-Goals

**Goals:**

- The computations of the views are plain functions over a small per-run snapshot, testable without the CLI.
- Memory stays bounded by the snapshots, not by N parsed result trees.

**Non-Goals:**

- An exit code for findings, such as `--exit-code` for flaky tests. Decided by the user: `compare` shows and doesn't judge.
- Finding the current run from the profile, as `diff` does for `CURRENT`. Every run is an argument.
- Expanding globs or reading directories; the shell expands `results/output-*.xml`.
- Merging the runs of a group into one column (decided: groups are ordered and separated).
- Thresholds for elapsed times, and charts such as `▁▃▅`. The text output stays ASCII apart from the Markdown it already uses, because of the cp1252 crash of #683.
- Rename detection, as for `diff`.
- Library versions, host names or environment variables. A result file doesn't record them; `--metadata` at run time does, and `--show environment` shows it.
- A `robot.toml` section for `compare`.

## Decisions

### D1: The command in `results.py`, the computations in `_compare.py`

The Click command `compare` goes into `results.py` next to `diff`, so that it shares the filter options, `_load_execution_result` and `_apply_tree_filters`. The computations go into a new module `_compare.py`:

- parsing the run arguments;
- ordering, grouping and numbering;
- the snapshot of a run;
- the status characters, flaky tests and failing since;
- the message key and the groups of failures and messages;
- the median growth.

The data shapes go into `_models.py`, the Markdown into `_render.py`.

Alternative: everything in `results.py`, as `diff` does. It already has 2,200 lines, and the views of `compare` are larger than all of `diff`.

### D2: Run arguments parsed in a callback

The argument `RUNS` takes `nargs=-1` strings. A callback turns each into a run with an optional name: an existing file is a path; otherwise the text before the first `=` is the name and the rest the path. A missing file, an empty or repeated name are a `click.BadParameter`; fewer than two runs a `click.UsageError`. Both exit with 128.

Alternative: `click.Path(exists=True)` as for `diff`. It can't take `NAME=PATH`.

### D3: A snapshot per run, taken right after loading

Each file is loaded, its execution messages are taken from `<errors>` before the filters (as `summary` does, because the filters move messages), the filters are applied, and the run is reduced to a snapshot:

- per test: the full name, status, elapsed time, message, source and line;
- per suite: the full name and elapsed time;
- the counts and the elapsed time;
- the tags of each test, normalized as `stats` does;
- start time, generator, top suite name and metadata;
- the execution messages with their level.

Then the parsed tree is dropped. `--by` reuses the bucketing of `_build_stats_section`, split out of it so that both commands share it; sorting and `--top` stay per command.

Alternative: keep every `Result`. Thirty large `output.xml` files would be held in memory at once.

### D4: Order, groups, numbers, then `--last`

1. The runs are ordered by argument order or, with `--run-order start-time`, by a stable sort on the start time: the top suite's start, else the earliest start of its child suites, else last.
2. With `--group-by-metadata`, a stable partition by the value of the top suite's metadata puts the runs of a group together, the groups in the order of their first run.
3. The runs are numbered `#1` to `#n` in that order.
4. `--last N` keeps the last N runs, of each group with groups. The numbers stay, so `#7` names the same run with and without `--last`.

Column heads are the run's name when it has one, else its number.

### D5: The status of a test and what follows from it

- Status characters: `P` (PASS), `F` (FAIL), `S` (SKIP), `N` (NOT RUN), `-` for a run without the test, a space between groups.
- Flaky: count the changes between `P` and `F` in the sequence without `S`, `N` and `-`. Two or more make the test flaky, so a new failure (`PPPFFF`) or a fix (`FFFPPP`) is not flaky, `diff` and "failing since" show those.
- Failing since: walk back from the last `F` of the sequence without `-` while the status is `F`.

All of this is computed per group (one group without `--group-by-metadata`).

### D6: Message key

`re.sub(r"\d+", "#", text)`, then the whitespace is collapsed with `" ".join(text.split())`. The shown message is the first one of the group in run order, cut to `--message-chars` (default 120, as for `diff`). Messages of execution errors are keyed by level and text.

Alternative: the exact text, or the first line only. Decided by the user: numbers are ignored.

### D7: Growth

`statistics.median` of the elapsed times of the runs before the last run that had the item, within the group. Growth is the last time minus the median; only growth above zero is listed. The percent is left empty when the median is 0.

### D8: Environment for every Robot Framework version

A helper bound once at import time, as the other version differences in `results.py`:

- From 7.2 on, it reads `Result.generator` and `Result.generation_time`.
- Before 7.2, it reads the attributes of the first element of an `output.xml` via `ElementTree.iterparse` with the `start` event.
- An `output.json` gives none before 7.2 (measured): robot writes JSON only from 7.2 on, rebot of 7.0 and 7.1 writes only the suite without these fields, and 7.0 and 7.1 refuse a JSON file of 7.2 or newer when they read it. Its environment stays empty.

A regex splits `Tool Version (Python X on Platform)`. A generator it can't split is shown as the tool, with the other fields empty.

### D9: Text output

Sections: `# Compare`, `## Runs`, `## By Tag` and `## By Suite`, `## Tests`, `## Failures`, `## Elapsed` with a table for suites and one for tests, `## Messages`, `## Environment`. Status sequences are code spans, so the characters line up. Per-group values are joined with ` · `. Every `--top` cut ends with the `_… N more not shown_` line of `stats`.

### D10: JSON shape

`CompareResult` holds `runs` (number, name, file info with the generator fields, group, start time, elapsed time, counts), the `--by` sections (one entry per run, `null` without the group), and one optional field per `--show` view.

Values that are computed per group are a list `perGroup` of objects with the group's name. Without `--group-by-metadata` the list has one entry whose name is `null`, so a script reads the same shape with and without groups.

Statuses are Robot Framework's names (`"PASS"`, `"FAIL"`, …), not the characters.

### D11: Docs and skill

- In `guides/cli/analyzing-results.md`:
  - a section "`compare` — runs side by side" after `diff`, with the overview, `--by`, every view, naming, order, groups and `--last`;
  - "`compare` JSON" in the JSON reference;
  - the CI recipe "Flakiness signal" uses `compare --show tests` with `jq` on `flaky`.
- `reference/cli.md` is regenerated.
- The skill's `references/results.md` in `robotframework-agent-plugins` gets a section on `compare`, and "five subcommands" becomes six. Without it an agent asked about flaky tests would compare files itself. The vendored copy in `chat-plugins/` is re-synced with `hatch run build:sync-chat-plugin` after the commit in agent-plugins.

## Risks / Trade-offs

- [Runs with different top suite names share no tests] → As for `diff`. The guide says to run with the same `--name`, and the overview shows each run's path.
- [Many runs make wide tables] → `--last N`, and JSON holds every run.
- [Ignoring numbers merges different assertions, such as `Expected 3 but got 5` and `Expected 1 but got 2`] → Accepted by the user. The group shows a real message, and JSON lists the tests.
- [A file written by `rebot` shows rebot's version] → Shown as `Rebot 7.5`, so it isn't mistaken for the run's version. The guide says so.
- [Start times have no time zone] → Runs from machines in different time zones may be ordered wrongly by `--run-order start-time`. The guide says so; argument order is the default.
- [An `output.json` read with Robot Framework 7.0 or 7.1 has no environment] → It records none (D8); the row shows the run's number only.
- [`_build_stats_section` is split for reuse] → `stats` keeps its output; its tests run unchanged.
