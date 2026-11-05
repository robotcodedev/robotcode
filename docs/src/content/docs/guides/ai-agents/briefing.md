---
title: Briefing the Agent
description: What to write down about your project for an AI agent, in which file each agent reads it, and the complete instruction file of the example project used on Working with the Agent.
sidebar:
  label: Briefing the Agent
  order: 150.2
---

The skill teaches the agent *how* to drive `robotcode`, and `robotcode` resolves everything in your configuration at runtime — paths, profiles, tags, suites, installed library versions — so you never have to repeat that for the agent.

What it **can't** infer is the surrounding setup and intent. Capturing those once in your agent's instructions file — `AGENTS.md` (an emerging cross-agent convention), `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, or whatever your agent reads — saves it from rediscovering them on every task and keeps it from guessing wrong. Worth recording:

- **Environment & package manager** — which tool manages dependencies (`uv`, `hatch`, `poetry`, `pip`, …) and where the project's virtual environment lives, so the agent runs `robotcode` from the right interpreter (see [Prerequisites](/guides/ai-agents/setting-up/#prerequisites)).
- **Installed libraries and their setup steps** — especially any one-off initialization needed after an install or update. For example, Browser Library needs `rfbrowser init` to download its Playwright browsers before its keywords work; an agent that doesn't know this runs into confusing failures.
- **The system under test** — what the application is, how to reach it (base URLs per environment, which profile points where), and any test data or accounts. Keep secrets out — describe *how* credentials are provided (env vars, a vault), not the values themselves.
- **Project conventions** — naming, tags, suite layout, and where new keywords belong, so generated tests match what you already have.

Name the RobotCode skill there instead of saying how to run the tests, as in *"Use the RobotCode skill for all work on the tests."* A rule such as "run tests with `robotcode robot`" repeats what the skill says, and as a standing rule it names only one of the ways the skill chooses from, such as the debugger or the results of a finished run.

Keep it short and factual; this is standing context the agent reads on every request, not a place to duplicate `robot.toml`.

## Which file the agent reads

`AGENTS.md` in the project's root folder is the file that all three agents of this guide read, so one file serves a team that uses several of them:

- **GitHub Copilot** in VS Code reads `.github/copilot-instructions.md` and `AGENTS.md`. The setting `chat.useAgentsMdFile`, on by default, controls `AGENTS.md`.
- **Codex** reads the `AGENTS.md` files from the project's root folder down to the folder it works in.
- **Claude Code** reads `CLAUDE.md`. From version 2.1.277 it reads `AGENTS.md` too, but only when there is no `CLAUDE.md` or `CLAUDE.local.md` in the folder it works in or above it. If your project has a `CLAUDE.md`, import `AGENTS.md` into it with a line `@AGENTS.md`.

## An example

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

It names the environment, the RobotCode skill and how to set up the Browser library, says where the shop comes from and what the profiles point to, and lists the conventions a new test should follow. Everything else, such as the paths, the variables and the profiles' settings, the agent reads from `robot.toml` through `robotcode`.

