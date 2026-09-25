# Proposal: cli-small-fixes

## Why

Small defects in the CLI surfaced as side findings of the Robot Framework 7.5 work. `robotcode results` on Robot Framework older than 7.0 rejects a JSON result file with a message that prints the installed version as `6.1.1.None.None.None`, because it joins every field of the internal version tuple. And the generated CLI reference `docs/03_reference/cli.md` documents commands that are hidden from `--help`: `debug-launch`, hidden as an internal command since 2023, has been in it since the reference was first generated, and regenerating the reference now also adds `analyze dump-model`, a developer tool whose JSON format has no stability guarantee. Regenerating it also reorders `--by-longname`, `--exclude-by-longname` and `--version` of `robot`, `robot-debug` and the `discover` commands, because these options are collected in sets whose iteration order depends on the environment; `--help` shows the same varying order.

## What Changes

- The error for a JSON result file on Robot Framework older than 7.0 no longer names the installed version. It says that Robot Framework 7.0+ is required and names the file.
- The hint for a result file with test metadata on Robot Framework older than 7.5 no longer names the installed version either (`… requires Robot Framework 7.5+.` instead of `… 7.5+, got 7.4.2.`).
- `scripts/create_cmdline_doc.py` leaves hidden commands out of the command lists and sections of `docs/03_reference/cli.md`, as `--help` does and as it already does for hidden options. The regenerated reference no longer contains `debug-launch` and does not gain `analyze dump-model`.
- The options shared by `robot`, `robot-debug` and the `discover` commands appear in a fixed order in `--help` and in the reference: `--by-longname`, `--exclude-by-longname`, `--version`.

## Capabilities

### New Capabilities

- `result-file-version-errors`: The errors of `robotcode results` when the installed Robot Framework cannot read a result file.
- `cli-reference-generation`: Which commands and options the generated CLI reference `docs/03_reference/cli.md` documents, and in which order.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/runner/src/robotcode/runner/cli/results/results.py`: `_load_execution_result` message, `_test_metadata_hint`.
- `docs/03_reference/analyzing-results.md`: example of the test metadata hint.
- `scripts/create_cmdline_doc.py`: skip hidden commands.
- `packages/runner/src/robotcode/runner/cli/robot.py`: `ROBOT_VERSION_OPTIONS`, `ROBOT_SIMPLE_OPTIONS` and `ROBOT_OPTIONS` become lists.
- `packages/repl/src/robotcode/repl/cli.py`: `robot-debug` leaves the version option out of `ROBOT_OPTIONS` without set difference.
- `docs/03_reference/cli.md`: regenerated, `debug-launch` removed, shared options reordered.
- Tests: `tests/robotcode/runner/cli/results/test_errors.py` (RF < 7.0 and RF < 7.5 only).
