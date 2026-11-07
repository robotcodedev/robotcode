---
title: How the RobotCode Skill Works
description: When an agent loads the RobotCode skill, which robotcode command it uses for which request, and how robotcode behaves when an agent runs it.
sidebar:
  label: How the Skill Works
  order: 150.3
---

The RobotCode plugin gives an agent one skill, called `robotcode`: a set of instructions that the agent loads when a request looks like Robot Framework work. The skill brings no tools or models of its own. It teaches the agent which `robotcode` command answers which question. This page explains when the agent loads the skill, which request leads to which command, and how `robotcode` behaves when an agent runs it.

## When the agent loads the skill

A skill is loaded by relevance: the agent compares your request with the skill's description and pulls the skill in when the request reads as Robot Framework work, such as writing, running, debugging or checking tests and tasks, looking up keywords and libraries, or setting up `robot.toml` and profiles. A short request in a project with several languages, such as "run it" or "fix this test", may not be enough. Mention Robot Framework, a suite, a profile, a keyword or `robotcode`, or name the skill: it is called **`robotcode`**.

An agent that runs a smaller, faster model, such as Claude Haiku, leaves the skill out more often, even for an ordinary question on a Robot Framework project such as "did the last test run pass?". It then reads `output.xml` itself instead of asking `robotcode results`. With such a model, name the skill in your first request: *Use the robotcode skill.* In Claude Code you can also start the request with `/robotcode:robotcode`.

## From request to command

The skill tells the agent to decide first what you want, because each kind of request has its own command:

| You want to | The agent uses |
| --- | --- |
| Try a keyword or a flow, with no test yet | the [REPL](/guides/cli/repl/), `robotcode repl` |
| Write tests or keywords | [`robotcode doc`](/guides/cli/browsing-documentation/) to reuse what exists, the REPL for the uncertain steps, then [`robotcode analyze code`](/guides/cli/analyzing-code/) and a run of just the new test |
| Run tests | `robotcode robot`, with one test, task or suite selected by its long name (`-bl`), a subset by tag or suite, and the profile you name |
| Know what failed in a finished run | [`robotcode results`](/guides/cli/analyzing-results/), before running anything again |
| Find out why a test fails, or step through it | the [debugger](/guides/cli/robot-debug/), `robotcode robot-debug`, when the results of the last run don't explain the failure |
| Check the code | `robotcode analyze code` |
| Know which tests, tasks, suites and tags exist | [`robotcode discover`](/guides/cli/discovering-tests/) |
| Set up the configuration | `robot.toml` and its profiles, with `robotcode config info desc` for a setting's documentation and `robotcode profiles show` for the result |
| Look up a keyword or a library | `robotcode doc keywords` and `robotcode doc keyword` |

For a test that exists, the agent uses the debugger and not the REPL. The debugger stops the real run at a breakpoint or at the first failure, with the suite's setup, variables and imports in place, and the agent reads the call stack and the variables and runs keywords right there. The REPL runs only the keywords the agent types, in a context of its own, so a test tried there is a copy that can behave differently.

An agent whose shell tool can't keep a command running and write to its input runs the REPL and the debugger with [`robotcode session`](/guides/cli/sessions/), one input per command.

Everything applies to tasks as well: in an RPA project, read "task" for "test". `robotcode discover tasks` lists them.

## Where the agent looks things up

For keywords and libraries, the skill puts `robotcode doc` first. `robotcode doc keywords` and `robotcode doc keyword` use the project's environment, the installed versions of the libraries, their import arguments, the project's variables and Python path, and its own resource files. Next come the REPL, when a keyword's behavior or a locator has to be tried against the application, and the project's existing tests and resources. Only when these cannot answer does the agent turn to external documentation or a web search.

For details of RobotCode's command line, the agent reads the plain-text version of this documentation: [`llms-full.txt`](https://robotcode.io/llms-full.txt), with the index [`llms.txt`](https://robotcode.io/llms.txt).

## When robotcode is missing

If `robotcode` is not installed in the project's environment, the agent asks you one question before it installs anything: whether to add RobotCode as a development dependency of the project or only to the current environment, and which extras to install. It installs into the project's environment and not with a tool runner such as `uvx` or `pipx`, whose environment of its own doesn't have the packages installed in the project's.

The same happens when the first word after `robotcode` answers `No such command`. Then the extra with that command is missing, such as `runner`, `analyze` or `repl`, or `robotcode` is older than the skill and needs an update. Further down, as in `robotcode discover test`, the message means a wrong subcommand.

## AI-agent detection

`robotcode` notices when an agent runs it and changes some defaults of its own output, whether the plugin is installed or not:

- Colors and the pager are off, so the agent gets plain text.
- [`robotcode repl`](/guides/cli/repl/) and [`robotcode robot-debug`](/guides/cli/robot-debug/) use the plain input backend, without completion popups and redraws of the prompt.
- `robotcode repl` shows its `>>> ` prompt on piped input too, which it otherwise shows only on a terminal. An agent that writes one statement at a time sees from the `>>> ` at the end of the output that the statement has ended.

This covers the output of `robotcode` itself. The console output of Robot Framework in `robotcode robot` and `robotcode robot-debug` keeps its colors on a terminal, as in the terminal of GitHub Copilot Chat; its option `--consolecolors off` turns them off. In a pipe, it has no colors anyway.

`robotcode` counts as run by an agent when one of these environment variables is set to a value other than empty or `0`:

| Set by | Variables |
| --- | --- |
| Any agent, as a generic convention | `AI_AGENT`, `AGENT` |
| Claude Code | `CLAUDECODE`, `CLAUDE_CODE` |
| Cursor | `CURSOR_AGENT`, `CURSOR_TRACE_ID` |
| Codex | `CODEX_CI`, `CODEX_THREAD_ID`, `CODEX_SANDBOX` |
| GitHub Copilot Chat in VS Code and GitHub Copilot CLI | `COPILOT_AGENT`, `COPILOT_AGENT_SESSION_ID`, `VSCODE_AGENT` |
| Gemini CLI and Antigravity | `GEMINI_CLI`, `ANTIGRAVITY_AGENT` |
| OpenCode | `OPENCODE`, `OPENCODE_CLIENT` |
| Augment and Cline | `AUGMENT_AGENT`, `CLINE_ACTIVE` |

Two variables decide the detection itself:

| Variable | Effect |
| --- | --- |
| `ROBOTCODE_FORCE_AI_AGENT=1` | Turns the detection on, for example for an agent whose variable isn't in the list yet. Wins over everything. |
| `ROBOTCODE_NO_AI_AGENT=1` | Turns the detection off. Wins over the variables of the agents, loses to `ROBOTCODE_FORCE_AI_AGENT`. |

Options and their environment variables win over the detection. [Pager and colour in the terminal](/guides/cli/analyzing-results/#pager-and-colour-in-the-terminal) describes those for colors and the pager, and [Disabling all enhancements](/guides/cli/repl/#disabling-all-enhancements-ai-agents-automation) those for the input backend and the prompt on piped input.
