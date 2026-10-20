## ADDED Requirements

### Requirement: The VS Code extension's tests run in CI

On every push to `main`, every pull request to `main` and every manual run, the CI SHALL run the tests of the VS Code extension (`npm test`) on Linux, Windows and macOS, in a job of its own for the VS Code extension. A failing test SHALL fail that job. The test results SHALL be uploaded and SHALL appear in the published test results of the run, together with the results of the Python tests and the JetBrains plugin's tests.

#### Scenario: A failing extension test

- **WHEN** a pull request makes one of the VS Code extension's tests fail
- **THEN** the VS Code test job fails on every operating system where the test fails, and the published test results name the failing test

#### Scenario: All extension tests pass

- **WHEN** a push leaves all of the VS Code extension's tests green
- **THEN** the VS Code test job succeeds on Linux, Windows and macOS, and the published test results list the extension's tests

### Requirement: The extension's tests run with the minimum and the newest VS Code version

The VS Code test job SHALL run the extension's tests on every operating system twice: with the minimum VS Code version that `engines.vscode` in `package.json` declares, and with the newest stable version. The published test results SHALL tell the two runs apart.

#### Scenario: A test fails only with the newest VS Code

- **WHEN** a new stable release of VS Code makes one of the extension's tests fail
- **THEN** the runs with the newest stable version fail and those with the minimum version pass, and the published test results show which version the failure belongs to

### Requirement: No package without passing extension tests

The CI SHALL build the RobotCode packages only after the VS Code test job has succeeded on every operating system, in the same way as it waits for the Python tests and the JetBrains plugin's tests.

#### Scenario: Failing extension tests block packaging

- **WHEN** the VS Code test job fails
- **THEN** the package job does not run, and nothing is published
