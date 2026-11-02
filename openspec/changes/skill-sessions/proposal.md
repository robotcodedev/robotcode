# Proposal

## Why

`robotcode session` lets an agent work with the REPL and the debugger turn by turn, but the agent skill doesn't teach it. The skill says "drive it interactively" without saying how, so agents build their own named pipes or send a fixed list of inputs (findings B1 and A3–A6 in `playground/agent-skill-befunde.md`). The next RobotCode release brings sessions, and the skill of that release should teach them. Task 3.8 of `docs-ai-agents-guide` then records the guide's sessions with that skill.

## What Changes

- The skill teaches sessions as the way an agent drives the REPL and the debugger: `session start`, one `session send` per input with its exit code, `status`, `result`, `wait`, `interrupt`, `restart`, and `session stop` at the end. The piped fallback goes. The base is the draft checked in three trials with Claude Code, Copilot CLI and Codex.
- The skill says what a failing `session` command in a sandbox means, for all `session` commands: sessions work when the whole agent runs in one sandbox, not where each command has a sandbox of its own. There, an agent with a tool that writes to a running command drives `robotcode repl` or `robotcode robot-debug` in its terminal. It no longer tells the agent to leave the sandbox.
- The skill says that the top suite is named after `paths` and that names for `-s` and `-bl` come from `robotcode discover suites` (finding A1).
- The skill names `robotcode results log --search` for whether a value or an argument occurred in a run (finding A2).
- The evals of the plugin repo follow: the REPL and debugger cases expect sessions, two new cases cover names and search, and the harness can run a skill from a folder.
- The section "Where sessions can't run" of `guides/cli/sessions.md` says the same about sandboxes.
- The copy of the skill in `chat-plugins/` is synced.

No code changes in robotcode; a session that can't write its file already reports it clearly (`aef19d34b`).

## Capabilities

### New Capabilities
- `agent-skill-guidance`: what the RobotCode agent skill tells an agent about driving the REPL and the debugger, about sessions in a sandbox, about suite names and about searching a finished run, and how the evals check it.

### Modified Capabilities
- `cli-sessions`: the guide on sessions says where sessions work in a sandbox and where they don't.

## Impact

- `robotframework-agent-plugins`, branch `next`: `plugins/robotcode/skills/robotcode/SKILL.md`, `references/repl.md`, `references/debugging.md`, `evals/robotcode/`. The maintainer pushes.
- `robotcode`: `chat-plugins/` and `.upstream.json` (synced with `hatch run build:sync-chat-plugin`), `docs/src/content/docs/guides/cli/sessions.md`.
- `docs-ai-agents-guide`: task 3.8 waits for this change.
- The skill needs a robotcode with sessions. Plugin and robotcode are released together (`agent-plugin-release`), and `next` is not what users install.
