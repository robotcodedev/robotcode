# Spec Delta

## Purpose

The AI agents guide of the documentation site: its pages, setting up and briefing an agent, how the skill works, a tutorial that teaches working with an agent with sessions of a real agent as evidence, how these sessions are recorded and shown, and troubleshooting.

## ADDED Requirements

### Requirement: Pages of the AI agents guide

The group AI Agents SHALL contain, in this order, the pages Overview, Setting Up, Briefing the Agent, How the Skill Works, Working with the Agent and Troubleshooting, with the overview at `/guides/ai-agents/` and the other pages below it; Working with the Agent SHALL be a group of its own. The overview SHALL say what an agent does with the RobotCode skill, name the agents it works with, list the steps of the tutorial and lead to the other pages.

#### Scenario: Pages in the sidebar
- **WHEN** a reader opens any page of the group AI Agents
- **THEN** the sidebar lists Overview, Setting Up, Briefing the Agent, How the Skill Works, Working with the Agent and Troubleshooting in this order
- **AND** Working with the Agent is a group of its own

#### Scenario: From the overview
- **WHEN** a reader opens `/guides/ai-agents/`
- **THEN** the page names the agents the skill works with
- **AND** it lists the seven steps of the tutorial, each linked
- **AND** link cards lead to the five other pages of the group

### Requirement: Setting up an agent

Setting Up SHALL say that RobotCode's command line tools must be installed in the project's Python environment. It SHALL describe the plugin that comes with the VS Code extension, the installation from the marketplace with the commands for Claude Code, GitHub Copilot CLI and Codex, matching the plugin to the RobotCode version, agents in PyCharm, and how to check that the agent works through `robotcode`.

#### Scenario: Claude Code
- **WHEN** a reader sets up Claude Code with the page
- **THEN** the page gives the commands that add the marketplace and install the plugin

#### Scenario: Plugin version
- **WHEN** a reader opens `/guides/ai-agents/setting-up/#matching-your-robotcode-version`
- **THEN** the section on matching the plugin to the RobotCode version is shown

#### Scenario: PyCharm
- **WHEN** a reader looks up how to use an agent in PyCharm
- **THEN** the page says that the usual agents work in PyCharm as well, that RobotCode's PyCharm plugin does not bring the plugin for them yet, and that they install it from the marketplace

### Requirement: Briefing the agent

Briefing the Agent SHALL say what to write down about a project for an agent: the Python environment and package manager, setup steps of libraries, the system under test and the project's conventions, without secrets. It SHALL name the instruction files the agents read, advise to name the RobotCode skill there instead of saying how to run the tests, and show in full the instruction file of the example project that the sessions were recorded with.

#### Scenario: Instruction file of the example project
- **WHEN** a reader opens `/guides/ai-agents/briefing/`
- **THEN** the page shows the complete instruction file of the example project
- **AND** it says which instruction file Claude Code, GitHub Copilot and Codex read

#### Scenario: The skill in the instruction file
- **WHEN** a reader reads the example instruction file
- **THEN** it names the RobotCode skill instead of saying how to run the tests

### Requirement: How the skill works

How the Skill Works SHALL explain when an agent loads the skill and how to make it do so, which request leads to which `robotcode` command, why the agent debugs an existing test with the debugger and not in the REPL, where it looks up keywords and RobotCode's documentation, and how `robotcode` adjusts its output in an agent session and how to override that.

#### Scenario: Detection of agent sessions
- **WHEN** a reader opens `/guides/ai-agents/how-the-skill-works/#ai-agent-detection`
- **THEN** the section on how `robotcode` detects an agent session, with its overrides, is shown

### Requirement: A tutorial for working with the agent

Working with the Agent SHALL be a tutorial with an overview and seven steps in this order: getting to know the project, writing a test from a requirement, running what you need, finding out why a test failed, debugging step by step, checking before a push, and a profile for the CI server. Each step SHALL say what the reader learns, how to ask the agent, what the agent does and why, and what to watch out for, for the reader's own project and any agent.

#### Scenario: Steps of the tutorial
- **WHEN** a reader opens `/guides/ai-agents/working-with-the-agent/`
- **THEN** the sidebar shows the group Working with the Agent with its overview and the seven steps in this order
- **AND** link cards lead to the seven steps

#### Scenario: A step
- **WHEN** a reader opens a step of the tutorial
- **THEN** it says what the reader learns, how to ask the agent, what the agent does and why, and what to watch out for
- **AND** the recorded sessions of the step follow its explanation

