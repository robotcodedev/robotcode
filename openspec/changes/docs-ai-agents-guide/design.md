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
- The guide teaches working with an agent step by step, for the reader's own project and any agent; sessions that really happened show each step.
- Every section and every anchor that is linked today stays reachable on the page that takes it over.

**Non-Goals:**
- Publishing the example project. The Briefing page shows its instruction file, and the overview of the tutorial describes the project in a few sentences. The reader works with their own project (decided by the maintainer at the review, 2026-10-29).
- Bringing the example project of the robot.toml guide (a web shop with other paths and profiles) in line with this one.
- Changing the skill. Findings from the recordings go to the maintainer (D9).

## Decisions

### D1: Pages, paths and orders

| File in `guides/ai-agents/` | Path | Title / label | Order |
| --- | --- | --- | --- |
| `index.mdx` (the current page, moved with `git mv`) | `/guides/ai-agents/` | "Working with AI Agents" / "Overview" | 150 |
| `setting-up.md` | `/guides/ai-agents/setting-up/` | "Setting Up Your Agent" / "Setting Up" | 150.1 |
| `briefing.md` | `/guides/ai-agents/briefing/` | "Briefing the Agent" | 150.2 |
| `how-the-skill-works.md` | `/guides/ai-agents/how-the-skill-works/` | "How the RobotCode Skill Works" / "How the Skill Works" | 150.3 |
| `working-with-the-agent/index.mdx` | `/guides/ai-agents/working-with-the-agent/` | "Working with the Agent" / "Overview" | 150.4 |
| `working-with-the-agent/<step>.md`, the seven steps of D3 | `/guides/ai-agents/working-with-the-agent/<step>/` | the step's title / its number and title, such as "Getting to Know the Project" / "1. Getting to Know the Project" | 150.41–150.47 |
| `troubleshooting.md` | `/guides/ai-agents/troubleshooting/` | "Troubleshooting AI Agents" / "Troubleshooting" | 150.5 |

- **Labels:** `GROUP_LABELS` gets `"ai-agents": "AI Agents"` and `"working-with-the-agent": "Working with the Agent"`.
- **Order:** With order 150, the group comes after Project Configuration (100–100.7) and before Tips & Tricks (200–220). The page was between Command Line and Project Configuration; the maintainer moved the group on 2026-10-29. The introduction and the description of `guides/index.mdx` name the groups in this order too (decided by the maintainer, 2026-10-30). How the Skill Works comes before Working with the Agent (decided by the maintainer at the review, 2026-10-29).
- **Overview title:** It keeps "Working with AI Agents", in the pattern of the other overviews.
- **Working with the Agent:** a tutorial in a group of its own within AI Agents: an overview (what the tutorial teaches, the version line, the legend and the example project) and the seven steps of D3. The labels number the steps; the titles do not. At first it was one page. At the review on 2026-10-29 the maintainer asked for a page per task in the sidebar, and then for a tutorial in place of the task pages: the guide should teach rather than show what the agent can do.

### D2: Where the current content goes

- **Overview:**
  - the introduction (why an agent needs `robotcode`), shortened;
  - the agents it works with;
  - three steps: set up, brief, ask;
  - the steps of the tutorial, each linked, in place of the nine abilities of the home page (decided by the maintainer at the review, 2026-10-29);
  - `<AreaOverview area="guides/ai-agents" />`.
- **Setting Up:**
  - Prerequisites, "In VS Code (GitHub Copilot Chat)", the marketplace with the commands per agent, "Matching your RobotCode version", "Adding the marketplace from VS Code" and "Avoiding duplicates", with these headings kept, so their anchors stay.
  - New: "In PyCharm". The usual agents work in PyCharm as well; RobotCode's PyCharm plugin does not bring the plugin for them yet (`pycharm/compared-with-vscode.mdx`), so they install it from the marketplace, with RobotCode's command line tools in the project's environment.
  - New: "Checking that it works". Ask which tests are tagged `smoke`, and the agent answers with a `robotcode discover` command instead of searching the files. `robotcode discover info` shows the environment it uses.
