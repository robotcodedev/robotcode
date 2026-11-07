# ai-agents-guide Specification

## Purpose

The AI agents guide of the documentation site: its pages, setting up and briefing an agent, how the skill works, a tutorial that teaches working with an agent through prompts, with answers of real runs and the commands the agent ran, its example project, and troubleshooting.

## Requirements

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

Setting Up SHALL say that `robotcode` must run in the project's Python environment, installed there outside VS Code and brought by the extension in VS Code. It SHALL describe the plugin of the VS Code extension, installing and updating the plugin from the marketplace for Claude Code, GitHub Copilot CLI and Codex, matching it to the RobotCode version, agents in PyCharm, and how to check that the agent works through `robotcode`.

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

### Requirement: How the skill works

How the Skill Works SHALL explain when an agent loads the skill and how to make it do so, which request leads to which `robotcode` command, why the agent debugs an existing test with the debugger and not in the REPL, where it looks up keywords and RobotCode's documentation, and how `robotcode` adjusts its output in an agent session and how to override that.

#### Scenario: Detection of agent sessions
- **WHEN** a reader opens `/guides/ai-agents/how-the-skill-works/#ai-agent-detection`
- **THEN** the section on how `robotcode` detects an agent session, with its overrides, is shown

### Requirement: A tutorial for working with the agent

Working with the Agent SHALL be a tutorial with an overview and seven steps in this order: getting to know the project, writing a test from a requirement, running what you need, finding out why a test failed, debugging step by step, checking before a push, and a profile for the CI server. Each step SHALL teach the reader to ask and instruct an agent, for the reader's own project and any agent.

#### Scenario: Steps of the tutorial
- **WHEN** a reader opens `/guides/ai-agents/working-with-the-agent/`
- **THEN** the sidebar shows the group Working with the Agent with its overview and the seven steps in this order
- **AND** link cards lead to the seven steps

#### Scenario: A step
- **WHEN** a reader opens a step of the tutorial
- **THEN** it leads through prompts to the agent in the order of the work, and between them says what to look for in the answer and what to do next
- **AND** it ends with what to take to the reader's own project

### Requirement: Everything goes through prompts

A step SHALL start from what the reader wants to find out or get done, and SHALL reach it through prompts to the agent. It SHALL NOT have the reader run a `robotcode` command before the agent has named it, and SHALL NOT explain commands one by one.

#### Scenario: Start of a step
- **WHEN** a reader follows a step from its beginning
- **THEN** the first thing the reader does in the project is to send the agent a prompt

#### Scenario: Commands in a step
- **WHEN** a step's own text mentions a `robotcode` command
- **THEN** an answer shown before it has named that command

### Requirement: Steps stand on their own

Each step SHALL start from the example project as it is in the repository, not from what an earlier step changed. A step SHALL NOT need git commands; to start over, the tutorial SHALL say to reset the repository.

#### Scenario: Opening a step directly
- **WHEN** a reader opens a step without having done the steps before it
- **THEN** its prompts work in a freshly set up example project
- **AND** the step links to how to set the project up

#### Scenario: Starting over
- **WHEN** a reader wants to undo what the agent changed
- **THEN** the tutorial says to reset the repository, without showing git commands

### Requirement: Following along

The overview of Working with the Agent SHALL say how to set up the example project and how to start over, that the answers shown are from real runs and differ from one run and one agent to the next, and that a prompt to a smaller model should name the skill. The steps SHALL NOT repeat this beyond a link to it.

#### Scenario: On the overview
- **WHEN** a reader opens `/guides/ai-agents/working-with-the-agent/`
- **THEN** the page says how to follow along with the example project, why answers differ, and when to name the skill in a prompt

### Requirement: Prompts are tried first

Every prompt a step shows SHALL have been run with several agents that use the skill before it is written down, in the example project or, for a large project, in a generated one. What the text says about the agent's behavior SHALL hold for these runs.

#### Scenario: A prompt in a step
- **WHEN** a step shows a prompt
- **THEN** the prompt was run turn by turn with several agents, in the order of the step

