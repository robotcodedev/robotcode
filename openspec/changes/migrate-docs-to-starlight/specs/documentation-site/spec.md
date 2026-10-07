# Spec Delta

## ADDED Requirements

### Requirement: Published at robotcode.io

The site SHALL be the one published at https://robotcode.io and SHALL replace the previous VitePress site entirely. It SHALL be built from the repository's `docs/` directory, where its pages are edited directly, so that each page's edit link points to its file under `docs/src/content/docs/`.

#### Scenario: New paths on the published site
- **WHEN** a reader opens `https://robotcode.io/reference/config/`
- **THEN** the robot.toml configuration reference of the new site is shown

#### Scenario: Old path on the published site
- **WHEN** a reader opens `https://robotcode.io/03_reference/config`
- **THEN** the site's not-found page is returned

#### Scenario: Edit link
- **WHEN** a reader opens `https://robotcode.io/getting-started/neovim/`
- **THEN** the page links to `docs/src/content/docs/getting-started/neovim.mdx` in the GitHub repository

### Requirement: Newest release notes at a fixed address

The site SHALL serve `/news/latest/`, which SHALL lead to the newest post tagged `release` of the build, so that a link to the newest release notes never has to change. The "What's New?" notification of the VS Code extension SHALL open it.

#### Scenario: What's new from the VS Code extension
- **WHEN** a reader selects "What's New?" in the notification that the VS Code extension shows after an update
- **THEN** the newest release post is shown

#### Scenario: New release post
- **WHEN** a post tagged `release` with a newer date than all other posts is added and the site is built
- **THEN** `/news/latest/` leads to that post, also without JavaScript

#### Scenario: Other news
- **WHEN** a post of another kind, such as `tips`, is newer than every release post
- **THEN** `/news/latest/` still leads to the newest release post

### Requirement: Generated reference pages

The generated CLI reference and the generated configuration reference SHALL be pages of the Reference area that declare their title and description and contain no top-level heading of their own. Their generators SHALL write them in place, and regenerating them with the documented commands SHALL change only their generated content.

#### Scenario: Regenerate the configuration reference
- **WHEN** the configuration reference is regenerated with the documented command without changes to the option model
- **THEN** the page is unchanged
- **AND** the site builds without errors

#### Scenario: Regenerate the CLI reference
- **WHEN** the CLI reference is regenerated with the documented command without changes to the command line
- **THEN** the page is unchanged

### Requirement: Home page demos

The demo windows of the home page — the window of the feature tour and the window of the agent conversations — SHALL show their parts one after another while the window is visible: a part stays until it can be read, a screen recording until it has played once from its beginning, and the steps of a conversation appear one by one. Selecting a part SHALL show it at once.

#### Scenario: Playing while visible
- **WHEN** the feature tour scrolls into view
- **THEN** its window shows the demo of the first feature and, when that demo is over, the demo of the next feature
- **AND** the list marks the feature shown and shows its description

#### Scenario: Editor screenshots
- **WHEN** the Multi-IDE feature is shown
- **THEN** its screenshots follow one another, the window title names the editor of each, and the reader can select each screenshot

#### Scenario: Running and debugging
- **WHEN** the Run, debug & test explorer feature is shown
- **THEN** a recording of running the tests from the test explorer plays, then a recording of a debug session, and the reader can select each recording

### Requirement: Holding and pausing a home page demo

A demo window of the home page SHALL hold its current part while the reader hovers over it or focuses it with the keyboard, while it is scrolled out of view and while one of its pictures is enlarged; its pause button SHALL hold it and show the whole current part until the button is pressed again.

#### Scenario: Holding a demo
- **WHEN** the reader hovers over a demo window
- **THEN** its current part stays until the pointer leaves the window

#### Scenario: Pausing a demo
- **WHEN** the reader presses the pause button of a demo window
- **THEN** the current part stays and shows all its steps, and no recording plays, until the button is pressed again

### Requirement: Enlarged parts and reduced motion in home page demos

Clicking a screen recording or a screenshot in a demo window of the home page SHALL show it enlarged until a click or Escape. With reduced motion requested by the reader's system, the windows SHALL change parts only when the reader selects one, show each part complete and play no recording by itself.

#### Scenario: Enlarging a recording
- **WHEN** the reader clicks the screen recording of Code intelligence
- **THEN** the recording is shown enlarged
- **AND** Escape closes the enlarged view

