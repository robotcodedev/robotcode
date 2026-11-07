# Tasks

## 1. The command and the overview

- [x] 1.1 Add `_compare.py` with the parsing of the run arguments (D2) and wire it into a `compare` command in `results.py`, placed after `diff`. In `tests/robotcode/runner/cli/results/test_compare.py`, cover the scenarios of "Runs from the arguments" and "Names are unique": two paths, named runs, an existing `a=b.xml`, one run only, a missing file, a repeated name. The error cases exit with 128. Verify that the tests pass.
- [x] 1.2 Add the snapshot of a run (D3) and the ordering and numbering (D4, without groups): `--run-order arguments|start-time` and `--last N`, with numbers that stay. Cover "Order of the runs" and "The last runs" with result files made in `tmp_path` by `robot` with the same `--name`: argument order, start time, a file merged by `rebot` from two outputs, the last three of five. Verify that the tests pass.
- [x] 1.3 Add the overview to the text output (`_render.py`) and to JSON (`CompareResult` and its runs in `_models.py`, D10), with the filters of `diff` applied to every run. Cover the scenarios of:
  - "Overview of the runs";
  - "Filters apply to every run";
  - "Tests are matched by their full name";
  - "Exit code": 0 with failed tests, 128 for a file that is no result file;
  - the JSON of the runs.

  Write the docstring with examples. Verify that the tests pass.
- [x] 1.4 In `docs/src/content/docs/guides/cli/analyzing-results.md`, add the section "`compare` — runs side by side" after `diff`. It covers the overview, naming with `NAME=PATH`, `--run-order` with its time-zone and `rebot` limits, `--last` and the same `--name` for all runs. Add "`compare` JSON" to the JSON reference with the runs. Regenerate `reference/cli.md` with `hatch run create-cmd-line-docs` and verify that its diff only adds `results compare`. Verify in the docs dev server that the page renders, and that every command in the new text runs as written.

## 2. Counts per tag or suite

- [x] 2.1 Split the bucketing out of `_build_stats_section` so that `stats` and `compare` share it (D3), and verify that `tests/robotcode/runner/cli/results/test_stats.py` passes unchanged.
- [x] 2.2 Add `--by tag|suite` (repeatable), `--sort name|total|failed|elapsed` by the last run, and `--top`, in text with `failed/total` cells and in JSON with one entry per run. Cover "Counts per tag or suite" and the `--by` part of "Limit of rows". Verify that the tests pass.
- [x] 2.3 Describe `--by`, `--sort` and `--top` of `compare` in the guide and in "`compare` JSON". Regenerate `reference/cli.md`, and verify the commands as written and the page in the dev server.

## 3. `--show` and the status of each test

- [x] 3.1 Add `--show` with the five views as choices, repeatable, shown once each in the order given after the `--by` tables, and `--top` for the views. Cover "Views": two views in order, an unknown view exiting with 128. Verify that the tests pass.
- [x] 3.2 Add `--show tests` (D5), computed per group with a single group for now (D10 `perGroup`):
  - the status characters with `-` for a run without the test;
  - the failed count out of the runs that had the test, and the sort by it;
  - flaky tests and failing since.

  Cover in plain function tests of `_compare.py`:
  - "Status of each test over the runs";
  - "Flaky tests": `PFPPFP`, `PPPFFF`, `PSF`;
  - "Failing since": `PPPFFF`, `PPF-FF`, `PPFFFP`.

  Cover with the CLI a test added later (`----PPFPPP`, `1/6`), `--top 5` of 8 tests, and the JSON statuses `null`, `"PASS"`, `"FAIL"` of "Same views in JSON". Verify that the tests pass.
- [x] 3.3 Describe `--show` and `--show tests` in the guide and in "`compare` JSON". Change the CI recipe "Flakiness signal" to `compare --show tests` with `jq` on `flaky`, and run it as written. Regenerate `reference/cli.md` and check the page in the dev server.

## 4. `--show failures`

- [x] 4.1 Add the message key (D6) and `--show failures`, per group: one shown message cut to `--message-chars`, the number of tests, the count per run, the first run, and the sort by the number of tests. Cover "The same failure over tests and runs" (numbers differ, first run, message length) in function and CLI tests. Verify that the tests pass.
- [x] 4.2 Describe `--show failures` and what counts as the same message, with its limits, in the guide and in "`compare` JSON". Verify the commands as written and the page in the dev server.

## 5. `--show elapsed`

