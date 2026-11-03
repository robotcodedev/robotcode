# Proposal

## Why

An independent review of the RobotCode agent skill on 2026-11-02 found 37 places that are wrong or can't be followed, most of them months old. An agent that follows them reports the wrong configuration under a profile, destroys the recorded run, or gets an error from a command the skill shows. The evals were green because no case touches these places. A check against the guides for writing skills found `SKILL.md` over the recommended length, with the rules on debugging and results behind the 5000 tokens that Claude Code keeps after compaction. Some causes lie in `robotcode` itself, not in the text.

## What Changes

In `robotcode`:

- A line breakpoint matches by file name, as in gdb: `--break login.robot:42` stops in `tests/login.robot`. The form is what the docs and the news on 2.6.0 show, and today it runs through without a word.
- A breakpoint that no keyword reached gets a warning at the end of the run, and `.breakpoints` shows the location as it was given.
- `.abort`, `session stop`, `session restart` and the idle timeout end a debug run at a stop as SIGTERM does, so `output.xml` stays readable. This changes what `.abort` means: teardowns run and the output files are written, where it used to end the process at once. The exit code stays 253.
- `config info desc` finds a setting by its exact name, also with brackets.
- The example in `results --help` works.
- A `{ expr }` that can't be evaluated ends with `[ ERROR ]` and exit code 252 instead of a traceback.
- A dot command that can't do what was asked makes `session send` exit with 1.

In the skill (`robotframework-agent-plugins`, branch `next`):

- All findings of the review are corrected, among them `profiles show` for what is in effect under a profile, a debug run overwriting the recorded run, `--output` being relative to `output-dir`, options before a path, tasks in `discover`, `analyze code` without a path, and `enabled`.
- `SKILL.md` shrinks to about 5000 tokens, in an order that puts running, results and debugging first.
- The `description` stays as it is: shorter wordings were measured and made agents read the output file before they used the skill.

In the docs: the same errors where they stand there, and the new behaviour of `.abort`, breakpoints and `session send`. News posts stay as released.

In the evals: nine new cases, including `authoring.md`, `config.md` and `large-projects.md`, which no case opened so far, and a case in which the skill must not load; a run without the skill to compare with; the README on `claude plugin eval`.

`config show` stays as it is; only the text changes for it.

## Capabilities

### New Capabilities

- `line-breakpoints`: how line breakpoints of the command-line debugger match, and what it says about one that no keyword reached.
- `config-info-lookup`: how `config info desc` and `config info list` find a setting.

### Modified Capabilities

- `session-termination`: `.abort` and the ways a session ends a debug run at a stop end it as SIGTERM does.
- `cli-exit-codes`: an expression in `robot.toml` that can't be evaluated.
- `cli-sessions`: the exit code of `session send` for a dot command that can't do what was asked.
- `agent-skill-guidance`: what the skill says about these commands, its length and order, its `description`, and what the evals cover. This capability comes with `skill-sessions`, which is archived first.

## Impact

- `robotcode`: `packages/repl/` (debugger controller, console interpreter, session), `packages/runner/` (robot options, `results --help`), `src/robotcode/cli/commands/config.py`, tests under `tests/robotcode/`; `docs/src/content/docs/guides/cli/robot-debug.md`, `sessions.md`; `reference/cli.md` (generated); prose of the guide pages of `docs-ai-agents-guide`; `chat-plugins/` (synced).
- `robotframework-agent-plugins`, branch `next`: `plugins/robotcode/skills/robotcode/`, `evals/robotcode/`. The maintainer pushes.
- `docs-ai-agents-guide`: task 3.8 waits for this change, because its recordings show the skill's commands.
