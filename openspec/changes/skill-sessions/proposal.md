# Proposal

## Why

`robotcode session` lets an agent work with the REPL and the debugger turn by turn, but the agent skill doesn't teach it. The skill says "drive it interactively" without saying how, so agents build their own named pipes or send a fixed list of inputs (findings B1 and A3–A6 in `playground/agent-skill-befunde.md`). The next RobotCode release brings sessions, and the skill of that release should teach them. Task 3.8 of `docs-ai-agents-guide` then records the guide's sessions with that skill.

After the first round, the maintainer read and tried the skill: it explains what an agent doesn't need, such as a detection that works by itself, and it explains many rules several times. About 27 KB of 138 KB can go. `references/repl.md` and `references/debugging.md` are also built differently: one starts with sessions, the other works with `robot-debug` and has a section for agents far at the end.

## What Changes

- `references/repl.md` and `references/debugging.md` get the same order and start with a question: can the agent's shell tool keep a command running and write to its input? Then it works at the prompt of `robotcode repl` or `robotcode robot-debug`. Otherwise it runs a session: `session start`, one `session send` per input with its exit code, `status`, `result`, `wait`, `interrupt`, `restart`, and `session stop` at the end. The piped fallback goes. The base is the draft checked in three trials with Claude Code, Copilot CLI and Codex.
- The skill says what a failing `session` command in a sandbox means, for all `session` commands: sessions work when the whole agent runs in one sandbox, not where each command has a sandbox of its own. It no longer tells the agent to leave the sandbox.
- The skill gets shorter. What works without the agent doing anything, what it sees in a message anyway, what it can't send, what isn't for agents, and what is explained several times goes.
- A rule stands once, in `SKILL.md` in the section on its topic, and the other places link to it. Selecting one test or suite gets a section of its own, and the Gotchas section goes.
- What is wrong rather than repeated gets corrected: places that still show the debugger without saying how to drive it, an example that hands over a single `.robot` file, `report.html` where `log.html` is meant. The skill also says not to send several debugger steps in one shell command.
- The skill says that the top suite is named after `paths` and that names for `-s` and `-bl` come from `robotcode discover suites` (finding A1).
- The skill names `robotcode results log --search` for whether a value or an argument occurred in a run (finding A2).
- The evals of the plugin repo follow: the REPL and debugger cases accept a session or the prompt, new cases cover what the skill teaches, and the harness runs a skill from a folder with several agents. Beyond the first round, this was done directly on `next` on the maintainer's decision (`35baf03`, `dce5bf2`).
- The section "Where sessions can't run" of `guides/cli/sessions.md` says the same about sandboxes.
- The copy of the skill in `chat-plugins/` is synced.

No code changes in robotcode; a session that can't write its file already reports it clearly (`aef19d34b`).

## Capabilities

### New Capabilities
- `agent-skill-guidance`: what the RobotCode agent skill tells an agent about driving the REPL and the debugger, about sessions in a sandbox, about suite names and about searching a finished run, what it leaves out, where a rule stands, and how the evals check it.

### Modified Capabilities
- `cli-sessions`: the guide on sessions says where sessions work in a sandbox and where they don't.

## Impact

- `robotframework-agent-plugins`, branch `next`: all of `plugins/robotcode/skills/robotcode/`, `evals/robotcode/`. The maintainer pushes.
- `robotcode`: `chat-plugins/` and `.upstream.json` (synced with `hatch run build:sync-chat-plugin`), `docs/src/content/docs/guides/cli/sessions.md`.
- `docs-ai-agents-guide`: task 3.8 waits for this change.
- The skill needs a robotcode with sessions. Plugin and robotcode are released together (`agent-plugin-release`), and `next` is not what users install.
