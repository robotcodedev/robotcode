# Proposal

## Why

The CI builds the IntelliJ plugin but never tests it. The package job runs `gradle buildPlugin` (`scripts/package.py`). The plugin's Kotlin tests (`intellij-client/src/test/kotlin/`, 15 JUnit tests, green locally in about 10 seconds) never run in CI. The plugin verifier step in the `code-quality` job is commented out; it was switched off while the plugin was broken. So a change can break the plugin's tests, or its compatibility with the IDE versions it claims to support, and still be packaged and published.

The 28 planned `intellij-*` changes each add unit tests. They only protect the plugin if the CI runs them on every push and pull request.

## What Changes

- The `code-quality` job runs the plugin verifier again: `gradle verifyPlugin` in `intellij-client/`, against the IDE versions the build configures. The verifier's report goes into the job summary and is uploaded as an artifact. Problems at the failure levels the build configures fail the job: an invalid plugin, compatibility problems, missing dependencies.
- A new job, `test-jetbrains`, runs `gradle test` in `intellij-client/` on Linux, Windows and macOS. The JUnit results are uploaded and appear in the published test results next to the Python tests.
- The package job waits for `test-jetbrains`, as it waits for the Python tests, so a plugin with failing tests is not packaged.
- The job is named for the JetBrains plugin so that a VS Code test job can be added next to it later. That job is not part of this change.

Not part of this change: UI and integration tests in a running IDE; VS Code extension tests; changes to the plugin itself, unless the restored verifier reports a problem that blocks the job.

## Capabilities

### New Capabilities

- `continuous-integration`: what the CI checks on every push and pull request before it packages and publishes RobotCode. This change adds the checks of the JetBrains plugin.

### Modified Capabilities

_None._

## Impact

- `.github/workflows/build-test-package-publish.yml`: the verifier step in `code-quality`, the new job `test-jetbrains`, the `needs` of `package` and `publish-test-results`, and the result pattern of `publish-test-results`.
- `intellij-client/`: no change expected; the verifier's first CI run decides.
- CI time: one job per operating system with a Gradle build and the IDE download for the tests, and the verifier's IDE downloads in `code-quality`. Caching keeps both small after the first run.
