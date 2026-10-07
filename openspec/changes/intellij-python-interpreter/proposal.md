# Proposal

## Why

A project in IntelliJ IDEA with the Python plugin, or in PyCharm with attached projects, can have several modules, each with its own Python interpreter. RobotCode uses the interpreter of the first module that has one, for the language server, test discovery and the profile list, and new Robot Framework run configurations start with the first module as well. When the Robot Framework files live in another module, RobotCode reports that Robot Framework is missing, although the interpreter of the module with the tests has it (#489).

Robot Framework run configurations get only PyCharm's own check that an interpreter is set. A configuration whose interpreter lacks Robot Framework, is too old or is remote, whose "Files and folders" target names a path that no longer exists, or whose stored tests were renamed, shows its problem only after Run was pressed, or runs no test at all.

## What Changes

- RobotCode keeps one interpreter per project and chooses it like this:
  - a project with one module that has an interpreter uses it, as today;
  - in a project with several such modules, RobotCode takes the module the user has chosen;
  - without a choice, it looks for the modules that are Robot Framework projects, as the VS Code extension does per workspace folder: a `robot.toml` or `.robot.toml`, a `pyproject.toml` or `requirements.txt` that depends on Robot Framework or RobotCode, or Robot Framework files;
  - exactly one such module becomes the choice; with none, the first module with an interpreter stays the rule; with several, a notification and the banner on Robot files ask the user to choose, and RobotCode starts nothing until then.
- The choice is stored for the current user. The "Robot Framework" settings page shows it and lets the user change it while the project has several modules with an interpreter. idea.log records the chosen interpreter and why.
- The language server, discovery, the profile list and new Robot Framework run configurations use this interpreter.
- Before a Robot Framework run configuration runs, and while it is edited, the plugin reports, in addition to PyCharm's own interpreter check:
  - an error when RobotCode's check found the configuration's interpreter unusable, with the reason and a fix that opens the Python Interpreter settings;
  - an error for a remote interpreter, which runs do not support yet;
  - a warning when the interpreter could not be checked;
  - an error for each path of a "Files and folders" target that does not exist;
  - a warning that names the stored tests and suites that the current discovery no longer contains.
- The validation uses results that already exist and never makes the IDE wait for a Python process.

Behaviour that users notice, for the release notes (not breaking): in projects with several modules, RobotCode now uses the module that holds the Robot Framework project, and asks when several modules do.

Not part of this change: one language server per module with its own interpreter, which LSP4IJ offers only as one instance per server definition (lsp4ij#1352) and which waits for workspace folder support in the RobotCode language server; choosing the interpreter of a single run configuration and activating its environment, which PyCharm's run configuration options already offer; support for remote interpreters; warnings for a target without paths or items, which the editor already shows.

## Capabilities

### New Capabilities

- `intellij-python-environment`: which interpreter RobotCode uses in a project.
- `intellij-run-configurations`: the checks a Robot Framework run configuration gets before it runs.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/RobotCodeHelpers.kt` and the environment state service: the interpreter choice and its detection replace `robotPythonSdk`.
- The personal settings component `RobotCodePersonalConfiguration` in `.idea/workspace.xml`: the chosen module.
- The "Robot Framework" settings page: a row for the module.
- A notification and the editor banner: the request to choose a module.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/`: `RobotCodeRunConfiguration.checkConfiguration()`, the default module of new configurations and of the template in `RobotCodeRunConfigurationFactory`.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the texts of the notification, the banner, the settings row and the validation.
- New unit and platform tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the VS Code extension or `robot.toml`.
