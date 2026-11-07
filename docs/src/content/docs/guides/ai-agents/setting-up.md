---
title: Setting Up Your Agent
description: Set up the RobotCode plugin and robotcode for GitHub Copilot Chat in VS Code, for Claude Code, GitHub Copilot CLI and Codex, and in PyCharm, and check that the agent works through robotcode.
sidebar:
  label: Setting Up
  order: 150.1
---

An agent needs two things to work with RobotCode: the RobotCode plugin, which teaches it to use `robotcode`, and `robotcode` itself, running in the project's Python environment. In VS Code, the extension brings both. This page sets them up in VS Code, for agents on the command line and in PyCharm, and shows how to check that the agent works through `robotcode`.

## Prerequisites

The plugin tells the agent how to use `robotcode`, but it doesn't contain it. `robotcode` has to run in the project's Python environment, because Robot Framework and your libraries are installed there. A tool runner such as `uvx` or `pipx` runs it in an environment of its own, which doesn't have them. In VS Code, the extension brings its own `robotcode` for this (see below). Everywhere else, [install RobotCode's command line tools](/getting-started/command-line/) into the project's environment. If they are missing, the agent asks you before it installs anything; see [When robotcode is missing](/guides/ai-agents/how-the-skill-works/#when-robotcode-is-missing).

## In VS Code (GitHub Copilot Chat)

The VS Code extension brings the RobotCode plugin for GitHub Copilot Chat. It is on by default, and you install nothing. Copilot Chat loads the plugin's skill when a request reads as Robot Framework work; see [When the agent loads the skill](/guides/ai-agents/how-the-skill-works/#when-the-agent-loads-the-skill).

You don't install `robotcode` here either. The extension brings its own copy, with every command, and adds it to the `PATH` of the integrated terminal, where Copilot Chat's agent runs its commands. That copy runs with the terminal's active Python interpreter, so Robot Framework and your project's libraries must be installed there.

The setting `robotcode.ai.enableChatPlugins` turns the plugin on and off:

```json
"robotcode.ai.enableChatPlugins": true
```

Set it to `false` if you install the plugin from the marketplace instead; see [Avoiding duplicates](#avoiding-duplicates). VS Code's own setting `chat.plugins.enabled` turns off all plugins, this one included.

## Other agents

Agents outside VS Code install the same plugin from the marketplace [`robotcodedev/robotframework-agent-plugins`](https://github.com/robotcodedev/robotframework-agent-plugins). Each agent has its own commands to add the marketplace and to install the plugin from it:

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

The [marketplace README](https://github.com/robotcodedev/robotframework-agent-plugins#install-per-agent) has the commands for other agents. For agents that load skill folders without a marketplace, the [plugin's README](https://github.com/robotcodedev/robotframework-agent-plugins/blob/main/plugins/robotcode/README.md#install) says how to copy the skill.

### Updating the plugin

The plugin from the marketplace is the one for the latest RobotCode release at the time you install or update it. To update it:

```sh
# Claude Code: refresh the marketplace, then update the plugin
claude plugin marketplace update robotframework-agent-plugins
claude plugin update robotcode@robotframework-agent-plugins

# GitHub Copilot CLI
copilot plugin update robotcode@robotframework-agent-plugins

# Codex: refreshing the marketplace also updates the plugin
codex plugin marketplace upgrade robotframework-agent-plugins
```

In VS Code, **Chat: Update Plugins** in the Command Palette updates the plugins from a marketplace.

## In PyCharm

Claude Code, GitHub Copilot CLI and Codex work in PyCharm's terminal as well. RobotCode's PyCharm plugin doesn't include the plugin for agents yet (see [PyCharm and VS Code](/guides/pycharm/compared-with-vscode/)), so install it from the [marketplace](#other-agents). GitHub Copilot's plugin for PyCharm can't use it, because GitHub offers plugins only in VS Code, GitHub Copilot CLI, the GitHub Copilot app and Copilot in the cloud.

Start the agent with the project's Python environment active and install RobotCode's command line tools there, as [Get Started on the Command Line](/getting-started/command-line/) shows, so that the agent's commands find `robotcode`.

## Checking that it works

Ask the agent something about the project, for example *"Which tests are tagged smoke?"*. It should run a `robotcode discover` command, such as `robotcode discover tests -i smoke`, and not search the `.robot` files. If it searches the files, see [The agent answers without robotcode](/guides/ai-agents/troubleshooting/#the-agent-answers-without-robotcode).

To see which environment the agent's `robotcode` uses, ask it to run `robotcode discover info`. It shows the versions of Robot Framework, RobotCode and Python and the Python executable.

## Special cases

### Matching your RobotCode version

A project that stays on an older RobotCode can pin the plugin to that version. Every release from 2.6.0 on, the first with the plugin, is tagged `robotcode--v<version>`. Check the version with `robotcode --version`, then add the marketplace with that tag:

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

To use the plugin from the marketplace in GitHub Copilot Chat instead of the one in the extension, the extension has two commands in the Command Palette. They edit the user setting `chat.plugins.marketplaces` for you:

- **RobotCode: Add Chat Plugins Marketplace**
- **RobotCode: Remove Chat Plugins Marketplace**

Only one of them shows at a time: *Add* until the marketplace is registered, *Remove* afterwards. *Remove* also clears an entry that was added by hand as a GitHub URL instead of `owner/repo`, or that is pinned to a tag.

### Avoiding duplicates

The plugin in the extension and the plugin from the marketplace are the same plugin. If you install it from the marketplace, turn the one in the extension off, so that the agent doesn't load it twice:

```json
"robotcode.ai.enableChatPlugins": false
```

*Add Chat Plugins Marketplace* offers to do this when the plugin in the extension is still on.
