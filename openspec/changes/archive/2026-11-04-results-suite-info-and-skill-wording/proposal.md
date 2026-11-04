# Proposal

## Why

Recording the 13 sessions of the AI agents guide again with the corrected skill (task 3.8 of `docs-ai-agents-guide`) showed three things that still cost an agent a try or that it can't get from `robotcode results`:

- In 4 of the 13 sessions, the agent named the file of another run in a form `robotcode results` doesn't accept, because it doesn't read `references/results.md` before a short query.
- `SKILL.md` says that `robotcode session start` prints the ID. It prints a sentence with the ID, so one agent's `ID=$(…)` held the sentence and its next five commands failed.
- The text output of `robotcode results log --suite-info` leaves out the suites above a test. `log.html` shows them and `--format json` has them. One agent read the metadata of the top suite with Robot Framework's Python API instead.

The maintainer decided on each of them on 2026-11-03. The facts are in `playground/agent-skill-befunde.md`, section "`docs-ai-agents-guide`, Aufgabe 3.8" (findings N1, N2 and N3).

## What Changes

- **`robotcode results log --suite-info`, text output:** it shows a header for the suites above a test too, each with its documentation and metadata, top suite first, as `log.html` shows them. The JSON output doesn't change.
- **`SKILL.md`, the file of another run:** a sentence in "Interpreting results" says that `-o <file>` goes after the subcommand.
- **`SKILL.md`, starting a session:** both places that say "prints its ID" say what it prints, `Started session <ID>.`.
- **An eval case** measures the sentence on the file of another run, against the skill without it and with it.

Not part of this change:
- N4 (`grep` as a second check after `discover`), N5 (`robotcode analyze code` on a file outside the project stays at `Files: 0` and exit code 0) and N6 (no `config info desc` for settings already in the file) stay as they are, by the maintainer's decision.
- `robotcode results` gets no other way to name its file.
- The sessions on the guide's pages stay as they were recorded.

## Capabilities

### New Capabilities

- `results-log-suites`: how `robotcode results log --suite-info` shows the suites of a run.

### Modified Capabilities

- `agent-skill-guidance`: new requirements for the file of another run and for what starting a session prints.

## Impact

- `robotcode`:
  - `packages/runner/src/robotcode/runner/cli/results/_render.py` and the help of `--suite-info` in `results.py`;
  - `tests/robotcode/runner/cli/results/test_log.py` and its fixture `suites/nested/__init__.robot`;
  - `docs/src/content/docs/guides/cli/analyzing-results.md`, and `reference/cli.md`, which is generated.
- `robotframework-agent-plugins`, branch `next`:
  - `plugins/robotcode/skills/robotcode/SKILL.md`;
  - `evals/robotcode/cases/30-results-of-another-run.json` and the table in `evals/robotcode/README.md`.
- The vendored copy of the skill in `robotcode` is synced afterwards with `hatch run build:sync-chat-plugin`.
- Without `--suite-info`, the output of `results log` stays as it is. With it, the text output gets more headers; the JSON output stays as it is.
