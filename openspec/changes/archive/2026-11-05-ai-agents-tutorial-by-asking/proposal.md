# Proposal

## Why

The tutorial of the AI agents guide, Working with the Agent, mostly retells what an agent once did: it explains commands, quotes recordings and lists what to watch out for. The reader doesn't learn how to ask or instruct an agent, and doesn't see what to look for in an answer or what to do next. The maintainer's verdict on 2026-11-04 was that it isn't really usable.

A probe of step 4 (`playground/tutorial-probe/finding-out-why-a-test-failed.md`) tried another way: the reader asks, looks at the answer, decides and instructs. The maintainer accepted its direction on 2026-11-05, with links to the documentation of the commands the agent names, and without the collapsed recordings.

## What Changes

- **The seven steps are written anew, in the way of the probe.** Each one starts from what the reader wants to find out or get done and reaches everything through prompts to the agent. Between the prompts, the text says what to look for and what to do next. Each step ends with what to take to the reader's own project. The order, the titles and the URLs of the steps stay.
- **Commands come from the agent.** A step never starts with a `robotcode` command, and it doesn't explain each command. When an answer names a command, the text right after it links to its documentation. Between a prompt and its answer, a step shows the `robotcode` commands the agent ran for it, each linked to its documentation, so that the answer doesn't look like magic.
- **The recordings go.** The collapsed sessions, their excerpts and the section about them on the overview are removed. A step shows short answers of real runs instead, as the agent wrote them and rendered as Markdown, in the frames the sessions use today.
- **Prompts are tried before they are written down.** Every prompt runs in the example project first, and the text says only what these runs support. It describes what applies and reports no test statistics.
- **The example project gets a flaky test.** Step 4 teaches how to find out whether a failure happens every time, so `Express Order` in `robotcodedev/webshop-ai-example` now fails only sometimes. The README no longer speaks of the guide's sessions.
- **The overview says how to follow along:** how to set up the example project, how to start over, and that answers differ from one run to the next. The note on naming the skill with smaller models moves there too, so that the steps don't repeat it.

Not part of this change:

- The findings on the other pages of the guide, in `playground/ai-agents-guide-befunde.md`, such as those in Setting Up, How the Skill Works and Troubleshooting, and what they say about code and files outside the guide. Only the sentences that speak of the recordings change there.
- Whether `robotcode discover` should substitute variables. The tutorial only stops saying that it shows them as a run does.
- The title of the group and "the usual agents".
- The agent demos of the home page, which have their own text.
- The recording pipeline in the git-ignored `playground/robotcode-demo/agent-sessions/`. It stays where it is, and the tutorial no longer uses it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ai-agents-guide`: the tutorial's requirement changes, requirements on prompts, answers, the commands the agent ran, links and what each step teaches are added, the five requirements on recorded sessions are removed, and the requirement on the example project is replaced because it speaks of the recordings and of a single failing test.

## Impact

- `docs/src/content/docs/guides/ai-agents/working-with-the-agent/`: all seven steps and the overview.
- `docs/src/content/docs/guides/ai-agents/index.mdx` (the summaries of the steps) and `docs/src/content/docs/guides/ai-agents/briefing.md` (one sentence on the recordings).
- `docs/src/styles/custom.css`: the rule for collapsed sessions goes, and the comment on the frames changes. The frames stay.
- The public repository `robotcodedev/webshop-ai-example`, pushed only after the maintainer confirms it.
- Runs of the prompts with several agents, in `playground/tutorial-probe/`, which aren't part of the repository.
- No code, no settings, no skill, no generated reference pages.
