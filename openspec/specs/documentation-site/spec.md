# Spec: documentation-site

## Purpose

Defines what RobotCode's Starlight documentation site offers its readers and what its build guarantees: where pages live, how readers navigate and find them, what each page carries, and which checks keep its links intact. Paths are relative to the root of the site.

## Requirements

### Requirement: Descriptive page paths without legacy URLs

The site SHALL serve the home page at `/` and every other page at a descriptive path without numeric prefixes that names its area: `/about/`, `/getting-started/` and `/getting-started/<page>/`, `/guides/` and `/guides/<page>/`, `/reference/` and `/reference/<page>/`, `/contributing/` and `/news/<post>/`.

#### Scenario: Configuration reference path
- **WHEN** a reader opens `/reference/config/`
- **THEN** the robot.toml configuration reference is shown

#### Scenario: Guide that used to be in Reference
- **WHEN** a reader opens `/guides/repl/`
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
- **WHEN** a reader opens `/reference/cli/`, `/guides/repl/` or `/getting-started/vscode/`
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
- **THEN** the Getting Started group lists Overview first and Configuration after the editor pages

#### Scenario: News sidebar
- **WHEN** a reader opens a news post
- **THEN** the sidebar lists news posts and tags and no documentation pages

### Requirement: Page title and description

Every page SHALL declare a title and a one-sentence description. The title SHALL be rendered as the page's only top-level heading. The description SHALL be emitted as the page's meta description and Open Graph description. Every page SHALL emit its own URL as canonical and Open Graph URL.

#### Scenario: Meta description
- **WHEN** `/guides/repl/` is built
- **THEN** its meta description is the description declared by the page

#### Scenario: Page URL in Open Graph
- **WHEN** `/guides/repl/` is built
- **THEN** its canonical link and `og:url` are `https://robotcode.io/guides/repl/`

### Requirement: Area overview pages

The overview pages of the Getting Started area (`/getting-started/`), the Guides area (`/guides/`) and the Reference area (`/reference/`) SHALL list every other page of their area as a link card with the page's title and description, in sidebar order. The Getting Started overview SHALL also state the requirements for using RobotCode.

#### Scenario: Complete overview
- **WHEN** the site is built
- **THEN** `/reference/` contains one link card for each page of the Reference area, showing that page's declared title and description

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

### Requirement: Optimized images and stable static files

Images shown on pages SHALL be emitted through the build's image optimization with width and height attributes; image files that no page references SHALL NOT be published. Files served unchanged at fixed URLs — the favicon, the Open Graph image and `/schemas/robot.toml.json` — SHALL keep their URLs.

#### Scenario: Screenshot on the VS Code page
- **WHEN** `/getting-started/vscode/` is built
- **THEN** its screenshots are served from optimized image files with width and height attributes

#### Scenario: JSON schema URL
- **WHEN** an editor requests `/schemas/robot.toml.json`
- **THEN** it receives the current JSON schema for `robot.toml`

### Requirement: Build fails on broken internal links

The site build SHALL fail when a page links to a page of the site that does not exist or to an anchor that does not exist on the target page, and SHALL name the page and the link.

#### Scenario: Missing page
- **WHEN** a page links to `/reference/does-not-exist/`
- **THEN** the build fails and names the linking page and the link

#### Scenario: Missing anchor
- **WHEN** a page links to `/guides/robot-debug/#no-such-heading`
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
- **THEN** the response lists `/guides/repl/` with its title and description

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

The home page SHALL show the product name and tagline, one picture of the RobotCode artwork chosen at random on each load, a subline chosen at random, actions to get started and to install the VS Code and JetBrains extensions, links to the GitHub repository and to sponsoring, the feature overview, the RoboCon 2024 tutorial video, the sponsoring options and the supporters. Previous and next buttons and a horizontal swipe on the picture SHALL switch to the neighbouring picture. Clicking the picture SHALL open an enlarged view that closes on a click or Escape and in which the left and right arrow keys switch pictures. Every feature card that links to a page SHALL link to the page that covers the feature.

#### Scenario: Random picture
- **WHEN** the home page is loaded
- **THEN** one picture of the RobotCode artwork is shown next to the product name
- **AND** the actions Get Started, Install VS Code and Install JetBrains are offered

#### Scenario: Browsing the pictures
- **WHEN** a reader swipes left on the picture, or clicks it and presses the right arrow key
- **THEN** the next picture is shown, in the enlarged view in the second case
- **AND** Escape closes the enlarged view

#### Scenario: Feature card target
- **WHEN** a reader follows the link of the "REPL & notebooks" feature card
- **THEN** the REPL guide `/guides/repl/` is shown

### Requirement: Not-found page

A request for a path the site does not serve SHALL receive a not-found page that explains that this documentation keeps evolving, so pages and links can move, and that offers the search and links to Getting Started, Guides, Reference and News.

#### Scenario: Moved page
- **WHEN** a reader follows a link to a page that no longer exists
- **THEN** the not-found page explains that content can move and offers the search and the links to the main areas

### Requirement: Pages sorted into areas

Pages for setting up an editor or tool and a first project SHALL be in Getting Started, pages that explain a task or a RobotCode tool SHALL be in Guides, and Reference SHALL contain only material to look up without task narrative, such as the CLI and `robot.toml` references and the diagnostic-modifier syntax.

#### Scenario: Guide to a RobotCode tool
- **WHEN** a reader opens `/guides/analyzing-code/`
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
