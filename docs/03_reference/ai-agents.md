# Working with AI Agents

AI coding agents are good at writing code and bad at guessing how *your* Robot Framework project is actually wired. Which files become suites, which tags a test really ends up with, where a keyword comes from, what a finished run contained — none of that is reliably visible by reading `.robot` files. It is decided at runtime by `robot.toml`, profiles, variables, the installed library versions, and pre-run modifiers.

**RobotCode** closes that gap by teaching the agent to work through the project's own [`robotcode`](cli.md) CLI instead of guessing. The agent discovers tests, runs suites, inspects results, looks up keywords, debugs failing tests at a real breakpoint, and explores live in the REPL — all through the same resolved view of the project that the rest of **RobotCode** uses. The result is an agent that behaves less like a generic code model and more like a Robot Framework engineer who knows your setup.

There are two pieces, and they work independently:

- **Chat plugins** (this page's main subject) — a RobotCode plugin that packages instructions for the agent. Today it ships a single *skill* that tells the agent *how* to use `robotcode`: which command answers which question, and which habits to avoid (don't grep for tests, don't load `output.xml` into the chat). The plugin is built to grow — more skills, agents, and other capabilities will ship in the same package.
- **AI-agent detection** ([below](#ai-agent-detection)) — the CLI noticing it runs inside an agent session and quietly adjusting its terminal output for clean capture.

**Who this is for:**

- **Developers using GitHub Copilot Chat in VS Code** — the plugin ships with the extension and is on by default.
- **Users of other agents** — Claude Code, Codex, GitHub Copilot CLI, and other [Open Plugins](https://open-plugins.com/)–compatible tools install the same plugin from a marketplace.
- **Anyone scripting agents against Robot Framework projects** — the CLI's agent-aware output makes capture predictable.

## What you can ask

Once the plugin is active, everyday Robot Framework requests are handled through the CLI with the right options, against your project's real configuration. For example:

- *"run the smoke suite with the `ci` profile"* — runs it through the selected profile and reports pass/fail counts
- *"rerun just the tests that failed last time"*
- *"why did `Login Works` fail in last night's run?"* — inspects the existing results, no re-run
- *"this test keeps failing — step through it and tell me what `${response}` is when it breaks"* — pauses the real run in the [debugger](robot-debug.md) and reads the live stack and variables, instead of re-running blindly or guessing
- *"break at `login.robot:42` and show me the variables there"*
- *"what tests and tags exist?"* — resolves the real set with `discover` (paths, profiles, variables, pre-run modifiers), not a file scan
- *"what arguments does our `Create Order` keyword take?"* — looks it up against the installed libraries and local resources
- *"is there already a keyword for waiting until the spinner is gone?"*
- *"try the new login flow against the real app, with a visible browser"* — drives it live in the REPL (no test written yet)
- *"set up a `prod` profile with `BASE_URL=https://prod.example.com`"*
- *"lint only the files I changed today"*

## Prerequisites

The chat plugin guides the agent in using `robotcode`; it does not bundle or replace the CLI. The [`robotcode` CLI tools](cli.md#installation) must be installed in the **project's** Python environment — not an isolated runner like `uvx` or `pipx`, which cannot see the project's libraries, resources, and local modules. If the CLI is missing, the agent is instructed to walk you through installing it (choosing scope and extras) before running anything.

## In VS Code (GitHub Copilot Chat)

The VS Code extension bundles the RobotCode chat plugin for GitHub Copilot Chat. It is **enabled by default** — no installation step, no marketplace. The agent picks it up automatically and starts using `robotcode` whenever a request is about Robot Framework.

You also don't need to install the `robotcode` CLI separately for this. The extension ships a bundled CLI — every subcommand included — and adds it to the integrated terminal's `PATH`; because Copilot Chat's agent runs its commands in that terminal, `robotcode` is available there out of the box. The bundle is only the *tool*, though: it runs against the terminal's active Python interpreter, so Robot Framework and your project's libraries still have to be installed in that environment for the CLI to inspect and run your project correctly.

Toggle it with the setting:

```json
"robotcode.ai.enableChatPlugins": true
```

Set it to `false` to turn the bundled plugin off — for example if you prefer to install the plugin from the marketplace instead (see the [duplication note](#avoiding-duplicates) below).

## Other agents — the marketplace

The same plugin is published as an [Open Plugins](https://open-plugins.com/) marketplace, [`robotcodedev/robotframework-agent-plugins`](https://github.com/robotcodedev/robotframework-agent-plugins), so agents outside VS Code can install it once and reuse it. Supported agents include Claude Code, GitHub Copilot (CLI and Chat), and Codex; check [open-plugins.com/supported-agents](https://open-plugins.com/supported-agents) for the current list.

Each agent uses its own commands to register a marketplace and install a plugin. For example:

```sh
# Claude Code
claude plugin marketplace add robotcodedev/robotframework-agent-plugins
claude plugin install robotcode@robotframework-agent-plugins

# GitHub Copilot CLI
copilot plugin marketplace add robotcodedev/robotframework-agent-plugins
copilot plugin install robotcode@robotframework-agent-plugins
```

See the [marketplace README](https://github.com/robotcodedev/robotframework-agent-plugins#install-per-agent) for the exact commands per agent, and for agents that load skill folders directly without a marketplace.

### Adding the marketplace from VS Code

To use the marketplace version in VS Code's Copilot Chat (instead of, or alongside, the bundled plugin), the extension provides two Command Palette commands that edit the user-level `chat.plugins.marketplaces` setting for you:

- **RobotCode: Add Chat Plugins Marketplace**
- **RobotCode: Remove Chat Plugins Marketplace**

Only the applicable one is shown at a time — *Add* until the marketplace is registered, *Remove* afterwards. (Removing also clears the entry if it was added by hand as a GitHub URL rather than the `owner/repo` shorthand.)

The `chat.plugins.marketplaces` setting is owned by GitHub Copilot Chat, not by RobotCode, so these commands require Copilot Chat (or another agent that provides that setting) to be installed — without it, updating it fails with an error.

### Avoiding duplicates

The bundled plugin and the marketplace plugin are the *same* plugin. If you install it from the marketplace, turn the bundled copy off so the agent doesn't load two identical plugins:

```json
"robotcode.ai.enableChatPlugins": false
```

The *Add Chat Plugins Marketplace* command offers to do this for you when the bundled plugin is still enabled.

## How it works

The plugin currently contains a single *skill* — a set of instructions the agent loads when a request looks Robot Framework–related — and is designed to gain more skills and agents over time. The skill calls no libraries or models of its own; it teaches the agent which `robotcode` command answers which question, and how to read the project the way Robot Framework does. The core habits it installs:

- **Inventory via [`discover`](discovering-tests.md), never by grepping files.** Which tests, tasks, suites, and tags exist is resolved at runtime — Robot's parsing rules, `robot.toml` paths, profiles, variables, and pre-run modifiers that add, remove, rename, or retag tests. A static file scan gets it wrong; `discover` runs the real resolution with the installed Robot Framework.
- **Keyword and library lookup via [`libdoc`](cli.md#libdoc), before generic knowledge.** `libdoc` reflects the *installed* library versions, the project's import arguments, the Python path, and local `.resource` files — things external documentation can't see.
- **Debugging a failing test via [`robot-debug`](robot-debug.md) — the agent's primary tool for any real test.** Whenever an existing test fails, won't run, or needs stepping through, the agent runs it under the command-line debugger: it pauses the real suite at a breakpoint (a `file:line`, a keyword, or the first uncaught failure), then reads the live call stack and per-frame variables and runs keywords in the paused context — capturing the actual state at the point of failure instead of re-running blindly or reasoning from the source. This is the default response to "why does this fail / step through it / what is `${x}` here?", and it is deliberately kept apart from the REPL below: the debugger acts on a test that *exists and runs*. Reaching for the REPL to fix a real test — instead of the debugger — is the single most common way the skill misfires.
- **Live exploration via the [REPL](repl.md) — only when there is *no* test yet.** A narrower tool: uncertain locators or keyword sequencing get tried interactively (optionally against the running app with a visible browser) rather than guessed. The moment a real test is in play, it is the debugger's job, not the REPL's.
- **Result inspection via [`results`](analyzing-results.md), not raw `output.xml`.** Finished runs are queried for bounded summaries, listings, traces, and diffs — including CI artifacts and a colleague's run — rather than loading a potentially huge XML file into the chat.
- **Static checks via [`analyze code`](analyzing-code.md)** before a run, and **runs via [`robot`](cli.md#robot)** honoring the active profile.

Throughout, the agent respects the project's [`robot.toml`](config.md) and profiles, so it operates on the same resolved configuration as the editor and the CLI.

## Give the agent project context

The skill teaches the agent *how* to drive `robotcode`, and `robotcode` resolves everything in your configuration at runtime — paths, profiles, tags, suites, installed library versions — so you never have to repeat that for the agent.

What it **can't** infer is the surrounding setup and intent. Capturing those once in your agent's instructions file — `AGENTS.md` (an emerging cross-agent convention), `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, or whatever your agent reads — saves it from rediscovering them on every task and keeps it from guessing wrong. Worth recording:

- **Environment & package manager** — which tool manages dependencies (`uv`, `hatch`, `poetry`, `pip`, …) and where the project's virtual environment lives, so the agent runs `robotcode` from the right interpreter (see [Prerequisites](#prerequisites)).
- **Installed libraries and their setup steps** — especially any one-off initialization needed after an install or update. For example, Browser Library needs `rfbrowser init` to download its Playwright browsers before its keywords work; an agent that doesn't know this runs into confusing failures.
- **The system under test** — what the application is, how to reach it (base URLs per environment, which profile points where), and any test data or accounts. Keep secrets out — describe *how* credentials are provided (env vars, a vault), not the values themselves.
- **Project conventions** — naming, tags, suite layout, and where new keywords belong, so generated tests match what you already have.

Keep it short and factual; this is standing context the agent reads on every request, not a place to duplicate `robot.toml`.

## AI-agent detection

Independently of the chat plugins, the `robotcode` CLI detects when it is running inside an AI-agent session and adjusts its presentation defaults so captured output stays clean:

- ANSI **colors** and the **pager** are disabled, so escape sequences and paging controls don't leak into the agent's captured stdout.
- The [`robotcode robot-debug`](robot-debug.md) prompt and the [`robotcode repl`](repl.md) shell fall back to the **plain input backend**, so completion popups and prompt redraws don't interfere with stdin/stdout — captured debug output (`.where`, `.vars`, `.print`) stays clean.

Detection is based on environment markers set by popular tools — Claude Code, Cursor, GitHub Copilot (CLI and VS Code agent flow), Codex, OpenCode, Gemini CLI, and others — plus the generic `AI_AGENT` and `AGENT` conventions. A marker counts as active when it is present with any value other than empty or `0`.

You rarely need to touch this, but every default can be overridden:

| Override | Effect |
| --- | --- |
| `ROBOTCODE_FORCE_AI_AGENT=1` | Force detection **on** (e.g. an agent whose marker isn't recognized yet). Wins over everything. |
| `ROBOTCODE_NO_AI_AGENT=1` | Force detection **off**. Wins over tool markers, loses to `ROBOTCODE_FORCE_AI_AGENT`. |
| `--color` / `--no-color`, `NO_COLOR`, `FORCE_COLOR` | Decide coloring explicitly, regardless of detection. |
| `--pager` / `--no-pager` | Decide paging explicitly. |
| `--plain` / `--backend`, `ROBOTCODE_REPL_PLAIN`, `ROBOTCODE_REPL_BACKEND` | Decide the prompt backend explicitly — applies to both `robot-debug` and the REPL. |

Explicit flags and environment variables always win over auto-detection, so you can opt back into colored, paged, or full-featured output inside an agent session when you want it.

## Troubleshooting

**The agent answers from generic knowledge instead of using `robotcode`.** A skill is loaded by *relevance* — the agent matches your request against the skill's description and only pulls it in when the request reads as Robot Framework work. A terse prompt in a mixed-language repo ("run it", "fix this test") may not trigger it. Name the domain — mention Robot Framework, a suite, a profile, a keyword, or `robotcode` itself — or invoke the skill explicitly by name (it's called **`robotcode`**). In VS Code, also confirm `robotcode.ai.enableChatPlugins` is `true` — see [In VS Code](#in-vs-code-github-copilot-chat).

**The agent's answers don't match your project** — libraries or keywords it should see are reported as missing, or argument lists look wrong. It is most likely driving a `robotcode` from the wrong environment rather than the project's (see [Prerequisites](#prerequisites)). Have the agent run `robotcode discover info` to show which interpreter and versions it is using, and compare that against the project's environment.

**The agent re-runs a failing test over and over (or pastes it into the REPL) instead of debugging it.** This is the skill's single most common misfire. When a *real* test fails, the right tool is the [debugger](robot-debug.md), not blind re-runs or the REPL — it pauses the actual run at the failure and exposes the live stack and variables. Tell it to debug the test ("step through it with `robot-debug`", "break where it fails and show me the variables"). The REPL is for exploring when there's no test yet; the debugger is for a test that already runs.

**The agent writes a `.robot` file when you only wanted it to *do* something** — try a keyword or check a locator with no test yet. Tell it not to write a test and to use the REPL instead ("don't write a test, just run it live"); it can save the session as a test afterwards if you ask. See [Interactive Robot Framework REPL](repl.md). (If a test already exists, you want the debugger above, not the REPL.)

**A marketplace install behaves differently from the bundled VS Code plugin.** The two copies are versioned independently: the bundled one ships with the extension, the marketplace one updates through your agent's `plugin marketplace update`. If behavior diverges, update the marketplace copy — and make sure you aren't running both at once (see [Avoiding duplicates](#avoiding-duplicates)).

## See also

- [Command Line Interface](cli.md) — every `robotcode` command the agent drives.
- [Discovering Tests, Tasks and Suites](discovering-tests.md) — how project inventory is resolved.
- [Analyzing Run Results](analyzing-results.md) — inspecting finished runs.
- [Command-line debugging with `robotcode robot-debug`](robot-debug.md) — pausing a real run at a breakpoint to inspect the live stack and variables.
- [Interactive Robot Framework REPL](repl.md) — the live keyword shell.
- [`robotframework-agent-plugins`](https://github.com/robotcodedev/robotframework-agent-plugins) — the marketplace and plugin source.
