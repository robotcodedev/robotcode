# Spec Delta

## MODIFIED Requirements

### Requirement: VS Code group in the Guides area

The Guides area SHALL contain a group labelled "VS Code" that follows the Guides overview directly in the sidebar. It SHALL contain, in this order, the pages Overview, Writing code, Finding information, Documentation Viewer, Test Explorer, Running and debugging, Configuration, Highlighting, Diagnostics and linting, REPL and Troubleshooting under `/guides/vscode/`. The setup page `/getting-started/vscode/` SHALL link to the group.

#### Scenario: Group in the sidebar
- **WHEN** a reader opens any page of the Guides area
- **THEN** the sidebar shows the group "VS Code" right after the Guides overview
- **AND** the group lists Overview first and Troubleshooting last

#### Scenario: Group address
- **WHEN** a reader opens `/guides/vscode/`
- **THEN** the overview page of the group is shown

#### Scenario: From the setup to the group
- **WHEN** a reader reaches the end of `/getting-started/vscode/`
- **THEN** a link leads to `/guides/vscode/`

### Requirement: Overview of the VS Code window

The overview page SHALL show a screenshot of the whole VS Code window with numbered markers and, below it, a list with the same numbers that names each marked part: the editor, the Test Explorer, the Keywords view, the language status items of RobotCode, the output channels and the Command Palette. The page SHALL list RobotCode's commands and link to every other page of the group.

#### Scenario: Marked window
- **WHEN** a reader opens `/guides/vscode/`
- **THEN** a screenshot of the whole window with numbered markers is shown
- **AND** the numbered list below it names the marked parts with the same numbers

#### Scenario: Commands of RobotCode
- **WHEN** a reader looks up a command on `/guides/vscode/`
- **THEN** the page lists every command titled "RobotCode: …" in the extension's command list, except the notebook commands, with what it does

#### Scenario: Pages of the group
- **WHEN** a reader opens `/guides/vscode/`
- **THEN** link cards lead to the other ten pages of the group

### Requirement: Writing code in VS Code

The page Writing code SHALL show with screenshots how RobotCode helps while writing Robot Framework code: completion, signature help, hover, inlay hints, semantic highlighting, quick fixes, rename and formatting, and how to create a new Robot Framework file. It SHALL link to the page Highlighting for experienced users.

#### Scenario: Completion
- **WHEN** a reader opens `/guides/vscode/writing-code/`
- **THEN** a screenshot shows the completion list with the documentation of the selected keyword

#### Scenario: Quick fix
- **WHEN** a reader opens `/guides/vscode/writing-code/`
- **THEN** the page shows the quick fix Create Keyword on a call of a keyword that does not exist

#### Scenario: Highlighting tip
- **WHEN** a reader opens `/guides/vscode/writing-code/`
- **THEN** a link leads to `/guides/vscode/highlighting/`

### Requirement: Documentation Viewer page

The page Documentation Viewer SHALL describe the Documentation Viewer with the content of the former section "VS Code" of the `robotcode doc` guide, with screenshots and a screen recording of a viewer in use. That guide SHALL keep only a short section that links to the page, and the home page's feature tour SHALL link to the page for the Documentation Viewer.

#### Scenario: Viewer page
- **WHEN** a reader opens `/guides/vscode/documentation-viewer/`
- **THEN** it explains how to open a viewer, the target field with its place and its suggestions, the bookmarks with the view Documentation Bookmarks, the outline with its context menu and filter, links, find, arranging viewers and Open as Markdown
- **AND** a screen recording shows a viewer in use

#### Scenario: Guide without the viewer's description
- **WHEN** a reader opens `/guides/cli/browsing-documentation/`
- **THEN** its section "VS Code" holds only a short paragraph with a link to `/guides/vscode/documentation-viewer/`

#### Scenario: Feature tour link
- **WHEN** a reader follows the Documentation Viewer link of the Code intelligence feature on the home page
- **THEN** `/guides/vscode/documentation-viewer/` is shown

### Requirement: REPL in VS Code

The page REPL SHALL explain how to start the REPL of RobotCode in the terminal of VS Code and link to the REPL guide for its features. No page of the group SHALL describe Robot Framework notebooks or their commands.

#### Scenario: Terminal REPL
- **WHEN** a reader opens `/guides/vscode/repl/`
- **THEN** a screenshot shows the REPL started with "RobotCode: Start Terminal REPL"
- **AND** a link leads to `/guides/cli/repl/`

#### Scenario: No notebooks
- **WHEN** the pages of the group are built
- **THEN** none of them mentions Robot Framework notebooks or the commands "RobotCode: New Robot Framework Notebook" and "RobotCode: Restart Kernel"

## ADDED Requirements

### Requirement: Highlighting in VS Code

The page Highlighting SHALL explain the font styles that RobotCode sets for Robot Framework code in VS Code and how to change them with token color rules in the settings, for experienced users.

#### Scenario: Changing a font style
- **WHEN** a reader opens `/guides/vscode/highlighting/`
- **THEN** the page shows a token color rule in `settings.json` that changes a font style RobotCode sets
