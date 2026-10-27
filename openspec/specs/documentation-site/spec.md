# Spec: documentation-site

## Purpose

Defines what RobotCode's Starlight documentation site offers its readers and what its build guarantees: where pages live, how readers navigate and find them, what each page carries, and which checks keep its links intact. Paths are relative to the root of the site.

## Requirements

### Requirement: Descriptive page paths without legacy URLs

The site SHALL serve the home page at `/` and every other page at a descriptive path without numeric prefixes that names its area: `/about/`, `/getting-started/` and `/getting-started/<page>/`, `/guides/`, `/guides/<page>/` and `/guides/<group>/<page>/`, `/reference/` and `/reference/<page>/`, `/contributing/` and `/news/<post>/`.

#### Scenario: Configuration reference path
- **WHEN** a reader opens `/reference/config/`
- **THEN** the robot.toml configuration reference is shown

#### Scenario: Guide that used to be in Reference
- **WHEN** a reader opens `/guides/cli/repl/`
- **THEN** the guide to `robotcode repl` is shown

#### Scenario: Editor setup
- **WHEN** a reader opens `/getting-started/vscode/`
- **THEN** the walkthrough for setting up RobotCode in VS Code is shown

#### Scenario: News post path
- **WHEN** a reader opens `/news/v2-7-0/`
- **THEN** the release post for RobotCode 2.7.0 is shown

#### Scenario: Old path
- **WHEN** a reader opens `/03_reference/config`
- **THEN** the site's not-found page is returned

### Requirement: Top navigation on every page

Every page, including the home page, SHALL show a navigation bar with the entries News, Documentation, Support & Contribute, Q&A (a link to the Q&A category of the GitHub Discussions) and a version menu labelled with the current RobotCode version that links to the changelog and the contributing guide. The entry of the area the current page belongs to SHALL be marked as current. The site title in the header SHALL link to the home page.

#### Scenario: Current area
- **WHEN** a reader opens `/reference/cli/`, `/guides/cli/repl/` or `/getting-started/vscode/`
- **THEN** the navigation bar marks Documentation as current

#### Scenario: Documentation entry
- **WHEN** a reader selects Documentation in the navigation bar
- **THEN** the Getting Started overview `/getting-started/` is shown

#### Scenario: News area
- **WHEN** a reader opens any page under `/news/`
- **THEN** the navigation bar marks News as current

#### Scenario: Narrow viewport
- **WHEN** a page is shown 390 pixels wide
- **THEN** a compact menu offers News, Documentation, Support & Contribute, Q&A, Changelog and Contributing

#### Scenario: Back to the home page
- **WHEN** a reader selects the site title in the header of any page
- **THEN** the home page is shown

### Requirement: Area sidebar

Documentation pages SHALL show a sidebar with About, the groups Getting Started, Guides and Reference, and Support & Contribute. Inside a group, pages SHALL appear in the order each page declares and under the short label each page declares. Pages under `/news/` SHALL show the news sidebar (posts, tags, feed) instead of the documentation page tree. The home page SHALL have no sidebar.

#### Scenario: Reference group
- **WHEN** a reader opens any page of the Reference area
- **THEN** the Reference group lists Overview, CLI and robot.toml first, in this order

#### Scenario: Getting Started group
- **WHEN** a reader opens any page of the Getting Started area
- **THEN** the Getting Started group lists Overview first and Configuration after the editor pages and the command-line page

#### Scenario: News sidebar
- **WHEN** a reader opens a news post
- **THEN** the sidebar lists news posts and tags and no documentation pages

### Requirement: Page title and description

Every page SHALL declare a title and a one-sentence description. The title SHALL be rendered as the page's only top-level heading. The description SHALL be emitted as the page's meta description and Open Graph description. Every page SHALL emit its own URL as canonical and Open Graph URL.

#### Scenario: Meta description
- **WHEN** `/guides/cli/repl/` is built
- **THEN** its meta description is the description declared by the page

#### Scenario: Page URL in Open Graph
- **WHEN** `/guides/cli/repl/` is built
- **THEN** its canonical link and `og:url` are `https://robotcode.io/guides/cli/repl/`

### Requirement: Area overview pages

