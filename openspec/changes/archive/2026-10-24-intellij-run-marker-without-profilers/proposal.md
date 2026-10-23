# Proposal

## Why

In PyCharm Professional, the menu of a run marker offers PyCharm's **Profile** and **Concurrency Diagram** for Robot Framework tests (finding J5 of the review of the PyCharm guide). Neither works for Robot Framework runs:

- **Profile** ends with "Robot Framework runs cannot be profiled." It is easy to mix up with **Run with Profile...**, which runs with a profile of `robot.toml`.
- **Concurrency Diagram** starts the test under PyCharm's Python debugger, and no diagram appears (checked in the harness on 2026-10-24).

The user decided on 2026-10-24 that both leave the run marker, and that Concurrency Diagram ends with a message like Profile wherever else PyCharm offers it.

## What Changes

- The menu of a run marker offers **Run**, **Debug**, **Run with Profile...**, **Debug with Profile...** and **Modify Run Configuration…**, without **Profile** and **Concurrency Diagram**.
- Elsewhere, for example under **More Run/Debug** in the editor's context menu or in the run widget, **Concurrency Diagram** for a Robot Framework run configuration ends with a message, without starting a process, as **Profile** does today.
- The PyCharm guide no longer mentions Profile in the run marker's menu, and its picture of the menu is taken again.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `intellij-run-configurations`: the menu of a run marker without PyCharm's profilers, and Concurrency Diagram ending with a message like Profile.

## Impact

- `intellij-client`:
  - `RobotCodeRunLineMarkerContributor.kt` keeps only the executor actions of Run and Debug.
  - `RobotCodeProgramRunner.kt`: `RobotCodeProfileRunner` also takes the executor of Concurrency Diagram.
  - `RobotCode.properties` gets the message for Concurrency Diagram.
  - Platform tests for both.
- `docs/src/content/docs/guides/pycharm/running-tests.mdx`: the sentence on the run marker's menu, and the picture `running-gutter-menu` in light and dark with its alt text.
- No change to the language server, VS Code, the profile actions or other run configurations.
