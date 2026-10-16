# Design

## Context

See proposal.md for the motivation. The current workflow, `.github/workflows/build-test-package-publish.yml`:

- **`test`:** Python tests only, on a matrix of operating system × Python × Robot Framework. It uploads `test-results/**/test-results.xml`.
- **`publish-test-results`:** needs `test`, downloads all artifacts of the run, and publishes `./**/test-results.xml` with `EnricoMi/publish-unit-test-result-action`.
- **`code-quality`:** Ubuntu. It sets up Node, Python, Hatch, Java 21 (JetBrains distribution) and Gradle (`gradle/actions/setup-gradle@v5`), then runs the Python lint and typing checks. The verifier step after them is commented out. It ran `gradle --no-daemon verifyPlugin -Dplugin.verifier.home.dir=~/.pluginVerifier`, appended the Markdown reports to the job summary through an exit trap, and uploaded `intellij-client/build/reports/pluginVerifier`.
- **`package`:** needs `test`; `hatch run build:package` runs `gradle buildPlugin` (`scripts/package.py`). **`publish`:** needs `code-quality` and `package`.

The plugin build (`intellij-client/build.gradle.kts`, IntelliJ Platform Gradle Plugin 2.19.0, Gradle wrapper 9.8.0):

- **Tests:** `testFramework(TestFrameworkType.Platform)`, JUnit 4. The test sandbox copies `package.json`, the syntaxes and `bundled/` from the repository root. The current tests need no Python.
- **Verifier:**
  - `pluginVerification` fails on `INVALID_PLUGIN`, `COMPATIBILITY_PROBLEMS` and `MISSING_DEPENDENCIES`, writes Markdown and plain reports, and checks `ides { recommended() }`.
  - `recommended()` reads JetBrains' release list on every run and includes the current EAP build. On 2026-10-16 (`./gradlew printProductsReleases`) it picked PY-2026.1.5, PY-2026.2.3 and PY-263.6800.43, a 2026.3 build without a release name.
  - The plugin claims `pluginSinceBuild = 261` and `pluginUntilBuild = 271.*`, so EAP builds of 2027.1 would come next.

**Checked locally:**
- `./gradlew test`, 2026-10-16:
  - it passes with 374 tests in 78 classes in about 31 seconds of test time;
  - `RobotCodeEnvironmentProbeTest` is skipped without the environment variable `ROBOTCODE_TEST_PYTHON`;
  - the maintainer ran the tests on Windows the same day and pushed the fixes (0f5df45d); they have not run on macOS.
- `./gradlew verifyPlugin`, 2026-10-15:
  - it passes against PY-261.27258.51, PY-262.10968.92 and PY-263.6800.43, all "Compatible";
  - the reports list 25–30 experimental API usages, and against 263 also 9 deprecated ones: `MacrosDialog.Filters` in the run configuration's option fragments and target panel, `FileEditorManager.openFile(VirtualFile, boolean)` and `FileEditorManager.openTextEditor(OpenFileDescriptor, boolean)`;
  - neither kind is a configured failure level.
- On 2026-10-04 the verifier's IDEs and plugins came from the Gradle cache, and `~/.pluginVerifier/ides` stayed empty.

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

### The verifier comes back: a gate on released versions, a report on EAP builds

The maintainer decided this split on 2026-10-16.

- **Selection of IDEs:** `pluginVerification.ides` uses `select` instead of `recommended()`, with the plugin's platform type, its build range from `pluginSinceBuild` and `pluginUntilBuild`, and the channel `RELEASE`. The Gradle property `verifyEap` switches to `latest` with the same filter and the channel `EAP`, and the report directory to `build/reports/pluginVerifier-eap`. `latest` keeps only the newest matching build, the current EAP build; between a release and the next EAP build, that is the last EAP build of the version just released. Without the property, `./gradlew verifyPlugin` checks the released versions, locally as in CI.
- **The gate:** the first step runs `./gradlew --console=plain verifyPlugin` in `code-quality` after the Python checks, without `continue-on-error`. A failure at a configured level fails `code-quality` and with it `publish`.
- **The EAP step:** it runs after the gate with the property and with `continue-on-error: true`. When it fails, the run gets a warning (`::warning::`) that names the problem, and the job stays green.
- **Summary:**
  - Each step has an exit trap that writes a heading, released versions or EAP, then one line per IDE with its verdict, and then each `report.md` with its headings shifted one level.
  - Each report starts with a heading and, after an empty line, the verdict, for example "Compatible. 3 usages of deprecated API. 15 usages of experimental API". Then it lists the deprecated and experimental API usages, so the notes appear even when the step passes.
- **Artifacts:** the upload of `build/reports/pluginVerifier` and `build/reports/pluginVerifier-eap` stays, with `if: always()`.
- **`-Dplugin.verifier.home.dir` goes:** the property belonged to the 1.x Gradle plugin. Version 2.x resolves the verifier's IDEs as Gradle dependencies, as the local run showed. The step "Export Properties" of the `package` job goes with it: it writes the output `pluginVerifierHomeDir` (`~/.pluginVerifier`), which no step has read since the step was added on 2024-12-29.

Experimental and deprecated API usages are only reported.

Alternatives:
- `recommended()` as the gate, as planned before. It includes the current EAP build, so an EAP build that removes an API the plugin uses would block every release for the released versions too. The nine deprecated usages against 263 are such candidates.
- `select` with the channel `EAP` for the EAP step. It returns the newest EAP build of every version in the range, on 2026-10-16 also PY-261.22158.126 and PY-262.8665.97, the last EAP builds of 2026.1 and 2026.2. That means two more IDE downloads in CI for builds that the released versions have superseded.
- No EAP verification at all. The removal of an API would then show up only once that version is released.
- `continue-on-error: true` for the gate until the first runs are green. The local run is already green, and a check that cannot fail protects nothing.

### Caching

`setup-gradle` caches Gradle's user home between runs, including the PyCharm distribution that the build and tests depend on and the verifier's IDEs. The first run downloads them; later runs reuse the cache.

## Risks / Trade-offs

- [The first CI run downloads PyCharm on three operating systems and the IDE versions of both verifier steps] → `setup-gradle`'s cache. If a job stays slow, narrow the verifier's IDEs or skip the test job for changes outside `intellij-client/` with path filters; neither is part of this change.
- [A new release of a supported version enters the gate on its own, and the verifier finds a problem there] → The change fixes the plugin or, if the finding is not a real problem, adjusts the failure levels together with the maintainer. The job summary names the problem, and EAP builds usually show it earlier as a warning.
- [Test failures that only macOS shows appear for the first time; Windows was fixed on 2026-10-16 (0f5df45d)] → `fail-fast: false` shows them per operating system. Fixing them belongs to this change, because the tests are meant to run on all three.

## Migration Plan

None. Rolling back means deleting the job, commenting the verifier steps out again and going back to `recommended()`.