- **Briefing the Agent:**
  - "Give the agent project context", with its four points;
  - which file each agent reads: `AGENTS.md`; Claude Code from 2.1.277 when there is no `CLAUDE.md`, else `@AGENTS.md` in `CLAUDE.md`; `.github/copilot-instructions.md` for GitHub Copilot.
  - the complete `AGENTS.md` of the example project (D5);
  - with task 3.8: the advice to name the RobotCode skill in the instruction file instead of repeating how to run the tests (D5).
- **Working with the Agent:** the tutorial of D3, with the sessions as evidence. The one-line prompts of "What you can ask" go to "How to ask the agent" of the step they belong to.
- **How the Skill Works:**
  - "How it works";
  - when the skill is loaded (from Troubleshooting: by relevance; name the subject or the skill);
  - the kinds of requests and their commands, in the order of the skill's "Pick the mode first";
  - the documentation the agent looks up: `robotcode doc` first, RobotCode's `llms-full.txt` for the CLI;
  - installing `robotcode` when it is missing: the agent asks first;
  - "AI-agent detection" with its table, heading kept.
- **Troubleshooting:** the five entries of today, by symptom. Its links point to the new pages.
- **See also:** its links go to the pages they belong to.

### D3: The tutorial and its sessions

| Step | Title and file in `working-with-the-agent/` | What the reader learns | Sessions |
| --- | --- | --- | --- |
| 1 Getting to know the project | "Getting to Know the Project", `getting-to-know-the-project.md` | which tests, tasks, tags, suites and keywords the project has, resolved the way Robot Framework does; which tests cover a requirement; counts and statistics in a large project | Coverage, Keywords, A large project |
| 2 Writing a test from a requirement | "Writing a Test from a Requirement", `writing-a-test.md` | learning a library from its documentation, trying keywords in the REPL, then writing, checking and running the test; a task the same way | From a requirement, Keywords in the REPL, A task |
| 3 Running what you need | "Running What You Need", `running-what-you-need.md` | a single test, a tag or a suite, with a profile | Smoke tests on staging, Another browser |
| 4 Finding out why a test failed | "Finding Out Why a Test Failed", `finding-out-why-a-test-failed.md` | reading the results of a finished run before running anything again; comparing two runs | A failing test, Comparing runs |
| 5 Debugging step by step | "Debugging Step by Step", `debugging-step-by-step.md` | stopping a run at a line and steering it turn by turn | Debugging step by step |
| 6 Checking before a push | "Checking Before a Push", `checking-before-a-push.md` | diagnostics and unused code, then the tests and their results | Before a push |
| 7 A profile for the CI server | "A Profile for the CI Server", `a-profile-for-the-ci-server.md` | writing `robot.toml` from the settings' documentation and checking it | A profile for the CI server |

- **A step:** "What you learn", "How to ask the agent" (prompts with placeholders such as `<your test>`, the recorded prompt as an example, and the prompts of "What you can ask" that belong there), "What the agent does" (the commands it uses and why, with excerpts, D4) and "What to watch out for", then the sessions (D4). The steps build on each other in what the reader learns, not on the state of a project.
- **The reader's own project:** The text speaks of the reader's project, and the sessions show the example project. A step that needs a failing test or a problem in the project says when it applies.
- **Any agent:** The text holds for every agent the overview names. Where agents differ, such as in driving the debugger or the REPL turn by turn, the step says how, from the facts of D9.
- **Checked statements:** Statements about the skill are checked against SKILL.md and its references on `next`, statements about `robotcode` against the CLI guides or the CLI itself.

The sessions, by step:

