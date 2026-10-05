## MODIFIED Requirements

### Requirement: Home page

The home page SHALL show the product name, the tagline, a subline chosen at random on each load, one picture of the RobotCode artwork chosen at random on each load, the actions Get Started, Install VS Code, Install JetBrains, Star on GitHub and Sponsor, and a note that RobotCode is free and open source, which leads to the open-source section. Previous and next buttons and a horizontal swipe on the picture SHALL switch to the neighbouring picture. Clicking the picture SHALL open an enlarged view that closes on a click or Escape and in which the left and right arrow keys switch pictures.

Below the hero the home page SHALL show, in this order, the feature tour, the AI agents section, the RoboCon 2024 tutorial video, the latest news and the open-source section. The feature tour SHALL list Code intelligence; Run, debug & test explorer; One config everywhere; Powerful CLI; Interactive REPL; and Multi-IDE, same core as feature cards, each with its description and links to the pages that cover it, next to a demo window that shows examples of the selected feature. The AI agents section SHALL describe what an AI agent does with the RobotCode skill, name the agents it works with, link to the setup guide `/guides/ai-agents/` and show conversations of an agent working through `robotcode`. The latest news SHALL list the three newest posts, newest first, with date, title and description, and link to all news. The open-source section SHALL state the license, link to the GitHub repository, to Support & Contribute and to the sponsoring options, and show the supporters. The home page SHALL show no edit link and no last-change date. On a viewport of 1366×768 or larger, the beginning of the feature tour SHALL be visible without scrolling.

#### Scenario: Random picture
- **WHEN** the home page is loaded
- **THEN** one picture of the RobotCode artwork is shown next to the product name
- **AND** the actions Get Started, Install VS Code and Install JetBrains are offered

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

### Requirement: Home page demos

The demo windows of the home page — the window of the feature tour and the window of the agent conversations — SHALL show their parts one after another while the window is visible: a part stays until it can be read, a screen recording until it has played once from its beginning, and the steps of a conversation or a terminal session appear one by one. A window SHALL hold its current part while the reader hovers over it or focuses it with the keyboard, while it is scrolled out of view and while one of its pictures is enlarged; its pause button SHALL hold it and show the whole current part until the button is pressed again. Selecting a part SHALL show it at once. Clicking a screen recording or a screenshot SHALL show it enlarged until a click or Escape. With reduced motion requested by the reader's system, the windows SHALL change parts only when the reader selects one, show each part complete and play no recording by itself. A conversation longer than its window SHALL scroll along with its newest step. The commands and output in the demos SHALL be taken from real runs of an example project, abridged, and the window of the agent conversations SHALL say so. `/llms-full.txt` SHALL NOT contain the demo windows; the texts of the feature tour and of the AI agents section SHALL be part of it.

The demo of each feature of the feature tour SHALL show several examples of the feature one after another, each one selectable by the reader, with a window title that names the editor or terminal and what the example shows. An example is a screen recording, a screenshot or a terminal session; a terminal session SHALL show its steps one by one from the first each time it is shown. The examples SHALL be, in this order:

- Code intelligence: writing a test with completion, signature help, a hover and a quick fix; the Documentation Viewer; Go to Definition from a keyword call into the Python library that implements the keyword; Find References; the diagnostics of RobotCode and Robocop; the Keywords view.
- Run, debug & test explorer: running the tests from the test explorer; a debug session with a breakpoint and stepping; the debugger stopping at a failure; a keyword run in the Debug Console while the debugger is stopped; the log opened after a run; a suite debugged in the terminal with `robotcode robot-debug`.
- One config everywhere: a `robot.toml` with a profile and the configuration that results from it; completion and hover in `robot.toml` from its JSON schema; a profile selected in VS Code and tests run with it; a CI workflow that runs the same profile.
- Powerful CLI: tests discovered by tag and by test metadata; `robotcode analyze code`; the results of a run; the documentation of a library with `robotcode doc`.
- Interactive REPL: keywords of a resource file called at the prompt and saved as a test; the Browser library used at the prompt; the REPL in VS Code; the debugger attached at the prompt, stopping in a keyword of a resource file.
- Multi-IDE, same core: screenshots of RobotCode in several editors.

The screen recordings of VS Code SHALL show the keyboard shortcuts pressed in them.

#### Scenario: Playing while visible
- **WHEN** the feature tour scrolls into view
- **THEN** its window shows the demo of the first feature and, when that demo is over, the demo of the next feature
- **AND** the list marks the feature shown and shows its description

#### Scenario: Holding a demo
- **WHEN** the reader hovers over a demo window
- **THEN** its current part stays until the pointer leaves the window

#### Scenario: Pausing a demo
- **WHEN** the reader presses the pause button of a demo window
- **THEN** the current part stays and shows all its steps, and no recording plays, until the button is pressed again

#### Scenario: Reduced motion
- **WHEN** the reader's system asks for reduced motion
- **THEN** no demo changes its part and no recording plays by itself
- **AND** selecting a part shows it complete

#### Scenario: Enlarging a recording
- **WHEN** the reader clicks the screen recording of Code intelligence
- **THEN** the recording is shown enlarged
- **AND** Escape closes the enlarged view

#### Scenario: Editor screenshots
- **WHEN** the Multi-IDE feature is shown
- **THEN** its screenshots follow one another, the window title names the editor of each, and the reader can select each screenshot

#### Scenario: Code intelligence examples
- **WHEN** the Code intelligence feature is shown
- **THEN** the recording of writing a test plays first, followed by the Documentation Viewer, Go to Definition, Find References, the diagnostics and the Keywords view
- **AND** the window title names each example, and the reader can select each one

#### Scenario: Running and debugging
- **WHEN** the Run, debug & test explorer feature is shown
- **THEN** the recordings of running the tests from the test explorer, of a debug session, of the debugger stopping at a failure, of the Debug Console and of the log after a run play one after another, followed by the terminal session of `robotcode robot-debug`
- **AND** the reader can select each example

#### Scenario: Terminal session in a series
- **WHEN** the reader selects the `robotcode analyze code` example of Powerful CLI
- **THEN** the window shows that session's steps one by one from the first
- **AND** selecting it again starts the session from the first step again

#### Scenario: Debugger at the REPL prompt
- **WHEN** the last example of Interactive REPL is shown
- **THEN** the session attaches the debugger at the prompt, calls a keyword of a resource file and stops in it at the debug prompt

#### Scenario: Shortcuts in a recording
- **WHEN** the Go to Definition recording plays
- **THEN** the shortcut that opens the definition is shown in the recording while it is pressed

#### Scenario: Demos in the LLM export
- **WHEN** `/llms-full.txt` is requested
- **THEN** it contains the descriptions of the features and the abilities of an agent from the home page
- **AND** it contains none of the terminal sessions and conversations of the demo windows
