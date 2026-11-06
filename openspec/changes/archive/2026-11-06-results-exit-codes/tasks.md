# Tasks

## 1. 128 for errors of the `results` commands

- [x] 1.1 Add `errors_exit_with_128` and `has_errors_exit_with_128` to `packages/plugin/src/robotcode/plugin/click_helper/exit_codes.py` and mark the `results` group with it (D1). In `RobotCodeGroup.invoke`, give every Click error of a marked command the code 128, written as `[ ERROR ] <message>` as before. In `tests/robotcode/cli/test_exit_codes.py`, which runs `robotcode` in a subprocess, cover the scenarios of "Errors of the results commands exit with 128": missing result file, invalid `--only` value, a file that is no result file, invalid `robot.toml`, unknown command of `results`, `diff --exit-code` with a missing file, and `robotcode --nonsense results summary` exiting with 2. Keep `test_other_commands_keep_their_exit_code` for `analyze` and `discover`. Verify that the new tests pass with the change and fail without it.
- [x] 1.2 Catch `Exception` for a marked command in `RobotCodeGroup.invoke` after re-raising `click.exceptions.Exit` and `click.Abort`, write the traceback with `traceback.print_exc()` and exit with 128 (D2). Cover it with a test that makes a `results` command raise an unexpected exception, patched where `results.py` uses it, and checks the traceback on standard error and the code 128. Verify that it passes with the change and fails without it.
- [x] 1.3 Change `test_search_invalid_regex_fails_before_the_result_file_is_read` in `tests/robotcode/runner/cli/results/test_search.py` from 2 to 128, and check the other tests under `tests/robotcode/runner/cli/results/` that expect an error. Verify with `hatch run test.rf75:test tests/robotcode/runner/cli/results tests/robotcode/cli`.
- [x] 1.4 In `docs/src/content/docs/guides/cli/analyzing-results.md`, add the sentence that every `results` command exits with 128 for an error that stops it, where the guide describes the commands' errors or in "Tips for terminal use". Verify that the page renders in the docs dev server.

## 2. Exit code of `results diff`

- [x] 2.1 Add the `DiffExitCode` flag type and the options `--exit-code` and `--exit-code-mask` to `diff` (D3, D4): the mask callback takes the names of `--only` and `all`, repeated or comma-separated, and raises `click.BadParameter` for an unknown name. Compute the code from the rendered `DiffResult` minus the mask, and end with `app.exit(code)` when `--exit-code` or a mask was given. In `tests/robotcode/runner/cli/results/test_diff.py`, cover every scenario of `results-diff`: one small pair of suites per category in `tmp_path`, run with `robot --name` so the tests share names, for 0, 1, 2, 4, 8, 16 and 17; `--only`, a filter, the mask with several values, the mask without `--exit-code`, `all`, an unknown mask name, JSON output, and 0 without the option. Verify that the tests pass with the change and fail without it.
- [x] 2.2 Add the "Exit codes" block to the docstring of `diff` (D6) and an example with `--only new-failures --exit-code`. Cover "The help names the exit codes" with a test of `results diff --help`. Regenerate `docs/src/content/docs/reference/cli.md` with `hatch run create-cmd-line-docs` and verify that its diff only touches `results diff` and the errors of `results`.
- [x] 2.3 In `guides/cli/analyzing-results.md`, replace "Why `diff` always exits 0" with "Exit codes" (the table, `--only`, the mask, 128), point the tip "`diff` doesn't fail the build" to it, and change the CI recipe "Fail only on new failures vs a checked-in baseline" to `--only new-failures --exit-code`. Verify in the docs dev server that the page renders and the anchor `#ci-recipes` and the new section's anchor work, and that every command in the new text runs as written.

## 3. Whole change

- [x] 3.1 Run `hatch run lint:all` and `hatch run test:test`, and report failures with their output.
- [x] 3.2 Check the real program before and after, with the reproduction of #685 in a scratch directory: `results diff` without and with `--exit-code`, `--only new-failures --exit-code`, `--exit-code-mask added`, a missing file, a broken XML file and `robotcode results nope`. Record the exit codes before and after in the report.

## Workflow follow-up

- Commit only on request. Suggested: group 1 and group 2 as `feat(runner)` commits, the second with `Fixes #685`; the plan and the tasks as `docs(openspec)`. Not marked breaking, decided by the user.
- Archive with `/opsx:archive` after the review, then `openspec validate --specs --strict`.