| Step | Session | Starts from | First prompt |
| --- | --- | --- | --- |
| 1 Getting to know the project | Coverage | the project | "Which tests cover the cart requirements SHOP-201 to SHOP-203?" |
| 1 Getting to know the project | Keywords | the project | "What arguments does our `Create Order` keyword take?" |
| 1 Getting to know the project | A large project | the generated project after a run (D7) | "How many tests does this project have, and how are they split across the teams?" |
| 2 Writing a test from a requirement | From a requirement | the project | "I want to test our web shop with the Browser library, but I've never used it. How do I open a page, type into a field and check a text?" |
| 2 Writing a test from a requirement | Keywords in the REPL | the project | "Open a REPL with our orders resource and order two coffees." Later: which variables there are now, ordering a mug (sold out, so `Create Order` fails), the status of the coffee order. |
| 2 Writing a test from a requirement | A task | the project plus `data/restock.csv` (products and quantities) | "Write a task that orders every product in `data/restock.csv` and logs the order ids, then run it." |
| 3 Running what you need | Smoke tests on staging | the project | "Which tests are in our smoke test?" |
| 3 Running what you need | Another browser | the state after "From a requirement" | "Can the Browser library run our web tests in Firefox?" |
| 4 Finding out why a test failed | A failing test | the project after a full run (Login Works fails) | "Why did `Login Works` fail in last night's run?" |
| 4 Finding out why a test failed | Comparing runs | the state after "A failing test", the earlier run kept in `results/nightly/` | "Run all tests and tell me what changed compared with last night's run in `results/nightly`." |
| 5 Debugging step by step | Debugging step by step | the project | "Run the order tests in the debugger and stop at line 19 of `tests/orders.robot`." Later: the variables, the call stack, a second breakpoint at line 21 of `resources/orders.resource` (`Should Be Equal    ${status}    ${expected}`), "continue to the next breakpoint" (`Express Order` reaches it again), continue to the end. |
| 6 Checking before a push | Before a push | the project (with the `Submit Ordr` typo) | "Check the project for problems before I push." |
| 7 A profile for the CI server | A profile for the CI server | the project | "Add a profile for our CI server: the staging shop, a browser without a window, and the results in `results/ci`." |

- **First prompts:** They come from the home page's scenarios where one exists.
- **Later prompts:** They react to the agent's answers and are written during the recording. Where the home page steers to a tool ("Show me in the debugger what the shop returns there"), the recording steers the same way.
- **Order:** "Another browser" and "Comparing runs" build on the session before them, and the other sessions start from a fresh copy of the project.
- **Links between steps:** A text that refers to a session in another step links it ("Another browser" to "From a requirement", "Debugging step by step" to "Keywords in the REPL").
- **Interactive sessions:** "Debugging step by step" and "Keywords in the REPL" are the two the maintainer asked for: the user steers each turn, and the debugger or the REPL keeps running between the prompts. Since task 3.8, Claude Code drives them with `robotcode session` (D9).

### D4: How a session is shown

- **Prompt:** text that starts with **You:**, in a frame of its own.
- **Command:** a code block in a terminal frame (`console`), with `$ ` and the command as Claude Code ran it, then its output.
- **File read:** a line **Read** with the file name, then the part of the file that matters, as a code block.
- **File written:** **Wrote**, then the file as a code block.
- **File changed:** **Edited**, then a `diff` code block of the change.
- **Skill loaded:** the line *Loaded the skill `robotcode`*.
- **Answer:** text that starts with **Agent:**, as Claude Code wrote it, in a frame of its own. A heading in an answer is shown as a bold line with the same words, so that it does not become a heading of the page.
- **Omissions:** Left-out lines of output, files or answers are replaced by one line `…`. A left-out step (for example a `ls`) is replaced by *…*.
- **Local paths:** Paths of the recording machine are replaced, so that the page shows neither the maintainer's folders nor the recording's scratch folders (decided by the maintainer, 2026-10-29). Nothing else is changed.

  | In the recording | On the page |
  | --- | --- |
  | the session project (`…/scratchpad/agent-work/webshop`) | `~/webshop` |
  | the large project (`…/agent-work/large`) | `~/shop-platform` |
  | other folders in the scratchpad, `/tmp/claude-1000/` | `/tmp` |
  | the RobotCode checkout | `~/robotcode` |
  | the Claude Code configuration of the recordings | `~/.claude` |
  | the rest of the home folder | `~` |

  `check_shortened.py` applies the same replacements to the complete session before it compares.
