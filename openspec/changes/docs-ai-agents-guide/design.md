# Design

## Context

- **The current page:** `docs/src/content/docs/guides/ai-agents.md`, title "Working with AI Agents", label "AI Agents", order 90. Its sections, with their length in words:
  - "What you can ask" (216);
  - Prerequisites (70), "In VS Code (GitHub Copilot Chat)" (168), "Other agents — the marketplace" (417, with "Matching your RobotCode version", "Adding the marketplace from VS Code", "Avoiding duplicates");
  - "How it works" (452), "Give the agent project context" (255), "AI-agent detection" (263);
  - Troubleshooting (402), See also (70).
- **Links into the page:**
  - `/guides/ai-agents/` without an anchor: `AiAgents.astro` ("Set up your agent"), `cli/index.mdx`, `pycharm/compared-with-vscode.mdx`, `news/v2-6-0.md` (twice), `news/v2-8-0.mdx`.
  - With an anchor: `#ai-agent-detection` from `news/v2-6-0.md` and `guides/cli/repl.md`, `#matching-your-robotcode-version` from `news/v2-8-0.mdx`, `#adding-the-marketplace-from-vs-code` from `guides/vscode/index.mdx`.
  - Nothing outside `docs/` links the page.
- **Groups:** A group is a folder below `guides/` with an `index.mdx` that has the lowest `sidebar.order` of the group and lists its pages with `<AreaOverview>`. Its label comes from `GROUP_LABELS` in `docs/src/routeData.ts` ("Groups of guides" in `CONTRIBUTING.md`). The other group overviews are titled "Working in VS Code", "Working in PyCharm" and "Working on the Command Line".
- **The home page sessions:**
  - `AgentDemo.astro` has seven scenarios: From a requirement, Smoke tests, Coverage, A failing test, Browsers, Keywords and Analysis. Their commands and output come from `playground/robotcode-demo/capture.sh`, and their conversation is written.
  - The demo project (git-ignored, README there) is a web shop that runs in memory (`libraries/ShopLibrary.py`) and has 13 tests. `Login Works` fails on purpose, and `resources/orders.resource` calls `Submit Ordr`.
  - Its `robot.toml` has `paths = ["tests"]` and the profiles `dev` (Firefox) and `ci` (staging shop). `capture.sh` serves `webshop/` at `BASE_URL` for the Browser library.
  - `pyproject.toml` takes robotcode from this checkout with `path = "../.."` sources, so `robotcode --version` reports the checkout's version (2.8.0 today).
- **Claude Code facts** (installed 2.1.312; docs at code.claude.com):
  - `CLAUDE_CONFIG_DIR` moves settings, session history, plugins and the login to another directory.
  - From 2.1.277 on, Claude Code reads `AGENTS.md` as project instructions when there is no `CLAUDE.md` or `CLAUDE.local.md` in the working directory or above it.
  - `claude -p` runs without prompts and takes these options: `--input-format stream-json` (further prompts in the same process), `--output-format stream-json`, `--session-id`/`--resume`, `--permission-mode`, `--allowedTools`, `--permission-prompts none`, `--strict-mcp-config` and `--no-chrome`.
  - Claude Code's Bash tool can run a command in the background and read its output from a file, but it has no way to write to a running command's input.
  - In a `-p` run, a background command may run 30 minutes (up to 2 hours with a longer timeout). If the prompt is passed as text, the limit is 10 minutes, and the run waits for its background commands after its answer.
- **The skill:** `plugins/robotcode/skills/robotcode/` in robotframework-agent-plugins, with SKILL.md and nine references (analyze, authoring, config, debugging, install, large-projects, repl, results, workflows). On the plugin's files, the marketplace (`main` = tag `robotcode--v2.8.0`) and `next` are the same.

## Goals / Non-Goals

**Goals:**
- What an agent does with the skill is shown by sessions that really happened, for every task the skill covers.
- Every section and every anchor that is linked today stays reachable on the page that takes it over.

