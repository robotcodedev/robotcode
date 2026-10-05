# Proposal

## Why

What the IntelliJ plugin does inside a running IDE is tested only by hand today. Starting the language server, discovery and run markers, runs and their results tree, the debugger: none of it has an automated test. The checks done so far ran in a headless PyCharm driven by ad-hoc scripts through JetBrains' Remote Robot server. Those scripts are not in the repository, and the Gradle task `runIdeForUiTests` that starts the IDE for them is all that is left of that setup. Remote Robot is deprecated; its README says new UI tests should use Starter and Driver.

The 28 planned `intellij-*` changes each end with a list of checks in a running PyCharm. Committed integration tests that run in CI turn those checks from a one-time manual step into a guard against regressions.

## What Changes

- An integration test setup for the plugin with JetBrains' IDE Starter and Driver: its own source set (`src/integrationTest/`), JUnit 5, and a Gradle task that builds the plugin, starts PyCharm in its own process with the plugin installed, and drives it.
- A small test project with Robot Framework files, and an interpreter with Robot Framework for it, so that the language server, discovery and runs work in the test IDE.
- A first set of smoke tests:
  - the IDE starts with the plugin, opens the test project, and logs no errors from RobotCode;
  - the language server starts and reports a diagnostic for an unknown keyword;
  - discovery puts run markers on the tests;
  - a test runs from a run configuration and shows as passed in the results tree.
- The JetBrains test job runs these tests on Linux in a virtual display, after the unit tests, and uploads the IDE logs and screenshots of failed tests.
- The Remote Robot task `runIdeForUiTests` and its robot-server plugin are removed once the new tests run.

Later changes add their checks as integration tests on this setup; this change adds none of theirs.

Not part of this change: integration tests on Windows and macOS; tests for the features of the planned changes; tests of the VS Code extension.

## Capabilities

### New Capabilities

- `continuous-integration`: adds the integration tests of the JetBrains plugin to the checks the CI runs. The capability is introduced by `intellij-ci-tests`; if this change is archived first, it creates it.

### Modified Capabilities

_None._

## Impact

- `intellij-client/build.gradle.kts`: the `integrationTest` source set, its dependencies (Starter and Driver through the IntelliJ Platform Gradle Plugin, JUnit 5, Kodein DI, Kotlin coroutines) and task; removal of `runIdeForUiTests`.
- `intellij-client/gradle/libs.versions.toml`: the new test dependencies.
- New `intellij-client/src/integrationTest/` with the tests, `@Remote` stubs for the plugin classes the tests query, and the test project.
- `.github/workflows/build-test-package-publish.yml`: Python with Robot Framework, a virtual display and the integration test step in the JetBrains test job on Linux; upload of logs and screenshots.
- No change to the plugin's production code.
