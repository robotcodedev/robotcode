---
title: Setting Up Your Agent
description: Install the RobotCode plugin for GitHub Copilot Chat in VS Code and for Claude Code, GitHub Copilot CLI, Codex and other agents, in PyCharm too, match it to your RobotCode version, and check that the agent works through robotcode.
sidebar:
  label: Setting Up
  order: 150.1
---

An agent needs two things to work with RobotCode: the RobotCode plugin, which teaches it to use `robotcode`, and RobotCode's command line tools in the project's Python environment. This page sets up both, in VS Code, for agents on the command line and in PyCharm, and shows how to check that the agent works through `robotcode`.

## Prerequisites

The chat plugin guides the agent in using `robotcode`; it does not bundle or replace the CLI. The [`robotcode` CLI tools](/reference/cli/#installation) must be installed in the **project's** Python environment — not an isolated runner like `uvx` or `pipx`, which cannot see the project's libraries, resources, and local modules. If the CLI is missing, the agent is instructed to walk you through installing it (choosing scope and extras) before running anything.

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

# Codex
codex plugin marketplace add robotcodedev/robotframework-agent-plugins
codex plugin add robotcode@robotframework-agent-plugins
```

See the [marketplace README](https://github.com/robotcodedev/robotframework-agent-plugins#install-per-agent) for the exact commands per agent, and for agents that load skill folders directly without a marketplace.

### Matching your RobotCode version

Installed this way, the plugin matches the latest **RobotCode** release. Every release is also tagged `robotcode--v<version>`, so a project that stays on an older version can pin the plugin to the matching tag. Check the version with `robotcode --version`, then add the marketplace with that tag:

```sh
# Claude Code
claude plugin marketplace add robotcodedev/robotframework-agent-plugins#robotcode--v2.7.0

# GitHub Copilot CLI
copilot plugin marketplace add robotcodedev/robotframework-agent-plugins#robotcode--v2.7.0

# Codex
codex plugin marketplace add robotcodedev/robotframework-agent-plugins --ref robotcode--v2.7.0
```

In VS Code, append the tag to the entry in `chat.plugins.marketplaces`, for example `"robotcodedev/robotframework-agent-plugins#robotcode--v2.7.0"`. Then install the plugin as usual.

A pinned marketplace receives no updates. To move to another version, remove the marketplace, add it again with the new tag, and reinstall the plugin.

### Adding the marketplace from VS Code

To use the marketplace version in VS Code's Copilot Chat (instead of, or alongside, the bundled plugin), the extension provides two Command Palette commands that edit the user-level `chat.plugins.marketplaces` setting for you:

- **RobotCode: Add Chat Plugins Marketplace**
- **RobotCode: Remove Chat Plugins Marketplace**

Only the applicable one is shown at a time — *Add* until the marketplace is registered, *Remove* afterwards. (Removing also clears the entry if it was added by hand as a GitHub URL rather than the `owner/repo` shorthand, or pinned to a tag.)

The `chat.plugins.marketplaces` setting is owned by GitHub Copilot Chat, not by RobotCode, so these commands require Copilot Chat (or another agent that provides that setting) to be installed — without it, updating it fails with an error.

### Avoiding duplicates

The bundled plugin and the marketplace plugin are the *same* plugin. If you install it from the marketplace, turn the bundled copy off so the agent doesn't load two identical plugins:

```json
"robotcode.ai.enableChatPlugins": false
```

The *Add Chat Plugins Marketplace* command offers to do this for you when the bundled plugin is still enabled.

## In PyCharm

The usual agents work in PyCharm as well. RobotCode's PyCharm plugin does not bring the plugin for them yet (see [PyCharm and VS Code](/guides/pycharm/compared-with-vscode/)), so install it from the [marketplace](#other-agents--the-marketplace) as described above. Start the agent with the project's Python environment active and install RobotCode's command line tools there, as [Get Started on the Command Line](/getting-started/command-line/) shows, so that the agent's commands find `robotcode`.

## Checking that it works

Ask the agent a question that only the project's configuration can answer, for example *"Which tests are tagged smoke?"*. It should answer with a `robotcode discover` command, such as `robotcode discover tests -i smoke`, and not by searching the `.robot` files. If it searches the files, see [Troubleshooting](/guides/ai-agents/troubleshooting/).

To see which environment the agent's `robotcode` uses, ask it to run `robotcode discover info`. It shows the versions of Robot Framework, RobotCode and Python and the Python executable.
