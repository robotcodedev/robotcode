# Spec Delta

## Purpose

Defines what the continuous integration of the RobotCode repository checks on every push and pull request before it packages and publishes RobotCode, so that a change that breaks a part of RobotCode is caught before it is released.

## ADDED Requirements

### Requirement: The JetBrains plugin's tests run in CI

On every push to `main`, every pull request to `main` and every manual run, the CI SHALL run the unit tests of the JetBrains plugin (`gradle test` in `intellij-client/`) on Linux, Windows and macOS, in a job of its own for the JetBrains plugin. A failing test SHALL fail that job. The test results SHALL be uploaded and SHALL appear in the published test results of the run, together with the results of the Python tests.

#### Scenario: A failing plugin test

- **WHEN** a pull request makes one of the plugin's unit tests fail
- **THEN** the JetBrains test job fails on every operating system where the test fails, and the published test results name the failing test

#### Scenario: All plugin tests pass

- **WHEN** a push leaves all of the plugin's unit tests green
- **THEN** the JetBrains test job succeeds on Linux, Windows and macOS, and the published test results list the plugin's tests

### Requirement: No package without passing plugin tests

The CI SHALL build the RobotCode packages, including the JetBrains plugin, only after the JetBrains test job has succeeded on every operating system, in the same way as it waits for the Python tests.

#### Scenario: Failing plugin tests block packaging

- **WHEN** the JetBrains test job fails
- **THEN** the package job does not run, and nothing is published

### Requirement: The plugin verifier runs in CI

The code-quality checks of the CI SHALL run the JetBrains plugin verifier (`gradle verifyPlugin` in `intellij-client/`) against the IDE versions that the plugin's build configures. A problem at one of the failure levels the build configures, such as an invalid plugin, a compatibility problem or a missing dependency, SHALL fail the code-quality checks.

#### Scenario: Compatibility problem

- **WHEN** a change makes the plugin use an API that one of the configured IDE versions does not have
- **THEN** the code-quality checks fail, and the job summary shows the verifier's report with the problem

### Requirement: The plugin verifier's results are shown

The job summary of the CI run SHALL show, for every verified IDE version, the plugin verifier's verdict and its notes, including the usages of deprecated and of experimental API, also when nothing fails. The verifier's reports SHALL also be uploaded with the run, also when the verifier fails.

#### Scenario: Clean verification

- **WHEN** the verifier finds no problem at a configured failure level
- **THEN** the code-quality checks pass, and the job summary lists each IDE version with its verdict, such as "Compatible. 3 usages of deprecated API. 15 usages of experimental API", followed by the usages themselves; the reports are also available as an artifact
