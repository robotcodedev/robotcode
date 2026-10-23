# Spec Delta

## Purpose

Defines what the repository's dev container, which GitHub Codespaces also uses, provides for working on RobotCode, so that a contributor can run the checks that the contribution guide asks for without setting up a machine of their own.

## ADDED Requirements

### Requirement: Every test suite runs in the dev container

After the repository's dev container (`.devcontainer/devcontainer.json`) has been created, locally or as a GitHub Codespace, the Python tests (`hatch run test:test`), the VS Code extension's tests (`xvfb-run -a npm test`) and the PyCharm plugin's tests (`./gradlew test` in `intellij-client/`) SHALL run in it without further setup. What a test run downloads by itself, such as VS Code, PyCharm or the Gradle distribution, does not count as setup.

#### Scenario: Plugin tests in a new Codespace

- **WHEN** a contributor opens the repository in a new Codespace and runs `./gradlew test` in `intellij-client/`
- **THEN** Gradle starts with the container's JDK 21, and the plugin's tests run

#### Scenario: Extension tests without a display

- **WHEN** a contributor runs `xvfb-run -a npm test` in the dev container
- **THEN** VS Code starts on the virtual display, and the extension's tests run

#### Scenario: Python tests

- **WHEN** a contributor runs `hatch run test:test` in the dev container
- **THEN** the Python tests run with every supported Robot Framework version, as on any other machine
