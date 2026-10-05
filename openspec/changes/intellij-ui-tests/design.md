# Design

## Context

See proposal.md for the motivation.

**Current state:**
- **Remote Robot:** `intellij-client/build.gradle.kts` registers `runIdeForUiTests`, a `runIde` variant with JetBrains' robot-server plugin (Remote Robot) on port 8082. The checks of the parity analysis and the GitHub issue triage in October 2026 drove that IDE through Rhino JavaScript sent to the server, from scripts in a temporary folder. Nothing of that is in the repository.
- **Unit tests:** JUnit 4 with `TestFrameworkType.Platform` in `src/test/kotlin/`, run by `gradle test`. `intellij-ci-tests` puts them into the CI job `test-jetbrains`.
- **Build:** IntelliJ Platform Gradle Plugin 2.19.0 builds against PyCharm 2026.1 (`platformVersion`).
- **Remote Robot's status:** its README calls the library deprecated: "New UI tests should use Starter and Driver."

**Starter and Driver** (IntelliJ Platform SDK docs, "Integration Tests"):
- **Starter** configures and starts an IDE in its own process, with a project and plugins, and collects its output.
- **Driver** talks to that IDE over JMX/RMI. It can call the IDE's and the plugin's API through `@Remote` interfaces that name the class and the plugin id, and it can find and use UI components.
- **Setup:** an `integrationTest` source set; `testFramework(TestFrameworkType.Starter, configurationName = "integrationTestImplementation")`; JUnit 5 (Starter supports only JUnit 5), Kodein DI and Kotlin coroutines; a task registered with `intellijPlatformTesting.testIdeUi`. That task depends on `prepareSandbox` and passes the built plugin as the system property `path.to.build.plugin`.
- **Status:** the docs mark Driver and its UI components as experimental.

**Lessons from the Remote Robot harness** (parity notes, section 12):
- the non-modal welcome screen opened a real user project;
- settings dialogs enable Apply only after real input;
- Ctrl+Space opened no completion popup under Xvfb, while typing did;
- the language server needs a Python interpreter with Robot Framework, set as the project SDK.

## Goals / Non-Goals

**Goals:**

- A committed, repeatable way to test the plugin in a running PyCharm, locally and in CI.
- A few smoke tests that guard the plugin's main path and show the patterns later tests copy: opening a project, waiting for the language server, reading markers, running a configuration.

**Non-Goals:**

- Tests for the features of the planned changes; each change adds its own.
- Windows and macOS runs of the integration tests.
- Replacing the unit tests; logic that a unit test can check stays in a unit test.

## Decisions

### Starter and Driver in their own source set

Following the SDK docs:
- `src/integrationTest/kotlin` and `src/integrationTest/resources`;
- dependencies through `testFramework(TestFrameworkType.Starter, …)`, with JUnit Jupiter, Kodein DI and Kotlin coroutines in the version catalog at their newest versions;
- a task `integrationTest` registered with `intellijPlatformTesting.testIdeUi`.

The JUnit 4 unit tests stay as they are. `gradle test` does not run the integration tests, so `test` stays fast. `integrationTest` is not part of `check`, so the existing build is unchanged.

Alternative: keep Remote Robot and commit the scripts. The library is deprecated and offers about twenty plain Swing fixtures. The scripts reached into the IDE through string-built JavaScript that no compiler checks.

### PyCharm as the test IDE, with a seeded configuration

The test context starts PyCharm in the version the build compiles against. Before the start, the test writes into the context's own config directory:
- the Python SDK pointing to the test interpreter;
- the test project as trusted;
- no update check;
- the classic welcome screen.

That is the same seeding the Remote Robot harness used, but written by Kotlin code in the repository. The context's directories live below the build directory, so a test never touches the developer's own IDE configuration or projects.

The first task checks whether Starter's own configuration API covers these settings and uses it where it does.

### The test project and its interpreter

`src/integrationTest/resources/project/` holds a small Robot Framework project:
- a suite with a passing and a failing test;
- a call of an unknown keyword;
- a `robot.toml`.

The test copies it into the context's project directory before each run. The interpreter comes from the environment variable `ROBOTCODE_IT_PYTHON`. Locally that is the hatch environment `test.rf75`. In CI, `actions/setup-python` and `pip install robotframework` provide it. Without the variable, the tests are skipped with a message that names it, not failed.

### What the tests read, and how

The tests prefer the IDE's and the plugin's API through `@Remote` stubs over clicking through the UI:
- the language server status from LSP4IJ's `LanguageServerManager`;
- the diagnostics of the open editor;
- the test items of the plugin's test manager;
- the run markers;
- the run configuration and the results tree of the run.

UI interaction through Driver is used only where the behaviour is the UI itself. Stubs live in one package and stub only the methods the tests use. Each stub names the plugin id `dev.robotcode.robotcode4ij` or `com.redhat.devtools.lsp4ij`, because plugins have separate class loaders.

The four smoke tests are the requirement's list. They wait with timeouts on conditions, never with fixed sleeps.

### CI: Linux only, in the JetBrains job, after the unit tests

On `ubuntu-latest`, the `test-jetbrains` job adds these steps after `gradle test`:
- Python 3.10 and Robot Framework;
- `./gradlew integrationTest` under `xvfb-run -a`.

Windows and macOS keep running the unit tests only. Starter's output folder, with `idea.log` and the screenshots Driver takes on failure, is uploaded when the step fails. The JUnit results go into the published test results next to the unit tests.

### Remote Robot goes

Once the smoke tests pass locally and in CI, `runIdeForUiTests` and `robotServerPlugin(...)` are removed from `build.gradle.kts`. The other `runIde` variants stay.

## Risks / Trade-offs

- [Driver and its UI components are experimental and may change with an IDE update] → The tests read API through stubs where possible and keep UI interaction to a minimum. An IDE update that breaks a test shows up in CI before a release.
- [Starter downloads PyCharm itself instead of using the distribution Gradle already has] → The first task finds out where Starter takes the IDE from and caches it. If it downloads, the CI caches its download folder.
- [Integration tests are slow and can be flaky] → Four tests at first, one IDE start per test class where Starter allows it, waits on conditions, and the logs and screenshots of failures uploaded. A flaky test is fixed or removed, never retried blindly.
- [The free mode of PyCharm 2026.1 may show dialogs on first start] → The seeded configuration switches them off, as the Remote Robot harness did. The first task records which dialogs appear.

## Migration Plan

None for users. For developers, `runIdeForUiTests` goes away; `runIde` stays for manual work. The section on the harness in the parity notes then points to the integration tests.