#### Scenario: Agents behave differently
- **WHEN** the agents differ in something the text would claim
- **THEN** the text doesn't claim it, or says what differs

### Requirement: The text describes what applies

The text of the tutorial SHALL describe what applies, in the present tense. It SHALL NOT retell a run, or report how runs went.

#### Scenario: What a prompt leads to
- **WHEN** the text says what a kind of prompt leads to
- **THEN** it says so without counts of runs, and without saying who tried it

### Requirement: Answers of the agent

A step SHALL show the agent's answer to a prompt as the agent wrote it, rendered as Markdown; only local paths SHALL be replaced by neutral ones, and parts MAY be left out if they are marked with "…". The answers of one step SHALL come from one run through it. A prompt MAY stand without an answer.

#### Scenario: Shortened answer
- **WHEN** a step leaves out part of an answer
- **THEN** the left-out part is marked with "…"

#### Scenario: Local paths in an answer
- **WHEN** an answer named a folder of the machine it ran on
- **THEN** the step shows a neutral path in its place, such as `~/webshop`

#### Scenario: Answers that fit together
- **WHEN** an answer in a step refers to an earlier result
- **THEN** that result is the one the step's earlier answer shows

### Requirement: Prompts and answers set apart

A prompt with its answer SHALL be in a frame that sets it apart from the guide's text, and the prompt and the answer SHALL look different from each other, in the dark and the light theme.

#### Scenario: Set apart from the guide's text
- **WHEN** a reader opens a step
- **THEN** each prompt and answer is in a frame, and the guide's text is outside of it
- **AND** this shows in the dark and the light theme

#### Scenario: Code in an answer
- **WHEN** an answer contains a code block or a diff
- **THEN** its indentation is as the agent wrote it, and no line is hidden by the block's controls

### Requirement: The commands the agent ran

Between a prompt and its answer, a step SHALL show the `robotcode` commands the agent ran for that prompt in the run the answer comes from, in that order, each linked to its documentation and without its output. What the shell does around a command and repeats SHALL be left out, and other left-out parts SHALL be marked with "…". The overview SHALL say that other commands the agent runs aren't shown.

#### Scenario: A prompt that runs commands
- **WHEN** the agent ran `robotcode` commands for a prompt
- **THEN** they stand between the prompt and its answer
- **AND** each links to the documentation of that command, a section of a CLI guide where there is one, the CLI reference otherwise

#### Scenario: A prompt without commands
- **WHEN** the agent ran no `robotcode` command for a prompt
- **THEN** nothing stands between the prompt and its answer

#### Scenario: Other commands of the agent
- **WHEN** a reader opens `/guides/ai-agents/working-with-the-agent/`
- **THEN** the page says that the agent also reads files and runs other commands, which aren't shown

### Requirement: Links to the commands an answer names

When an answer a step shows names a `robotcode` command, the guide's text right after the answer SHALL link to that command's documentation: a section of a CLI guide where there is one, the CLI reference otherwise. The answer itself SHALL stay as the agent wrote it.

#### Scenario: A command in an answer
- **WHEN** an answer names `robotcode results summary`
- **THEN** the text right after it links to the section on `summary` of the guide on analyzing results

#### Scenario: A command without a guide
- **WHEN** an answer names `robotcode robot`
- **THEN** the text right after it links to `robot` in the CLI reference

#### Scenario: Commands differ between runs
- **WHEN** the agents named different commands for the same prompt
- **THEN** the text says that the reader's agent may name others, and links to one of them as an example

### Requirement: What the steps teach

Each step SHALL teach what to ask or tell an agent for its kind of work, on a real question in the example project.

#### Scenario: Getting to know the project
- **WHEN** a reader opens the step on getting to know the project
- **THEN** prompts ask which tests there are, which tests cover a requirement and what a keyword takes, and have the agent try a keyword
- **AND** the step says to name the scope and, in a large project, to ask for counts before lists

