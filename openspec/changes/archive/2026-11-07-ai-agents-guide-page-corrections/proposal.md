# Proposal

## Why

The review of the AI agents guide (`playground/ai-agents-guide-befunde.md`, 2026-11-04) found wrong statements, contradictions and repetition on the five pages outside the tutorial: Overview, Setting Up, Briefing the Agent, How the Skill Works and Troubleshooting. The tutorial has since been rewritten; these five pages still read like the old one-page guide. Two requirements of the guide's spec describe what the pages said, not what is true.

## What Changes

- **How the Skill Works:** the list "How it works" goes, with its wrong statements (the debugger as the main tool, an unmeasured "most common misfire", `discover` resolving variables). The reason for the debugger over the REPL stays, in two sentences under the table. The table sends "why does it fail" to the debugger only when the results don't explain the failure. "When robotcode is missing" says when `No such command` means a missing extra, an old `robotcode` or a wrong subcommand. "AI-agent detection" stays under its anchor, says that it covers only `robotcode`'s own output, lists every variable it checks, and links the CLI guides for the overrides of colour, pager and prompt.
- **Setting Up:** the requirement that `robotcode` runs in the project's environment no longer contradicts the VS Code section. "Open Plugins" and the dead link to its list of agents go. A section on updating the plugin from the marketplace has the commands per agent. The false claim that `chat.plugins.marketplaces` needs Copilot Chat goes. PyCharm names Claude Code, GitHub Copilot CLI and Codex and says that Copilot's plugin for PyCharm can't use the plugin. The special cases (pinning, the marketplace in VS Code, duplicates) come after "Checking that it works", under their old anchors.
- **Troubleshooting:** one heading per symptom. Updating names the real commands. A failing test is answered with the results first, then the debugger.
- **Briefing the Agent:** GitHub Copilot CLI gets its entry, `chat.useAgentsMdFile` is limited to local sessions, and repetition goes.
- **Overview:** the skill is explained where the word first appears, and "turn the plugin on" goes.
- The four pages are written in the tutorial's voice: one fact per sentence, no dashes, one name per thing.
- **VS Code extension:** the error message of *Add/Remove Chat Plugins Marketplace* no longer claims that the setting needs GitHub Copilot Chat; it shows the error.

## Capabilities

### New Capabilities

### Modified Capabilities
- `ai-agents-guide`: "Setting up an agent" says where `robotcode` runs in VS Code and elsewhere, covers updating the plugin, and names the agents in PyCharm. "Briefing the agent" names Copilot CLI's files and no longer speaks of recorded sessions.

## Impact

- `docs/src/content/docs/guides/ai-agents/{index.mdx,setting-up.md,briefing.md,how-the-skill-works.md,troubleshooting.md}`.
- `vscode-client/extension/chatPluginsManager.ts`: one error message.
- Anchors that other pages link stay as they are. Renamed are only `#other-agents--the-marketplace` and `#an-example`, which no other page links.