The overview pages of the Getting Started area (`/getting-started/`), the Guides area (`/guides/`) and the Reference area (`/reference/`) SHALL list every other page of their area as a link card with the page's title and description, in sidebar order. A group of pages inside an area SHALL be listed as one link card to the group's first page, which SHALL list the other pages of the group the same way. The Getting Started overview SHALL also state the requirements for using RobotCode.

#### Scenario: Complete overview
- **WHEN** the site is built
- **THEN** `/reference/` contains one link card for each page of the Reference area, showing that page's declared title and description

#### Scenario: Group inside an area
- **WHEN** the site is built
- **THEN** `/guides/` contains one link card to `/guides/vscode/` and no link card to another page of the VS Code group
- **AND** `/guides/vscode/` contains one link card for each other page of the group

### Requirement: News posts, tags and feed

News posts SHALL carry a publication date, exactly one kind tag (`release`, `april-fools` or `tips`) and topic tags from the site's documented tag vocabulary. `/news/` SHALL list the posts newest first, each with its title, date, author and excerpt, split into pages of a fixed maximum number of posts. Every tag SHALL have a page that lists its posts. The site SHALL publish an RSS feed of the posts at `/news/rss.xml`.

#### Scenario: Post list
- **WHEN** a reader opens `/news/`
- **THEN** the newest post is listed first, with its excerpt and not its full text

#### Scenario: Feed
- **WHEN** a feed reader requests `/news/rss.xml`
- **THEN** it receives an RSS feed whose first item is the newest post

#### Scenario: Tag page
- **WHEN** a reader follows the tag of a post
- **THEN** a page lists all posts with that tag

#### Scenario: Release tag
- **WHEN** a reader opens the page of the tag `release`
- **THEN** it lists the release announcements and not the April Fools post

#### Scenario: Joke post
- **WHEN** a reader or an agent reads the April Fools post, on its page or in `/llms-full.txt`
- **THEN** its first paragraph says that the post is a joke and that its features do not exist

### Requirement: Build fails on broken internal links

The site build SHALL fail when a page links to a page of the site that does not exist or to an anchor that does not exist on the target page, and SHALL name the page and the link.

#### Scenario: Missing page
- **WHEN** a page links to `/reference/does-not-exist/`
- **THEN** the build fails and names the linking page and the link

#### Scenario: Missing anchor
- **WHEN** a page links to `/guides/cli/robot-debug/#no-such-heading`
- **THEN** the build fails and names the linking page and the link

### Requirement: Command-line text stays literal

Prose SHALL be rendered without typographic replacements: double hyphens, straight quotes and three consecutive dots SHALL appear exactly as written.

#### Scenario: Option names in prose
- **WHEN** a page contains `--include` outside a code span
- **THEN** it is rendered as `--include` and not with an en dash

### Requirement: Code blocks

Code blocks tagged `robot` or `robotframework` SHALL be highlighted with RobotCode's Robot Framework grammar in the light and the dark theme. Every code block SHALL offer a copy button. A code block MAY carry a title that is shown above it, and single lines MAY be marked as inserted, removed or highlighted.

#### Scenario: Robot Framework code
- **WHEN** a page contains a code block tagged `robot` with a `*** Test Cases ***` section
- **THEN** the section header, test name and keyword calls are highlighted according to RobotCode's grammar

### Requirement: Search

Every page SHALL offer a full-text search over all pages of the site whose results link to the matching page section.

#### Scenario: Setting name
- **WHEN** a reader searches for `console-colors`
- **THEN** the results include the section of the configuration reference that describes the setting

### Requirement: LLM text exports

The site SHALL publish `/llms.txt`, an index that lists every documentation page with its title, URL and description, and `/llms-full.txt`, the complete documentation as plain text.

#### Scenario: Page index
- **WHEN** `/llms.txt` is requested
- **THEN** the response lists `/guides/cli/repl/` with its title and description

#### Scenario: Full export
- **WHEN** `/llms-full.txt` is requested
- **THEN** the response contains the text of the CLI reference and of the configuration reference

### Requirement: Edit link and last change

Every documentation page except the home page SHALL link to the file in the GitHub repository that holds its content, for editing, and SHALL show the date of that file's last change in the repository history.

#### Scenario: Edit link
- **WHEN** a reader opens `/getting-started/neovim/`
- **THEN** the page links to the file on GitHub that holds the page's content
- **AND** it shows the date of that file's last commit

