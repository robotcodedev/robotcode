# Proposal

## Why

A project in IntelliJ IDEA with the Python plugin can have several modules, each with its own Python interpreter. RobotCode uses the interpreter of the first module that has one, for the language server, test discovery and the profile list, and new Robot Framework run configurations start with the first module as well. When the Robot Framework files live in another module, RobotCode reports that Robot Framework is missing, although the interpreter of the module with the tests has it (#489).

Robot Framework run configurations get only PyCharm's own check that an interpreter is set. A configuration whose interpreter lacks Robot Framework, is too old or is remote, whose "Files and folders" target names a path that no longer exists, or whose stored tests were renamed, shows its problem only after Run was pressed, or runs no test at all.

## What Changes

- RobotCode chooses one interpreter per project, in this order:
  1. the interpreter of the module that holds the Robot Framework project: the module of the project folder when the project folder has a `robot.toml` or `.robot.toml`, otherwise the module that contains the Robot Framework files;
  2. the project's interpreter;
  3. the interpreter of the first module that has one.
- The language server, test discovery and the profile list use this interpreter, and new Robot Framework run configurations start with it instead of the first module. idea.log records which interpreter was chosen and why. The choice is made again when modules or their interpreters change.
- Before a Robot Framework run configuration runs, and while it is edited, the plugin reports, in addition to PyCharm's own interpreter check:
  - an error when RobotCode's check found the configuration's interpreter unusable, with the reason and a fix that opens the Python Interpreter settings;
  - an error for a remote interpreter, which runs do not support yet;
  - a warning when the interpreter could not be checked;
  - an error for each path of a "Files and folders" target that does not exist;
  - a warning that names the stored tests and suites that the current discovery no longer contains.
- The validation uses results that already exist and never makes the IDE wait for a Python process.

The interpreter choice for the module with the Robot Framework files (#489) may land earlier as a plain fix. This change keeps the item.

Behaviour that users notice, for the release notes (not breaking): in projects with several modules, RobotCode can now use another module's interpreter than before, namely the one that holds the Robot Framework project.

Not part of this change: choosing the interpreter of a single run configuration and activating its environment, which PyCharm's run configuration options already offer; support for remote interpreters; one language server per module; warnings for a target without paths or items, which the editor already shows.

## Capabilities

### New Capabilities

- `intellij-python-environment`: which interpreter RobotCode uses in a project.
- `intellij-run-configurations`: the checks a Robot Framework run configuration gets before it runs.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/RobotCodeHelpers.kt` and the environment state service: the interpreter choice replaces `robotPythonSdk`.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/`: `RobotCodeRunConfiguration.checkConfiguration()`, the default module of new configurations and of the template in `RobotCodeRunConfigurationFactory`.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the validation texts.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the VS Code extension or `robot.toml`.