- [x] 5.1 Add `--show elapsed` for suites and tests (D7), per group: median of the runs before the last one that had the item, last time, growth in seconds and percent, only growth above zero, items in at least two runs. Cover "Growth of elapsed times" in function tests with the values of its scenarios (10, 11, 30, 12, then 20 gives 11.5 and 8.5; faster is not listed), plus a CLI test with a suite whose test sleeps longer in the last run. Verify that the tests pass.
- [x] 5.2 Describe `--show elapsed` in the guide and in "`compare` JSON", and point the CI recipe "Slow-test report" to it. Verify the commands as written and the page in the dev server.

## 6. `--show messages`

- [x] 6.1 Add `--show messages`, per group: the execution messages of `<errors>` as `log.html` shows them, taken before the filters, with the count per level and run. Per message, it shows the count per run, the first and the last run, and new and gone. Cover "Messages of the runs": a warning logged with `Log … WARN` only in the last run, and an import error of a missing library in runs 1 and 2 of three. Verify that the tests pass.
- [x] 6.2 Describe `--show messages` in the guide and in "`compare` JSON". Verify the commands as written and the page in the dev server.

## 7. `--show environment`

- [x] 7.1 Add the version-bound generator helper (D8) and `--show environment`, with one row per run and one column per metadata name of the top suites, cut to `--message-chars`. Cover "Environment of the runs":
  - versions and metadata, where the test reads the expected versions from the running Python and Robot Framework;
  - a file written by `rebot`;
  - a generator it can't split.

  Verify with `hatch run test.rf50:test`, `test.rf70:test` and `test.rf71:test` on `tests/robotcode/runner/cli/results/test_compare.py` that the helper finds the generator in an `output.xml` before 7.2, and that an `output.json` written by rebot of 7.0 or 7.1, which records none, leaves the environment empty. Verify that the tests pass on `test.rf72` and `test.rf75` too, including an `output.json` written by robot.
- [x] 7.2 Describe `--show environment` in the guide: what a result file records, `--metadata` for anything else, the `rebot` version and the missing metadata of merged files. Add it to "`compare` JSON". Verify the commands as written and the page in the dev server.

## 8. Groups of runs

- [x] 8.1 Add `--group-by-metadata NAME` (D4): the stable partition, a group for runs without the metadata, the group column and a sum row per group in the overview, `--last N` per group, and a space between groups in the status of a test. Cover "Groups of runs" with four runs of two platforms, set by `--metadata Platform:…`. Verify that the tests pass.
- [x] 8.2 Make every value that depends on the order of the runs use the groups, with ` · ` between groups in the text and one `perGroup` entry per group in JSON:
  - the failed count, flaky tests and failing since;
  - the first run of a failure;
  - the growth;
  - new and gone.

  Cover "Values that depend on the order are computed per group": fails only on one platform (`PPPPP FFPFF`, `0/5 · 4/5`), the last runs per group, and one JSON check of `perGroup`. Verify that the tests pass.
- [x] 8.3 Describe groups in the guide and in "`compare` JSON". Regenerate `reference/cli.md`, and verify the commands as written and the page in the dev server.

## 9. Agent skill

- [x] 9.1 In `robotframework-agent-plugins`, add a section on `robotcode results compare` to `plugins/robotcode/skills/robotcode/references/results.md`, after `diff`. It says when to use `compare` instead of `diff`, with the views and a few examples. Change "five subcommands" to six and update the contents list. Verify that each command in the section runs as written against result files in a scratch directory.

## 10. Whole change

- [x] 10.1 Run `hatch run lint:all` and `hatch run test:test`, and report failures with their output.
- [x] 10.2 Check the real program in a scratch directory with ten runs of one suite on two platforms (`--metadata Platform:…`), one of them merged by `rebot`, and a flaky, a newly failing and a slower test. Run the overview, every `--by` and `--show` value, names, `--run-order start-time`, `--last` and `--group-by-metadata`, and read the text and JSON output as a user would. Record what each view shows in the report.

## Workflow follow-up

- Commit only on request. Suggested: the command as `feat(runner)` commits, one per task group or one in all; the plan as `docs(openspec)`; the skill as `docs(skill)` in `robotframework-agent-plugins`. After that commit, run `hatch run build:sync-chat-plugin` in robotcode and commit the vendored copy as `chore(chat-plugin)`. Not breaking.
- Archive with `/opsx:archive` after the review, then `openspec validate --specs --strict`.