### Requirement: Home page

The home page SHALL show the product name, the tagline, a subline and a picture of the RobotCode artwork, both chosen at random on each load, the actions Get Started, VS Code Extension, JetBrains Plugin, Star on GitHub and Sponsor, and a note that RobotCode is free and open source, leading to the open-source section, but no edit link and no last-change date. During a site season with its own pictures, the gallery SHALL hold only those, the first chosen at random, and none of them outside it.

#### Scenario: Random picture
- **WHEN** the home page is loaded
- **THEN** one picture of the RobotCode artwork is shown next to the product name
- **AND** the actions Get Started, VS Code Extension and JetBrains Plugin are offered

#### Scenario: Season pictures
- **WHEN** the home page is loaded during the Halloween season and the site has Halloween pictures
- **THEN** one of the Halloween pictures, chosen at random, is shown next to the product name
- **AND** the next button switches only between the Halloween pictures

#### Scenario: Browsing the pictures
- **WHEN** a reader swipes left on the picture, or clicks it and presses the right arrow key
- **THEN** the next picture is shown, in the enlarged view in the second case
- **AND** Escape closes the enlarged view

#### Scenario: Feature card target
- **WHEN** a reader selects the "Interactive REPL" feature card in the feature tour and follows its link
- **THEN** the REPL guide `/guides/cli/repl/` is shown

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

### Requirement: Home page gallery moves on by itself

The gallery next to the title of the home page SHALL move on to the next picture by itself every eight seconds, fading over to it. It SHALL NOT move on while the pointer or the keyboard focus is on it, while the enlarged view is open or while the browser tab is hidden, and not at all when the visitor's system asks for reduced motion. After the reader changes the picture, the new picture SHALL be shown for the full eight seconds.

#### Scenario: Moving on by itself
- **WHEN** a reader looks at the home page for eight seconds without touching the gallery
- **THEN** the gallery fades over to the next picture

#### Scenario: Pointer on the picture
- **WHEN** the pointer rests on the picture
- **THEN** the gallery stays on that picture

#### Scenario: Enlarged view
- **WHEN** the reader has opened the enlarged view
- **THEN** the gallery stays on the picture until the view is closed

#### Scenario: Change by hand
- **WHEN** the reader clicks the next button
- **THEN** the next picture is shown for the full eight seconds before the gallery moves on

#### Scenario: Reduced motion
- **WHEN** a visitor whose system asks for reduced motion opens the home page
- **THEN** the picture changes only when the visitor changes it

### Requirement: Not-found page

A request for a path the site does not serve SHALL receive a not-found page that explains that this documentation keeps evolving, so pages and links can move, and that offers the search and links to Getting Started, Guides, Reference and News.

#### Scenario: Moved page
- **WHEN** a reader follows a link to a page that no longer exists
- **THEN** the not-found page explains that content can move and offers the search and the links to the main areas

### Requirement: Pages sorted into areas

Pages for setting up an editor or tool and a first project SHALL be in Getting Started, pages that explain a task or a RobotCode tool SHALL be in Guides, and Reference SHALL contain only material to look up without task narrative, such as the CLI and `robot.toml` references and the diagnostic-modifier syntax.

#### Scenario: Guide to a RobotCode tool
- **WHEN** a reader opens `/guides/cli/analyzing-code/`
- **THEN** the guide to `robotcode analyze code` is shown

### Requirement: No paths of the previous site

The paths of the previous site (`/01_about`, `/02_get_started/…`, `/03_reference/…`, `/04_tip_and_tricks/…`, `/05_contributing/`, `/news/<date>-whats-new-…`) SHALL NOT be served and SHALL NOT redirect; a request for them SHALL receive the site's not-found page.

#### Scenario: Old about page
- **WHEN** a reader opens `/01_about`
- **THEN** the site's not-found page is returned, without a redirect

### Requirement: Navigation on narrow viewports

On narrow viewports all entries of the navigation bar SHALL remain reachable through a compact menu.

#### Scenario: Version menu on a narrow viewport
- **WHEN** a page is shown 390 pixels wide
- **THEN** the links of the version menu to the changelog and the contributing guide are reachable through the compact menu

