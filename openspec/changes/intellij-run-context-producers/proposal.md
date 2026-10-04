# Proposal

## Why

In PyCharm and IntelliJ IDEA, Robot Framework runs start from context only in a few places. With the caret inside the body of a test, neither the editor's context menu nor Ctrl+Shift+F10 offers a Robot Framework run; they work only with the caret on the first character of the test's name. Selecting two suite files in the Project view and choosing Run runs only one of them. Suite and folder nodes in the results tree can be neither run again nor opened in the editor. A suite file that discovery does not know cannot be run at all: a file outside the paths of `robot.toml`, a file opened before discovery finished, or any file of a project whose discovery failed. For folders, PyCharm's own pytest configuration wins over the Robot Framework configuration. While the IDE indexes, run markers and context runs disappear.

VS Code runs any selection of its Test Explorer, and "Run Current File" runs any suite file by its path.

## What Changes

- Run and Debug from the editor's context menu, Ctrl+Shift+F10 and Ctrl+Shift+F9 run the test or task whose body holds the caret. Anywhere else in a suite file, such as in the settings, variables or keywords, they run the file's suite.
- Several selected suite files, folders or results-tree nodes run together in one configuration. Duplicates and items whose parent is also selected are left out.
- Suite and folder nodes in the results tree offer Run, Debug and Jump to Source.
- Suite files and folders that discovery does not know run by their path, in a configuration named "Robot <name>".
- For folders that discovery reports as Robot Framework suites, the Robot Framework configuration ranks before pytest's. The pytest configuration stays in the menu.
- Configurations created from context take every value except the target and the name from the configuration template. So Before launch tasks, "Allow multiple instances", the interpreter, environment and working directory set in the template apply to gutter and context runs. A template stored as a project file shares these defaults with the team, the counterpart of a launch configuration with purpose `default` in VS Code.
- Configuration names follow the target. A configuration that runs files or folders follows when they are renamed or moved.
- Run markers, context runs and the configuration editor stay available while the IDE indexes.

Behaviour that users notice, for the release notes (not breaking): Ctrl+Shift+F10 inside a test runs that test; several selected files run together; results-tree suites can be rerun; values of the configuration template apply to gutter runs; Robot Framework folders run as Robot Framework suites by default instead of as pytest tests.

Not part of this change: rerunning only the failed tests; running with a chosen `robot.toml` profile; a test explorer tool window; run markers for tasks.

## Capabilities

### New Capabilities

- `intellij-run-configurations`: creating and reusing Robot Framework run configurations from the editor, the Project view and the results tree, with names and template values.
- `intellij-test-discovery`: run markers stay available while the IDE indexes.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeRunConfigurationProducer.kt`: caret mapping, multi-selection, path fallback, names, ranking against pytest, dumb awareness.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotSMTestLocator.kt`: locations for file and folder suite nodes.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeRunConfiguration.kt`: generated names and following renamed or moved paths; `RobotCodeConfigurationType.kt`, `RobotCodeRunConfigurationFactory.kt` and `RobotCodeRunLineMarkerContributor.kt`: availability while indexing.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/testing/RobotCodeTestManager.kt`: lookups of the enclosing test and of items for files and folders.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the debugger, discovery or `robot.toml`.
