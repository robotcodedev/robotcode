# Design

## Context

See `proposal.md` for the motivation. `playground/robotcode-demo/agent-sessions/record.sh` already defines the project the sessions start from: its `restore` copies `robot.toml`, `pyproject.toml`, `libraries`, `resources`, `tests`, `requirements`, `webshop` and `.github`, adds `uv.lock` and `AGENTS.md`, uses `README.project.md` as `README.md` and writes a `.gitignore`. The rest of the 1.2 GB folder is the harness, recordings, screenshots and `.venv`.

`robotcode session`, which Claude Code and GitHub Copilot CLI need for the REPL and the debugger, isn't in release 2.8.0. It comes with the next release, planned for mid-November. PyPI has dev builds of it, uploaded nightly. The live site has `/guides/ai-agents/`, but `/guides/ai-agents/working-with-the-agent/` only appears with the next deployment of the site.

Tried on 2026-11-04 with a copy of these files, with `[tool.uv.sources]` removed and `robotcode[all]>=2.9.0.dev0`:

- `uv lock --python 3.13` resolves robotcode 2.9.0.dev115, robotframework 7.5.1 and robotframework-browser 20.6.0 and 21.0.0, and `uv sync` works.
- `robotcode robot` gives 13 tests, 12 passed, 1 failed (`Tests.Login.Login Works`: `Welcome back, alice! != Welcome back, Alice!`).
- `robotcode analyze code` reports one error, `KeywordNotFound` for `Submit Ordr`. `robotcode session --help` works.

## Goals / Non-Goals

**Goals:**

- A reader can read the example's code and run it with what is public today.
- The repository stays the start of the recorded sessions, apart from the differences named below.

**Non-Goals:**

- Sessions that can be repeated exactly. The guide already says that another agent or another day gives other steps.
- Keeping the playground and the repository in sync automatically.

## Decisions

### An own repository

The maintainer chose it over a folder in the robotcode repository and over a docs page. In a folder of the robotcode repository, Claude Code wouldn't read the example's `AGENTS.md`, because its documentation says it reads only `CLAUDE.md` when one lies above the working directory. A docs page can only be read, not run.

### Content and differences from the recordings

The content is what `restore` builds, plus `data/restock.csv`, which `record.sh` only copies for the session on a task and which the prompt of that session names, plus a `LICENSE`. `agent/`, `capture.sh`, `my.html`, `nvim`, `vscode`, `pycharm`, `agent-sessions` and `screenshots` stay out.

| File | Difference from the recordings |
| --- | --- |
| `pyproject.toml` | no `[tool.uv.sources]`; `robotcode[all]>=2.9.0.dev0`; name `webshop-ai-example` and a description that fits (no session shows the old name) |
| `uv.lock` | new, resolved from PyPI |
| `.github/workflows/tests.yml` | `on: workflow_dispatch` instead of `on: push`; `setup-uv` and `uv sync --locked` instead of `setup-python` and `pip install` |
| `robot.toml`, `tests/*.robot` | `resources` on the `python-path`, and resources imported by name instead of with relative paths |
| `README.md` | the additions below |

The licence is Apache-2.0, like robotcode and `rbcn25-mastering-robotcode`. That is an assumption of this plan, not a decision of the maintainer.

### A dev build until the release

The maintainer chose to publish now with `robotcode[all]>=2.9.0.dev0` rather than wait for the release or use 2.8.0, which has no `robotcode session`. `uv.lock` pins the dev build, so a clone gets what was tested. With the next release, the bound goes to the released version and `uv.lock` is refreshed; a `TODO:` on the guide's overview reminds of that, because the maintainer reviews those comments before each release.

### The workflow only starts by hand

`Login Works` fails on purpose, so the workflow would be red on every push. The maintainer chose `on: workflow_dispatch`, with Actions left on, over turning Actions off and over leaving it red. The sessions keep showing `on: push`, and one sentence on the guide says so.

### The workflow installs with `uv`

The workflow first came unchanged from the playground, with `setup-python` and `pip install robotframework robotcode[runner]`. The maintainer questioned that. `pip` ignores `uv.lock`, so it would install release 2.8.0 without `robotcode session` and without the Browser library, while `AGENTS.md` says the dependencies are managed with `uv`.

The workflow now follows uv's guide on GitHub Actions: `astral-sh/setup-uv` and `actions/checkout` pinned to a commit with the version as a comment, a fixed uv version, `uv sync --locked`, then `uv run`. The action's `python-version` input keeps Python 3.13, because the repository has no `.python-version` for `uv python install` to read. The steps ran on a clean clone with uv 0.13.7 and `UV_PYTHON=3.13`. The workflow itself hasn't run on GitHub, because it would fail on purpose.

### Resources are imported by name

