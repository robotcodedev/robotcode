# Design

## Context

See proposal.md for the motivation. The current workflow, `.github/workflows/build-test-package-publish.yml`:

- **`test`:** Python tests only, on a matrix of operating system × Python × Robot Framework. It uploads `test-results/**/test-results.xml`.
- **`publish-test-results`:** needs `test`, downloads all artifacts of the run, and publishes `./**/test-results.xml` with `EnricoMi/publish-unit-test-result-action`.
- **`code-quality`:** Ubuntu. It sets up Node, Python, Hatch, Java 21 (JetBrains distribution) and Gradle (`gradle/actions/setup-gradle@v5`), then runs the Python lint and typing checks. The verifier step after them is commented out. It ran `gradle --no-daemon verifyPlugin -Dplugin.verifier.home.dir=~/.pluginVerifier`, appended the Markdown reports to the job summary through an exit trap, and uploaded `intellij-client/build/reports/pluginVerifier`.
- **`package`:** needs `test`; `hatch run build:package` runs `gradle buildPlugin` (`scripts/package.py`). **`publish`:** needs `code-quality` and `package`.

The plugin build (`intellij-client/build.gradle.kts`, IntelliJ Platform Gradle Plugin 2.19.0, Gradle wrapper 9.8.0):

- **Tests:** `testFramework(TestFrameworkType.Platform)`, JUnit 4. The test sandbox copies `package.json`, the syntaxes and `bundled/` from the repository root. The current tests need no Python.
- **Verifier:** `pluginVerification` fails on `INVALID_PLUGIN`, `COMPATIBILITY_PROBLEMS` and `MISSING_DEPENDENCIES`, writes Markdown and plain reports, and checks `ides { recommended() }`.

**Checked locally on 2026-10-04:**
- `./gradlew test --rerun` passes: 15 tests in 5 classes, about 10 seconds.
- `./gradlew verifyPlugin` passes in 58 seconds against PY-261.27258.51, PY-262.10968.92 and PY-263.6259.38, all "Compatible". The reports list two or three deprecated and 15–20 experimental API usages; neither is a configured failure level.
  - The deprecated usages are the status bar widget's `getPresentation` and the run configuration editor's `EnvironmentVariablesComponent()` constructor. Both go away with planned changes.
  - The verifier's IDEs and plugins came from the Gradle cache; `~/.pluginVerifier/ides` stays empty.

## Goals / Non-Goals

**Goals:**

- Run every check the plugin already has on every push and pull request, and keep a broken plugin from being packaged.
- A job layout that a VS Code test job and the planned UI tests fit into without moving anything.

**Non-Goals:**

- UI or integration tests in a running IDE.
- Coverage reports in CI; Kover's XML report is bound to `check`, which this change does not run.
- Changing how the package job builds the plugin.

## Decisions

### A job of its own for the JetBrains plugin

`test-jetbrains` runs on `ubuntu-latest`, `windows-latest` and `macos-latest`, with `fail-fast: false` like the Python job. Its steps:
- checkout;
- Java 21 (JetBrains distribution);
- `gradle/actions/setup-gradle@v5`;
- `./gradlew test` in `intellij-client/`, with `shell: bash` so that the same line works on Windows.

It uses the wrapper, so CI runs the Gradle version the repository pins. `gradle` on the runner image is whatever version the image ships.

No Python, Node or Hatch setup: the tests need none of them. A test that needs them later adds the setup itself.

Alternative: steps in the existing `test` job. That job runs 135 combinations of Python and Robot Framework, none of which matters to the plugin; the tests would run 45 times per operating system.

### Results in the published test report

The job uploads `intellij-client/build/test-results/test/` as `test-results-jetbrains-<os>`, also when tests fail. `publish-test-results` needs both test jobs and publishes `./**/test-results.xml` and `./**/TEST-*.xml`, the name pattern of Gradle's JUnit XML files.

### Packaging waits for the plugin tests

`package` needs `test` and `test-jetbrains`. `publish` already needs `package`, so a failing plugin test also stops a release.

### The verifier step comes back, as a gate

The step runs in `code-quality` after the Python checks, as `./gradlew verifyPlugin` in `intellij-client/`.
- The exit trap that appends each `report.md` to the job summary stays, with its heading shift. Each report starts with the verdict (for example "Compatible. 3 usages of deprecated API. 15 usages of experimental API") and lists the deprecated and experimental API usages below it, so the notes appear in the summary even when the step passes. Before the reports, the trap writes one line per IDE with its verdict, so the result is visible without scrolling through three reports of about 8 KB each.
- The upload of `build/reports/pluginVerifier` stays, with `if: always()`.
- `continue-on-error` and `-Dplugin.verifier.home.dir` go. The property belonged to the 1.x Gradle plugin; version 2.x resolves the verifier's IDEs as Gradle dependencies, as the local run showed.

A failure at a configured level fails `code-quality` and with it `publish`. Experimental and deprecated API usages are only reported.

Alternative: keep `continue-on-error: true` until the first runs are green. The local run is already green against all three IDEs, and a check that cannot fail protects nothing.

### Caching

`setup-gradle` caches Gradle's user home between runs, including the PyCharm distribution that the build and tests depend on and the verifier's IDEs. The first run downloads them; later runs reuse the cache.

## Risks / Trade-offs

- [The first CI run downloads PyCharm on three operating systems and three IDE versions for the verifier] → `setup-gradle`'s cache. If a job stays slow, narrow the verifier's IDEs or skip the test job for changes outside `intellij-client/` with path filters; neither is part of this change.
- [The verifier finds something in CI that it did not find locally, for example because `recommended()` picks a newer IDE] → The change fixes the plugin or, if the finding is not a real problem, adjusts the failure levels together with the maintainer. The verifier's report in the job summary names the problem.
- [Windows-specific test failures appear for the first time] → `fail-fast: false` shows them per operating system; fixing them belongs to this change, because the tests are meant to run on all three.

## Migration Plan

None. Rolling back means deleting the job and commenting the step out again.
