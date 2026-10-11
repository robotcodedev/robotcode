# Spec Delta

## ADDED Requirements

### Requirement: Feature tour in the site's theme

The screen recordings and the editor screenshots of the home page's feature tour, of VS Code, PyCharm and Neovim, SHALL exist in a light and a dark variant. The tour SHALL show the variant that matches the site's theme, in its window and in its enlarged view, and SHALL request only the files of that variant.

#### Scenario: Light site
- **WHEN** the home page is shown in the light theme
- **THEN** the recordings of the feature tour and its screenshots of VS Code, PyCharm and Neovim show their editor in a light theme
- **AND** no file of a dark variant is requested

#### Scenario: Enlarged view
- **WHEN** the reader enlarges a recording or a screenshot of the feature tour
- **THEN** the enlarged view shows the variant that matches the site's theme

### Requirement: Theme switch during the feature tour

When the reader switches the site's theme, the feature tour SHALL show the variants of the new theme at once, without reloading the page, and a recording that is playing SHALL go on in the new variant from the point it had reached.

#### Scenario: Switching while a recording plays
- **WHEN** the reader switches from the dark to the light theme while the Go to Definition recording of the tour plays
- **THEN** the light variant of that recording plays on from the same point

### Requirement: Recordings on the About page in the site's theme

The screen recordings on the About page SHALL exist in a light and a dark variant, and the page SHALL show the variant that matches the site's theme, also after the reader switches it.

#### Scenario: Light site
- **WHEN** `/about/` is shown in the light theme
- **THEN** its recordings show VS Code in its light theme

### Requirement: Recordings on Get Started with VS Code

The screen recordings on Get Started with VS Code SHALL show the steps of their sections with the VS Code and RobotCode of the time of recording: adding RobotCode to the workspace recommendations, creating a Python environment and running the first test. Each SHALL exist in a light and a dark variant, and the page SHALL show the variant that matches the site's theme.

#### Scenario: Creating a Python environment
- **WHEN** `/getting-started/vscode/` is shown in the dark theme
- **THEN** the recording of its Python environment section shows **Python: Create Environment** creating a `.venv` environment in VS Code's dark theme

#### Scenario: Running the first test
- **WHEN** the reader switches the page to the light theme
- **THEN** the recording of its first-test section shows the test run from the play button next to it, and `Hello world` in the Debug Console, in VS Code's light theme