### Requirement: April Fools posts say they are jokes

A post tagged `april-fools` SHALL state at its top that it is a joke and that the features it describes do not exist.

#### Scenario: Top of an April Fools post
- **WHEN** a reader opens a post tagged `april-fools`
- **THEN** its top states that the post is a joke and that the features it describes do not exist

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

The feature tour SHALL list Code intelligence; Run, debug & test explorer; One config everywhere; Powerful CLI; Interactive REPL; and Multi-IDE, same core as feature cards, each with its description and links to the pages that cover it, next to a demo window that shows examples of the selected feature.

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

### Requirement: Guides grouped by tool and topic

The Guides sidebar SHALL list, in this order, the overview, the groups VS Code, PyCharm and Command Line, the page AI Agents, the group Project Configuration, the page Finding Robot Files, and the group Robot Framework Tips. Every other guide SHALL be a page of one of these groups, at a path under the group's path. The groups SHALL be shown collapsed, except the group that contains the open page.

#### Scenario: Order in the sidebar
- **WHEN** a reader opens `/guides/`
- **THEN** the sidebar lists Overview, VS Code, PyCharm, Command Line, AI Agents, Project Configuration, Finding Robot Files and Robot Framework Tips in this order
- **AND** every group is collapsed

#### Scenario: Names by subject
- **WHEN** a reader looks for the guides to `robot.toml` and to `.robotignore` in the sidebar
- **THEN** they are listed as the group Project Configuration, at `/guides/robot-toml/`, and the page Finding Robot Files, at `/guides/ignoring-files/`

#### Scenario: Group of the open page
- **WHEN** a reader opens `/guides/cli/repl/`
- **THEN** the group Command Line is expanded and marks REPL as the current page
- **AND** the other groups are collapsed

#### Scenario: Command Line group
- **WHEN** a reader opens `/guides/cli/`
- **THEN** the overview of the group is shown
- **AND** link cards lead to the guides to `discover`, `analyze code`, `results`, `repl`, `robot-debug`, `doc` and running tests through a wrapper

#### Scenario: Robot Framework Tips group
- **WHEN** a reader opens `/guides/tips/`
- **THEN** the overview of the group is shown
- **AND** link cards lead to the pages on avoiding a global resource file and on variables shown as not found

#### Scenario: Path of a moved guide
- **WHEN** a reader opens `/guides/repl/`
- **THEN** the site's not-found page is returned, without a redirect

### Requirement: Overview of the command line

The overview page of the Command Line group SHALL say that the `robotcode` commands run in the project's Python environment and read the project's `robot.toml` files and profiles, as the editors do. For each everyday task it SHALL name the command and link to the guide for it; for running tests, to the guide to `robot.toml` on the command line.

#### Scenario: Running tests
- **WHEN** a reader looks up on `/guides/cli/` how to run tests
- **THEN** the page names `robotcode robot`
- **AND** it links to `/guides/robot-toml/command-line/`

#### Scenario: Results of a run
- **WHEN** a reader looks up on `/guides/cli/` how to see why a test failed in the last run
- **THEN** the page names `robotcode results`
- **AND** it links to `/guides/cli/analyzing-results/`

### Requirement: Getting started on the command line

Getting Started SHALL have a page that sets RobotCode up for the command line: which package each command needs, installing the packages into the project's Python environment with pip or uv, checking the installed version, and a first look at the project and a first run with `robotcode`. It SHALL lead on to the configuration page and to the Command Line group. The README's section on the command line SHALL link to it.

#### Scenario: Page in Getting Started
- **WHEN** a reader opens `/getting-started/command-line/`
- **THEN** the page is shown
- **AND** the Getting Started sidebar lists it after PyCharm and before Neovim

#### Scenario: Packages for a CI run
- **WHEN** a reader wants to run the tests of their project in a CI pipeline
- **THEN** the page names the package `robotcode[runner]` and shows how to install it with pip and with uv

#### Scenario: Next steps
- **WHEN** a reader reaches the end of `/getting-started/command-line/`
- **THEN** links lead to `/getting-started/configuration/` and to `/guides/cli/`

#### Scenario: README link
- **WHEN** a reader reads the section "Command Line and Other Editors" of the README
- **THEN** it links to `https://robotcode.io/getting-started/command-line/`
