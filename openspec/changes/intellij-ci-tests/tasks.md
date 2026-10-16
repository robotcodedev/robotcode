# Tasks

## 1. JetBrains test job

- [x] 1.1 Add the job `test-jetbrains` to `.github/workflows/build-test-package-publish.yml`: matrix `ubuntu-latest`, `windows-latest`, `macos-latest` with `fail-fast: false`, `shell: bash`, checkout, Java 21 (JetBrains distribution), `gradle/actions/setup-gradle@v5`, and `./gradlew --console=plain test` in `intellij-client/`. Upload `intellij-client/build/test-results/test/` as `test-results-jetbrains-${{ matrix.os }}` with `if: always()`. Verify that the file still parses as YAML (`python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <file>`) and that the job definition matches design.md.
- [x] 1.2 Let `publish-test-results` need `test` and `test-jetbrains`, and publish `./**/test-results.xml` and `./**/TEST-*.xml`. Let `package` need `test` and `test-jetbrains`. Verify by reading the `needs` graph in the workflow file.

## 2. Plugin verifier

- [x] 2.1 In `intellij-client/build.gradle.kts`, replace `recommended()` in `pluginVerification.ides` with `select`, using the plugin's platform type, `pluginSinceBuild`/`pluginUntilBuild` and the channel `RELEASE`. The Gradle property `verifyEap` switches to `latest` with the same filter and the channel `EAP`, and the reports to `build/reports/pluginVerifier-eap`. Verify locally:
  - `./gradlew verifyPlugin` checks only released versions (on 2026-10-16 these were PY-2026.1.5 and PY-2026.2.3) and passes;
  - with the property it checks the current EAP build (on 2026-10-16 PY-263.6800.43) and writes its reports to the EAP directory.
- [x] 2.2 Replace the commented-out verifier steps in `code-quality` with two active steps.
  - **Gate:** `./gradlew --console=plain verifyPlugin` in `intellij-client/`, without `continue-on-error` and without `-Dplugin.verifier.home.dir`.
  - **EAP step:** the same with the property, with `continue-on-error: true`, and with a `::warning::` that names the problem when it fails.
  - **Exit trap of each step:** it writes a heading (released versions or EAP), then one line per IDE with its verdict (the first line after the report's heading that is not empty), then each `report.md` of its directory with headings shifted one level, into `$GITHUB_STEP_SUMMARY`.
  - **Upload:** both report directories, with `if: always()`.

  Verify that the workflow still parses as YAML, and that running both trap scripts with `GITHUB_STEP_SUMMARY` pointing to a temporary file produces the headings, the verdict lines and the reports with their deprecated and experimental API usages.
- [x] 2.3 Remove the step "Export Properties" from `package`: it writes the output `pluginVerifierHomeDir`, which no step reads. Verify that the workflow still parses as YAML and that nothing in `.github/` refers to `steps.properties` or `pluginVerifierHomeDir`.

## 3. Verification

- [ ] 3.1 After the maintainer pushes, check the first run:
  - `test-jetbrains` is green on all three operating systems, and the published test results list the plugin's tests;
  - `code-quality` shows the verdicts and reports of both verifier steps in its summary and has the report artifact;
  - the result of the EAP step doesn't decide the job;
  - `package` started only after `test-jetbrains`. Note the duration of the first and of a second run (cache). Fix any failure that the run reveals, or agree with the maintainer how to handle a verifier finding that is not a real problem.
- [x] 3.2 Only if the maintainer wants it: check the gate with a throw-away pull request whose deliberately failing assertion in one plugin test makes `test-jetbrains` fail and keeps `package` from running; close the pull request afterwards. Otherwise verify the gate by reading the `needs` graph and mark the task with that note.
  - Verified by reading the `needs` graph; the maintainer decided against the pull request on 2026-10-16. `package` needs `test` and `test-jetbrains` and has no `if` of its own, so GitHub skips it when `test-jetbrains` fails, and `publish` needs `package`. A failing test fails the step: `build.gradle.kts` doesn't set `ignoreFailures`, and the step has no `continue-on-error`.
