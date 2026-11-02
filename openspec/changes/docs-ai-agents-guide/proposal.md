# Proposal

## Why

The guide `/guides/ai-agents/` is one page of about 2300 words. Most of it covers setup and reference: the plugin in VS Code, the marketplace, version pinning, the detection of agent sessions and troubleshooting. What an agent does with the RobotCode skill appears only as eleven one-line example prompts without results and a list of habits. The home page shows more: seven sessions with real commands and output, and nine abilities. Topics such as the coverage of requirements, comparing runs, unused code, configuration, RPA tasks and large projects are missing from the guide or get half a sentence. The guide should teach how to work with an agent, step by step, and use the sessions as evidence rather than show what the agent can do.

## What Changes

- **AI Agents becomes a group**, like VS Code, PyCharm and Command Line, after Project Configuration in the sidebar. Its overview keeps `/guides/ai-agents/`, so the home page's "Set up your agent" and the links to the guide stay as they are.
- **Six pages:** Overview, Setting Up, Briefing the Agent, How the Skill Works, Working with the Agent and Troubleshooting. The content of the current page moves to them:
  - setup, marketplace and versions to Setting Up;
  - the project context to Briefing the Agent;
  - the habits and the detection of agent sessions to How the Skill Works;
  - the troubleshooting to its own page.
- **Setting Up** also covers PyCharm (the usual agents, with the plugin from the marketplace) and a check that the agent uses `robotcode`.
- **Briefing the Agent** comes right after Setting Up. It shows the complete instruction file of the example project that the sessions were recorded with.
- **How the Skill Works** comes right before Working with the Agent.
- **Working with the Agent is a tutorial** in a group of its own: an overview and seven steps in a learning order:
  1. getting to know the project;
  2. writing a test from a requirement;
  3. running what you need;
  4. finding out why a test failed;
  5. debugging step by step;
  6. checking before a push;
  7. a profile for the CI server.

  Each step says what you learn, how to ask the agent, what the agent does and why, with short excerpts from a recorded session, and what to watch out for. The reader works with their own project, and the text holds for any agent. The recorded sessions follow each step, collapsed, each in a frame that sets it apart from the guide's text: the prompt, the commands with their output, the files the agent read or changed, and its answer.
- **The overview** shows the steps of the tutorial in place of the list of abilities.
- **Two interactive sessions** that the user steers turn by turn: debugging a paused run step by step, and running keywords one after another in the REPL.
- **The recordings test the skill.** Findings (the agent going against the skill, or guidance that is missing or wrong) are collected. A session with a finding goes on its page as recorded and is replaced once it has been recorded again with the improved skill or CLI. The improvements themselves are changes of their own.
- **The sessions are real Claude Code transcripts**, shortened only by leaving parts out. Claude Code runs in an empty configuration with only the RobotCode plugin, in a copy of the example project behind the home page's demos. The first recordings take the plugin from the marketplace, the final ones from a local folder, because the improved skill comes out with the next release. The session on large projects runs in a generated project with thousands of tests. The overview of the tutorial names the versions of Claude Code and RobotCode and the model.
- **Links follow:**
  - four links that point to sections of the current page get the new pages, two of them in news posts, where only the link target changes and not the text;
  - the PyCharm comparison links the PyCharm section of Setting Up;
  - `CONTRIBUTING.md` lists the folder `ai-agents/` among the groups of guides.

Not part of this change:
- the home page's AI agents section and its demo, which stay as they are;
- publishing the example project of the sessions: the reader works with their own project;
- improving the RobotCode skill or the CLI. The recordings collect the findings, and the improvements follow as changes of their own, for example for driving the debugger and the REPL turn by turn.

## Capabilities

### New Capabilities

- `ai-agents-guide`: the pages of the AI agents guide, the setup and briefing of an agent, the sessions of a real agent and how they are recorded and shown, and how the skill works.

### Modified Capabilities

- `documentation-site`: in "Guides grouped by tool and topic", AI Agents becomes a group, so every guide except the Guides overview is a page of a group.

## Impact

- `docs/src/content/docs/guides/ai-agents.md` moves to `guides/ai-agents/index.mdx`; four new pages in `guides/ai-agents/` and the group `guides/ai-agents/working-with-the-agent/` with an overview and seven steps; `docs/src/routeData.ts` gets the labels of the groups; `docs/src/styles/custom.css` gets the frames of the sessions.
- Links in `news/v2-6-0.md`, `news/v2-8-0.mdx` (only the link targets), `guides/cli/repl.md`, `guides/vscode/index.mdx` and `guides/pycharm/compared-with-vscode.mdx`; `CONTRIBUTING.md` ("Groups of guides").
- Recording tools in the git-ignored `playground/robotcode-demo/`: a script that prepares the session project and runs Claude Code, a converter from Claude Code's output to Markdown, a generator for the large project, and a script that fills the sessions into the steps and checks the excerpts.
- The recordings run on the maintainer's Claude account. The maintainer logs in once in the empty configuration.
- No code of RobotCode changes.
