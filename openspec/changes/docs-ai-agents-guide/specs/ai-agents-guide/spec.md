# Spec Delta

## Purpose

The AI agents guide of the documentation site: its pages, setting up and briefing an agent, the sessions of a real agent that show what the RobotCode skill does, how these sessions are recorded and shown, how the skill works, and troubleshooting.

## ADDED Requirements

### Requirement: Pages of the AI agents guide

The group AI Agents SHALL contain, in this order, the pages Overview, Setting Up, Briefing the Agent, Working with the Agent, How the Skill Works and Troubleshooting, with the overview at `/guides/ai-agents/` and the other pages below it. The overview SHALL say what an agent does with the RobotCode skill, name the agents it works with and lead to the other pages.

#### Scenario: Pages in the sidebar
- **WHEN** a reader opens any page of the group AI Agents
- **THEN** the sidebar lists Overview, Setting Up, Briefing the Agent, Working with the Agent, How the Skill Works and Troubleshooting in this order

#### Scenario: From the overview
- **WHEN** a reader opens `/guides/ai-agents/`
- **THEN** the page names the agents the skill works with
- **AND** link cards lead to the five other pages of the group

### Requirement: Setting up an agent

Setting Up SHALL say that RobotCode's command line tools must be installed in the project's Python environment. It SHALL describe the plugin that comes with the VS Code extension, the installation from the marketplace with the commands for Claude Code, GitHub Copilot CLI and Codex, matching the plugin to the RobotCode version, an agent in PyCharm's terminal, and how to check that the agent works through `robotcode`.

#### Scenario: Claude Code
- **WHEN** a reader sets up Claude Code with the page
- **THEN** the page gives the commands that add the marketplace and install the plugin

#### Scenario: Plugin version
- **WHEN** a reader opens `/guides/ai-agents/setting-up/#matching-your-robotcode-version`
- **THEN** the section on matching the plugin to the RobotCode version is shown

#### Scenario: PyCharm
- **WHEN** a reader looks up how to use an agent in PyCharm
- **THEN** the page says that PyCharm has no plugin of its own for AI agents, and that an agent in PyCharm's terminal installs the plugin from the marketplace

### Requirement: Briefing the agent

Briefing the Agent SHALL say what to write down about a project for an agent: the Python environment and package manager, setup steps of libraries, the system under test and the project's conventions, without secrets. It SHALL name the instruction files the agents read, and show in full the instruction file of the example project that the sessions of Working with the Agent were recorded with.

#### Scenario: Instruction file of the example project
- **WHEN** a reader opens `/guides/ai-agents/briefing/`
- **THEN** the page shows the complete instruction file of the example project
- **AND** it says which instruction file Claude Code, GitHub Copilot and Codex read

### Requirement: Sessions for each task

Working with the Agent SHALL have a section each for writing tests and tasks, running tests, failing tests, knowing the project, code quality and the configuration. Each section SHALL show at least one session of Claude Code with the RobotCode skill, with the prompts, the commands with their output, the files the agent read or changed, and its answers.

#### Scenario: Failing test
- **WHEN** a reader reads the section on failing tests
- **THEN** a session shows how the agent finds out from the results of the last run why a test failed, with the commands it ran and their output

#### Scenario: Comparing runs
- **WHEN** a reader reads the section on failing tests
- **THEN** a session shows the agent comparing two runs of the project

#### Scenario: Tasks
- **WHEN** a reader reads the section on writing tests and tasks
- **THEN** a session shows the agent writing a task and running it

#### Scenario: Large project
- **WHEN** a reader reads the section on knowing the project
- **THEN** a session recorded in a project with thousands of tests shows how the agent answers questions about it

### Requirement: Interactive sessions

Working with the Agent SHALL show a debugging session in which the user steers the paused run turn by turn, and a REPL session in which the agent runs keywords one after another, shows the current state when asked and reacts to their output and failures. In both, the debugger or the REPL SHALL keep running between the user's prompts.

#### Scenario: Debugging step by step
- **WHEN** a reader reads the section on failing tests
- **THEN** a session shows the agent stopping a run at a line the user names, showing the variables and the call stack when the user asks, and continuing to the next breakpoint when the user says so

#### Scenario: Keywords in the REPL
- **WHEN** a reader reads the section on writing tests and tasks
- **THEN** a session shows the agent running keywords one after another in one REPL, showing its variables when the user asks, and reacting to a keyword that fails

### Requirement: Recording of the sessions

The sessions SHALL be recorded in the example project of a web shop that the home page's demos use, and the session on a large project in a generated project with thousands of tests. Claude Code SHALL run in a configuration of its own with only the RobotCode plugin installed, without further instructions, memory or MCP servers. The page SHALL name the versions of Claude Code and RobotCode and the model.

#### Scenario: Versions
- **WHEN** a reader opens `/guides/ai-agents/working-with-the-agent/`
- **THEN** the page names the version of Claude Code, the model and the version of RobotCode the sessions were recorded with

### Requirement: Sessions shown as recorded

A session SHALL show what the agent did and answered without rewording. Parts MAY be left out and SHALL then be marked with "…". A prompt SHALL be shown as a quote, a command with its output as a code block, a changed file as a diff, and an answer as text.

#### Scenario: Shortened output
- **WHEN** a command printed more lines than its session shows
- **THEN** the left-out lines are marked with "…"

### Requirement: How the skill works

How the Skill Works SHALL explain when an agent loads the skill and how to make it do so, which request leads to which `robotcode` command, why the agent debugs an existing test with the debugger and not in the REPL, where it looks up keywords and RobotCode's documentation, and how `robotcode` adjusts its output in an agent session and how to override that.

#### Scenario: Detection of agent sessions
- **WHEN** a reader opens `/guides/ai-agents/how-the-skill-works/#ai-agent-detection`
- **THEN** the section on how `robotcode` detects an agent session, with its overrides, is shown

### Requirement: Troubleshooting AI agents

Troubleshooting SHALL describe, by symptom, what helps when the agent answers without `robotcode`, uses another environment than the project's, re-runs a failing test or uses the REPL instead of debugging it, writes a test when it was asked to try something out, or when the plugin from the marketplace behaves differently from the one in VS Code.

#### Scenario: Agent answers without robotcode
- **WHEN** a reader looks up why the agent answers from general knowledge
- **THEN** the page says to name the subject or the skill `robotcode` in the request, and in VS Code to check `robotcode.ai.enableChatPlugins`
