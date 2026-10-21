# Proposal

## Why

A project in IntelliJ IDEA with the Python plugin, or in PyCharm with attached projects, can have several modules, each with its own Python interpreter. RobotCode uses the interpreter of the first module that has one, for the language server, test discovery and the profile list, and new Robot Framework run configurations start with the first module as well. When the Robot Framework files live in another module, RobotCode reports that Robot Framework is missing, although the interpreter of the module with the tests has it (#489).

The content and source roots that the switches of the "Robot" page put on the Python path (#430) come from that first module too. A project can have a module without any roots before the one that holds the project, with the same interpreter: PyCharm's pyproject.toml project model left such a module in a test project on 2026-10-21. The analysis, discovery and runs then get none of the roots, and a resource in a folder marked as Sources is not found.

Robot Framework run configurations get PyCharm's check that an interpreter is set and RobotCode's warning about unknown profiles. A configuration whose interpreter lacks Robot Framework, is too old or is remote, whose "Files and folders" target names a path that no longer exists, or whose stored tests were renamed, shows its problem only after Run was pressed, or runs no test at all. When a run starts, the plugin checks the project's interpreter, not the configuration's, which can differ.

## What Changes

- RobotCode keeps one interpreter per project and chooses it like this:
  - a project with one module that has an interpreter uses it, as today;
  - in a project with several such modules, RobotCode takes the module the user has chosen;
  - without a choice, it looks for the modules that are Robot Framework projects, as the VS Code extension does per workspace folder: a `robot.toml` or `.robot.toml`, a `pyproject.toml` or `requirements.txt` that depends on Robot Framework or RobotCode, or Robot Framework files;
  - exactly one such module becomes the choice; with none, the first module with an interpreter stays the rule; with several, a notification and the banner on Robot files ask the user to choose, and RobotCode starts nothing until then.
- The choice is stored for the current user. The "General" settings page shows it and lets the user change it while the project has several modules with an interpreter. idea.log records the chosen interpreter and why.
- The language server, discovery, the profile list and new Robot Framework run configurations use this interpreter, and the content and source roots of the "Robot" page's switches come from the chosen module and the modules it depends on.
- While a Robot Framework run configuration is edited, and before it runs, the plugin reports, in addition to PyCharm's own interpreter check:
  - an error when RobotCode's check found the configuration's interpreter unusable, with the reason and a fix that opens the Python Interpreter settings;
  - an error for a remote interpreter, which runs do not support yet;
  - a warning when the interpreter could not be checked;
  - an error for each path of a "Files and folders" target that does not exist;
  - a warning that names the stored tests and suites that the current discovery no longer contains.
- The validation uses results that already exist and never makes the IDE wait for a Python process.
- The start of a run checks the configuration's interpreter instead of the project's.

Behaviour that users notice, for the release notes (not breaking): in projects with several modules, RobotCode now uses the module that holds the Robot Framework project, and asks when several modules do; the roots of that module reach the Python path.

Not part of this change: one language server per module with its own interpreter, which LSP4IJ offers only as one instance per server definition and which waits for a scope API in LSP4IJ (lsp4ij#1701); choosing the interpreter of a single run configuration and activating its environment, which PyCharm's run configuration options already offer; support for remote interpreters; warnings for a target without paths or items, which the editor already shows.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-python-environment`: which interpreter RobotCode uses in a project when it has several modules, how the user chooses one, and what the plugin does until then.
- `intellij-run-configurations`: the checks a Robot Framework run configuration gets before it runs; remote interpreters are reported in the editor as well.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/`:
  - `RobotCodeHelpers.kt`: `robotPythonModule` and `robotPythonSdk` return the chosen module and its interpreter, so `RobotCodeEnvironment.projectInterpreter`, the defaults of run configurations and `RobotCodeRootPythonPath` follow the choice;
  - `RobotCodeEnvironment.kt`: the choice and its detection as part of the environment state, resolved again on the workspace model changes it already watches; `ensureUsableForRun` takes the configuration's interpreter;
  - `lsp/RobotCodeLanguageServerFactory.kt` (`isEnabled`) and the test discovery: nothing starts while a choice is missing;
  - `editor/EditorNotificationProvider.kt` and a notification: the request to choose a module;
  - `configuration/RobotCodePersonalConfiguration.kt`: a field for the chosen module; `configuration/RobotCodeGeneralConfigurable.kt`: a row for it;
  - `execution/RobotCodeRunConfiguration.kt`: `checkConfiguration()` and `getState`.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the texts of the notification, the banner, the settings row and the validation.
- New unit and platform tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the VS Code extension or `robot.toml`.
