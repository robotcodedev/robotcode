# Spec Delta

## Purpose

Defines what the continuous integration of the RobotCode repository checks on every push and pull request before it packages and publishes RobotCode, so that a change that breaks a part of RobotCode is caught before it is released.

## ADDED Requirements

### Requirement: The JetBrains plugin's integration tests run in CI

The repository SHALL contain integration tests that start PyCharm in its own process with the JetBrains plugin installed, open a test project with Robot Framework files and an interpreter that has Robot Framework, and check the plugin's behaviour in that IDE. On every push to `main`, every pull request to `main` and every manual run, the CI SHALL run these tests on Linux in the job for the JetBrains plugin, in a virtual display. A failing integration test SHALL fail that job, and with it packaging. For a failed test, the CI SHALL upload the IDE's logs and a screenshot taken at the failure.

The integration tests SHALL at least check that:

- the IDE starts with the plugin, opens the test project, and logs no error that names RobotCode;
- the RobotCode language server starts and reports a diagnostic for a call of an unknown keyword;
- the tests of the test project get run markers;
- a test of the test project runs from a run configuration and shows as passed in the results tree.

#### Scenario: The plugin no longer starts its language server

- **WHEN** a change keeps the RobotCode language server from starting in the test IDE
- **THEN** the integration test for the diagnostic fails, the JetBrains test job fails, and the run has the IDE's logs and a screenshot of that test

#### Scenario: Smoke tests pass

- **WHEN** a push leaves the plugin working
- **THEN** the integration tests pass on Linux, and their results appear in the published test results of the run

#### Scenario: Running the tests locally

- **WHEN** a developer runs the integration test task in `intellij-client/` on Linux with a display or a virtual display
- **THEN** the same tests run against PyCharm with the plugin built from the working tree, without touching the developer's own IDE configuration or projects