- **Version line:** It is on the overview of Working with the Agent: "Recorded on <date> with Claude Code <version> (<model>) and RobotCode". It names RobotCode without a version (decided by the maintainer on 2026-11-03), and a line of a session that prints RobotCode's version is left out.

- **Frames:** The session is in a frame that sets it apart from the guide's text; in it, each prompt is a bubble on the right and each answer has an accent line on the left, as in the agent demo of the home page. Without them, the answers could not be told from the guide's text, so the maintainer chose frames at the review on 2026-10-29. `assemble_page.py` puts a `<div>` with the class `rc-session`, `rc-session-prompt` or `rc-session-answer` around them, with blank lines, so that Astro renders the Markdown inside (`rehype-raw`). Their look is in `docs/src/styles/custom.css`, with Starlight's colors for both themes. `page/*.md` and `check_shortened.py` stay without frames.
- **Collapsed:** Each session is a `<details>` element below its step's explanation; its `<summary>` names the session and its first prompt. Starlight styles `<details>` already, and `getting-started/vscode.mdx` uses it. The frames stay inside.
- **Excerpts:** An excerpt in a step's explanation is a verbatim part of a session below it, as shown there (neutral paths, `…` for left-out lines), introduced as an excerpt of that session.
- **Where the text lives:** The overview of the tutorial and the step pages are written by hand in `docs/`, so they can be edited as text. `assemble_page.py` fills each session in between `<!-- session: <name> -->` and `<!-- /session -->`, collapsed and framed, from `page/<name>.md`, and checks every excerpt marked with `<!-- excerpt: <name> -->` against the complete Markdown of that session, as `check_shortened.py` does. Before, it wrote the whole pages from texts kept in the git-ignored playground, so an edit in `docs/` would have been lost the next time it ran.

Rejected: rendering the sessions with the home page's component, which the maintainer turned down for Markdown, so that the page reads as documentation and can be edited as text. Rejected at the review: the answers as quotes, which Starlight draws with a thin line only, or as asides.

### D5: The example project and its instruction file

- **The session project:** It is a copy of the demo project's project files: `robot.toml`, `pyproject.toml`, `libraries/`, `resources/`, `tests/`, `requirements/`, `webshop/` and `.github/`.
  - Left out are the playground's own files: `README.md` (it says that `Login Works` fails on purpose), `capture.sh`, `agent/` (the test of the home page demo), `.robotignore` (it only hides `agent/`), the folders of the VS Code, PyCharm and Neovim harnesses, `screenshots/`, `results/` and the caches.
  - In their place, the copy gets a short `README.md` of its own and becomes a git repository with a `.gitignore` (`results/`, `.venv/`, caches) and a first commit, as a real project would be. Without them, the agent in "Before a push" rightly reported the missing README and the missing `.gitignore`. Only the absolute paths of the checkout in `pyproject.toml` stay, as long as robotcode comes from the checkout.
- **`AGENTS.md`:** It is written for this project and shown on the Briefing page, and Claude Code reads it, since the session project has no `CLAUDE.md`. It covers:
  - uv and `.venv`;
  - `rfbrowser init` after installing or updating the Browser library;
  - the shop: runs in memory, `BASE_URL` per profile, `dev` and `ci`;
  - conventions: area tags, `[Metadata]    Requirement`, `Risk`, keywords in `resources/`, Python keywords in `libraries/ShopLibrary.py`;
  - RobotCode in `.venv`, and the RobotCode skill named for all work on the tests instead of a rule on how to run them.