**Non-Goals:**
- Publishing the example project. The Briefing page shows its instruction file, and the Working page describes the project in a few sentences.
- Bringing the example project of the robot.toml guide (a web shop with other paths and profiles) in line with this one.
- Changing the skill. Findings from the recordings go to the maintainer (D9).

## Decisions

### D1: Pages, paths and orders

| File in `guides/ai-agents/` | Path | Title / label | Order |
| --- | --- | --- | --- |
| `index.mdx` (the current page, moved with `git mv`) | `/guides/ai-agents/` | "Working with AI Agents" / "Overview" | 90 |
| `setting-up.md` | `/guides/ai-agents/setting-up/` | "Setting Up Your Agent" / "Setting Up" | 90.1 |
| `briefing.md` | `/guides/ai-agents/briefing/` | "Briefing the Agent" | 90.2 |
| `working-with-the-agent.md` | `/guides/ai-agents/working-with-the-agent/` | "Working with the Agent" | 90.3 |
| `how-the-skill-works.md` | `/guides/ai-agents/how-the-skill-works/` | "How the RobotCode Skill Works" / "How the Skill Works" | 90.4 |
| `troubleshooting.md` | `/guides/ai-agents/troubleshooting/` | "Troubleshooting AI Agents" / "Troubleshooting" | 90.5 |

- **Labels:** `GROUP_LABELS` gets `"ai-agents": "AI Agents"`.
- **Order:** With order 90, the group stays where the page was, between Command Line (10–70) and Project Configuration (100).
- **Overview title:** It keeps "Working with AI Agents", in the pattern of the other overviews.

### D2: Where the current content goes

- **Overview:**
  - the introduction (why an agent needs `robotcode`), shortened;
  - the agents it works with;
  - three steps: set up, brief, ask;
  - what the agent can do, in the nine abilities of the home page, each linked to its section on the Working page;
  - `<AreaOverview area="guides/ai-agents" />`.
- **Setting Up:**
  - Prerequisites, "In VS Code (GitHub Copilot Chat)", the marketplace with the commands per agent, "Matching your RobotCode version", "Adding the marketplace from VS Code" and "Avoiding duplicates", with these headings kept, so their anchors stay.
  - New: "In PyCharm". PyCharm has no plugin for AI agents (`pycharm/compared-with-vscode.mdx`). An agent such as Claude Code, GitHub Copilot CLI or Codex runs in PyCharm's terminal and installs the plugin from the marketplace, with RobotCode's command line tools in the project's environment.
  - New: "Checking that it works". Ask which tests are tagged `smoke`, and the agent answers with a `robotcode discover` command instead of searching the files. `robotcode discover info` shows the environment it uses.
- **Briefing the Agent:**
  - "Give the agent project context", with its four points;
  - which file each agent reads: `AGENTS.md`; Claude Code from 2.1.277 when there is no `CLAUDE.md`, else `@AGENTS.md` in `CLAUDE.md`; `.github/copilot-instructions.md` for GitHub Copilot.
  - the complete `AGENTS.md` of the example project (D5).
- **Working with the Agent:** the sessions (D3), each with a short note on what the agent did and why. The one-line prompts of "What you can ask" that no session shows go below the section they belong to.
- **How the Skill Works:**
  - "How it works";
  - when the skill is loaded (from Troubleshooting: by relevance; name the subject or the skill);
  - the kinds of requests and their commands, in the order of the skill's "Pick the mode first";
  - the documentation the agent looks up: `robotcode doc` first, RobotCode's `llms-full.txt` for the CLI;
  - installing `robotcode` when it is missing: the agent asks first;
  - "AI-agent detection" with its table, heading kept.
- **Troubleshooting:** the five entries of today, by symptom. Its links point to the new pages.
- **See also:** its links go to the pages they belong to.

### D3: The sessions of Working with the Agent

