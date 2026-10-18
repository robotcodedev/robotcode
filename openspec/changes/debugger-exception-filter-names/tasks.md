# Tasks

## 1. Debugger

- [ ] 1.1 In `packages/debugger/src/robotcode/debugger/default_capabilities.py`, name `failed_test` "Failed Tests" and `failed_suite` "Failed Suites", and describe `failed_suite` as "Breaks on failed suites". Add a test to `tests/robotcode/debugger/test_exception_breakpoints.py` that checks the name and description of each of the four advertised filters. Verify with `hatch run test:test` and `hatch run lint:all`.

## 2. Documentation

- [ ] 2.1 Use "**Failed Tests**" and "**Failed Suites**" in the two sentences of the section "Stopping at failures" in `docs/src/content/docs/guides/vscode/running-and-debugging.mdx`, and mark finding T4 in `playground/pycharm-befunde.md` as resolved by this change. Verify that `npm run docs:build` passes and that no page under `docs/src/content/docs/` names "Failed Test" or "Failed Suite" in the singular any more.

## 3. Verification

- [ ] 3.1 In the isolated harness with the real RobotCode extension: switch "Failed Test" on in VS Code's Breakpoints view with the debugger before the rename (before task 1.1, or with a copy of the committed debugger); with the renamed debugger, the view lists "Failed Keywords", "Uncaught Failed Keywords", switched on, "Failed Tests" and "Failed Suites", "Failed Tests" is off once, as design.md expects, and switched on again it stops the run at the end of a failing test. Record the results in design.md under a Verification section.

## Workflow follow-up

- Archive the change with `/opsx:archive` once it is implemented and committed.
