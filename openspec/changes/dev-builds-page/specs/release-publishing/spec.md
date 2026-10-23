# Spec Delta

## ADDED Requirements

### Requirement: The documentation tells users how to get the dev builds

robotcode.io SHALL have a page in Getting Started that explains, for the VS Code extension, the PyCharm plugin and the Python packages, how a user switches to the dev builds, how they go back to the releases, and what the version of a dev build looks like. The README SHALL link to that page.

#### Scenario: PyCharm user subscribes to the dev builds

- **WHEN** a PyCharm user follows the page
- **THEN** they add the plugin repository of RobotCode's channel `dev`, and the IDE offers the newest dev build of RobotCode, but no dev builds of other plugins

#### Scenario: VS Code user goes back to the release

- **WHEN** a VS Code user on a dev build follows the page's way back
- **THEN** VS Code installs the newest release version of the extension

#### Scenario: Python dev version without other pre-releases

- **WHEN** a user installs a Python dev version as the page shows
- **THEN** pip installs that dev version of `robotcode` and of its packages, and installs releases of all other dependencies, such as Robot Framework

#### Scenario: README link

- **WHEN** a reader looks for ways to help in the README
- **THEN** "Get Involved" links to the page
