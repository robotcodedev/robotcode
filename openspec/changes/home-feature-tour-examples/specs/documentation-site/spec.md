## MODIFIED Requirements

### Requirement: Home page

The home page SHALL show the product name, the tagline, a subline chosen at random on each load, one picture of the RobotCode artwork chosen at random on each load, the actions Get Started, VS Code Extension, JetBrains Plugin, Star on GitHub and Sponsor, and a note that RobotCode is free and open source, which leads to the open-source section. The home page SHALL show no edit link and no last-change date.

#### Scenario: Random picture
- **WHEN** the home page is loaded
- **THEN** one picture of the RobotCode artwork is shown next to the product name
- **AND** the actions Get Started, VS Code Extension and JetBrains Plugin are offered

#### Scenario: Browsing the pictures
- **WHEN** a reader swipes left on the picture, or clicks it and presses the right arrow key
- **THEN** the next picture is shown, in the enlarged view in the second case
- **AND** Escape closes the enlarged view

#### Scenario: Feature card target
- **WHEN** a reader selects the "Interactive REPL" feature card in the feature tour and follows its link
- **THEN** the REPL guide `/guides/repl/` is shown

#### Scenario: Section order
- **WHEN** a reader scrolls down the home page
- **THEN** the feature tour, the AI agents section, the tutorial video, the latest news and the open-source section follow the hero in this order

#### Scenario: Feature tour in the first screen
- **WHEN** the home page is opened in a 1366×768 browser window
- **THEN** the heading and the beginning of the feature tour are visible without scrolling

#### Scenario: Setting up an agent
- **WHEN** a reader follows "Set up your agent" in the AI agents section
- **THEN** the guide `/guides/ai-agents/` is shown

#### Scenario: Latest news
- **WHEN** the home page is built
- **THEN** its latest news lists the three newest posts, newest first, each with its date, title and description and a link to the post
- **AND** a link leads to `/news/`

#### Scenario: Open source
- **WHEN** a reader follows the open-source note in the hero
- **THEN** the open-source section is shown with the license, a link to the GitHub repository, a link to Support & Contribute, the sponsoring options and the supporters

### Requirement: Feature tour on the home page

The feature tour SHALL list Code intelligence; Run, debug & test explorer; One config everywhere; Powerful CLI; Interactive REPL; and Multi-IDE, same core as feature cards, each with its description and links to the pages that cover it, next to a demo window that shows examples of the selected feature.

#### Scenario: Demo of a feature card
- **WHEN** a reader selects the "Powerful CLI" feature card in the feature tour
- **THEN** its description and links are shown next to the demo of the CLI

### Requirement: Home page demos

The demo windows of the home page — the window of the feature tour and the window of the agent conversations — SHALL show their parts one after another while the window is visible: a part stays until it can be read, a screen recording until it has played once from its beginning, and the steps of a conversation or a terminal session appear one by one. Selecting a part SHALL show it at once.

#### Scenario: Playing while visible
- **WHEN** the feature tour scrolls into view
- **THEN** its window shows the demo of the first feature and, when that demo is over, the demo of the next feature
- **AND** the list marks the feature shown and shows its description

#### Scenario: Editor screenshots
- **WHEN** the Multi-IDE feature is shown
- **THEN** its screenshots follow one another, the window title names the editor of each, and the reader can select each screenshot

#### Scenario: Running and debugging
- **WHEN** the Run, debug & test explorer feature is shown
- **THEN** the recordings of running the tests from the test explorer, of a debug session, of the debugger stopping at a failure, of the Debug Console and of the log after a run play one after another, followed by the terminal session of `robotcode robot-debug`
- **AND** the reader can select each example

## ADDED Requirements

### Requirement: Examples in the feature demos

The demo of each feature of the feature tour SHALL show several examples of the feature one after another, each one selectable by the reader, with a window title that names the editor or terminal and what the example shows. An example is a screen recording, a screenshot or a terminal session; a terminal session SHALL show its steps one by one from the first each time it is shown.

#### Scenario: Terminal session in a series
- **WHEN** the reader selects the `robotcode analyze code` example of Powerful CLI
- **THEN** the window shows that session's steps one by one from the first
- **AND** selecting it again starts the session from the first step again

### Requirement: Code intelligence examples

The examples of Code intelligence SHALL be, in this order: writing a test with completion, signature help, a hover and a quick fix; the Documentation Viewer; Go to Definition from a keyword call into the Python library that implements the keyword; Find References; the diagnostics of RobotCode and Robocop; the Keywords view.

#### Scenario: Code intelligence examples
- **WHEN** the Code intelligence feature is shown
- **THEN** the recording of writing a test plays first, followed by the Documentation Viewer, Go to Definition, Find References, the diagnostics and the Keywords view
- **AND** the window title names each example, and the reader can select each one

### Requirement: Run, debug and test explorer examples

The examples of Run, debug & test explorer SHALL be, in this order: running the tests from the test explorer; a debug session with a breakpoint and stepping; the debugger stopping at a failure; a keyword run in the Debug Console while the debugger is stopped; the log opened after a run; a suite debugged in the terminal with `robotcode robot-debug`.

#### Scenario: Last example of running and debugging
- **WHEN** the Run, debug & test explorer feature is shown
- **THEN** its last example is a suite debugged in the terminal with `robotcode robot-debug`

### Requirement: One config everywhere examples

The examples of One config everywhere SHALL be, in this order: a `robot.toml` with a profile and the configuration that results from it; completion and hover in `robot.toml` from its JSON schema; a profile selected in VS Code and tests run with it; a CI workflow that runs the same profile.

#### Scenario: First and last configuration example
- **WHEN** the One config everywhere feature is shown
- **THEN** its first example is a `robot.toml` with a profile and the configuration that results from it, and its last is a CI workflow that runs the same profile

### Requirement: Powerful CLI examples

The examples of Powerful CLI SHALL be, in this order: tests discovered by tag and by test metadata; `robotcode analyze code`; the results of a run; the documentation of a library with `robotcode doc`.

#### Scenario: First and last CLI example
- **WHEN** the Powerful CLI feature is shown
- **THEN** its first example discovers tests by tag and by test metadata, and its last shows the documentation of a library with `robotcode doc`

### Requirement: Interactive REPL examples

The examples of Interactive REPL SHALL be, in this order: keywords of a resource file called at the prompt and saved as a test; the Browser library used at the prompt; the REPL in VS Code; the debugger attached at the prompt, stopping in a keyword of a resource file.

#### Scenario: Debugger at the REPL prompt
- **WHEN** the last example of Interactive REPL is shown
- **THEN** the session attaches the debugger at the prompt, calls a keyword of a resource file and stops in it at the debug prompt

### Requirement: Multi-IDE examples

The examples of Multi-IDE, same core SHALL be screenshots of RobotCode in several editors.

#### Scenario: Screenshots of editors
- **WHEN** the Multi-IDE feature is shown
- **THEN** its examples are screenshots of RobotCode in several editors

### Requirement: Shortcuts in the screen recordings

The screen recordings of VS Code SHALL show the keyboard shortcuts pressed in them.

#### Scenario: Shortcuts in a recording
- **WHEN** the Go to Definition recording plays
- **THEN** the shortcut that opens the definition is shown in the recording while it is pressed