The tests first came from the playground with relative imports such as `../resources/shop.resource`. The maintainer doesn't want those, because the resources can be found through the `python-path`. `robot.toml` now has `python-path = ["libraries", "resources"]`, as the guide on `robot.toml` already shows, and the six imports use the file's name. A clean clone gives the same results, and `robotcode doc keyword orders.resource` works too.

The evals' fixture keeps its relative imports: it isn't part of what readers get as an example.

### The skill's advice on style gives way

`references/authoring.md` said "Match the project's conventions" and then prescribed one, with `Resource    ../common.resource` as an import by name. The maintainer asked whether the skill should set conventions at all, since a project can already define them, and that an instruction file like `AGENTS.md` is only one of the places they can be. So the file now says in general terms that rules defined elsewhere come first and that what it says about style is a general recommendation. It says so once, near the top, so that it also covers the other advice, such as tags and extracting keywords. The line on imports states how a resource is found, says to do as the project's files do, and recommends importing by name for what they don't settle.

### The README

It keeps the text of `README.project.md` and adds what a reader needs. It says that some things are wrong on purpose but not which, so that an agent working in the repository isn't told the answers. It links to `/guides/ai-agents/`, which exists today and leads to the tutorial after the next deployment.

```markdown
# Web shop acceptance tests

The example project of [RobotCode's AI agents guide](https://robotcode.io/guides/ai-agents/): Robot Framework tests for a small web shop, in the state the guide's sessions start from. Some things in it are wrong on purpose, because the sessions find them.

## Setup

uv sync                     # Robot Framework, RobotCode and the Browser library in .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
rfbrowser init              # once, after installing or updating the Browser library

## Running the tests

robotcode robot              # all tests, against the local shop
robotcode -p dev robot       # in Firefox
robotcode -p ci robot        # against the staging shop, as the CI does

Results go to `results/`. The requirements the tests check are in `requirements/`.

Tests with the Browser library need the shop's page, at `http://localhost:8080`:

python -m http.server 8080 --bind 127.0.0.1 --directory webshop
```

The commands go in `sh` code blocks in the real file.

### The guide's text

`working-with-the-agent/index.mdx`, at the end of "The example project":

> Its code is in [`robotcodedev/webshop-ai-example`](https://github.com/robotcodedev/webshop-ai-example), in the state the sessions start from, so you can try the prompts there. Its README says how to set it up. Some things in it are wrong on purpose, because the sessions find them. Two things differ from the sessions: the tests import their resources by name through `python-path` instead of with relative paths, and the CI workflow installs the project with `uv` instead of `pip` and only starts by hand, because a test fails on purpose.

The same page's "You work with your own project and with the agent you set up" becomes "You work with your own project or the [example project](#the-example-project), and with the agent you set up". `ai-agents/index.mdx`'s "You work through them with your own project and the agent you use" becomes "You work through them with your own project or the example project, and with the agent you use". `briefing.md`'s "in a small web shop project with this `AGENTS.md`" becomes "in a small web shop project, [`robotcodedev/webshop-ai-example`](https://github.com/robotcodedev/webshop-ai-example), with this `AGENTS.md`".

### Working on it with our own sources

The repository stays free of local paths, and it needs nothing for our own work:

- **Recording:** `record.sh` copies the project and points it at a snapshot of the checkout, as today.
- **Evals:** `run.py` takes `--project`, `--venv` and `--plugin-dir`, so it can run in a clone with RobotCode and the skill from our working copies.
- **By hand:** activate `playground/robotcode-demo/.venv` in the clone and start the agent with `--plugin-dir` on `plugins/robotcode` of the `robotframework-agent-plugins` working copy, in Claude Code and GitHub Copilot CLI. Tried on 2026-11-04: `robotcode` then comes from `src/robotcode/cli/` of the checkout, with 13 tests found and the expected result. `uv run` would use the clone's own environment with the dev build instead, so this way doesn't use it.

## Risks / Trade-offs

- [The repository and `playground/robotcode-demo` can drift apart] → Changes to the example go into both by hand. The example rarely changes, and a new recording shows any difference.
- [A later recording would show `on: workflow_dispatch`, or the new README, only if the playground gets them too] → `record.sh` stays as it is for now. The sessions show the state they were recorded in.
- [The sessions show the relative imports in 3 places, `python-path = ["libraries"]` in 5 and `pip` until they are recorded anew] → The guide names both differences. The maintainer chose to record the sessions anew with the text pass; `playground/robotcode-demo` needs the same changes first, because `record.sh` reads it.
- [`uv.lock` pins a dev build until the release] → PyPI has kept the dev builds so far, and none is yanked. The `TODO:` replaces it with the release.
- [Publishing cannot be fully undone] → The repository is created only after the maintainer has seen the files.