#### Scenario: Writing a test
- **WHEN** a reader opens the step on writing a test from a requirement
- **THEN** prompts have the agent learn the library, try keywords in a REPL that keeps running between the prompts, write the test from the requirement, check it and run it
- **AND** the step says how to check what the agent wrote, also what else it changed
- **AND** a prompt asks for a task

#### Scenario: Running what you need
- **WHEN** a reader opens the step on running what you need
- **THEN** prompts name what to run: a tag, a suite, one test or a profile
- **AND** the reader asks what a profile changes before relying on it, and the step's own text says why that matters

#### Scenario: Finding out why a test failed
- **WHEN** a reader opens the step on finding out why a test failed
- **THEN** the reader first asks what happened, gets the commands from the agent, checks whether the failure happens every time, decides what is right, and only then asks for the fix with its proof and looks at the change
- **AND** the step says that deciding what is right is up to the reader

#### Scenario: Debugging
- **WHEN** a reader opens the step on debugging step by step
- **THEN** the reader starts from a real question that the results of a run don't answer
- **AND** prompts stop the run where the reader says, show what the reader asks for, and continue when the reader says so, with the run paused between the prompts
- **AND** a prompt ends the debugger

#### Scenario: Checking before a push
- **WHEN** a reader opens the step on checking before a push
- **THEN** the reader asks for a check without running the tests, also with the profile CI uses, decides what gets fixed, and has a finding that is intended marked as such

#### Scenario: A CI profile
- **WHEN** a reader opens the step on a profile for the CI server
- **THEN** the reader says what the CI needs, sees the resulting profile on the page, and has the agent show what a run with it gets without running the tests
- **AND** the page says which settings of a profile replace those of `robot.toml` and which add to them

### Requirement: Troubleshooting AI agents

Troubleshooting SHALL describe, by symptom, what helps when the agent answers without `robotcode`, loads `robotcode` although another skill fits better or skips it although it fits, uses another environment than the project's, re-runs a failing test or uses the REPL instead of debugging it, writes a test when it was asked to try something out, or when the plugin from the marketplace behaves differently from the one in VS Code.

#### Scenario: Agent answers without robotcode
- **WHEN** a reader looks up why the agent answers from general knowledge
- **THEN** the page says to name the subject or the skill `robotcode` in the request, and in VS Code to check `robotcode.ai.enableChatPlugins`

#### Scenario: Agent picks the wrong skill
- **WHEN** a reader looks up why the agent loads `robotcode` although another skill fits better, or skips it although it fits
- **THEN** the page says that agents choose from a list of skills of limited size, and that descriptions in it can be shortened or dropped when it overflows
- **AND** the page says what helps: naming the skill in the request, removing or turning off skills that aren't needed and, where the agent allows it, raising the limit
- **AND** the page describes this for agents in general, with Claude Code only as an example

### Requirement: The example project of the tutorial

The example project of the tutorial SHALL be public in the repository `robotcodedev/webshop-ai-example`, and the overview of Working with the Agent and Briefing the Agent SHALL link to it.

#### Scenario: Finding the example project
- **WHEN** a reader opens `/guides/ai-agents/working-with-the-agent/` or `/guides/ai-agents/briefing/`
- **THEN** the page links to `robotcodedev/webshop-ai-example`

#### Scenario: Wrong on purpose
- **WHEN** a reader opens `/guides/ai-agents/working-with-the-agent/`
- **THEN** the page says that some things in the example project are wrong on purpose

#### Scenario: A clean clone
- **WHEN** a reader clones the repository and follows its README
- **THEN** `robotcode robot` runs 13 tests, of which `Login Works` fails every time, `Express Order` fails only sometimes and the others pass
- **AND** `robotcode analyze code` reports the unknown keyword `Submit Ordr`
- **AND** `robotcode session` is available

#### Scenario: The README keeps the answers back
- **WHEN** an agent working in the repository reads its README
- **THEN** the README says that some things are wrong on purpose, without naming them

#### Scenario: Pushing to the repository
- **WHEN** someone pushes to the repository
- **THEN** no workflow starts, and the workflow in `.github/workflows/tests.yml` can be started by hand
