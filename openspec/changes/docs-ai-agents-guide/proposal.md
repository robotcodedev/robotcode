# Proposal

## Why

The guide `/guides/ai-agents/` is one page of about 2300 words. Most of it covers setup and reference: the plugin in VS Code, the marketplace, version pinning, the detection of agent sessions and troubleshooting. What an agent does with the RobotCode skill appears only as eleven one-line example prompts without results and a list of habits. The home page shows more: seven sessions with real commands and output, and nine abilities. Topics such as the coverage of requirements, comparing runs, unused code, configuration, RPA tasks and large projects are missing from the guide or get half a sentence.

## What Changes

- **AI Agents becomes a group**, like VS Code, PyCharm and Command Line, at the same place in the sidebar. Its overview keeps `/guides/ai-agents/`, so the home page's "Set up your agent" and the links to the guide stay as they are.
- **Six pages:** Overview, Setting Up, Briefing the Agent, Working with the Agent, How the Skill Works and Troubleshooting. The content of the current page moves to them:
  - setup, marketplace and versions to Setting Up;
  - the project context to Briefing the Agent;
  - the habits and the detection of agent sessions to How the Skill Works;
  - the troubleshooting to its own page.
- **Setting Up** also covers PyCharm (an agent in PyCharm's terminal) and a check that the agent uses `robotcode`.
- **Briefing the Agent** comes right after Setting Up. It shows the complete instruction file of the example project that the sessions were recorded with.
- **Working with the Agent** has a section for each task:
  - writing tests and tasks;
  - running tests;
  - failing tests and comparing runs;
  - knowing the project, also a large one;
  - code quality;
  - configuration.

  Each section shows sessions of a real agent as Markdown: the prompt, the commands with their output, the files the agent read or changed, and its answer.
- **The sessions are real Claude Code transcripts**, shortened only by leaving parts out. Claude Code runs in an empty configuration with only the RobotCode plugin from the marketplace, in a copy of the example project behind the home page's demos. The session on large projects runs in a generated project with thousands of tests. The page names the versions of Claude Code and RobotCode and the model.
- **Links follow:**
  - four links that point to sections of the current page get the new pages;
  - the PyCharm comparison links the PyCharm section of Setting Up;
  - `CONTRIBUTING.md` lists the folder `ai-agents/` among the groups of guides.

Not part of this change:
- the home page's AI agents section and its demo, which stay as they are;
- the RobotCode skill itself. Where the recordings show the agent going against the skill, that is reported as a finding for the skill.

## Capabilities

### New Capabilities

- `ai-agents-guide`: the pages of the AI agents guide, the setup and briefing of an agent, the sessions of a real agent and how they are recorded and shown, and how the skill works.

### Modified Capabilities

- `documentation-site`: in "Guides grouped by tool and topic", AI Agents becomes a group, so every guide except the Guides overview is a page of a group.

## Impact

- `docs/src/content/docs/guides/ai-agents.md` moves to `guides/ai-agents/index.mdx`; five new pages in `guides/ai-agents/`; `docs/src/routeData.ts` gets the label of the group.
- Links in `news/v2-6-0.md`, `news/v2-8-0.mdx`, `guides/cli/repl.md`, `guides/vscode/index.mdx` and `guides/pycharm/compared-with-vscode.mdx`; `CONTRIBUTING.md` ("Groups of guides").
- Recording tools in the git-ignored `playground/robotcode-demo/`: a script that prepares the session project and runs Claude Code, a converter from Claude Code's output to Markdown, and a generator for the large project.
- The recordings run on the maintainer's Claude account. The maintainer logs in once in the empty configuration.
- No code of RobotCode changes.
