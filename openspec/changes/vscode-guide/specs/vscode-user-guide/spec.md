# Spec Delta

## Purpose

The pages of the documentation site that teach working with RobotCode in VS Code — the window, writing and navigating code, the Documentation Viewer, the Test Explorer, running and debugging, configuration, diagnostics, the REPL and troubleshooting — and the screenshots and screen recordings on them.

## ADDED Requirements

### Requirement: VS Code group in the Guides area

The Guides area SHALL contain a group labelled "VS Code" that follows the Guides overview directly in the sidebar. It SHALL contain, in this order, the pages Overview, Writing code, Finding information, Documentation Viewer, Test Explorer, Running and debugging, Configuration, Diagnostics and linting, REPL and Troubleshooting under `/guides/vscode/`. The setup page `/getting-started/vscode/` SHALL link to the group.

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
- **THEN** link cards lead to the other nine pages of the group

### Requirement: Writing code in VS Code

The page Writing code SHALL show with screenshots how RobotCode helps while writing Robot Framework code: completion, signature help, hover, inlay hints, semantic highlighting, quick fixes, rename and formatting, and how to create a new Robot Framework file. It SHALL link to the highlighting tip for experienced users, which stays a page of its own outside the group.

#### Scenario: Completion
- **WHEN** a reader opens `/guides/vscode/writing-code/`
- **THEN** a screenshot shows the completion list with the documentation of the selected keyword

#### Scenario: Quick fix
- **WHEN** a reader opens `/guides/vscode/writing-code/`
- **THEN** the page shows the quick fix Create Keyword on a call of a keyword that does not exist

#### Scenario: Highlighting tip
- **WHEN** a reader opens `/guides/vscode/writing-code/`
- **THEN** a link leads to `/guides/vscode-highlighting/`

### Requirement: Finding information in VS Code

The page Finding information SHALL explain with screenshots how to go from a keyword call or a variable to its definition, also into the Python code of a library; how to find references, also through CodeLens; how to use the outline and the workspace symbols; and how the Keywords view lists the keywords a file can use and inserts one or shows its documentation.

#### Scenario: Into a library
- **WHEN** a reader opens `/guides/vscode/finding-information/`
- **THEN** a screenshot shows Go to Definition opening the Python source of a library keyword

#### Scenario: Keywords view
- **WHEN** a reader opens `/guides/vscode/finding-information/`
- **THEN** a screenshot shows the Keywords view
- **AND** the page explains its actions Insert Keyword and Show in Documentation Viewer

### Requirement: Documentation Viewer page

The page Documentation Viewer SHALL describe the Documentation Viewer with the content of the former section "VS Code" of the `robotcode doc` guide, with screenshots and a screen recording of a viewer in use. That guide SHALL no longer contain the section and SHALL link to the page instead, and so SHALL the home page's feature tour for the Documentation Viewer.

#### Scenario: Viewer page
- **WHEN** a reader opens `/guides/vscode/documentation-viewer/`
- **THEN** it explains how to open a viewer, the outline and filter, links, find, arranging viewers and Open as Markdown
- **AND** a screen recording shows a viewer in use

#### Scenario: Guide without the section
- **WHEN** a reader opens `/guides/browsing-documentation/`
- **THEN** the page has no section about VS Code
- **AND** a link leads to `/guides/vscode/documentation-viewer/`

#### Scenario: Feature tour link
- **WHEN** a reader follows the Documentation Viewer link of the Code intelligence feature on the home page
- **THEN** `/guides/vscode/documentation-viewer/` is shown

### Requirement: Test Explorer in VS Code

The page Test Explorer SHALL explain with screenshots how tests and tasks get into the Test Explorer and when it updates, how its tree follows the workspace folders and suites, how to filter it by text and by tags, which run profiles RobotCode offers there, how results and failures are shown, how errors of a suite and of the discovery appear, and how to switch the Test Explorer off.

#### Scenario: Where the tests come from
- **WHEN** a reader opens `/guides/vscode/test-explorer/`
- **THEN** the page explains that the Test Explorer shows what `robotcode discover` finds with the project's `robot.toml` and `.robotignore`
- **AND** that it updates when a file is changed, saved, created or deleted

#### Scenario: Run profiles
- **WHEN** a reader opens `/guides/vscode/test-explorer/`
- **THEN** the page names the run profiles RobotCode creates: Run and Debug for each workspace folder, whose configure button selects configuration profiles; a Run and a Debug profile for each profile of `robot.toml`; and a Run and a Debug profile for each `launch.json` configuration with the purpose `test-profile`

#### Scenario: Failed test
- **WHEN** a reader opens `/guides/vscode/test-explorer/`
- **THEN** a screenshot shows the Test Explorer with passed and failed tests and the failure message of a failed test at the line that failed

#### Scenario: Switching it off
- **WHEN** a reader opens `/guides/vscode/test-explorer/`
- **THEN** the page names the setting `robotcode.testExplorer.enabled` and links to its entry in the settings reference

### Requirement: Running and debugging in VS Code

The page Running and debugging SHALL explain with screenshots how to run and debug tests from the editor, with the icons beside the tests and with Run or Debug Current File, the `launch.json` configurations RobotCode offers, breakpoints, the Debug Console and inline values, how to open the log after a run, and how to choose the configuration profiles for a run. It SHALL link to the Test Explorer page.

