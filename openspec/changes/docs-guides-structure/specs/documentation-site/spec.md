# Spec Delta

## MODIFIED Requirements

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

### Requirement: Build fails on broken internal links

The site build SHALL fail when a page links to a page of the site that does not exist or to an anchor that does not exist on the target page, and SHALL name the page and the link.

#### Scenario: Missing page
- **WHEN** a page links to `/reference/does-not-exist/`
- **THEN** the build fails and names the linking page and the link

#### Scenario: Missing anchor
- **WHEN** a page links to `/guides/cli/robot-debug/#no-such-heading`
- **THEN** the build fails and names the linking page and the link

### Requirement: LLM text exports

The site SHALL publish `/llms.txt`, an index that lists every documentation page with its title, URL and description, and `/llms-full.txt`, the complete documentation as plain text.

#### Scenario: Page index
- **WHEN** `/llms.txt` is requested
- **THEN** the response lists `/guides/cli/repl/` with its title and description

#### Scenario: Full export
- **WHEN** `/llms-full.txt` is requested
- **THEN** the response contains the text of the CLI reference and of the configuration reference

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

### Requirement: Pages sorted into areas

Pages for setting up an editor or tool and a first project SHALL be in Getting Started, pages that explain a task or a RobotCode tool SHALL be in Guides, and Reference SHALL contain only material to look up without task narrative, such as the CLI and `robot.toml` references and the diagnostic-modifier syntax.

#### Scenario: Guide to a RobotCode tool
- **WHEN** a reader opens `/guides/cli/analyzing-code/`
- **THEN** the guide to `robotcode analyze code` is shown

## ADDED Requirements

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
