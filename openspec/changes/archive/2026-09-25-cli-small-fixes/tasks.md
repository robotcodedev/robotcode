# Tasks: cli-small-fixes

## 1. Result file messages

- [x] 1.1 In `_load_execution_result` of `packages/runner/src/robotcode/runner/cli/results/results.py` drop the installed version from the message, keeping the required version and the file; verify with a new test in `tests/robotcode/runner/cli/results/test_errors.py`, skipped on Robot Framework 7.0+, that runs `results show --output <tmp_path>/output.json` and asserts a non-zero exit, `Robot Framework 7.0+` and the file name in the output; run it with `hatch run test.rf61:test -- tests/robotcode/runner/cli/results/test_errors.py -p no:cacheprovider`
- [x] 1.2 Drop `got <version>` from `_test_metadata_hint` in the same file and the now unused `get_robot_version_str` import; update the example in `docs/03_reference/analyzing-results.md`; verify that the hint tests in `tests/robotcode/runner/cli/results/test_errors.py` assert the hint up to its final `7.5+.` and pass on RF 7.4 (`hatch run test.rf74:test -- tests/robotcode/runner/cli/results/test_errors.py -p no:cacheprovider`)

## 2. CLI reference

- [x] 2.1 In `scripts/create_cmdline_doc.py` resolve the subcommands of a group once, leaving out commands that are `None` or hidden, and use that list for the command list, the alias list and the recursion; drop the now redundant `cmd.hidden` check in the alias loop; verify with `hatch run create-cmd-line-docs` (default env with the newest Robot Framework, see CONTRIBUTING.md) that the diff of `docs/03_reference/cli.md` only removes the command list entry and the section of `debug-launch`, and that `dump-model` and `--read-from-stdin` do not appear

- [x] 2.2 Turn `ROBOT_VERSION_OPTIONS`, `ROBOT_SIMPLE_OPTIONS` and `ROBOT_OPTIONS` in `packages/runner/src/robotcode/runner/cli/robot.py` into lists (`--by-longname`, `--exclude-by-longname`, version option, argument) and replace the set difference for `robot-debug` in `packages/repl/src/robotcode/repl/cli.py` with a filter; verify that `hatch run create-cmd-line-docs` gives the same `docs/03_reference/cli.md` with different `PYTHONHASHSEED` values, that its diff only removes `debug-launch` and moves the shared options into that order, and with a new test `tests/robotcode/runner/cli/test_option_order.py` that checks this order in `--help` of `robot`, `robot-debug` and the five `discover` commands (fails without the fix); the `tests/robotcode/runner` and `tests/robotcode/repl` tests pass on the full Robot Framework matrix

## 3. Verification

- [x] 3.1 Run `hatch run lint:all` and `hatch run test:test -- tests/robotcode/runner/cli/results` on the full Robot Framework matrix and confirm both pass; build the docs with `npm run docs:build` and confirm there is no broken link to `#debug-launch`
