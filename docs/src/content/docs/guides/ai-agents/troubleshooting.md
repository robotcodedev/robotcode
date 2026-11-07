---
title: Troubleshooting AI Agents
description: What to do when an agent doesn't use the RobotCode skill as you expect, by what you see it do.
sidebar:
  label: Troubleshooting
  order: 150.5
---

## The agent answers without robotcode

It answers from general knowledge or searches the files, because it hasn't loaded the skill. Name the skill in your request, as in *Use the robotcode skill.* [When the agent loads the skill](/guides/ai-agents/how-the-skill-works/#when-the-agent-loads-the-skill) says why a short request may not be enough. In VS Code, also check that `robotcode.ai.enableChatPlugins` and VS Code's `chat.plugins.enabled` are `true`; see [In VS Code](/guides/ai-agents/setting-up/#in-vs-code-github-copilot-chat).

## The agent picks the wrong skill

It loads `robotcode` although another skill fits better, or it skips `robotcode` although it fits. Agents choose a skill from a list of the installed skills and their descriptions, and that list has a limited size. Some agents tie the limit to the context window, so it is tighter with a small window; others use a fixed size. In Claude Code, for example, it is 1 % of the context window, which is 8000 characters at 200K tokens, and Claude Code's own skills already use most of that. `claude --debug` warns when the list overflows.

With several skills installed, the list can overflow. Descriptions are then shortened or dropped, often down to the name, and the agent can no longer tell what a skill is for. Which skill loses its description first depends on the agent: the one used least, the one with the longest description, or the last one in the list.

Name the skill you want in your request, and remove or turn off skills you don't need. Some agents also let you raise the limit, such as Claude Code with [`skillListingBudgetFraction`](https://code.claude.com/docs/en/settings-reference#skilllistingbudgetfraction) and Codex with `skills.max_context_tokens`.

## The answers don't match your project

Libraries or keywords it should see are reported as missing, or argument lists look wrong. The agent may run a `robotcode` from another environment than the project's; see [Prerequisites](/guides/ai-agents/setting-up/#prerequisites). Have it run `robotcode discover info`, which shows the interpreter and the versions it uses, and compare that with the project's environment. The same happens when `robot.toml` lacks a `python-path` that the project needs, or when the profile that sets it isn't selected.

## The agent re-runs a failing test

It runs a failing test again and again, or tries it in the REPL, instead of finding out why it fails. Ask it why the test failed. The skill has it read the results of the last run with [`robotcode results`](/guides/cli/analyzing-results/) first, which often name the cause. If they don't, ask it to debug the test, as in "step through it with `robot-debug`" or "stop where it fails and show me the variables". The [debugger](/guides/cli/robot-debug/) stops the real run at the failure and shows the call stack and the variables. The REPL is for trying things while there is no test yet.

## The agent writes a test when you wanted to try something

You only wanted it to try a keyword or check a locator, and there is no test yet. Tell it not to write a test and to use the REPL instead, as in "don't write a test, just try it live". If you ask, it can save what worked as a test afterwards; see [Interactive Robot Framework REPL](/guides/cli/repl/). If a test already exists, you want the debugger instead; see [The agent re-runs a failing test](#the-agent-re-runs-a-failing-test).

## The plugin from the marketplace behaves differently

The plugin in the VS Code extension always fits the extension's version. The plugin from the marketplace is the one for the latest RobotCode release when you install or update it, or for the tag you pinned it to. If the two behave differently, [update the plugin from the marketplace](/guides/ai-agents/setting-up/#updating-the-plugin) or [pin it to your version](/guides/ai-agents/setting-up/#matching-your-robotcode-version). Also check that you don't use both at once; see [Avoiding duplicates](/guides/ai-agents/setting-up/#avoiding-duplicates).
