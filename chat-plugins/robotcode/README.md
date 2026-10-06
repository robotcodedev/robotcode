# robotcode

> Agent skill that teaches AI coding agents to drive [`robotcode`](https://robotcode.io) properly in Robot Framework projects.

With this plugin, your AI coding agent uses [`robotcode`](https://robotcode.io) like an experienced Robot Framework engineer — picking the right command for the task and honoring your project's profiles. Instead of guessing, it tries things interactively, looks keywords up against your installed libraries, runs your suites, inspects finished runs, and analyzes the project for issues. Things you can ask:

- "run the smoke suite with the `dev` profile"
- "rerun just the tests that failed last time"
- "try the new login flow against the real app, with a visible browser"
- "does `css=.cart-icon` actually match anything on the live cart page?"
- "draft a test for password reset, reusing what we already have"
- "extract this block into a reusable keyword"
- "why did `Login Works` fail in last night's run?"
- "summarize the failures from yesterday's nightly run"
- "what arguments does our `Create Order` keyword take?"
- "is there already a keyword for waiting until the spinner is gone?"
- "what keywords does `common.resource` expose?"
- "list the tags we have and how many tests use each"
- "set up a `prod` profile with `BASE_URL=https://prod.example.com`"
- "show me the effective config when I use `-p ci -p docker`"
- "lint only the files I changed today"
- "are there any unused keywords or unresolved variables?"

## Prerequisites

- A Robot Framework project.
- The [`robotcode`](https://robotcode.io) CLI tools, installed in the project's Python environment (the command-line tool — not to be confused with the VS Code extension of the same name). You can set it up yourself following the [installation guide](https://robotcode.io/reference/cli/), or let the skill walk you through scope (dev dependency vs. venv-only) and extras (`runner`, `analyze`, `repl`, …) on first use.
- An AI agent that supports plugins — see [supported agents](https://open-plugins.com/supported-agents) for the current list. Agents without plugin support can still load the skill directly (see [Install](#install)).

## Install

Add the parent marketplace once, then install this plugin from it:

```sh
# Claude Code
claude plugin marketplace add robotcodedev/robotframework-agent-plugins
claude plugin install robotcode@robotframework-agent-plugins

# GitHub Copilot CLI
copilot plugin marketplace add robotcodedev/robotframework-agent-plugins
copilot plugin install robotcode@robotframework-agent-plugins
```

For Codex, VS Code Copilot Chat, and other Open-Plugins-compliant agents, see the [marketplace README](../../README.md).

> Using the [RobotCode VS Code extension](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode)? It already bundles this plugin via `contributes.chatPlugins` — no separate install needed for VS Code Copilot Chat.

**Without the marketplace.** The skill content is plain Markdown, so any agent that loads skill folders from a known directory can use it directly. For Claude Code:

```sh
git clone --depth 1 https://github.com/robotcodedev/robotframework-agent-plugins
cp -r robotframework-agent-plugins/plugins/robotcode/skills/robotcode ~/.claude/skills/
```

Other agents have analogous skill directories — consult their docs. The trade-off is that updates won't flow through `plugin marketplace update`; you re-pull manually. To get the skill for a specific `robotcode` release, add `--branch robotcode--v<version>` to the clone.

## Match your robotcode version

The skill describes the commands and options of a specific `robotcode` release, and every `robotcode` release has a matching tag `robotcode--v<version>`. Installing without a ref gives you the plugin for the latest release.

If your project uses an older `robotcode` (check with `robotcode --version`), pin the marketplace to the matching tag. For example, for `robotcode` 2.7.0 in Claude Code:

```sh
claude plugin marketplace add robotcodedev/robotframework-agent-plugins#robotcode--v2.7.0
claude plugin install robotcode@robotframework-agent-plugins
```

See [Versions and pinning](../../README.md#versions-and-pinning) for the command in other agents and for switching between versions.

## Updating

```sh
claude plugin marketplace update   # or your agent's equivalent
```

A marketplace pinned to a tag doesn't update. To move to another `robotcode` version, switch the tag as described in [Match your robotcode version](#match-your-robotcode-version).

The marketplace [`robotcodedev/robotframework-agent-plugins`](https://github.com/robotcodedev/robotframework-agent-plugins) is the source of truth. Pull requests welcome — see the marketplace [CONTRIBUTING notes](../../README.md#contributing).

## Links

- RobotCode documentation — <https://robotcode.io>
- RobotCode CLI source — <https://github.com/robotcodedev/robotcode>
- Marketplace — <https://github.com/robotcodedev/robotframework-agent-plugins>

## License

Apache-2.0 — see [LICENSE](LICENSE).