- **The skill instead of a run rule:** The first recordings used the line "Run tests with `robotcode robot`, not with `robot`, so that `robot.toml` and its profiles apply". It repeats what the skill says, and as a standing rule it names only one of the ways the skill chooses from. At the review on 2026-10-30, the maintainer had it replaced by naming the skill. Task 3.8 records all 13 sessions again with the new file; until then, the Briefing page shows the file the sessions were recorded with.

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
  - For task 3.8, the recordings take the improved skill with `--plugin-dir` from the working copy of robotframework-agent-plugins on `next`, and the plugin installed in the configuration is off for the session (`--settings`, so that no file lands in the session project; decided by the maintainer on 2026-11-02). Until the release, that skill is only on `next`, and the marketplace has the released one. The site goes online only with a `v*` tag, so readers get the sessions together with that skill. `neutral_paths.py` replaces the path of the plugin folder, which can show up in a session.
  - Also for task 3.8: robotcode comes from a snapshot of the checkout's last commit in the work folder, so that unfinished work of a parallel session stays out of the recordings; `neutral_paths.py` shows it as `~/robotcode`. `XDG_RUNTIME_DIR` is a short folder of the recording, so that the agent sees only its own sessions.
  - A session runs as one process: `claude -p --input-format stream-json --output-format stream-json`, with `--strict-mcp-config` (no MCP server, also none of the account) and `--no-chrome`. The script writes each prompt to its input when the answer to the one before has arrived.
  - This keeps the agent's background commands, such as a paused debugger or a REPL, running between the user's prompts: with this input, a background command may run 30 minutes, up to 2 hours.
  - Rejected: one `claude -p --resume` per prompt. Each run ends with its answer, and a run whose prompt is passed as text waits at most 10 minutes for its background commands and then stops them. A debugger started for one prompt would be gone by the next.
  - Before the first session, `claude mcp list` in that configuration must list no server.
  - Found while setting it up:
    - A login brings the account's claude.ai connectors and synced skills along. The configuration's `settings.json` therefore sets `disableClaudeAiConnectors: true`, `syncClaudeAiPlugins: false` and `syncClaudeAiSkills: false`. What remains are Claude Code's bundled skills and plugins, which every user has.
    - `claude plugin …` must not run in `~`: there, `~/.claude/settings.json` counts as project settings.
    - Stream-json output needs `--verbose`, and `--replay-user-messages` puts the prompts into the transcript.
- **Permissions:**
  - `--permission-mode auto` lets Claude Code's classifier approve what a user would approve, such as edits in the session project or a loop over `robotcode doc` calls. It blocks what is risky.
  - `--allowedTools` allows `robotcode` commands and read-only shell commands without the classifier, and `--permission-prompts none` denies what the classifier blocks without a prompt.
  - When a denial changes the course of a session, the permissions are widened and the session recorded again.
  - Rejected: `--permission-mode acceptEdits` with the allow list alone. In the first recording it denied a `for` loop over `robotcode doc keyword` ("A variable in this command can't be checked before it runs"), and the agent reported the denial in its answer. A user at a prompt would simply have approved it.
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
- **Shortening:** Done by hand on that Markdown, only by leaving parts out (D4). The version line takes the model, Claude Code's version and the date from the transcript's init event.

### D9: The recordings test the skill

The recordings are also a test of the skill and the plugin. The maintainer chose to record first, collect the findings and improve afterwards.

