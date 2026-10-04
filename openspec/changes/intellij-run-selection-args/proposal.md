# Proposal

## Why

In PyCharm and IntelliJ IDEA, running one test or one suite from the gutter or the Project view passes Robot Framework only `-bl <longname>`. Robot Framework then parses every file below the project root before it selects anything. Errors in unrelated files show up in the run, and a single file that Robot Framework cannot read aborts the run with exit code 252 (issue #631). VS Code had the same problem (#624) and fixed it by passing `-I`, `-N` and `-s` as well; PyCharm never got that fix.

VS Code's fix has a gap of its own (#656): when `robot.toml` lists several paths, `-I` leaves the other top-level folders empty, and Robot Framework rejects the run with "Suite 'Folder1' contains no tests or tasks". Passing `--runemptysuite` together with `-I` avoids the error; this was checked on the command line with Robot Framework 7.5. The PyCharm port uses the corrected rule from the start.

## What Changes

- A run of a test, a task, a file suite or a folder suite passes the same selection arguments as VS Code's Test Explorer:
  - `-I` for each involved suite file or folder, so Robot Framework parses only those. This happens only when discovery reports that the project's Robot Framework supports `--parseinclude` (6.1 and newer).
  - `-N` with the name of the top-level suite, `-s` for each selected suite and for the suite of each selected test, and `-bl` for each selected item.
- A run that passes `-I` also passes `--runemptysuite`, so projects whose `robot.toml` lists several paths can run single tests (#656).
- A run of the whole project gets no selection arguments, as before.
- Robot Framework arguments follow a `--` separator; the debugger's own options, such as `--no-debug` and `--tcp`, stay before it.
- The VS Code fix for #656, which adds the same `--runemptysuite` rule to VS Code's test runs, lands before this change or together with it, so that both clients pass the same arguments.

Behaviour that users notice, for the release notes (not breaking): running a single test or suite no longer parses the whole project, so errors in unrelated files no longer appear in or break the run. Projects with several paths in `robot.toml` can run single tests. A run whose selected test no longer exists, for example a rerun after renaming the test, now ends with "0 tests" instead of Robot Framework's "contains no tests" error.

Not part of this change: keeping the selection of a run configuration across IDE restarts, editing it, excluding items, running several selected files at once, default paths other than `.`, and per-configuration options.

## Capabilities

### New Capabilities

- `intellij-run-configurations`: what a Robot Framework run configuration of the IntelliJ plugin runs, and the arguments its runs pass to Robot Framework.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeRunProfileState.kt`: the run command line gets the selection arguments after `--`, and `--tcp` moves before it.
- A new pure selection-argument builder in `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/`, which reads the items the run configuration holds, the current discovery model and its `--parseinclude` support from `testing/RobotCodeTestManager.kt`.
- New unit tests under `intellij-client/src/test/kotlin/`.
- If the VS Code fix for #656 has not landed yet: `vscode-client/extension/debugmanager.ts` (`DebugManager.runTests`).
- No change to the language server, the debugger, discovery or `robot.toml`.
