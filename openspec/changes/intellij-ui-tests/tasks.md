# Tasks

## 1. Setup

- [ ] 1.1 Add the `integrationTest` source set, the dependencies (`testFramework(TestFrameworkType.Starter, configurationName = "integrationTestImplementation")`, JUnit Jupiter, Kodein DI, Kotlin coroutines at their newest versions in `gradle/libs.versions.toml`) and the task `integrationTest` registered with `intellijPlatformTesting.testIdeUi` (JUnit Platform, the source set's classes and classpath). Verify that `./gradlew integrationTest` compiles and runs an empty test class, and that `./gradlew test` still runs only the unit tests.
- [ ] 1.2 Write the first test, which only starts PyCharm in the build's version with the plugin from `path.to.build.plugin` and closes it again. Record where Starter takes the IDE from, where it writes its output, and which dialogs appear on the first start. Verify that the test passes locally under `xvfb-run -a` and that the developer's own IDE configuration and `~/PyCharmMiscProject` stay unchanged (checksums before and after).

## 2. Test project and IDE configuration

- [ ] 2.1 Add the test project under `src/integrationTest/resources/project/` (a suite with a passing and a failing test, a call of an unknown keyword, `robot.toml`) and a helper that copies it into the test context's project directory. Verify that the copied project opens in the test IDE.
- [ ] 2.2 Seed the test context before the start: Python SDK from `ROBOTCODE_IT_PYTHON`, the project as trusted, no update check, the classic welcome screen. Use Starter's configuration API where it covers a setting, a file in the context's config directory otherwise. Skip the tests with a message naming the variable when it is unset. Verify that the project opens without a dialog and with the SDK set, and that the tests are skipped without the variable.

## 3. Smoke tests

- [ ] 3.1 Add `@Remote` stubs for the classes the tests query: LSP4IJ's `LanguageServerManager`, the plugin's test manager and the classes they return. Name the plugin id in each stub. Verify by a test that reads the language server status.
- [ ] 3.2 Add the four smoke tests of the spec:
  - start without RobotCode errors in `idea.log`;
  - a diagnostic for the unknown keyword;
  - run markers on the tests;
  - a test run from a run configuration that shows as passed in the results tree.

  They wait on conditions with timeouts. Verify that all four pass locally three times in a row, and that each fails when its condition is broken on purpose (for example a wrong expected marker count), with a screenshot in Starter's output.

## 4. CI

- [ ] 4.1 Extend the job `test-jetbrains` on `ubuntu-latest`: Python 3.10 with `pip install robotframework`, `ROBOTCODE_IT_PYTHON` pointing to it, and `./gradlew --console=plain integrationTest` under `xvfb-run -a` after `gradle test`. Upload Starter's output folder when the step fails, and add the integration test results to the uploaded JUnit results. If Starter downloads the IDE, cache its download folder. Verify that the workflow still parses as YAML.
- [ ] 4.2 After the maintainer pushes: the integration tests pass in CI and appear in the published test results. Note the duration of the first run and of a second run with the cache.

## 5. Remote Robot

- [ ] 5.1 Remove `runIdeForUiTests` and its `robotServerPlugin(...)` from `build.gradle.kts`, and update the harness section of `playground/intellij-vscode-parity.md` to point to the integration tests. Verify that `./gradlew buildPlugin verifyPlugin test integrationTest` passes.
