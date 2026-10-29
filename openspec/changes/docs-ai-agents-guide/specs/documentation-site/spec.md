# Spec Delta

## MODIFIED Requirements

### Requirement: Guides grouped by tool and topic

The Guides sidebar SHALL list, in this order, the overview and the groups VS Code, PyCharm, Command Line, AI Agents, Project Configuration and Tips & Tricks. Every other guide SHALL be a page of one of these groups, at a path under the group's path. The groups SHALL be shown collapsed, except the group that contains the open page.

#### Scenario: Order in the sidebar
- **WHEN** a reader opens `/guides/`
- **THEN** the sidebar lists Overview, VS Code, PyCharm, Command Line, AI Agents, Project Configuration and Tips & Tricks in this order
- **AND** every group is collapsed

#### Scenario: Names by subject
- **WHEN** a reader looks for the guides to `robot.toml` and to `.robotignore` in the sidebar
- **THEN** both are in the group Project Configuration, at `/guides/robot-toml/`
- **AND** the group lists the page Finding Robot Files right after Files and Project Root

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
- **THEN** the overview of the group, titled Tips & Tricks, is shown
- **AND** link cards lead to the pages on avoiding a global resource file and on variables shown as not found

#### Scenario: Project Configuration group
- **WHEN** a reader opens `/guides/robot-toml/`
- **THEN** the overview of the group is shown
- **AND** link cards lead to the guides to `robot.toml` and to Finding Robot Files

#### Scenario: AI Agents group
- **WHEN** a reader opens `/guides/ai-agents/`
- **THEN** the overview of the group is shown
- **AND** the group AI Agents is expanded in the sidebar

#### Scenario: Path of a moved guide
- **WHEN** a reader opens `/guides/repl/`
- **THEN** the site's not-found page is returned, without a redirect