| Section | Session | Starts from | First prompt |
| --- | --- | --- | --- |
| Writing tests and tasks | From a requirement | the project | "I want to test our web shop with the Browser library, but I've never used it. How do I open a page, type into a field and check a text?" |
| Writing tests and tasks | A task | the project plus `data/restock.csv` (products and quantities) | "Write a task that orders every product in `data/restock.csv` and logs the order ids, then run it." |
| Writing tests and tasks | Keywords in the REPL | the project | "Open a REPL with our orders resource and order two coffees." Later: which variables there are now, ordering a mug (sold out, so `Create Order` fails), the status of the coffee order. |
| Running tests | Smoke tests on staging | the project | "Which tests are in our smoke test?" |
| Running tests | Another browser | the state after "From a requirement" | "Can the Browser library run our web tests in Firefox?" |
| Failing tests | A failing test | the project after a full run (Login Works fails) | "Why did `Login Works` fail in last night's run?" |
| Failing tests | Comparing runs | the state after "A failing test", the earlier run kept in `results/nightly/` | "Run all tests and tell me what changed compared with last night's run in `results/nightly`." |
| Failing tests | Debugging step by step | the project | "Run the order tests in the debugger and stop at line 19 of `tests/orders.robot`." Later: the variables, the call stack, a second breakpoint at line 21 of `resources/orders.resource` (`Should Be Equal    ${status}    ${expected}`), "continue to the next breakpoint" (`Express Order` reaches it again), continue to the end. |
| Knowing the project | Coverage | the project | "Which tests cover the cart requirements SHOP-201 to SHOP-203?" |
| Knowing the project | Keywords | the project | "What arguments does our `Create Order` keyword take?" |
| Knowing the project | A large project | the generated project after a run (D7) | "How many tests does this project have, and how are they split across the teams?" |
| Code quality | Before a push | the project (with the `Submit Ordr` typo) | "Check the project for problems before I push." |
| Configuration | A profile for the CI server | the project | "Add a profile for our CI server: the staging shop, a browser without a window, and the results in `results/ci`." |

- **First prompts:** They come from the home page's scenarios where one exists.
- **Later prompts:** They react to the agent's answers and are written during the recording. Where the home page steers to a tool ("Show me in the debugger what the shop returns there"), the recording steers the same way.
- **Order:** "Another browser" and "Comparing runs" build on the session before them, and the other sessions start from a fresh copy of the project.
- **Interactive sessions:** "Debugging step by step" and "Keywords in the REPL" are the two the maintainer asked for: the user steers each turn, and the debugger or the REPL keeps running between the prompts. With today's skill, Claude Code probably sends a fixed `printf` sequence instead (D9).

### D4: How a session is shown

- **Prompt:** a quote that starts with **You:**.
- **Command:** a code block in a terminal frame (`console`), with `$ ` and the command as Claude Code ran it, then its output.
- **File read:** a line **Read** with the file name, then the part of the file that matters, as a code block.
- **File written:** **Wrote**, then the file as a code block.
- **File changed:** **Edited**, then a `diff` code block of the change.
- **Skill loaded:** the line *Loaded the skill `robotcode`*.
- **Answer:** text that starts with **Agent:**, as Claude Code wrote it.
- **Omissions:** Left-out lines of output, files or answers are replaced by one line `…`. A left-out step (for example a `ls`) is replaced by *…*.
- **Version line:** It is at the top of the page: "Recorded on <date> with Claude Code <version> (<model>) and RobotCode <version>".

Rejected: rendering the sessions with the home page's component, which the maintainer turned down for Markdown, so that the page reads as documentation and can be edited as text.

### D5: The example project and its instruction file

- **The session project:** It is a copy of the demo project's project files: `robot.toml`, `pyproject.toml`, `libraries/`, `resources/`, `tests/`, `requirements/`, `webshop/` and `.github/`.
  - Left out are the playground's own files: `README.md` (it says that `Login Works` fails on purpose), `capture.sh`, `agent/` (the test of the home page demo), `.robotignore` (it only hides `agent/`), the folders of the VS Code, PyCharm and Neovim harnesses, `screenshots/`, `results/` and the caches.
