# Proposal

## Why

`robotcode results diff` compares exactly two runs, with a direction from baseline to current. Questions about more runs have no command: which tests are flaky over the last ten nights, since when a test fails, which failure hits many tests at once, which tests got slower, or what differs between the runs on Linux and on Windows. Today they need a script over `-f json` of several `diff` or `stats` calls.

## What Changes

- New command `robotcode results compare RUN RUN [RUN...]`, which puts two or more result files side by side. A run is a path or `NAME=PATH`.
- The overview, one row per run with its counts, start and elapsed time, always comes first and numbers the runs `#1`, `#2`, … or uses their names.
- `--by tag|suite` adds the counts per tag or suite with one column per run, as `stats --by` does for one run, with `--sort` and `--top`.
- `--show` adds views, repeatable:
  - `tests`: the status of each test that failed in a run, as one character per run, with the failed count, flaky tests and "failing since";
  - `failures`: the same failure message over tests and runs, numbers ignored, with the run it first appears in;
  - `elapsed`: tests and suites ranked by how much the last run grew over the median of the runs before it;
  - `messages`: the errors and warnings of each run, and which are new or gone;
  - `environment`: the Robot Framework, Python and platform of each run, and the metadata of its top suite.
- `--run-order arguments|start-time` orders the runs, by argument order by default; `--last N` keeps the last N runs.
- `--group-by-metadata NAME` groups the runs by a metadata value of their top suite: the runs of a group stand together, and every value that depends on the order of the runs is computed per group.
- The filters of `diff` apply to every run. `-f json` gives the same views with one value per run.
- The exit code is 0, as for `stats`; errors exit with 128 like every `results` command.
- The guide "Analyzing results" and the agent skill's results reference get a section on `compare`.

## Capabilities

### New Capabilities

- `results-compare`: what `robotcode results compare` shows for two or more result files, how runs are named, ordered and grouped, and its exit code.

### Modified Capabilities

None. The `results` commands' exit code 128 for errors in `cli-exit-codes` already covers the new command.

## Impact

- `packages/runner/src/robotcode/runner/cli/results/`: the command in `results.py`, its data shapes in `_models.py`, its Markdown in `_render.py`.
- Tests under `tests/robotcode/runner/cli/results/`.
- `docs/src/content/docs/guides/cli/analyzing-results.md`, the generated `docs/src/content/docs/reference/cli.md`.
- The agent skill in `robotframework-agent-plugins` (`references/results.md`) and its vendored copy in `chat-plugins/`.
- No new dependencies.
