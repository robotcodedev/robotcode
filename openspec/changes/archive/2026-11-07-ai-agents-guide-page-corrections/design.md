# Design

## Context

The findings are in `playground/ai-agents-guide-befunde.md`, with evidence in `playground/ai-agents-guide-befunde/fakten.md` and proposed wording in `playground/ai-agents-guide-befunde/text.md`. The five pages had not changed since the review, apart from the links to the tutorial's steps, so the line numbers there still apply. The maintainer decided the open points J3, J4, J8 and J9 on 2026-11-07.

## Goals / Non-Goals

**Goals:**
- Every finding on the five pages is corrected: wrong, contradictory, imprecise, repeated, and the voice of the old guide.
- Anchors that other pages, the news or the spec link keep working.

**Non-Goals:**
- The tutorial's pages and their answers.
- The layout of the plugin in `robotframework-agent-plugins` (F3: a `plugin.json` in the plugin's folder as the Agent Plugins standard now asks). It is a task of its own, with an install test per agent.
- The text of the news posts.

## Decisions

- **The list "How it works" is deleted (J3).** It retold the openings of the CLI guides, the table below says the same with the same links, and three of its statements were wrong. The spec asks for the reason why the agent debugs an existing test with the debugger and not in the REPL; it stays as two sentences under the table. Alternative: keep and correct the list; rejected, the repetition would stay.
- **"AI-agent detection" stays where it is (J4).** Its anchor is linked from `guides/cli/repl.md`, `news/v2-6-0.md` and the spec. It is corrected (only `robotcode`'s own output; Robot Framework's console keeps its colours on a terminal) and shortened to what only this page documents: the variables that count and the two that decide the detection. The overrides of colour, pager, backend and prompt are linked to the CLI guides. The variables are listed in full, because `repl.md` links the section for "the full marker list". Alternative: move it to `guides/cli/index.mdx`; rejected, it changes the anchor, a link in the news and the spec for little gain.
- **PyCharm names the agents (J9).** "The usual agents" held for agents on the command line but not for GitHub Copilot's plugin for JetBrains IDEs, which GitHub's documentation doesn't list among the surfaces with plugins. The page names Claude Code, GitHub Copilot CLI and Codex and says that Copilot's plugin can't use it.
- **The extension's error message is corrected too (J8),** in a commit of its own. VS Code registers `chat.plugins.marketplaces` itself, so "requires GitHub Copilot Chat" was a wrong reason; the message now shows the error.
- **Setting Up gets a section "Special cases".** Pinning, the marketplace in VS Code and the duplicates move after "Checking that it works", as H3 under that section. Their slugs stay the same. "Updating the plugin" is a new H3 under "Other agents", so that Troubleshooting can link it.
- **Troubleshooting gets one H2 per symptom.** The other troubleshooting pages of the site have headings, and Setting Up can now link a symptom.
- **Update commands come from the tests of 2026-11-05** with a local marketplace (Claude Code 2.1.318, Copilot CLI 1.0.105, codex-cli 0.166.0). VS Code's *Chat: Update Plugins* and the list of Copilot surfaces come from their documentation.

## Risks / Trade-offs

- [The list of Copilot surfaces with plugins changes] → The sentence names GitHub as its source in plain words; a later review catches it.
- [The extension's message is not tried in VS Code] → It only changes the text; `eslint`, `tsc` and the build pass.
- [The variables of the detection change in the code] → The section names them in one table, next to `_agent_detection.py`'s own list.