#### Scenario: Reduced motion
- **WHEN** the reader's system asks for reduced motion
- **THEN** no demo changes its part and no recording plays by itself
- **AND** selecting a part shows it complete

### Requirement: Content of the home page demos

A conversation longer than its window SHALL scroll along with its newest step. The commands and output in the demos SHALL be taken from real runs of an example project, abridged, and the window of the agent conversations SHALL say so. `/llms-full.txt` SHALL NOT contain the demo windows; the texts of the feature tour and of the AI agents section SHALL be part of it.

#### Scenario: Demos in the LLM export
- **WHEN** `/llms-full.txt` is requested
- **THEN** it contains the descriptions of the features and the abilities of an agent from the home page
- **AND** it contains none of the terminal sessions and conversations of the demo windows

### Requirement: Optimized images, screen recordings and stable static files

Images shown on pages SHALL be emitted through the build's image optimization with width and height attributes; image files that no page references SHALL NOT be published. Screen recordings SHALL be shown as videos with width and height attributes that play by themselves, muted and in a loop. Files served unchanged at fixed URLs — the favicon, the Open Graph image and `/schemas/robot.toml.json` — SHALL keep their URLs.

#### Scenario: Screenshot on the Neovim page
- **WHEN** `/getting-started/neovim/` is built
- **THEN** its screenshot is served from an optimized image file with width and height attributes

#### Scenario: Screen recordings on the VS Code page
- **WHEN** `/getting-started/vscode/` is built
- **THEN** its screen recordings are videos with width and height attributes that play by themselves, muted and in a loop

#### Scenario: JSON schema URL
- **WHEN** an editor requests `/schemas/robot.toml.json`
- **THEN** it receives the current JSON schema for `robot.toml`

### Requirement: Pictures of the home page

Previous and next buttons and a horizontal swipe on the picture of the home page SHALL switch to the neighbouring picture. Clicking the picture SHALL open an enlarged view that closes on a click or Escape and in which the left and right arrow keys switch pictures.

#### Scenario: Next button
- **WHEN** a reader presses the next button of the picture
- **THEN** the next picture of the artwork is shown

### Requirement: Sections below the hero

Below the hero the home page SHALL show, in this order, the feature tour, the AI agents section, the RoboCon 2024 tutorial video, the latest news and the open-source section. On a viewport of 1366×768 or larger, the beginning of the feature tour SHALL be visible without scrolling.

#### Scenario: Larger window
- **WHEN** the home page is opened in a 1920×1080 browser window
- **THEN** the beginning of the feature tour is visible without scrolling

### Requirement: Feature tour on the home page

The feature tour SHALL list Code intelligence; Run, debug & test explorer; One config everywhere; Powerful CLI; Interactive REPL; and Multi-IDE, same core as feature cards, each with its description and links to the pages that cover it, next to a demo of the selected feature: screen recordings for code intelligence and for running and debugging tests, terminal sessions for the configuration, the CLI and the REPL, and screenshots of RobotCode in several editors for Multi-IDE.

#### Scenario: Demo of a feature card
- **WHEN** a reader selects the "Powerful CLI" feature card in the feature tour
- **THEN** its description and links are shown next to the demo of the CLI

### Requirement: AI agents section on the home page

The AI agents section SHALL describe what an AI agent does with the RobotCode skill, name the agents it works with, link to the setup guide `/guides/ai-agents/` and show conversations of an agent working through `robotcode`.

#### Scenario: Agent conversations
- **WHEN** a reader views the AI agents section of the home page
- **THEN** it names the agents the skill works with and shows conversations of an agent working through `robotcode`

### Requirement: Latest news and open source on the home page

The latest news SHALL list the three newest posts, newest first, with date, title and description, and link to all news. The open-source section SHALL state the license, link to the GitHub repository, to Support & Contribute and to the sponsoring options, and show the supporters.

#### Scenario: All news
- **WHEN** a reader follows the link to all news in the latest news of the home page
- **THEN** `/news/` is shown

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

## REMOVED Requirements

### Requirement: Optimized images and stable static files

**Reason**: Its scenario expects screenshots on `/getting-started/vscode/`, which shows screen recordings as videos since the switch (design D8).

**Migration**: Replaced by "Optimized images, screen recordings and stable static files", which keeps the image and static file rules and adds the recordings.