#### Scenario: Icons beside the tests
- **WHEN** a reader opens `/guides/vscode/running-and-debugging/`
- **THEN** a screenshot shows the icons beside the tests in the editor that run or debug a test

#### Scenario: Link to the Test Explorer page
- **WHEN** a reader opens `/guides/vscode/running-and-debugging/`
- **THEN** a link leads to `/guides/vscode/test-explorer/`

#### Scenario: Launch configurations
- **WHEN** a reader opens `/guides/vscode/running-and-debugging/`
- **THEN** the page names every `launch.json` configuration RobotCode offers and what it is for

#### Scenario: Profiles for a run
- **WHEN** a reader opens `/guides/vscode/running-and-debugging/`
- **THEN** the page shows how to choose configuration profiles with "RobotCode: Select Configuration Profiles"

### Requirement: Configuration in VS Code

The page Configuration SHALL explain where a setting belongs: in `robot.toml`, in the user or workspace settings of VS Code, or in the settings of a workspace folder. It SHALL show how to select the Python environment and the configuration profiles, explain how RobotCode handles several workspace folders, and link to the VS Code settings reference.

#### Scenario: Where a setting belongs
- **WHEN** a reader opens `/guides/vscode/configuration/`
- **THEN** the page explains that `robot.toml` holds the options shared by runs in every editor and on the command line, and names the settings that exist only in VS Code

#### Scenario: Python environment
- **WHEN** a reader opens `/guides/vscode/configuration/`
- **THEN** a screenshot shows how to select the Python environment

#### Scenario: Settings reference
- **WHEN** a reader opens `/guides/vscode/configuration/`
- **THEN** a link leads to `/reference/vscode-settings/`

### Requirement: Diagnostics and linting in VS Code

The page Diagnostics and linting SHALL explain with screenshots where RobotCode's diagnostics appear, how to enable and disable Robocop, how to change the severity of a diagnostic or hide it with diagnostic modifiers, how to report unused keywords and variables, and when to clear the analysis cache.

#### Scenario: Problems
- **WHEN** a reader opens `/guides/vscode/diagnostics-and-linting/`
- **THEN** a screenshot shows diagnostics of RobotCode in the editor and in the Problems view

#### Scenario: Modifiers
- **WHEN** a reader opens `/guides/vscode/diagnostics-and-linting/`
- **THEN** a link leads to `/reference/diagnostics-modifiers/`

### Requirement: REPL in VS Code

The page REPL SHALL explain how to start the REPL of RobotCode in the terminal of VS Code and link to the REPL guide for its features. No page of the group SHALL describe Robot Framework notebooks or their commands.

#### Scenario: Terminal REPL
- **WHEN** a reader opens `/guides/vscode/repl/`
- **THEN** a screenshot shows the REPL started with "RobotCode: Start Terminal REPL"
- **AND** a link leads to `/guides/repl/`

#### Scenario: No notebooks
- **WHEN** the pages of the group are built
- **THEN** none of them mentions Robot Framework notebooks or the commands "RobotCode: New Robot Framework Notebook" and "RobotCode: Restart Kernel"

### Requirement: Troubleshooting in VS Code

The page Troubleshooting SHALL explain where RobotCode writes its output and logs in VS Code, how to check which RobotCode, Robot Framework and Python versions are used, how to restart the language servers, how to clear the cache and restart them, and how to report an issue.

#### Scenario: Versions in use
- **WHEN** a reader opens `/guides/vscode/troubleshooting/`
- **THEN** a screenshot shows the language status items with the RobotCode, Robot Framework and Python versions

#### Scenario: Restart and report
- **WHEN** a reader opens `/guides/vscode/troubleshooting/`
- **THEN** the page explains "RobotCode: Restart Language Servers", "RobotCode: Clear Cache and Restart Language Servers" and "RobotCode: Report Issue..."

### Requirement: Screenshots in the site's theme

Every screenshot and screen recording of the group SHALL exist in VS Code's light and in its dark theme, and a page SHALL show the variant that matches the theme the site is shown in, also after the reader switches the site's theme.

#### Scenario: Dark site
- **WHEN** a reader views `/guides/vscode/writing-code/` with the site in its dark theme
- **THEN** the screenshots show VS Code in its dark theme

#### Scenario: Switching the theme
- **WHEN** the reader switches the site to its light theme
- **THEN** the screenshots on the page show VS Code in its light theme, without reloading the page

### Requirement: Full-size window screenshots

A screenshot that shows the whole VS Code window SHALL open in its full size when the reader clicks it.

#### Scenario: Window screenshot
- **WHEN** a reader clicks the screenshot of the window on `/guides/vscode/`
- **THEN** the screenshot is shown in its full size

### Requirement: Screenshots of one example project

The screenshots and screen recordings of the group SHALL show one example project with tests, resource files and a Python library, as the current RobotCode shows it. They SHALL show no user names, host names or personal paths.

#### Scenario: No personal data
- **WHEN** the screenshots and recordings of the group are reviewed
- **THEN** no user name, host name or path of a home directory is visible in them