- **Not edited into shape:** A session is never edited into shape.
- **Findings:** Every place where the agent goes against the skill, or where the skill's guidance is missing or wrong, goes into `playground/agent-skill-befunde.md` (git-ignored, like the other findings lists), with the session and the transcript lines. Examples: the agent greps instead of using `discover`, re-runs instead of debugging, loads `output.xml`, or sends a fixed `printf` sequence instead of steering the debugger or the REPL turn by turn.
- **Improvements:** They are changes of their own, in robotframework-agent-plugins for the skill and in robotcode for the CLI, planned after the recordings. They are not part of this change. For the CLI they were `repl-prompt-and-statement-results` and `cli-sessions`, for the skill it is `skill-sessions`.
- **The notes on driving the REPL and the debugger:** "Driving the REPL" on `writing-a-test.md` and "Driving the debugger" on `debugging-step-by-step.md` describe the named pipe and the fixed list of inputs. With task 3.8 they say that the agent drives both with `robotcode session` and link to the CLI guide on sessions, also for what happens in a sandbox.
- **Sessions with a finding:** They go into their step as recorded, like the others. Once the improvement is applied, they are recorded again and replace the old version.
  - Decided by the maintainer after the recordings (2026-10-29).
  - Rejected: keeping sessions with a finding off the page until then (the first version of this decision). With six of twelve sessions affected, it would have left the sections on writing tests and failing tests with one session each.
- **Findings known before the first recording:**
  - **The skill has no "how" for interactivity.** It says to drive the debugger and the REPL interactively, but not how. VS Code's Copilot has `send_to_terminal` and `get_terminal_output` (since 1.115 for background terminals, 1.116 also for visible ones), and Codex has `exec_command` with `write_stdin`. Claude Code has no tool that writes to a running command's input.
  - **The FIFO trial (2026-10-29, demo project):** Input from a FIFO held open and output into a log file. For `robot-debug` this already works turn by turn: the prompt `(rdb) ` ends each answer. `robotcode repl` runs the statements, but it prints `>>> ` only when its input is a terminal (`console_interpreter.py:940-942`). So nothing shows when a statement is done, and a statement without output leaves nothing in the log.
  - **Windows has no `mkfifo`.** That recipe would not apply there as it is. PowerShell can redirect the input and output of a running process too; the maintainer has done that (2026-10-30).

### D10: Links

- `#ai-agent-detection` in `news/v2-6-0.md` and `guides/cli/repl.md` → `/guides/ai-agents/how-the-skill-works/#ai-agent-detection`;
- `#matching-your-robotcode-version` in `news/v2-8-0.mdx` → `/guides/ai-agents/setting-up/#matching-your-robotcode-version`;
- `#adding-the-marketplace-from-vs-code` in `guides/vscode/index.mdx` → `/guides/ai-agents/setting-up/#adding-the-marketplace-from-vs-code`;
- `guides/pycharm/compared-with-vscode.mdx` → `/guides/ai-agents/setting-up/#in-pycharm`.

In a news post, only the link target changes and never its text (decided by the maintainer, 2026-10-29): a news post belongs to its release.

The links without an anchor keep `/guides/ai-agents/`. `CONTRIBUTING.md` ("Groups of guides") lists `ai-agents/` among the folders.

## Risks / Trade-offs

- [Sessions grow stale when robotcode's output or the skill changes] → The raw transcripts, the script and the prompts stay in the playground, so a session can be recorded again. The version line says what the sessions show.
- [A real agent answers differently each time] → Accepted. The sessions show one real run. The prompts are kept in the playground, not the answers.
- [The recordings cost time and run on the maintainer's account] → Thirteen sessions of a few prompts each. The maintainer logs in once, and the script runs them one after another.
- [The page shows sessions with a finding until the improvements] → Accepted by the maintainer. Task 3.8 records them again after the improvements and replaces them, so the change stays open until then.
- [Absolute paths of the maintainer's machine could show in a session, for example if the agent reads `pyproject.toml`] → Such lines are left out (D4).
- [The sessions make long pages] → They are collapsed below the explanation of their step (D4).
- [Excerpts and explanations grow stale when a session is recorded again (task 3.8)] → `assemble_page.py` checks every excerpt against its session and names the ones that no longer match.
- [Steps 4 and 6 need a failing test or a problem in the reader's project] → The step says when it applies, and its sessions show it in the example project.
