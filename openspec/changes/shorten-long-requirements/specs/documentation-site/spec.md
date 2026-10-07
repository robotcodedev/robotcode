# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