- **`AGENTS.md`:** It is written for this project and shown on the Briefing page, and Claude Code reads it, since the session project has no `CLAUDE.md`. It covers:
  - uv and `.venv`;
  - `rfbrowser init` after installing or updating the Browser library;
  - the shop: runs in memory, `BASE_URL` per profile, `dev` and `ci`;
  - conventions: area tags, `[Metadata]    Requirement`, `Risk`, keywords in `resources/`, Python keywords in `libraries/ShopLibrary.py`.

### D6: Recording

The script `playground/robotcode-demo/agent-sessions/record.sh` (git-ignored) does the following.

- **Session project location:** The session project is outside the repository, in the scratchpad. Claude Code reads `CLAUDE.md` and `AGENTS.md` of the folders above its working directory. Inside the checkout it would read RobotCode's own contributor instructions and see RobotCode's git repository.
- **Environment:**
  - The copy's `pyproject.toml` gets the absolute path of the checkout in place of `../..`. `uv sync` then installs robotcode from the checkout, as in the home page demos.
  - `rfbrowser init` runs once.
  - `webshop/` is served at `BASE_URL` (`python3 -m http.server 8080`, as in `capture.sh`).
  - `XDG_CONFIG_HOME` points to an empty folder, so the maintainer's user `robot.toml` stays out.
- **Claude Code:**
  - `CLAUDE_CONFIG_DIR` is a folder of its own, in which the maintainer logs in once. Only the plugin from the marketplace is installed there (`claude plugin marketplace add robotcodedev/robotframework-agent-plugins`, `claude plugin install robotcode@robotframework-agent-plugins`).
  - A session runs as one process: `claude -p --input-format stream-json --output-format stream-json`, with `--strict-mcp-config` (no MCP server, also none of the account) and `--no-chrome`. The script writes each prompt to its input when the answer to the one before has arrived.
  - This keeps the agent's background commands, such as a paused debugger or a REPL, running between the user's prompts: with this input, a background command may run 30 minutes, up to 2 hours.
  - Rejected: one `claude -p --resume` per prompt. Each run ends with its answer, and a run whose prompt is passed as text waits at most 10 minutes for its background commands and then stops them. A debugger started for one prompt would be gone by the next.
  - Before the first session, `claude mcp list` in that configuration must list no server.
- **Permissions:**
  - `--permission-mode acceptEdits` lets the agent change files in the session project.
  - `--allowedTools` allows `robotcode` commands and read-only shell commands, and `--permission-prompts none` denies anything else without a prompt.
  - When a denial changes the course of a session, the list is widened and the session recorded again.
