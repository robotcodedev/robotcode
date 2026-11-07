# Spec Delta

## MODIFIED Requirements

### Requirement: Setting up an agent

Setting Up SHALL say that `robotcode` must run in the project's Python environment: outside VS Code, RobotCode's command line tools are installed there, and in VS Code the extension brings its own copy, which runs with the terminal's Python interpreter. It SHALL describe the plugin that comes with the VS Code extension, the installation from the marketplace with the commands for Claude Code, GitHub Copilot CLI and Codex, updating the plugin from the marketplace, matching the plugin to the RobotCode version, agents in PyCharm, and how to check that the agent works through `robotcode`.

#### Scenario: Claude Code
- **WHEN** a reader sets up Claude Code with the page
- **THEN** the page gives the commands that add the marketplace and install the plugin

#### Scenario: Plugin version
- **WHEN** a reader opens `/guides/ai-agents/setting-up/#matching-your-robotcode-version`
- **THEN** the section on matching the plugin to the RobotCode version is shown

#### Scenario: PyCharm
- **WHEN** a reader looks up how to use an agent in PyCharm
- **THEN** the page says that Claude Code, GitHub Copilot CLI and Codex work in PyCharm's terminal as well, that RobotCode's PyCharm plugin does not include the plugin for agents yet, and that they install it from the marketplace
- **AND** it says that GitHub Copilot's plugin for PyCharm can't use the plugin

#### Scenario: Updating the plugin
- **WHEN** a reader wants to update the plugin from the marketplace
- **THEN** the page gives the commands for Claude Code, GitHub Copilot CLI and Codex, and the command for VS Code

### Requirement: Briefing the agent

Briefing the Agent SHALL say what to write down about a project for an agent: the Python environment and package manager, setup steps of libraries, the system under test and the project's conventions, without secrets. It SHALL name the instruction files the agents read, advise to name the RobotCode skill there instead of saying how to run the tests, and show in full the instruction file of the example project that the tutorial uses.

#### Scenario: Instruction file of the example project
- **WHEN** a reader opens `/guides/ai-agents/briefing/`
- **THEN** the page shows the complete instruction file of the example project
- **AND** it says which instruction files GitHub Copilot Chat, GitHub Copilot CLI, Codex and Claude Code read

#### Scenario: The skill in the instruction file
- **WHEN** a reader reads the example instruction file
- **THEN** it names the RobotCode skill instead of saying how to run the tests
