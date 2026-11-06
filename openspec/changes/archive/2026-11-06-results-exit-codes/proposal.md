# Proposal

## Why

`robotcode results diff` exits with 0 even when it reports new failures, so it can't gate a CI step or an agent loop without parsing its output ([#685](https://github.com/robotcodedev/robotcode/issues/685)). Its errors exit with 1 or 2, so an exit code that tells what the diff found also needs the errors to be out of its way.

## What Changes

- `results diff` gets an opt-in `--exit-code`. With it, the exit code is 0 for an empty diff and otherwise a bitwise combination of the categories that have entries, like the exit code of `analyze code`: 1 new failures, 2 new passes, 4 status changes, 8 added, 16 removed.
- `--only` decides what is shown and what counts. `--exit-code-mask` keeps categories in the output but takes them out of the exit code, and turns on `--exit-code` by itself.
- Without `--exit-code` and `--exit-code-mask`, `results diff` exits with 0 as today.
- Every `results` command (`diff`, `log`, `show`, `stats`, `summary`) exits with 128 for an error that stops it: a usage error, a result file that is missing or can't be read, an invalid `robot.toml`, and an unexpected error. Today these exit with 1 or 2. Not breaking, decided by the user: the codes stay non-zero, and few scripts depend on these commands yet.
- `results diff --help` and the guide say what the exit codes mean. The guide's section on why `diff` always exits with 0 and its `jq` recipe for a regression gate are replaced.

## Capabilities

### New Capabilities

- `results-diff`: the comparison of two result files by `robotcode results diff`, starting with its exit code.

### Modified Capabilities

- `cli-exit-codes`: the `results` commands leave the group of commands that keep their exit codes, and exit with 128 for their errors.

## Impact

- `src/robotcode/cli/__init__.py`: the root command group maps the exit code of an error of a `results` command, as it does for the commands that exit with 252.
- `packages/plugin` (`click_helper/exit_codes.py`): a marker for commands whose errors exit with 128, next to `robot_exit_codes`.
- `packages/runner` (`cli/results/results.py`): the `results` group carries the marker; `diff` gets `--exit-code` and `--exit-code-mask` and its help text.
- Tests under `tests/robotcode/runner/cli/results/` and `tests/robotcode/cli/test_exit_codes.py`; one test that expects 2 today (`test_search.py`).
- Docs: `guides/cli/analyzing-results.md`; `reference/cli.md` is regenerated.
- The agent skill doesn't change: it says nothing about exit codes, so nothing in it becomes wrong.
