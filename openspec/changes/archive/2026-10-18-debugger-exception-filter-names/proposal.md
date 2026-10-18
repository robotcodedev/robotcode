# Proposal

## Why

The debugger names two of its four exception filters in the singular, "Failed Test" and "Failed Suite", next to "Failed Keywords" and "Uncaught Failed Keywords". VS Code shows these names, while the IntelliJ plugin calls the same filters "Failed Tests" and "Failed Suites" (finding T4 of the review of the PyCharm guide). Each filter stands for a kind of failure that occurs many times in a run and stops at every one: every failed keyword, every failed test, every failed suite, and one failing test fails its suite and every enclosing suite. The names are therefore plural, as the descriptions "Breaks on failed keywords" and "Breaks on failed tests" already say.

## What Changes

- The debugger offers the exception filters "Failed Tests" and "Failed Suites" instead of "Failed Test" and "Failed Suite", and describes the second as "Breaks on failed suites" instead of "Breaks on failed suite". The filter ids `failed_test` and `failed_suite`, their defaults and what they stop at stay.
- VS Code's Breakpoints view shows the same four names as the IntelliJ plugin, and the VS Code guide uses them.
- VS Code recognizes a stored exception filter by its id, name and description. After the update, "Failed Tests" and "Failed Suites" therefore show once with their default, off; who had switched "Failed Test" or "Failed Suite" on switches the filter on again. Not breaking.

## Capabilities

### New Capabilities

- `debugger-exception-filters`: the exception filters the debugger offers a debug client, with their names and descriptions.

### Modified Capabilities

None. The spec `intellij-debugging` names the IntelliJ plugin's exception breakpoints "Failed Tests" and "Failed Suites" already.

## Impact

- `packages/debugger/src/robotcode/debugger/default_capabilities.py`: two names and one description.
- `tests/robotcode/debugger/`: a test of the names and descriptions the debugger advertises.
- `docs/src/content/docs/guides/vscode/running-and-debugging.mdx`: the two names in the section "Stopping at failures".
- `openspec/changes/debugger-exception-info`: its two scenarios with "Failed Test" name the filter by its id `failed_test`, so that its spec does not depend on the name.
- No change to the IntelliJ plugin, its tests, the PyCharm guide or the spec `intellij-debugging`.
