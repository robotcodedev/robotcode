# Proposal

## Why

A Robot Framework run configuration in PyCharm and IntelliJ IDEA can choose what it runs and with which interpreter and environment, but not how Robot Framework runs it. VS Code's launch configurations offer `args`, `variables`, `variableFiles`, `robotPythonPath`, `outputDir`, `mode`, `languages`, `dryRun`, `include` and `exclude`; in PyCharm the only way to set any of these is `robot.toml`. IntelliJ has no test explorer with a tag filter either, so running the smoke tests, or a run with a different log level, needs a profile in `robot.toml` or the command line. VS Code also substitutes variables such as `${workspaceFolder}` in these values; PyCharm offers no macros in Robot Framework run configurations.

## What Changes

- A "Robot arguments" field in every Robot Framework run configuration. Its text is split like a command line and passed to Robot Framework, for example `--loglevel DEBUG`.
- Typed Robot Framework options behind "Modify options", each passed as its Robot Framework option:
  - variables as name and value pairs (`-v name:value`);
  - variable files (`-V`);
  - the Robot Framework Python path (`-P`);
  - the output directory (`-d`);
  - the mode: inherit (the default; nothing is passed, so `robot.toml` decides), RPA (`--rpa`) or test automation (`--norpa`);
  - languages (`--language`);
  - dry run (`--dryrun`).
- Include and exclude tags behind "Modify options" (`-i`, `-e`), so a configuration can run tests by tag.
- The options are passed after the options of `robot.toml`: a single value such as the output directory replaces the one from `robot.toml`, and list values such as variable files and tags add to it. A variable set in the configuration overrides the same variable from `robot.toml`.
- Path fields and the robot arguments offer IntelliJ's macros through "Insert Macros", including the files and folders of the target. Macros are expanded at the start of each run.

Behaviour that users notice, for the release notes (not breaking): VS Code's `${workspaceFolder}`, `${file}` and `${input:...}` correspond to the IntelliJ macros `$ProjectFileDir$`, `$FilePath$` and `$Prompt$`. Languages are passed on every Robot Framework version; Robot Framework 5 reports `--language` as an unknown option.

Not part of this change: project-wide defaults for these options and merging them into runs; default paths; profiles; robotcode and debugger options; the interpreter and environment options, which run configurations already have.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-run-configurations`: the Robot Framework options, tags and macros of a Robot Framework run configuration, and the order in which runs pass them.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/`: new properties in the run configuration's options class; a pure function that turns them into Robot Framework arguments; macro expansion in the run state; new fragments in the run configuration editor; macro support on the target's paths.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the texts of the new fragments.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the debugger, discovery or `robot.toml`.
