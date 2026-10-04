# Proposal

## Why

In PyCharm and IntelliJ IDEA, Robot Framework run configurations are not saved. A configuration that a gutter run created, such as "Test First Test Passes", keeps only its name: after the IDE restarts, it runs the whole project. "Store as project file" writes an empty configuration, so nothing can be shared with the team. The configuration editor is a stub: its "Suite", "Environment variables" and "Arguments" fields are bound to nothing, Apply stays disabled, and the values are gone when the dialog is opened again. After an edit moves a test, running it from the gutter again creates a copy named "Test First Test Passes (1)". There is no way to choose the interpreter, the environment or the working directory of a run. Issue #418 tracks this.

Remote interpreters are a goal, starting with WSL. Run configurations therefore become PyCharm Python run configurations, which can run on such targets later and bring PyCharm's own interpreter and environment options with them.

## What Changes

- A run configuration stores what it runs, its target:
  - "Configured paths": the paths of `robot.toml`, or the project folder. This is the default for new configurations.
  - "Files and folders": the given paths, which replace the configured paths.
  - "Tests and suites": the tests, tasks and suites a gutter or context run selected. They are stored by their names below the top-level suite, so a configuration shared as a project file still matches in a checkout with another folder name.
- Saved and temporary configurations keep their target across IDE restarts. "Store as project file" and configuration templates work, with paths stored relative to the project.
- Robot Framework run configurations become PyCharm Python run configurations. Their editor is PyCharm's run configuration editor with "Modify options":
  - a "Robot Framework" section for the target;
  - PyCharm's options for the Python interpreter (the module's interpreter by default), interpreter options, working directory, environment variables and `.env` files, and adding content and source roots to `PYTHONPATH` (off by default);
  - Before launch, "Allow multiple instances" and logs.
  Every field takes effect.
- Runs keep starting the bundled `robotcode` with the debugger connection, the test tree and the console. Run and Debug use RobotCode's runners, not PyCharm's Python runner or debugger. "Run with Coverage" is not offered.
- Runs execute on the local machine. A configuration whose interpreter is remote (WSL, Docker, SSH) is refused with a message that says so.
- Gutter and context runs recognize their configuration by its target, so edits no longer create "(1)" copies.

Behaviour that users notice, for the release notes (not breaking):
- Configurations saved by earlier versions keep their names but have no target, because earlier versions never saved one. They run the configured paths, as they did after every restart, until a target is set.
- A virtualenv or conda interpreter is activated for runs, as PyCharm does for its own Python runs.
- A configuration without a valid Python interpreter is flagged with an error before the run, as PyCharm's Python run configurations are.

Not part of this change: Robot Framework options and arguments per configuration, such as variables, tags or the output directory; profiles per configuration; robotcode and debugger options; opening the report or log; validating the target before a run; running the test at the caret, several selected files at once, or files outside discovery; runs with remote interpreters; attaching to a running debugger; merging project settings into runs.

## Capabilities

### New Capabilities

- `intellij-run-configurations`: what a Robot Framework run configuration of the IntelliJ plugin runs, how it is stored, shared and edited, which interpreter and environment its runs use, and how gutter and context runs reuse it.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/`:
  - `RobotCodeRunConfiguration.kt` on PyCharm's Python run configuration base class, with a new options class returned by `RobotCodeRunConfigurationFactory.kt`;
  - `RobotCodeRunProfileState.kt` on PyCharm's Python command-line state, with the selection arguments resolved from the stored target;
  - `RobotCodeRunConfigurationEditor.kt` replaced by a fragmented editor with a Robot Framework target fragment;
  - `RobotCodeProgramRunner.kt` and `debugging/RobotCodeDebugProgramRunner.kt`, which start the run off the UI thread;
  - `RobotCodeRunConfigurationProducer.kt`, which writes and compares the stored target.
- `intellij-client/src/main/resources/META-INF/plugin.xml`: the order of the two program runners.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the texts of the target fragment.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the debugger, discovery or `robot.toml`.
