# Tasks

## 1. JetBrains test job

- [ ] 1.1 Add the job `test-jetbrains` to `.github/workflows/build-test-package-publish.yml`: matrix `ubuntu-latest`, `windows-latest`, `macos-latest` with `fail-fast: false`, `shell: bash`, checkout, Java 21 (JetBrains distribution), `gradle/actions/setup-gradle@v5`, and `./gradlew --console=plain test` in `intellij-client/`. Upload `intellij-client/build/test-results/test/` as `test-results-jetbrains-${{ matrix.os }}` with `if: always()`. Verify that the file still parses as YAML (`python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <file>`) and that the job definition matches design.md.
- [ ] 1.2 Let `publish-test-results` need `test` and `test-jetbrains`, and publish `./**/test-results.xml` and `./**/TEST-*.xml`. Let `package` need `test` and `test-jetbrains`. Verify by reading the `needs` graph in the workflow file.

## 2. Plugin verifier

- [ ] 2.1 Replace the commented-out verifier steps in `code-quality` with active ones: `./gradlew --console=plain verifyPlugin` in `intellij-client/`, the exit trap that writes one line per IDE with its verdict (the report's second line) and then appends each `build/reports/pluginVerifier/*/report.md` to `$GITHUB_STEP_SUMMARY` with headings shifted one level, no `continue-on-error`, no `-Dplugin.verifier.home.dir`, and the upload of `intellij-client/build/reports/pluginVerifier` with `if: always()`. Verify locally that `./gradlew verifyPlugin` still passes and that running the trap's script with `GITHUB_STEP_SUMMARY` pointing to a temporary file produces the verdict lines and the three reports with their deprecated and experimental API usages.

## 3. Verification

- [ ] 3.1 After the maintainer pushes: check the first run. `test-jetbrains` is green on all three operating systems, the published test results list the plugin's 15 tests, `code-quality` shows the verdict per IDE and the reports with the deprecated and experimental API usages in its summary and has the report artifact, and `package` started only after `test-jetbrains`. Note the duration of the first and of a second run (cache). Fix any failure that the run reveals, or agree with the maintainer how to handle a verifier finding that is not a real problem.
- [ ] 3.2 Only if the maintainer wants it: check the gate with a throw-away pull request whose deliberately failing assertion in one plugin test makes `test-jetbrains` fail and keeps `package` from running; close the pull request afterwards. Otherwise verify the gate by reading the `needs` graph and mark the task with that note.
