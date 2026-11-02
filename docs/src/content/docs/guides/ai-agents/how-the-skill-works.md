---
title: How the RobotCode Skill Works
description: When an agent loads the RobotCode skill, which robotcode command it uses for which request, why it debugs a failing test instead of re-running it, where it looks things up, what it does when robotcode is missing, and how robotcode adjusts its output in an agent session.
sidebar:
  label: How the Skill Works
  order: 150.3
---

The RobotCode plugin gives an agent one skill, called `robotcode`. This page explains what the skill teaches the agent, when the agent uses it, and how `robotcode` itself behaves when an agent runs it.

## How it works

The plugin currently contains a single *skill* — a set of instructions the agent loads when a request looks Robot Framework–related — and is designed to gain more skills and agents over time. The skill calls no libraries or models of its own; it teaches the agent which `robotcode` command answers which question, and how to read the project the way Robot Framework does. The core habits it installs:

- **Inventory via [`discover`](/guides/cli/discovering-tests/), never by grepping files.** Which tests, tasks, suites, and tags exist is resolved at runtime — Robot's parsing rules, `robot.toml` paths, profiles, variables, and pre-run modifiers that add, remove, rename, or retag tests. A static file scan gets it wrong; `discover` runs the real resolution with the installed Robot Framework.
- **Keyword and library lookup via [`doc`](/guides/cli/browsing-documentation/), before generic knowledge.** `robotcode doc keywords` and `robotcode doc keyword` reflect the *installed* library versions, the import arguments given with the library name (`MyLibrary::arg`), the project's variables and Python path, and local `.resource` files — things external documentation can't see.
- **Debugging a failing test via [`robot-debug`](/guides/cli/robot-debug/) — the agent's primary tool for any real test.** Whenever an existing test fails, won't run, or needs stepping through, the agent runs it under the command-line debugger: it pauses the real suite at a breakpoint (a `file:line`, a keyword, or the first uncaught failure), then reads the live call stack and per-frame variables and runs keywords in the paused context — capturing the actual state at the point of failure instead of re-running blindly or reasoning from the source. This is the default response to "why does this fail / step through it / what is `${x}` here?", and it is deliberately kept apart from the REPL below: the debugger acts on a test that *exists and runs*. Reaching for the REPL to fix a real test — instead of the debugger — is the single most common way the skill misfires.
- **Live exploration via the [REPL](/guides/cli/repl/) — only when there is *no* test yet.** A narrower tool: uncertain locators or keyword sequencing get tried interactively (optionally against the running app with a visible browser) rather than guessed. The moment a real test is in play, it is the debugger's job, not the REPL's.
- **Result inspection via [`results`](/guides/cli/analyzing-results/), not raw `output.xml`.** Finished runs are queried for bounded summaries, listings, traces, and diffs — including CI artifacts and a colleague's run — rather than loading a potentially huge XML file into the chat.
- **Static checks via [`analyze code`](/guides/cli/analyzing-code/)** before a run, and **runs via [`robot`](/reference/cli/#robot)** honoring the active profile.

Throughout, the agent respects the project's [`robot.toml`](/reference/config/) and profiles, so it operates on the same resolved configuration as the editor and the CLI.

## When the agent loads the skill

A skill is loaded by relevance: the agent compares your request with the skill's description and pulls the skill in when the request reads as Robot Framework work, such as writing, running, debugging or checking tests and tasks, looking up keywords and libraries, or setting up `robot.toml` and profiles. A short request in a project with several languages, such as "run it" or "fix this test", may not be enough. Mention Robot Framework, a suite, a profile, a keyword or `robotcode`, or name the skill: it is called **`robotcode`**.

Smaller, faster models such as Claude Haiku leave the skill out more often, even for an ordinary question on a Robot Framework project such as "did the last test run pass?". They then read `output.xml` themselves instead of asking `robotcode results`. With such a model, name the skill in your first request: *Use the robotcode skill.* In Claude Code you can also start the request with `/robotcode:robotcode`.

## From request to command

The skill tells the agent to decide first what you want, because each kind of request has its own command:

| You want to | The agent uses |
| --- | --- |
| Try a keyword or a flow, with no test yet | the [REPL](/guides/cli/repl/), `robotcode repl` |
| Write tests or keywords | [`robotcode doc`](/guides/cli/browsing-documentation/) to reuse what exists, the REPL for the uncertain steps, then [`robotcode analyze code`](/guides/cli/analyzing-code/) and a run of just the new test |
| Run tests | `robotcode robot`, with one test, task or suite selected by its long name (`-bl`), a subset by tag or suite, and the profile you name |
| Know what failed in a finished run | [`robotcode results`](/guides/cli/analyzing-results/), before running anything again |
| Find out why a test fails, or step through it | the [debugger](/guides/cli/robot-debug/), `robotcode robot-debug` |
| Check the code | `robotcode analyze code` |
| Know which tests, tasks, suites and tags exist | [`robotcode discover`](/guides/cli/discovering-tests/) |
| Set up the configuration | `robot.toml` and its profiles, with `robotcode config info desc` for a setting's documentation and `robotcode config show` for the result |
| Look up a keyword or a library | `robotcode doc keywords` and `robotcode doc keyword` |

Several of these can follow each other in one task, for example trying something out, writing the test, running it and looking at the results. Everything applies to tasks as well: in an RPA project, read "task" for "test". Only a run gets `--rpa`, and `robotcode discover tasks` lists the tasks.

## Where the agent looks things up

For keywords and libraries, the skill puts `robotcode doc` first. `robotcode doc keywords` and `robotcode doc keyword` use the project's environment, the installed versions of the libraries, their import arguments, the project's variables and Python path, and its own resource files. Next come the REPL, when a keyword's behavior or a locator has to be tried against the application, and the project's existing tests and resources. Only when these cannot answer does the agent turn to external documentation or a web search.

For details of RobotCode's command line, the agent reads RobotCode's documentation as text for language models: [`llms-full.txt`](https://robotcode.io/llms-full.txt), with the index [`llms.txt`](https://robotcode.io/llms.txt).

## When robotcode is missing

If `robotcode` is not installed in the project's environment, or a command answers `No such command`, the agent asks you before it installs anything, with both questions in one: whether to add RobotCode as a development dependency of the project or only to the current environment, and which extras to install. It installs into the project's environment, never with a tool runner such as `uvx` or `pipx`, which cannot see the project's libraries. A missing command means that its extra is missing, for example `runner`, `analyze` or `repl`.

## AI-agent detection

Independently of the chat plugins, the `robotcode` CLI detects when it is running inside an AI-agent session and adjusts its presentation defaults so captured output stays clean:

- ANSI **colors** and the **pager** are disabled, so escape sequences and paging controls don't leak into the agent's captured stdout.
- The [`robotcode robot-debug`](/guides/cli/robot-debug/) prompt and the [`robotcode repl`](/guides/cli/repl/) shell fall back to the **plain input backend**, so completion popups and prompt redraws don't interfere with stdin/stdout — captured debug output (`.where`, `.vars`, `.print`) stays clean.
- The `robotcode repl` shell shows its **`>>> ` prompt** on piped input too, which it otherwise shows only on a terminal: an agent that writes one statement at a time sees from the `>>> ` at the end of the output that the statement has ended.

Detection is based on environment markers set by popular tools — Claude Code, Cursor, GitHub Copilot (CLI and VS Code agent flow), Codex, OpenCode, Gemini CLI, and others — plus the generic `AI_AGENT` and `AGENT` conventions. A marker counts as active when it is present with any value other than empty or `0`.

You rarely need to touch this, but every default can be overridden:

| Override | Effect |
| --- | --- |
| `ROBOTCODE_FORCE_AI_AGENT=1` | Force detection **on** (e.g. an agent whose marker isn't recognized yet). Wins over everything. |
| `ROBOTCODE_NO_AI_AGENT=1` | Force detection **off**. Wins over tool markers, loses to `ROBOTCODE_FORCE_AI_AGENT`. |
| `--color` / `--no-color`, `NO_COLOR`, `FORCE_COLOR` | Decide coloring explicitly, regardless of detection. |
| `--pager` / `--no-pager` | Decide paging explicitly. |
| `--plain` / `--backend`, `ROBOTCODE_REPL_PLAIN`, `ROBOTCODE_REPL_BACKEND` | Decide the prompt backend explicitly — applies to both `robot-debug` and the REPL. |
| `--show-prompt` / `--no-show-prompt`, `ROBOTCODE_REPL_SHOW_PROMPT` | Decide whether the REPL shows its prompt on piped input. |

Explicit flags and environment variables always win over auto-detection, so you can opt back into colored, paged, or full-featured output inside an agent session when you want it.

## See also

- [Command Line Interface](/reference/cli/) — every `robotcode` command the agent drives.
- [Discovering Tests, Tasks and Suites](/guides/cli/discovering-tests/) — how project inventory is resolved.
- [Analyzing Run Results](/guides/cli/analyzing-results/) — inspecting finished runs.
- [Command-line debugging with `robotcode robot-debug`](/guides/cli/robot-debug/) — pausing a real run at a breakpoint to inspect the live stack and variables.
- [Interactive Robot Framework REPL](/guides/cli/repl/) — the live keyword shell.
- [`robotframework-agent-plugins`](https://github.com/robotcodedev/robotframework-agent-plugins) — the marketplace and plugin source.