### Requirement: Sessions as evidence

Each step SHALL show at least one recorded session of Claude Code with the RobotCode skill below its explanation, and the explanation SHALL quote short excerpts from these sessions, marked as excerpts. A session SHALL show the prompts, the commands with their output, the files the agent read or changed, and its answers.

#### Scenario: Excerpt
- **WHEN** a step explains what the agent does
- **THEN** it quotes a short excerpt of one of its sessions, marked as an excerpt

#### Scenario: Failing test
- **WHEN** a reader opens the step on finding out why a test failed
- **THEN** a session shows how the agent finds out from the results of the last run why a test failed, with the commands it ran and their output

#### Scenario: Comparing runs
- **WHEN** a reader opens the step on finding out why a test failed
- **THEN** a session shows the agent comparing two runs of the project

#### Scenario: Tasks
- **WHEN** a reader opens the step on writing a test from a requirement
- **THEN** a session shows the agent writing a task and running it

#### Scenario: Large project
- **WHEN** a reader opens the step on getting to know the project
- **THEN** a session recorded in a project with thousands of tests shows how the agent answers questions about it

### Requirement: Interactive sessions

Working with the Agent SHALL show a debugging session in which the user steers the paused run turn by turn, and a REPL session in which the agent runs keywords one after another, shows the current state when asked and reacts to their output and failures. In both, the debugger or the REPL SHALL keep running between the user's prompts.

#### Scenario: Debugging step by step
- **WHEN** a reader opens the step on debugging step by step
- **THEN** a session shows the agent stopping a run at a line the user names, showing the variables and the call stack when the user asks, and continuing to the next breakpoint when the user says so

#### Scenario: Keywords in the REPL
- **WHEN** a reader opens the step on writing a test from a requirement
- **THEN** a session shows the agent running keywords one after another in one REPL, showing its variables when the user asks, and reacting to a keyword that fails

### Requirement: Recording of the sessions

The sessions SHALL be recorded in the example project of a web shop that the home page's demos use, and the session on a large project in a generated project with thousands of tests. Claude Code SHALL run in a configuration of its own with only the RobotCode plugin installed, without further instructions, memory or MCP servers. The overview of Working with the Agent SHALL name the version of Claude Code and the model.

#### Scenario: Versions
- **WHEN** a reader opens `/guides/ai-agents/working-with-the-agent/`
- **THEN** the page names the version of Claude Code and the model the sessions were recorded with

### Requirement: Sessions shown as recorded

A session, and an excerpt of it in a step's explanation, SHALL show what the agent did and answered without rewording; only the local paths of the machine it was recorded on SHALL be replaced by neutral ones, such as `~/webshop`. Parts MAY be left out and SHALL then be marked with "…".

#### Scenario: Shortened output
- **WHEN** a command printed more lines than its session shows
- **THEN** the left-out lines are marked with "…"

#### Scenario: Local paths
- **WHEN** a command or its output named a folder of the recording machine, such as the session project's folder
- **THEN** the session shows a neutral path in its place, such as `~/webshop`

#### Scenario: Excerpt as recorded
- **WHEN** a step quotes a session in its explanation
- **THEN** the lines of the excerpt appear in that session as recorded, in the same order

### Requirement: How a session is shown

A session SHALL be collapsed below its step's explanation until the reader opens it. Open, it SHALL be set apart from the guide's text by a frame, and in it each prompt and each answer by a frame of its own; a command with its output SHALL be a code block and a changed file a diff.

#### Scenario: Collapsed
- **WHEN** a reader opens a step
- **THEN** its sessions are collapsed, each with a summary that names the session and its first prompt
- **AND** opening one shows the whole session

#### Scenario: Set apart from the guide
- **WHEN** a reader opens a session
- **THEN** the session is in a frame, and each of its prompts and answers in a frame of its own
- **AND** the frames show in the dark and the light theme

### Requirement: Troubleshooting AI agents

Troubleshooting SHALL describe, by symptom, what helps when the agent answers without `robotcode`, uses another environment than the project's, re-runs a failing test or uses the REPL instead of debugging it, writes a test when it was asked to try something out, or when the plugin from the marketplace behaves differently from the one in VS Code.

#### Scenario: Agent answers without robotcode
- **WHEN** a reader looks up why the agent answers from general knowledge
- **THEN** the page says to name the subject or the skill `robotcode` in the request, and in VS Code to check `robotcode.ai.enableChatPlugins`
