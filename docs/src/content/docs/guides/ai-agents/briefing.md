---
title: Briefing the Agent
description: What to write down about your project for an AI agent, in which file each agent reads it, and the complete instruction file of the example project used on Working with the Agent.
sidebar:
  label: Briefing the Agent
  order: 150.2
---

The skill teaches the agent how to drive `robotcode`, and `robotcode` reads your configuration when it runs: the paths, the profiles, the tags, the suites and the installed versions of the libraries. You don't have to write these down for the agent.

The agent can't find out from `robotcode` how the project is set up around the tests and what you want from them. Write that down once in your agent's instruction file ([which file](#which-file-the-agent-reads)), so that it doesn't have to find it out again on every task, or guess. Worth writing down:

- **Environment and package manager:** which tool manages the dependencies (`uv`, `hatch`, `poetry`, `pip`, …) and where the project's virtual environment is, so that the agent runs `robotcode` with the right interpreter (see [Prerequisites](/guides/ai-agents/setting-up/#prerequisites)).
- **Installed libraries and their setup steps:** above all a step that is needed once after an install or update. For example, the Browser library needs `rfbrowser init` to download its Playwright browsers before its keywords work, and an agent that doesn't know this runs into confusing failures.
- **The system under test:** what the application is, how to reach it (base URLs per environment, which profile points where), and any test data or accounts. Keep secrets out: describe how credentials are provided, such as environment variables or a vault, not the values themselves.
- **Project conventions:** naming, tags, the layout of the suites and where new keywords belong, so that new tests match what you already have.

In that file, name the RobotCode skill, as in *"Use the RobotCode skill for all work on the tests."* Don't say how to run the tests. A rule such as "run tests with `robotcode robot`" repeats what the skill says, and it names only one of the ways the skill chooses from: the others include the debugger and the results of a finished run.

Keep it short and factual: the agent reads it on every request.

## Which file the agent reads

GitHub Copilot Chat, GitHub Copilot CLI, Codex and Claude Code all read `AGENTS.md` in the project's root folder, so one file serves a team that uses several of them:

- **GitHub Copilot Chat** in VS Code reads `.github/copilot-instructions.md` and `AGENTS.md`. In its local agent sessions, the setting `chat.useAgentsMdFile`, on by default, controls `AGENTS.md`.
- **GitHub Copilot CLI** reads `AGENTS.md`, `.github/copilot-instructions.md` and `CLAUDE.md`, in the repository's root folder, in the folder it works in and in the folders between them.
- **Codex** reads the `AGENTS.md` files from the project's root folder down to the folder it works in.
- **Claude Code** reads `CLAUDE.md`. From version 2.1.277 it reads `AGENTS.md` too, but only when there is no `CLAUDE.md` or `CLAUDE.local.md` in the folder it works in or above it. If your project has a `CLAUDE.md`, import `AGENTS.md` into it with a line `@AGENTS.md`.

## The instruction file of the example project

The tutorial on [Working with the Agent](/guides/ai-agents/working-with-the-agent/) uses a small web shop project, [`robotcodedev/webshop-ai-example`](https://github.com/robotcodedev/webshop-ai-example), with this `AGENTS.md`:

```markdown title="AGENTS.md"
# Web shop acceptance tests

Robot Framework tests for our web shop, run with RobotCode.

## Environment

- Python dependencies are managed with uv (`pyproject.toml`, `uv.lock`). The project's environment is `.venv`, and it is active in the terminal. After changing `pyproject.toml`, run `uv sync`.
- RobotCode is installed in `.venv` with all extras. Use the RobotCode skill for all work on the tests.
- The Browser library needs `rfbrowser init` after it is installed or updated. It downloads Playwright and the browsers.

## The shop

- The suites talk to the shop through `libraries/ShopLibrary.py`, which runs the shop in memory, so they need no server. The shop's test users, prices and stock are defined there.
- The shop's web page, for tests with the Browser library, is served at `BASE_URL`, locally `http://localhost:8080`.
- Profiles in `robot.toml`: `dev` runs locally in Firefox, `ci` runs against the staging shop. The CI runs `robotcode -p ci robot` (`.github/workflows/tests.yml`).

## Conventions

- There is one suite per area in `tests/`: login, cart, orders and search. Each suite names its team with `Metadata    Owner`. The suites for login, cart and orders also tag their tests with their area (`Test Tags`).
- Tests that belong to the smoke test are tagged `smoke`.
- The tests of login, cart and orders name their requirement with `[Metadata]    Requirement    SHOP-<number>`, and those with a high risk also have `[Metadata]    Risk    high`. New tests do the same. The requirements are in `requirements/`, one Markdown file each.
- Keywords go into the resource file of their area in `resources/`, and keywords in Python into `libraries/ShopLibrary.py`.
- Runs write their results to `results/`.
```

Everything else, such as the paths, the variables and the settings of the profiles, the agent reads from `robot.toml` through `robotcode`.