- **Outer environment:** The variables of the outer agent session are removed: `CLAUDECODE`, `CLAUDE_*` apart from `CLAUDE_CONFIG_DIR`, `AI_AGENT`, `AGENT`, `COPILOT_*` and the others of the harness list.
  - The outer session sets, for example, `CLAUDE_CODE_CHILD_SESSION`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_EFFORT` and a messaging socket. Without them the inner Claude Code runs as a session of its own.
  - robotcode then sees only the markers of the inner session.
- **Between sessions:** The project files are restored, and the per-project data in the configuration (session history and Claude Code's memory) is removed, so that no session builds on another.
- **Raw transcripts:** Each session's stream-json goes to `playground/robotcode-demo/agent-sessions/<session>.jsonl` and survives the scratchpad.

### D7: The large project

`agent-sessions/large_project.py` writes a project with about 5000 tests in about 500 suites:
- folders per team, tags for team, `smoke` and `regression`, `[Metadata]    Requirement`;
- a few dozen tests that fail on purpose;
- keywords from a resource with BuiltIn keywords only, so that a full run takes about a minute.

The script runs it once before the session, so the session can ask about the results too. It is generated into the scratchpad like the session project, without Browser or ShopLibrary.

### D8: Converting and shortening

- **Converter:** `agent-sessions/to_markdown.py` turns a `.jsonl` into the Markdown of D4, complete. It reads the prompts, the tool calls with their results (Bash, Read, Write, Edit, Skill) and the answers. The field names are checked against the first recording.
- **Shortening:** Done by hand on that Markdown, only by leaving parts out (D4). The version line takes the model, Claude Code's version and the date from the transcript's init event, and RobotCode's version from `robotcode --version` in the session project.

### D9: The recordings test the skill

The recordings are also a test of the skill and the plugin. The maintainer chose to record first, collect the findings and improve afterwards.

- **Not edited into shape:** A session is never edited into shape.
- **Findings:** Every place where the agent goes against the skill, or where the skill's guidance is missing or wrong, goes into `playground/agent-skill-befunde.md` (git-ignored, like the other findings lists), with the session and the transcript lines. Examples: the agent greps instead of using `discover`, re-runs instead of debugging, loads `output.xml`, or sends a fixed `printf` sequence instead of steering the debugger or the REPL turn by turn.
- **Improvements:** They are changes of their own, in robotframework-agent-plugins for the skill and in robotcode for the CLI, planned after the recordings. They are not part of this change.
- **Sessions with a finding:** They stay off the page and are recorded again once the improvement is applied. The other sessions go on the page as recorded.
- **Findings known before the first recording:**
  - **The skill has no "how" for interactivity.** It says to drive the debugger and the REPL interactively, but not how. VS Code's Copilot has `send_to_terminal` and `get_terminal_output` (since 1.115 for background terminals, 1.116 also for visible ones), and Codex has `exec_command` with `write_stdin`. Claude Code has no tool that writes to a running command's input.
  - **The FIFO trial (2026-10-29, demo project):** Input from a FIFO held open and output into a log file. For `robot-debug` this already works turn by turn: the prompt `(rdb) ` ends each answer. `robotcode repl` runs the statements, but it prints `>>> ` only when its input is a terminal (`console_interpreter.py:940-942`). So nothing shows when a statement is done, and a statement without output leaves nothing in the log.
  - **Windows has no `mkfifo`.** That recipe would not apply there.

### D10: Links

- `#ai-agent-detection` in `news/v2-6-0.md` and `guides/cli/repl.md` → `/guides/ai-agents/how-the-skill-works/#ai-agent-detection`;
- `#matching-your-robotcode-version` in `news/v2-8-0.mdx` → `/guides/ai-agents/setting-up/#matching-your-robotcode-version`;
- `#adding-the-marketplace-from-vs-code` in `guides/vscode/index.mdx` → `/guides/ai-agents/setting-up/#adding-the-marketplace-from-vs-code`;
- `guides/pycharm/compared-with-vscode.mdx` → `/guides/ai-agents/setting-up/#in-pycharm`.

The links without an anchor keep `/guides/ai-agents/`. `CONTRIBUTING.md` ("Groups of guides") lists `ai-agents/` among the folders.

## Risks / Trade-offs

- [Sessions grow stale when robotcode's output or the skill changes] → The raw transcripts, the script and the prompts stay in the playground, so a session can be recorded again. The version line says what the sessions show.
- [A real agent answers differently each time] → Accepted. The sessions show one real run. The prompts are kept in the playground, not the answers.
- [The recordings cost time and run on the maintainer's account] → Thirteen sessions of a few prompts each. The maintainer logs in once, and the script runs them one after another.
- [The change cannot be finished before the improvements] → The two interactive sessions, and any other session with a finding, go on the page only after they are recorded again with the improved skill or CLI. Until then, the change stays open with those tasks (3.8).
- [Absolute paths of the maintainer's machine could show in a session, for example if the agent reads `pyproject.toml`] → Such lines are left out (D4).
- [The page gets long with thirteen sessions] → Accepted with the choice of one page. Each section starts with what the agent can do, and the sessions follow.
